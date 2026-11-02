from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from noite.activity import make_activity_event
from noite.activity_panel import ContextActivityPanel
from noite.command_palette import CommandAction, CommandPalette


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_palette_filters_live_actions_and_executes_with_keyboard(app):
    executed = []
    actions = [
        CommandAction("new", "Nova conversa", "Começar uma sessão", lambda: executed.append("new")),
        CommandAction(
            "search",
            "Pesquisar arquivos",
            "Buscar no projeto",
            lambda: executed.append("search"),
            ("workspace",),
        ),
    ]
    palette = CommandPalette(lambda: actions)
    palette.open()
    assert palette.results.count() == 2

    palette.search_input.setText("workspace")
    assert palette.results.count() == 1
    assert palette.results.currentItem().data(Qt.ItemDataRole.UserRole) == "search"

    QTest.keyClick(palette.search_input, Qt.Key.Key_Return)
    app.processEvents()
    assert executed == ["search"]
    assert not palette.isVisible()


def test_palette_escape_closes_without_executing_action(app):
    executed = []
    palette = CommandPalette(
        lambda: [CommandAction("new", "Nova conversa", "Iniciar", lambda: executed.append(True))]
    )
    palette.open()
    QTest.keyClick(palette.search_input, Qt.Key.Key_Escape)
    app.processEvents()

    assert not palette.isVisible()
    assert executed == []


def test_palette_arrow_navigation_selects_next_action(app):
    executed = []
    palette = CommandPalette(
        lambda: [
            CommandAction("first", "Primeira ação", "", lambda: executed.append("first")),
            CommandAction("second", "Segunda ação", "", lambda: executed.append("second")),
        ]
    )
    palette.open()
    QTest.keyClick(palette.search_input, Qt.Key.Key_Down)
    assert palette.results.currentRow() == 1
    QTest.keyClick(palette.results, Qt.Key.Key_Return)
    app.processEvents()

    assert executed == ["second"]
    assert not palette.isVisible()


def test_ctrl_k_opens_palette_in_main_window(app, tmp_path, monkeypatch):
    from noite import ui
    from noite.config import Settings
    from noite.ide import ProjectDock
    from noite.ui import NoiteWindow

    settings = Settings(_env_file=None, data_dir=tmp_path)
    monkeypatch.setattr(ui, "get_settings", lambda: settings)
    monkeypatch.setattr(NoiteWindow, "_check_status", lambda self: None)
    monkeypatch.setattr(ProjectDock, "_restore_workspace", lambda self: None)
    window = NoiteWindow()
    window.show()
    window.activateWindow()
    window.input.setFocus()
    app.processEvents()
    QTest.keyClick(window.input, Qt.Key.Key_K, Qt.KeyboardModifier.ControlModifier)
    app.processEvents()

    assert window.command_palette.isVisible()
    window.command_palette.reject()
    window.close()
    app.processEvents()


def test_activity_panel_shows_real_event_and_expandable_details(app):
    panel = ContextActivityPanel()
    event = make_activity_event(
        "Busca no projeto",
        "completed",
        "Pesquisa concluída · 2 resultado(s)",
        duration_ms=42,
        details="Projeto: exemplo",
    )
    panel.add_event(event)

    assert panel.events.count() == 1
    assert "Pesquisa concluída" in panel.events.item(0).text()
    assert not panel.details_toggle.isHidden()
    panel.details_toggle.setChecked(True)
    assert not panel.details.isHidden()
    assert panel.details.text() == "Projeto: exemplo"
