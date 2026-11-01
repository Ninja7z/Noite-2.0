import re

_PHONETIC_FIXES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b(?:iutub|yutub|rutube)\b", re.IGNORECASE), "youtube"),
    (re.compile(r"\bgugol\b", re.IGNORECASE), "google"),
)


def normalize_transcription(text: str) -> str:
    """Corrige formas fonéticas conhecidas sem alterar o restante da frase."""
    normalized = text.strip()
    for pattern, replacement in _PHONETIC_FIXES:
        normalized = pattern.sub(replacement, normalized)
    return normalized
