from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="NOITE_",
        extra="ignore",
    )

    off_grid: bool = True
    local_model: str = "qwen2.5:3b"
    ollama_base_url: str = "http://127.0.0.1:11435"
    data_dir: Path = Field(default_factory=lambda: Path.home() / ".noite")
    anthropic_model: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
