from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "integrations" / "openwebui"))

from noite_api import _conversation_id, _history_messages, _last_user_text  # noqa: E402


def test_conversation_id_uses_openwebui_chat_id() -> None:
    chat_id = "chat-123"
    expected = "openwebui_" + hashlib.sha256(chat_id.encode()).hexdigest()
    assert _conversation_id({"metadata": {"chat_id": chat_id}}) == expected


def test_conversation_id_falls_back_stably_without_chat_metadata() -> None:
    body = {
        "user": {"id": "user-1"},
        "messages": [{"role": "user", "content": "Primeira pergunta"}],
    }
    assert _conversation_id(body) == _conversation_id(body)
    other = {
        "user": {"id": "user-1"},
        "messages": [{"role": "user", "content": "Outra pergunta"}],
    }
    assert _conversation_id(body) != _conversation_id(other)


def test_last_user_text_accepts_openai_input_text_parts() -> None:
    messages = [
        {"role": "user", "content": [{"type": "input_text", "text": "  Olá Noite  "}]}
    ]
    assert _last_user_text(messages) == "Olá Noite"


def test_history_uses_previous_user_and_assistant_messages_only() -> None:
    messages = [
        {"role": "system", "content": "Instrução externa"},
        {"role": "user", "content": "Oi"},
        {"role": "assistant", "content": "Olá!"},
        {"role": "tool", "content": "resultado"},
        {"role": "user", "content": "Como você está?"},
    ]
    assert _history_messages(messages) == [("user", "Oi"), ("assistant", "Olá!")]


def test_history_ignores_non_text_multimodal_parts() -> None:
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,AA=="}}
            ],
        },
        {"role": "user", "content": "Pergunta atual"},
    ]
    assert _history_messages(messages) == []
    assert _last_user_text(messages) == "Pergunta atual"
