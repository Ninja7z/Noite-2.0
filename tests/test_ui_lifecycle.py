from __future__ import annotations

import asyncio
import json
import os
import threading
import time
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QIcon, QTextCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QInputDialog,
    QLabel,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTextBrowser,
    QToolButton,
)

from noite.activity import make_activity_event
from noite.activity_panel import ContextActivityPanel
from noite.ui import MCPDialog, NoiteWindow, TaskThread


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_close_waits_for_running_worker_to_finish(app):
    gate = threading.Event()
    window = NoiteWindow.__new__(NoiteWindow)
    QMainWindow.__init__(window)
    window._workers = set()
    window._close_when_idle = False
    window.worker = None
    window.input = QPlainTextEdit()
    window.send_button = QPushButton()
    window.cancel_button = QPushButton()
    window.mcp_button = QPushButton()
    window.progress = QLabel()
    worker = TaskThread(lambda: gate.wait(timeout=3), window)
    worker_finished = threading.Event()
    window._workers.add(worker)
    window.worker = worker
    worker.finished.connect(lambda current=worker: window._worker_finished(current))
    worker.finished.connect(worker_finished.set)
    window.show()
    worker.start()

    window.close()
    assert window.isVisible()
    assert window._close_when_idle
    assert not window.input.isEnabled()

    gate.set()
    deadline = time.monotonic() + 5
    while window.isVisible() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    app.processEvents()

    assert worker_finished.is_set()
    assert not window.isVisible()
    assert not window._workers


def test_window_close_cancels_async_worker_and_waits(app):
    started = threading.Event()
    cleaned = threading.Event()
    window = NoiteWindow.__new__(NoiteWindow)
    QMainWindow.__init__(window)
    window._workers = set()
    window._close_when_idle = False
    window.worker = None
    window.input = QPlainTextEdit()
    window.send_button = QPushButton()
    window.cancel_button = QPushButton()
    window.mcp_button = QPushButton()
    window.progress = QLabel()

    async def work(_worker):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cleaned.set()

    cancelled = threading.Event()
    worker_finished = threading.Event()
    worker = window._start_worker(work, cancelled=cancelled.set, finished=worker_finished.set)
    window.worker = worker
    window.show()
    assert started.wait(timeout=2)

    window.close()
    deadline = time.monotonic() + 5
    while window.isVisible() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    app.processEvents()

    assert cancelled.is_set()
    assert cleaned.is_set()
    assert worker_finished.is_set()
    assert not window.isVisible()
    assert not window._workers


def test_worker_signal_handlers_are_connected_before_start(app, monkeypatch):
    window = NoiteWindow.__new__(NoiteWindow)
    QMainWindow.__init__(window)
    window._workers = set()
    received = []

    def immediate_result(worker):
        worker.completed.emit("too fast")

    monkeypatch.setattr(TaskThread, "start", immediate_result)
    worker = window._start_worker(lambda _worker: None, completed=received.append)

    assert received == ["too fast"]
    window._workers.clear()
    worker.deleteLater()
    window.deleteLater()


def test_streamed_text_is_inserted_as_plain_text(app):
    window = NoiteWindow.__new__(NoiteWindow)
    QMainWindow.__init__(window)
    window.chat = QTextBrowser()
    window._streaming_response_active = False
    window._streaming_response_text = ""
    window._record_activity = lambda _event: None
    window._show_chat = lambda: None

    window._on_stream_chunk("<script>")
    window._on_stream_chunk("literal text")
    QTest.qWait(140)

    assert "<script>literal text" in window.chat.toPlainText()
    assert window.chat.document().toHtml().count("&lt;script&gt;") == 1
    window.deleteLater()


def test_streaming_preserves_manual_scroll_and_reports_generation(app):
    window = NoiteWindow.__new__(NoiteWindow)
    QMainWindow.__init__(window)
    window.chat = QTextBrowser()
    window.chat.setFixedSize(320, 120)
    window.chat.setPlainText("\n".join(f"linha {index}" for index in range(80)))
    window.chat.show()
    app.processEvents()
    window.chat.verticalScrollBar().setValue(0)
    window._streaming_response_active = False
    window._streaming_response_text = ""
    window._messages = []
    window._show_chat = lambda: None
    events = []
    window._record_activity = events.append

    window._on_stream_chunk("trecho")

    assert window.chat.verticalScrollBar().value() == 0
    assert events[0].operation == "Geração da resposta"
    assert events[0].state == "started"
    window.deleteLater()


