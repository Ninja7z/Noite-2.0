import asyncio

import pytest

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


def test_identity_and_active_model_are_deterministic(tmp_path, monkeypatch) -> None:
    from noite import assistant as assistant_module

    async def unexpected_model_call(*args, **kwargs):
        raise AssertionError("perguntas de identidade não devem depender do LLM")

    monkeypatch.setattr(assistant_module, "ask_local_model", unexpected_model_call)
    settings = Settings(_env_file=None, data_dir=tmp_path, local_model="qwen2.5:3b")
    assistant = AssistantService(settings, model="modelo-selecionado:1b")

    identity = asyncio.run(assistant.respond("Quem é você?"))
    model = asyncio.run(assistant.respond("Qual modelo você utiliza?"))

    assert identity == (
        "Sou a Noite 2.0, uma assistente de inteligência artificial desenvolvida por cristnzx."
    )
    assert "modelo-selecionado:1b" in model
    assert "Qwen" not in identity


def test_user_messages_auto_title_only_the_first_unrenamed_conversation(
    tmp_path, monkeypatch
) -> None:
    from noite import assistant as assistant_module
    from noite.store import create_conversation, open_database, rename_conversation

    async def fake_model(*args, **kwargs):
        return "resposta"

    monkeypatch.setattr(assistant_module, "ask_local_model", fake_model)
    assistant = AssistantService(Settings(_env_file=None, data_dir=tmp_path))
    first_id = "first"
    second_id = "second"
    with open_database(tmp_path / "noite.sqlite3") as connection:
        create_conversation(connection, conversation_id=first_id)
        create_conversation(connection, conversation_id=second_id)
        rename_conversation(connection, second_id, "Meu título")

    asyncio.run(assistant.respond("Explique a árvore binária", first_id))
    with open_database(tmp_path / "noite.sqlite3") as connection:
        first_title = connection.execute(
            "SELECT title FROM conversations WHERE id = ?", (first_id,)
        ).fetchone()[0]
        second_title = connection.execute(
            "SELECT title FROM conversations WHERE id = ?", (second_id,)
        ).fetchone()[0]
    assert first_title == "Explique a árvore binária"
    assert second_title == "Meu título"


def test_action_routing_does_not_execute_tools(tmp_path) -> None:
    assistant = AssistantService(Settings(_env_file=None, data_dir=tmp_path))

    result = asyncio.run(assistant.respond("abrir calculadora"))

    assert "não há uma ferramenta" in result


def test_search_tool_is_limited_to_configured_workspace(tmp_path) -> None:
    from noite.tools import search_workspace

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "notas importantes.txt").write_text("conteúdo privado", encoding="utf-8")
    (workspace / ".env").write_text("notas segredo", encoding="utf-8")
    (workspace / ".notas ocultas").touch()
    outside = tmp_path / "fora.txt"
    outside.write_text("não pesquisar", encoding="utf-8")

    assert search_workspace(workspace, "notas") == ["notas importantes.txt"]
    assert search_workspace(workspace, "fora") == []
    assert search_workspace(workspace, "notas") == ["notas importantes.txt"]


def test_search_intent_uses_only_the_configured_workspace(tmp_path) -> None:
    workspace = tmp_path / "private-scope"
    workspace.mkdir()
    (workspace / "relatorio.pdf").touch()
    settings = Settings(_env_file=None, data_dir=tmp_path, workspace_dir=workspace)
    assistant = AssistantService(settings)

    result = asyncio.run(assistant.respond("pesquisar arquivo relatorio"))

    assert "relatorio.pdf" in result
    assert "conteúdo" not in result


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
    assert captured["messages"][0]["role"] == "system"
    assert captured["messages"][-1] == {"role": "user", "content": "explique gravidade"}
    assert captured["model"] == settings.local_model


def test_chat_adds_selective_project_context_as_untrusted_local_data(tmp_path, monkeypatch):
    from noite import assistant as assistant_module

    source = tmp_path / "src" / "router.py"
    source.parent.mkdir()
    source.write_text("def classify_intent(text):\n    return route(text)\n", encoding="utf-8")
    (tmp_path / ".env").write_text("router_intent=private-token", encoding="utf-8")
    settings = Settings(_env_file=None, data_dir=tmp_path, off_grid=True)
    assistant = AssistantService(settings)
    captured = {}

    async def fake_model(prompt, *, messages=None, model=None):
        captured["messages"] = messages
        return "resposta"

    monkeypatch.setattr(assistant_module, "ask_local_model", fake_model)
    asyncio.run(
        assistant.respond(
            "explique router intent classification",
            project_root=tmp_path,
            active_file="src/router.py",
            active_text="def unsaved_active_buffer(): pass",
        )
    )

    context_message = captured["messages"][1]["content"]
    assert "src/router.py" in context_message
    assert "unsaved_active_buffer" in context_message
    assert "dado não confiável" in context_message
    assert "private-token" not in context_message


