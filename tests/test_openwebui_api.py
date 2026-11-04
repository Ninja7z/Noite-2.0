from __future__ import annotations

import asyncio
import hashlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("fastapi")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "integrations" / "openwebui"))

from noite_api import (  # noqa: E402
    INTEGRATION_CHECKS,
    _conversation_id,
    _history_messages,
    _last_user_text,
    _openwebui_image_messages,
    _openwebui_reference_context,
    _openwebui_tool_messages,
    _openwebui_tool_request,
    _validated_tool_assistant_message,
    chat_completions,
    gerenciar_mascote,
)


def test_integration_health_map_uses_the_actual_local_ports() -> None:
    ports = {item[0]: item[3] for item in INTEGRATION_CHECKS}
    assert ports == {
        "noite-api": 8765,
        "noite-web": 8766,
        "noite-mcp": 8767,
        "roblox-mcp": 8768,
        "open-webui": 8080,
        "ollama": 11434,
    }


def test_conversation_id_uses_openwebui_chat_id() -> None:
    chat_id = "chat-123"
    expected = "openwebui_" + hashlib.sha256(chat_id.encode()).hexdigest()
    assert _conversation_id({"metadata": {"chat_id": chat_id}}) == expected


def test_conversation_id_without_chat_metadata_is_unique_per_request() -> None:
    body = {
        "user": {"id": "user-1"},
        "messages": [{"role": "user", "content": "Primeira pergunta"}],
    }
    assert _conversation_id(body) != _conversation_id(body)


def test_last_user_text_accepts_openai_input_text_parts() -> None:
    messages = [{"role": "user", "content": [{"type": "input_text", "text": "  Olá Noite  "}]}]
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
            "content": [{"type": "image_url", "image_url": {"url": "data:image/png;base64,AA=="}}],
        },
        {"role": "user", "content": "Pergunta atual"},
    ]
    assert _history_messages(messages) == []
    assert _last_user_text(messages) == "Pergunta atual"


@pytest.mark.parametrize(
    ("action", "expected_answer", "expected_call"),
    [
        ("close", "Mascote encerrado.", "close"),
        ("hide", "Mascote escondido.", "hide"),
    ],
)
def test_gerenciar_mascote_dispatches_explicit_action(
    monkeypatch, action: str, expected_answer: str, expected_call: str
) -> None:
    calls: list[str] = []

    def close_mascot() -> dict[str, object]:
        calls.append("close")
        return {"ok": True}

    def hide_mascot() -> dict[str, object]:
        calls.append("hide")
        return {"ok": True}

    monkeypatch.setattr("noite_api._close_mascot", close_mascot)
    monkeypatch.setattr("noite_api._hide_mascot", hide_mascot)

    intent = SimpleNamespace(parameters={"action": action})
    answer = asyncio.run(gerenciar_mascote(intent))

    assert answer == expected_answer
    assert calls == [expected_call]


def test_gerenciar_mascote_defaults_to_hide(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        "noite_api._hide_mascot",
        lambda: calls.append("hide") or {"ok": True},
    )

    answer = asyncio.run(gerenciar_mascote(SimpleNamespace(parameters={})))

    assert answer == "Mascote escondido."
    assert calls == ["hide"]


def test_openwebui_tool_request_accepts_function_tools() -> None:
    tools = [
        {
            "type": "function",
            "function": {
                "name": "noite_status",
                "description": "Status local",
                "parameters": {"type": "object", "properties": {}},
            },
        }
    ]
    assert _openwebui_tool_request({"tools": tools}) == (tools, "auto")


@pytest.mark.parametrize(
    "body",
    [
        {"tools": "not-a-list"},
        {"tools": [{"type": "shell", "function": {}}]},
        {"tools": [{"type": "function", "function": {"name": "bad name"}}]},
        {"tools": [{"type": "function", "function": {"name": "x", "parameters": []}}]},
        {"tools": [{"type": "function", "function": {"name": "x"}}], "tool_choice": "invalid"},
    ],
)
def test_openwebui_tool_request_rejects_invalid_definitions(body) -> None:
    with pytest.raises(Exception):
        _openwebui_tool_request(body)


