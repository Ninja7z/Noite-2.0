from __future__ import annotations

import asyncio

from noite import assistant as assistant_module
from noite.activity import ActivityEvent
from noite.assistant import AssistantService
from noite.config import Settings


def test_assistant_reports_real_model_lifecycle_without_prompt_content(tmp_path, monkeypatch):
    service = AssistantService(Settings(_env_file=None, data_dir=tmp_path))
    captured = {}

    async def fake_model(prompt, *, messages=None, model=None):
        captured["prompt"] = prompt
        return "Resposta local"

    monkeypatch.setattr(assistant_module, "ask_local_model", fake_model)
    events: list[ActivityEvent] = []
    prompt = "explique como funciona o padrão MVC"

    answer = asyncio.run(service.respond(prompt, on_activity=events.append))

    assert answer == "Resposta local"
    assert captured["prompt"] == prompt
    assert [event.state for event in events] == ["started", "completed"]
    assert events[0].operation == "Chamada ao modelo · Ollama local"
    assert events[1].duration_ms is not None
    assert prompt not in " ".join(event.details for event in events)
