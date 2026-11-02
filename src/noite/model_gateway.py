import asyncio
import json
import logging
import random
from collections.abc import Callable, Sequence
from time import perf_counter
from uuid import uuid4

import httpx
from litellm import acompletion, completion_cost
from litellm.exceptions import APIConnectionError, OpenAIError, Timeout

from .config import get_settings
from .task_router import route_model
from .workspace import _redact_secret_values

logger = logging.getLogger("noite.model_gateway")
MAX_THINKING_RESPONSE_TOKENS = 2048


class _InvalidModelResponse(Exception):
    pass


async def ask_local_model(
    prompt: str,
    *,
    messages: Sequence[dict[str, str]] | None = None,
    model: str | None = None,
    on_chunk: Callable[[str], None] | None = None,
    on_thinking: Callable[[str], None] | None = None,
) -> str:
    settings = get_settings()
    timeout_seconds = getattr(settings, "model_timeout_seconds", 180)
    selected_model = model or settings.local_model
    if on_thinking is not None and await _model_supports_thinking(
        settings.ollama_base_url, selected_model
    ):
        try:
            return await _ask_ollama_thinking_chat(
                settings.ollama_base_url,
                selected_model,
                list(messages) if messages is not None else [{"role": "user", "content": prompt}],
                timeout_seconds,
                on_chunk,
                on_thinking,
            )
        except httpx.TimeoutException:
            raise RuntimeError(
                f"O modelo local excedeu o tempo limite de {timeout_seconds} segundos."
            ) from None
        except httpx.HTTPError:
            raise RuntimeError("O provedor do modelo local retornou um erro.") from None
    try:
        response = await acompletion(
            model=f"ollama/{selected_model}",
            api_base=settings.ollama_base_url,
            messages=(
                list(messages) if messages is not None else [{"role": "user", "content": prompt}]
            ),
            stream=on_chunk is not None,
            timeout=timeout_seconds,
            num_retries=0,
        )
        if on_chunk is not None:
            parts: list[str] = []
            async for chunk in response:
                choices = getattr(chunk, "choices", ())
                if not choices:
                    continue
                delta = getattr(choices[0], "delta", None)
                content = getattr(delta, "content", None)
                if isinstance(content, str) and content:
                    parts.append(content)
                    on_chunk(content)
            return "".join(parts)
    except Timeout:
        raise RuntimeError(
            f"O modelo local excedeu o tempo limite de {timeout_seconds} segundos."
        ) from None
    except APIConnectionError:
        raise RuntimeError("Não foi possível conectar ao Ollama local.") from None
    except OpenAIError:
        raise RuntimeError("O provedor do modelo local retornou um erro.") from None
    content = response.choices[0].message.content
    return content if isinstance(content, str) else ""


