from __future__ import annotations

import asyncio
import html
import logging
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .activity import ActivityEvent
from .assistant import AssistantService
from .config import get_settings
from .logging_setup import setup_logging

logger = logging.getLogger("noite.mascot")


class AssistantWorker(QThread):
    chunk = Signal(str)
    activity = Signal(object)
    completed = Signal(str)
    failed = Signal(str)

    def __init__(self, service: AssistantService, conversation_id: str, prompt: str):
        super().__init__()
        self.service = service
        self.conversation_id = conversation_id
        self.prompt = prompt

    def run(self) -> None:
        try:
            answer = asyncio.run(
                self.service.respond(
                    self.prompt,
                    conversation_id=self.conversation_id,
                    on_chunk=self.chunk.emit,
                    on_activity=self.activity.emit,
                )
            )
            self.completed.emit(answer)
        except Exception as exc:
            logger.error("Mascot request failed (%s)", type(exc).__name__)
            self.failed.emit(f"Não consegui concluir. Falha: {type(exc).__name__}.")


class DiagnosticsWorker(QThread):
    completed = Signal(object)

    def __init__(self, service: AssistantService):
        super().__init__()
        self.service = service

    def run(self) -> None:
        try:
            self.completed.emit(self.service.model_diagnostics())
        except Exception as exc:
            self.completed.emit({"server": "down", "message": type(exc).__name__})


