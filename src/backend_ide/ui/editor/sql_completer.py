"""PySide6 QCompleter Integration for SQL IntelliSense Autocompletion."""

import qtawesome as qta
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel, QTextCursor
from PySide6.QtWidgets import QCompleter, QListView

from backend_ide.domain.schema import DatabaseSchema
from backend_ide.domain.sql.completer import CompletionKind, SqlCompletionEngine
from backend_ide.ui.theme import ThemeManager

KIND_ICONS = {
    CompletionKind.KEYWORD: "fa6s.key",
    CompletionKind.TYPE: "fa6s.tag",
    CompletionKind.SCHEMA: "fa6s.box",
    CompletionKind.TABLE: "fa6s.table",
    CompletionKind.VIEW: "fa6s.eye",
    CompletionKind.COLUMN: "fa6s.table-columns",
    CompletionKind.FUNCTION: "fa6s.bolt",
    CompletionKind.PROCEDURE: "fa6s.gears",
    CompletionKind.ALIAS: "fa6s.at",
    CompletionKind.SNIPPET: "fa6s.code",
}


class SqlCompleter(QCompleter):
    """Context-aware autocompleter popup for SqlCodeEditor."""

    def __init__(self, editor, parent=None) -> None:
        super().__init__(parent or editor)
        self.editor = editor
        self.setWidget(editor)
        self.engine = SqlCompletionEngine()

        self.model_items = QStandardItemModel(self)
        self.setModel(self.model_items)
        self.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

        popup = QListView()
        popup.setObjectName("completion_popup")
        self.setPopup(popup)
        self.activated.connect(self._insert_completion)

    def set_schema_model(self, schema_model: DatabaseSchema) -> None:
        """Update schema model for autocomplete engine."""
        self.engine.set_schema_model(schema_model)

    def update_completions(
        self,
        prefix: str,
        context_text: str,
        cursor_position: int | None = None,
    ) -> None:
        """Re-populate popup model with matching completion suggestions."""
        self.model_items.clear()
        if cursor_position is None:
            completions = self.engine.get_completions(prefix, context_text)
        else:
            completions = self.engine.complete(context_text, cursor_position)
        palette = ThemeManager.get_instance().current_palette

        for item in completions:
            display_text = item.text
            if item.detail:
                display_text += f"   [{item.detail}]"

            model_item = QStandardItem(display_text)
            model_item.setIcon(qta.icon(KIND_ICONS[item.kind], color=palette.text_secondary))
            model_item.setData(item.text, Qt.ItemDataRole.UserRole)
            model_item.setData(item.insert_text, Qt.ItemDataRole.UserRole + 1)
            model_item.setData(item.kind.value, Qt.ItemDataRole.UserRole + 2)
            if item.documentation:
                model_item.setToolTip(item.documentation)
            self.model_items.appendRow(model_item)

    def trigger_popup(self, *, force: bool = False) -> None:
        """Evaluate cursor position and trigger autocomplete popup if appropriate."""
        cursor = self.editor.textCursor()
        block_text = cursor.block().text()[: cursor.positionInBlock()]

        if not block_text.strip() and not force:
            self.popup().hide()
            return

        # Find word prefix being typed
        prefix = self._get_word_under_cursor(block_text)
        if len(prefix) < 1 and "." not in block_text and not force:
            self.popup().hide()
            return

        self.update_completions(prefix, self.editor.toPlainText(), cursor.position())
        if self.model_items.rowCount() == 0:
            self.popup().hide()
            return

        # Calculate popup position at cursor
        cr = self.editor.cursorRect()
        cr.setWidth(
            self.popup().sizeHintForColumn(0)
            + self.popup().verticalScrollBar().sizeHint().width()
            + 20
        )
        self.complete(cr)
        first_index = self.model_items.index(0, 0)
        self.popup().setCurrentIndex(first_index)

    def eventFilter(self, watched, event) -> bool:
        """Accept the highlighted suggestion with Tab while the popup is visible."""
        if (
            watched is self.editor
            and event.type() == QEvent.Type.KeyPress
            and event.key() in (Qt.Key.Key_Tab, Qt.Key.Key_Return, Qt.Key.Key_Enter)
            and self.popup().isVisible()
        ):
            return self._accept_current()
        if (
            watched is self.editor
            and event.type() == QEvent.Type.KeyPress
            and event.key() == Qt.Key.Key_Escape
            and self.popup().isVisible()
        ):
            self.popup().hide()
            return True
        return super().eventFilter(watched, event)

    def _accept_current(self) -> bool:
        index = self.popup().currentIndex()
        if not index.isValid() and self.model_items.rowCount() > 0:
            index = self.model_items.index(0, 0)
            self.popup().setCurrentIndex(index)
        if not index.isValid():
            return False
        self._insert_completion(index.data(Qt.ItemDataRole.DisplayRole))
        self.popup().hide()
        return True

    def _get_word_under_cursor(self, block_text: str) -> str:
        """Extract word under cursor."""
        words = block_text.replace("(", " ").replace(")", " ").replace(",", " ").split()
        if words:
            last = words[-1]
            if "." in last:
                return last.split(".")[-1]
            return last
        return ""

    def _insert_completion(self, completion_text: str) -> None:
        """Insert selected completion item into editor at cursor."""
        # Retrieve original clean token text from UserRole data
        item_index = self.popup().currentIndex()
        clean_text = item_index.data(Qt.ItemDataRole.UserRole + 1)
        if not clean_text:
            clean_text = item_index.data(Qt.ItemDataRole.UserRole)
        if not clean_text:
            clean_text = completion_text.split()[0].strip()

        cursor = self.editor.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        cursor.removeSelectedText()
        cursor.insertText(clean_text)
        self.editor.setTextCursor(cursor)
