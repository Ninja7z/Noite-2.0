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


@pytest.fixture
def web_client(tmp_path, monkeypatch):
    monkeypatch.setattr(noite_api.service, "database_path", tmp_path / "web.sqlite3")
    with TestClient(noite_api.app, base_url="http://127.0.0.1") as client:
        yield client


def _session(client: TestClient) -> dict[str, str]:
    response = client.get("/web/session")
    assert response.status_code == 200
    return {"X-Noite-CSRF": response.json()["csrf"], "Origin": "http://127.0.0.1"}


def test_web_shell_assets_and_session_security(web_client: TestClient) -> None:
    page = web_client.get("/")
    assert page.status_code == 200
    assert "Noite 2.0" in page.text
    assert "Content-Security-Policy" in page.headers
    app_page = web_client.get("/app/")
    assert app_page.status_code == 200
    assert "Converse com a Noite" in app_page.text
    assert web_client.get("/app/assets/app.css").status_code == 200
    assert web_client.get("/app/assets/app.js").status_code == 200

    session = web_client.get("/web/session")
    assert session.status_code == 200
    cookie = session.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=strict" in cookie

    assert web_client.post("/web/api/conversations").status_code == 403
    assert web_client.post(
        "/web/api/conversations",
        headers={"X-Noite-CSRF": session.json()["csrf"], "Origin": "http://evil.example"},
    ).status_code == 403

    hostile_host = TestClient(noite_api.app, base_url="http://evil.example")
    assert hostile_host.get("/").status_code == 400


def test_web_chat_stream_and_conversation_lifecycle(web_client: TestClient) -> None:
    headers = _session(web_client)
    bootstrap = web_client.get("/web/api/bootstrap")
    assert bootstrap.status_code == 200

    created = web_client.post("/web/api/conversations", headers=headers)
    assert created.status_code == 200
    conversation_id = created.json()["id"]

    response = web_client.post(
        "/web/api/chat",
        json={"message": "sobre a noite", "conversation_id": conversation_id},
        headers=headers,
    )
    assert response.status_code == 200
    assert "event: token" in response.text
    assert "Noite 2.0" in response.text
    assert "event: done" in response.text

    history = web_client.get(
        f"/web/api/conversations/{conversation_id}/messages"
    )
    assert history.status_code == 200
    assert [item["role"] for item in history.json()["messages"]] == ["user", "assistant"]

    renamed = web_client.patch(
        f"/web/api/conversations/{conversation_id}",
        json={"title": "Teste web local"},
        headers=headers,
    )
    assert renamed.status_code == 200

    deleted = web_client.delete(
        f"/web/api/conversations/{conversation_id}",
        headers=headers,
    )
    assert deleted.status_code == 200
    assert deleted.json()["active_conversation_id"] != conversation_id
