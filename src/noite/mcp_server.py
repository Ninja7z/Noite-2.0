from __future__ import annotations

import asyncio
import os
import secrets
from pathlib import Path
from urllib.parse import urlsplit

from mcp.server.fastmcp import FastMCP

from .assistant import AssistantService
from .tools import search_workspace

MAX_PROMPT_CHARS = 4_000
MAX_RESPONSE_CHARS = 12_000
MIN_TOKEN_CHARS = 24
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def _bind_host() -> str:
    """O servidor só escuta em loopback; qualquer outro valor é recusado."""
    host = os.getenv("NOITE_MCP_HOST", "127.0.0.1").strip()
    if host not in _LOOPBACK_HOSTS:
        raise ValueError("NOITE_MCP_HOST só aceita 127.0.0.1, localhost ou ::1.")
    return host


def _is_loopback_origin(origin: str) -> bool:
    try:
        return (urlsplit(origin).hostname or "") in _LOOPBACK_HOSTS
    except ValueError:
        return False


class BearerAuthMiddleware:
    """Exige 'Authorization: Bearer <token>' e rejeita Origin que não seja loopback."""

    def __init__(self, app, token: str) -> None:
        self._app = app
        self._token = token.encode("utf-8")

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        origin = headers.get(b"origin")
        if origin is not None and not _is_loopback_origin(origin.decode("latin-1")):
            await self._reject(send, 403, b"Origem nao permitida.")
            return
        scheme, _, supplied = headers.get(b"authorization", b"").partition(b" ")
        if scheme.lower() != b"bearer" or not secrets.compare_digest(
            supplied.strip(), self._token
        ):
            await self._reject(send, 401, b"Token ausente ou invalido.")
            return
        await self._app(scope, receive, send)

    @staticmethod
    async def _reject(send, status: int, body: bytes) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"text/plain; charset=utf-8"),
                    (b"www-authenticate", b"Bearer"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


service = AssistantService()
_request_lock = asyncio.Lock()

mcp = FastMCP(
    "Noite 2.0",
    instructions=(
        "Ferramentas locais da Noite 2.0. Responda em português brasileiro. "
        "noite_ask conversa com o serviço existente da Noite e respeita as configurações "
        "de modelo e privacidade já definidas. noite_search_workspace pesquisa somente "
        "nomes de arquivos no workspace configurado; não lê nem altera arquivos. "
        "Nenhuma ferramenta deste servidor executa comandos do sistema ou modifica arquivos."
    ),
    host=_bind_host(),
    port=int(os.getenv("NOITE_MCP_PORT", "8767")),
    streamable_http_path="/mcp",
    stateless_http=True,
    json_response=True,
)


@mcp.tool()
def noite_status() -> dict[str, object]:
    """Retorna o estado do Ollama e do modelo configurado na Noite, sem expor segredos."""
    diagnostics = service.model_diagnostics()
    return {
        "assistant": "Noite 2.0",
        "model": diagnostics.get("model"),
        "ollama": diagnostics.get("server"),
        "model_installed": diagnostics.get("model_installed"),
        "installed_models": diagnostics.get("installed_models", []),
        "message": diagnostics.get("message", "Diagnóstico indisponível."),
    }


@mcp.tool()
def noite_search_workspace(query: str, limit: int = 20) -> dict[str, object]:
    """Pesquisa nomes de arquivos no workspace configurado, sem ler ou modificar seu conteúdo."""
    clean_query = query.strip()
    if not clean_query:
        raise ValueError("Informe um termo para pesquisar.")
    workspace = service.settings.workspace_dir or (Path(service.settings.data_dir) / "workspace")
    if not workspace.is_dir():
        return {"workspace_available": False, "results": []}
    matches = search_workspace(workspace, clean_query, limit=max(1, min(limit, 20)))
    return {"workspace_available": True, "count": len(matches), "results": matches}


@mcp.tool()
async def noite_ask(prompt: str) -> str:
    """Envia uma pergunta ao serviço da Noite 2.0 usando o modelo e as regras já configurados."""
    clean_prompt = prompt.strip()
    if not clean_prompt:
        raise ValueError("A pergunta não pode estar vazia.")
    if len(clean_prompt) > MAX_PROMPT_CHARS:
        raise ValueError(f"A pergunta excede o limite de {MAX_PROMPT_CHARS} caracteres.")
    async with _request_lock:
        answer = await service.respond(clean_prompt, conversation_id="mcp-openwebui")
    return answer[:MAX_RESPONSE_CHARS]


def main() -> None:
    token = os.getenv("NOITE_MCP_TOKEN", "").strip()
    if len(token) < MIN_TOKEN_CHARS:
        raise SystemExit(
            f"Defina NOITE_MCP_TOKEN com pelo menos {MIN_TOKEN_CHARS} caracteres "
            "(ex.: python -c \"import secrets; print(secrets.token_urlsafe(32))\") "
            "e envie-o como 'Authorization: Bearer <token>' no cliente MCP."
        )
    import uvicorn

    app = BearerAuthMiddleware(mcp.streamable_http_app(), token)
    uvicorn.run(app, host=mcp.settings.host, port=mcp.settings.port, log_level="warning")


if __name__ == "__main__":
    main()
