from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from noite.assistant import AssistantService  # noqa: E402
from noite.contracts import IntentKind  # noqa: E402
from noite.orchestrator import Orchestrator  # noqa: E402

MODEL_ID = "noite-2.0"
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
API_KEY = os.environ.get("NOITE_OPENWEBUI_API_KEY", "").strip()
service = AssistantService()
orchestrator = Orchestrator(service)
orchestrator.set_activity_callback(
    lambda event: _record_activity(event.operation, event.state, event.summary, event.details)
)
_recent_activities: list[dict] = []


def _visible_mascot_pid() -> int | None:
    """Retorna o PID que realmente possui a janela visível do mascote no Windows."""
    if os.name != "nt":
        return None

    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    enum_windows = user32.EnumWindows
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    enum_windows.argtypes = [callback_type, wintypes.LPARAM]
    enum_windows.restype = wintypes.BOOL
    get_title = user32.GetWindowTextW
    get_title.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    get_title.restype = ctypes.c_int
    is_visible = user32.IsWindowVisible
    is_visible.argtypes = [wintypes.HWND]
    is_visible.restype = wintypes.BOOL
    get_pid = user32.GetWindowThreadProcessId
    get_pid.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    get_pid.restype = wintypes.DWORD

    found: list[int] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def visit(hwnd: int, _lparam: int) -> bool:
        if is_visible(hwnd):
            title = ctypes.create_unicode_buffer(256)
            get_title(hwnd, title, len(title))
            if title.value == "Noite 2.0":
                pid = wintypes.DWORD()
                get_pid(hwnd, ctypes.byref(pid))
                if pid.value:
                    found.append(int(pid.value))
                    return False
        return True

    enum_windows(visit, 0)
    return found[0] if found else None


def _restore_existing_mascot() -> int | None:
    """Mostra uma instância já aberta, mesmo se ela estiver oculta."""
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [callback, wintypes.LPARAM]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    found: list[int] = []

    @callback
    def visit(hwnd, _):
        title = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, title, len(title))
        if title.value == "Noite 2.0":
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            user32.ShowWindow(hwnd, 5)  # SW_SHOW
            found.append(int(pid.value))
            return False
        return True

    user32.EnumWindows(visit, 0)
    return found[0] if found else None


def _launch_mascot() -> dict[str, object]:
    """Inicia o mascote e só confirma sucesso quando a janela real estiver visível."""
    app_data = Path(os.environ.get("LOCALAPPDATA", str(ROOT))) / "NoiteAPI"
    app_data.mkdir(parents=True, exist_ok=True)
    pid_file = app_data / "mascot.pid"

    visible_pid = _restore_existing_mascot()
    if visible_pid is not None:
        pid_file.write_text(str(visible_pid), encoding="utf-8")
        return {"ok": True, "detail": "Mascote já está visível na tela.", "pid": visible_pid}

    pythonw = ROOT / ".venv" / "Scripts" / "pythonw.exe"
    python = ROOT / ".venv" / "Scripts" / "python.exe"
    executable = pythonw if pythonw.is_file() else python
    if not executable.is_file():
        return {"ok": False, "detail": f"Python do ambiente Noite não encontrado: {executable}"}

    pid_file.unlink(missing_ok=True)
    try:
        process = subprocess.Popen(
            [str(executable), "-m", "noite"],
            cwd=str(ROOT),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0),
        )
    except OSError as exc:
        return {"ok": False, "detail": f"Falha ao iniciar o mascote: {type(exc).__name__}"}

    if os.name == "nt":
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            visible_pid = _visible_mascot_pid()
            if visible_pid is not None:
                pid_file.write_text(str(visible_pid), encoding="utf-8")
                return {
                    "ok": True,
                    "detail": "Mascote aberto e janela visível.",
                    "pid": visible_pid,
                }
            if process.poll() is not None:
                break
            time.sleep(0.25)

        return {
            "ok": False,
            "detail": (
                "O processo foi iniciado, mas a janela do mascote não ficou "
                "visível em até 10 segundos."
            ),
            "pid": process.pid,
        }

    pid_file.write_text(str(process.pid), encoding="utf-8")
    return {"ok": True, "detail": "Mascote iniciado.", "pid": process.pid}


