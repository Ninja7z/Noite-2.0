import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from noite.config import Settings  # noqa: E402
from noite.orchestrator import ChatAgent, Orchestrator  # noqa: E402


class _FakeService:
    model = "qwen2.5:3b"
    settings = Settings(_env_file=None)

    def active_conversation_id(self) -> str:
        return "conv-1"

    async def respond(self, text, conversation_id=None, history_override=None, on_chunk=None):
        answer = f"eco: {text}"
        if on_chunk is not None:
            on_chunk(answer[:4])
            on_chunk(answer[4:])
        return answer


def test_orchestrator_uses_registered_agent(tmp_path):
    service = _FakeService()
    orch = Orchestrator(service)
    events = []
    orch.set_activity_callback(lambda e: events.append(e))

    import asyncio

    answer = asyncio.run(orch.process_request("oi", conversation_id="c1"))
    assert answer == "eco: oi"
    started = [e for e in events if e.state == "started"]
    completed = [e for e in events if e.state == "completed"]
    assert any("orquestrador" in e.operation for e in started)
    assert any("orquestrador" in e.operation for e in completed)


def test_orchestrator_forwards_streamed_chunks_to_chat_service():
    import asyncio

    orch = Orchestrator(_FakeService())
    chunks = []
    answer = asyncio.run(orch.process_request("resposta", on_chunk=chunks.append))

    assert answer == "eco: resposta"
    assert "".join(chunks) == answer
    assert len(chunks) == 2


def test_orchestrator_executes_registered_deterministic_action_before_model():
    import asyncio

    from noite.contracts import IntentKind

    service = _FakeService()
    orch = Orchestrator(service)
    calls = []

    async def show_mascot(intent):
        calls.append(intent.parameters["endpoint"])
        return "Mascote aberto na tela."

    orch.register_action_handler(IntentKind.SHOW_MASCOT, show_mascot)
    answer = asyncio.run(orch.process_request("abrir mascote"))

    assert answer == "Mascote aberto na tela."
    assert calls == ["/v1/mascot/show"]


def test_orchestrator_chat_agent_is_registered(tmp_path):
    service = _FakeService()
    orch = Orchestrator(service)
    assert "chat" in orch.agents
    assert isinstance(orch.agents["chat"], ChatAgent)


def test_orchestrator_plan_records_intent(tmp_path):
    service = _FakeService()
    orch = Orchestrator(service)

    import asyncio

    async def run():
        answer = await orch.process_request("abra o bloco de notas", conversation_id="c1")
        return answer

    answer = asyncio.run(run())
    assert answer.startswith("eco:")


def test_orchestrator_timeout_is_enforced():
    import asyncio

    import pytest

    class SlowService(_FakeService):
        async def respond(self, text, conversation_id=None, history_override=None, on_chunk=None):
            await asyncio.sleep(0.1)
            return "late"

    async def run():
        orch = Orchestrator(SlowService())
        orch.set_timeout(0.01)
        with pytest.raises(TimeoutError):
            await orch.process_request("oi")

    asyncio.run(run())


def test_orchestrator_rejects_non_positive_limits():
    import pytest

    orch = Orchestrator(_FakeService())
    with pytest.raises(ValueError):
        orch.set_max_iterations(0)
    with pytest.raises(ValueError):
        orch.set_timeout(0)


def test_concurrent_requests_keep_activity_callbacks_isolated():
    import asyncio

    service = _FakeService()
    orch = Orchestrator(service)
    first_events = []
    second_events = []

    async def run():
        await asyncio.gather(
            orch.process_request("primeira", on_activity=first_events.append),
            orch.process_request("segunda", on_activity=second_events.append),
        )

    asyncio.run(run())
    assert first_events
    assert second_events
    assert first_events[0].details == "primeira"
    assert second_events[0].details == "segunda"
