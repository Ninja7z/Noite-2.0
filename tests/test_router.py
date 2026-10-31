import pytest

from noite.contracts import IntentKind
from noite.router import route


def test_route_open_application() -> None:
    intent = route("abrir calculadora")
    assert intent.kind == IntentKind.OPEN_APPLICATION
    assert intent.parameters == {"app": "calculadora"}


def test_route_search_file() -> None:
    intent = route("Pesquisar arquivo notas")
    assert intent.kind == IntentKind.SEARCH_FILE
    assert intent.parameters == {"query": "notas"}


def test_route_chat_and_preserve_original_text() -> None:
    intent = route("  Olá  ")
    assert intent.kind == IntentKind.CHAT
    assert intent.original_text == "  Olá  "
    assert intent.normalized_text == "Olá"


@pytest.mark.parametrize("text", ["", "   "])
def test_route_rejects_empty_text(text: str) -> None:
    with pytest.raises(ValueError, match="não pode estar vazio"):
        route(text)
