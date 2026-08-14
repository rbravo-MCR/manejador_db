"""PySide6 QCompleter Integration for SQL IntelliSense Autocompletion."""

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel, QTextCursor
from PySide6.QtWidgets import QCompleter, QListView

from backend_ide.domain.schema import DatabaseSchema
from backend_ide.domain.sql.completer import SqlCompletionEngine


class SqlCompleter(QCompleter):
    """Context-aware autocompleter popup for SqlCodeEditor."""

    def __init__(self, editor, parent=None) -> None:
        super().__init__(parent or editor)
        self.editor = editor
        self.engine = SqlCompletionEngine()

        self.model_items = QStandardItemModel(self)
        self.setModel(self.model_items)
        self.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

        popup = QListView()
        popup.setStyleSheet(
            "QListView { font-family: 'Fira Code', monospace; font-size: 11px; padding: 2px; }"
        )
        self.setPopup(popup)
        self.activated.connect(self._insert_completion)

    def set_schema_model(self, schema_model: DatabaseSchema) -> None:
        """Update schema model for autocomplete engine."""
        self.engine.set_schema_model(schema_model)

    def update_completions(self, prefix: str, context_text: str) -> None:
        """Re-populate popup model with matching completion suggestions."""
        self.model_items.clear()
        completions = self.engine.get_completions(prefix, context_text)

        for item in completions:
            display_text = f"{item.icon_prefix}{item.text}"
            if item.detail:
                display_text += f"   [{item.detail}]"

            model_item = QStandardItem(display_text)
            model_item.setData(item.text, Qt.ItemDataRole.UserRole)
            self.model_items.appendRow(model_item)

    def trigger_popup(self) -> None:
        """Evaluate cursor position and trigger autocomplete popup if appropriate."""
        cursor = self.editor.textCursor()
        block_text = cursor.block().text()[: cursor.positionInBlock()]

        if not block_text.strip():
            self.popup().hide()
            return

        # Find word prefix being typed
        prefix = self._get_word_under_cursor(block_text)
        if len(prefix) < 1 and "." not in block_text:
            self.popup().hide()
            return

        self.update_completions(prefix, block_text)
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
        self.complete(
            QRect(
                self.editor.mapToGlobal(cr.bottomLeft()),
                self.editor.mapToGlobal(cr.topRight()),
            )
        )

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
        clean_text = item_index.data(Qt.ItemDataRole.UserRole)
        if not clean_text:
            clean_text = completion_text.split()[0].replace("🔑", "").replace("📋", "").strip()

        cursor = self.editor.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        cursor.removeSelectedText()
        cursor.insertText(clean_text)
        self.editor.setTextCursor(cursor)
