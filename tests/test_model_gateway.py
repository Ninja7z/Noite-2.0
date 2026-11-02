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


def test_glm_uses_litellm_and_logs_usage_without_content(monkeypatch, caplog) -> None:
    from noite.config import Settings

    captured = {}

    async def fake_completion(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="resposta GLM"))],
            usage=SimpleNamespace(prompt_tokens=12, completion_tokens=4),
        )

    settings = Settings(
        _env_file=None,
        off_grid=False,
        glm_enabled=True,
        glm_api_key="synthetic-key-for-test",
        glm_task_categories="summarization",
    )
    caplog.set_level("INFO", logger="noite.model_gateway")
    monkeypatch.setattr(model_gateway, "get_settings", lambda: settings)
    monkeypatch.setattr(model_gateway, "acompletion", fake_completion)
    monkeypatch.setattr(model_gateway, "completion_cost", lambda **kwargs: 0.00001)

    result = _run(model_gateway.ask_glm_model("Resuma um texto público", category="summarization"))

    assert result == "resposta GLM"
    assert captured["model"] == "zai/glm-5.3-flash"
    assert captured["api_base"] == "https://api.z.ai/api/paas/v4"
    assert captured["api_key"] == "synthetic-key-for-test"
    assert captured["num_retries"] == 0
    assert captured["messages"][0]["role"] == "system"
    assert captured["messages"][1] == {"role": "user", "content": "Resuma um texto público"}
    assert "Resuma um texto público" not in caplog.text
    assert "input_tokens=12" in caplog.text
    assert "cost_usd=0.00001000" in caplog.text


def test_glm_coding_plan_uses_its_dedicated_endpoint(monkeypatch) -> None:
    from noite.config import Settings

    captured = {}

    async def fake_completion(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="resposta"))]
        )

    settings = Settings(
        _env_file=None,
        off_grid=False,
        glm_enabled=True,
        glm_api_mode="coding_plan",
        glm_api_key="synthetic-key-for-test",
        glm_task_categories="classification",
    )
    monkeypatch.setattr(model_gateway, "get_settings", lambda: settings)
    monkeypatch.setattr(model_gateway, "acompletion", fake_completion)

    _run(model_gateway.ask_glm_model("Classifique este valor", category="classification"))

    assert captured["api_base"] == "https://api.z.ai/api/coding/paas/v4"


def test_glm_fails_closed_without_an_api_key(monkeypatch) -> None:
    from noite.config import Settings

    monkeypatch.delenv("ZAI_API_KEY", raising=False)
    monkeypatch.setattr(
        model_gateway,
        "get_settings",
        lambda: Settings(
            _env_file=None,
            off_grid=False,
            glm_enabled=True,
            glm_api_key="",
            glm_task_categories="classification",
        ),
    )

    async def unexpected_completion(**kwargs):
        raise AssertionError("No request should be sent without a key")

    monkeypatch.setattr(model_gateway, "acompletion", unexpected_completion)
    with pytest.raises(RuntimeError, match="autorizada"):
        _run(model_gateway.ask_glm_model("Classifique este valor", category="classification"))


def test_glm_retries_transient_timeout_once_with_bounded_attempts(monkeypatch) -> None:
    from noite.config import Settings

    timeout_type = type("Timeout", (Exception,), {})
    monkeypatch.setattr(model_gateway, "Timeout", timeout_type)
    monkeypatch.setattr(
        model_gateway,
        "get_settings",
        lambda: Settings(
            _env_file=None,
            off_grid=False,
            glm_enabled=True,
            glm_api_key="synthetic-key-for-test",
            glm_max_retries=1,
            glm_task_categories="classification",
        ),
    )
    monkeypatch.setattr(model_gateway.asyncio, "sleep", lambda _seconds: _immediate_sleep())
    calls = 0

    async def fake_completion(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise timeout_type("transient")
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="resposta"))]
        )

    async def _immediate_sleep():
        return None

    monkeypatch.setattr(model_gateway, "acompletion", fake_completion)
    result = _run(model_gateway.ask_glm_model("Classifique este valor", category="classification"))

    assert result == "resposta"
    assert calls == 2