def test_settings_dialog_scrolls_at_compact_size(app, tmp_path, monkeypatch):
    from PySide6.QtCore import QSettings

    from noite import ui
    from noite.config import Settings
    from noite.ide import ProjectDock

    settings = Settings(_env_file=None, data_dir=tmp_path)
    monkeypatch.setattr(
        ui,
        "QSettings",
        lambda *_args: QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat),
    )
    monkeypatch.setattr(ui, "get_settings", lambda: settings)
    monkeypatch.setattr(NoiteWindow, "_check_status", lambda self: None)
    monkeypatch.setattr(ProjectDock, "_restore_workspace", lambda self: None)
    scrollbars = []

    def inspect_compact_dialog(dialog):
        dialog.resize(430, 370)
        dialog.show()
        app.processEvents()
        scroll = dialog.findChild(QScrollArea, "settingsScrollArea")
        assert scroll is not None
        scrollbars.append(scroll.verticalScrollBar().maximum())
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(QDialog, "exec", inspect_compact_dialog)
    window = NoiteWindow()
    window._open_settings()

    assert scrollbars and scrollbars[0] > 0
    window.close()


def test_context_panel_contains_only_reference_cards_and_elides_directory(app):
    from noite.theme import DARK_THEME

    panel = ContextActivityPanel()
    panel.setStyleSheet(DARK_THEME)
    panel.resize(280, 700)
    panel.set_reference_context(
        {
            "project": "Noite-2.0",
            "directory": r"C:\Users\example\Documents\workspace\very-long-project-directory",
            "indexed_documents": 18,
        }
    )
    panel.show()
    app.processEvents()

    visible_text = " ".join(label.text() for label in panel.findChildren(QLabel))
    assert "Destaques" in visible_text
    assert "Contexto Atual" in visible_text
    assert "Ferramentas" in visible_text
    assert "Atividade" not in visible_text
    assert "produtividade." in visible_text
    title = panel.findChild(QLabel, "highlightTitle")
    assert title is not None
    assert not panel.highlight_laptop.isVisible()
    title_lines = title.text().splitlines()
    assert len(title_lines) == 2
    assert all(
        title.fontMetrics().horizontalAdvance(line) <= title.width()
        for line in title_lines
    )
    assert "…" in panel.reference_directory.text()
    assert "very-long-project-directory" in panel.reference_directory.toolTip()
    panel.deleteLater()


def test_chat_messages_have_no_card_background_and_code_has_copy_action():
    user_html = NoiteWindow._bubble_html("user", "Minha pergunta\n```py\nprint(1)\n```")
    assistant_html = NoiteWindow._bubble_html("assistant", "```python\nprint(1)\n```")

    assert "Você" in user_html
    assert "Noite" in assistant_html
    assert "background" not in user_html.casefold()
    assert 'href="copy:' in user_html
    assert 'href="copy:' in assistant_html


def test_thinking_panel_shows_only_received_text_and_collapses_after_response(
    app, tmp_path, monkeypatch
):
    from PySide6.QtCore import QSettings

    from noite import ui
    from noite.config import Settings
    from noite.ide import ProjectDock
    from ui.client import MockClient

    settings = Settings(_env_file=None, data_dir=tmp_path)
    monkeypatch.setattr(
        ui,
        "QSettings",
        lambda *_args: QSettings(str(tmp_path / "thinking.ini"), QSettings.Format.IniFormat),
    )
    monkeypatch.setattr(ui, "get_settings", lambda: settings)
    monkeypatch.setattr(NoiteWindow, "_check_status", lambda self: None)
    monkeypatch.setattr(ProjectDock, "_restore_workspace", lambda self: None)
    window = NoiteWindow(client=MockClient())
    window.show()
    app.processEvents()

    assert window.thinking_panel.isHidden()
    window._on_thinking_chunk("Vou conferir os dados recebidos.")
    app.processEvents()
    assert not window.thinking_panel.isHidden()
    assert window.thinking_text_label.text() == "Vou conferir os dados recebidos."
    assert window.thinking_title.text() == "Pensamento"

    window._finish_thinking()
    QTest.qWait(230)
    assert window.thinking_title.text().startswith("Pensou por ")
    assert window.thinking_text_label.isHidden()
    window._toggle_thinking_panel()
    QTest.qWait(230)
    assert not window.thinking_text_label.isHidden()
    assert window.thinking_text_label.text() == "Vou conferir os dados recebidos."
    window.close()


