from __future__ import annotations

import asyncio
import html
from collections.abc import Callable
from contextlib import closing

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
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
        self.worker = TaskThread(self.service.model_status, self)
        self.worker.completed.connect(lambda value: self.status_label.setText(str(value)))
        self.worker.failed.connect(lambda _error: self.status_label.setText("Estado indisponível"))
        self.worker.start()

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
        self.worker = TaskThread(lambda: asyncio.run(self.service.respond(text)), self)
        self.worker.completed.connect(self._on_response)
        self.worker.failed.connect(self._on_error)
        self.worker.finished.connect(lambda: self.send_button.setEnabled(True))
        self.worker.start()

    def _on_response(self, response: object) -> None:
        self._append_message("assistant", str(response))
        self.progress.setText("Pronta")

    def _on_error(self, message: str) -> None:
        self._append_message("assistant", message)
        self.progress.setText("A solicitação falhou; você pode tentar novamente.")


def run_gui() -> int:
    app = QApplication.instance() or QApplication([])
    window = NoiteWindow()
    window.show()
    return app.exec()
