"""Deterministic, privacy-first selection of a model for auxiliary tasks."""

import re
from dataclasses import dataclass
from enum import StrEnum

from .config import Settings
from .workspace import _redact_secret_values


class TaskCategory(StrEnum):
    CONVERSATION = "conversation"
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    STRUCTURED_OUTPUT = "structured_output"
    SUMMARIZATION = "summarization"
    DOCUMENTATION = "documentation"
    TEST_GENERATION = "test_generation"
    CODE_ANALYSIS = "code_analysis"


@dataclass(frozen=True)
class ModelRoute:
    provider: str
    category: TaskCategory
    reason: str


_CATEGORY_PATTERNS = (
    (
        TaskCategory.CLASSIFICATION,
        re.compile(r"\b(classify|classificar|classifique|categorize|categorizar)\b", re.I),
    ),
    (
        TaskCategory.EXTRACTION,
        re.compile(r"\b(extract|extraia|extrair)\b", re.I),
    ),
    (
        TaskCategory.STRUCTURED_OUTPUT,
        re.compile(
            r"\b(estruture|format(?:e|ar) em json|converta para json|serialize|serializar)\b",
            re.I,
        ),
    ),
    (
        TaskCategory.SUMMARIZATION,
        re.compile(r"\b(summarize|summarise|resuma|sintetize)\b", re.I),
    ),
    (
        TaskCategory.DOCUMENTATION,
        re.compile(r"\b(document|documente|write documentation|documente em README)\b", re.I),
    ),
    (
        TaskCategory.TEST_GENERATION,
        re.compile(
            r"\b(generate tests|gerar testes|gere testes|crie testes|testes auxiliares)\b",
            re.I,
        ),
    ),
    (
        TaskCategory.CODE_ANALYSIS,
        re.compile(r"\b(review code|revise o código|analise o código|análise de código)\b", re.I),
    ),
)
_SENSITIVE_DATA = re.compile(
    r"(?i)\b(password|passwd|secret|api[_ -]?key|access[_ -]?token|credential|"
    r"private[_ -]?key|senha|segredo|credencial|cpf|cnpj|ssn|cartão(?: de crédito)?|"
    r"conta bancária|bank account|prontuário|medical|health|patient|paciente|"
    r"saúde|diagnóstico|dados pessoais|personal data|informações pessoais|"
    r"endereço(?: residencial)?|home address|telefone|phone number|e-mail|email|"
    r"data de nascimento|birth date|dados financeiros|financial data|folha salarial|payroll)\b"
)
_EMAIL_ADDRESS = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_BRAZILIAN_ID = re.compile(r"\b\d{3}[. ]?\d{3}[. ]?\d{3}[-. ]?\d{2}\b")
_BRAZILIAN_COMPANY_ID = re.compile(r"\b\d{2}[. ]?\d{3}[. ]?\d{3}/?\d{4}[-. ]?\d{2}\b")
_PHONE_NUMBER = re.compile(r"(?<!\w)\+?\d[\d(). -]{7,}\d(?!\w)")
_TASK_START = re.compile(
    r"(?i)^\s*(?:(?:por favor|please|could you|can you)\s+)?"
    r"(?:classify|classificar|classifique|categorize|categorizar|extract|extraia|extrair|"
    r"estruture|formate em json|formatar em json|converta para json|serialize|serializar|"
    r"summarize|summarise|resuma|sintetize|document|documente|generate tests|gerar testes|"
    r"gere testes|crie testes|review code|revise o código|analise o código|análise de código)\b"
)


def classify_task(text: str) -> TaskCategory:
    matches = matching_task_categories(text)
    return matches[0] if len(matches) == 1 else TaskCategory.CONVERSATION


def matching_task_categories(text: str) -> tuple[TaskCategory, ...]:
    """Return every explicit auxiliary task verb present in the request."""
    if not _TASK_START.search(text):
        return ()
    return tuple(category for category, pattern in _CATEGORY_PATTERNS if pattern.search(text))