async def _model_supports_thinking(base_url: str, model: str) -> bool:
    """Use Ollama's advertised metadata; do not guess based on the model name."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/api/show", json={"model": model}
            )
            response.raise_for_status()
        values = response.json().get("thinking", {}).get("values", ())
    except (httpx.HTTPError, ValueError, AttributeError, TypeError):
        return False
    if not isinstance(values, (list, tuple)):
        return False
    return any(value is True or isinstance(value, str) for value in values)


async def _ask_ollama_thinking_chat(
    base_url: str,
    model: str,
    messages: list[dict[str, str]],
    timeout: float,
    on_chunk: Callable[[str], None] | None,
    on_thinking: Callable[[str], None] | None,
) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "think": True,
        "stream": on_chunk is not None,
        "options": {"num_predict": MAX_THINKING_RESPONSE_TOKENS},
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        if on_chunk is None:
            response = await client.post(f"{base_url.rstrip('/')}/api/chat", json=payload)
            response.raise_for_status()
            message = response.json().get("message", {})
            thinking = message.get("thinking")
            if on_thinking is not None and isinstance(thinking, str) and thinking:
                on_thinking(thinking)
            content = message.get("content")
            return content if isinstance(content, str) else ""

        parts: list[str] = []
        async with client.stream(
            "POST", f"{base_url.rstrip('/')}/api/chat", json=payload
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                message = json.loads(line).get("message", {})
                thinking = message.get("thinking")
                content = message.get("content")
                if isinstance(thinking, str) and thinking and on_thinking is not None:
                    on_thinking(thinking)
                if isinstance(content, str) and content:
                    parts.append(content)
                    on_chunk(content)
        return "".join(parts)


async def ask_glm_model(
    prompt: str,
    *,
    category: str,
    on_chunk: Callable[[str], None] | None = None,
) -> str:
    """Call the opted-in Z.ai route and log usage metadata without message content."""
    settings = get_settings()
    api_key = (settings.glm_api_key or "").strip()
    selected_route = route_model(prompt, settings)
    if selected_route.provider != "glm" or selected_route.category.value != category:
        raise RuntimeError("A chamada GLM não está autorizada pela configuração local.")

    safe_prompt = _redact_secret_values(prompt)
    messages = [
        {
            "role": "system",
            "content": (
                "Você é um assistente auxiliar para tarefas pontuais. Responda somente ao pedido "
                "atual do usuário. Não presuma acesso ao histórico, arquivos ou ferramentas."
            ),
        },
        {"role": "user", "content": safe_prompt},
    ]

    trace_id = uuid4().hex
    started = perf_counter()
    response = None
    attempts = 0

    async def complete_request() -> str:
        nonlocal response, attempts
        for attempt in range(settings.glm_max_retries + 1):
            attempts = attempt
            try:
                response = await acompletion(
                    model=settings.glm_model,
                    api_base=settings.glm_api_base,
                    api_key=api_key,
                    messages=messages,
                    stream=on_chunk is not None,
                    timeout=settings.glm_timeout_seconds,
                    num_retries=0,
                )
                break
            except (Timeout, APIConnectionError):
                if attempt >= settings.glm_max_retries:
                    raise
                await asyncio.sleep(random.uniform(0.1, 0.3) * (2**attempt))
            except OpenAIError as exc:
                status_code = getattr(exc, "status_code", None)
                is_transient = "ratelimit" in type(exc).__name__.casefold() or (
                    isinstance(status_code, int) and 500 <= status_code <= 599
                )
                if not is_transient:
                    raise
                if attempt >= settings.glm_max_retries:
                    raise
                await asyncio.sleep(random.uniform(0.1, 0.3) * (2**attempt))
        if on_chunk is not None:
            parts: list[str] = []
            async for chunk in response:
                choices = getattr(chunk, "choices", ())
                if not choices:
                    continue
                delta = getattr(choices[0], "delta", None)
                content = getattr(delta, "content", None)
                if isinstance(content, str) and content:
                    parts.append(content)
                    on_chunk(content)
                if getattr(chunk, "usage", None) is not None:
                    response = chunk
            answer = "".join(parts)
        else:
            content = response.choices[0].message.content
            answer = content if isinstance(content, str) else ""
        return answer

    try:
        answer = await asyncio.wait_for(complete_request(), timeout=settings.glm_timeout_seconds)
        if not answer.strip():
            raise _InvalidModelResponse
        _log_model_usage(
            trace_id, "zai", settings.glm_model, category, started, response, retries=attempts
        )
        return answer
    except (Timeout, TimeoutError):
        _log_model_usage(
            trace_id, "zai", settings.glm_model, category, started, response, "timeout", attempts
        )
        raise RuntimeError("O provedor GLM excedeu o tempo limite configurado.") from None
    except _InvalidModelResponse:
        _log_model_usage(
            trace_id,
            "zai",
            settings.glm_model,
            category,
            started,
            response,
            "invalid_response",
            attempts,
        )
        raise RuntimeError("O provedor GLM retornou uma resposta vazia.") from None
    except APIConnectionError:
        _log_model_usage(
            trace_id,
            "zai",
            settings.glm_model,
            category,
            started,
            response,
            "unavailable",
            attempts,
        )
        raise RuntimeError("Não foi possível conectar ao provedor GLM.") from None
    except OpenAIError:
        _log_model_usage(
            trace_id,
            "zai",
            settings.glm_model,
            category,
            started,
            response,
            "provider_error",
            attempts,
        )
        raise RuntimeError("O provedor GLM retornou um erro.") from None
    except Exception:
        _log_model_usage(
            trace_id, "zai", settings.glm_model, category, started, response, "error", attempts
        )
        raise RuntimeError("Falha não classificada no provedor GLM.") from None


def _log_model_usage(
    trace_id: str,
    provider: str,
    model: str,
    category: str,
    started: float,
    response,
    status: str = "ok",
    retries: int = 0,
) -> None:
    usage = getattr(response, "usage", None)
    input_tokens = getattr(usage, "prompt_tokens", None)
    output_tokens = getattr(usage, "completion_tokens", None)
    cached_tokens = getattr(getattr(usage, "prompt_tokens_details", None), "cached_tokens", None)
    try:
        cost = completion_cost(completion_response=response) if response is not None else None
    except Exception:
        cost = None
    logger.info(
        "model_call trace_id=%s provider=%s model=%s category=%s status=%s "
        "latency_ms=%d input_tokens=%s output_tokens=%s cached_tokens=%s retries=%d cost_usd=%s",
        trace_id,
        provider,
        model,
        category,
        status,
        round((perf_counter() - started) * 1000),
        input_tokens if input_tokens is not None else "unavailable",
        output_tokens if output_tokens is not None else "unavailable",
        cached_tokens if cached_tokens is not None else "unavailable",
        retries,
        f"{cost:.8f}" if isinstance(cost, (int, float)) else "unavailable",
    )
