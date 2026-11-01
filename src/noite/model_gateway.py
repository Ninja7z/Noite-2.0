from collections.abc import Callable, Sequence

from litellm import acompletion
from litellm.exceptions import APIConnectionError, OpenAIError, Timeout

from .config import get_settings


async def ask_local_model(
    prompt: str,
    *,
    messages: Sequence[dict[str, str]] | None = None,
    model: str | None = None,
    on_chunk: Callable[[str], None] | None = None,
) -> str:
    settings = get_settings()
    timeout_seconds = getattr(settings, "model_timeout_seconds", 180)
    try:
        response = await acompletion(
            model=f"ollama/{model or settings.local_model}",
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