def test_glm_gateway_enforces_category_allowlist_and_sensitive_data(monkeypatch) -> None:
    from noite.config import Settings

    settings = Settings(
        _env_file=None,
        off_grid=False,
        glm_enabled=True,
        glm_api_key="synthetic-key-for-test",
        glm_task_categories="summarization",
    )
    monkeypatch.setattr(model_gateway, "get_settings", lambda: settings)

    async def unexpected_completion(**kwargs):
        raise AssertionError("Unauthorized requests must be rejected before LiteLLM")

    monkeypatch.setattr(model_gateway, "acompletion", unexpected_completion)
    with pytest.raises(RuntimeError, match="autorizada"):
        _run(model_gateway.ask_glm_model("Classifique um texto", category="classification"))
    with pytest.raises(RuntimeError, match="autorizada"):
        _run(
            model_gateway.ask_glm_model(
                "Resuma o contato alice@example.com", category="summarization"
            )
        )


@pytest.mark.parametrize(
    ("status_code", "expected_attempts"),
    [(401, 1), (403, 1), (429, 2), (503, 2)],
)
def test_glm_http_errors_are_sanitized_and_retries_are_bounded(
    monkeypatch, status_code, expected_attempts
):
    from noite.config import Settings

    provider_error = type("OpenAIError", (Exception,), {})
    error_name = "RateLimitError" if status_code == 429 else "ProviderResponseError"
    http_error = type(error_name, (provider_error,), {})
    monkeypatch.setattr(model_gateway, "OpenAIError", provider_error)
    monkeypatch.setattr(
        model_gateway,
        "get_settings",
        lambda: Settings(
            _env_file=None,
            off_grid=False,
            glm_enabled=True,
            glm_api_key="synthetic-key-for-test",
            glm_task_categories="summarization",
            glm_max_retries=1,
        ),
    )
    monkeypatch.setattr(model_gateway.asyncio, "sleep", lambda _seconds: _immediate_sleep())
    calls = 0

    async def _immediate_sleep():
        return None

    async def failing_completion(**kwargs):
        nonlocal calls
        calls += 1
        error = http_error("provider included synthetic-private-content")
        error.status_code = status_code
        raise error

    monkeypatch.setattr(model_gateway, "acompletion", failing_completion)
    with pytest.raises(RuntimeError, match="provedor GLM retornou um erro") as error:
        _run(model_gateway.ask_glm_model("Resuma um texto público", category="summarization"))

    assert calls == expected_attempts
    assert "synthetic-private-content" not in str(error.value)


def test_glm_timeout_bounds_all_attempts(monkeypatch) -> None:
    from noite.config import Settings

    monkeypatch.setattr(
        model_gateway,
        "get_settings",
        lambda: Settings(
            _env_file=None,
            off_grid=False,
            glm_enabled=True,
            glm_api_key="synthetic-key-for-test",
            glm_task_categories="classification",
            glm_timeout_seconds=1,
            glm_max_retries=2,
        ),
    )
    calls = 0

    async def never_finishes(**kwargs):
        nonlocal calls
        calls += 1
        await asyncio.Future()

    monkeypatch.setattr(model_gateway, "acompletion", never_finishes)
    with pytest.raises(RuntimeError, match="excedeu o tempo limite"):
        _run(model_gateway.ask_glm_model("Classifique esta frase", category="classification"))
    assert calls == 1


@pytest.mark.parametrize(
    ("response", "error_message"),
    [
        (SimpleNamespace(choices=[]), "Falha não classificada"),
        (
            SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=""))]),
            "resposta vazia",
        ),
    ],
)
def test_glm_rejects_malformed_and_empty_responses(monkeypatch, response, error_message):
    from noite.config import Settings

    monkeypatch.setattr(
        model_gateway,
        "get_settings",
        lambda: Settings(
            _env_file=None,
            off_grid=False,
            glm_enabled=True,
            glm_api_key="synthetic-key-for-test",
            glm_task_categories="summarization",
        ),
    )

    async def malformed_completion(**kwargs):
        return response

    monkeypatch.setattr(model_gateway, "acompletion", malformed_completion)
    with pytest.raises(RuntimeError, match=error_message) as error:
        _run(model_gateway.ask_glm_model("Resuma um texto público", category="summarization"))

    assert "prompt" not in str(error.value).casefold()