def test_openwebui_tool_messages_preserve_tool_round_trip_and_add_guard() -> None:
    incoming = [
        {"role": "system", "content": "Estilo de resposta conciso."},
        {"role": "user", "content": "Veja o status."},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "noite_status", "arguments": "{}"},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call_1", "content": "{'status': 'ok'}"},
        {"role": "user", "content": "Resuma o resultado."},
    ]

    result = _openwebui_tool_messages(incoming)

    assert result[0] == incoming[0]
    assert "Open WebUI controla a execução" in result[1]["content"]
    assert result[3]["tool_calls"] == incoming[2]["tool_calls"]
    assert result[4]["tool_call_id"] == "call_1"
    assert result[4]["content"] == "{'status': 'ok'}"


def test_openwebui_tool_messages_reject_tool_result_without_call_id() -> None:
    with pytest.raises(Exception):
        _openwebui_tool_messages(
            [{"role": "user", "content": "Oi"}, {"role": "tool", "content": "resultado"}]
        )


def test_validated_assistant_tool_message_requires_json_object_arguments() -> None:
    with pytest.raises(Exception):
        _validated_tool_assistant_message(
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "noite_status", "arguments": "[]"},
                    }
                ],
            }
        )

    valid = _validated_tool_assistant_message(
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_2",
                    "type": "function",
                    "function": {"name": "noite_status", "arguments": "{}"},
                }
            ],
        }
    )
    assert valid["tool_calls"][0]["function"]["arguments"] == "{}"


@pytest.mark.parametrize("stream", [False, True])
def test_chat_completions_returns_openwebui_tool_calls(monkeypatch, stream: bool) -> None:
    import json

    from starlette.requests import Request

    import noite.model_gateway

    monkeypatch.setattr("noite_api.API_KEY", "test-openwebui-key")
    captured = {}

    async def fake_tool_completion(*, messages, tools, tool_choice):
        captured.update(messages=messages, tools=tools, tool_choice=tool_choice)
        return {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_test",
                    "type": "function",
                    "function": {"name": "noite_status", "arguments": "{}"},
                }
            ],
        }

    monkeypatch.setattr(
        noite.model_gateway,
        "ask_local_model_with_tools",
        fake_tool_completion,
    )
    body = {
        "model": "noite-2.0",
        "stream": stream,
        "messages": [{"role": "user", "content": "Consulte o status."}],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "noite_status",
                    "description": "Status local",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ],
    }
    request = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/v1/chat/completions",
            "raw_path": b"/v1/chat/completions",
            "query_string": b"",
            "headers": [],
            "server": ("127.0.0.1", 8765),
            "client": ("127.0.0.1", 12345),
        }
    )

    async def invoke():
        response = await chat_completions(
            body,
            request,
            authorization="Bearer test-openwebui-key",
            x_openwebui_chat_id="chat-tool-test",
        )
        if stream:
            chunks = [chunk async for chunk in response.body_iterator]
            return (
                "".join(chunks)
                if chunks and isinstance(chunks[0], str)
                else b"".join(chunks).decode("utf-8")
            )
        return response.body.decode("utf-8")

    response_body = asyncio.run(invoke())

    assert "Open WebUI controla a execução" in captured["messages"][0]["content"]
    assert captured["tools"] == body["tools"]
    if stream:
        assert '"finish_reason": "tool_calls"' in response_body
        assert '"name": "noite_status"' in response_body
        assert response_body.endswith("data: [DONE]\n\n")
    else:
        payload = json.loads(response_body)
        choice = payload["choices"][0]
        assert choice["finish_reason"] == "tool_calls"
        assert choice["message"]["tool_calls"][0]["id"] == "call_test"


