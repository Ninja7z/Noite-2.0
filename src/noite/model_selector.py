"""Seleção automática e local do modelo mais adequado por tipo de pergunta.

A seleção considera apenas modelos já instalados no Ollama. Não baixa modelos,
não envia prompts para serviços externos e mantém um fallback configurado.
"""
from __future__ import annotations

import re
import time
from collections.abc import Sequence

import httpx

_CACHE_SECONDS = 30.0
_models_cache: dict[str, object] = {"expires": 0.0, "models": ()}

_PATTERNS = {
    "coding": re.compile(
        r"\b(código|codigo|programa|programação|programacao|python|javascript|"
        r"html|css|bug|debug|script|função|funcao|erro no código)\b", re.I
    ),
    "reasoning": re.compile(
        r"\b(raciocine|raciocínio|raciocinio|analise profundamente|passo a passo|"
        r"compare|avalie|estratégia|estrategia|matemática|matematica|lógica|"
        r"logica|por que|explique detalhadamente)\b", re.I
    ),
    "summary": re.compile(r"\b(resuma|resumo|sintetize|resumir|pontos principais)\b", re.I),
    "simple": re.compile(
        r"^\s*(oi|olá|ola|obrigad[oa]|valeu|bom dia|boa tarde|boa noite|tchau)"
        r"(?:[, ]+.*)?[.!? ]*$", re.I
    ),
}

_PREFERENCES = {
    "coding": ("qwen3.5:4b", "qwen2.5:3b"),
    "reasoning": ("deepseek-r1:1.5b", "qwen3.5:4b"),
    "summary": ("qwen3.5:4b", "gemma3:4b", "qwen2.5:3b"),
    "simple": ("qwen2.5:3b", "deepseek-r1:1.5b"),
    "general": ("qwen3.5:4b", "qwen2.5:3b", "gemma3:4b"),
}


def classify_request(prompt: str) -> str:
    """Classifica a intenção principal sem chamar outro modelo."""
    for category in ("coding", "reasoning", "summary", "simple"):
        if _PATTERNS[category].search(prompt):
            return category
    return "general"


def choose_installed_model(
    prompt: str, installed_models: Sequence[str], fallback: str
) -> tuple[str, str]:
    """Escolhe por capacidade conhecida, sempre limitado ao inventário instalado."""
    installed = {name.casefold(): name for name in installed_models if name}
    category = classify_request(prompt)
    for candidate in _PREFERENCES[category]:
        if candidate.casefold() in installed:
            return installed[candidate.casefold()], category
    if fallback.casefold() in installed:
        return installed[fallback.casefold()], category
    # Nunca tenta carregar um modelo inexistente: usa o primeiro do inventário.
    if installed_models:
        return installed_models[0], category
    return fallback, category


async def select_local_model(prompt: str, base_url: str, fallback: str) -> tuple[str, str]:
    """Consulta /api/tags com cache curto e seleciona um modelo já instalado."""
    now = time.monotonic()
    cached_url = _models_cache.get("url")
    if cached_url == base_url and now < float(_models_cache.get("expires", 0.0)):
        installed = _models_cache.get("models", ())
    else:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{base_url.rstrip('/')}/api/tags")
                response.raise_for_status()
            payload = response.json()
            installed = tuple(
                str(item.get("name", "")).strip()
                for item in payload.get("models", [])
                if isinstance(item, dict) and item.get("name")
            )
            _models_cache.update(url=base_url, models=installed, expires=now + _CACHE_SECONDS)
        except (httpx.HTTPError, ValueError, TypeError, AttributeError):
            installed = ()
            _models_cache.update(url=base_url, models=installed, expires=now + 5.0)
    return choose_installed_model(prompt, installed, fallback)
