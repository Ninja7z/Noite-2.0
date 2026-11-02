"""Collapsible session context and real-operation activity feed."""

from __future__ import annotations

from time import monotonic

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QToolButton,
    QVBoxLayout,
)

from .activity import ActivityEvent


class ContextActivityPanel(QFrame):
    close_requested = Signal()

    _STATE_LABELS = {
        "started": "em andamento",
        "completed": "concluída",
        "failed": "falhou",
        "cancelled": "cancelada",
    }
    _STATE_GLYPHS = {
        "started": "◌",
        "completed": "✓",
        "failed": "!",
        "cancelled": "–",
    }

    @property
    def has_active_operations(self) -> bool:
        return bool(self._active_operations)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("contextActivityPanel")
        self.setFixedWidth(292)
        self._events: dict[str, ActivityEvent] = {}
        self._active_operations: dict[str, tuple[str, float]] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 18, 16, 14)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Contexto da sessão")
        title.setObjectName("contextPanelTitle")
        close = QToolButton()
        close.setText("×")
        close.setToolTip("Fechar painel de contexto e atividade")
        close.setAccessibleName("Fechar painel de contexto e atividade")
        close.clicked.connect(self.close_requested)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(close)
        layout.addLayout(header)

        self.model_value = self._context_value("Modelo local", "contextModel")
        layout.addWidget(self.model_value)
        self.project_value = self._context_value("Nenhum projeto aberto", "contextProject")
        layout.addWidget(self.project_value)
        self.file_value = self._context_value("Nenhum arquivo ativo", "contextFile")
        layout.addWidget(self.file_value)

        self.progress = QLabel("Sem operações em andamento.")
        self.progress.setObjectName("activityProgress")
        self.progress.setWordWrap(True)
        layout.addWidget(self.progress)

        section = QLabel("Atividade recente")
        section.setObjectName("contextSection")
        layout.addWidget(section)
        self.empty_activity = QLabel("As operações realizadas aparecerão aqui.")
        self.empty_activity.setObjectName("emptyActivity")
        self.empty_activity.setWordWrap(True)
        layout.addWidget(self.empty_activity)
        self.events = QListWidget()
        self.events.setObjectName("activityEvents")
        self.events.setAccessibleName("Atividade recente da Noite")
        self.events.currentItemChanged.connect(self._show_event_details)
        layout.addWidget(self.events, 1)

        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(1000)
        self._progress_timer.timeout.connect(self._refresh_progress)
        self._progress_timer.start()

        self.details_toggle = QToolButton()
        self.details_toggle.setText("Ver detalhes")
        self.details_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.details_toggle.setCheckable(True)
        self.details_toggle.setObjectName("activityDetailsToggle")
        self.details_toggle.toggled.connect(self._toggle_details)
        self.details_toggle.hide()
        layout.addWidget(self.details_toggle, 0, Qt.AlignmentFlag.AlignLeft)
        self.details = QLabel()
        self.details.setObjectName("activityDetails")
        self.details.setWordWrap(True)
        self.details.hide()
        layout.addWidget(self.details)

    @staticmethod
    def _context_value(text: str, object_name: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName(object_name)
        label.setWordWrap(True)
        return label

    def set_model(self, model: str, state: str) -> None:
        self.model_value.setText(f"Modelo · {model}\n{state}")

    def set_project(self, name: str, active_file: str | None = None) -> None:
        self.project_value.setText(f"Projeto · {name}")
        self.file_value.setText(f"Arquivo relacionado · {active_file or 'nenhum'}")

    def set_active_file(self, path: str | None) -> None:
        self.file_value.setText(f"Arquivo relacionado · {path or 'nenhum'}")

    def add_event(self, event: ActivityEvent) -> None:
        if event.state == "started":
            self._active_operations[event.operation] = (event.summary, monotonic())
        else:
            self._active_operations.pop(event.operation, None)
        self._refresh_progress()
        self.empty_activity.hide()
        self._events[event.event_id] = event
        clock = event.occurred_at.strftime("%H:%M:%S")
        state = self._STATE_LABELS.get(event.state, event.state)
        glyph = self._STATE_GLYPHS.get(event.state, "·")
        duration = f" · {event.duration_ms} ms" if event.duration_ms is not None else ""
        item = QListWidgetItem(f"{glyph}  {event.summary}\n{clock} · {state}{duration}")
        item.setData(Qt.ItemDataRole.UserRole, event.event_id)
        item.setToolTip(event.summary)
        self.events.insertItem(0, item)
        while self.events.count() > 40:
            removed = self.events.takeItem(self.events.count() - 1)
            if removed is not None:
                self._events.pop(removed.data(Qt.ItemDataRole.UserRole), None)
        self.events.setCurrentItem(item)

    def _refresh_progress(self) -> None:
        if not self._active_operations:
            self.progress.setText("Sem operações em andamento.")
            return
        operation, (summary, started) = next(reversed(self._active_operations.items()))
        elapsed = max(0, int(monotonic() - started))
        self.progress.setText(f"{summary}\n{operation} · {elapsed} s")

    def _show_event_details(self, current: QListWidgetItem | None, _previous) -> None:
        event_id = current.data(Qt.ItemDataRole.UserRole) if current is not None else None
        event = self._events.get(event_id)
        details = event.details if event and event.details else "Sem detalhes adicionais."
        self.details.setText(details)
        self.details_toggle.setVisible(event is not None)
        self.details_toggle.setChecked(False)
        self.details.hide()

    def _toggle_details(self, visible: bool) -> None:
        self.details.setVisible(visible)
        self.details_toggle.setText("Ocultar detalhes" if visible else "Ver detalhes")
