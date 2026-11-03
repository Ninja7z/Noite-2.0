from __future__ import annotations

import asyncio
import ctypes
import ctypes.wintypes
import html
import logging
import threading
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QSettings, Qt, QThread, QTimer, Signal
from PySide6.QtGui import (
    QCloseEvent,
    QColor,
    QKeyEvent,
    QMouseEvent,
    QPainter,
)
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
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

SETTINGS_ORGANIZATION = "Noite2"
SETTINGS_APPLICATION = "Mascot"
DIAGNOSTICS_INTERVAL_MS = 30_000
IDLE_RETURN_MS = 2600


class AssistantWorker(QThread):
    """Executa AssistantService.respond em uma thread separada da thread visual."""

    chunk = Signal(str)
    activity = Signal(object)
    completed = Signal(str)
    failed = Signal(str)

    def __init__(self, service: AssistantService, conversation_id: str, prompt: str):
        super().__init__()
        self.service = service
        self.conversation_id = conversation_id
        self.prompt = prompt
        self._cancelled = False

    def cancel(self) -> None:
        """Sinaliza cancelamento; emissões subsequentes são ignoradas."""
        self._cancelled = True

    def run(self) -> None:
        try:
            answer = asyncio.run(
                self.service.respond(
                    self.prompt,
                    conversation_id=self.conversation_id,
                    on_chunk=self._emit_chunk,
                    on_activity=self._emit_activity,
                )
            )
            if not self._cancelled:
                self.completed.emit(answer)
        except Exception as exc:
            if not self._cancelled:
                logger.error("Mascot request failed (%s)", type(exc).__name__)
                self.failed.emit(f"Não consegui concluir. Falha: {type(exc).__name__}.")

    def _emit_chunk(self, text: str) -> None:
        if self._cancelled:
            return
        self.chunk.emit(text)

    def _emit_activity(self, event: ActivityEvent) -> None:
        if self._cancelled:
            return
        self.activity.emit(event)


class DiagnosticsWorker(QThread):
    """Inspeciona Ollama e o modelo fora da thread visual."""

    completed = Signal(dict)
    failed = Signal(str)

    def __init__(self, service: AssistantService):
        super().__init__()
        self.service = service

    def run(self) -> None:
        try:
            self.completed.emit(self.service.model_diagnostics())
        except Exception as exc:
            self.failed.emit(type(exc).__name__)


class GlobalHotkeyWorker(QThread):
    """Registra Alt+C globalmente no Windows sem bloquear a interface."""

    activated = Signal()
    registration_failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread_id = 0
        self._ready = threading.Event()

    def run(self) -> None:
        if not hasattr(ctypes, "windll"):
            self._ready.set()
            self.registration_failed.emit("Atalho global disponível apenas no Windows.")
            return
        user32 = ctypes.windll.user32
        from ctypes import wintypes

        user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        user32.RegisterHotKey.restype = wintypes.BOOL
        user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.GetMessageW.argtypes = [
            ctypes.POINTER(wintypes.MSG),
            wintypes.HWND,
            wintypes.UINT,
            wintypes.UINT,
        ]
        user32.GetMessageW.restype = ctypes.c_int
        user32.PeekMessageW.argtypes = [
            ctypes.POINTER(wintypes.MSG),
            wintypes.HWND,
            wintypes.UINT,
            wintypes.UINT,
            wintypes.UINT,
        ]
        user32.PeekMessageW.restype = wintypes.BOOL
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        if not user32.RegisterHotKey(None, 0x4E32, 0x0001, 0x43):
            self._ready.set()
            self.registration_failed.emit("Não foi possível registrar Alt+C.")
            return
        msg = wintypes.MSG()
        # Garante que a fila de mensagens exista antes de outro thread enviar WM_QUIT.
        user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)
        self._ready.set()
        try:
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == 0x0312 and msg.wParam == 0x4E32:
                    self.activated.emit()
        finally:
            user32.UnregisterHotKey(None, 0x4E32)

    def stop(self) -> bool:
        if not self.isRunning():
            return True
        self._ready.wait(1.0)
        if self._thread_id:
            user32 = ctypes.windll.user32
            user32.PostThreadMessageW.argtypes = [
                ctypes.wintypes.DWORD,
                ctypes.wintypes.UINT,
                ctypes.wintypes.WPARAM,
                ctypes.wintypes.LPARAM,
            ]
            user32.PostThreadMessageW.restype = ctypes.wintypes.BOOL
            if not user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0):
                logger.warning("Não foi possível enviar WM_QUIT à thread do atalho global.")
        return self.wait(2000)