def route_model(text: str, settings: Settings, *, api_key: str | None = None) -> ModelRoute:
    categories = matching_task_categories(text)
    category = categories[0] if len(categories) == 1 else TaskCategory.CONVERSATION
    if (
        _SENSITIVE_DATA.search(text)
        or _EMAIL_ADDRESS.search(text)
        or _BRAZILIAN_ID.search(text)
        or _BRAZILIAN_COMPANY_ID.search(text)
        or _PHONE_NUMBER.search(text)
        or _redact_secret_values(text) != text
    ):
        return ModelRoute("local", category, "conteúdo potencialmente sensível")
    if len(categories) > 1:
        return ModelRoute("local", category, "pedido com categorias ambíguas")
    if not settings.glm_enabled:
        return ModelRoute("local", category, "provedor GLM desativado")
    if settings.off_grid:
        return ModelRoute("local", category, "modo offline ativo")
    if settings.glm_model != "zai/glm-5.3-flash":
        return ModelRoute("local", category, "modelo GLM não reconhecido")
    if settings.glm_api_mode not in {"general", "coding_plan"}:
        return ModelRoute("local", category, "modalidade da API GLM inválida")
    if category.value not in settings.enabled_glm_task_categories:
        return ModelRoute("local", category, "categoria não autorizada para nuvem")
    configured_key = api_key if api_key is not None else settings.glm_api_key
    if not (configured_key or "").strip():
        return ModelRoute("local", category, "chave Z.ai ausente")
    return ModelRoute("glm", category, "tarefa auxiliar autorizada")


_HARDWARE_PROFILE = {
    "cpu_cores": 4,
    "system_ram_gb": 16,
    "vram_gb": 6,
    "gpu": "gtx_1660s",
}

# VRAM estimada (GB) para os pesos Q4_K_M de cada faixa de parâmetros (em bilhões).
_MODEL_SIZE_MAP = {
    0.5: 0.3,
    1.5: 1.2,
    2.0: 1.8,
    2.5: 2.0,
    3.0: 2.3,
    3.8: 2.6,
    4.0: 2.8,
    5.0: 3.5,
    6.0: 4.0,
    7.0: 4.7,  # 7B Q4_K_M ~4.7GB de pesos, mais preciso que a média.
    8.0: 5.2,
    9.0: 5.8,
    10.0: 6.5,
    13.0: 8.5,
    14.0: 9.0,
    20.0: 12.5,
    30.0: 18.0,
}
# O sufixo "b" pertence ao número, então precisa ficar fora do lookahead negativo
# final; assim "7b" casa e o "2.5" de "qwen2.5" continua ignorado.
_PARAMETER_COUNT = re.compile(r"(?<![a-z0-9])(\d+(?:\.\d+)?)b(?![a-z0-9])")
# Fallback para tags sem sufixo "b" (ex.: "mistral:7").
_TAGGED_PARAMETER_COUNT = re.compile(r":(\d+(?:\.\d+)?)\b")

# Overhead conservador: pesos + buffers, KV cache inicial e metadados.
_VRAM_OVERHEAD_RATIO = 1.25
_RAM_OVERHEAD_RATIO = 1.3
_COMFORTABLE_FREE_VRAM_PERCENT = 20.0

_RECOMMENDED_MODELS = (
    (
        "gemma:2b",
        "2B Q4_K_M -- cabe nos 6GB de VRAM da GTX 1660S; rapido em CPU+GPU misturada.",
    ),
    (
        "gemma:3b",
        "3B Q4_K_M -- cabe nos 6GB de VRAM; use se precisar de mais capacidade.",
    ),
    (
        "phi3:3.8b",
        "3.8B Q4_K_M -- bom equilibrio velocidade/qualidade; cabe nos 6GB de VRAM.",
    ),
    (
        "llama3.2:3b",
        "3B Q4_K_M -- similar ao phi3; pode ser ligeiramente mais lento.",
    ),
    (
        "mistral:7b",
        "7B Q4_K_M -- cabe na RAM de 16GB; depende da divisao CPU/GPU. Use se necessario.",
    ),
)


