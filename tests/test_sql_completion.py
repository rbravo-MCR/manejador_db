"""Unit and Integration tests for Autocompletion & IntelliSense with Alias Resolution."""

from __future__ import annotations

import os

from backend_ide.domain.schema import (
    Column,
    DatabaseSchema,
    ForeignKey,
    ForeignKeyColumnMapping,
    NormalizedDataType,
    PrimaryKey,
    Schema,
    Table,
)
from backend_ide.domain.sql.completer import CompletionKind, SqlCompletionEngine
from backend_ide.ui.editor import SqlEditorWidget

os.environ["QT_QPA_PLATFORM"] = "offscreen"


def create_travel_schema() -> DatabaseSchema:
    """Helper providing reservations, customers, and payments schema with real columns."""
    customers_table = Table(
        name="customers",
        schema_name="public",
        columns=[
            Column(
                name="id",
                native_type="INT",
                normalized_type=NormalizedDataType.INTEGER,
                is_primary_key=True,
            ),
            Column(
                name="name",
                native_type="VARCHAR(100)",
                normalized_type=NormalizedDataType.VARCHAR,
            ),
            Column(
                name="email",
                native_type="VARCHAR(255)",
                normalized_type=NormalizedDataType.VARCHAR,
            ),
            Column(
                name="phone",
                native_type="VARCHAR(20)",
                normalized_type=NormalizedDataType.VARCHAR,
            ),
        ],
        primary_key=PrimaryKey(column_names=["id"]),
    )

    reservations_table = Table(
        name="reservations",
        schema_name="public",
        columns=[
            Column(
                name="id",
                native_type="INT",
                normalized_type=NormalizedDataType.INTEGER,
                is_primary_key=True,
            ),
            Column(
                name="customer_id",
                native_type="INT",
                normalized_type=NormalizedDataType.INTEGER,
            ),
            Column(
                name="code",
                native_type="VARCHAR(20)",
                normalized_type=NormalizedDataType.VARCHAR,
            ),
            Column(
                name="total_amount",
                native_type="DECIMAL(10,2)",
                normalized_type=NormalizedDataType.DECIMAL,
            ),
            Column(
                name="created_at",
                native_type="TIMESTAMP",
                normalized_type=NormalizedDataType.TIMESTAMP,
            ),
        ],
        primary_key=PrimaryKey(column_names=["id"]),
        foreign_keys=[
            ForeignKey(
                name="fk_reservations_customer",
                source_schema="public",
                source_table="reservations",
                target_schema="public",
                target_table="customers",
                column_mappings=[
                    ForeignKeyColumnMapping(source_column="customer_id", target_column="id")
                ],
            )
        ],
    )

    return DatabaseSchema(
        engine_name="postgresql",
        database_name="travel_db",
        schemas=[Schema(name="public", tables=[customers_table, reservations_table])],
    )


def test_completion_engine_keywords():
    """Test completion engine matching SQL keywords."""
    engine = SqlCompletionEngine()
    completions = engine.get_completions(prefix="SEL")

    assert len(completions) > 0
    match_select = next((c for c in completions if c.text == "SELECT"), None)
    assert match_select is not None
    assert match_select.kind == CompletionKind.KEYWORD


def test_completion_in_from_clause_suggests_tables():
    """Typing 'FROM ' must prioritize real table names."""
    schema = create_travel_schema()
    engine = SqlCompletionEngine(schema)

    completions = engine.get_completions(prefix="", context_text="SELECT * FROM ")

    # First items must be tables
    assert len(completions) > 0
    first_two = [c.text for c in completions[:2]]
    assert "customers" in first_two or "reservations" in first_two
    assert completions[0].kind == CompletionKind.TABLE


def test_completion_in_select_clause_suggests_fields_from_existing_from_table():
    """Typing 'SELECT ' when document has 'FROM reservations' must prioritize its fields."""
    schema = create_travel_schema()
    engine = SqlCompletionEngine(schema)

    sql_doc = "SELECT \nFROM reservations"
    cursor_line = "SELECT "

    completions = engine.get_completions(prefix="", context_text=cursor_line, full_text=sql_doc)

    # Top items must be columns of reservations
    assert len(completions) > 0
    top_cols = [c.text for c in completions if c.kind == CompletionKind.COLUMN]
    assert "id" in top_cols
    assert "customer_id" in top_cols
    assert "code" in top_cols
    assert "total_amount" in top_cols


def test_dot_completion_for_select_alias_multiline():
    """Must suggest real columns of reservations when typing 'SELECT r.' with table alias."""
    schema = create_travel_schema()
    engine = SqlCompletionEngine(schema)

    sql_doc = "SELECT r.\nFROM reservations r"
    cursor_line = "SELECT r."

    completions = engine.get_completions(prefix="", context_text=cursor_line, full_text=sql_doc)

    col_names = [c.text for c in completions if c.kind == CompletionKind.COLUMN]
    assert "id" in col_names
    assert "customer_id" in col_names
    assert "code" in col_names
    assert "total_amount" in col_names
    assert "created_at" in col_names


def test_dot_completion_for_where_alias():
    """Must suggest real columns of customers when typing 'WHERE c.' in SQL query."""
    schema = create_travel_schema()
    engine = SqlCompletionEngine(schema)

    sql_doc = "SELECT *\nFROM customers c\nWHERE c."
    cursor_line = "WHERE c."

    completions = engine.get_completions(prefix="", context_text=cursor_line, full_text=sql_doc)

    col_names = [c.text for c in completions if c.kind == CompletionKind.COLUMN]
    assert "id" in col_names
    assert "name" in col_names
    assert "email" in col_names
    assert "phone" in col_names


def test_dot_completion_for_join_on_alias():
    """Must suggest real columns of customers when typing 'JOIN customers c ON c.'."""
    schema = create_travel_schema()
    engine = SqlCompletionEngine(schema)

    sql_doc = "SELECT *\nFROM reservations r\nJOIN customers c ON c."
    cursor_line = "JOIN customers c ON c."

    completions = engine.get_completions(prefix="", context_text=cursor_line, full_text=sql_doc)

    col_names = [c.text for c in completions if c.kind == CompletionKind.COLUMN]
    assert "id" in col_names
    assert "name" in col_names
    assert "email" in col_names
    assert "phone" in col_names


def test_sql_completer_integration_with_editor(qtbot):
    """SqlCompleter must populate popup with columns when typing 'SELECT r.' in editor."""
    editor_widget = SqlEditorWidget()
    qtbot.addWidget(editor_widget)

    schema = create_travel_schema()
    editor_widget.set_completion_schema(schema)

    # Set text: multiline query
    editor_widget.set_sql_text("SELECT r.\nFROM reservations r")

    # Position cursor at end of line 1 right after 'r.'
    cursor = editor_widget.editor.textCursor()
    cursor.setPosition(9)  # right after 'SELECT r.'
    editor_widget.editor.setTextCursor(cursor)

    # Trigger popup
    editor_widget.completer.trigger_popup()

    assert editor_widget.completer.model_items.rowCount() >= 5
    first_item_text = editor_widget.completer.model_items.item(0).text()
    assert "🔹" in first_item_text
