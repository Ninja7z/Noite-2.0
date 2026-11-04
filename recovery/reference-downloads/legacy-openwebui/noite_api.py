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
        raise HTTPException(status_code=503, detail="Chave interna da API da Noite não configurada.")
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
        or forwarded_chat_id
    )
    if not raw_id:
        raise HTTPException(
            status_code=400,
            detail="Open WebUI não enviou metadata.chat_id; não é seguro associar o histórico.",
        )
    digest = hashlib.sha256(str(raw_id).encode("utf-8")).hexdigest()
    return f"openwebui_{digest}"


def _last_user_text(messages: object) -> str:
    if not isinstance(messages, list):
        raise HTTPException(status_code=400, detail="Campo messages inválido.")
    for message in reversed(messages):
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        content = message.get("content", "")
        if isinstance(content, str):
            text = content.strip()
        elif isinstance(content, list):
            text = "\n".join(
                str(part.get("text", ""))
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            ).strip()
        else:
            text = ""
        if text:
            return text
    raise HTTPException(status_code=400, detail="Nenhuma mensagem de usuário com texto foi recebida.")


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
    conversation_id = _conversation_id(body, x_openwebui_chat_id)
    user_text = _last_user_text(body.get("messages"))
    completion_id = f"chatcmpl-{uuid4().hex}"
    created = int(time.time())
    requested_model = str(body.get("model") or MODEL_ID)

    if not body.get("stream", False):
        try:
            answer = await service.respond(user_text, conversation_id=conversation_id)
        except Exception:
            raise HTTPException(status_code=502, detail="A Noite não conseguiu concluir a resposta.") from None
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
                        "choices": [{"index": 0, "delta": {"content": chunk}, "finish_reason": None}],
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
                        "choices": [{"index": 0, "delta": {"content": answer}, "finish_reason": None}],
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
            task.cancel()
            raise
        except Exception:
            if not task.done():
                task.cancel()
            yield event({"error": {"message": "A Noite não conseguiu concluir a resposta.", "type": "server_error"}})
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream_events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")