def test_reference_dashboard_and_composer_follow_empty_chat_layout(app, tmp_path, monkeypatch):
    from noite import ui
    from noite.config import Settings
    from ui.client import MockClient

    settings = Settings(_env_file=None, data_dir=tmp_path)
    monkeypatch.setattr(ui, "get_settings", lambda: settings)
    monkeypatch.setattr(NoiteWindow, "_check_status", lambda self: None)
    window = NoiteWindow(client=MockClient())
    window.resize(1000, 700)
    window.show()
    app.processEvents()

    assert window.sidebar.width() == 220
    assert window.chips_grid.rowCount() == 2
    assert window.main_layout.indexOf(window.composer) == -1
    assert window.welcome_layout.indexOf(window.composer) >= 0
    assert window.context_panel.reference_project.text() == "Projeto ativo\nNoite-2.0"
    assert "18 documentos" in window.context_panel.reference_documents.text()
    assert window.context_panel.isHidden()
    assert window.activity_toggle_button.text() == "Abrir painel"
    assert window.findChild(QLabel, "chromeName") is None
    assert set(window.context_panel.tool_buttons) == {
        "Calculadora",
        "Pesquisa na Web",
        "Executar Comando",
        "Abrir Arquivo",
    }

    window._append_message("user", "Teste de layout")
    assert window.main_layout.indexOf(window.composer) >= 0
    window._messages.clear()
    window._render_chat()
    assert window.welcome_layout.indexOf(window.composer) >= 0
    window.close()


def test_moon_icon_is_multiresolution_and_loadable(app):
    from pathlib import Path

    icon_path = Path(__file__).parents[1] / "assets" / "noite.ico"
    icon = QIcon(str(icon_path))
    sizes = {(size.width(), size.height()) for size in icon.availableSizes()}

    assert not icon.isNull()
    assert {(16, 16), (32, 32), (48, 48), (256, 256)} <= sizes


def _grant_mcp_access(data_dir) -> None:
    """MCP is default-deny: simulate the user granting access in settings."""
    security = Path(data_dir) / "security"
    security.mkdir(parents=True, exist_ok=True)
    (security / "permissions.json").write_text(
        json.dumps({"schema_version": 1, "profile": "full", "enabled": ["mcp.call"]}),
        encoding="utf-8",
    )


def test_mcp_call_requires_explicit_approval(app, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    dialog = MCPDialog(tmp_path)
    dialog.servers = {"example": {"command": "configured-server", "args": []}}
    dialog._save_servers()
    dialog._approved["example"] = dialog._server_fingerprint(dialog.servers["example"])
    dialog._refresh_servers()
    item = QListWidgetItem("write_file")
    item.setData(
        Qt.UserRole,
        {"name": "write_file", "description": "Write a file", "input_schema": {}},
    )
    dialog.tools.addItem(item)
    dialog.tools.setCurrentItem(item)
    dialog.arguments_input.setPlainText('{"path":"notes.txt"}')
    _grant_mcp_access(tmp_path)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.No)

    dialog._call_selected()

    assert dialog.worker is None


def test_mcp_call_without_permission_is_denied_and_never_executed(app, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    from noite import mcp_client

    executed = []

    async def fake_call(self, server, name, arguments, input_schema=None):
        executed.append(name)
        return ["should not run"]

    monkeypatch.setattr(mcp_client.MCPClient, "call_tool", fake_call)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Yes)
    dialog = MCPDialog(tmp_path)
    config = {"command": "configured-server", "args": []}
    dialog.servers = {"example": config}
    dialog._save_servers()
    dialog._approved["example"] = dialog._server_fingerprint(config)
    dialog._refresh_servers()
    item = QListWidgetItem("write_file")
    item.setData(Qt.UserRole, {"name": "write_file", "input_schema": {}})
    dialog.tools.addItem(item)
    dialog.tools.setCurrentItem(item)
    dialog.arguments_input.setPlainText('{"path":"notes.txt"}')

    dialog._call_selected()

    assert dialog.worker is None
    assert executed == []
    assert "Permissão negada" in dialog.result.toPlainText()


