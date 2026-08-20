"""Unit and Integration tests for Phase 8 - Intelligent Autocompletion & IntelliSense."""

import os
from time import perf_counter

from PySide6.QtCore import Qt

from backend_ide.domain.schema import (
    Column,
    DatabaseSchema,
    Function,
    NormalizedDataType,
    PrimaryKey,
    Schema,
    Table,
    View,
)
from backend_ide.domain.sql.completer import CompletionKind, SqlCompletionEngine
from backend_ide.domain.sql.dialects import get_dialect_provider
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
            Column(name="user_status", native_type="VARCHAR(30)"),
            Column(
                name="created_at",
                native_type="TIMESTAMP",
                normalized_type=NormalizedDataType.TIMESTAMP,
            ),
        ],
        primary_key=PrimaryKey(column_names=["id"]),
    )

    reservations_table = Table(
        name="reservations",
        schema_name="public",
        columns=[
            Column(name="id", native_type="BIGINT", is_primary_key=True),
            Column(name="confirmation_number", native_type="VARCHAR(40)"),
            Column(name="customer_id", native_type="BIGINT"),
            Column(name="status", native_type="VARCHAR(30)"),
        ],
    )

    return DatabaseSchema(
        engine_name="postgresql",
        database_name="app_db",
        schemas=[
            Schema(
                name="public",
                tables=[users_table, reservations_table],
                views=[View(name="active_users", schema_name="public")],
                functions=[
                    Function(name="calculate_total", schema_name="public", return_type="numeric")
                ],
            )
        ],
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


def test_completion_engine_resolves_multiline_schema_qualified_alias():
    """Typing an alias prefix must suggest columns from its table declaration."""
    engine = SqlCompletionEngine(create_sample_schema())

    completions = engine.get_completions(
        prefix="em",
        context_text="SELECT c.em\nFROM public.users AS c",
    )

    assert [item.text for item in completions] == ["email"]
    assert completions[0].kind == CompletionKind.COLUMN


def test_complete_uses_sources_after_cursor_for_alias_columns():
    engine = SqlCompletionEngine(create_sample_schema())
    sql = "SELECT r.\nFROM reservations r"

    completions = engine.complete(sql, len("SELECT r."))

    assert [item.text for item in completions] == [
        "id",
        "confirmation_number",
        "customer_id",
        "status",
    ]


def test_complete_resolves_join_where_update_and_insert_columns():
    engine = SqlCompletionEngine(create_sample_schema())
    cases = {
        "SELECT * FROM users u JOIN reservations r ON r.cus": "customer_id",
        "SELECT * FROM users u WHERE u.em": "email",
        "UPDATE users SET ema": "email",
        "INSERT INTO users (ema": "email",
    }

    for sql, expected in cases.items():
        suggestions = engine.complete(sql, len(sql))
        assert suggestions[0].text == expected
        assert suggestions[0].kind == CompletionKind.COLUMN


def test_schema_dot_returns_only_tables_and_views_from_that_schema():
    engine = SqlCompletionEngine(create_sample_schema())
    sql = "SELECT * FROM public."

    suggestions = engine.complete(sql, len(sql))

    assert {item.text for item in suggestions} == {"users", "reservations", "active_users"}
    assert {item.kind for item in suggestions} == {CompletionKind.TABLE, CompletionKind.VIEW}


def test_contextual_ranking_prioritizes_columns_over_generic_keywords():
    engine = SqlCompletionEngine(create_sample_schema())
    sql = "SELECT us FROM users"
    cursor = len("SELECT us")

    suggestions = engine.complete(sql, cursor)

    assert suggestions[0].text == "user_status"
    assert suggestions[0].kind == CompletionKind.COLUMN
    using = next((item for item in suggestions if item.text == "USING"), None)
    if using is not None:
        assert suggestions.index(using) > 0


def test_fuzzy_matching_finds_table_without_prefix_match():
    engine = SqlCompletionEngine(create_sample_schema())
    sql = "SELECT * FROM rsv"

    suggestions = engine.complete(sql, len(sql))

    assert any(item.text == "reservations" for item in suggestions)


def test_dialect_functions_and_cached_database_functions_are_available():
    postgres = SqlCompletionEngine(create_sample_schema())
    sqlite_schema = create_sample_schema().model_copy(update={"engine_name": "sqlite"})
    sqlite = SqlCompletionEngine(sqlite_schema)

    postgres_names = {item.text for item in postgres.complete("SELECT date_tr", 14)}
    sqlite_names = {item.text for item in sqlite.complete("SELECT strf", 11)}
    cached_names = {item.text for item in postgres.complete("SELECT calculate", 16)}

    assert "DATE_TRUNC" in postgres_names
    assert "STRFTIME" in sqlite_names
    assert "calculate_total" in cached_names
    assert "DATE_TRUNC" not in {item.text for item in sqlite.complete("SELECT date_tr", 14)}


def test_four_dialect_providers_are_available_without_ui_conditionals():
    assert get_dialect_provider("postgresql").name == "postgresql"
    assert get_dialect_provider("mysql").name == "mysql"
    assert get_dialect_provider("mariadb").name == "mysql"
    assert get_dialect_provider("sqlite").name == "sqlite"
    assert get_dialect_provider("sqlserver").name == "sqlserver"


def test_basic_snippet_is_ranked_for_its_trigger():
    suggestions = SqlCompletionEngine().complete("sel", 3)

    snippet = next(item for item in suggestions if item.kind == CompletionKind.SNIPPET)
    assert snippet.text == "sel"
    assert snippet.insert_text == "SELECT *\nFROM table_name;"


def test_cached_completion_stays_under_budget_and_caps_large_catalog_results():
    large_schema = DatabaseSchema(
        engine_name="postgresql",
        database_name="large_app",
        schemas=[
            Schema(
                name="public",
                tables=[Table(name=f"customer_event_{index}") for index in range(2000)],
            )
        ],
    )
    engine = SqlCompletionEngine(large_schema)
    sql = "SELECT * FROM cstmr_ev_1999"

    started = perf_counter()
    suggestions = engine.complete(sql, len(sql))
    elapsed_ms = (perf_counter() - started) * 1000

    assert elapsed_ms < 100
    assert suggestions[0].text == "customer_event_1999"
    assert len(suggestions) <= 200


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


def test_completion_popup_uses_clean_text_icons_and_global_theme(qtbot):
    """Suggestions must use real icons and inherit the centralized popup theme."""
    editor_widget = SqlEditorWidget()
    qtbot.addWidget(editor_widget)
    editor_widget.set_completion_schema(create_sample_schema())

    editor_widget.completer.update_completions("us", "SELECT us")
    item = next(
        editor_widget.completer.model_items.item(row)
        for row in range(editor_widget.completer.model_items.rowCount())
        if editor_widget.completer.model_items.item(row).data(Qt.ItemDataRole.UserRole) == "users"
    )

    assert item.text() == "users   [Table (public)]"
    assert not item.icon().isNull()
    assert editor_widget.completer.popup().objectName() == "completion_popup"
    assert editor_widget.completer.popup().styleSheet() == ""


def test_typing_automatically_populates_intellisense_popup(qtbot):
    """Editor keystrokes must drive real completion suggestions without manual plumbing."""
    editor_widget = SqlEditorWidget()
    qtbot.addWidget(editor_widget)
    editor_widget.set_completion_schema(create_sample_schema())
    editor_widget.show()
    editor_widget.editor.setFocus()
    assert editor_widget.completer.widget() is editor_widget.editor

    qtbot.keyClicks(editor_widget.editor, "SEL")

    qtbot.waitUntil(lambda: editor_widget.completer.model_items.rowCount() > 0, timeout=1000)
    suggestions = [
        editor_widget.completer.model_items.item(row).data(Qt.ItemDataRole.UserRole)
        for row in range(editor_widget.completer.model_items.rowCount())
    ]
    assert "SELECT" in suggestions


def test_automatic_completion_is_debounced_but_remains_responsive(qtbot):
    editor_widget = SqlEditorWidget()
    qtbot.addWidget(editor_widget)
    editor_widget.show()
    editor_widget.editor.setFocus()

    qtbot.keyClicks(editor_widget.editor, "SEL")

    assert editor_widget.completer.model_items.rowCount() == 0
    qtbot.waitUntil(lambda: editor_widget.completer.model_items.rowCount() > 0, timeout=500)
    assert editor_widget.completion_timer.interval() == 150


def test_dot_opens_alias_columns_immediately_without_waiting_for_debounce(qtbot):
    editor_widget = SqlEditorWidget()
    qtbot.addWidget(editor_widget)
    editor_widget.set_completion_schema(create_sample_schema())
    editor_widget.set_sql_text("SELECT u\nFROM users u")
    cursor = editor_widget.editor.textCursor()
    cursor.setPosition(len("SELECT u"))
    editor_widget.editor.setTextCursor(cursor)
    editor_widget.completer.model_items.clear()
    editor_widget.show()
    editor_widget.editor.setFocus()

    qtbot.keyClick(editor_widget.editor, Qt.Key.Key_Period)

    suggestions = [
        editor_widget.completer.model_items.item(row).data(Qt.ItemDataRole.UserRole)
        for row in range(editor_widget.completer.model_items.rowCount())
    ]
    assert "email" in suggestions
    assert editor_widget.completion_timer.isActive() is False


def test_popup_uses_full_document_to_complete_alias_on_another_line(qtbot):
    """Alias completion must inspect the statement beyond the cursor's current line."""
    editor_widget = SqlEditorWidget()
    qtbot.addWidget(editor_widget)
    editor_widget.set_completion_schema(create_sample_schema())
    sql = "SELECT c.em\nFROM public.users AS c"
    editor_widget.set_sql_text(sql)
    cursor = editor_widget.editor.textCursor()
    cursor.setPosition(len("SELECT c.em"))
    editor_widget.editor.setTextCursor(cursor)

    editor_widget.completer.trigger_popup()

    suggestions = [
        editor_widget.completer.model_items.item(row).data(Qt.ItemDataRole.UserRole)
        for row in range(editor_widget.completer.model_items.rowCount())
    ]
    assert suggestions == ["email"]


def test_ctrl_space_manually_opens_intellisense(qtbot):
    """The documented keyboard command must request suggestions at the cursor."""
    editor_widget = SqlEditorWidget()
    qtbot.addWidget(editor_widget)
    editor_widget.set_completion_schema(create_sample_schema())
    editor_widget.set_sql_text("SELECT us")
    cursor = editor_widget.editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    editor_widget.editor.setTextCursor(cursor)
    editor_widget.completer.model_items.clear()
    editor_widget.show()
    editor_widget.editor.setFocus()

    qtbot.keyClick(
        editor_widget.editor,
        Qt.Key.Key_Space,
        modifier=Qt.KeyboardModifier.ControlModifier,
    )

    qtbot.waitUntil(lambda: editor_widget.completer.model_items.rowCount() > 0, timeout=1000)
    suggestions = [
        editor_widget.completer.model_items.item(row).data(Qt.ItemDataRole.UserRole)
        for row in range(editor_widget.completer.model_items.rowCount())
    ]
    assert "users" in suggestions


def test_ctrl_space_shows_suggestions_in_an_empty_editor(qtbot):
    """Manual IntelliSense must work without requiring an initial character."""
    editor_widget = SqlEditorWidget()
    qtbot.addWidget(editor_widget)
    editor_widget.set_completion_schema(create_sample_schema())
    editor_widget.show()
    editor_widget.editor.setFocus()

    qtbot.keyClick(
        editor_widget.editor,
        Qt.Key.Key_Space,
        modifier=Qt.KeyboardModifier.ControlModifier,
    )

    qtbot.waitUntil(lambda: editor_widget.completer.model_items.rowCount() > 0, timeout=1000)
    suggestions = [
        editor_widget.completer.model_items.item(row).data(Qt.ItemDataRole.UserRole)
        for row in range(editor_widget.completer.model_items.rowCount())
    ]
    assert "users" in suggestions
    assert "SELECT" in suggestions


def test_tab_accepts_current_completion_and_replaces_only_prefix(qtbot):
    """Tab must accept the highlighted suggestion instead of inserting indentation."""
    editor_widget = SqlEditorWidget()
    qtbot.addWidget(editor_widget)
    editor_widget.set_completion_schema(create_sample_schema())
    editor_widget.set_sql_text("SELECT us")
    cursor = editor_widget.editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    editor_widget.editor.setTextCursor(cursor)
    editor_widget.show()
    editor_widget.editor.setFocus()
    editor_widget.completer.trigger_popup()
    users_index = next(
        editor_widget.completer.model_items.index(row, 0)
        for row in range(editor_widget.completer.model_items.rowCount())
        if editor_widget.completer.model_items.item(row).data(Qt.ItemDataRole.UserRole) == "users"
    )
    editor_widget.completer.popup().setCurrentIndex(users_index)

    qtbot.keyClick(editor_widget.editor, Qt.Key.Key_Tab)

    assert editor_widget.editor.toPlainText() == "SELECT users"


def test_enter_accepts_completion_and_escape_dismisses_popup(qtbot):
    editor_widget = SqlEditorWidget()
    qtbot.addWidget(editor_widget)
    editor_widget.set_completion_schema(create_sample_schema())
    editor_widget.set_sql_text("SELECT us")
    cursor = editor_widget.editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    editor_widget.editor.setTextCursor(cursor)
    editor_widget.show()
    editor_widget.editor.setFocus()
    editor_widget.completer.trigger_popup()
    users_index = next(
        editor_widget.completer.model_items.index(row, 0)
        for row in range(editor_widget.completer.model_items.rowCount())
        if editor_widget.completer.model_items.item(row).data(Qt.ItemDataRole.UserRole) == "users"
    )
    editor_widget.completer.popup().setCurrentIndex(users_index)

    qtbot.keyClick(editor_widget.editor, Qt.Key.Key_Return)

    assert editor_widget.editor.toPlainText() == "SELECT users"
    editor_widget.completer.trigger_popup(force=True)
    assert editor_widget.completer.popup().isVisible()
    qtbot.keyClick(editor_widget.editor, Qt.Key.Key_Escape)
    assert not editor_widget.completer.popup().isVisible()


def test_popup_model_exposes_insert_text_and_documentation(qtbot):
    editor_widget = SqlEditorWidget()
    qtbot.addWidget(editor_widget)
    editor_widget.set_completion_schema(create_sample_schema())

    editor_widget.completer.update_completions("em", "SELECT u.em\nFROM users u", 11)
    item = editor_widget.completer.model_items.item(0)

    assert item.data(Qt.ItemDataRole.UserRole) == "email"
    assert item.data(Qt.ItemDataRole.UserRole + 1) == "email"
    assert "VARCHAR(255)" in item.toolTip()
