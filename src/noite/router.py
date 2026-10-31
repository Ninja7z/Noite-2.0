import re

from .contracts import Intent, IntentKind
from .normalization import normalize_transcription

_OPEN_APP = re.compile(r"^abrir\s+(?P<app>.+)$", re.IGNORECASE)
_SEARCH_FILE = re.compile(
    r"^(?:pesquisar|procurar|buscar)\s+(?:arquivo\s+)?(?P<query>.+)$",
    re.IGNORECASE,
)


def route(text: str) -> Intent:
    original = text
    normalized = normalize_transcription(text)
    if not normalized:
        raise ValueError("O texto de entrada não pode estar vazio.")

    if match := _OPEN_APP.fullmatch(normalized):
        return Intent(
            kind=IntentKind.OPEN_APPLICATION,
            original_text=original,
            normalized_text=normalized,
            parameters={"app": match.group("app").strip()},
        )

    if match := _SEARCH_FILE.fullmatch(normalized):
        return Intent(
            kind=IntentKind.SEARCH_FILE,
            original_text=original,
            normalized_text=normalized,
            parameters={"query": match.group("query").strip()},
        )

    return Intent(
        kind=IntentKind.CHAT,
        original_text=original,
        normalized_text=normalized,
        source="local_model",
    )
