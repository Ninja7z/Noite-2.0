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
    assert settings.ollama_base_url == "http://127.0.0.1:11435"


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
