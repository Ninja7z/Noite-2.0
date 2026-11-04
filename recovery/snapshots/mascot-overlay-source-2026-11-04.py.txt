from __future__ import annotations

import asyncio
import ctypes
import ctypes.wintypes
import html
import logging
import threading
from pathlib import Path

from PySide6.QtCore import QEvent, QPoint, QRect, QSettings, Qt, QThread, QTimer, Signal
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
        """Sinaliza cancelamento; emissÃµes subsequentes sÃ£o ignoradas."""
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
                self.failed.emit(f"NÃ£o consegui concluir. Falha: {type(exc).__name__}.")

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
