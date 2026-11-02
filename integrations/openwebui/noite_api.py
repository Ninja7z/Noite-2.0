from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import sys
import time
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from noite.assistant import AssistantService  # noqa: E402

MODEL_ID = "noite-2.0"
API_KEY = os.environ.get("NOITE_OPENWEBUI_API_KEY", "").strip()
service = AssistantService()
app = FastAPI(title="Noite 2.0 API", version="0.1.0")


def _authorize(authorization: str | None) -> None:
    if not API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Chave interna da API da Noite não configurada.",
        )
    supplied = ""
    if authorization and authorization.lower().startswith("bearer "):
        supplied = authorization[7:].strip()
    if not supplied or not hmac.compare_digest(supplied, API_KEY):
        raise HTTPException(status_code=401, detail="Credencial inválida.")


def _conversation_id(body: dict, forwarded_chat_id: str | None = None) -> str:
    metadata = body.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    raw_id = (
        metadata.get("chat_id")
        or body.get("chat_id")
        or body.get("conversation_id")
        or metadata.get("session_id")
        or body.get("session_id")
        or forwarded_chat_id
    )
    if not raw_id:
        messages = body.get("messages")
        first_user = next(
            (
                message
                for message in messages
                if isinstance(message, dict) and message.get("role") == "user"
            ),
            None,
        ) if isinstance(messages, list) else None
        first_text = _content_text(first_user.get("content", "")) if first_user else ""
        user_info = body.get("user")
        user_id = metadata.get("user_id")
        if isinstance(user_info, dict):
            user_id = user_id or user_info.get("id")
        elif isinstance(user_info, str):
            user_id = user_id or user_info
        if first_text:
            seed = json.dumps(
                {"user": user_id or "local", "first_message": first_text},
                ensure_ascii=False,
                sort_keys=True,
            )
            raw_id = "fallback_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()
        else:
            raw_id = "fallback_" + uuid4().hex
    digest = hashlib.sha256(str(raw_id).encode("utf-8")).hexdigest()
    return f"openwebui_{digest}"


def _content_text(content: object) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, dict):
        if content.get("type") in {"text", "input_text"}:
            value = content.get("text", content.get("content", ""))
            return value.strip() if isinstance(value, str) else ""
        nested = content.get("content")
        return _content_text(nested) if nested is not None else ""
    if isinstance(content, list):
        parts = []
        for part in content:
            if not isinstance(part, dict) or part.get("type") not in {"text", "input_text"}:
                continue
            value = part.get("text", part.get("content", ""))
            if isinstance(value, str) and value.strip():
                parts.append(value.strip())
        return "\n".join(parts).strip()
    return ""


def _last_user_text(messages: object) -> str:
    if not isinstance(messages, list):
        raise HTTPException(status_code=400, detail="Campo messages inválido.")
    for message in reversed(messages):
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        text = _content_text(message.get("content", ""))
        if text:
            return text
    raise HTTPException(
        status_code=400,
        detail="Nenhuma mensagem de usuário com texto foi recebida.",
    )


def _history_messages(messages: object) -> list[tuple[str, str]]:
    if not isinstance(messages, list):
        return []
    last_user_index = next(
        (
            index
            for index in range(len(messages) - 1, -1, -1)
            if isinstance(messages[index], dict) and messages[index].get("role") == "user"
        ),
        len(messages),
    )
    history: list[tuple[str, str]] = []
    for message in messages[:last_user_index]:
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        if role not in {"user", "assistant"}:
            continue
        text = _content_text(message.get("content", ""))
        if text:
            history.append((role, text))
    return history[-12:]


@app.get("/health")
async def health() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "Noite 2.0",
        "model": service.model,
        "ollama": service.settings.ollama_base_url,
    }


@app.get("/v1/models")
async def models(authorization: str | None = Header(default=None)) -> dict[str, object]:
    _authorize(authorization)
    return {
        "object": "list",
        "data": [
            {
                "id": MODEL_ID,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "noite",
            }
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(
    body: dict,
    request: Request,
    authorization: str | None = Header(default=None),
    x_openwebui_chat_id: str | None = Header(default=None),
):
    _authorize(authorization)
    messages = body.get("messages")
    forwarded_chat_id = (
        x_openwebui_chat_id
        or request.headers.get("x-chat-id")
        or request.headers.get("x-conversation-id")
    )
    conversation_id = _conversation_id(body, forwarded_chat_id)
    user_text = _last_user_text(messages)
    history = _history_messages(messages)
    completion_id = f"chatcmpl-{uuid4().hex}"
    created = int(time.time())
    requested_model = str(body.get("model") or MODEL_ID)

    if not body.get("stream", False):
        try:
            answer = await service.respond(
                user_text,
                conversation_id=conversation_id,
                history_override=history,
            )
        except Exception:
            raise HTTPException(
                status_code=502,
                detail="A Noite não conseguiu concluir a resposta.",
            ) from None
        return JSONResponse(
            {
                "id": completion_id,
                "object": "chat.completion",
                "created": created,
                "model": requested_model,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": answer},
                        "finish_reason": "stop",
                    }
                ],
            }
        )

    async def stream_events():
        queue: asyncio.Queue[str] = asyncio.Queue()
        emitted: list[str] = []

        def on_chunk(chunk: str) -> None:
            if chunk:
                emitted.append(chunk)
                queue.put_nowait(chunk)

        task = asyncio.create_task(
            service.respond(
                user_text,
                conversation_id=conversation_id,
                on_chunk=on_chunk,
                history_override=history,
            )
        )

        def event(payload: dict) -> str:
            return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

        try:
            while not task.done() or not queue.empty():
                if await request.is_disconnected():
                    task.cancel()
                    return
                try:
                    chunk = await asyncio.wait_for(queue.get(), timeout=0.2)
                except TimeoutError:
                    continue
                yield event(
                    {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": requested_model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": chunk},
                                "finish_reason": None,
                            }
                        ],
                    }
                )

            answer = await task
            if not emitted and answer:
                yield event(
                    {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": requested_model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": answer},
                                "finish_reason": None,
                            }
                        ],
                    }
                )
            yield event(
                {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": requested_model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                }
            )
            yield "data: [DONE]\n\n"
        except asyncio.CancelledError:
            raise
        except Exception:
            yield event(
                {
                    "error": {
                        "message": "A Noite não conseguiu concluir a resposta.",
                        "type": "server_error",
                    }
                }
            )
            yield "data: [DONE]\n\n"
        finally:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    return StreamingResponse(
        stream_events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")
