from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "integrations" / "openwebui"))

import noite_api  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def test_provider_mode_requires_gemini_key_and_persists_nightly(tmp_path, monkeypatch):
    monkeypatch.setattr(noite_api.service.settings, "data_dir", tmp_path)
    monkeypatch.setattr(noite_api.service.settings, "gemini_api_key", None)
    with TestClient(noite_api.app, base_url="http://127.0.0.1") as client:
        session = client.get("/web/session")
        headers = {
            "X-Noite-CSRF": session.json()["csrf"],
            "Origin": "http://127.0.0.1",
        }
        status = client.get("/web/api/provider")
        assert status.status_code == 200
        assert status.json()["mode"] == "nightly"
        assert status.json()["gemini_configured"] is False

        blocked = client.post("/web/api/provider", json={"mode": "cloud"}, headers=headers)
        assert blocked.status_code == 409

        changed = client.post("/web/api/provider", json={"mode": "nightly"}, headers=headers)
        assert changed.status_code == 200
        assert changed.json()["mode"] == "nightly"
        assert (tmp_path / "provider_preferences.json").is_file()

        invalid = client.post("/web/api/provider", json={"mode": "other"}, headers=headers)
        assert invalid.status_code == 422


def test_cloud_mode_uses_gemini_for_normal_conversation(tmp_path, monkeypatch):
    from noite import assistant as assistant_module
    from noite.assistant import AssistantService
    from noite.config import Settings

    settings = Settings(_env_file=None, data_dir=tmp_path, provider_mode="cloud")
    assistant = AssistantService(settings)
    called = {}

    async def fake_gemini(*, messages, on_chunk=None):
        called["messages"] = messages
        return "resposta Gemini"

    async def unexpected_local(*args, **kwargs):
        raise AssertionError("Cloud mode should use Gemini")

    monkeypatch.setattr(assistant_module, "ask_gemini_model", fake_gemini)
    monkeypatch.setattr(assistant_module, "ask_local_model", unexpected_local)

    import asyncio

    answer = asyncio.run(assistant.respond("Explique a fotossíntese"))

    assert answer == "resposta Gemini"
    assert called["messages"][-1]["content"] == "Explique a fotossíntese"


def test_cloud_mode_keeps_sensitive_requests_local(tmp_path, monkeypatch):
    from noite import assistant as assistant_module
    from noite.assistant import AssistantService
    from noite.config import Settings

    settings = Settings(_env_file=None, data_dir=tmp_path, provider_mode="cloud")
    assistant = AssistantService(settings)
    called = {}

    async def fake_local(prompt, *, messages=None, model=None, on_chunk=None):
        called["prompt"] = prompt
        return "resposta local"

    async def unexpected_gemini(*args, **kwargs):
        raise AssertionError("Sensitive content must not be sent to Gemini")

    monkeypatch.setattr(assistant_module, "ask_local_model", fake_local)
    monkeypatch.setattr(assistant_module, "ask_gemini_model", unexpected_gemini)

    import asyncio

    answer = asyncio.run(assistant.respond("Resuma meu prontuário de saúde"))

    assert answer == "resposta local"
    assert "prontuário" in called["prompt"]


def test_cloud_mode_keeps_conversation_local_if_history_is_sensitive(tmp_path, monkeypatch):
    import asyncio

    from noite import assistant as assistant_module
    from noite.assistant import AssistantService
    from noite.config import Settings

    settings = Settings(_env_file=None, data_dir=tmp_path, provider_mode="cloud")
    assistant = AssistantService(settings)
    assistant._save("default", "user", "Meu CPF é 123.456.789-09")
    assistant._save("default", "assistant", "Entendi, vou manter esse dado privado.")
    called = {}

    async def fake_local(prompt, *, messages=None, model=None, on_chunk=None):
        called["provider"] = "local"
        return "resposta local"

    async def unexpected_gemini(*args, **kwargs):
        raise AssertionError("Sensitive history must not be sent to Gemini")

    monkeypatch.setattr(assistant_module, "ask_local_model", fake_local)
    monkeypatch.setattr(assistant_module, "ask_gemini_model", unexpected_gemini)

    answer = asyncio.run(assistant.respond("Me explique como proteger meus dados"))

    assert answer == "resposta local"
    assert called["provider"] == "local"
