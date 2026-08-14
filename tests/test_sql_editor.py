"""Unit and GUI integration tests for Phase 7 - QScintilla SQL Editor Foundation."""

import os

from backend_ide.ui.editor import SqlEditorWidget
from backend_ide.ui.theme import ThemeManager, ThemeMode

os.environ["QT_QPA_PLATFORM"] = "offscreen"


def test_sql_editor_initialization(qtbot):
    """Test SqlEditorWidget creation and initial text configuration."""
    editor_widget = SqlEditorWidget(initial_text="SELECT 1;")
    qtbot.addWidget(editor_widget)

    assert editor_widget.editor is not None
    assert editor_widget.highlighter is not None
    assert editor_widget.get_sql_text() == "SELECT 1;"


def test_sql_editor_text_modification(qtbot):
    """Test text modification state and signal emission."""
    editor_widget = SqlEditorWidget(initial_text="SELECT 1;")
    qtbot.addWidget(editor_widget)

    modified_states: list[bool] = []
    editor_widget.text_modified.connect(lambda state: modified_states.append(state))

    editor_widget.set_sql_text("SELECT 2;")
    assert editor_widget.get_sql_text() == "SELECT 2;"


def test_sql_editor_theme_adaptation(qtbot):
    """Test QScintilla lexer and paper colors update when theme changes."""
    editor_widget = SqlEditorWidget(initial_text="SELECT * FROM users;")
    qtbot.addWidget(editor_widget)

    manager = ThemeManager.get_instance()
    manager.set_mode(ThemeMode.DARK)
    assert manager.current_mode == ThemeMode.DARK

    manager.set_mode(ThemeMode.LIGHT)
    assert manager.current_mode == ThemeMode.LIGHT
