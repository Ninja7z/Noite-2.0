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
