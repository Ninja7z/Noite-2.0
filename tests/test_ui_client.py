from __future__ import annotations

import asyncio

from ui.client import MockClient, ServiceClient


def test_mock_client_has_reference_sessions_context_and_tools():
    client = MockClient()

    assert [title for _, title, _ in client.sessoes()] == [
        "Análise de código Python",
        "Planejamento do projeto",
        "Dúvidas sobre IA local",
    ]
    assert client.contexto()["project"] == "Noite-2.0"
    assert client.contexto()["indexed_documents"] == 18
    assert client.ferramentas() == [
        "Calculadora",
        "Pesquisa na Web",
        "Executar Comando",
        "Abrir Arquivo",
    ]


def test_mock_client_streams_only_when_explicitly_selected():
    client = MockClient()
    chunks = []

    response = asyncio.run(client.enviar("Teste", on_chunk=chunks.append))

    assert "Teste" in response
    assert "".join(chunks) == response


def test_service_client_delegates_to_assistant_service(monkeypatch, tmp_path):
    from noite.config import Settings
    from ui import client as client_module

    captured = {}

    class FakeAssistantService:
        def __init__(self, settings, model=None):
            captured["settings"] = settings
            captured["model"] = model

        async def respond(self, text, **kwargs):
            captured["text"] = text
            captured["kwargs"] = kwargs
            return "ok"

    monkeypatch.setattr(client_module, "AssistantService", FakeAssistantService)
    settings = Settings(_env_file=None, data_dir=tmp_path)
    client = ServiceClient(settings, model="qwen2.5:3b")
    streamed = []

    result = asyncio.run(
        client.enviar(
            "pergunta",
            conversation_id="conversation-1",
            on_chunk=streamed.append,
        )
    )

    assert result == "ok"
    assert captured["settings"] is settings
    assert captured["model"] == "qwen2.5:3b"
    assert captured["text"] == "pergunta"
    assert captured["kwargs"]["conversation_id"] == "conversation-1"
