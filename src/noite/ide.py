from __future__ import annotations

import ast
import difflib
import re
import threading
from pathlib import Path
from time import perf_counter

from PySide6.QtCore import QDir, QSettings, QSortFilterProxyModel, Qt, QThread, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QKeySequence,
    QShortcut,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
)
from PySide6.QtWidgets import (
    QDialog,
    QDockWidget,
    QFileDialog,
    QFileSystemModel,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QToolBar,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from .activity import make_activity_event
from .workspace import (
    SearchMatch,
    _is_sensitive,
    create_workspace_directory,
    create_workspace_file,
    read_workspace_text,
    save_workspace_text,
    search_workspace_text,
)


class ProjectFileFilter(QSortFilterProxyModel):
    _ignored_directories = {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
    }

    def filterAcceptsRow(self, source_row: int, source_parent) -> bool:
        index = self.sourceModel().index(source_row, 0, source_parent)
        path = Path(self.sourceModel().filePath(index))
        if _is_sensitive(path) or self.sourceModel().fileInfo(index).isSymLink():
            return False
        return not (
            self.sourceModel().isDir(index) and path.name.casefold() in self._ignored_directories
        )


class LineNumberArea(QWidget):
    def __init__(self, editor: CodeEditor) -> None:
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return self.editor.line_number_size()

    def paintEvent(self, event) -> None:
        self.editor.paint_line_numbers(event)


class PythonHighlighter(QSyntaxHighlighter):
    _keywords = (
        "and as assert async await break class continue def del elif else except False "
        "finally for from global if import in is lambda None nonlocal not or pass raise "
        "return True try while with yield"
    )
    _rules = [
        (
            rf"\b({'|'.join(_keywords.split())})\b",
            "#cf91ff",
        ),
        (r"\b\d+(?:\.\d+)?\b", "#e5b567"),
        (r"#[^\n]*", "#778091"),
        (r"(?<![\w])(?:[\"'])(?:\\.|[^\\])*?(?:[\"'])", "#a8c98b"),
        (r"\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\()", "#78b9dc"),
    ]

    def __init__(self, document) -> None:
        super().__init__(document)
        self.rules = []
        for pattern, color in self._rules:
            style = QTextCharFormat()
            style.setForeground(QColor(color))
            self.rules.append((re.compile(pattern), style))

    def highlightBlock(self, text: str) -> None:
        for pattern, style in self.rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), style)


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None, *, python_highlighting: bool = False) -> None:
        super().__init__(parent)
        self._line_area = LineNumberArea(self)
        self.blockCountChanged.connect(self._update_line_number_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._highlight_current_line)
        self._update_line_number_width()
        self._highlight_current_line()
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.highlighter = PythonHighlighter(self.document()) if python_highlighting else None

    def line_number_size(self):
        digits = len(str(max(1, self.blockCount())))
        return self.fontMetrics().horizontalAdvance("9") * digits + 16

    def _update_line_number_width(self, _count: int | None = None) -> None:
        self.setViewportMargins(self.line_number_size(), 0, 0, 0)

    def _update_line_number_area(self, rect, dy: int) -> None:
        if dy:
            self._line_area.scroll(0, dy)
        else:
            self._line_area.update(0, rect.y(), self._line_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_number_width()

    def _highlight_current_line(self) -> None:
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(QColor("#222832"))
        selection.format.setProperty(QTextCharFormat.Property.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection])

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        content = self.contentsRect()
        self._line_area.setGeometry(
            content.left(), content.top(), self.line_number_size(), content.height()
        )

    def paint_line_numbers(self, event) -> None:
        from PySide6.QtGui import QPainter

        painter = QPainter(self._line_area)
        painter.fillRect(event.rect(), QColor("#202126"))
        block = self.firstVisibleBlock()
        number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        painter.setPen(QColor("#777b86"))
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.drawText(
                    0,
                    top,
                    self._line_area.width() - 6,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    str(number + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            number += 1


class WorkspaceSearchWorker(QThread):
    matches_ready = Signal(object)
    failed = Signal(str)
    progress = Signal(str)
    activity = Signal(object)

    def __init__(self, workspace: Path, query: str, parent=None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.query = query
        self._cancel = threading.Event()

    def request_cancel(self) -> None:
        self._cancel.set()

    def run(self) -> None:
        started_at = perf_counter()
        self.activity.emit(
            make_activity_event(
                "Busca no projeto",
                "started",
                "Pesquisa iniciada",
                details=f"Projeto: {self.workspace.name}",
            )
        )
        try:
            matches = search_workspace_text(
                self.workspace,
                self.query,
                cancelled=self._cancel.is_set,
                progress=self.progress.emit,
            )
        except Exception as exc:
            self.activity.emit(
                make_activity_event(
                    "Busca no projeto",
                    "failed",
                    "Pesquisa não concluída",
                    duration_ms=max(0, round((perf_counter() - started_at) * 1000)),
                    details=f"Falha do tipo {type(exc).__name__}.",
                )
            )
            self.failed.emit(f"{type(exc).__name__}: falha na busca do projeto.")
            return
        state = "cancelled" if self._cancel.is_set() else "completed"
        summary = (
            "Pesquisa cancelada"
            if state == "cancelled"
            else f"Pesquisa concluída · {len(matches)} resultado(s)"
        )
        self.activity.emit(
            make_activity_event(
                "Busca no projeto",
                state,
                summary,
                duration_ms=max(0, round((perf_counter() - started_at) * 1000)),
                details=f"Projeto: {self.workspace.name}",
            )
        )
        self.matches_ready.emit(matches)


class WorkspaceSearchDialog(QDialog):
    match_activated = Signal(object)
    activity = Signal(object)

    def __init__(self, workspace: Path, parent=None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.worker: WorkspaceSearchWorker | None = None
        self._close_when_done = False
        self.setWindowTitle("Buscar no projeto")
        self.resize(680, 480)
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Texto a buscar no workspace (case-insensitive)")
        self.search_button = QPushButton("Buscar")
        self.search_button.clicked.connect(self.start_search)
        row.addWidget(self.query_input, 1)
        row.addWidget(self.search_button)
        layout.addLayout(row)
        self.status = QLabel("Arquivos sensíveis, binários e diretórios ignorados são excluídos.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.results = QListWidget()
        self.results.itemDoubleClicked.connect(self._activate_result)
        layout.addWidget(self.results, 1)
        self.cancel_button = QPushButton("Fechar")
        self.cancel_button.clicked.connect(self.close)
        layout.addWidget(self.cancel_button)

    def start_search(self) -> None:
        query = self.query_input.text().strip()
        if not query or len(query) > 200:
            self.status.setText("Digite um termo de 1 a 200 caracteres.")
            return
        if self.worker is not None and self.worker.isRunning():
            return
        self.results.clear()
        self.status.setText("Pesquisando…")
        self.search_button.setEnabled(False)
        self.worker = WorkspaceSearchWorker(self.workspace, query, self)
        self.worker.matches_ready.connect(self._show_matches)
        self.worker.failed.connect(self.status.setText)
        self.worker.progress.connect(self.status.setText)
        self.worker.activity.connect(self.activity.emit)
        self.worker.finished.connect(self._worker_finished)
        self.worker.start()

    def _show_matches(self, matches: list[SearchMatch]) -> None:
        self.results.clear()
        for match in matches:
            item = QListWidgetItem(
                f"{match.path.relative_to(self.workspace)}:{match.line}  {match.excerpt}"
            )
            item.setData(Qt.ItemDataRole.UserRole, match)
            self.results.addItem(item)
        self.status.setText(f"{len(matches)} resultado(s). Dê duplo clique para abrir.")

    def _activate_result(self, item: QListWidgetItem) -> None:
        match = item.data(Qt.ItemDataRole.UserRole)
        self.match_activated.emit(match)
        self.close()

    def _worker_finished(self) -> None:
        self.search_button.setEnabled(True)
        if self.worker is not None:
            self.worker.deleteLater()
            self.worker = None
        if self._close_when_done:
            self.close()

    def closeEvent(self, event) -> None:
        if self.worker is not None and self.worker.isRunning():
            self._close_when_done = True
            self.status.setText("Cancelando a busca…")
            self.worker.request_cancel()
            event.ignore()
            return
        event.accept()


class ProjectDock(QDockWidget):
    workspace_changed = Signal(str)
    activity = Signal(object)
    active_file_changed = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__("Projeto", parent)
        self.setObjectName("projectDock")
        self.workspace: Path | None = None
        self._documents: dict[str, tuple[CodeEditor, str, str, bool]] = {}
        self._last_write_undo: tuple[str, str, str, str, bool] | None = None
        self._model = QFileSystemModel(self)
        self._model.setFilter(QDir.AllDirs | QDir.Files | QDir.NoDotAndDotDot)
        self._file_filter = ProjectFileFilter(self)
        self._file_filter.setSourceModel(self._model)

        root = QWidget(self)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(8, 8, 8, 8)
        toolbar = QToolBar()
        self.open_button = QPushButton("Abrir…")
        self.open_button.clicked.connect(self.choose_workspace)
        self.create_file_button = QPushButton("Arquivo +")
        self.create_file_button.setToolTip("Criar arquivo vazio, após confirmação")
        self.create_file_button.clicked.connect(self.create_file)
        self.create_directory_button = QPushButton("Pasta +")
        self.create_directory_button.setToolTip("Criar pasta, após confirmação")
        self.create_directory_button.clicked.connect(self.create_directory)
        self.find_file_button = QPushButton("Localizar")
        self.find_file_button.setToolTip("Localizar e substituir na aba ativa (Ctrl+F)")
        self.find_file_button.clicked.connect(self.show_find_replace)
        self.search_button = QPushButton("Buscar")
        self.search_button.clicked.connect(self.open_global_search)
        self.save_button = QPushButton("Salvar")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_current)
        self.undo_write_button = QPushButton("Desfazer gravação")
        self.undo_write_button.setEnabled(False)
        self.undo_write_button.setToolTip(
            "Reverter a última gravação feita pelo editor, se o arquivo não mudou desde então"
        )
        self.undo_write_button.clicked.connect(self.undo_last_write)
        self.syntax_button = QPushButton("Sintaxe")
        self.syntax_button.setToolTip(
            "Verificar sintaxe Python no buffer aberto; não executa o arquivo"
        )
        self.syntax_button.clicked.connect(self.check_python_syntax)
        toolbar.addWidget(self.open_button)
        toolbar.addWidget(self.create_file_button)
        toolbar.addWidget(self.create_directory_button)
        toolbar.addWidget(self.find_file_button)
        toolbar.addWidget(self.search_button)
        toolbar.addWidget(self.save_button)
        toolbar.addWidget(self.undo_write_button)
        toolbar.addWidget(self.syntax_button)
        layout.addWidget(toolbar)
        self.find_bar = QWidget()
        find_layout = QHBoxLayout(self.find_bar)
        find_layout.setContentsMargins(0, 0, 0, 0)
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("Localizar (sensível a maiúsculas)")
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Substituir por")
        self.find_next_button = QPushButton("Próximo")
        self.find_next_button.clicked.connect(self.find_next)
        self.find_input.returnPressed.connect(self.find_next)
        self.replace_button = QPushButton("Substituir")
        self.replace_button.clicked.connect(self.replace_current)
        self.replace_all_button = QPushButton("Tudo")
        self.replace_all_button.clicked.connect(self.replace_all)
        self.find_status = QLabel()
        self.find_close_button = QPushButton("×")
        self.find_close_button.setToolTip("Fechar busca")
        self.find_close_button.clicked.connect(self.find_bar.hide)
        for widget in (
            self.find_input,
            self.replace_input,
            self.find_next_button,
            self.replace_button,
            self.replace_all_button,
            self.find_status,
            self.find_close_button,
        ):
            find_layout.addWidget(widget)
        self.find_bar.hide()
        layout.addWidget(self.find_bar)
        self.workspace_label = QLabel("Nenhum projeto aberto")
        self.workspace_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.workspace_label.setWordWrap(True)
        layout.addWidget(self.workspace_label)

        body = QSplitter(Qt.Orientation.Horizontal)
        body.setChildrenCollapsible(False)
        self.tree = QTreeView()
        self.tree.setModel(self._file_filter)
        self.tree.setMinimumWidth(180)
        self.tree.setHeaderHidden(True)
        for column in (1, 2, 3):
            self.tree.hideColumn(column)
        self.tree.doubleClicked.connect(self.open_index)
        body.addWidget(self.tree)
        self.tabs = QTabWidget()
        self.tabs.setMinimumWidth(260)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self._update_save_button)
        body.addWidget(self.tabs)
        body.setSizes([300, 450])
        layout.addWidget(body, 1)
        self.problems = QListWidget()
        self.problems.setMaximumHeight(110)
        self.problems.itemDoubleClicked.connect(self._navigate_to_problem)
        layout.addWidget(self.problems)
        self.setWidget(root)
        self.setMinimumWidth(500)
        self._restore_workspace()
        shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        shortcut.activated.connect(self.show_find_replace)
        self._find_shortcut = shortcut
        self._set_workspace_actions_enabled(self.workspace is not None)

    def _restore_workspace(self) -> None:
        stored = QSettings("cristnzx", "Noite2").value("workspace/last_path", "")
        if stored and Path(stored).is_dir():
            self.set_workspace(Path(stored))

    def choose_workspace(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Abrir projeto")
        if selected:
            self.set_workspace(Path(selected))

    def open_global_search(self) -> None:
        if self.workspace is None:
            QMessageBox.information(self, "Projeto não aberto", "Abra um projeto antes de buscar.")
            return
        existing = getattr(self, "_search_dialog", None)
        if existing is not None and existing.isVisible():
            existing.raise_()
            existing.activateWindow()
            return
        dialog = WorkspaceSearchDialog(self.workspace, self)
        dialog.match_activated.connect(self.open_search_match)
        dialog.activity.connect(self.activity.emit)
        dialog.show()
        self._search_dialog = dialog

    def open_search_match(self, match: SearchMatch) -> None:
        if self.workspace is None:
            return
        source_index = self._model.index(str(match.path))
        index = self._file_filter.mapFromSource(source_index)
        self.open_index(index)
        editor = self.tabs.currentWidget()
        if isinstance(editor, CodeEditor):
            cursor = editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.movePosition(
                QTextCursor.MoveOperation.NextBlock,
                QTextCursor.MoveMode.MoveAnchor,
                max(0, match.line - 1),
            )
            editor.setTextCursor(cursor)
            editor.setFocus()

    def set_workspace(self, path: Path) -> None:
        root = Path(path).resolve(strict=True)
        if not root.is_dir():
            raise ValueError("O projeto precisa ser uma pasta.")
        self.workspace = root
        self._last_write_undo = None
        self.undo_write_button.setEnabled(False)
        self._model.setRootPath(str(root))
        self.tree.setRootIndex(self._file_filter.mapFromSource(self._model.index(str(root))))
        self.workspace_label.setText(str(root))
        QSettings("cristnzx", "Noite2").setValue("workspace/last_path", str(root))
        self._set_workspace_actions_enabled(True)
        self.workspace_changed.emit(str(root))

    def _set_workspace_actions_enabled(self, enabled: bool) -> None:
        for button in (
            self.create_file_button,
            self.create_directory_button,
            self.find_file_button,
            self.search_button,
        ):
            button.setEnabled(enabled)

    def show_find_replace(self) -> None:
        current = self._current_document()
        if current is None:
            QMessageBox.information(
                self, "Nenhum arquivo aberto", "Abra um arquivo antes de localizar texto."
            )
            return
        self.find_bar.show()
        self.find_input.setFocus()
        self.find_input.selectAll()

    def find_next(self) -> bool:
        current = self._current_document()
        query = self.find_input.text()
        if current is None or not query:
            return False
        editor = current[1]
        if editor.find(query, QTextDocument.FindFlag.FindCaseSensitively):
            self.find_status.setText("Encontrado")
            return True
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        editor.setTextCursor(cursor)
        found = editor.find(query, QTextDocument.FindFlag.FindCaseSensitively)
        self.find_status.setText("Encontrado desde o início" if found else "Não encontrado")
        return found

    def replace_current(self) -> bool:
        current = self._current_document()
        query = self.find_input.text()
        if current is None or not query:
            return False
        editor = current[1]
        cursor = editor.textCursor()
        replaced = cursor.hasSelection() and cursor.selectedText() == query
        if replaced:
            cursor.insertText(self.replace_input.text())
            editor.setTextCursor(cursor)
        found = self.find_next()
        if replaced and not found:
            self.find_status.setText("Substituído")
        return replaced or found

    def replace_all(self) -> int:
        current = self._current_document()
        query = self.find_input.text()
        if current is None or not query:
            return 0
        editor = current[1]
        cursor = QTextCursor(editor.document())
        cursor.beginEditBlock()
        count = 0
        while True:
            match = editor.document().find(
                query, cursor, QTextDocument.FindFlag.FindCaseSensitively
            )
            if match.isNull():
                break
            match.insertText(self.replace_input.text())
            cursor = match
            count += 1
        cursor.endEditBlock()
        editor.setTextCursor(cursor)
        self.find_status.setText(f"{count} substituição(ões)")
        return count

    def create_file(self) -> None:
        if self.workspace is None:
            return
        name, accepted = QInputDialog.getText(self, "Criar arquivo", "Nome (na raiz do projeto):")
        if not accepted or not name.strip():
            return
        if (
            QMessageBox.question(
                self,
                "Confirmar criação",
                f"Criar um arquivo vazio em {self.workspace.name}/{name.strip()}?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            != QMessageBox.Yes
        ):
            return
        try:
            path = create_workspace_file(self.workspace, name)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Não foi possível criar", str(exc))
            return
        index = self._file_filter.mapFromSource(self._model.index(str(path)))
        self.open_index(index)

    def create_directory(self) -> None:
        if self.workspace is None:
            return
        name, accepted = QInputDialog.getText(self, "Criar pasta", "Nome (na raiz do projeto):")
        if not accepted or not name.strip():
            return
        if (
            QMessageBox.question(
                self,
                "Confirmar criação",
                f"Criar a pasta {self.workspace.name}/{name.strip()}?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            != QMessageBox.Yes
        ):
            return
        try:
            path = create_workspace_directory(self.workspace, name)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Não foi possível criar", str(exc))
            return
        index = self._file_filter.mapFromSource(self._model.index(str(path)))
        if index.isValid():
            self.tree.setExpanded(index, True)

    def open_index(self, index) -> None:
        if self.workspace is None:
            return
        source_index = self._file_filter.mapToSource(index)
        candidate = Path(self._model.filePath(source_index))
        if candidate.is_dir():
            return
        started_at = perf_counter()
        self.activity.emit(
            make_activity_event(
                "Leitura de arquivo",
                "started",
                f"Lendo arquivo · {candidate.name}",
                details=f"Caminho no projeto: {candidate.relative_to(self.workspace).as_posix()}",
            )
        )
        try:
            document = read_workspace_text(self.workspace, candidate)
        except (OSError, ValueError) as exc:
            self.activity.emit(
                make_activity_event(
                    "Leitura de arquivo",
                    "failed",
                    f"Não foi possível abrir · {candidate.name}",
                    duration_ms=max(0, round((perf_counter() - started_at) * 1000)),
                    details=f"Falha do tipo {type(exc).__name__}.",
                )
            )
            QMessageBox.warning(self, "Não foi possível abrir", str(exc))
            return
        self.activity.emit(
            make_activity_event(
                "Leitura de arquivo",
                "completed",
                f"Arquivo aberto · {candidate.name}",
                duration_ms=max(0, round((perf_counter() - started_at) * 1000)),
                details=f"Caminho no projeto: {candidate.relative_to(self.workspace).as_posix()}",
            )
        )
        key = str(document.path)
        if key in self._documents:
            self.tabs.setCurrentWidget(self._documents[key][0])
            return
        editor = CodeEditor(python_highlighting=document.path.suffix.casefold() in {".py", ".pyw"})
        editor.setFont(QFont("Cascadia Code", 10))
        editor.setPlainText(document.text)
        editor.document().setModified(False)
        editor.document().modificationChanged.connect(
            lambda _dirty, path=key: self._refresh_title(path)
        )
        self._documents[key] = (
            editor,
            document.sha256,
            document.line_ending,
            document.has_utf8_bom,
        )
        tab_index = self.tabs.addTab(editor, document.path.name)
        self.tabs.setTabToolTip(tab_index, key)
        self.tabs.setCurrentIndex(tab_index)
        self._update_save_button()

    def _current_document(self) -> tuple[str, CodeEditor, str, str, bool] | None:
        editor = self.tabs.currentWidget()
        if not isinstance(editor, CodeEditor):
            return None
        for path, (candidate, digest, line_ending, has_bom) in self._documents.items():
            if candidate is editor:
                return path, editor, digest, line_ending, has_bom
        return None

    def active_document_snapshot(self) -> tuple[str, str] | None:
        current = self._current_document()
        if current is None or self.workspace is None:
            return None
        path, editor, _digest, _line_ending, _has_bom = current
        try:
            relative = Path(path).resolve(strict=True).relative_to(self.workspace).as_posix()
        except (OSError, ValueError):
            return None
        return relative, editor.toPlainText()

    def _refresh_title(self, path: str) -> None:
        document = self._documents.get(path)
        if document is None:
            return
        editor = document[0]
        index = self.tabs.indexOf(editor)
        if index >= 0:
            self.tabs.setTabText(
                index,
                f"{Path(path).name}{' •' if editor.document().isModified() else ''}",
            )
            self._update_save_button()

    def _update_save_button(self, _index: int | None = None) -> None:
        current = self._current_document()
        self.save_button.setEnabled(bool(current and current[1].document().isModified()))
        self.find_file_button.setEnabled(current is not None)
        self.syntax_button.setEnabled(current is not None)
        snapshot = self.active_document_snapshot()
        self.active_file_changed.emit(snapshot[0] if snapshot else None)

    def check_python_syntax(self) -> None:
        current = self._current_document()
        if current is None:
            return
        path, editor, _digest, _line_ending, _has_bom = current
        self.problems.clear()
        if Path(path).suffix.casefold() not in {".py", ".pyw"}:
            self.problems.addItem("Verificação de sintaxe disponível apenas para Python.")
            return
        try:
            ast.parse(editor.toPlainText(), filename=Path(path).name)
        except SyntaxError as exc:
            item = QListWidgetItem(
                f"{Path(path).name}:{exc.lineno or 1}:{exc.offset or 1}: "
                f"{exc.msg or 'erro de sintaxe'}"
            )
            item.setData(Qt.ItemDataRole.UserRole, (exc.lineno or 1, exc.offset or 1))
            self.problems.addItem(item)
        else:
            self.problems.addItem(f"{Path(path).name}: sintaxe válida")

    def _navigate_to_problem(self, item: QListWidgetItem) -> None:
        location = item.data(Qt.ItemDataRole.UserRole)
        current = self._current_document()
        if location is None or current is None:
            return
        line, column = location
        cursor = current[1].textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        cursor.movePosition(
            QTextCursor.MoveOperation.NextBlock,
            QTextCursor.MoveMode.MoveAnchor,
            max(0, line - 1),
        )
        cursor.movePosition(
            QTextCursor.MoveOperation.Right,
            QTextCursor.MoveMode.MoveAnchor,
            max(0, column - 1),
        )
        current[1].setTextCursor(cursor)
        current[1].setFocus()

    def save_current(self) -> None:
        current = self._current_document()
        if current is None or self.workspace is None:
            return
        path, editor, digest, line_ending, has_bom = current
        try:
            original = read_workspace_text(self.workspace, Path(path))
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Não foi possível revisar", str(exc))
            return
        proposed = editor.toPlainText()
        if proposed == original.text:
            editor.document().setModified(False)
            self._refresh_title(path)
            return
        diff = "".join(
            difflib.unified_diff(
                original.text.splitlines(keepends=True),
                proposed.splitlines(keepends=True),
                fromfile=f"atual/{Path(path).name}",
                tofile=f"proposta/{Path(path).name}",
            )
        )
        review = QMessageBox(self)
        review.setIcon(QMessageBox.Icon.Question)
        review.setWindowTitle("Revisar alterações")
        review.setText(
            f"Aplicar as alterações em {Path(path).name}?\n"
            "Confira o diff antes de confirmar."
        )
        review.setDetailedText(
            diff[:25_000] + ("\n… diff truncado para exibição." if len(diff) > 25_000 else "")
        )
        review.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        review.setDefaultButton(QMessageBox.StandardButton.No)
        if review.exec() != QMessageBox.StandardButton.Yes:
            return
        try:
            new_digest = save_workspace_text(
                self.workspace,
                Path(path),
                editor.toPlainText(),
                digest,
                line_ending=line_ending,
                has_utf8_bom=has_bom,
            )
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Não foi possível salvar", str(exc))
            return
        self._documents[path] = (editor, new_digest, line_ending, has_bom)
        self._last_write_undo = (
            path,
            original.text,
            new_digest,
            original.line_ending,
            original.has_utf8_bom,
        )
        self.undo_write_button.setEnabled(True)
        editor.document().setModified(False)
        self._refresh_title(path)

    def undo_last_write(self) -> None:
        undo = self._last_write_undo
        if undo is None or self.workspace is None:
            return
        path, prior_text, expected_digest, line_ending, has_bom = undo
        document = self._documents.get(path)
        if document is None:
            QMessageBox.information(
                self, "Desfazer indisponível", "Reabra o arquivo para reverter a última gravação."
            )
            return
        editor = document[0]
        if editor.document().isModified():
            QMessageBox.warning(
                self,
                "Buffer com alterações",
                "Salve ou descarte as alterações atuais antes de desfazer a gravação anterior.",
            )
            return
        if (
            QMessageBox.question(
                self,
                "Confirmar reversão",
                f"Restaurar a versão anterior de {Path(path).name}?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            != QMessageBox.Yes
        ):
            return
        try:
            restored_digest = save_workspace_text(
                self.workspace,
                Path(path),
                prior_text,
                expected_digest,
                line_ending=line_ending,
                has_utf8_bom=has_bom,
            )
        except (OSError, ValueError) as exc:
            QMessageBox.warning(
                self,
                "Não foi possível desfazer",
                f"O arquivo pode ter sido alterado desde a gravação. {exc}",
            )
            return
        editor.setPlainText(prior_text)
        editor.document().setModified(False)
        self._documents[path] = (editor, restored_digest, line_ending, has_bom)
        self._last_write_undo = None
        self.undo_write_button.setEnabled(False)
        self._refresh_title(path)

    def close_tab(self, index: int) -> None:
        editor = self.tabs.widget(index)
        if not isinstance(editor, CodeEditor):
            return
        if editor.document().isModified():
            choice = QMessageBox.question(
                self,
                "Alterações não salvas",
                "Salvar as alterações antes de fechar esta aba?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Cancel,
            )
            if choice == QMessageBox.Cancel:
                return
            if choice == QMessageBox.Save:
                self.tabs.setCurrentWidget(editor)
                self.save_current()
                if editor.document().isModified():
                    return
        for path, (candidate, _digest, _line_ending, _has_bom) in list(self._documents.items()):
            if candidate is editor:
                del self._documents[path]
                break
        self.tabs.removeTab(index)
        editor.deleteLater()
        self._update_save_button()
