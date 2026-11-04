import pytest

from noite.config import Settings
from noite.task_router import (
    TaskCategory,
    classify_task,
    get_model_category,
    is_model_compatible,
    route_model,
)


def test_classify_supported_auxiliary_tasks_deterministically():
    assert classify_task("Resuma este texto") == TaskCategory.SUMMARIZATION
    assert classify_task("Extraia os campos em JSON") == TaskCategory.EXTRACTION
    assert classify_task("Gere testes para este módulo") == TaskCategory.TEST_GENERATION
    assert classify_task("Como está o tempo?") == TaskCategory.CONVERSATION


def test_every_auxiliary_category_has_an_explicit_task_phrase():
    phrases = {
        TaskCategory.CLASSIFICATION: "Classifique este pedido",
        TaskCategory.EXTRACTION: "Extraia os campos deste texto",
        TaskCategory.STRUCTURED_OUTPUT: "Formate em JSON este resultado",
        TaskCategory.SUMMARIZATION: "Resuma este texto",
        TaskCategory.DOCUMENTATION: "Documente este módulo",
        TaskCategory.TEST_GENERATION: "Gere testes para este módulo",
        TaskCategory.CODE_ANALYSIS: "Revise o código deste módulo",
    }
    for category, phrase in phrases.items():
        assert classify_task(phrase) == category


def test_local_is_selected_by_default_even_with_an_api_key():
    settings = Settings(_env_file=None)
    result = route_model("Resuma este texto", settings, api_key="configured")
    assert result.provider == "local"


def test_glm_requires_opt_in_allowed_category_and_key():
    settings = Settings(
        _env_file=None,
        off_grid=False,
        glm_enabled=True,
        glm_task_categories="summarization",
    )
    assert route_model("Resuma este texto", settings, api_key="").provider == "local"
    assert route_model("Converse comigo", settings, api_key="configured").provider == "local"
    assert route_model("Resuma este texto", settings, api_key="configured").provider == "glm"


@pytest.mark.parametrize(
    ("phrase", "category"),
    [
        ("Classifique este pedido", "classification"),
        ("Extraia campos do texto", "extraction"),
        ("Formate em JSON este resultado", "structured_output"),
        ("Resuma este texto", "summarization"),
        ("Documente este módulo", "documentation"),
        ("Gere testes para este módulo", "test_generation"),
        ("Revise o código deste módulo", "code_analysis"),
    ],
)
def test_each_allowlisted_category_selects_glm_and_other_categories_stay_local(phrase, category):
    settings = Settings(
        _env_file=None,
        off_grid=False,
        glm_enabled=True,
        glm_api_key="configured",
        glm_task_categories=category,
    )
    assert route_model(phrase, settings).provider == "glm"
    assert route_model(phrase, settings).category.value == category
    settings.glm_task_categories = ""
    assert route_model(phrase, settings).provider == "local"


def test_invalid_glm_model_or_api_mode_stays_local():
    for values in (
        {"glm_model": "unknown/model"},
        {"glm_api_mode": "unknown"},
    ):
        settings = Settings(
            _env_file=None,
            off_grid=False,
            glm_enabled=True,
            glm_api_key="configured",
            glm_task_categories="summarization",
            **values,
        )
        assert route_model("Resuma este texto", settings).provider == "local"


def test_sensitive_tasks_never_route_to_glm():
    settings = Settings(
        _env_file=None,
        off_grid=False,
        glm_enabled=True,
        glm_task_categories="summarization",
    )
    result = route_model("Resuma meu prontuário de saúde", settings, api_key="configured")
    assert result.provider == "local"
    assert result.reason == "conteúdo potencialmente sensível"


@pytest.mark.parametrize(
    "text",
    [
        "Resuma o e-mail alice@example.com",
        "Resuma CPF 123.456.789-09",
        "Resuma 12.345.678/0001-95",
        "Resuma o número +1 (415) 555-0198",
        "Resuma Authorization: Bearer synthetic-bearer-value",
        "Resuma password=synthetic pass phrase",
    ],
)
def test_sensitive_formats_stay_local_even_when_category_is_allowed(text):
    settings = Settings(
        _env_file=None,
        off_grid=False,
        glm_enabled=True,
        glm_api_key="configured",
        glm_task_categories="summarization",
    )
    assert route_model(text, settings).provider == "local"


def test_ambiguous_multiple_task_categories_stay_local():
    settings = Settings(
        _env_file=None,
        off_grid=False,
        glm_enabled=True,
        glm_api_key="configured",
        glm_task_categories="summarization,classification",
    )
    result = route_model("Resuma e classifique este texto", settings)
    assert result.provider == "local"
    assert result.reason == "pedido com categorias ambíguas"


def test_incidental_json_mention_is_not_an_auxiliary_task():
    assert classify_task("Explique o que significa JSON") == TaskCategory.CONVERSATION
    assert classify_task("O que significa a palavra classifique?") == TaskCategory.CONVERSATION


def test_offline_mode_blocks_glm_even_when_enabled():
    settings = Settings(_env_file=None, off_grid=True, glm_enabled=True)
    assert route_model("Resuma este texto", settings, api_key="configured").provider == "local"


def test_model_compatibility_reads_parameter_count_after_tag_not_model_family():
    assert is_model_compatible("qwen2.5-coder:7b-instruct-q4_K_M", 6, 16)
    assert not is_model_compatible("qwen2.5-coder:13b-instruct-q4_K_M", 6, 16)
    assert is_model_compatible("llama3.2:3b", 6, 16)


def test_model_category_parses_quantized_ollama_tags():
    compatible, category = get_model_category("qwen2.5-coder:7b-instruct-q4_K_M", 6, 16)
    assert compatible is True
    assert category in {"confortavel", "limitado", "inviavel"}


def test_model_category_marks_unknown_parameter_size_as_indeterminate():
    compatible, category = get_model_category("custom-model-without-size-tag", 6, 16)
    assert compatible is None
    assert category == "indeterminado"
