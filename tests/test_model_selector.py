from noite.model_selector import choose_installed_model, classify_request


def test_routes_code_questions_to_qwen_when_installed():
    model, category = choose_installed_model(
        "Me ajude a corrigir este código Python",
        ["qwen2.5:3b", "qwen3.5:4b", "deepseek-r1:1.5b"],
        "qwen2.5:3b",
    )
    assert model == "qwen3.5:4b"
    assert category == "coding"


def test_routes_deep_reasoning_to_deepseek_when_installed():
    model, category = choose_installed_model(
        "Explique detalhadamente o raciocínio passo a passo",
        ["qwen2.5:3b", "deepseek-r1:1.5b"],
        "qwen2.5:3b",
    )
    assert model == "deepseek-r1:1.5b"
    assert category == "reasoning"


def test_uses_only_installed_models_and_falls_back_safely():
    model, _ = choose_installed_model(
        "Escreva um script Python",
        ["qwen2.5:3b", "gemma3:4b"],
        "qwen2.5:3b",
    )
    assert model == "qwen2.5:3b"


def test_uses_first_installed_model_when_default_is_missing():
    model, _ = choose_installed_model("Olá", ["gemma3:4b"], "missing:model")
    assert model == "gemma3:4b"


def test_empty_inventory_uses_configured_fallback():
    model, _ = choose_installed_model("Olá", [], "qwen2.5:3b")
    assert model == "qwen2.5:3b"


def test_simple_greeting_uses_lightweight_model():
    assert classify_request("Oi, tudo bem?") == "simple"
