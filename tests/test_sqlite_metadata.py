"""SQLite metadata provider integration against an in-memory database."""

import sqlite3

from backend_ide.infrastructure.database.sqlite import SQLiteMetadataProvider


class SQLiteTestConnection:
    def __init__(self) -> None:
        self.database_name = ":memory:"
        self.raw = sqlite3.connect(":memory:")
        self.raw.row_factory = sqlite3.Row

    def execute_query(self, query, params=None):
        cursor = self.raw.execute(query, params or ())
        return [dict(row) for row in cursor.fetchall()]


def test_sqlite_provider_loads_tables_views_columns_and_primary_keys():
    connection = SQLiteTestConnection()
    connection.raw.executescript(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            display_name TEXT DEFAULT 'anonymous'
        );
        CREATE VIEW active_users AS SELECT id, email FROM users;
        """
    )

    metadata = SQLiteMetadataProvider(connection).inspect_database()

    assert metadata.engine_name == "sqlite"
    assert metadata.database_name == ":memory:"
    assert [schema.name for schema in metadata.schemas] == ["main"]
    assert [table.name for table in metadata.schemas[0].tables] == ["users"]
    assert [view.name for view in metadata.schemas[0].views] == ["active_users"]
    users = metadata.find_table("users", "main")
    assert [column.name for column in users.columns] == ["id", "email", "display_name"]
    assert users.columns[0].is_primary_key is True
    assert users.columns[0].is_auto_increment is True
    assert users.columns[1].is_nullable is False
    assert users.columns[2].default_value == "'anonymous'"


def test_sqlite_provider_can_refresh_columns_for_one_table():
    connection = SQLiteTestConnection()
    connection.raw.execute("CREATE TABLE events (id INTEGER, occurred_at TEXT)")

    columns = SQLiteMetadataProvider(connection).get_columns("events", "main")

    assert [column.name for column in columns] == ["id", "occurred_at"]
