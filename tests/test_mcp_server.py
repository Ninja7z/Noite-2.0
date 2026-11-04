import asyncio
from types import SimpleNamespace

import pytest

from noite import mcp_server


def test_noite_status_returns_only_safe_diagnostics(monkeypatch):
    monkeypatch.setattr(
        mcp_server.service,
        "model_diagnostics",
        lambda: {
            "model": "qwen2.5:3b",
            "server": "up",
            "model_installed": True,
            "installed_models": ["qwen2.5:3b"],
            "message": "Ollama conectado.",
            "api_key": "must-not-be-returned",
        },
    )

    result = mcp_server.noite_status()

    assert result == {
        "assistant": "Noite 2.0",
        "model": "qwen2.5:3b",
        "ollama": "up",
        "model_installed": True,
        "installed_models": ["qwen2.5:3b"],
        "message": "Ollama conectado.",
    }
    assert "api_key" not in result


def test_workspace_search_uses_only_configured_workspace(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "camera_controller.py").touch()
    (workspace / ".env").write_text("PRIVATE_TOKEN=hidden", encoding="utf-8")
    monkeypatch.setattr(
        mcp_server.service,
        "settings",
        SimpleNamespace(workspace_dir=workspace, data_dir=tmp_path),
    )

    result = mcp_server.noite_search_workspace("camera", limit=1000)

    assert result == {
        "workspace_available": True,
        "count": 1,
        "results": ["camera_controller.py"],
    }


def test_workspace_search_reports_missing_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(
        mcp_server.service,
        "settings",
        SimpleNamespace(workspace_dir=None, data_dir=tmp_path / "missing"),
    )

    assert mcp_server.noite_search_workspace("camera") == {
        "workspace_available": False,
        "results": [],
    }


def test_noite_ask_uses_an_isolated_temporary_conversation_and_caps_output(monkeypatch):
    captured = {}
    deleted = []

    async def fake_respond(prompt, *, conversation_id):
        captured["prompt"] = prompt
        captured["conversation_id"] = conversation_id
        return "x" * (mcp_server.MAX_RESPONSE_CHARS + 10)

    def fake_delete(conversation_id):
        deleted.append(conversation_id)

    monkeypatch.setattr(mcp_server.service, "respond", fake_respond)
    monkeypatch.setattr(mcp_server.service, "delete_conversation", fake_delete)

    answer = asyncio.run(mcp_server.noite_ask("  explique a cÃ¢mera  "))

    assert captured["prompt"] == "explique a cÃ¢mera"
    conversation_id = captured["conversation_id"]
    assert conversation_id.startswith("mcp-openwebui-")
    assert len(conversation_id) > len("mcp-openwebui-")
    assert deleted == [conversation_id]
    assert len(answer) == mcp_server.MAX_RESPONSE_CHARS


def test_noite_ask_rejects_empty_or_oversized_prompt():
    with pytest.raises(ValueError, match="vazia"):
        asyncio.run(mcp_server.noite_ask("   "))
    with pytest.raises(ValueError, match="excede o limite"):
        asyncio.run(mcp_server.noite_ask("x" * (mcp_server.MAX_PROMPT_CHARS + 1)))


def test_mcp_http_auth_verifies_only_the_configured_bearer_token():
    verifier = mcp_server._StaticTokenVerifier("local-test-token")

    valid = asyncio.run(verifier.verify_token("local-test-token"))
    invalid = asyncio.run(verifier.verify_token("wrong-token"))
    empty = asyncio.run(mcp_server._StaticTokenVerifier("").verify_token("anything"))

    assert valid is not None
    assert valid.client_id == "noite-local"
    assert valid.scopes == ["noite"]
    assert valid.resource == f"http://{mcp_server.MCP_HOST}:{mcp_server.MCP_PORT}"
    assert invalid is None
    assert empty is None
    assert mcp_server.mcp.settings.host == "127.0.0.1"
    assert mcp_server.mcp.settings.auth is not None
    assert mcp_server.mcp.settings.auth.required_scopes == ["noite"]
    assert mcp_server.mcp._token_verifier is not None
