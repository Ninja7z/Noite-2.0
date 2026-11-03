from enum import StrEnum

from pydantic import BaseModel, Field


class IntentKind(StrEnum):
    CHAT = "chat"
    OPEN_APPLICATION = "open_application"
    SEARCH_FILE = "search_file"
    SHOW_MASCOT = "show_mascot"
    HIDE_MASCOT = "hide_mascot"


class Intent(BaseModel):
    kind: IntentKind
    original_text: str
    normalized_text: str
    parameters: dict[str, str] = Field(default_factory=dict)
    source: str = "rules"
