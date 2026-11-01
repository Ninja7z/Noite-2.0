from __future__ import annotations

import asyncio
import html
import json
import shlex
from collections.abc import Callable
from contextlib import closing
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
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

    def __init__(self, task: Callable[[], object], parent=None) -> None:
        super().__init__(parent)
        self.task = task

    def run(self) -> None:
        try:
            self.completed.emit(self.task())
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: não foi possível concluir a operação.")


class NoiteWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = get_settings()
        self.service = AssistantService(self.settings)
        self.conversation_id = "default"
        self.worker: TaskThread | None = None
        self._workers: set[TaskThread] = set()
        self._close_when_idle = False
        self.setWindowTitle("Noite 2.0")
        self.resize(900, 680)
        self._build_ui()
        self._load_history()
        self._check_status()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("Noite")
        title.setObjectName("title")
        self.status_label = QLabel("Verificando Ollama…")
        self.status_label.setObjectName("status")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(QLabel("Modelo"))
        self.model_box = QComboBox()
        self.model_box.setEditable(True)
        self.model_box.addItem(self.settings.local_model)
        self.model_box.setMinimumWidth(180)
        self.model_box.setToolTip("Modelo usado nesta sessão")
        header.addWidget(self.model_box)
        header.addWidget(self.status_label)
        self.mcp_button = QPushButton("Ferramentas MCP")
        self.mcp_button.clicked.connect(self._open_mcp_dialog)
        header.addWidget(self.mcp_button)
        layout.addLayout(header)

        self.chat = QTextBrowser()
        self.chat.setOpenExternalLinks(False)
        self.chat.setObjectName("chat")
        layout.addWidget(self.chat, 1)

        compose = QHBoxLayout()
        self.input = InputBox()
        self.input.setPlaceholderText(
            "Converse com a Noite… (Enter envia, Shift+Enter quebra linha)"
        )
        self.input.setFixedHeight(86)
        self.input.send_requested.connect(self.send_message)
        self.send_button = QPushButton("Enviar")
        self.send_button.setDefault(True)
        self.send_button.clicked.connect(self.send_message)
        compose.addWidget(self.input, 1)
        compose.addWidget(self.send_button)
        layout.addLayout(compose)

        self.progress = QLabel("Local-first · conversas salvas neste computador")
        self.progress.setObjectName("progress")
        layout.addWidget(self.progress)
        self.setCentralWidget(root)
        self.setStyleSheet(
            "QMainWindow, QWidget { background: #10131a; color: #e8eaf0; font-size: 14px; }"
            "QLabel#title { font-size: 25px; font-weight: 700; color: #c8b6ff; }"
            "QLabel#status, QLabel#progress { color: #a4adbd; }"
            "QTextBrowser, QPlainTextEdit, QComboBox { background: #191e28; "
            "border: 1px solid #303849; "
            "border-radius: 10px; padding: 10px; selection-background-color: #6251a8; }"
            "QPushButton { background: #8068d8; border: 0; border-radius: 9px; padding: 12px 20px; "
            "font-weight: 600; } QPushButton:hover { background: #947fea; }"
            "QPushButton:disabled { background: #424652; color: #b1b5c0; }"
        )

    def _append_message(self, role: str, content: str) -> None:
        safe = html.escape(content).replace("\n", "<br>")
        if role == "user":
            self.chat.append(
                f'<p style="margin:14px 0 4px"><b style="color:#b6a4ff">Você</b></p>'
                f'<p style="margin:0 0 12px">{safe}</p>'
            )
        else:
            self.chat.append(
                f'<p style="margin:14px 0 4px"><b style="color:#7ddbb3">Noite</b></p>'
                f'<p style="margin:0 0 12px">{safe}</p>'
            )

    def _load_history(self) -> None:
        with closing(open_database(self.service.database_path)) as connection:
            messages = recent_messages(connection, self.conversation_id, limit=50)
        for role, content in messages:
            self._append_message(role, content)

    def _check_status(self) -> None:
        worker = self._start_worker(self.service.model_status)
        worker.completed.connect(lambda value: self.status_label.setText(str(value)))
        worker.failed.connect(lambda _error: self.status_label.setText("Estado indisponível"))

    def _start_worker(self, task: Callable[[], object]) -> TaskThread:
        worker = TaskThread(task, self)
        self._workers.add(worker)
        worker.finished.connect(lambda current=worker: self._worker_finished(current))
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
        self.worker = self._start_worker(lambda: asyncio.run(self.service.respond(text)))
        self.worker.completed.connect(self._on_response)
        self.worker.failed.connect(self._on_error)
        self.worker.finished.connect(lambda: self.send_button.setEnabled(True))

    def _on_response(self, response: object) -> None:
        self._append_message("assistant", str(response))
        self.progress.setText("Pronta")

    def _on_error(self, message: str) -> None:
        self._append_message("assistant", message)
        self.progress.setText("A solicitação falhou; você pode tentar novamente.")

    def _open_mcp_dialog(self) -> None:
        dialog = MCPDialog(self.settings.data_dir, self)
        dialog.exec()

    def closeEvent(self, event) -> None:
        running = [worker for worker in self._workers if worker.isRunning()]
        if running:
            self._close_when_idle = True
            self.input.setEnabled(False)
            self.send_button.setEnabled(False)
            self.mcp_button.setEnabled(False)
            self.progress.setText("Aguardando as operações em andamento para fechar com segurança…")
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
        self.worker = TaskThread(lambda: asyncio.run(MCPClient().discover_tools(server)), self)
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
            lambda: asyncio.run(MCPClient().call_tool(server, str(tool["name"]), arguments)),
            self,
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
            self.result.setPlainText("Aguardando a operação MCP para fechar com segurança…")
            event.ignore()
            return
        event.accept()


def run_gui() -> int:
    app = QApplication.instance() or QApplication([])
    window = NoiteWindow()
    window.show()
    return app.exec()