def test_approved_mcp_call_runs_only_selected_tool(app, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    from noite import mcp_client

    captured = {}
    done = threading.Event()

    async def fake_call(self, server, name, arguments, input_schema=None):
        captured["server"] = server
        captured["name"] = name
        captured["arguments"] = arguments
        captured["input_schema"] = input_schema
        done.set()
        return ["completed"]

    monkeypatch.setattr(mcp_client.MCPClient, "call_tool", fake_call)
    _grant_mcp_access(tmp_path)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Yes)
    dialog = MCPDialog(tmp_path)
    dialog.servers = {"example": {"command": "configured-server", "args": ["--stdio"]}}
    dialog._save_servers()
    dialog._approved["example"] = dialog._server_fingerprint(dialog.servers["example"])
    dialog._refresh_servers()
    item = QListWidgetItem("write_file")
    item.setData(
        Qt.UserRole,
        {
            "name": "write_file",
            "description": "",
            "input_schema": {"type": "object"},
        },
    )
    dialog.tools.addItem(item)
    dialog.tools.setCurrentItem(item)
    dialog.arguments_input.setPlainText('{"path":"notes.txt"}')

    dialog._call_selected()
    deadline = time.monotonic() + 5
    while "Dados não confiáveis" not in dialog.result.toPlainText():
        if time.monotonic() >= deadline:
            break
        app.processEvents()
        time.sleep(0.01)
    app.processEvents()

    assert done.is_set()
    assert captured["name"] == "write_file"
    assert captured["arguments"] == {"path": "notes.txt"}
    assert captured["input_schema"] == {"type": "object"}
    assert captured["server"].allowed_tools == frozenset({"write_file"})
    assert "completed" in dialog.result.toPlainText()
    assert "não confiáveis" in dialog.result.toPlainText()


def test_mcp_config_corruption_is_preserved_and_reported(app, tmp_path):
    config_path = tmp_path / "mcp_servers.json"
    config_path.write_text("{broken", encoding="utf-8")
    prior_backup = tmp_path / "mcp_servers.json.corrupt"
    prior_backup.write_text("previous backup", encoding="utf-8")

    dialog = MCPDialog(tmp_path)

    backup = tmp_path / "mcp_servers.json.corrupt.1"
    assert backup.read_text(encoding="utf-8") == "{broken"
    assert prior_backup.read_text(encoding="utf-8") == "previous backup"
    assert "inválida" in dialog.result.toPlainText()


def test_mcp_configuration_change_after_discovery_requires_rediscovery(app, tmp_path, monkeypatch):
    dialog = MCPDialog(tmp_path)
    config = {"command": "configured-server", "args": ["--safe"]}
    dialog.servers = {"example": config}
    dialog._save_servers()
    dialog._approved["example"] = dialog._server_fingerprint(config)
    dialog._refresh_servers()
    item = QListWidgetItem("read_file")
    item.setData(Qt.UserRole, {"name": "read_file", "input_schema": {}})
    dialog.tools.addItem(item)
    dialog.tools.setCurrentItem(item)
    dialog.arguments_input.setPlainText("{}")
    (tmp_path / "mcp_servers.json").write_text(
        '{"example":{"command":"changed-server","args":[]}}', encoding="utf-8"
    )
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: warnings.append(args[1]))

    dialog._call_selected()

    assert dialog.worker is None
    assert warnings == ["Configuração alterada"]


def test_mcp_configuration_change_while_confirmation_is_open_aborts_call(
    app, tmp_path, monkeypatch
):
    dialog = MCPDialog(tmp_path)
    config = {"command": "configured-server", "args": []}
    dialog.servers = {"example": config}
    dialog._save_servers()
    dialog._approved["example"] = dialog._server_fingerprint(config)
    dialog._refresh_servers()
    item = QListWidgetItem("read_file")
    item.setData(Qt.UserRole, {"name": "read_file", "input_schema": {}})
    dialog.tools.addItem(item)
    dialog.tools.setCurrentItem(item)
    dialog.arguments_input.setPlainText("{}")
    warnings = []

    def alter_config_during_approval(*args, **kwargs):
        (tmp_path / "mcp_servers.json").write_text(
            '{"example":{"command":"changed-server","args":[]}}', encoding="utf-8"
        )
        return QMessageBox.Yes

    _grant_mcp_access(tmp_path)
    monkeypatch.setattr(QMessageBox, "question", alter_config_during_approval)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: warnings.append(args[1]))

    dialog._call_selected()

    assert dialog.worker is None
    assert warnings == ["Configuração alterada"]


