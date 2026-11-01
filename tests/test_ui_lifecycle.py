from __future__ import annotations

import asyncio
import os
import threading
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QListWidgetItem,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QTextBrowser,
)

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

    window._on_stream_chunk("<script>")
    window._on_stream_chunk("literal text")

    assert "<script>literal text" in window.chat.toPlainText()
    assert window.chat.document().toHtml().count("&lt;script&gt;") == 1
    window.deleteLater()


def test_mcp_call_requires_explicit_approval(app, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    dialog = MCPDialog(tmp_path)
    dialog.servers = {"example": {"command": "configured-server", "args": []}}
    dialog._refresh_servers()
    item = QListWidgetItem("write_file")
    item.setData(
        Qt.UserRole,
        {"name": "write_file", "description": "Write a file", "input_schema": {}},
    )
    dialog.tools.addItem(item)
    dialog.tools.setCurrentItem(item)
    dialog.arguments_input.setPlainText('{"path":"notes.txt"}')
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.No)

    dialog._call_selected()

    assert dialog.worker is None


def test_approved_mcp_call_runs_only_selected_tool(app, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    from noite import mcp_client

    captured = {}
    done = threading.Event()

    async def fake_call(self, server, name, arguments):
        captured["server"] = server
        captured["name"] = name
        captured["arguments"] = arguments
        done.set()
        return ["completed"]

    monkeypatch.setattr(mcp_client.MCPClient, "call_tool", fake_call)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Yes)
    dialog = MCPDialog(tmp_path)
    dialog.servers = {"example": {"command": "configured-server", "args": ["--stdio"]}}
    dialog._refresh_servers()
    item = QListWidgetItem("write_file")
    item.setData(Qt.UserRole, {"name": "write_file", "description": "", "input_schema": {}})
    dialog.tools.addItem(item)
    dialog.tools.setCurrentItem(item)
    dialog.arguments_input.setPlainText('{"path":"notes.txt"}')

    dialog._call_selected()
    deadline = time.monotonic() + 5
    while not done.is_set() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    app.processEvents()

    assert done.is_set()
    assert captured["name"] == "write_file"
    assert captured["arguments"] == {"path": "notes.txt"}
    assert captured["server"].allowed_tools == frozenset({"write_file"})
    assert dialog.result.toPlainText() == "completed"

