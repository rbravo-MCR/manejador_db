"""SQLite metadata inspection mapped to the Universal Schema Model."""

from __future__ import annotations

from typing import Any

from backend_ide.domain.schema import (
    Column,
    DatabaseSchema,
    ForeignKey,
    ForeignKeyColumnMapping,
    NormalizedDataType,
    PrimaryKey,
    Schema,
    Table,
    View,
)
from backend_ide.infrastructure.database.contracts import DatabaseConnection


class SQLiteMetadataProvider:
    """Read SQLite catalog and PRAGMA metadata through a database connection adapter."""

    def __init__(self, connection: DatabaseConnection) -> None:
        self.connection = connection

    def inspect_database(self) -> DatabaseSchema:
        rows = self.connection.execute_query(
            """
            SELECT name, type, sql
            FROM sqlite_master
            WHERE type IN ('table', 'view')
              AND name NOT LIKE 'sqlite_%'
            ORDER BY type, name
            """
        )
        tables: list[Table] = []
        views: list[View] = []
        for row in rows:
            if row["type"] == "table":
                columns = self.get_columns(row["name"], "main")
                pk_names = [column.name for column in columns if column.is_primary_key]
                tables.append(
                    Table(
                        name=row["name"],
                        schema_name="main",
                        columns=columns,
                        primary_key=PrimaryKey(column_names=pk_names) if pk_names else None,
                        foreign_keys=self.get_foreign_keys(row["name"], "main"),
                    )
                )
            else:
                views.append(
                    View(
                        name=row["name"],
                        schema_name="main",
                        definition=row.get("sql"),
                    )
                )
        return DatabaseSchema(
            engine_name="sqlite",
            database_name=self._database_name(),
            schemas=[Schema(name="main", tables=tables, views=views)],
        )

    def get_schemas(self) -> list[str]:
        return [row["name"] for row in self.connection.execute_query("PRAGMA database_list")]

    def get_tables(self, schema: str | None = None) -> list[Table]:
        target = schema or "main"
        rows = self.connection.execute_query(
            f'SELECT name FROM "{target}".sqlite_master '
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        return [
            Table(
                name=row["name"], schema_name=target, columns=self.get_columns(row["name"], target)
            )
            for row in rows
        ]

    def get_views(self, schema: str | None = None) -> list[View]:
        target = schema or "main"
        rows = self.connection.execute_query(
            f"SELECT name, sql FROM \"{target}\".sqlite_master WHERE type = 'view' ORDER BY name"
        )
        return [
            View(name=row["name"], schema_name=target, definition=row.get("sql")) for row in rows
        ]

    def get_columns(self, table: str, schema: str | None = None) -> list[Column]:
        target = schema or "main"
        rows = self.connection.execute_query(
            f'PRAGMA "{target}".table_info("{self._quote_pragma_identifier(table)}")'
        )
        table_sql = self._table_sql(table, target).upper()
        auto_increment = "AUTOINCREMENT" in table_sql
        return [
            Column(
                name=row["name"],
                native_type=row.get("type") or "BLOB",
                normalized_type=self._normalize_type(row.get("type") or "BLOB"),
                is_nullable=not bool(row.get("notnull")),
                is_primary_key=bool(row.get("pk")),
                is_auto_increment=bool(row.get("pk")) and auto_increment,
                default_value=row.get("dflt_value"),
            )
            for row in rows
        ]

    def get_foreign_keys(self, table: str, schema: str | None = None) -> list[ForeignKey]:
        target = schema or "main"
        rows = self.connection.execute_query(
            f'PRAGMA "{target}".foreign_key_list("{self._quote_pragma_identifier(table)}")'
        )
        return [
            ForeignKey(
                name=f"fk_{table}_{row['id']}_{row['seq']}",
                source_schema=target,
                source_table=table,
                target_schema=target,
                target_table=row["table"],
                column_mappings=[
                    ForeignKeyColumnMapping(
                        source_column=row["from"],
                        target_column=row["to"],
                    )
                ],
            )
            for row in rows
        ]

    def get_functions(self) -> list[Any]:
        return []

    def _table_sql(self, table: str, schema: str) -> str:
        rows = self.connection.execute_query(
            f"SELECT sql FROM \"{schema}\".sqlite_master WHERE type = 'table' AND name = ?",
            (table,),
        )
        return str(rows[0].get("sql") or "") if rows else ""

    def _database_name(self) -> str:
        direct = getattr(self.connection, "database_name", None)
        if direct:
            return str(direct)
        config = getattr(self.connection, "config", None)
        return str(getattr(config, "database", "main"))

    @staticmethod
    def _quote_pragma_identifier(identifier: str) -> str:
        return identifier.replace('"', '""')

    @staticmethod
    def _normalize_type(native_type: str) -> NormalizedDataType:
        value = native_type.upper()
        if "INT" in value:
            return NormalizedDataType.INTEGER
        if any(token in value for token in ("CHAR", "CLOB", "TEXT")):
            return NormalizedDataType.TEXT
        if "BLOB" in value or not value:
            return NormalizedDataType.BINARY
        if any(token in value for token in ("REAL", "FLOA", "DOUB")):
            return NormalizedDataType.FLOAT
        if any(token in value for token in ("NUM", "DEC")):
            return NormalizedDataType.DECIMAL
        return NormalizedDataType.UNKNOWN
