"""Unit and Integration tests for SQLite Adapter and Inspector."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from backend_ide.domain.schema.enums import ForeignKeyAction, NormalizedDataType
from backend_ide.infrastructure.database.contracts import ConnectionConfig
from backend_ide.infrastructure.database.sqlite.connection import SQLiteConnection
from backend_ide.infrastructure.database.sqlite.inspector import SQLiteInspector
from backend_ide.infrastructure.database.sqlite.type_mapper import (
    map_sqlite_type_to_normalized,
)


def test_sqlite_type_mapper():
    """Verify SQLite type affinity and explicit types mapping to NormalizedDataType."""
    assert map_sqlite_type_to_normalized("INTEGER") == NormalizedDataType.INTEGER
    assert map_sqlite_type_to_normalized("INT") == NormalizedDataType.INTEGER
    assert map_sqlite_type_to_normalized("BIGINT") == NormalizedDataType.BIGINT
    assert map_sqlite_type_to_normalized("VARCHAR(255)") == NormalizedDataType.VARCHAR
    assert map_sqlite_type_to_normalized("TEXT") == NormalizedDataType.TEXT
    assert map_sqlite_type_to_normalized("REAL") == NormalizedDataType.FLOAT
    assert map_sqlite_type_to_normalized("FLOAT") == NormalizedDataType.FLOAT
    assert map_sqlite_type_to_normalized("DECIMAL(10,2)") == NormalizedDataType.DECIMAL
    assert map_sqlite_type_to_normalized("DATETIME") == NormalizedDataType.DATETIME
    assert map_sqlite_type_to_normalized("BOOLEAN") == NormalizedDataType.BOOLEAN
    assert map_sqlite_type_to_normalized("BLOB") == NormalizedDataType.BINARY
    assert map_sqlite_type_to_normalized("JSON") == NormalizedDataType.JSON


def test_sqlite_connection_memory_and_query_execution():
    """Verify SQLiteConnection can open in-memory database and execute queries."""
    config = ConnectionConfig(
        name="Test SQLite",
        engine="sqlite",
        database=":memory:",
    )
    conn = SQLiteConnection(config)
    assert conn.test_connection() is True

    conn.connect()
    assert conn.is_connected() is True

    conn.execute_query("CREATE TABLE test_items (id INT, label TEXT);")
    conn.execute_query("INSERT INTO test_items VALUES (1, 'Alpha'), (2, 'Beta');")

    rows = conn.execute_query("SELECT * FROM test_items ORDER BY id;")
    assert len(rows) == 2
    assert rows[0] == {"id": 1, "label": "Alpha"}
    assert rows[1] == {"id": 2, "label": "Beta"}

    conn.disconnect()
    assert conn.is_connected() is False


def test_sqlite_inspector_full_database_introspections(tmp_path: Path):
    """Verify SQLiteInspector parses tables, columns, PKs, FKs, unique constraints, and views."""
    db_file = tmp_path / "app_travel.sqlite"
    native_conn = sqlite3.connect(str(db_file))
    native_conn.execute(
        """
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name VARCHAR(100) NOT NULL,
            email TEXT UNIQUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    native_conn.execute(
        """
        CREATE TABLE reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            code VARCHAR(20) NOT NULL,
            total_amount REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
        );
        """
    )
    native_conn.execute(
        """
        CREATE VIEW active_reservations AS
        SELECT r.id, r.code, c.full_name, r.total_amount
        FROM reservations r
        JOIN customers c ON c.id = r.customer_id;
        """
    )
    native_conn.close()

    config = ConnectionConfig(
        name="Travel SQLite",
        engine="sqlite",
        database=str(db_file),
    )
    conn = SQLiteConnection(config)
    conn.connect()

    inspector = SQLiteInspector(conn)
    schema_model = inspector.inspect_database_summary()

    assert schema_model.engine_name == "sqlite"
    assert len(schema_model.schemas) == 1

    main_schema = schema_model.schemas[0]
    assert main_schema.name == "main"

    # Verify tables
    table_names = [t.name for t in main_schema.tables]
    assert "customers" in table_names
    assert "reservations" in table_names

    # Verify customers table columns & PK
    customers = main_schema.get_table("customers")
    assert customers is not None
    assert customers.primary_key is not None
    assert customers.primary_key.column_names == ["id"]

    cust_cols = {c.name: c for c in customers.columns}
    assert cust_cols["id"].is_primary_key is True
    assert cust_cols["full_name"].is_nullable is False
    assert cust_cols["full_name"].normalized_type == NormalizedDataType.VARCHAR
    assert cust_cols["email"].normalized_type == NormalizedDataType.TEXT

    # Verify unique constraint on email
    assert len(customers.unique_constraints) >= 1

    # Verify reservations FK
    reservations = main_schema.get_table("reservations")
    assert reservations is not None
    assert len(reservations.foreign_keys) == 1
    fk = reservations.foreign_keys[0]
    assert fk.target_table == "customers"
    assert fk.column_mappings[0].source_column == "customer_id"
    assert fk.column_mappings[0].target_column == "id"
    assert fk.on_delete == ForeignKeyAction.CASCADE

    # Verify view
    assert len(main_schema.views) == 1
    view = main_schema.views[0]
    assert view.name == "active_reservations"
    assert "SELECT" in (view.definition or "")

    conn.disconnect()
