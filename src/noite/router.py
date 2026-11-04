import re

from .contracts import Intent, IntentKind
from .normalization import normalize_transcription

_SHOW_MASCOT = re.compile(
    r"(?:(?:abrir|abir|abra|abre|mostrar|mostra|exibir|exiba|chamar|chama)\s+"
    r"(?:(?:o|a)\s+)?(?:mascote|noite(?:\s+2\.0)?)"
    r"|(?:open|show|display|launch|call)\s+(?:(?:the|my)\s+)?(?:mascot|noite)"
    r"|bring\s+(?:(?:the|my)\s+)?(?:mascot|noite)\s+up)"
    r"(?:\s+(?:on\s+screen|na\s+tela))?",
    re.IGNORECASE,
)
_CLOSE_MASCOT = re.compile(
    r"(?:(?:fechar|fecha|feche|encerre|encerrar|sair|saia)\s+(?:(?:o|a)\s+)?(?:mascote|noite(?:\s+2\.0)?))"
    r"|(?:close|exit|quit)\s+(?:(?:the|my)\s+)?(?:mascot|noite)"
    r"|(?:fechar|fecha|feche|encerre|encerrar|sair|saia)\s+(?:a\s+)?noite\s+2\.0",
    re.IGNORECASE,
)

_HIDE_MASCOT = re.compile(
    r"(?:esconder|esconda|esconde|ocultar|oculte|oculta|sumir|some|hide)[ ]+"
    r"(?:(?:o|a|the|my)[ ]+)?(?:mascote|mascot|noite(?:[ ]+2[.]0)?)",
    re.IGNORECASE,
)
_OPEN_APP = re.compile(r"(?:abrir|abra|abre)\s+(?P<app>.+)", re.IGNORECASE)
_SEARCH_FILE = re.compile(
    r"(?:pesquisar|pesquise|procurar|procure|buscar|busque)\s+"
    r"arquivos?\s+(?P<query>.+)",
    re.IGNORECASE,
)


def route(text: str) -> Intent:
    original = text
    normalized = normalize_transcription(text)
    if not normalized:
        raise ValueError("O texto de entrada não pode estar vazio.")

    if _CLOSE_MASCOT.fullmatch(normalized):
        return Intent(
            kind=IntentKind.HIDE_MASCOT,
            original_text=original,
            normalized_text=normalized,
            parameters={"action": "close", "endpoint": "/v1/mascot/close"},
        )

    if _HIDE_MASCOT.fullmatch(normalized):
        return Intent(
            kind=IntentKind.HIDE_MASCOT,
            original_text=original,
            normalized_text=normalized,
            parameters={"action": "hide", "endpoint": "/v1/mascot/hide"},
        )

    if _SHOW_MASCOT.fullmatch(normalized):
        return Intent(
            kind=IntentKind.SHOW_MASCOT,
            original_text=original,
            normalized_text=normalized,
            parameters={"action": "show", "endpoint": "/v1/mascot/show"},
        )

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