def test_openwebui_tool_request_validates_explicit_tool_choice() -> None:
    tool = {
        "type": "function",
        "function": {"name": "noite_status", "parameters": {"type": "object"}},
    }
    selected = {"type": "function", "function": {"name": "noite_status"}}
    assert _openwebui_tool_request({"tools": [tool], "tool_choice": selected}) == (
        [tool],
        selected,
    )
    with pytest.raises(Exception):
        _openwebui_tool_request(
            {"tools": [tool], "tool_choice": {"type": "function", "function": {"name": "other"}}}
        )


def test_model_cannot_return_a_tool_that_openwebui_did_not_advertise() -> None:
    with pytest.raises(Exception):
        _validated_tool_assistant_message(
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "call_unknown",
                        "type": "function",
                        "function": {"name": "not_advertised", "arguments": "{}"},
                    }
                ],
            },
            allowed_tool_names={"noite_status"},
        )


_TEST_PNG_DATA_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j0XcAAAAASUVORK5CYII="
)


def test_openwebui_image_messages_convert_inline_image_to_ollama_format() -> None:
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "O que aparece nesta imagem?"},
                {"type": "image_url", "image_url": {"url": _TEST_PNG_DATA_URL}},
            ],
        }
    ]

    result = _openwebui_image_messages(messages)

    assert result is not None
    assert "Analise as imagens fornecidas" in result[0]["content"]
    assert result[1]["content"] == "O que aparece nesta imagem?"
    assert result[1]["images"] == [_TEST_PNG_DATA_URL.split(",", 1)[1]]
    assert _last_user_text(messages) == "O que aparece nesta imagem?"


def test_openwebui_image_messages_support_image_only_user_turn() -> None:
    messages = [
        {
            "role": "user",
            "content": [{"type": "input_image", "image_url": _TEST_PNG_DATA_URL}],
        }
    ]
    assert _last_user_text(messages) == "Analise a imagem enviada."
    result = _openwebui_image_messages(messages)
    assert result is not None
    assert result[-1]["content"] == "Analise a imagem enviada."
    assert result[-1]["images"] == [_TEST_PNG_DATA_URL.split(",", 1)[1]]


@pytest.mark.parametrize(
    "image_url",
    [
        "https://example.invalid/image.png",
        "data:image/gif;base64,AAAA",
        "data:image/png;base64,not-base64!",
    ],
)
def test_openwebui_image_messages_reject_external_or_invalid_images(image_url: str) -> None:
    with pytest.raises(Exception):
        _openwebui_image_messages(
            [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": image_url}}]}]
        )


def test_openwebui_image_messages_enforces_image_count_limit() -> None:
    content = [{"type": "image_url", "image_url": {"url": _TEST_PNG_DATA_URL}} for _ in range(5)]
    with pytest.raises(Exception):
        _openwebui_image_messages([{"role": "user", "content": content}])


@pytest.mark.parametrize("stream", [False, True])
def test_chat_completions_routes_inline_images_to_vision_model(monkeypatch, stream: bool) -> None:
    from starlette.requests import Request

    import noite.model_gateway

    monkeypatch.setattr("noite_api.API_KEY", "test-openwebui-key")
    captured = {}

    async def fake_vision_completion(*, messages):
        captured["messages"] = messages
        return "Uma imagem de teste."

    monkeypatch.setattr(
        noite.model_gateway,
        "ask_local_vision_model",
        fake_vision_completion,
    )
    body = {
        "model": "noite-2.0",
        "stream": stream,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Descreva."},
                    {"type": "image_url", "image_url": {"url": _TEST_PNG_DATA_URL}},
                ],
            }
        ],
    }
    request = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/v1/chat/completions",
            "raw_path": b"/v1/chat/completions",
            "query_string": b"",
            "headers": [],
            "server": ("127.0.0.1", 8765),
            "client": ("127.0.0.1", 12345),
        }
    )

    async def invoke():
        response = await chat_completions(
            body,
            request,
            authorization="Bearer test-openwebui-key",
            x_openwebui_chat_id="chat-image-test",
        )
        if stream:
            chunks = [chunk async for chunk in response.body_iterator]
            return (
                "".join(chunks)
                if chunks and isinstance(chunks[0], str)
                else b"".join(chunks).decode()
            )
        return response.body.decode("utf-8")

    response_body = asyncio.run(invoke())
    assert captured["messages"][-1]["images"] == [_TEST_PNG_DATA_URL.split(",", 1)[1]]
    if stream:
        assert '"content": "Uma imagem de teste."' in response_body
        assert response_body.endswith("data: [DONE]\n\n")
    else:
        import json

        payload = json.loads(response_body)
        assert payload["choices"][0]["message"]["content"] == "Uma imagem de teste."


