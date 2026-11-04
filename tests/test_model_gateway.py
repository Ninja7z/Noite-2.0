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


def test_native_ollama_thinking_stream_separates_thinking_from_answer(monkeypatch) -> None:
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def aiter_lines(self):
            for line in (
                '{"message":{"thinking":"Vou verificar."}}',
                '{"message":{"content":"Está correto."}}',
            ):
                yield line

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        def stream(self, method, url, *, json):
            captured.update(method=method, url=url, payload=json)
            return FakeResponse()

    async def supports_thinking(_base_url, _model):
        return True

    monkeypatch.setattr(
        model_gateway,
        "httpx",
        SimpleNamespace(
            AsyncClient=FakeClient,
            TimeoutException=Exception,
            HTTPError=Exception,
        ),
    )
    monkeypatch.setattr(model_gateway, "_model_supports_thinking", supports_thinking)
    monkeypatch.setattr(
        model_gateway,
        "get_settings",
        lambda: SimpleNamespace(
            local_model="qwen3:4b",
            ollama_base_url="http://127.0.0.1:11434",
            model_timeout_seconds=30,
        ),
    )
    answer_chunks, thought_chunks = [], []

    answer = _run(
        model_gateway.ask_local_model(
            "Pergunta",
            messages=[{"role": "user", "content": "Pergunta"}],
            on_chunk=answer_chunks.append,
            on_thinking=thought_chunks.append,
        )
    )

    assert captured["url"].endswith("/api/chat")
    assert captured["payload"]["think"] is True
    assert captured["payload"]["options"]["num_predict"] == 2048
    assert answer == "Está correto."
    assert answer_chunks == ["Está correto."]
    assert thought_chunks == ["Vou verificar."]


def test_qwen35_normal_chat_disables_thinking_channel(monkeypatch) -> None:
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"message": {"content": "Resposta visível."}}

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, *, json):
            captured.update(url=url, payload=json)
            return FakeResponse()

    monkeypatch.setattr(
        model_gateway,
        "httpx",
        SimpleNamespace(
            AsyncClient=FakeClient,
            TimeoutException=Exception,
            HTTPError=Exception,
        ),
    )
    monkeypatch.setattr(
        model_gateway,
        "get_settings",
        lambda: SimpleNamespace(
            local_model="qwen3.5:4b",
            ollama_base_url="http://127.0.0.1:11434",
            model_timeout_seconds=30,
        ),
    )

    answer = _run(model_gateway.ask_local_model("Pergunta"))

    assert captured["url"].endswith("/api/chat")
    assert captured["payload"]["think"] is False
    assert answer == "Resposta visível."


@pytest.mark.parametrize(
    ("values", "expected"),
    [([False], False), ([True, False], True), (["low", "high"], True), (None, False)],
)
def test_ollama_thinking_detection_uses_advertised_values(monkeypatch, values, expected):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"thinking": {"values": values}} if values is not None else {}

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **_kwargs):
            return FakeResponse()

    monkeypatch.setattr(
        model_gateway,
        "httpx",
        SimpleNamespace(
            AsyncClient=FakeClient,
            HTTPError=Exception,
        ),
    )

    assert _run(model_gateway._model_supports_thinking("http://ollama", "model")) is expected


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


def test_model_usage_log_never_serializes_response_headers(caplog):
    secret = "synthetic-glm-auth-header-secret"
    response = SimpleNamespace(
        usage=None,
        _hidden_params={"headers": {"Authorization": f"Bearer {secret}"}},
    )

    model_gateway._log_model_usage(
        "trace-test", "zai", "glm-test", "summarization", 0.0, response, "provider_error"
    )

    assert secret not in caplog.text
    assert "Authorization" not in caplog.text


