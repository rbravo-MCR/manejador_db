"""Unit tests for SchemaDiffEngine and SchemaDiffDialog."""

from __future__ import annotations

from backend_ide.domain.diff.engine import SchemaDiffEngine
from backend_ide.domain.schema.enums import NormalizedDataType
from backend_ide.domain.schema.models import (
    Column,
    DatabaseSchema,
    PrimaryKey,
    Schema,
    Table,
)


def test_schema_diff_engine_detects_changes():
    """Verify SchemaDiffEngine accurately identifies added, dropped, and modified tables/columns."""
    # Source Schema (Old DB)
    src_users = Table(
        name="users",
        columns=[
            Column(
                name="id",
                native_type="INT",
                normalized_type=NormalizedDataType.INTEGER,
                is_primary_key=True,
            ),
            Column(
                name="email",
                native_type="VARCHAR(100)",
                normalized_type=NormalizedDataType.VARCHAR,
            ),
            Column(
                name="old_col",
                native_type="TEXT",
                normalized_type=NormalizedDataType.TEXT,
            ),
        ],
        primary_key=PrimaryKey(column_names=["id"]),
    )
    src_legacy = Table(
        name="legacy_logs",
        columns=[
            Column(
                name="id",
                native_type="INT",
                normalized_type=NormalizedDataType.INTEGER,
            )
        ],
    )
    src_schema = DatabaseSchema(
        database_name="prod_db",
        engine_name="postgresql",
        schemas=[Schema(name="public", tables=[src_users, src_legacy])],
    )

    # Target Schema (New Desired DB)
    tgt_users = Table(
        name="users",
        columns=[
            Column(
                name="id",
                native_type="BIGINT",
                normalized_type=NormalizedDataType.BIGINT,
                is_primary_key=True,
            ),
            Column(
                name="email",
                native_type="VARCHAR(255)",
                normalized_type=NormalizedDataType.VARCHAR,
            ),
            Column(
                name="new_col",
                native_type="BOOLEAN",
                normalized_type=NormalizedDataType.BOOLEAN,
            ),
        ],
        primary_key=PrimaryKey(column_names=["id"]),
    )
    tgt_orders = Table(
        name="orders",
        columns=[
            Column(
                name="id",
                native_type="BIGINT",
                normalized_type=NormalizedDataType.BIGINT,
                is_primary_key=True,
            ),
            Column(
                name="total",
                native_type="DECIMAL(10,2)",
                normalized_type=NormalizedDataType.DECIMAL,
            ),
        ],
        primary_key=PrimaryKey(column_names=["id"]),
    )
    tgt_schema = DatabaseSchema(
        database_name="dev_db",
        engine_name="postgresql",
        schemas=[Schema(name="public", tables=[tgt_users, tgt_orders])],
    )

    diff = SchemaDiffEngine.compare(src_schema, tgt_schema)
    assert diff.has_differences is True
    assert len(diff.added_tables) == 1
    assert diff.added_tables[0].name == "orders"
    assert len(diff.dropped_tables) == 1
    assert diff.dropped_tables[0].name == "legacy_logs"
    assert len(diff.modified_tables) == 1
    assert diff.modified_tables[0].table_name == "users"

    users_diff = diff.modified_tables[0]
    assert len(users_diff.added_columns) == 1
    assert users_diff.added_columns[0].name == "new_col"
    assert len(users_diff.dropped_columns) == 1
    assert users_diff.dropped_columns[0].name == "old_col"
    assert len(users_diff.modified_columns) >= 1

    # DDL generation
    ddl = SchemaDiffEngine.generate_migration_ddl(diff, dialect="postgresql", safe_mode=True)
    assert "CREATE TABLE orders" in ddl
    assert "ALTER TABLE users ADD COLUMN new_col" in ddl
    assert "-- [SAFE MODE - UNCOMMENT TO DROP]: ALTER TABLE users DROP COLUMN old_col;" in ddl
