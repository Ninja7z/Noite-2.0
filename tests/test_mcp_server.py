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


def test_noite_ask_reuses_assistant_service_and_caps_output(monkeypatch):
    captured = {}

    async def fake_respond(prompt, *, conversation_id):
        captured["prompt"] = prompt
        captured["conversation_id"] = conversation_id
        return "x" * (mcp_server.MAX_RESPONSE_CHARS + 10)

    monkeypatch.setattr(mcp_server.service, "respond", fake_respond)

    answer = asyncio.run(mcp_server.noite_ask("  explique a cÃ¢mera  "))

    assert captured == {
        "prompt": "explique a cÃ¢mera",
        "conversation_id": "mcp-openwebui",
    }
    assert len(answer) == mcp_server.MAX_RESPONSE_CHARS


def test_noite_ask_rejects_empty_or_oversized_prompt():
    with pytest.raises(ValueError, match="vazia"):
        asyncio.run(mcp_server.noite_ask("   "))
    with pytest.raises(ValueError, match="excede o limite"):
        asyncio.run(mcp_server.noite_ask("x" * (mcp_server.MAX_PROMPT_CHARS + 1)))


def _call_asgi(app, headers):
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    scope = {"type": "http", "method": "POST", "path": "/mcp", "headers": headers}
    asyncio.run(app(scope, receive, send))
    return sent


def _auth_app():
    calls = []

    async def inner(scope, receive, send):
        calls.append(scope["path"])
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    return mcp_server.BearerAuthMiddleware(inner, "t" * 32), calls


def test_mcp_http_rejects_missing_or_wrong_token():
    app, calls = _auth_app()
    assert _call_asgi(app, [])[0]["status"] == 401
    wrong = [(b"authorization", b"Bearer " + b"x" * 32)]
    assert _call_asgi(app, wrong)[0]["status"] == 401
    assert calls == []


def test_mcp_http_accepts_valid_token_and_loopback_origin():
    app, calls = _auth_app()
    headers = [
        (b"authorization", b"Bearer " + b"t" * 32),
        (b"origin", b"http://localhost:3000"),
    ]
    assert _call_asgi(app, headers)[0]["status"] == 200
    assert calls == ["/mcp"]


def test_mcp_http_rejects_foreign_origin_even_with_valid_token():
    app, calls = _auth_app()
    headers = [
        (b"authorization", b"Bearer " + b"t" * 32),
        (b"origin", b"https://evil.example"),
    ]
    assert _call_asgi(app, headers)[0]["status"] == 403
    assert calls == []


def test_mcp_bind_host_refuses_non_loopback(monkeypatch):
    monkeypatch.setenv("NOITE_MCP_HOST", "0.0.0.0")
    with pytest.raises(ValueError, match="127.0.0.1"):
        mcp_server._bind_host()
    monkeypatch.setenv("NOITE_MCP_HOST", "localhost")
    assert mcp_server._bind_host() == "localhost"


def test_mcp_main_requires_strong_token(monkeypatch):
    monkeypatch.setenv("NOITE_MCP_TOKEN", "curto")
    with pytest.raises(SystemExit, match="NOITE_MCP_TOKEN"):
        mcp_server.main()