def test_local_model_forwards_openwebui_tools_and_returns_tool_calls(monkeypatch) -> None:
    captured = {}
    expected_calls = [
        {
            "id": "call_123",
            "type": "function",
            "function": {"name": "noite_status", "arguments": "{}"},
        }
    ]

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_123",
                            "function": {
                                "name": "noite_status",
                                "arguments": {},
                            },
                        }
                    ],
                }
            }

    class FakeClient:
        def __init__(self, **kwargs):
            captured["timeout"] = kwargs["timeout"]

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, *, json):
            captured.update(url=url, payload=json)
            return FakeResponse()

    monkeypatch.setattr(
        model_gateway,
        "httpx",
        SimpleNamespace(AsyncClient=FakeClient, TimeoutException=TimeoutError, HTTPError=Exception),
    )
    monkeypatch.setattr(
        model_gateway,
        "get_settings",
        lambda: SimpleNamespace(
            local_model="qwen2.5:3b",
            ollama_base_url="http://127.0.0.1:11434",
            model_timeout_seconds=45,
        ),
    )
    tools = [{"type": "function", "function": {"name": "noite_status", "parameters": {}}}]
    messages = [{"role": "user", "content": "Confira o status."}]

    result = _run(
        model_gateway.ask_local_model_with_tools(
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
    )

    assert captured["url"] == "http://127.0.0.1:11434/api/chat"
    assert captured["timeout"] == 45
    assert captured["payload"]["model"] == "qwen2.5:3b"
    assert captured["payload"]["messages"] == messages
    assert captured["payload"]["tools"] == tools
    assert result["role"] == "assistant"
    assert result["tool_calls"] == expected_calls


def test_local_model_gateway_reconstructs_openai_tool_round_trip(monkeypatch) -> None:
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"message": {"role": "assistant", "content": "Encontrei cinco arquivos."}}

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, _url, *, json):
            captured.update(payload=json)
            return FakeResponse()

    monkeypatch.setattr(
        model_gateway,
        "httpx",
        SimpleNamespace(AsyncClient=FakeClient, TimeoutException=TimeoutError, HTTPError=Exception),
    )
    monkeypatch.setattr(
        model_gateway,
        "get_settings",
        lambda: SimpleNamespace(
            local_model="qwen2.5:3b",
            ollama_base_url="http://127.0.0.1:11434",
            model_timeout_seconds=45,
        ),
    )
    messages = [
        {"role": "user", "content": "Pesquise arquivos."},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_search",
                    "type": "function",
                    "function": {
                        "name": "noite_search_workspace",
                        "arguments": '{"query": "relatorio", "limit": 5}',
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_search",
            "name": "noite_search_workspace",
            "content": "relatorio.txt",
        },
        {"role": "user", "content": "Resuma o retorno."},
    ]

    result = _run(
        model_gateway.ask_local_model_with_tools(
            messages=messages,
            tools=[],
            tool_choice="auto",
        )
    )

    native_messages = captured["payload"]["messages"]
    assert native_messages[1]["tool_calls"][0]["function"]["arguments"] == {
        "query": "relatorio",
        "limit": 5,
    }
    assert native_messages[2]["role"] == "tool"
    assert native_messages[2]["tool_name"] == "noite_search_workspace"
    assert native_messages[2]["content"] == "relatorio.txt"
    assert result["content"] == "Encontrei cinco arquivos."


def test_local_vision_model_uses_installed_qwen_vl(monkeypatch) -> None:
    captured = {}

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class FakeClient:
        def __init__(self, **kwargs):
            captured["timeout"] = kwargs["timeout"]

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, url):
            captured["tags_url"] = url
            return FakeResponse({"models": [{"name": "qwen2.5vl:3b"}]})

        async def post(self, url, *, json):
            captured.update(chat_url=url, payload=json)
            return FakeResponse({"message": {"role": "assistant", "content": "Uma imagem."}})

    monkeypatch.setattr(
        model_gateway,
        "httpx",
        SimpleNamespace(
            AsyncClient=FakeClient,
            TimeoutException=TimeoutError,
            HTTPError=Exception,
        ),
    )
    monkeypatch.setattr(
        model_gateway,
        "get_settings",
        lambda: SimpleNamespace(
            local_model="qwen2.5:3b",
            ollama_base_url="http://127.0.0.1:11434",
            model_timeout_seconds=60,
        ),
    )
    messages = [{"role": "user", "content": "Descreva a imagem.", "images": ["aGVsbG8="]}]

    result = _run(model_gateway.ask_local_vision_model(messages=messages))

    assert result == "Uma imagem."
    assert captured["tags_url"] == "http://127.0.0.1:11434/api/tags"
    assert captured["chat_url"] == "http://127.0.0.1:11434/api/chat"
    assert captured["payload"]["model"] == "qwen2.5vl:3b"
    assert captured["payload"]["messages"] == messages
