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
