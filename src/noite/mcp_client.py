from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MCPServer:
    """Explicit local MCP server configuration; never created from model output."""

    name: str
    command: str
    args: tuple[str, ...] = ()
    allowed_tools: frozenset[str] = field(default_factory=frozenset)


class MCPClient:
    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout

    @asynccontextmanager
    async def _session(self, server: MCPServer):
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError as exc:
            raise RuntimeError("Instale o extra MCP com: pip install -e '.[mcp]'") from exc

        params = StdioServerParameters(command=server.command, args=list(server.args))
        async with asyncio.timeout(self.timeout):
            async with stdio_client(params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    yield session

    async def discover_tools(self, server: MCPServer) -> list[dict[str, Any]]:
        async with self._session(server) as session:
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
        self, server: MCPServer, name: str, arguments: dict[str, Any]
    ) -> list[str]:
        if name not in server.allowed_tools:
            raise PermissionError(f"A ferramenta MCP '{name}' não está autorizada.")
        async with self._session(server) as session:
            response = await session.list_tools()
            tool = next((candidate for candidate in response.tools if candidate.name == name), None)
            if tool is None:
                raise LookupError(f"A ferramenta MCP '{name}' não foi encontrada.")
            try:
                from jsonschema import validate

                validate(instance=arguments, schema=tool.inputSchema)
            except ImportError as exc:
                raise RuntimeError("Instale o extra MCP com: pip install -e '.[mcp]'") from exc
            result = await session.call_tool(name, arguments)
        if result.isError:
            raise RuntimeError("O servidor MCP informou falha ao executar a ferramenta.")
        return [
            block.text
            for block in result.content
            if getattr(block, "type", None) == "text" and isinstance(block.text, str)
        ]
