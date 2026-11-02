from __future__ import annotations

import asyncio
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .assistant import AssistantService
from .tools import search_workspace

MAX_PROMPT_CHARS = 4_000
MAX_RESPONSE_CHARS = 12_000

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
    host=os.getenv("NOITE_MCP_HOST", "127.0.0.1"),
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


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