def _hide_mascot() -> dict[str, object]:
    """Oculta todas as janelas visíveis do mascote sem encerrar os processos."""
    if os.name != "nt":
        return {"ok": False, "detail": "Disponível apenas no Windows."}
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindow.restype = wintypes.BOOL

    windows: list[int] = []

    @callback_type
    def visit(hwnd, _lparam):
        title = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, title, len(title))
        if title.value == "Noite 2.0" and user32.IsWindowVisible(hwnd):
            windows.append(int(hwnd))
        return True

    user32.EnumWindows(visit, 0)
    for hwnd in windows:
        user32.ShowWindow(hwnd, 0)  # SW_HIDE

    if not windows:
        return {"ok": False, "detail": "Nenhuma janela visível do mascote foi encontrada."}

    app_data = Path(os.environ.get("LOCALAPPDATA", str(ROOT))) / "NoiteAPI"
    (app_data / "mascot.pid").unlink(missing_ok=True)
    return {"ok": True, "detail": "Mascote ocultado.", "windows_hidden": len(windows)}


async def abrir_mascote(_intent) -> str:
    """Ação determinística: abre o mascote desktop, sem passar pelo MCP do Roblox."""
    result = _launch_mascot()
    if not result.get("ok"):
        raise RuntimeError(str(result.get("detail") or "Falha ao iniciar o mascote."))
    return "Mascote aberto na tela."


async def esconder_mascote(_intent) -> str:
    """Ação determinística: oculta a janela sem encerrar o mascote."""
    result = _hide_mascot()
    if not result.get("ok"):
        raise RuntimeError(str(result.get("detail") or "Falha ao ocultar o mascote."))
    return "Mascote escondido."


orchestrator.register_action_handler(IntentKind.SHOW_MASCOT, abrir_mascote)
orchestrator.register_action_handler(IntentKind.HIDE_MASCOT, esconder_mascote)
app = FastAPI(title="Noite 2.0 API", version="0.1.0")


def _record_activity(operation: str, state: str, summary: str, details: str = "") -> None:
    _recent_activities.append(
        {
            "operation": operation,
            "state": state,
            "summary": summary,
            "details": details,
            "occurred_at": datetime.now().astimezone().isoformat(),
        }
    )
    if len(_recent_activities) > 200:
        _recent_activities.pop(0)


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
        first_user = (
            next(
                (
                    message
                    for message in messages
                    if isinstance(message, dict) and message.get("role") == "user"
                ),
                None,
            )
            if isinstance(messages, list)
            else None
        )
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


async def _ollama_installed_models() -> list[dict[str, object]]:
    """Consulta o Ollama local e retorna os modelos instalados no formato OpenAI."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            response.raise_for_status()
            payload = response.json()
    except Exception:
        return []
    models: list[dict[str, object]] = []
    for entry in payload.get("models", []):
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", "")).strip()
        if not name:
            continue
        models.append(
            {
                "id": name,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "ollama",
            }
        )
    return models


@app.get("/v1/models")
async def models(authorization: str | None = Header(default=None)) -> dict[str, object]:
    _authorize(authorization)
    data: list[dict[str, object]] = [
        {
            "id": MODEL_ID,
            "object": "model",
            "created": int(time.time()),
            "owned_by": "noite",
        }
    ]
    data.extend(await _ollama_installed_models())
    return {"object": "list", "data": data}


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
            answer = await orchestrator.process_request(
                user_text,
                conversation_id=conversation_id,
                history=history,
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
            orchestrator.process_request(
                user_text,
                conversation_id=conversation_id,
                history=history,
                on_activity=lambda event: _record_activity(
                    event.operation, event.state, event.summary, event.details
                ),
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


@app.post("/v1/mascot/show")
async def mascot_show(authorization: str | None = Header(default=None)) -> dict[str, object]:
    """Chama o mascote para a tela (overlay sem janela de fundo)."""
    _authorize(authorization)
    return _launch_mascot()


@app.post("/v1/mascot/hide")
async def mascot_hide(authorization: str | None = Header(default=None)) -> dict[str, object]:
    """Esconde o mascote da tela."""
    _authorize(authorization)
    return _hide_mascot()


@app.post("/v1/mascot/balloon")
async def mascot_balloon(
    body: dict,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    """Exibe um balão de atividade no mascote."""
    _authorize(authorization)
    return {"ok": False, "detail": "Balões de texto foram removidos do mascote."}


@app.get("/v1/mascot/activity")
async def mascot_activity(
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    """Retorna as atividades recentes do orquestrador para o mascote exibir."""
    _authorize(authorization)
    return {"activities": list(_recent_activities)}


@app.get("/v1/mascot/status")
async def mascot_status(
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    """Retorna o status atual do mascote."""
    _authorize(authorization)
    pid = _visible_mascot_pid()
    return {"ok": pid is not None, "status": "visible" if pid is not None else "hidden"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")
