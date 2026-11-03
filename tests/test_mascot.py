import os

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QApplication

from noite.config import Settings
from noite.mascot import (
    AssistantService,
    AssistantWorker,
    DiagnosticsWorker,
    MascotFace,
    MascotWindow,
)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_APP = QApplication.instance() or QApplication([])
_APP.setQuitOnLastWindowClosed(False)


def test_mascot_face_exposes_activity_states():
    app = _APP
    face = MascotFace()
    for state in ("idle", "thinking", "working", "done", "error"):
        face.set_state(state)
        assert face.state == state
    face.resize(132, 132)
    face.show()
    app.processEvents()
    assert face.size().width() == 132
    face.close()
    app.processEvents()


class _FakeService:
    """Serviço mínimo sem rede nem banco, para testar os workers isoladamente."""

    model = "qwen2.5:3b"

    def active_conversation_id(self) -> str:
        return "conv-1"

    def model_diagnostics(self) -> dict:
        return {
            "server": "up",
            "model": self.model,
            "model_installed": True,
            "model_details": [
                {
                    "name": self.model,
                    "size_bytes": 1_900_000_000,
                    "family": "qwen",
                    "parameter_size": "3B",
                    "quantization": "Q4_K_M",
                    "format": "gguf",
                }
            ],
        }

    async def respond(self, text, conversation_id=None, on_chunk=None, on_activity=None):
        if on_chunk:
            on_chunk("parcial ")
            on_chunk("resposta")
        return "resposta completa"


def test_mascot_window_expand_collapse_toggle(tmp_path):
    app = _APP
    service = AssistantService(Settings(_env_file=None, data_dir=tmp_path))
    window = MascotWindow(service)
    try:
        window.show()
        app.processEvents()

        assert window._expanded is False
        assert window.panel.isVisible() is False

        window.expand()
        assert window._expanded is True
        assert window.panel.isVisible() is True

        window.collapse()
        assert window._expanded is False
        assert window.panel.isVisible() is False
    finally:
        window.diagnostics_timer.stop()
        window.close()
        app.processEvents()


def test_right_click_on_mascot_opens_conversation(tmp_path):
    app = _APP
    service = AssistantService(Settings(_env_file=None, data_dir=tmp_path))
    window = MascotWindow(service)
    try:
        window.show()
        app.processEvents()
        assert window._expanded is False
        event = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            window.face.rect().center(),
            Qt.MouseButton.RightButton,
            Qt.MouseButton.RightButton,
            Qt.KeyboardModifier.NoModifier,
        )
        window._face_pressed(event)
        app.processEvents()
        assert window._expanded is True
        assert window.panel.isVisible()
    finally:
        window.diagnostics_timer.stop()
        window.close()
        app.processEvents()


def test_mascot_window_escape_closes_when_collapsed(tmp_path):
    app = _APP
    service = AssistantService(Settings(_env_file=None, data_dir=tmp_path))
    window = MascotWindow(service)
    try:
        window.show()
        app.processEvents()

        assert window._expanded is False
        assert window.isVisible()
        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
        window.keyPressEvent(event)
        app.processEvents()

        assert not window.isVisible()
    finally:
        window.diagnostics_timer.stop()


def test_mascot_window_escape_collapses_when_expanded(tmp_path):
    app = _APP
    service = AssistantService(Settings(_env_file=None, data_dir=tmp_path))
    window = MascotWindow(service)
    try:
        window.show()
        app.processEvents()

        window.expand()
        assert window._expanded is True
        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
        window.keyPressEvent(event)

        assert window._expanded is False
        assert window.panel.isVisible() is False
    finally:
        window.diagnostics_timer.stop()
        window.close()
        app.processEvents()


def test_refresh_diagnostics_skipped_when_collapsed(tmp_path):
    app = _APP
    service = AssistantService(Settings(_env_file=None, data_dir=tmp_path))
    window = MascotWindow(service)
    try:
        assert window._expanded is False
        window.refresh_diagnostics()
        assert window.diagnostics_worker is None
        app.processEvents()
    finally:
        window.diagnostics_timer.stop()
        window.close()
        app.processEvents()


def test_assistant_worker_emits_chunks_and_completed():
    app = _APP
    service = _FakeService()
    worker = AssistantWorker(service, "conv-1", "oi")
    chunks: list[str] = []
    result: dict[str, object] = {}
    worker.chunk.connect(chunks.append)
    worker.completed.connect(lambda answer: result.setdefault("answer", answer))
    worker.start()
    assert worker.wait(5000)
    app.processEvents()
    assert chunks == ["parcial ", "resposta"]
    assert result["answer"] == "resposta completa"
    worker.deleteLater()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_diagnostics_worker_emits_completed_and_failed():
    app = _APP

    worker = DiagnosticsWorker(_FakeService())
    out: dict[str, object] = {}
    worker.completed.connect(lambda info: out.setdefault("completed", info))
    worker.failed.connect(lambda message: out.setdefault("failed", message))
    worker.start()
    assert worker.wait(5000)
    app.processEvents()
    assert out["completed"]["server"] == "up"
    assert "failed" not in out
    worker.deleteLater()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    class FailingService:
        def model_diagnostics(self) -> dict:
            raise RuntimeError("ollama não responde")

    worker2 = DiagnosticsWorker(FailingService())
    out2: dict[str, object] = {}
    worker2.completed.connect(lambda info: out2.setdefault("completed", info))
    worker2.failed.connect(lambda message: out2.setdefault("failed", message))
    worker2.start()
    assert worker2.wait(5000)
    app.processEvents()
    assert out2["failed"] == "RuntimeError"
    assert "completed" not in out2
    worker2.deleteLater()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_diagnostics_ready_shows_model_detail(tmp_path):
    app = _APP
    service = AssistantService(Settings(_env_file=None, data_dir=tmp_path))
    window = MascotWindow(service)
    try:
        window._diagnostics_ready(
            {
                "server": "up",
                "model": "qwen2.5:3b",
                "model_installed": True,
                "model_details": [
                    {
                        "name": "qwen2.5:3b",
                        "parameter_size": "3B",
                        "quantization": "Q4_K_M",
                    }
                ],
            }
        )
        assert window._diagnostics["model"] == "qwen2.5:3b"
        assert window._diagnostics["model_details"][0]["quantization"] == "Q4_K_M"
        app.processEvents()
    finally:
        window.diagnostics_timer.stop()
        window.close()
        app.processEvents()