def suggest_models_for_hardware(settings) -> list[dict[str, str]]:
    """Retorna modelos recomendados para o hardware atual baseado em RAM/VRAM."""
    recommendations = [
        {"model": model, "provider": "ollama", "reason": reason}
        for model, reason in _RECOMMENDED_MODELS
    ]
    user_model = (settings.local_model or "").strip().casefold()
    if not user_model:
        return recommendations
    for index, rec in enumerate(recommendations):
        if rec["model"].casefold().startswith(user_model):
            return [rec] + recommendations[:index] + recommendations[index + 1 :]
    return recommendations


def _parameter_count_billions(model_id: str) -> float | None:
    """Extrai a quantidade de parâmetros (bilhões) do nome ou da tag do modelo."""
    model = model_id.casefold()
    match = _PARAMETER_COUNT.search(model) or _TAGGED_PARAMETER_COUNT.search(model)
    if match is None:
        return None
    return float(match.group(1))


def _memory_fit(parameter_count: float, vram_gb: int, ram_gb: int) -> tuple[bool, str]:
    """Estima se o modelo cabe em VRAM/RAM e qual a margem livre resultante."""
    estimated_vram = _MODEL_SIZE_MAP.get(parameter_count, parameter_count * 0.65)
    estimated_vram_real = estimated_vram * _VRAM_OVERHEAD_RATIO
    estimated_ram = max(2.0, estimated_vram_real * _RAM_OVERHEAD_RATIO)
    fits_vram = estimated_vram_real <= vram_gb
    fits_ram = estimated_ram <= ram_gb
    if fits_vram and fits_ram:
        free_vram_pct = ((vram_gb - estimated_vram_real) / vram_gb) * 100 if vram_gb else 0.0
        comfortable = free_vram_pct >= _COMFORTABLE_FREE_VRAM_PERCENT
        category = "confortavel" if comfortable else "limitado"
    elif fits_vram or fits_ram:
        # Cabe em um dos recursos, mas nao nos dois com margem.
        category = "limitado"
    else:
        category = "inviavel"
    return fits_vram and fits_ram, category


def is_model_compatible(model_id: str, vram_gb: int, ram_gb: int) -> bool | None:
    """Estima compatibilidade de modelos quantizados com VRAM e RAM disponíveis.

    A estimativa assume quantização próxima de Q4 e não substitui a medição
    do uso real, que também depende da janela de contexto e do offload.

    Returns:
        True se o modelo caber na VRAM e RAM especificados (estimativa).
        False se exceder a memória disponível (estimativa).
        None se não for possível determinar o tamanho do modelo.

    Notas:
        1. "Caber na memória" NÃO equivale a desempenho suave: pesos, buffers,
           KV cache e metadados podem aumentar o consumo em 15-30%.
        2. Ausência de AVX2 limita o processamento na CPU, não o offload para a GPU;
           transferências RAM<->VRAM é que degradam a performance.
        3. Contexto maior aumenta o KV cache e pressiona a VRAM além do esperado.
    """
    parameter_count = _parameter_count_billions(model_id)
    if parameter_count is None:
        # Indeterminado: retorna None para forçar avaliação explícita do chamador.
        return None
    fits, _ = _memory_fit(parameter_count, vram_gb, ram_gb)
    return fits


def get_model_category(model_id: str, vram_gb: int, ram_gb: int) -> tuple[bool | None, str]:
    """Classifica o nível de compatibilidade em categorias detalhadas.

    Returns:
        Tuple de (bool_compatível, categoria_str):
        - bool: True se caber na VRAM e RAM (mesmo algoritmo de is_model_compatible)
        - str: Categoria - "confortavel", "limitado", "inviavel" ou "indeterminado"

    Categories:
        - 🟢 Confortável: margem de memória >= 20% livre após carregado
        - 🟡 Limitado: modelo que cabe, mas com margem < 20% ou offload necessário
        - 🔴 Inviável: modelo excede VRAM/RAM disponíveis ou performance impraticável
    """
    parameter_count = _parameter_count_billions(model_id)
    if parameter_count is None:
        return (None, "indeterminado")
    return _memory_fit(parameter_count, vram_gb, ram_gb)


def get_hardware_profile() -> dict:
    return dict(_HARDWARE_PROFILE)
