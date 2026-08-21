"""PySide6 QCompleter Integration for SQL IntelliSense Autocompletion."""

from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QCompleter, QListView

from backend_ide.domain.schema import DatabaseSchema
from backend_ide.domain.sql.completer import SqlCompletionEngine


class SqlCompleter(QCompleter):
    """Context-aware autocompleter popup for SqlCodeEditor."""

    def __init__(self, editor, parent=None) -> None:
        super().__init__(parent or editor)
        self.editor = editor
        self.setWidget(self.editor)
        self.editor._completer = self
        self.engine = SqlCompletionEngine()
        self.current_prefix: str = ""

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
        self.editor.trigger_completion.connect(self.trigger_popup)

    def set_schema_model(self, schema_model: DatabaseSchema) -> None:
        """Update schema model for autocomplete engine."""
        self.engine.set_schema_model(schema_model)

    def update_completions(self, prefix: str, context_text: str, full_text: str = "") -> None:
        """Re-populate popup model with matching completion suggestions."""
        self.model_items.clear()
        self.current_prefix = prefix
        completions = self.engine.get_completions(
            prefix=prefix, context_text=context_text, full_text=full_text
        )

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
        full_text = self.editor.toPlainText()

        if not block_text.strip():
            self.popup().hide()
            return

        # Find word prefix being typed
        prefix = self._get_word_under_cursor(block_text)
        is_after_dot = bool(re.search(r"\.[\w]*$", block_text.strip()))
        is_context_trigger = (
            is_after_dot
            or self.engine._is_table_context(block_text)
            or self.engine._is_join_context(block_text)
            or self.engine._is_column_context(block_text)
        )

        if len(prefix) < 1 and not is_context_trigger:
            self.popup().hide()
            return

        self.update_completions(prefix=prefix, context_text=block_text, full_text=full_text)
        if self.model_items.rowCount() == 0:
            self.popup().hide()
            return

        # Select first item by default
        self.popup().setCurrentIndex(self.model_items.index(0, 0))

        # Calculate popup position at cursor in widget coordinates
        cr = self.editor.cursorRect()
        cr.setWidth(
            self.popup().sizeHintForColumn(0)
            + self.popup().verticalScrollBar().sizeHint().width()
            + 30
        )
        self.complete(cr)

    def _get_word_under_cursor(self, block_text: str) -> str:
        """Extract word or sub-identifier prefix under cursor."""
        match = re.search(r"([a-zA-Z_][\w]*)$", block_text)
        if match:
            return match.group(1)
        return ""

    def _insert_completion(self, completion_text: str) -> None:
        """Insert selected completion item into editor at cursor."""
        item_index = self.popup().currentIndex()
        clean_text = item_index.data(Qt.ItemDataRole.UserRole)
        if not clean_text:
            clean_text = (
                completion_text.split()[0]
                .replace("🔑", "")
                .replace("📋", "")
                .replace("🔹", "")
                .replace("🔗", "")
                .strip()
            )

        cursor = self.editor.textCursor()
        prefix = self.current_prefix

        if prefix:
            for _ in range(len(prefix)):
                cursor.deletePreviousChar()

        cursor.insertText(clean_text)
        self.editor.setTextCursor(cursor)
