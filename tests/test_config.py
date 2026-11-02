import pytest

from noite.config import Settings


def test_settings_load_dotenv_file(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "NOITE_OLLAMA_BASE_URL=http://127.0.0.1:11435\n",
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.ollama_base_url == "http://127.0.0.1:11435"


def test_settings_default_ollama_url() -> None:
    settings = Settings(_env_file=None)
    assert settings.ollama_base_url == "http://127.0.0.1:11434"


def test_blank_workspace_setting_does_not_grant_current_directory(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("NOITE_WORKSPACE_DIR=\n", encoding="utf-8")

    settings = Settings(_env_file=env_file)

    assert settings.workspace_dir is None


def test_off_grid_requires_local_http_ollama_endpoint() -> None:
    import pytest

    with pytest.raises(ValueError, match="endpoint local"):
        Settings(_env_file=None, off_grid=True, ollama_base_url="https://example.com")


@pytest.mark.parametrize("url", ["file:///tmp/model", "ftp://127.0.0.1:11435"])
def test_ollama_endpoint_rejects_non_http_schemes(url) -> None:
    import pytest

    with pytest.raises(ValueError, match="http ou https"):
        Settings(_env_file=None, off_grid=False, ollama_base_url=url)


def test_ollama_endpoint_rejects_embedded_credentials() -> None:
    with pytest.raises(ValueError, match="Credenciais"):
        Settings(
            _env_file=None,
            ollama_base_url="http://user:password@127.0.0.1:11435",
        )


def test_glm_is_disabled_and_general_api_is_default() -> None:
    settings = Settings(_env_file=None)
    assert settings.glm_enabled is False
    assert settings.glm_model == "zai/glm-5.3-flash"
    assert settings.glm_api_base == "https://api.z.ai/api/paas/v4"


def test_invalid_glm_configuration_does_not_prevent_local_settings_startup() -> None:
    settings = Settings(
        _env_file=None,
        glm_enabled=True,
        glm_model="unknown/model",
        glm_api_mode="unknown",
    )
    assert settings.local_model == "qwen2.5:3b"


def test_glm_coding_plan_endpoint_is_explicit() -> None:
    settings = Settings(_env_file=None, off_grid=False, glm_api_mode="coding_plan")
    assert settings.glm_api_base == "https://api.z.ai/api/coding/paas/v4"


def test_glm_task_categories_parse_comma_separated_configuration() -> None:
    settings = Settings(
        _env_file=None,
        off_grid=False,
        glm_task_categories="summarization, documentation, ,classification",
    )
    assert settings.enabled_glm_task_categories == {
        "summarization",
        "documentation",
        "classification",
    }


def test_zai_api_key_loads_from_dotenv_but_is_not_represented(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("ZAI_API_KEY=synthetic-test-key\n", encoding="utf-8")

    settings = Settings(_env_file=env_file)

    assert settings.glm_api_key == "synthetic-test-key"
    assert "synthetic-test-key" not in repr(settings)