class MascotFace(QWidget):
    """Visual do mascote; a animação é leve e controlada por estados."""

    # States: idle, working, thinking, error, done, angry, dizzy, listening
    state_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(112, 116)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.state = "idle"
        self._blink = False
        self._phase = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(900)

    def set_state(self, state: str) -> None:
        self.state = state
        self.update()

    def _animate(self) -> None:
        self._phase = (self._phase + 1) % 8
        self._blink = self._phase == 0
        self.update()

    def _set_state(self, state: str, label: str = "") -> None:
        self.state = state
        self.state_changed.emit(state)
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


class MascotWindow(QWidget):
    """Floating Noite companion without a background window."""

    def __init__(self, service: AssistantService):
        super().__init__()
        self.service = service
        self.conversation_id = service.active_conversation_id()
        self.worker: AssistantWorker | None = None
        self.diagnostics_worker: DiagnosticsWorker | None = None
        self._drag_offset: QPoint | None = None
        self._close_pending = False
        self._streamed_any = False
        self._state = "idle"
        self.setObjectName("noiteMascotWindow")
        self.setWindowTitle("Noite 2.0")
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(136, 136)
        self._build_ui()
        self.diagnostics_timer = QTimer(self)
        self.diagnostics_timer.timeout.connect(self.refresh_diagnostics)
        self.diagnostics_timer.stop()
        self._restore_position()
        self._set_state("idle")
        # Qt's offscreen platform is used by automated tests; don't register
        # a native OS hotkey from a headless test process.
        if QApplication.platformName().casefold() != "offscreen":
            self.hotkey = GlobalHotkeyWorker(self)
            self.hotkey.activated.connect(self.toggle_visibility)
            self.hotkey.registration_failed.connect(lambda reason: logger.warning(reason))
            self.hotkey.start()

    def _build_ui(self) -> None:
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Top bar: face.
        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(0)
        self.face = MascotFace()
        self.face.setFixedSize(136, 136)
        top.addWidget(self.face)
        top.addStretch(1)
        self.layout.addLayout(top)

        # Collapsible chat panel.
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
        self.layout.addWidget(self.panel)
        self.panel.hide()
        self._expanded = False
        self.face.mousePressEvent = self._face_pressed
        self.face.mouseMoveEvent = self._face_move
        self.face.mouseReleaseEvent = self._face_release

    def _restore_position(self) -> None:
        settings = QSettings(SETTINGS_ORGANIZATION, SETTINGS_APPLICATION)
        x = settings.value("x", None)
        y = settings.value("y", None)
        if x is not None and y is not None:
            self.move(int(x), int(y))
        else:
            screen = QApplication.primaryScreen()
            area = screen.availableGeometry() if screen else QRect(0, 0, 1280, 720)
            self.move(area.right() - 175, area.bottom() - 180)

    def _save_position(self) -> None:
        settings = QSettings(SETTINGS_ORGANIZATION, SETTINGS_APPLICATION)
        settings.setValue("x", self.x())
        settings.setValue("y", self.y())
        settings.setValue("collapsed", "true" if not self._expanded else "false")

    def _face_pressed(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self.toggle_panel()
            event.accept()

    def _face_move(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def _face_release(self, event: QMouseEvent) -> None:
        self._drag_offset = None
        self._save_position()
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def toggle_panel(self) -> None:
        self.expand() if not self._expanded else self.collapse()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            if self._expanded:
                self.collapse()
            else:
                self.close()
            event.accept()
            return
        super().keyPressEvent(event)

    def toggle_visibility(self) -> None:
        # A API pode ocultar a janela pelo Win32; consulte o estado nativo,
        # não apenas o estado em cache do QWidget.
        if hasattr(ctypes, "windll"):
            user32 = ctypes.windll.user32
            hwnd = int(self.winId())
            if user32.IsWindowVisible(hwnd):
                user32.ShowWindow(hwnd, 0)  # SW_HIDE
            else:
                user32.ShowWindow(hwnd, 5)  # SW_SHOW
                user32.SetForegroundWindow(hwnd)
            return
        if self.isVisible():
            self.hide()
        else:
            self.show()

    def expand(self) -> None:
        self._expanded = True
        self.panel.show()
        self.setMinimumSize(370, 390)
        self.setMaximumSize(370, 620)
        self.resize(370, 390)
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
        self.diagnostics_timer.start()
        self._save_position()

    def collapse(self) -> None:
        self._expanded = False
        self.panel.hide()
        self.setFixedSize(136, 136)
        self.adjustSize()
        self.diagnostics_timer.stop()
        self._save_position()

    def _set_state(self, state: str, label: str = "") -> None:
        self._state = state
        self.face.set_state(state)

    def refresh_diagnostics(self) -> None:
        if not self._expanded:
            return
        if self.diagnostics_worker is not None:
            try:
                if self.diagnostics_worker.isRunning():
                    return
            except RuntimeError:
                self.diagnostics_worker = None
        worker = DiagnosticsWorker(self.service)
        self.diagnostics_worker = worker
        worker.completed.connect(self._diagnostics_ready)
        worker.failed.connect(self._diagnostics_failed)
        worker.finished.connect(self._diagnostics_finished)
        worker.start()

    def _diagnostics_finished(self) -> None:
        worker = self.sender()
        if worker is self.diagnostics_worker:
            self.diagnostics_worker = None
        if worker is not None:
            worker.deleteLater()
        self._maybe_close()

    def _diagnostics_failed(self, message: str) -> None:
        logger.warning("Mascot diagnostics failed (%s)", message)

    def _diagnostics_ready(self, info: dict) -> None:
        self._diagnostics = dict(info)

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
        self._streamed_any = False
        self._set_state("thinking")
        self.send_button.setEnabled(False)
        self.worker = AssistantWorker(self.service, self.conversation_id, prompt)
        self.worker.chunk.connect(self._receive_chunk)
        self.worker.activity.connect(self._receive_activity)
        self.worker.completed.connect(self._request_completed)
        self.worker.failed.connect(self._request_failed)
        self.worker.finished.connect(self._worker_finished)
        self.worker.start()

    def _receive_chunk(self, chunk: str) -> None:
        self._streamed_any = True
        cursor = self.transcript.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(chunk)
        self.transcript.setTextCursor(cursor)
        self.transcript.ensureCursorVisible()
        self._set_state("working")

    def _receive_activity(self, event: ActivityEvent) -> None:
        if event.state == "started":
            self._set_state("thinking")
        elif event.state == "failed":
            self._set_state("error")
        elif event.state == "completed":
            self._set_state("working")

    def _request_completed(self, answer: str) -> None:
        if not self._streamed_any:
            cursor = self.transcript.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.insertText(answer)
        # Removido: self.transcript.append("</p>")
        self.transcript.ensureCursorVisible()
        self._set_state("done")
        QTimer.singleShot(
            IDLE_RETURN_MS,
            lambda: self._set_state("idle") if self._state == "done" else None,
        )

    def _request_failed(self, message: str) -> None:
        self.transcript.append(f'<p style="color:#ff8aa1">{html.escape(message)}</p>')
        self._set_state("error")

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

    def closeEvent(self, event: QCloseEvent) -> None:
        self._save_position()
        self.diagnostics_timer.stop()
        if hasattr(self, "hotkey") and self.hotkey.isRunning() and not self.hotkey.stop():
            event.ignore()
            QTimer.singleShot(100, self.close)
            return
        worker_running = self.worker is not None and self.worker.isRunning()
        diagnostics_running = (
            self.diagnostics_worker is not None and self.diagnostics_worker.isRunning()
        )
        if worker_running or diagnostics_running:
            self._close_pending = True
            self.setEnabled(False)
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
