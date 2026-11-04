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
        cwd=str(server_path.parent.resolve()),
    )
    client = MCPClient(startup_timeout=20, call_timeout=20)

    async def exercise():
        tools = await client.discover_tools(server)
        assert any(tool["name"] == "echo" for tool in tools)
        return await client.call_tool(server, "echo", {"text": "local"})

    assert asyncio.run(exercise()) == ["echo:local"]


def test_mcp_server_requires_absolute_existing_executable(tmp_path):
    client = MCPClient()
    server = MCPServer("invalid", "python", cwd=str(tmp_path))

    async def exercise():
        async with client._session(server):
            pass

    with pytest.raises(ValueError, match="caminho absoluto existente"):
        asyncio.run(exercise())


def test_mcp_server_requires_configured_environment_variable(tmp_path, monkeypatch):
    client = MCPClient()
    server = MCPServer(
        "invalid",
        sys.executable,
        cwd=str(tmp_path),
        env_vars=("NOITE_MCP_TEST_MISSING_VAR",),
    )

    async def exercise():
        async with client._session(server):
            pass

    monkeypatch.delenv("NOITE_MCP_TEST_MISSING_VAR", raising=False)
    with pytest.raises(ValueError, match="não está definida"):
        asyncio.run(exercise())


def test_mcp_arguments_resolve_secret_references_without_persisting_values(monkeypatch):
    from noite.mcp_client import _resolve_server_args

    monkeypatch.setenv("NOITE_MCP_TEST_VALUE", "secret-value")
    server = MCPServer(
        "safe",
        sys.executable,
        ("--api-key", "\u0024{NOITE_MCP_TEST_VALUE}"),
        env_vars=("NOITE_MCP_TEST_VALUE",),
    )

    assert _resolve_server_args(server, {"NOITE_MCP_TEST_VALUE": "secret-value"}) == [
        "--api-key",
        "secret-value",
    ]
    assert "secret-value" not in repr(server)


@pytest.mark.parametrize(
    "args",
    [
        ("--api-key", "hard-coded-secret"),
        ("--token=hard-coded-secret",),
        ("sk-12345678901234567890",),
        ("\u0024{NOITE_UNAUTHORIZED}",),
    ],
)
def test_mcp_arguments_reject_inline_or_unauthorized_secrets(args):
    from noite.mcp_client import _resolve_server_args

    server = MCPServer("unsafe", sys.executable, args)

    with pytest.raises(ValueError):
        _resolve_server_args(server, {})


def test_mcp_argument_validation_rejects_oversized_nested_and_non_json_values():
    from noite.mcp_client import _validate_tool_arguments

    with pytest.raises(ValueError, match="reservada"):
        _validate_tool_arguments({"__proto__": "polluted"})
    nested = "value"
    for _ in range(10):
        nested = {"child": nested}
    with pytest.raises(ValueError, match="estrutura"):
        _validate_tool_arguments({"nested": nested})
    with pytest.raises(ValueError, match="caracteres"):
        _validate_tool_arguments({"payload": "x" * 8_001})
    with pytest.raises(ValueError, match="JSON válido"):
        _validate_tool_arguments({"number": float("nan")})


def test_mcp_argument_validation_rejects_untrusted_schema_features():
    from noite.mcp_client import _validate_tool_schema

    with pytest.raises(ValueError, match="referência interna ou externa"):
        _validate_tool_schema({"type": "object", "$ref": "https://example.invalid/schema"})
    with pytest.raises(ValueError, match="referência interna ou externa"):
        _validate_tool_schema({"type": "object", "$ref": "#/$defs/node"})
    with pytest.raises(ValueError, match="padrões"):
        _validate_tool_schema({"type": "object", "properties": {"value": {"pattern": ".*"}}})


def test_mcp_client_rejects_host_and_provider_secrets_in_server_environment(tmp_path, monkeypatch):
    client = MCPClient()
    monkeypatch.setenv("ZAI_API_KEY", "private-provider-key")
    server = MCPServer(
        "unsafe",
        sys.executable,
        cwd=str(tmp_path),
        env_vars=("ZAI_API_KEY",),
    )

    async def exercise():
        async with client._session(server):
            pass

    with pytest.raises(ValueError, match="bloqueada"):
        asyncio.run(exercise())


@pytest.mark.parametrize(
    "name",
    ["MCP_SERVER_SECRET", "NOITE_MCP_PRIVATE_KEY", "MCP_CUSTOM_API_KEY", "NOITE_MCP_SESSION_TOKEN"],
)
def test_mcp_environment_prefix_does_not_authorize_secret_variables(name):
    from noite.mcp_client import _is_allowed_mcp_environment_variable

    assert not _is_allowed_mcp_environment_variable(name)
