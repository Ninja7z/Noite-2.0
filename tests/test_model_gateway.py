import asyncio
from types import SimpleNamespace

import pytest

from noite import model_gateway


def _run(coroutine):
    return asyncio.run(coroutine)


def test_ask_local_model_returns_content(monkeypatch) -> None:
    async def fake_completion(**kwargs):
        assert kwargs["timeout"] == 180
        assert kwargs["num_retries"] == 0
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="resposta local"))]
        )

    monkeypatch.setattr(model_gateway, "acompletion", fake_completion)
    monkeypatch.setattr(
        model_gateway,
        "get_settings",
        lambda: SimpleNamespace(local_model="test-model", ollama_base_url="http://localhost"),
    )

    assert _run(model_gateway.ask_local_model("oi")) == "resposta local"


@pytest.mark.parametrize(
    ("exception_name", "message"),
    [
        ("Timeout", "O modelo local excedeu o tempo limite de 180 segundos."),
        ("APIConnectionError", "Não foi possível conectar ao Ollama local."),
        ("OpenAIError", "O provedor do modelo local retornou um erro."),
    ],
)
def test_provider_errors_are_sanitized(monkeypatch, exception_name, message) -> None:
    exception_type = type(exception_name, (Exception,), {})

    async def failing_completion(**kwargs):
        raise exception_type("sensitive credential detail")

    monkeypatch.setattr(model_gateway, exception_name, exception_type)
    monkeypatch.setattr(model_gateway, "acompletion", failing_completion)
    monkeypatch.setattr(
        model_gateway,
        "get_settings",
        lambda: SimpleNamespace(local_model="test-model", ollama_base_url="http://localhost"),
    )

    with pytest.raises(RuntimeError, match=message) as error:
        _run(model_gateway.ask_local_model("oi"))
    assert "sensitive credential detail" not in str(error.value)
    assert error.value.__cause__ is None


def test_unexpected_errors_are_not_silenced(monkeypatch) -> None:
    async def failing_completion(**kwargs):
        raise ValueError("unexpected")

    monkeypatch.setattr(model_gateway, "acompletion", failing_completion)
    monkeypatch.setattr(
        model_gateway,
        "get_settings",
        lambda: SimpleNamespace(local_model="test-model", ollama_base_url="http://localhost"),
    )

    with pytest.raises(ValueError, match="unexpected"):
        _run(model_gateway.ask_local_model("oi"))


def test_streaming_yields_each_text_delta(monkeypatch) -> None:
    chunks = [
        SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Olá"))]),
        SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=" mundo"))]),
    ]

    class FakeStream:
        def __aiter__(self):
            async def items():
                for chunk in chunks:
                    yield chunk

            return items()

    async def fake_completion(**kwargs):
        assert kwargs["stream"] is True
        return FakeStream()

    monkeypatch.setattr(model_gateway, "acompletion", fake_completion)
    monkeypatch.setattr(
        model_gateway,
        "get_settings",
        lambda: SimpleNamespace(local_model="test-model", ollama_base_url="http://localhost"),
    )
    received = []

    result = _run(model_gateway.ask_local_model("oi", on_chunk=received.append))

    assert result == "Olá mundo"
    assert received == ["Olá", " mundo"]