def test_openwebui_reference_context_is_bounded_and_marked_untrusted() -> None:
    messages = [
        {"role": "system", "content": "Trecho recuperado: manual de configuração."},
        {"role": "developer", "content": "Conteúdo extraído do documento."},
        {"role": "user", "content": "Resuma o arquivo."},
    ]
    context = _openwebui_reference_context(messages, max_chars=80)
    assert "UNTRUSTED REFERENCE CONTEXT" in context
    assert "manual de configuração" in context
    assert len(context.split("material:\n", 1)[-1]) <= 80


def test_chat_completions_preserves_openwebui_rag_context_as_untrusted(monkeypatch) -> None:
    import json

    import noite_api
    from starlette.requests import Request

    monkeypatch.setattr("noite_api.API_KEY", "test-openwebui-key")
    captured = {}

    async def fake_process_request(text, **kwargs):
        captured["text"] = text
        return "Contexto recebido."

    monkeypatch.setattr(noite_api.orchestrator, "process_request", fake_process_request)
    body = {
        "model": "noite-2.0",
        "stream": False,
        "messages": [
            {"role": "system", "content": "Trecho do documento: a senha de teste é falsa."},
            {"role": "user", "content": "Resuma o documento."},
        ],
    }
    request = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/v1/chat/completions",
            "raw_path": b"/v1/chat/completions",
            "query_string": b"",
            "headers": [],
            "server": ("127.0.0.1", 8765),
            "client": ("127.0.0.1", 12345),
        }
    )
    response = asyncio.run(
        chat_completions(
            body,
            request,
            authorization="Bearer test-openwebui-key",
            x_openwebui_chat_id="chat-rag-test",
        )
    )
    payload = json.loads(response.body)

    assert payload["choices"][0]["message"]["content"] == "Contexto recebido."
    assert "UNTRUSTED REFERENCE CONTEXT" in captured["text"]
    assert "Trecho do documento" in captured["text"]


@pytest.mark.parametrize(
    "tool_choice",
    [
        "required",
        {"type": "function", "function": {"name": "noite_status"}},
    ],
)
def test_chat_completions_rejects_missing_required_tool_call(monkeypatch, tool_choice) -> None:
    from fastapi import HTTPException
    from starlette.requests import Request

    import noite.model_gateway

    monkeypatch.setattr("noite_api.API_KEY", "test-openwebui-key")

    async def fake_tool_completion(*, messages, tools, tool_choice):
        return {"role": "assistant", "content": "Não vou chamar a ferramenta."}

    monkeypatch.setattr(
        noite.model_gateway,
        "ask_local_model_with_tools",
        fake_tool_completion,
    )
    body = {
        "model": "noite-2.0",
        "stream": False,
        "messages": [{"role": "user", "content": "Consulte o status."}],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "noite_status",
                    "description": "Status local",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ],
        "tool_choice": tool_choice,
    }
    request = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/v1/chat/completions",
            "raw_path": b"/v1/chat/completions",
            "query_string": b"",
            "headers": [],
            "server": ("127.0.0.1", 8765),
            "client": ("127.0.0.1", 12345),
        }
    )

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            chat_completions(
                body,
                request,
                authorization="Bearer test-openwebui-key",
                x_openwebui_chat_id="chat-required-tool-test",
            )
        )

    assert error.value.status_code == 502
    assert "chamada de ferramenta obrigatória" in error.value.detail
