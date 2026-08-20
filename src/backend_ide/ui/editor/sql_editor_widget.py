"""Native PySide6 SQL Editor Surface with Line Numbers, Syntax Highlighting, and Autocomplete."""

from __future__ import annotations

import re

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextDocument,
    QTextFormat,
)
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit, QVBoxLayout, QWidget

from backend_ide.domain.schema import DatabaseSchema
from backend_ide.domain.sql.constants import SQL_KEYWORDS, SQL_TYPES
from backend_ide.ui.editor.sql_completer import SqlCompleter
from backend_ide.ui.theme import ThemeManager, ThemeMode


class SqlSyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for SQL queries in PySide6."""

    def __init__(self, document: QTextDocument) -> None:
        super().__init__(document)
        self.rules: list[tuple[re.Pattern[str], QTextCharFormat]] = []
        self._fmt_keyword = QTextCharFormat()
        self._fmt_type = QTextCharFormat()
        self._fmt_string = QTextCharFormat()
        self._fmt_comment = QTextCharFormat()
        self._fmt_number = QTextCharFormat()
        self._update_rules()

    def set_theme_colors(self, mode_str: str, palette) -> None:
        """Update syntax highlighting colors based on theme."""
        if mode_str == ThemeMode.DARK.value:
            self._fmt_keyword.setForeground(QColor("#cba6f7"))
            self._fmt_keyword.setFontWeight(QFont.Weight.Bold)
            self._fmt_type.setForeground(QColor("#89b4fa"))
            self._fmt_string.setForeground(QColor("#a6e3a1"))
            self._fmt_comment.setForeground(QColor("#6c7086"))
            self._fmt_comment.setFontItalic(True)
            self._fmt_number.setForeground(QColor("#fab387"))
        else:
            self._fmt_keyword.setForeground(QColor("#8839ef"))
            self._fmt_keyword.setFontWeight(QFont.Weight.Bold)
            self._fmt_type.setForeground(QColor("#1e66f5"))
            self._fmt_string.setForeground(QColor("#40a02b"))
            self._fmt_comment.setForeground(QColor("#8c8fa1"))
            self._fmt_comment.setFontItalic(True)
            self._fmt_number.setForeground(QColor("#fe640b"))

        self._update_rules()
        self.rehighlight()

    def _update_rules(self) -> None:
        """Build regex matching rules."""
        self.rules.clear()

        # Keywords
        kw_pattern = r"\b(" + "|".join(SQL_KEYWORDS) + r")\b"
        self.rules.append((re.compile(kw_pattern, re.IGNORECASE), self._fmt_keyword))

        # Types
        type_pattern = r"\b(" + "|".join(SQL_TYPES) + r")\b"
        self.rules.append((re.compile(type_pattern, re.IGNORECASE), self._fmt_type))

        # Numbers
        self.rules.append((re.compile(r"\b\d+(\.\d+)?\b"), self._fmt_number))

        # Single and Double Quoted Strings
        self.rules.append((re.compile(r"'[^']*'"), self._fmt_string))
        self.rules.append((re.compile(r'"[^"]*"'), self._fmt_string))

        # Comments
        self.rules.append((re.compile(r"--[^\n]*"), self._fmt_comment))
        self.rules.append((re.compile(r"/\*.*?\*/", re.DOTALL), self._fmt_comment))

    def highlightBlock(self, text: str) -> None:
        """Apply highlighting rules to text block."""
        for pattern, fmt in self.rules:
            for match in pattern.finditer(text):
                start, end = match.span()
                self.setFormat(start, end - start, fmt)


class LineNumberArea(QWidget):
    """Left margin widget for displaying line numbers."""

    def __init__(self, editor: SqlCodeEditor) -> None:
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event) -> None:
        self.code_editor.line_number_area_paint_event(event)


class SqlCodeEditor(QPlainTextEdit):
    """Subclassed QPlainTextEdit providing line numbers and completion signals."""

    text_modified = Signal(bool)
    trigger_completion = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)

        font = QFont("Fira Code", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        self.setFont(font)

        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.document().modificationChanged.connect(self._on_modification_changed)
        self.textChanged.connect(self._on_text_changed)

        self.update_line_number_area_width(0)
        self.highlight_current_line()

    def _on_modification_changed(self, modified: bool) -> None:
        self.text_modified.emit(modified)

    def _on_text_changed(self) -> None:
        self.trigger_completion.emit()

    def line_number_area_width(self) -> int:
        digits = max(1, len(str(self.blockCount())))
        space = 15 + self.fontMetrics().horizontalAdvance("9") * digits
        return space

    def update_line_number_area_width(self, _new_block_count: int) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def highlight_current_line(self) -> None:
        extra_selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor(ThemeManager.get_instance().current_palette.bg_hover)
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.setExtraSelections(extra_selections)

    def line_number_area_paint_event(self, event) -> None:
        painter = QPainter(self.line_number_area)
        p = ThemeManager.get_instance().current_palette
        painter.fillRect(event.rect(), QColor(p.bg_sidebar))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor(p.text_muted))
                painter.drawText(
                    0,
                    top,
                    self.line_number_area.width() - 5,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    number,
                )
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1


class SqlEditorWidget(QWidget):
    """Advanced SQL editing surface with syntax highlighting and IntelliSense."""

    text_modified = Signal(bool)

    def __init__(self, initial_text: str = "", parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.editor = SqlCodeEditor(self)
        self.highlighter = SqlSyntaxHighlighter(self.editor.document())
        self.completer = SqlCompleter(self.editor, self)
        layout.addWidget(self.editor)

        self.editor.text_modified.connect(self.text_modified.emit)

        if initial_text:
            self.set_sql_text(initial_text)

        self._theme_manager = ThemeManager.get_instance()
        self._theme_manager.theme_changed.connect(self._apply_theme)
        self._apply_theme(self._theme_manager.current_mode.value)

    def set_completion_schema(self, schema_model: DatabaseSchema) -> None:
        """Update schema model for autocompletion engine."""
        self.completer.set_schema_model(schema_model)

    def _apply_theme(self, mode_str: str) -> None:
        p = self._theme_manager.current_palette
        style = f"""
        QPlainTextEdit {{
            background-color: {p.bg_surface};
            color: {p.text_primary};
            border: none;
        }}
        """
        self.editor.setStyleSheet(style)
        self.highlighter.set_theme_colors(self._theme_manager.resolved_mode.value, p)
        self.editor.highlight_current_line()

    def get_sql_text(self) -> str:
        """Return the selected SQL, or the complete document when there is no selection."""
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            selected = cursor.selectedText().replace("\u2029", "\n").replace("\u2028", "\n")
            return selected.strip()
        return self.editor.toPlainText().strip()

    def set_sql_text(self, text: str) -> None:
        self.editor.setPlainText(text)
        self.editor.document().setModified(False)