def test_conversation_sidebar_supports_create_open_rename_delete_and_restore(
    app, tmp_path, monkeypatch
):
    from noite import ui
    from noite.config import Settings
    from noite.store import add_message, get_active_conversation_id, open_database

    settings = Settings(_env_file=None, data_dir=tmp_path)
    monkeypatch.setattr(ui, "get_settings", lambda: settings)
    monkeypatch.setattr(NoiteWindow, "_check_status", lambda self: None)
    with open_database(tmp_path / "noite.sqlite3") as connection:
        add_message(connection, "user", "histórico legado", "default")

    window = NoiteWindow()
    assert "histórico legado" in window.chat.toPlainText()
    assert (
        len(
            [
                button
                for button in window.findChildren(QToolButton)
                if button.objectName() == "railButton"
            ]
        )
        == 2
    )

    window.new_conversation()
    created_id = window.conversation_id
    assert created_id != "default"
    assert not window.chat.toPlainText().strip()

    asyncio.run(window.client.enviar("oi", conversation_id=created_id))
    window._refresh_conversation_list(created_id)
    assert window.conversation_list.currentItem().text() == "oi"

    monkeypatch.setattr(
        QInputDialog,
        "getText",
        lambda *args, **kwargs: ("Conversa nomeada", True),
    )
    window.rename_current_conversation()
    assert window.conversation_list.currentItem().text() == "Conversa nomeada"

    window.open_conversation("default")
    assert "histórico legado" in window.chat.toPlainText()
    assert "Oi! Como posso ajudar?" not in window.chat.toPlainText()
    window.open_conversation(created_id)
    assert "Oi! Como posso ajudar?" in window.chat.toPlainText()

    restarted = NoiteWindow()
    assert restarted.conversation_id == created_id
    assert "Oi! Como posso ajudar?" in restarted.chat.toPlainText()
    restarted.hide()

    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Yes)
    window.delete_current_conversation()
    assert window.conversation_id == "default"
    assert "histórico legado" in window.chat.toPlainText()
    with open_database(tmp_path / "noite.sqlite3") as connection:
        assert (
            connection.execute("SELECT 1 FROM conversations WHERE id = ?", (created_id,)).fetchone()
            is None
        )
        assert get_active_conversation_id(connection) == "default"
        assert connection.execute(
            "SELECT count(*) FROM messages WHERE conversation_id = 'default'"
        ).fetchone() == (1,)

    window.hide()


def test_command_palette_shortcut_navigation_and_collapsible_panels(
    app, tmp_path, monkeypatch
):
    from PySide6.QtCore import QSettings

    from noite import ui
    from noite.config import Settings

    settings = Settings(_env_file=None, data_dir=tmp_path)
    preferences_file = str(tmp_path / "ui.ini")
    monkeypatch.setattr(
        ui,
        "QSettings",
        lambda *_args: QSettings(preferences_file, QSettings.Format.IniFormat),
    )
    ui.QSettings("Noite", "Noite 2.0").clear()
    monkeypatch.setattr(ui, "get_settings", lambda: settings)
    monkeypatch.setattr(NoiteWindow, "_check_status", lambda self: None)
    from noite.ide import ProjectDock

    # QSettings persiste o último workspace da máquina; isole para validar a
    # paleta sem projeto aberto, independentemente do estado local do usuário.
    monkeypatch.setattr(ProjectDock, "_restore_workspace", lambda self: None)
    window = NoiteWindow()
    window.resize(1366, 768)

    assert window.context_panel.isHidden()
    assert "search-files" not in {action.action_id for action in window._palette_actions()}
    assert window._palette_shortcut.key().toString() == "Ctrl+K"

    window._toggle_context_panel()
    assert not window.context_panel.isHidden()
    window._toggle_context_panel()
    assert window.context_panel.isHidden()
    window._toggle_sidebar()
    assert window.sidebar.isHidden()
    assert not window.expand_sidebar_button.isHidden()
    window._toggle_sidebar()
    assert not window.sidebar.isHidden()
    assert window.expand_sidebar_button.isHidden()
    assert window.size().width() == window.maximumWidth()

    window.close()


