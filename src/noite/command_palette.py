"""Keyboard-first command palette for actions that already exist in the app."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class CommandAction:
    action_id: str
    title: str
    description: str
    callback: Callable[[], None]
    keywords: tuple[str, ...] = ()

    @property
    def search_text(self) -> str:
        return " ".join((self.title, self.description, *self.keywords)).casefold()


class CommandPalette(QDialog):
    """A searchable, keyboard-operated dialog populated from live app actions."""

    def __init__(self, actions_provider: Callable[[], Iterable[CommandAction]], parent=None):
        super().__init__(parent)
        self._actions_provider = actions_provider
        self._visible_actions: list[CommandAction] = []
        self.setObjectName("commandPalette")
        self.setWindowTitle("Command Palette")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setModal(True)
        self.setFixedSize(620, 500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(12)
        heading = QHBoxLayout()
        title = QLabel("Ações rápidas")
        title.setObjectName("paletteTitle")
        hint = QLabel("ESC para fechar")
        hint.setObjectName("paletteHint")
        heading.addWidget(title)
        heading.addStretch(1)
        heading.addWidget(hint)
        layout.addLayout(heading)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("paletteSearch")
        self.search_input.setPlaceholderText("O que você quer fazer?")
        self.search_input.textChanged.connect(self._filter_actions)
        self.search_input.installEventFilter(self)
        layout.addWidget(self.search_input)

        self.results = QListWidget()
        self.results.setObjectName("paletteResults")
        self.results.setAccessibleName("Ações disponíveis")
        self.results.itemActivated.connect(self._execute_item)
        layout.addWidget(self.results, 1)

        footer = QLabel("↑ ↓ navegar     ↵ executar     Ctrl + K abrir")
        footer.setObjectName("paletteFooter")
        layout.addWidget(footer)
        self.set_theme("dark")

    def set_theme(self, theme: str) -> None:
        colors = (
            ("#fbfaff", "#ded8ee", "#29253b", "#514b66", "#fffefe", "#39334c")
            if theme == "light"
            else ("#1b1a20", "#51466c", "#f4f0ff", "#96919f", "#25232b", "#393044")
        )
        background, border, primary, muted, input_background, selected = colors
        self.setStyleSheet(
            f"QDialog#commandPalette {{ background: {background}; border: 1px solid {border}; "
            "border-radius: 16px; }"
            f"QLabel#paletteTitle {{ font-size: 16px; font-weight: 650; color: {primary}; }}"
            f"QLabel#paletteHint, QLabel#paletteFooter {{ color: {muted}; font-size: 11px; }}"
            f"QLineEdit#paletteSearch {{ background: {input_background}; "
            f"border: 1px solid {border}; "
            f"border-radius: 10px; padding: 12px 14px; color: {primary}; font-size: 15px; }}"
            "QListWidget#paletteResults { background: transparent; border: 0; outline: 0; }"
            f"QListWidget#paletteResults::item {{ padding: 13px 12px; border-radius: 9px; "
            f"color: {primary}; }}"
            f"QListWidget#paletteResults::item:selected {{ background: {selected}; "
            f"color: {primary}; }}"
        )

    def open(self) -> None:
        self.search_input.clear()
        self._filter_actions()
        if self.parentWidget() is not None:
            frame = self.parentWidget().frameGeometry()
            self.move(frame.center() - self.rect().center())
        self.show()
        self.raise_()
        self.activateWindow()
        self.search_input.setFocus()

    def _filter_actions(self, query: str = "") -> None:
        term = query.strip().casefold()
        actions = list(self._actions_provider())
        self._visible_actions = [action for action in actions if term in action.search_text]
        self.results.clear()
        for action in self._visible_actions:
            item = QListWidgetItem(f"{action.title}\n{action.description}")
            item.setData(Qt.ItemDataRole.UserRole, action.action_id)
            self.results.addItem(item)
        if self.results.count():
            self.results.setCurrentRow(0)

    def _execute_item(self, item: QListWidgetItem) -> None:
        action_id = item.data(Qt.ItemDataRole.UserRole)
        action = next(
            (candidate for candidate in self._visible_actions if candidate.action_id == action_id),
            None,
        )
        if action is None:
            return
        self.accept()
        action.callback()

    def eventFilter(self, watched: QWidget, event) -> bool:
        if watched is self.search_input and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Down, Qt.Key.Key_Up) and self.results.count():
                current = self.results.currentRow()
                delta = 1 if event.key() == Qt.Key.Key_Down else -1
                self.results.setCurrentRow((current + delta) % self.results.count())
                self.results.setFocus()
                return True
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                current = self.results.currentItem()
                if current is not None:
                    self._execute_item(current)
                return True
            if event.key() == Qt.Key.Key_Escape:
                self.reject()
                return True
        return super().eventFilter(watched, event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            return
        super().keyPressEvent(event)
