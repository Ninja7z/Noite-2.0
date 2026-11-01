from __future__ import annotations

import asyncio
import html
import inspect
import json
import shlex
import threading
from collections.abc import Callable
from contextlib import closing
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QKeyEvent, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .assistant import AssistantService
from .config import get_settings
from .store import open_database, recent_messages


class InputBox(QPlainTextEdit):
    send_requested = Signal()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if (
            event.key() in (Qt.Key_Return, Qt.Key_Enter)
            and not event.modifiers() & Qt.ShiftModifier
        ):
            self.send_requested.emit()
            return
        super().keyPressEvent(event)


class TaskThread(QThread):
    completed = Signal(object)
    failed = Signal(str)
    cancelled = Signal()
    streamed = Signal(str)

    def __init__(self, task: Callable[[], object], parent=None) -> None:
        super().__init__(parent)
        self.task = task
        self._cancel_requested = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._async_task: asyncio.Task | None = None

    def run(self) -> None:
        try:
            result = self.task()
            if inspect.isawaitable(result):
                result = self._run_async(result)
            self.completed.emit(result)
        except asyncio.CancelledError:
            self.cancelled.emit()
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: não foi possível concluir a operação.")

    def request_cancel(self) -> None:
        self._cancel_requested.set()
        loop = self._loop
        task = self._async_task
        if loop is not None and task is not None:
            try:
                loop.call_soon_threadsafe(task.cancel)
            except RuntimeError:
                # The task may finish between reading the loop and scheduling cancellation.
                pass

    def _run_async(self, awaitable):
        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        task = loop.create_task(awaitable)
        self._async_task = task
        if self._cancel_requested.is_set():
            loop.call_soon(task.cancel)
        try:
            return loop.run_until_complete(task)
        finally:
            pending = asyncio.all_tasks(loop)
            for pending_task in pending:
                pending_task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.run_until_complete(loop.shutdown_asyncgens())
            asyncio.set_event_loop(None)
            self._async_task = None
            self._loop = None
            loop.close()


class NoiteWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = get_settings()
        self.service = AssistantService(self.settings)
        self.conversation_id = "default"
        self.worker: TaskThread | None = None
        self._workers: set[TaskThread] = set()
        self._close_when_idle = False
        self._streaming_response_active = False
        self._streaming_response_text = ""
        self.setWindowTitle("Noite 2.0")
        self.setMinimumSize(920, 620)
        self.resize(1160, 720)
        self._build_ui()
        self._load_history()
        self._check_status()

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("appRoot")
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        rail = QFrame()
        rail.setObjectName("iconRail")
        rail.setFixedWidth(54)
        rail_layout = QVBoxLayout(rail)
        rail_layout.setContentsMargins(8, 14, 8, 14)
        rail_layout.setSpacing(16)
        mark = QLabel("N")
        mark.setObjectName("brandMark")
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setFixedSize(38, 38)
        rail_layout.addWidget(mark)
        rail_layout.addWidget(self._rail_glyph("⌂", "Noite 2.0"))
        rail_layout.addWidget(self._rail_glyph("◷", "Conversa local"))
        rail_layout.addStretch(1)
        rail_layout.addWidget(self._rail_glyph("···", "Ferramentas MCP"))
        shell.addWidget(rail)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(270)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(16, 20, 16, 16)
        side_layout.setSpacing(10)
        side_title = QLabel("Noite 2.0")
        side_title.setObjectName("sideTitle")
        side_layout.addWidget(side_title)
        side_layout.addSpacing(16)
        self._side_section(side_layout, "PROJETO")
        project = QLabel("▱   Noite 2.0")
        project.setObjectName("projectTile")
        project.setMinimumHeight(40)
        side_layout.addWidget(project)
        self._side_section(side_layout, "CONVERSAS")
        conversation = QLabel("◦   Conversa local")
        conversation.setObjectName("conversationTile")
        conversation.setMinimumHeight(36)
        side_layout.addWidget(conversation)
        self._side_section(side_layout, "FERRAMENTAS")
        self.mcp_button = QPushButton("◇   Ferramentas MCP")
        self.mcp_button.setObjectName("sideButton")
        self.mcp_button.setMinimumHeight(38)
        self.mcp_button.setToolTip("Configurar e aprovar chamadas MCP")
        self.mcp_button.clicked.connect(self._open_mcp_dialog)
        side_layout.addWidget(self.mcp_button)
        side_layout.addStretch(1)
        local_note = QLabel("Local-first\nConversas salvas neste computador")
        local_note.setObjectName("sideNote")
        local_note.setWordWrap(True)
        side_layout.addWidget(local_note)
        shell.addWidget(sidebar)

        main = QWidget()
        main.setObjectName("mainPane")
        layout = QVBoxLayout(main)
        layout.setContentsMargins(28, 20, 28, 18)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Noite 2.0")
        title.setObjectName("title")
        self.status_label = QLabel("Verificando Ollama…")
        self.status_label.setObjectName("status")
        header.addWidget(title)
        header.addStretch(1)
        model_label = QLabel("Modelo")
        model_label.setObjectName("muted")
        header.addWidget(model_label)
        self.model_box = QComboBox()
        self.model_box.setEditable(True)
        self.model_box.addItem(self.settings.local_model)
        self.model_box.setMinimumWidth(172)
        self.model_box.setToolTip("Modelo usado nesta sessão")
        header.addWidget(self.model_box)
        header.addWidget(self.status_label)
        layout.addLayout(header)

        self.welcome = QFrame()
        self.welcome.setObjectName("welcome")
        welcome_layout = QVBoxLayout(self.welcome)
        welcome_layout.setContentsMargins(20, 32, 20, 32)
        welcome_layout.setSpacing(12)
        welcome_layout.addStretch(1)
        welcome_mark = QLabel("☾")
        welcome_mark.setObjectName("welcomeMark")
        welcome_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_layout.addWidget(welcome_mark)
        welcome_title = QLabel("O que vamos fazer em Noite 2.0?")
        welcome_title.setObjectName("welcomeTitle")
        welcome_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_layout.addWidget(welcome_title)
        welcome_hint = QLabel("Seu assistente local está pronto. Escreva para começar.")
        welcome_hint.setObjectName("welcomeHint")
        welcome_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_layout.addWidget(welcome_hint)
        welcome_layout.addStretch(1)
        layout.addWidget(self.welcome, 1)

        self.chat = QTextBrowser()
        self.chat.setOpenExternalLinks(False)
        self.chat.setObjectName("chat")
        self.chat.hide()
        layout.addWidget(self.chat, 1)

        composer = QFrame()
        composer.setObjectName("composer")
        composer_layout = QVBoxLayout(composer)
        composer_layout.setContentsMargins(14, 10, 14, 10)
        composer_layout.setSpacing(8)
        composer_head = QHBoxLayout()
        composer_project = QLabel("▱   Noite 2.0")
        composer_project.setObjectName("composerProject")
        composer_head.addWidget(composer_project)
        composer_head.addStretch(1)
        self.progress = QLabel("Pronta")
        self.progress.setObjectName("progress")
        composer_head.addWidget(self.progress)
        composer_layout.addLayout(composer_head)

        compose = QHBoxLayout()
        compose.setSpacing(10)
        self.input = InputBox()
        self.input.setObjectName("input")
        self.input.setPlaceholderText("Pergunte qualquer coisa à Noite…")
        self.input.setFixedHeight(74)
        self.input.send_requested.connect(self.send_message)
        self.send_button = QPushButton("↑")
        self.send_button.setObjectName("sendButton")
        self.send_button.setAccessibleName("Enviar mensagem")
        self.send_button.setFixedSize(42, 42)
        self.send_button.setDefault(True)
        self.send_button.clicked.connect(self.send_message)
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setObjectName("cancelButton")
        self.cancel_button.clicked.connect(self.cancel_generation)
        self.cancel_button.hide()
        compose.addWidget(self.input, 1)
        compose.addWidget(self.send_button)
        compose.addWidget(self.cancel_button)
        composer_layout.addLayout(compose)
        layout.addWidget(composer)
        footer = QLabel(
            "Enter envia  ·  Shift+Enter quebra linha  ·  Ferramentas MCP exigem aprovação"
        )
        footer.setObjectName("footerHint")
        layout.addWidget(footer)
        shell.addWidget(main, 1)
        self.setCentralWidget(root)
        self.setStyleSheet(
            "QWidget { background: #171719; color: #ededf0; font-size: 13px; }"
            "QLabel { background: transparent; }"
            "QWidget#iconRail { background: #17191d; border-right: 1px solid #2c2d31; }"
            "QWidget#sidebar { background: #1d1d20; border-right: 1px solid #303035; }"
            "QWidget#mainPane { background: #171719; }"
            "QLabel#brandMark { background: #31343a; color: #f4f4f5; border-radius: 11px; "
            "font-size: 17px; font-weight: 700; }"
            "QLabel#railGlyph { color: #96979d; font-size: 18px; padding: 6px 0; }"
            "QLabel#sideTitle { font-size: 19px; font-weight: 650; }"
            "QLabel#sectionLabel { color: #92939a; font-size: 10px; font-weight: 700; "
            "padding-top: 14px; letter-spacing: 1px; }"
            "QLabel#projectTile { background: #303136; border-radius: 8px; padding: 0 10px; "
            "font-weight: 600; }"
            "QLabel#conversationTile { color: #c6c6cb; padding: 0 10px; }"
            "QPushButton#sideButton { background: transparent; color: #c6c6cb; text-align: left; "
            "border: 0; border-radius: 8px; padding: 0 10px; }"
            "QPushButton#sideButton:hover { background: #2b2b30; color: white; }"
            "QLabel#sideNote, QLabel#footerHint, QLabel#muted { color: #92939a; }"
            "QLabel#sideNote { border-top: 1px solid #303035; padding-top: 12px; font-size: 11px; }"
            "QLabel#title { font-size: 18px; font-weight: 650; }"
            "QLabel#status { color: #8ecda9; background: #202a24; border-radius: 11px; "
            "padding: 6px 10px; font-size: 11px; }"
            "QLabel#progress { color: #a5a5ac; font-size: 11px; }"
            "QLabel#welcomeMark { color: #829bc8; font-size: 40px; }"
            "QLabel#welcomeTitle { color: #f0f0f2; font-size: 28px; font-weight: 500; }"
            "QLabel#welcomeHint { color: #96969e; font-size: 14px; }"
            "QFrame#composer { background: #292a2d; border: 1px solid #3a3b40; "
            "border-radius: 16px; }"
            "QLabel#composerProject { color: #e4e4e8; font-weight: 600; }"
            "QTextBrowser { background: transparent; border: 0; padding: 8px 14px; "
            "selection-background-color: #435f91; }"
            "QPlainTextEdit#input { background: transparent; border: 0; padding: 8px 4px; "
            "selection-background-color: #435f91; }"
            "QComboBox { background: #27282c; border: 1px solid #3a3b40; border-radius: 8px; "
            "padding: 6px 10px; }"
            "QPushButton#sendButton { background: #496fa9; color: white; border: 0; "
            "border-radius: 21px; font-size: 22px; font-weight: 600; }"
            "QPushButton#sendButton:hover { background: #5b82bd; }"
            "QPushButton#cancelButton { background: #44454a; border: 0; border-radius: 8px; "
            "padding: 10px 14px; }"
            "QPushButton:disabled { background: #414248; color: #a5a5ab; }"
            "QLabel#footerHint { font-size: 10px; padding-left: 4px; }"
        )

    @staticmethod
    def _rail_glyph(text: str, accessible_name: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("railGlyph")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setToolTip(accessible_name)
        label.setFixedHeight(32)
        return label

    @staticmethod
    def _side_section(layout: QVBoxLayout, text: str) -> None:
        label = QLabel(text)
        label.setObjectName("sectionLabel")
        layout.addWidget(label)

    def _append_message(self, role: str, content: str) -> None:
        welcome = getattr(self, "welcome", None)
        if welcome is not None:
            welcome.hide()
            self.chat.show()
        safe = html.escape(content).replace("\n", "<br>")
        if role == "user":
            self.chat.append(
                f'<p style="margin:18px 0 4px"><b style="color:#9bb8eb">Você</b></p>'
                f'<p style="margin:0 0 12px; color:#e4e4e8">{safe}</p>'
            )
        else:
            self.chat.append(
                f'<p style="margin:18px 0 4px"><b style="color:#a8c2ee">Noite</b></p>'
                f'<p style="margin:0 0 12px; color:#e4e4e8">{safe}</p>'
            )

    def _load_history(self) -> None:
        with closing(open_database(self.service.database_path)) as connection:
            messages = recent_messages(connection, self.conversation_id, limit=50)
        for role, content in messages:
            self._append_message(role, content)

    def _check_status(self) -> None:
        self._start_worker(
            lambda _worker: self.service.model_status(),
            completed=lambda value: self.status_label.setText(str(value)),
            failed=lambda _error: self.status_label.setText("Estado indisponível"),
        )

    def _start_worker(
        self,
        task: Callable[[TaskThread], object],
        *,
        completed: Callable[[object], None] | None = None,
        failed: Callable[[str], None] | None = None,
        cancelled: Callable[[], None] | None = None,
        streamed: Callable[[str], None] | None = None,
        finished: Callable[[], None] | None = None,
    ) -> TaskThread:
        worker = None
        worker = TaskThread(lambda: task(worker), self)
        self._workers.add(worker)
        if completed is not None:
            worker.completed.connect(completed)
        if failed is not None:
            worker.failed.connect(failed)
        if cancelled is not None:
            worker.cancelled.connect(cancelled)
        if streamed is not None:
            worker.streamed.connect(streamed)
        worker.finished.connect(lambda current=worker: self._worker_finished(current))
        if finished is not None:
            worker.finished.connect(finished)
        worker.start()
        return worker

    def _worker_finished(self, worker: TaskThread) -> None:
        self._workers.discard(worker)
        if self.worker is worker:
            self.worker = None
        worker.deleteLater()
        if self._close_when_idle and not self._workers:
            QTimer.singleShot(0, self.close)

    def send_message(self) -> None:
        text = self.input.toPlainText().strip()
        if not text or (self.worker is not None and self.worker.isRunning()):
            return
        self.input.clear()
        self._append_message("user", text)
        self.send_button.setEnabled(False)
        self.progress.setText("A Noite está pensando…")
        model = self.model_box.currentText().strip() or self.settings.local_model
        self.service = AssistantService(self.settings, model=model)
        self._streaming_response_active = False
        self._streaming_response_text = ""
        self.cancel_button.setEnabled(True)
        self.cancel_button.show()
        self.worker = self._start_worker(
            lambda worker: self.service.respond(text, on_chunk=worker.streamed.emit),
            completed=self._on_response,
            failed=self._on_error,
            cancelled=self._on_cancelled,
            streamed=self._on_stream_chunk,
            finished=self._generation_finished,
        )

    def _generation_finished(self) -> None:
        self.send_button.setEnabled(True)
        self.cancel_button.hide()

    def cancel_generation(self) -> None:
        if self.worker is None or not self.worker.isRunning():
            return
        self.cancel_button.setEnabled(False)
        self.progress.setText("Cancelando geração…")
        self.worker.request_cancel()

    def _on_stream_chunk(self, chunk: str) -> None:
        if not self._streaming_response_active:
            self._append_message("assistant", "")
            self._streaming_response_active = True
        self._streaming_response_text += chunk
        cursor = self.chat.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(chunk)
        self.chat.setTextCursor(cursor)
        self.chat.ensureCursorVisible()

    def _on_response(self, response: object) -> None:
        if self._streaming_response_active:
            self._streaming_response_active = False
            self._streaming_response_text = ""
        else:
            self._append_message("assistant", str(response))
        self.progress.setText("Pronta")

    def _on_error(self, message: str) -> None:
        self._append_message("assistant", message)
        self._streaming_response_active = False
        self._streaming_response_text = ""
        self.progress.setText("A solicitação falhou; você pode tentar novamente.")

    def _on_cancelled(self) -> None:
        if self._streaming_response_active:
            cursor = self.chat.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText("\n[Geração cancelada]")
            self.chat.setTextCursor(cursor)
        self._streaming_response_active = False
        self._streaming_response_text = ""
        self.progress.setText("Geração cancelada. Você pode enviar outra mensagem.")

    def _open_mcp_dialog(self) -> None:
        dialog = MCPDialog(self.settings.data_dir, self)
        dialog.exec()

    def closeEvent(self, event) -> None:
        running = [worker for worker in self._workers if worker.isRunning()]
        if running:
            self._close_when_idle = True
            self.input.setEnabled(False)
            self.send_button.setEnabled(False)
            self.cancel_button.setEnabled(False)
            self.mcp_button.setEnabled(False)
            self.progress.setText("Cancelando as operações para fechar com segurança…")
            for worker in running:
                worker.request_cancel()
            event.ignore()
            return
        event.accept()


class MCPDialog(QDialog):
    """Configura servidores MCP locais e exige aprovação antes de cada chamada."""

    def __init__(self, data_dir: Path, parent=None) -> None:
        super().__init__(parent)
        self.data_dir = Path(data_dir)
        self.config_path = self.data_dir / "mcp_servers.json"
        self.servers: dict[str, dict[str, object]] = self._load_servers()
        self.worker: TaskThread | None = None
        self._close_when_idle = False
        self.setWindowTitle("Ferramentas MCP")
        self.resize(640, 560)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("ex.: arquivos-local")
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("caminho do executável do servidor")
        self.args_input = QLineEdit("[]")
        self.args_input.setPlaceholderText('["arg1", "arg2"]')
        form.addRow("Nome", self.name_input)
        form.addRow("Executável", self.command_input)
        form.addRow("Argumentos (JSON)", self.args_input)
        layout.addLayout(form)

        row = QHBoxLayout()
        self.server_box = QComboBox()
        self.discover_button = QPushButton("Salvar e descobrir ferramentas")
        self.discover_button.clicked.connect(self._discover)
        row.addWidget(self.server_box, 1)
        row.addWidget(self.discover_button)
        layout.addLayout(row)

        self.tools = QListWidget()
        layout.addWidget(self.tools, 1)
        layout.addWidget(QLabel("Argumentos da ferramenta (objeto JSON):"))
        self.arguments_input = QPlainTextEdit("{}")
        self.arguments_input.setMaximumHeight(100)
        layout.addWidget(self.arguments_input)
        self.result = QPlainTextEdit()
        self.result.setReadOnly(True)
        self.result.setPlaceholderText("Resultado da chamada aparecerá aqui.")
        layout.addWidget(self.result, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        self.call_button = buttons.addButton("Chamar ferramenta…", QDialogButtonBox.ActionRole)
        self.call_button.clicked.connect(self._call_selected)
        buttons.rejected.connect(self.close)
        layout.addWidget(buttons)
        self.server_box.currentTextChanged.connect(self._show_server_config)
        self._refresh_servers()

    def _load_servers(self) -> dict[str, dict[str, object]]:
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return {}
            return {
                name: value
                for name, value in data.items()
                if isinstance(name, str)
                and isinstance(value, dict)
                and isinstance(value.get("command"), str)
                and isinstance(value.get("args", []), list)
                and all(isinstance(arg, str) for arg in value.get("args", []))
            }
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_servers(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.config_path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(self.servers, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary.replace(self.config_path)

    def _refresh_servers(self) -> None:
        current = self.server_box.currentText()
        self.server_box.blockSignals(True)
        self.server_box.clear()
        self.server_box.addItems(sorted(self.servers))
        if current in self.servers:
            self.server_box.setCurrentText(current)
        self.server_box.blockSignals(False)
        self._show_server_config(self.server_box.currentText())

    def _show_server_config(self, name: str) -> None:
        config = self.servers.get(name, {})
        self.name_input.setText(name)
        self.command_input.setText(str(config.get("command", "")))
        self.args_input.setText(json.dumps(config.get("args", []), ensure_ascii=False))
        self.tools.clear()

    def _read_server_form(self) -> tuple[str, str, list[str]]:
        name = self.name_input.text().strip()
        command = self.command_input.text().strip()
        try:
            args = json.loads(self.args_input.text())
        except json.JSONDecodeError as exc:
            raise ValueError("Os argumentos precisam ser uma lista JSON de textos.") from exc
        if not name or not command or not isinstance(args, list) or not all(
            isinstance(arg, str) for arg in args
        ):
            raise ValueError("Informe nome, executável e uma lista JSON de argumentos.")
        return name, command, args

    def _discover(self) -> None:
        try:
            name, command, args = self._read_server_form()
        except ValueError as exc:
            QMessageBox.warning(self, "Configuração inválida", str(exc))
            return
        approved = QMessageBox.question(
            self,
            "Iniciar servidor MCP",
            "Iniciar este processo local para descobrir ferramentas?\n\n"
            f"{name}\n{command} {shlex.join(args)}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if approved != QMessageBox.Yes:
            return
        self.servers[name] = {"command": command, "args": args}
        self._save_servers()
        self._refresh_servers()
        self.server_box.setCurrentText(name)
        self._set_busy(True)
        self.result.setPlainText("Conectando e consultando a lista de ferramentas…")
        from .mcp_client import MCPClient, MCPServer

        server = MCPServer(name, command, tuple(args))
        self.worker = TaskThread(lambda: MCPClient().discover_tools(server), self)
        self.worker.completed.connect(self._show_tools)
        self.worker.failed.connect(lambda message: self.result.setPlainText(message))
        self.worker.finished.connect(self._task_finished)
        self.worker.start()

    def _show_tools(self, items: object) -> None:
        self.tools.clear()
        for tool in items:
            description = str(tool.get("description", ""))
            item = QListWidgetItem(f"{tool['name']} — {description}".strip(" —"))
            item.setData(Qt.UserRole, tool)
            self.tools.addItem(item)
        self.result.setPlainText(
            "Selecione uma ferramenta, informe os argumentos e aprove a chamada."
        )

    def _call_selected(self) -> None:
        item = self.tools.currentItem()
        name = self.server_box.currentText()
        if item is None or name not in self.servers:
            QMessageBox.information(
                self, "Seleção necessária", "Escolha um servidor e uma ferramenta."
            )
            return
        try:
            arguments = json.loads(self.arguments_input.toPlainText())
        except json.JSONDecodeError:
            QMessageBox.warning(
                self, "JSON inválido", "Os argumentos precisam ser um objeto JSON válido."
            )
            return
        if not isinstance(arguments, dict):
            QMessageBox.warning(self, "JSON inválido", "Os argumentos precisam ser um objeto JSON.")
            return
        tool = item.data(Qt.UserRole)
        if QMessageBox.question(
            self,
            "Aprovar chamada MCP",
            "O servidor receberá esta chamada e estes argumentos. "
            "Respostas do servidor são dados não confiáveis.\n\n"
            f"Servidor: {name}\nFerramenta: {tool['name']}\n"
            f"Argumentos: {json.dumps(arguments, ensure_ascii=False)}\n\nAutorizar agora?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        from .mcp_client import MCPClient, MCPServer

        config = self.servers[name]
        server = MCPServer(
            name,
            str(config["command"]),
            tuple(config.get("args", [])),
            frozenset({str(tool["name"])}),
        )
        self._set_busy(True)
        self.result.setPlainText("Executando a chamada aprovada…")
        self.worker = TaskThread(
            lambda: MCPClient().call_tool(server, str(tool["name"]), arguments), self
        )
        self.worker.completed.connect(
            lambda result: self.result.setPlainText("\n".join(map(str, result)))
        )
        self.worker.failed.connect(lambda message: self.result.setPlainText(message))
        self.worker.finished.connect(self._task_finished)
        self.worker.start()

    def _set_busy(self, busy: bool) -> None:
        self.discover_button.setEnabled(not busy)
        self.call_button.setEnabled(not busy)

    def _task_finished(self) -> None:
        self._set_busy(False)
        if self.worker is not None:
            self.worker.deleteLater()
            self.worker = None
        if self._close_when_idle:
            QTimer.singleShot(0, self.close)

    def closeEvent(self, event) -> None:
        if self.worker is not None and self.worker.isRunning():
            self._close_when_idle = True
            self.setEnabled(False)
            self.result.setPlainText("Cancelando a operação MCP para fechar com segurança…")
            self.worker.request_cancel()
            event.ignore()
            return
        event.accept()


def run_gui() -> int:
    app = QApplication.instance() or QApplication([])
    window = NoiteWindow()
    window.show()
    return app.exec()