def test_project_context_status_updates_existing_labels(app, tmp_path):
    from types import SimpleNamespace

    from PySide6.QtWidgets import QLabel

    window = NoiteWindow.__new__(NoiteWindow)
    QMainWindow.__init__(window)
    window.settings = SimpleNamespace(off_grid=True)
    window.context_panel = SimpleNamespace(
        set_project=lambda name: setattr(window, "project_name", name)
    )
    window.composer_project_label = QLabel()

    window._update_project_context_status(str(tmp_path))

    assert window.project_name == tmp_path.name
    assert tmp_path.name in window.composer_project_label.text()


def test_sidebar_positions_and_theme_preferences_persist(app, tmp_path, monkeypatch):
    from PySide6.QtCore import QSettings

    from noite import ui
    from noite.config import Settings
    from noite.ide import ProjectDock

    settings = Settings(_env_file=None, data_dir=tmp_path)
    preferences_file = str(tmp_path / "ui.ini")
    monkeypatch.setattr(
        ui,
        "QSettings",
        lambda *_args: QSettings(preferences_file, QSettings.Format.IniFormat),
    )
    monkeypatch.setattr(ui, "get_settings", lambda: settings)
    monkeypatch.setattr(NoiteWindow, "_check_status", lambda self: None)
    monkeypatch.setattr(ProjectDock, "_restore_workspace", lambda self: None)
    window = NoiteWindow()
    assert window.windowFlags() & Qt.WindowType.FramelessWindowHint
    screen_size = QGuiApplication.primaryScreen().availableGeometry().size()
    assert window.minimumSize().width() == min(900, screen_size.width())
    assert window.size().width() <= screen_size.width()
    assert window.size().height() <= screen_size.height()
    assert window.size().width() == min(
        screen_size.width(),
        max(window.minimumSize().width(), round(screen_size.width() * 0.8)),
    )
    window._apply_theme("light")
    assert window.styleSheet() == ui.LIGHT_THEME
    assert "#fbfaff" in window.command_palette.styleSheet()
    window._apply_theme("system")
    assert window.preferences.value("appearance/theme") == "system"

    window._apply_sidebar_position("left")
    assert window.shell_layout.direction() == ui.QBoxLayout.Direction.LeftToRight
    assert window.shell_layout.indexOf(window.sidebar) < window.shell_layout.indexOf(
        window.content_area
    )
    window._apply_sidebar_position("right")
    assert window.shell_layout.indexOf(window.sidebar) > window.shell_layout.indexOf(
        window.content_area
    )
    window._apply_sidebar_position("top")
    assert window.shell_layout.direction() == ui.QBoxLayout.Direction.TopToBottom
    assert window.preferences.value("appearance/sidebar") == "top"
    window.resize(920, 620)
    assert window.minimumSize().width() <= 920

    persisted = QSettings(preferences_file, QSettings.Format.IniFormat)
    assert persisted.value("appearance/theme") == "system"
    assert persisted.value("appearance/sidebar") == "top"
    window.close()


def test_real_operation_updates_composer_status_without_opening_side_panel(
    app, tmp_path, monkeypatch
):
    from PySide6.QtCore import QSettings

    from noite import ui
    from noite.config import Settings
    from noite.ide import ProjectDock

    settings = Settings(_env_file=None, data_dir=tmp_path)
    preferences_file = str(tmp_path / "progress.ini")
    monkeypatch.setattr(
        ui,
        "QSettings",
        lambda *_args: QSettings(preferences_file, QSettings.Format.IniFormat),
    )
    monkeypatch.setattr(ui, "get_settings", lambda: settings)
    monkeypatch.setattr(NoiteWindow, "_check_status", lambda self: None)
    monkeypatch.setattr(ProjectDock, "_restore_workspace", lambda self: None)
    QSettings(preferences_file, QSettings.Format.IniFormat).setValue(
        "panels/activity_visible", False
    )

    window = NoiteWindow()
    assert window.context_panel.isHidden()
    started = make_activity_event("Leitura de anexos", "started", "Extraindo documentos")
    window._record_activity(started)
    assert window.context_panel.isHidden()
    assert window.progress.text() == "Pensando…"

    window._record_activity(
        make_activity_event("Leitura de anexos", "completed", "Extração concluída")
    )
    assert window.context_panel.isHidden()
    assert window.progress.text() == "Resposta recebida"
    window.close()


