"""Context dashboard shown beside the conversation."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QFontMetrics, QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .theme import UI_TOKENS


class MiddleElideLabel(QLabel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._full_text = ""
        self.setWordWrap(False)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_full_text(self, text: str) -> None:
        self._full_text = text
        self._refresh_text()
        self.setToolTip(text)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh_text()

    def _refresh_text(self) -> None:
        self.setText(QFontMetrics(self.font()).elidedText(
            self._full_text, Qt.TextElideMode.ElideMiddle, max(0, self.width())
        ))


class MinHeightCard(QFrame):
    def __init__(self, minimum_height: int, parent=None) -> None:
        super().__init__(parent)
        self._minimum_height = minimum_height

    def sizeHint(self) -> QSize:
        hint = super().sizeHint()
        return QSize(hint.width(), max(hint.height(), self._minimum_height))

    def minimumSizeHint(self) -> QSize:
        hint = super().minimumSizeHint()
        return QSize(hint.width(), max(hint.height(), self._minimum_height))


class ContextActivityPanel(QFrame):
    close_requested = Signal()
    highlight_requested = Signal()
    details_requested = Signal()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_highlight_layout()

    def _update_highlight_layout(self) -> None:
        laptop = getattr(self, "highlight_laptop", None)
        if laptop is not None:
            laptop.setVisible(
                self.width() >= UI_TOKENS["layout"]["highlight_compact_width"]
            )

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("contextActivityPanel")
        self.setMinimumWidth(280)
        self.setMaximumWidth(440)
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        scroll = QScrollArea(self)
        scroll.setObjectName("activityPanelScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area = scroll
        content = QWidget()
        content.setMinimumWidth(0)
        content.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 10, 8, 8)
        layout.setSpacing(5)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

        header = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(self._icon("star").pixmap(21, 21))
        header.addWidget(icon)
        title = QLabel("Destaques")
        title.setObjectName("contextPanelTitle")
        close = QToolButton()
        close.setIcon(self._icon("chevron-right"))
        close.setIconSize(QSize(18, 18))
        close.setToolTip("Fechar painel")
        close.setAccessibleName("Fechar painel")
        close.clicked.connect(self.close_requested)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(close)
        layout.addLayout(header)

        highlights = MinHeightCard(UI_TOKENS["layout"]["highlight_card_min_height"])
        highlights.setObjectName("highlightCard")
        highlights.setMinimumWidth(0)
        highlights.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        highlight_layout = QHBoxLayout(highlights)
        highlight_layout.setContentsMargins(16, 15, 12, 15)
        highlight_layout.setSpacing(6)
        highlight_copy_layout = QVBoxLayout()
        highlight_copy_layout.setContentsMargins(0, 0, 0, 0)
        highlight_copy_layout.setSpacing(7)
        highlight_title = QLabel("Mais foco, mais\nprodutividade.")
        highlight_title.setObjectName("highlightTitle")
        highlight_title.setWordWrap(True)
        highlight_title.setMinimumWidth(0)
        highlight_copy_layout.addWidget(highlight_title)
        highlight_copy = QLabel("Use o Noite para automatizar tarefas, pesquisar e criar.")
        highlight_copy.setObjectName("highlightCopy")
        highlight_copy.setWordWrap(True)
        highlight_copy.setMinimumWidth(0)
        highlight_copy_layout.addWidget(highlight_copy)
        learn_more = QPushButton("Saiba mais")
        learn_more.setObjectName("highlightAction")
        learn_more.clicked.connect(self.highlight_requested)
        highlight_copy_layout.addWidget(learn_more, 0, Qt.AlignmentFlag.AlignLeft)
        highlight_layout.addLayout(highlight_copy_layout, 1)
        laptop = QLabel()
        laptop.setPixmap(self._icon("laptop-moon").pixmap(92, 48))
        laptop.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.highlight_laptop = laptop
        highlight_layout.addWidget(laptop)
        layout.addWidget(highlights)
        self._update_highlight_layout()

        context_card = MinHeightCard(UI_TOKENS["layout"]["context_card_min_height"])
        context_card.setObjectName("referenceContextCard")
        context_card.setMinimumWidth(0)
        context_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        context_card.setMinimumHeight(UI_TOKENS["layout"]["context_card_min_height"])
        context_layout = QVBoxLayout(context_card)
        context_layout.setContentsMargins(15, 6, 15, 6)
        context_layout.setSpacing(2)
        context_icon = QLabel()
        context_icon.setPixmap(self._icon("cube").pixmap(20, 20))
        context_layout.addWidget(context_icon, 0, Qt.AlignmentFlag.AlignLeft)
        context_title = QLabel("Contexto Atual")
        context_title.setObjectName("contextPanelTitle")
        context_layout.addWidget(context_title)
        self.reference_project = QLabel("Projeto ativo\n—")
        self.reference_project.setObjectName("referenceContextValue")
        context_layout.addWidget(self.reference_project)
        directory_caption = QLabel("Diretório")
        directory_caption.setObjectName("referenceContextCaption")
        context_layout.addWidget(directory_caption)
        self.reference_directory = MiddleElideLabel()
        self.reference_directory.setObjectName("referenceContextValue")
        context_layout.addWidget(self.reference_directory)
        self.reference_documents = QLabel("Arquivos indexados\n—")
        self.reference_documents.setObjectName("referenceContextValue")
        context_layout.addWidget(self.reference_documents)
        details_button = QPushButton("Ver detalhes")
        details_button.setObjectName("contextDetailsButton")
        details_button.setFixedHeight(24)
        details_button.clicked.connect(self.details_requested)
        context_layout.addWidget(details_button)
        layout.addWidget(context_card)

        tools_card = QFrame()
        tools_card.setObjectName("referenceToolsCard")
        tools_card.setMinimumWidth(0)
        tools_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        tools_layout = QVBoxLayout(tools_card)
        tools_layout.setContentsMargins(15, 10, 15, 10)
        tools_layout.setSpacing(2)
        tools_icon = QLabel()
        tools_icon.setPixmap(self._icon("wrench").pixmap(20, 20))
        tools_layout.addWidget(tools_icon, 0, Qt.AlignmentFlag.AlignLeft)
        tools_title = QLabel("Ferramentas")
        tools_title.setObjectName("contextPanelTitle")
        tools_layout.addWidget(tools_title)
        self.tool_buttons = {}
        tool_icons = {
            "Calculadora": "calculator",
            "Pesquisa na Web": "web",
            "Executar Comando": "terminal",
            "Abrir Arquivo": "file",
        }
        for name in ("Calculadora", "Pesquisa na Web", "Executar Comando", "Abrir Arquivo"):
            button = QToolButton()
            button.setObjectName("referenceToolButton")
            button.setText(name)
            button.setIcon(self._icon(tool_icons[name]))
            button.setIconSize(QSize(18, 18))
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            button.setProperty("toolName", name)
            button.setMinimumHeight(29)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            tools_layout.addWidget(button)
            self.tool_buttons[name] = button
        layout.addSpacing(26)
        layout.addWidget(tools_card)

    @staticmethod
    def _icon(name: str) -> QIcon:
        root = Path(__file__).resolve().parents[2]
        return QIcon(str(root / "assets" / "icons" / f"{name}.svg"))

    def set_model(self, model: str, state: str) -> None:
        self.setToolTip(f"Modelo local: {model} · {state}")

    def set_project(self, name: str, active_file: str | None = None) -> None:
        self.reference_project.setText(f"Projeto ativo\n{name}")
        if active_file:
            self.reference_project.setToolTip(f"Arquivo relacionado: {active_file}")

    def set_reference_context(self, context: dict[str, object]) -> None:
        project = str(context.get("project") or context.get("workspace") or "—")
        directory = str(context.get("directory") or context.get("workspace") or "—")
        count = context.get("indexed_documents")
        self.reference_project.setText(f"Projeto ativo\n{project}")
        self.reference_directory.set_full_text(directory)
        self.reference_documents.setText(
            f"Arquivos indexados\n{count} documentos"
            if count is not None
            else "Arquivos indexados\n—"
        )

    def set_active_file(self, path: str | None) -> None:
        if path:
            self.reference_project.setToolTip(f"Arquivo ativo: {path}")
