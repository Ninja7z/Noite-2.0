from __future__ import annotations

import asyncio
import os
import re
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MAX_TOOL_RESULT_CHARS = 20_000
_ENV_REFERENCE = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")
_SECRET_ARGUMENT = re.compile(
    r"(?:sk-[A-Za-z0-9]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|"
    r"xox[baprs]-[A-Za-z0-9-]{12,}|AKIA[A-Z0-9]{16}|-----BEGIN [^-]*PRIVATE KEY-----)"
)
_SECRET_FLAGS = {"--token", "--api-key", "--password", "--secret", "--access-token"}


def _resolve_server_args(server: MCPServer, environment: dict[str, str]) -> list[str]:
    resolved_args: list[str] = []
    for index, argument in enumerate(server.args):
        reference = _ENV_REFERENCE.fullmatch(argument)
        if reference:
            variable = reference.group(1)
            if variable not in environment:
                raise ValueError(
                    f"O argumento MCP referencia uma variável não autorizada: {variable}."
                )
            resolved_args.append(environment[variable])
            continue
        if _SECRET_ARGUMENT.search(argument):
            raise ValueError(
                "Argumentos MCP parecem conter um segredo; use uma referência de ambiente."
            )
        if argument.casefold() in _SECRET_FLAGS:
            next_arg = server.args[index + 1] if index + 1 < len(server.args) else ""
            if not _ENV_REFERENCE.fullmatch(next_arg):
                raise ValueError(
                    "Valores de opções secretas MCP devem usar uma referência de ambiente."
                )
        if any(flag + "=" in argument.casefold() for flag in _SECRET_FLAGS):
            option, value = argument.split("=", maxsplit=1)
            reference = _ENV_REFERENCE.fullmatch(value)
            if reference is None:
                raise ValueError(
                    "Valores de opções secretas MCP devem usar uma referência de ambiente."
                )
            variable = reference.group(1)
            if variable not in environment:
                raise ValueError(
                    f"O argumento MCP referencia uma variável não autorizada: {variable}."
                )
            resolved_args.append(f"{option}={environment[variable]}")
            continue
        resolved_args.append(argument)
    return resolved_args


@dataclass(frozen=True)
class MCPServer:
    """Explicit local MCP server configuration; never created from model output."""

    name: str
    command: str
    args: tuple[str, ...] = ()
    allowed_tools: frozenset[str] = field(default_factory=frozenset)
    cwd: str = field(default_factory=lambda: str(Path.cwd()))
    env_vars: tuple[str, ...] = ()
    startup_timeout: float = 15.0
    call_timeout: float = 60.0


class MCPClient:
    def __init__(
        self,
        *,
        startup_timeout: float | None = None,
        call_timeout: float | None = None,
    ) -> None:
        self.startup_timeout = startup_timeout
        self.call_timeout = call_timeout

    @asynccontextmanager
    async def _session(self, server: MCPServer):
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError as exc:
            raise RuntimeError("Instale o extra MCP com: pip install -e '.[mcp]'") from exc

        executable = Path(server.command)
        if not executable.is_absolute() or not executable.is_file():
            raise ValueError("O executável MCP precisa ser um caminho absoluto existente.")
        cwd = Path(server.cwd).resolve(strict=True)
        if not cwd.is_dir():
            raise ValueError("O diretório de trabalho MCP precisa ser uma pasta existente.")
        if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) for name in server.env_vars):
            raise ValueError("Variáveis de ambiente MCP devem ser informadas somente pelo nome.")
        missing = [name for name in server.env_vars if name not in os.environ]
        if missing:
            raise ValueError("Uma variável de ambiente MCP configurada não está definida.")
        environment = {name: os.environ[name] for name in server.env_vars}
        resolved_args = _resolve_server_args(server, environment)
        params = StdioServerParameters(
            command=str(executable),
            args=resolved_args,
            env=environment,
            cwd=str(cwd),
        )
        startup_timeout = self.startup_timeout or server.startup_timeout
        async with AsyncExitStack() as stack:
            async with asyncio.timeout(startup_timeout):
                errlog = stack.enter_context(open(os.devnull, "w", encoding="utf-8"))
                read_stream, write_stream = await stack.enter_async_context(
                    stdio_client(params, errlog=errlog)
                )
                session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
                await session.initialize()
            yield session

    async def discover_tools(self, server: MCPServer) -> list[dict[str, Any]]:
        async with self._session(server) as session:
            async with asyncio.timeout(self.call_timeout or server.call_timeout):
                response = await session.list_tools()
        return [
            {
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": tool.inputSchema,
            }
            for tool in response.tools
        ]

    async def call_tool(
        self,
        server: MCPServer,
        name: str,
        arguments: dict[str, Any],
        input_schema: dict[str, Any] | None = None,
    ) -> list[str]:
        if name not in server.allowed_tools:
            raise PermissionError(f"A ferramenta MCP '{name}' não está autorizada.")
        try:
            from jsonschema import validate
        except ImportError as exc:
            raise RuntimeError("Instale o extra MCP com: pip install -e '.[mcp]'") from exc
        if input_schema is not None:
            validate(instance=arguments, schema=input_schema)
        async with self._session(server) as session:
            if input_schema is None:
                async with asyncio.timeout(self.call_timeout or server.call_timeout):
                    response = await session.list_tools()
                tool = next(
                    (candidate for candidate in response.tools if candidate.name == name), None
                )
                if tool is None:
                    raise LookupError(f"A ferramenta MCP '{name}' não foi encontrada.")
                validate(instance=arguments, schema=tool.inputSchema)
            async with asyncio.timeout(self.call_timeout or server.call_timeout):
                result = await session.call_tool(name, arguments)
        if result.isError:
            raise RuntimeError("O servidor MCP informou falha ao executar a ferramenta.")
        output: list[str] = []
        remaining = MAX_TOOL_RESULT_CHARS
        truncated = False
        for block in result.content:
            if getattr(block, "type", None) != "text" or not isinstance(block.text, str):
                continue
            if len(block.text) > remaining:
                output.append(block.text[:remaining])
                truncated = True
                break
            output.append(block.text)
            remaining -= len(block.text)
            if remaining == 0:
                truncated = True
                break
        if truncated:
            output.append(f"[… resultado truncado em {MAX_TOOL_RESULT_CHARS} caracteres]")
        return output