def test_selected_attachment_excerpt_is_sent_through_chat_worker(
    app, tmp_path, monkeypatch
):
    from PySide6.QtCore import QSettings

    from noite import ui
    from noite.attachments import ExtractedAttachment
    from noite.config import Settings
    from noite.ide import ProjectDock

    settings = Settings(_env_file=None, data_dir=tmp_path)
    preferences_file = str(tmp_path / "attachment-chat.ini")
    monkeypatch.setattr(
        ui,
        "QSettings",
        lambda *_args: QSettings(preferences_file, QSettings.Format.IniFormat),
    )
    monkeypatch.setattr(ui, "get_settings", lambda: settings)
    monkeypatch.setattr(NoiteWindow, "_check_status", lambda self: None)
    monkeypatch.setattr(ProjectDock, "_restore_workspace", lambda self: None)
    captured = {}

    async def fake_respond(self, text, **_kwargs):
        captured["text"] = text
        return "Resposta de teste"

    class SignalStub:
        def emit(self, *_args):
            return None

    class WorkerStub:
        streamed = SignalStub()
        thinking_streamed = SignalStub()
        activity = SignalStub()

    def synchronous_worker(self, task, *, completed=None, finished=None, **_kwargs):
        result = asyncio.run(task(WorkerStub()))
        if completed is not None:
            completed(result)
        if finished is not None:
            finished()
        return None

    monkeypatch.setattr(ui.ServiceClient, "enviar", fake_respond)
    monkeypatch.setattr(NoiteWindow, "_start_worker", synchronous_worker)
    window = NoiteWindow()
    attachment_text = "Introdução. " * 500 + "GPU VRAM regressão Qwen. " + "Apêndice. " * 500
    window._attachments = [
        ExtractedAttachment(
            path=tmp_path / "report.txt",
            media_type="TXT",
            size_bytes=len(attachment_text),
            text=attachment_text,
            truncated=False,
        )
    ]
    window.input.setPlainText("Qual a regressão de VRAM do Qwen?")
    window._pending_attachment_count = 1
    window.send_message()
    assert not captured
    assert window.input.toPlainText()
    window._pending_attachment_count = 0
    window.send_message()

    assert "VRAM regressão Qwen" in captured["text"]
    assert "dado não confiável" in captured["text"]
    assert len(captured["text"]) < 5000
    assert "report.txt" in window.chat.toPlainText()
    window.close()


def test_terminal_dock_opens_without_running_commands(app, tmp_path, monkeypatch):
    from noite import ui
    from noite.config import Settings
    from noite.ide import ProjectDock

    settings = Settings(_env_file=None, data_dir=tmp_path)
    monkeypatch.setattr(ui, "get_settings", lambda: settings)
    monkeypatch.setattr(NoiteWindow, "_check_status", lambda self: None)
    monkeypatch.setattr(ProjectDock, "_restore_workspace", lambda self: None)
    window = NoiteWindow()
    assert window.terminal_dock.isHidden()
    window._toggle_terminal()
    assert not window.terminal_dock.isHidden()
    assert window.terminal_run_button.isEnabled() is False
    from types import SimpleNamespace

    window._terminal_last_result = SimpleNamespace(
        command="Get-Location", exit_code=0, output="C:\\workspace"
    )
    window._insert_terminal_result()
    assert "dados não confiáveis" in window.input.toPlainText()
    assert "Código de saída: 0" in window.input.toPlainText()
    window.close()


