"""MySQL Schema Inspector.

Inspects MySQL / MariaDB information_schema and converts the structure
into the Universal Schema Model (DatabaseSchema).
"""

from __future__ import annotations

from backend_ide.domain.schema.enums import (
    ForeignKeyAction,
)
from backend_ide.domain.schema.models import (
    Column,
    DatabaseSchema,
    ForeignKey,
    ForeignKeyColumnMapping,
    PrimaryKey,
    Schema,
    Table,
    View,
)
from backend_ide.infrastructure.database.contracts import DatabaseConnection
from backend_ide.infrastructure.database.mysql.type_mapper import (
    map_mysql_type_to_normalized,
)
from backend_ide.infrastructure.logging import get_logger

logger = get_logger(__name__)


class MySQLInspector:
    """Inspector for MySQL and MariaDB databases."""

    def __init__(self, connection: DatabaseConnection) -> None:
        self.connection = connection

    def list_databases(self) -> list[str]:
        """List user databases in MySQL."""
        query = """
        SELECT schema_name
        FROM information_schema.schemata
        WHERE schema_name NOT IN ('information_schema', 'mysql', 'performance_schema', 'sys')
        ORDER BY schema_name;
        """
        rows = self.connection.execute_query(query)
        return [r["schema_name"] for r in rows if r.get("schema_name")]

    def inspect_database_summary(self) -> DatabaseSchema:
        """Build complete schema, table, column, and foreign key model for MySQL."""
        db_name = self.connection.config.database

        # 1. Fetch tables
        table_rows = self.connection.execute_query(
            """
            SELECT table_schema, table_name, table_type
            FROM information_schema.tables
            WHERE table_schema = %s
            ORDER BY table_name;
            """,
            (db_name,),
        )

        base_tables = [r["table_name"] for r in table_rows if r.get("table_type") == "BASE TABLE"]
        view_names = [r["table_name"] for r in table_rows if r.get("table_type") == "VIEW"]

        # 2. Bulk fetch columns
        col_rows = self.connection.execute_query(
            """
            SELECT
                table_name,
                column_name,
                data_type,
                column_type,
                is_nullable,
                column_default,
                character_maximum_length,
                numeric_precision,
                numeric_scale,
                extra,
                column_key
            FROM information_schema.columns
            WHERE table_schema = %s
            ORDER BY table_name, ordinal_position;
            """,
            (db_name,),
        )

        cols_by_table: dict[str, list[Column]] = {}
        pks_by_table: dict[str, list[str]] = {}

        for r in col_rows:
            tbl = r["table_name"]
            raw_type = r.get("column_type") or r.get("data_type") or "VARCHAR"
            is_auto = "auto_increment" in str(r.get("extra", "")).lower()
            is_pk = r.get("column_key") == "PRI"

            if is_pk:
                pks_by_table.setdefault(tbl, []).append(r["column_name"])

            norm_type = map_mysql_type_to_normalized(raw_type)

            cols_by_table.setdefault(tbl, []).append(
                Column(
                    name=r["column_name"],
                    native_type=str(raw_type).upper(),
                    normalized_type=norm_type,
                    is_primary_key=is_pk,
                    is_nullable=r["is_nullable"] == "YES",
                    is_auto_increment=is_auto,
                    default_value=str(r["column_default"])
                    if r.get("column_default") is not None
                    else None,
                    precision=r.get("numeric_precision"),
                    scale=r.get("numeric_scale"),
                    length=r.get("character_maximum_length"),
                )
            )

        # 3. Bulk fetch foreign keys
        fk_rows = self.connection.execute_query(
            """
            SELECT
                kcu.constraint_name,
                kcu.table_name AS source_table,
                kcu.column_name AS source_column,
                kcu.referenced_table_schema AS target_schema,
                kcu.referenced_table_name AS target_table,
                kcu.referenced_column_name AS target_column,
                rc.update_rule,
                rc.delete_rule
            FROM information_schema.key_column_usage AS kcu
            JOIN information_schema.referential_constraints AS rc
              ON kcu.constraint_name = rc.constraint_name
             AND kcu.table_schema = rc.constraint_schema
            WHERE kcu.table_schema = %s
              AND kcu.referenced_table_name IS NOT NULL
            ORDER BY kcu.table_name, kcu.ordinal_position;
            """,
            (db_name,),
        )

        fks_by_table: dict[str, dict[str, dict]] = {}
        for r in fk_rows:
            src_tbl = r["source_table"]
            c_name = r["constraint_name"]
            if src_tbl not in fks_by_table:
                fks_by_table[src_tbl] = {}

            if c_name not in fks_by_table[src_tbl]:
                fks_by_table[src_tbl][c_name] = {
                    "target_schema": r.get("target_schema") or db_name,
                    "target_table": r["target_table"],
                    "mappings": [],
                    "on_update": self._map_fk_action(r.get("update_rule")),
                    "on_delete": self._map_fk_action(r.get("delete_rule")),
                }

            fks_by_table[src_tbl][c_name]["mappings"].append(
                ForeignKeyColumnMapping(
                    source_column=r["source_column"],
                    target_column=r["target_column"],
                )
            )

        tables: list[Table] = []
        for tbl_name in base_tables:
            pk_cols = pks_by_table.get(tbl_name, [])
            pk = PrimaryKey(name=f"pk_{tbl_name}", column_names=pk_cols) if pk_cols else None

            table_fks: list[ForeignKey] = []
            if tbl_name in fks_by_table:
                for c_name, fk_data in fks_by_table[tbl_name].items():
                    table_fks.append(
                        ForeignKey(
                            name=c_name,
                            source_schema=db_name,
                            source_table=tbl_name,
                            target_schema=fk_data["target_schema"],
                            target_table=fk_data["target_table"],
                            column_mappings=fk_data["mappings"],
                            on_update=fk_data["on_update"],
                            on_delete=fk_data["on_delete"],
                        )
                    )

            tables.append(
                Table(
                    name=tbl_name,
                    schema_name=db_name,
                    columns=cols_by_table.get(tbl_name, []),
                    primary_key=pk,
                    foreign_keys=table_fks,
                )
            )

        views: list[View] = [View(name=v_name, schema_name=db_name) for v_name in view_names]

        return DatabaseSchema(
            engine_name="mysql",
            database_name=db_name,
            schemas=[
                Schema(
                    name=db_name,
                    tables=tables,
                    views=views,
                )
            ],
        )

    def inspect_table_columns(self, schema_name: str, table_name: str) -> list[Column]:
        """Inspect fields for a single table."""
        col_rows = self.connection.execute_query(
            """
            SELECT
                column_name,
                data_type,
                column_type,
                is_nullable,
                column_default,
                character_maximum_length,
                numeric_precision,
                numeric_scale,
                extra,
                column_key
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position;
            """,
            (schema_name, table_name),
        )
        columns: list[Column] = []
        for r in col_rows:
            raw_type = r.get("column_type") or r.get("data_type") or "VARCHAR"
            is_auto = "auto_increment" in str(r.get("extra", "")).lower()
            is_pk = r.get("column_key") == "PRI"
            norm_type = map_mysql_type_to_normalized(raw_type)

            columns.append(
                Column(
                    name=r["column_name"],
                    native_type=str(raw_type).upper(),
                    normalized_type=norm_type,
                    is_primary_key=is_pk,
                    is_nullable=r["is_nullable"] == "YES",
                    is_auto_increment=is_auto,
                    default_value=str(r["column_default"])
                    if r.get("column_default") is not None
                    else None,
                    precision=r.get("numeric_precision"),
                    scale=r.get("numeric_scale"),
                    length=r.get("character_maximum_length"),
                )
            )
        return columns

    def inspect_database(
        self, schema_names: list[str] | None = None, include_views: bool = True
    ) -> DatabaseSchema:
        """Inspect MySQL database and construct DatabaseSchema instance."""
        return self.inspect_database_summary()

    def _map_fk_action(self, action_str: str | None) -> ForeignKeyAction:
        """Map MySQL FK action string to ForeignKeyAction enum."""
        if not action_str:
            return ForeignKeyAction.NO_ACTION
        action_clean = action_str.upper().replace(" ", "_")
        action_map = {
            "CASCADE": ForeignKeyAction.CASCADE,
            "SET_NULL": ForeignKeyAction.SET_NULL,
            "SET_DEFAULT": ForeignKeyAction.SET_DEFAULT,
            "RESTRICT": ForeignKeyAction.RESTRICT,
            "NO_ACTION": ForeignKeyAction.NO_ACTION,
        }
        return action_map.get(action_clean, ForeignKeyAction.NO_ACTION)
