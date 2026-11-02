from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import AliasChoices, Field, field_validator, model_validator
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
    ollama_base_url: str = "http://127.0.0.1:11434"
    model_timeout_seconds: int = Field(default=180, ge=1, le=600)
    data_dir: Path = Field(default_factory=lambda: Path.home() / ".noite")
    workspace_dir: Path | None = None
    anthropic_model: str | None = None
    glm_enabled: bool = False
    glm_model: str = "zai/glm-5.3-flash"
    glm_api_mode: str = "general"
    glm_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ZAI_API_KEY", "glm_api_key"),
        repr=False,
    )
    glm_timeout_seconds: int = Field(default=60, ge=1, le=600)
    glm_max_retries: int = Field(default=1, ge=0, le=2)
    glm_task_categories: str = ""

    @field_validator("workspace_dir", mode="before")
    @classmethod
    def empty_workspace_means_default(cls, value):
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        return value

    @model_validator(mode="after")
    def validate_ollama_endpoint(self):
        parts = urlsplit(self.ollama_base_url)
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            raise ValueError("NOITE_OLLAMA_BASE_URL precisa usar http ou https e ter um host")
        if parts.username is not None or parts.password is not None:
            raise ValueError("Credenciais não podem ser embutidas em NOITE_OLLAMA_BASE_URL")
        if self.off_grid and parts.hostname.casefold() not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("NOITE_OFF_GRID=true exige um endpoint local para o Ollama")
        return self

    @property
    def enabled_glm_task_categories(self) -> frozenset[str]:
        return frozenset(
            value.strip().casefold()
            for value in self.glm_task_categories.split(",")
            if value.strip()
        )

    @property
    def glm_api_base(self) -> str:
        if self.glm_api_mode == "coding_plan":
            return "https://api.z.ai/api/coding/paas/v4"
        return "https://api.z.ai/api/paas/v4"


@lru_cache
def get_settings() -> Settings:
    return Settings()
