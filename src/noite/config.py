from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
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
    model_timeout_seconds: int = Field(default=180, ge=1, le=600)
    data_dir: Path = Field(default_factory=lambda: Path.home() / ".noite")
    workspace_dir: Path | None = None
    anthropic_model: str | None = None

    @field_validator("workspace_dir", mode="before")
    @classmethod
    def empty_workspace_means_default(cls, value):
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