class MascotFace(QWidget):
    """Original pixel-art robot face. Drawn from integer pixel clusters."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(112, 116)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.state = "idle"
        self._blink = False
        self._phase = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(650)

    def set_state(self, state: str) -> None:
        self.state = state
        self.update()

    def _animate(self) -> None:
        self._phase = (self._phase + 1) % 8
        self._blink = self._phase == 0
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        side = min(self.width(), self.height())
        scale = max(1, side // 30)
        x0 = (self.width() - 26 * scale) // 2
        y0 = (self.height() - 27 * scale) // 2

        def px(x: int, y: int, w: int, h: int, color: str) -> None:
            painter.fillRect(
                QRect(x0 + x * scale, y0 + y * scale, w * scale, h * scale), QColor(color)
            )

        # Antenna and side audio/ear modules.
        px(12, 0, 2, 2, "#26334f")
        px(11, 1, 4, 1, "#9fb8ee")
        px(2, 8, 2, 9, "#26334f")
        px(22, 8, 2, 9, "#26334f")
        px(1, 10, 2, 5, "#37c8ff")
        px(23, 10, 2, 5, "#37c8ff")
        # White helmet silhouette.
        px(7, 3, 12, 1, "#202a43")
        px(4, 4, 18, 1, "#202a43")
        px(3, 5, 20, 2, "#dce6ff")
        px(2, 7, 22, 11, "#202a43")
        px(3, 18, 20, 2, "#202a43")
        px(5, 20, 16, 1, "#202a43")
        px(5, 5, 16, 1, "#ffffff")
        px(4, 6, 18, 2, "#f8faff")
        px(3, 8, 20, 9, "#f8faff")
        px(4, 17, 18, 2, "#f8faff")
        px(6, 19, 14, 1, "#c9d6f5")
        px(6, 7, 14, 1, "#c8d6f8")
        # Dark glass visor.
        px(5, 8, 16, 9, "#111a31")
        px(6, 8, 14, 1, "#263454")
        px(6, 16, 14, 1, "#1e2a49")
        px(7, 9, 12, 6, "#0b1328")
        px(8, 9, 2, 1, "#34466e")
        # Eyes: expressions follow the activity state.
        eye = "#69e8ff" if self.state in {"working", "thinking"} else "#46bfff"
        if self.state == "error":
            eye = "#ff708e"
        if self.state == "done":
            eye = "#7cf4bd"
        if self._blink:
            px(8, 12, 3, 1, eye)
            px(15, 12, 3, 1, eye)
        elif self.state == "thinking":
            px(8, 10, 3, 4, eye)
            px(15, 9, 3, 4, eye)
        elif self.state == "error":
            px(8, 10, 3, 3, eye)
            px(15, 10, 3, 3, eye)
            px(8, 9, 1, 1, eye)
            px(17, 9, 1, 1, eye)
        elif self.state == "done":
            px(8, 11, 3, 2, eye)
            px(15, 11, 3, 2, eye)
        else:
            px(8, 10, 3, 4, eye)
            px(15, 10, 3, 4, eye)
        # Body, shoulder plates, arms and feet.
        px(8, 21, 10, 1, "#202a43")
        px(7, 22, 12, 4, "#202a43")
        px(8, 22, 10, 3, "#f3f6ff")
        px(5, 22, 2, 3, "#202a43")
        px(4, 23, 3, 2, "#dce6ff")
        px(20, 22, 2, 3, "#202a43")
        px(19, 23, 3, 2, "#dce6ff")
        px(10, 23, 1, 2, "#4dcfff")
        px(15, 23, 1, 2, "#4dcfff")
        px(8, 26, 4, 1, "#202a43")
        px(14, 26, 4, 1, "#202a43")
        px(7, 27, 5, 1, "#aebde0")
        px(14, 27, 5, 1, "#aebde0")
        # Small status pixel on chest.
        px(12, 24, 2, 1, eye)
        painter.end()


class MascotWindow(QWidget):
    """Floating Noite companion with a compact chat/activity panel."""

    def __init__(self, service: AssistantService):
        super().__init__()
        self.service = service
        self.conversation_id = service.active_conversation_id()
        self.worker: AssistantWorker | None = None
        self.diagnostics_worker: DiagnosticsWorker | None = None
        self._drag_offset: QPoint | None = None
        self._drag_start_position: QPoint | None = None
        self._close_pending = False
        self._stream_text = ""
        self._state = "idle"
        self.setObjectName("noiteMascotWindow")
        self.setWindowTitle("Noite 2.0")
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumWidth(180)
        self.setMaximumWidth(390)
        self.setFixedWidth(180)
        self.setMinimumHeight(180)
        self.setStyleSheet("""
            QWidget#noiteMascotWindow { background: transparent; color: #eef5ff; }
            QFrame#shell { background: #111827; border: 1px solid #344b70; border-radius: 18px; }
            QLabel#title { color: #f2f7ff; font-size: 13px; font-weight: 700; }
            QLabel#status { color: #8fa9ce; font-size: 10px; }
            QLabel#activity { color: #8bdfff; font-size: 10px; }
            QTextBrowser { background: #0b1220; border: 1px solid #293c5a; border-radius: 10px;
                color: #dce9ff; padding: 8px; font-size: 11px; }
            QLineEdit { background: #0b1220; border: 1px solid #354b70; border-radius: 11px;
                padding: 8px 10px; color: #f2f7ff; }
            QPushButton { background: #20375a; border: 1px solid #3b5c89; border-radius: 10px;
                color: #f2f7ff; padding: 6px 10px; }
            QPushButton:hover { background: #2d4d79; }
            QPushButton#close {
                background: transparent; border: 0; color: #9eb4d5; font-size: 15px;
            }
        """)
        self._build_ui()
        self._restore_position()
        self._set_state("idle", "Pronta")
        self.refresh_diagnostics()
        self.diagnostics_timer = QTimer(self)
        self.diagnostics_timer.timeout.connect(self.refresh_diagnostics)
        self.diagnostics_timer.start(30_000)

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.shell = QFrame()
        self.shell.setObjectName("shell")
        outer.addWidget(self.shell)
        self.layout = QVBoxLayout(self.shell)
        self.layout.setContentsMargins(10, 9, 10, 10)
        self.layout.setSpacing(7)

        top = QHBoxLayout()
        self.face = MascotFace()
        self.face.setFixedSize(124, 124)
        top.addWidget(self.face)
        top.addStretch(1)
        self.close_button = QPushButton("×")
        self.close_button.setObjectName("close")
        self.close_button.setFixedSize(25, 25)
        self.close_button.setToolTip("Sair da Noite")
        self.close_button.clicked.connect(self.close)
        top.addWidget(self.close_button, 0, Qt.AlignmentFlag.AlignTop)
        self.layout.addLayout(top)
        self.status = QLabel("Iniciando…")
        self.status.setObjectName("status")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.activity = QLabel("Aguardando")
        self.activity.setObjectName("activity")
        self.activity.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.activity.setWordWrap(True)
        self.layout.addWidget(self.status)
        self.layout.addWidget(self.activity)

        self.panel = QWidget()
        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(6)
        self.transcript = QTextBrowser()
        self.transcript.setMinimumHeight(155)
        self.transcript.setMaximumHeight(250)
        self.transcript.setOpenExternalLinks(False)
        self.transcript.setPlaceholderText("A Noite está aqui. Pode mandar.")
        panel_layout.addWidget(self.transcript)
        compose = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Fale com a Noite…")
        self.input.returnPressed.connect(self.send_message)
        self.send_button = QPushButton("Enviar")
        self.send_button.clicked.connect(self.send_message)
        compose.addWidget(self.input, 1)
        compose.addWidget(self.send_button)
        panel_layout.addLayout(compose)
        controls = QHBoxLayout()
        self.hide_panel_button = QPushButton("Recolher")
        self.hide_panel_button.clicked.connect(self.collapse)
        controls.addStretch(1)
        controls.addWidget(self.hide_panel_button)
        panel_layout.addLayout(controls)
        self.layout.addWidget(self.panel)
        self.panel.hide()
        self._expanded = False
        self.face.mousePressEvent = self._face_pressed
        self.face.mouseMoveEvent = self._face_move
        self.face.mouseReleaseEvent = self._face_release

    def _restore_position(self) -> None:
        from PySide6.QtCore import QSettings

        settings = QSettings("Noite2", "Mascot")
        x = settings.value("x", None)
        y = settings.value("y", None)
        if x is not None and y is not None:
            self.move(int(x), int(y))
        else:
            screen = QApplication.primaryScreen()
            area = screen.availableGeometry() if screen else QRect(0, 0, 1280, 720)
            self.move(area.right() - 175, area.bottom() - 180)

    def _save_position(self) -> None:
        from PySide6.QtCore import QSettings

        settings = QSettings("Noite2", "Mascot")
        settings.setValue("x", self.x())
        settings.setValue("y", self.y())

    def _face_pressed(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._drag_start_position = self.pos()
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self.close()

    def _face_move(self, event) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def _face_release(self, event) -> None:
        start = self._drag_start_position
        self._drag_offset = None
        self._drag_start_position = None
        if start is not None and (self.pos() - start).manhattanLength() <= 3:
            self.toggle_panel()
        self._save_position()
        event.accept()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_offset = None
        self._save_position()
        super().mouseReleaseEvent(event)

    def toggle_panel(self) -> None:
        self.expand() if not self._expanded else self.collapse()

    def expand(self) -> None:
        self._expanded = True
        self.panel.show()
        self.setFixedWidth(370)
        self.setMinimumHeight(390)
        self.input.setFocus()
        self.adjustSize()
        screen = (
            QApplication.screenAt(self.frameGeometry().center()) or QApplication.primaryScreen()
        )
        if screen is not None:
            area = screen.availableGeometry()
            x = min(self.x(), area.right() - self.width())
            y = min(self.y(), area.bottom() - self.height())
            self.move(max(area.left(), x), max(area.top(), y))

    def collapse(self) -> None:
        self._expanded = False
        self.panel.hide()
        self.setFixedWidth(180)
        self.setMinimumHeight(180)
        self.adjustSize()
        self._save_position()

    def _set_state(self, state: str, label: str) -> None:
        self._state = state
        self.face.set_state(state)
        self.status.setText(label)

    def refresh_diagnostics(self) -> None:
        if self.diagnostics_worker is not None:
            try:
                if self.diagnostics_worker.isRunning():
                    return
            except RuntimeError:
                pass
            self.diagnostics_worker = None
        worker = DiagnosticsWorker(self.service)
        self.diagnostics_worker = worker
        worker.completed.connect(self._diagnostics_ready)
        worker.finished.connect(self._diagnostics_finished)
        worker.start()

    def _diagnostics_finished(self) -> None:
        worker = self.sender()
        if worker is self.diagnostics_worker:
            self.diagnostics_worker = None
        if worker is not None:
            worker.deleteLater()
        self._maybe_close()

    def _diagnostics_ready(self, info: dict) -> None:
        if info.get("server") == "up":
            model = str(info.get("model") or self.service.model)
            installed = info.get("model_installed")
            self.status.setText(
                f"Ollama online · {model}" if installed else "Ollama online · modelo ausente"
            )
        else:
            self.status.setText("Ollama offline")
            self.activity.setText("Verifique o serviço local")

    def _append_user(self, text: str) -> None:
        self.transcript.append(f'<p style="color:#9ab8e7"><b>Você</b><br>{html.escape(text)}</p>')

    def send_message(self) -> None:
        prompt = self.input.text().strip()
        if not prompt or self.worker is not None:
            return
        self.expand()
        self.input.clear()
        self._append_user(prompt)
        self.transcript.append('<p style="color:#70dcff"><b>Noite</b><br>')
        self._stream_text = ""
        self._set_state("thinking", "Pensando…")
        self.activity.setText("Processando sua mensagem")
        self.send_button.setEnabled(False)
        self.worker = AssistantWorker(self.service, self.conversation_id, prompt)
        self.worker.chunk.connect(self._receive_chunk)
        self.worker.activity.connect(self._receive_activity)
        self.worker.completed.connect(self._request_completed)
        self.worker.failed.connect(self._request_failed)
        self.worker.finished.connect(self._worker_finished)
        self.worker.start()

    def _receive_chunk(self, chunk: str) -> None:
        self._stream_text += chunk
        cursor = self.transcript.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(chunk)
        self.transcript.setTextCursor(cursor)
        self.transcript.ensureCursorVisible()
        self._set_state("working", "Trabalhando…")

    def _receive_activity(self, event: ActivityEvent) -> None:
        self.activity.setText(event.summary)
        if event.state == "started":
            self._set_state("thinking", "Pensando…")
        elif event.state == "failed":
            self._set_state("error", "Algo deu errado")
        elif event.state == "completed":
            self._set_state("working", "Finalizando…")

    def _request_completed(self, answer: str) -> None:
        if not self._stream_text:
            cursor = self.transcript.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.insertText(answer)
        self.transcript.append("</p>")
        self.transcript.ensureCursorVisible()
        self._set_state("done", "Concluído")
        self.activity.setText("Resposta pronta")
        QTimer.singleShot(
            2600, lambda: self._set_state("idle", "Pronta") if self._state == "done" else None
        )

    def _request_failed(self, message: str) -> None:
        self.transcript.append(f'<p style="color:#ff8aa1">{html.escape(message)}</p>')
        self._set_state("error", "Falha")
        self.activity.setText(message)

    def _worker_finished(self) -> None:
        self.send_button.setEnabled(True)
        worker = self.worker
        self.worker = None
        if worker is not None:
            worker.deleteLater()
        self.refresh_diagnostics()
        self._maybe_close()

    def _maybe_close(self) -> None:
        if not self._close_pending:
            return
        worker_running = self.worker is not None and self.worker.isRunning()
        diagnostics_running = (
            self.diagnostics_worker is not None and self.diagnostics_worker.isRunning()
        )
        if not worker_running and not diagnostics_running:
            self.close()

    def closeEvent(self, event) -> None:
        self._save_position()
        self.diagnostics_timer.stop()
        worker_running = self.worker is not None and self.worker.isRunning()
        diagnostics_running = (
            self.diagnostics_worker is not None and self.diagnostics_worker.isRunning()
        )
        if worker_running or diagnostics_running:
            self._close_pending = True
            self.setEnabled(False)
            self.activity.setText("Finalizando a operação local antes de sair…")
            event.ignore()
            return
        event.accept()


def run_mascot() -> int:
    app = QApplication.instance() or QApplication([])
    app.setApplicationName("Noite 2.0")
    settings = get_settings()
    setup_logging(settings.data_dir)
    icon_path = Path(__file__).resolve().parents[2] / "assets" / "noite.ico"
    if icon_path.is_file():
        from PySide6.QtGui import QIcon

        app.setWindowIcon(QIcon(str(icon_path)))
    service = AssistantService(settings)
    window = MascotWindow(service)
    window.show()
    return app.exec()
