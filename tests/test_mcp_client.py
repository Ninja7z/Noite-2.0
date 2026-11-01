import asyncio
import sys
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

from noite.mcp_client import MCPClient, MCPServer


class FakeSession:
    async def list_tools(self):
        return SimpleNamespace(
            tools=[
                SimpleNamespace(
                    name="lookup",
                    description="Untrusted description",
                    inputSchema={
                        "type": "object",
                        "properties": {"term": {"type": "string"}},
                        "required": ["term"],
                        "additionalProperties": False,
                    },
                )
            ]
        )

    async def call_tool(self, name, arguments):
        assert name == "lookup"
        assert arguments == {"term": "hello"}
        return SimpleNamespace(
            isError=False,
            content=[SimpleNamespace(type="text", text="Untrusted result")],
        )


def _fake_session(client):
    @asynccontextmanager
    async def session(_server):
        yield FakeSession()

    client._session = session


def test_discover_tools_uses_configured_server(monkeypatch) -> None:
    client = MCPClient()
    _fake_session(client)
    server = MCPServer("example", "trusted-command", ("--stdio",))

    tools = asyncio.run(client.discover_tools(server))

    assert tools[0]["name"] == "lookup"
    assert tools[0]["input_schema"]["required"] == ["term"]


def test_call_tool_requires_allowlist(tmp_path) -> None:
    client = MCPClient()
    server = MCPServer("example", "trusted-command")

    with pytest.raises(PermissionError):
        asyncio.run(client.call_tool(server, "lookup", {"term": "hello"}))


def test_call_tool_validates_schema_and_returns_data() -> None:
    client = MCPClient()
    _fake_session(client)
    server = MCPServer("example", "trusted-command", allowed_tools=frozenset({"lookup"}))

    with pytest.raises(Exception):
        asyncio.run(client.call_tool(server, "lookup", {"wrong": "hello"}))
    assert asyncio.run(client.call_tool(server, "lookup", {"term": "hello"})) == [
        "Untrusted result"
    ]


def test_tool_schema_is_validated_before_opening_server() -> None:
    client = MCPClient()
    opened = []

    @asynccontextmanager
    async def fake_session(_server):
        opened.append(True)
        yield FakeSession()

    client._session = fake_session
    server = MCPServer("example", "configured-server", allowed_tools=frozenset({"lookup"}))

    with pytest.raises(Exception):
        asyncio.run(
            client.call_tool(
                server,
                "lookup",
                {"wrong": "value"},
                input_schema={
                    "type": "object",
                    "properties": {"term": {"type": "string"}},
                    "required": ["term"],
                    "additionalProperties": False,
                },
            )
        )
    assert opened == []


def test_tool_result_is_capped():
    from noite.mcp_client import MAX_TOOL_RESULT_CHARS

    client = MCPClient()
    _fake_session(client)
    server = MCPServer("example", "trusted-command", allowed_tools=frozenset({"lookup"}))

    class LargeSession(FakeSession):
        async def call_tool(self, name, arguments):
            return SimpleNamespace(
                isError=False,
                content=[SimpleNamespace(type="text", text="x" * (MAX_TOOL_RESULT_CHARS + 10))],
            )

    @asynccontextmanager
    async def large_session(_server):
        yield LargeSession()

    client._session = large_session
    output = asyncio.run(
        client.call_tool(
            server,
            "lookup",
            {"term": "hello"},
            input_schema={"type": "object", "properties": {"term": {"type": "string"}}},
        )
    )

    assert len(output[0]) == MAX_TOOL_RESULT_CHARS
    assert "truncado" in output[1]


def test_stdio_client_discovers_and_calls_real_local_server() -> None:
    from pathlib import Path

    server_path = Path(__file__).with_name("mcp_echo_server.py")
    server = MCPServer(
        "integration",
        sys.executable,
        (str(server_path),),
        allowed_tools=frozenset({"echo"}),
    )
    client = MCPClient(timeout=20)

    async def exercise():
        tools = await client.discover_tools(server)
        assert any(tool["name"] == "echo" for tool in tools)
        return await client.call_tool(server, "echo", {"text": "local"})

    assert asyncio.run(exercise()) == ["echo:local"]