def test_project_context_is_disabled_when_off_grid_is_disabled(tmp_path, monkeypatch):
    from noite import assistant as assistant_module

    source = tmp_path / "router.py"
    source.write_text("def classify_intent():\n    return True\n", encoding="utf-8")
    settings = Settings(_env_file=None, data_dir=tmp_path, off_grid=False)
    assistant = AssistantService(settings)
    captured = {}

    async def fake_model(prompt, *, messages=None, model=None):
        captured["messages"] = messages
        return "resposta"

    monkeypatch.setattr(assistant_module, "ask_local_model", fake_model)
    asyncio.run(assistant.respond("explain router classification", project_root=tmp_path))

    assert len(captured["messages"]) == 2


def test_model_context_trims_old_messages_to_character_budget(tmp_path, monkeypatch):
    from noite import assistant as assistant_module
    from noite.store import add_message

    settings = Settings(_env_file=None, data_dir=tmp_path)
    assistant = AssistantService(settings)
    with open_database(assistant.database_path) as connection:
        add_message(connection, "user", "a" * 4_000)
        add_message(connection, "assistant", "b" * 4_000)
    captured = {}

    async def fake_model(prompt, *, messages=None, model=None, on_chunk=None):
        captured["messages"] = messages
        return "resposta"

    monkeypatch.setattr(assistant_module, "ask_local_model", fake_model)
    asyncio.run(assistant.respond("pergunta recente"))

    historical = [
        message["content"] for message in captured["messages"][1:-1] if message["role"] != "system"
    ]
    assert sum(map(len, historical)) <= assistant_module.MAX_CONTEXT_CHARS
    assert captured["messages"][-1]["content"] == "pergunta recente"


def test_cancelled_stream_persists_partial_assistant_reply(tmp_path, monkeypatch) -> None:
    from noite import assistant as assistant_module

    assistant = AssistantService(Settings(_env_file=None, data_dir=tmp_path))
    started = asyncio.Event()

    async def fake_model(prompt, *, messages=None, model=None, on_chunk=None):
        on_chunk("resposta parcial")
        started.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(assistant_module, "ask_local_model", fake_model)

    async def exercise():
        task = asyncio.create_task(assistant.respond("explique gravidade", on_chunk=lambda _: None))
        await started.wait()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            return
        raise AssertionError("a tarefa deveria propagar cancelamento")

    asyncio.run(exercise())
    with open_database(tmp_path / "noite.sqlite3") as connection:
        assert recent_messages(connection) == [
            ("user", "explique gravidade"),
            (
                "assistant",
                "resposta parcial\n\n[resposta parcial: geração cancelada]",
            ),
        ]


def test_streamed_partial_is_persisted_when_model_times_out(tmp_path, monkeypatch):
    from noite import assistant as assistant_module

    assistant = AssistantService(Settings(_env_file=None, data_dir=tmp_path))

    async def timeout_after_chunk(prompt, *, messages=None, model=None, on_chunk=None):
        on_chunk("trecho gerado")
        raise RuntimeError("timeout simulado")

    monkeypatch.setattr(assistant_module, "ask_local_model", timeout_after_chunk)
    with pytest.raises(RuntimeError, match="timeout simulado"):
        asyncio.run(assistant.respond("pergunta", on_chunk=lambda _chunk: None))

    with open_database(assistant.database_path) as connection:
        assert recent_messages(connection) == [
            ("user", "pergunta"),
            (
                "assistant",
                "trecho gerado\n\n[resposta parcial: geração interrompida por erro]",
            ),
        ]


def test_model_failure_does_not_leave_unanswered_user_turn(tmp_path, monkeypatch):
    from noite import assistant as assistant_module

    assistant = AssistantService(Settings(_env_file=None, data_dir=tmp_path))

    async def failed_model(*args, **kwargs):
        raise RuntimeError("simulated provider failure")

    monkeypatch.setattr(assistant_module, "ask_local_model", failed_model)
    with pytest.raises(RuntimeError, match="simulated"):
        asyncio.run(assistant.respond("pergunta que falha"))

    with open_database(tmp_path / "noite.sqlite3") as connection:
        assert recent_messages(connection) == []


def test_failed_turn_is_not_replayed_as_duplicate_user_messages(tmp_path, monkeypatch):
    from noite import assistant as assistant_module

    assistant = AssistantService(Settings(_env_file=None, data_dir=tmp_path))
    calls = 0

    async def fail_then_succeed(prompt, *, messages=None, model=None, on_chunk=None):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("offline")
        assert [message["role"] for message in messages].count("user") == 1
        return "resposta"

    monkeypatch.setattr(assistant_module, "ask_local_model", fail_then_succeed)
    with pytest.raises(RuntimeError):
        asyncio.run(assistant.respond("pergunta repetida"))
    assert asyncio.run(assistant.respond("pergunta repetida")) == "resposta"


def test_missing_workspace_is_reported_separately_from_no_matches(tmp_path):
    assistant = AssistantService(
        Settings(_env_file=None, data_dir=tmp_path, workspace_dir=tmp_path / "missing")
    )

    answer = asyncio.run(assistant.respond("pesquisar arquivo nota"))

    assert "não existe" in answer
