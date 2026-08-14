"""Unit and Integration tests for Phase 8 - Intelligent Autocompletion & IntelliSense."""

import os

from backend_ide.domain.schema import (
    Column,
    DatabaseSchema,
    NormalizedDataType,
    PrimaryKey,
    Schema,
    Table,
)
from backend_ide.domain.sql.completer import CompletionKind, SqlCompletionEngine
from backend_ide.ui.editor import SqlEditorWidget

os.environ["QT_QPA_PLATFORM"] = "offscreen"


def create_sample_schema() -> DatabaseSchema:
    """Helper to create sample schema for autocompletion tests."""
    users_table = Table(
        name="users",
        schema_name="public",
        columns=[
            Column(
                name="id",
                native_type="INT",
                normalized_type=NormalizedDataType.INTEGER,
                is_primary_key=True,
            ),
            Column(
                name="email",
                native_type="VARCHAR(255)",
                normalized_type=NormalizedDataType.VARCHAR,
            ),
            Column(
                name="created_at",
                native_type="TIMESTAMP",
                normalized_type=NormalizedDataType.TIMESTAMP,
            ),
        ],
        primary_key=PrimaryKey(column_names=["id"]),
    )

    return DatabaseSchema(
        engine_name="postgresql",
        database_name="app_db",
        schemas=[Schema(name="public", tables=[users_table])],
    )


def test_completion_engine_keywords():
    """Test completion engine matching SQL keywords."""
    engine = SqlCompletionEngine()
    completions = engine.get_completions(prefix="SEL")

    assert len(completions) > 0
    match_select = next((c for c in completions if c.text == "SELECT"), None)
    assert match_select is not None
    assert match_select.kind == CompletionKind.KEYWORD


def test_completion_engine_schema_objects_and_dot_context():
    """Test completion engine matching tables, columns, and dot context."""
    sample_db = create_sample_schema()
    engine = SqlCompletionEngine(sample_db)

    # Match table name 'users'
    table_completions = engine.get_completions(prefix="us")
    assert any(c.text == "users" and c.kind == CompletionKind.TABLE for c in table_completions)

    # Match dot context 'users.' -> columns of users
    dot_completions = engine.get_completions(prefix="", context_text="SELECT users.")
    col_names = [c.text for c in dot_completions]
    assert "id" in col_names
    assert "email" in col_names
    assert "created_at" in col_names


def test_sql_completer_integration(qtbot):
    """Test SqlCompleter popup updating from SqlEditorWidget."""
    editor_widget = SqlEditorWidget(initial_text="SELECT ")
    qtbot.addWidget(editor_widget)

    sample_db = create_sample_schema()
    editor_widget.set_completion_schema(sample_db)

    completer = editor_widget.completer
    assert completer is not None

    completer.update_completions("us", "SELECT us")
    assert completer.model_items.rowCount() > 0
