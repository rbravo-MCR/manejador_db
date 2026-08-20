"""Cursor-aware SQL context analysis independent from Qt."""

from backend_ide.domain.sql.context import SQLContextAnalyzer


def test_analyzer_resolves_join_alias_at_cursor():
    sql = "SELECT * FROM users u JOIN orders o ON o."

    context = SQLContextAnalyzer().analyze(sql, len(sql))

    assert context.qualifier == "o"
    assert context.aliases == {"u": "users", "o": "orders"}
    assert context.tables == ("users", "orders")
    assert context.clause == "ON"


def test_analyzer_reads_sources_after_cursor_in_the_current_statement():
    sql = "SELECT r.\nFROM reservations r"
    cursor = len("SELECT r.")

    context = SQLContextAnalyzer().analyze(sql, cursor)

    assert context.qualifier == "r"
    assert context.aliases == {"r": "reservations"}
    assert context.tables == ("reservations",)


def test_analyzer_isolates_current_statement():
    sql = "SELECT x. FROM old x; SELECT u. FROM users u"

    context = SQLContextAnalyzer().analyze(sql, len(sql))

    assert context.statement == " SELECT u. FROM users u"
    assert context.aliases == {"u": "users"}
    assert context.tables == ("users",)


def test_analyzer_detects_relation_and_schema_context():
    sql = "SELECT * FROM public."

    context = SQLContextAnalyzer().analyze(sql, len(sql))

    assert context.clause == "FROM"
    assert context.schema_qualifier == "public"
    assert context.expects_relation is True
    assert context.current_token == ""


def test_analyzer_detects_insert_and_update_target_contexts():
    insert_sql = "INSERT INTO users (ema"
    update_sql = "UPDATE users SET ema"

    insert = SQLContextAnalyzer().analyze(insert_sql, len(insert_sql))
    update = SQLContextAnalyzer().analyze(update_sql, len(update_sql))

    assert insert.clause == "INSERT_COLUMNS"
    assert insert.tables == ("users",)
    assert insert.current_token == "ema"
    assert update.clause == "SET"
    assert update.tables == ("users",)
    assert update.current_token == "ema"


def test_analyzer_ignores_semicolons_and_aliases_inside_strings_and_comments():
    sql = "SELECT 'ignore; FROM ghosts g' FROM users u -- JOIN hidden h\nWHERE u."

    context = SQLContextAnalyzer().analyze(sql, len(sql))

    assert context.aliases == {"u": "users"}
    assert context.tables == ("users",)
    assert context.qualifier == "u"
    assert context.clause == "WHERE"
