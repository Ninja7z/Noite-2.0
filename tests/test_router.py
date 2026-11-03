import pytest

from noite.contracts import IntentKind
from noite.router import route


def test_route_show_mascot_maps_to_show_endpoint() -> None:
    intent = route("abrir mascote")
    assert intent.kind == IntentKind.SHOW_MASCOT
    assert intent.parameters == {"action": "show", "endpoint": "/v1/mascot/show"}


def test_route_open_application() -> None:
    intent = route("abrir calculadora")
    assert intent.kind == IntentKind.OPEN_APPLICATION
    assert intent.parameters == {"app": "calculadora"}


def test_route_search_file() -> None:
    intent = route("Pesquisar arquivo notas")
    assert intent.kind == IntentKind.SEARCH_FILE
    assert intent.parameters == {"query": "notas"}


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("abra calculadora", IntentKind.OPEN_APPLICATION),
        ("abre editor", IntentKind.OPEN_APPLICATION),
        ("abrir mascote", IntentKind.SHOW_MASCOT),
        ("abra o mascote", IntentKind.SHOW_MASCOT),
        ("mostrar mascote", IntentKind.SHOW_MASCOT),
        ("chama a Noite", IntentKind.SHOW_MASCOT),
        ("Open Mascot", IntentKind.SHOW_MASCOT),
        ("open mascot", IntentKind.SHOW_MASCOT),
        ("open the mascot", IntentKind.SHOW_MASCOT),
        ("show mascot", IntentKind.SHOW_MASCOT),
        ("display the mascot", IntentKind.SHOW_MASCOT),
        ("launch mascot", IntentKind.SHOW_MASCOT),
        ("bring the mascot up", IntentKind.SHOW_MASCOT),
        ("open Noite", IntentKind.SHOW_MASCOT),
        ("pesquise arquivos receitas", IntentKind.SEARCH_FILE),
        ("busque arquivo relatório", IntentKind.SEARCH_FILE),
        ("procure arquivos fotos", IntentKind.SEARCH_FILE),
    ],
)
def test_route_understands_imperative_forms_only_for_explicit_actions(text, kind):
    assert route(text).kind == kind


@pytest.mark.parametrize(
    "text",
    ["abril", "esporte", "arquitetura", "anote", "pesquise receitas no youtube"],
)
def test_route_does_not_misclassify_unrelated_phrases(text):
    assert route(text).kind == IntentKind.CHAT


def test_route_chat_and_preserve_original_text() -> None:
    intent = route("  Olá  ")
    assert intent.kind == IntentKind.CHAT
    assert intent.original_text == "  Olá  "
    assert intent.normalized_text == "Olá"


@pytest.mark.parametrize("text", ["", "   "])
def test_route_rejects_empty_text(text: str) -> None:
    with pytest.raises(ValueError, match="não pode estar vazio"):
        route(text)