def test_project_dock_opens_edits_and_saves_workspace_file(app, tmp_path, monkeypatch):
    from PySide6.QtCore import QSettings

    from noite.ide import ProjectDock

    QSettings("cristnzx", "Noite2").setValue("workspace/last_path", "")
    source = tmp_path / "hello.py"
    source.write_text("print('hello')\n", encoding="utf-8")
    dock = ProjectDock()
    dock.set_workspace(tmp_path)
    file_index = dock._file_filter.mapFromSource(dock._model.index(str(source)))
    ignored = tmp_path / ".venv"
    ignored.mkdir()
    ignored_index = dock._model.index(str(ignored))
    assert not dock._file_filter.filterAcceptsRow(ignored_index.row(), ignored_index.parent())
    dock.open_index(file_index)

    editor = dock.tabs.currentWidget()
    assert isinstance(editor, QPlainTextEdit)
    assert "print('hello')" in editor.toPlainText()
    assert dock.active_document_snapshot() == ("hello.py", "print('hello')\n")
    assert dock.save_button.isEnabled() is False
    editor.moveCursor(QTextCursor.MoveOperation.End)
    editor.insertPlainText("# saved\n")
    assert dock.save_button.isEnabled() is True
    dock.save_current()

    assert source.read_text(encoding="utf-8") == "print('hello')\n# saved\n"
    assert editor.document().isModified() is False
    from noite.workspace import SearchMatch

    dock.open_search_match(SearchMatch(source.resolve(), 2, "saved"))
    assert dock.tabs.currentWidget().textCursor().blockNumber() == 1
    dock.find_input.setText("saved")
    assert dock.find_next()
    assert dock.tabs.currentWidget().textCursor().selectedText() == "saved"
    dock.replace_input.setText("updated")
    assert dock.replace_current()
    assert dock.find_status.text() == "Substituído"
    assert "# updated" in editor.toPlainText()
    assert source.read_text(encoding="utf-8") == "print('hello')\n# saved\n"
    dock.close()
    QSettings("cristnzx", "Noite2").setValue("workspace/last_path", "")


def test_project_dock_creates_items_only_after_confirmation(app, tmp_path, monkeypatch):
    from PySide6.QtCore import QSettings

    from noite.ide import ProjectDock

    QSettings("cristnzx", "Noite2").setValue("workspace/last_path", "")
    dock = ProjectDock()
    dock.set_workspace(tmp_path)
    monkeypatch.setattr(QInputDialog, "getText", lambda *args, **kwargs: ("new.py", True))
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.No)
    dock.create_file()
    assert not (tmp_path / "new.py").exists()

    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Yes)
    dock.create_file()
    assert (tmp_path / "new.py").is_file()
    assert isinstance(dock.tabs.currentWidget(), QPlainTextEdit)

    monkeypatch.setattr(QInputDialog, "getText", lambda *args, **kwargs: ("new-folder", True))
    dock.create_directory()
    assert (tmp_path / "new-folder").is_dir()
    dock.close()
    QSettings("cristnzx", "Noite2").setValue("workspace/last_path", "")
    QSettings("cristnzx", "Noite2").setValue("workspace/last_path", "")


def test_project_dock_replace_all_stays_in_buffer_and_undoes_as_one_edit(app, tmp_path):
    from PySide6.QtCore import QSettings

    from noite.ide import ProjectDock

    QSettings("cristnzx", "Noite2").setValue("workspace/last_path", "")
    source = tmp_path / "sample.py"
    source.write_text("value = 'old'\nprint('old')\n", encoding="utf-8")
    dock = ProjectDock()
    dock.set_workspace(tmp_path)
    dock.open_index(dock._file_filter.mapFromSource(dock._model.index(str(source))))
    editor = dock.tabs.currentWidget()
    dock.find_input.setText("old")
    dock.replace_input.setText("new")

    assert dock.replace_all() == 2
    assert editor.toPlainText() == "value = 'new'\nprint('new')\n"
    assert source.read_text(encoding="utf-8") == "value = 'old'\nprint('old')\n"
    assert editor.document().isModified()
    editor.undo()
    assert editor.toPlainText() == "value = 'old'\nprint('old')\n"
    dock.close()
    QSettings("cristnzx", "Noite2").setValue("workspace/last_path", "")


def test_project_dock_reports_python_syntax_and_navigates_to_error(app, tmp_path):
    from PySide6.QtCore import QSettings

    from noite.ide import ProjectDock

    QSettings("cristnzx", "Noite2").setValue("workspace/last_path", "")
    source = tmp_path / "broken.py"
    source.write_text("value = 1\n", encoding="utf-8")
    dock = ProjectDock()
    dock.set_workspace(tmp_path)
    dock.open_index(dock._file_filter.mapFromSource(dock._model.index(str(source))))
    editor = dock.tabs.currentWidget()

    dock.check_python_syntax()
    assert dock.problems.item(0).text() == "broken.py: sintaxe válida"
    editor.setPlainText("value = (\n")
    dock.check_python_syntax()
    problem = dock.problems.item(0)
    assert "broken.py:1:" in problem.text()
    dock._navigate_to_problem(problem)
    assert editor.textCursor().blockNumber() == 0
    dock.close()
    QSettings("cristnzx", "Noite2").setValue("workspace/last_path", "")
