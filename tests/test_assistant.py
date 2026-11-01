import asyncio

from noite.assistant import AssistantService
from noite.config import Settings
from noite.store import open_database, recent_messages


def test_quick_responses_are_deterministic_and_saved(tmp_path) -> None:
    assistant = AssistantService(Settings(_env_file=None, data_dir=tmp_path))

    assert asyncio.run(assistant.respond("oi")) == "Oi! Como posso ajudar?"
    with open_database(tmp_path / "noite.sqlite3") as connection:
        assert recent_messages(connection) == [
            ("user", "oi"),
            ("assistant", "Oi! Como posso ajudar?"),
        ]


def test_action_routing_does_not_execute_tools(tmp_path) -> None:
    assistant = AssistantService(Settings(_env_file=None, data_dir=tmp_path))

    result = asyncio.run(assistant.respond("abrir calculadora"))

    assert "não há uma ferramenta" in result


def test_chat_uses_mocked_local_model_and_history(tmp_path, monkeypatch) -> None:
    from noite import assistant as assistant_module

    settings = Settings(_env_file=None, data_dir=tmp_path)
    assistant = AssistantService(settings)
    captured = {}

    async def fake_model(prompt, *, messages=None, model=None):
        captured["prompt"] = prompt
        captured["messages"] = messages
        captured["model"] = model
        return "resposta simulada"

    monkeypatch.setattr(assistant_module, "ask_local_model", fake_model)
    assert asyncio.run(assistant.respond("explique gravidade")) == "resposta simulada"
    assert captured["messages"][-1] == {"role": "user", "content": "explique gravidade"}
    assert captured["model"] == settings.local_model
