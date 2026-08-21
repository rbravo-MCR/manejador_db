"""SQLite Schema Inspector.

Inspects SQLite sqlite_master and PRAGMA metadata and converts the database structure
into the Universal Schema Model (DatabaseSchema).
"""

from __future__ import annotations

from pathlib import Path

from backend_ide.domain.schema.enums import (
    ForeignKeyAction,
    IndexType,
)
from backend_ide.domain.schema.models import (
    Column,
    DatabaseSchema,
    ForeignKey,
    ForeignKeyColumnMapping,
    Index,
    PrimaryKey,
    Schema,
    Table,
    UniqueConstraint,
    View,
)
from backend_ide.infrastructure.database.contracts import DatabaseConnection
from backend_ide.infrastructure.database.sqlite.type_mapper import (
    map_sqlite_type_to_normalized,
)
from backend_ide.infrastructure.logging import get_logger

logger = get_logger(__name__)


class SQLiteInspector:
    """Inspector for SQLite databases."""

    def __init__(self, connection: DatabaseConnection) -> None:
        self.connection = connection

    def _get_current_database_name(self) -> str:
        """Resolve database name or base filename."""
        try:
            rows = self.connection.execute_query("PRAGMA database_list;")
            for r in rows:
                if r.get("name") == "main" and r.get("file"):
                    return Path(r["file"]).stem or "main"
        except Exception:
            pass
        return "main"

    def list_databases(self) -> list[str]:
        """List attached SQLite database schema names (main, temp, attached)."""
        try:
            rows = self.connection.execute_query("PRAGMA database_list;")
            return [r["name"] for r in rows if r.get("name")]
        except Exception:
            return ["main"]

    def inspect_database_summary(self) -> DatabaseSchema:
        """Build the complete schema, table, column, and foreign key model for SQLite."""
        db_name = self._get_current_database_name()
        tables = self._inspect_tables()
        views = self._inspect_views()

        return DatabaseSchema(
            engine_name="sqlite",
            database_name=db_name,
            schemas=[
                Schema(
                    name="main",
                    tables=tables,
                    views=views,
                )
            ],
        )

    def inspect_table_columns(self, schema_name: str, table_name: str) -> list[Column]:
        """Inspect fields for a single table."""
        columns, _pk = self._inspect_table_columns_and_pk(table_name)
        return columns

    def inspect_database(
        self, schema_names: list[str] | None = None, include_views: bool = True
    ) -> DatabaseSchema:
        """Inspect SQLite database and construct DatabaseSchema instance."""
        return self.inspect_database_summary()

    def _inspect_tables(self) -> list[Table]:
        """Inspect all user tables in SQLite database."""
        rows = self.connection.execute_query(
            """
            SELECT name, sql
            FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name;
            """
        )
        tables: list[Table] = []
        for r in rows:
            table_name = r["name"]
            table_sql = r.get("sql") or ""
            columns, primary_key = self._inspect_table_columns_and_pk(table_name, table_sql)
            foreign_keys = self._inspect_foreign_keys(table_name)
            indexes, unique_constraints = self._inspect_indexes_and_uniques(table_name)

            tables.append(
                Table(
                    name=table_name,
                    schema_name="main",
                    columns=columns,
                    primary_key=primary_key,
                    foreign_keys=foreign_keys,
                    indexes=indexes,
                    unique_constraints=unique_constraints,
                )
            )
        return tables

    def _inspect_views(self) -> list[View]:
        """Inspect all views in SQLite database."""
        rows = self.connection.execute_query(
            """
            SELECT name, sql
            FROM sqlite_master
            WHERE type='view' AND name NOT LIKE 'sqlite_%'
            ORDER BY name;
            """
        )
        views: list[View] = []
        for r in rows:
            view_name = r["name"]
            view_sql = r.get("sql") or ""
            views.append(
                View(
                    name=view_name,
                    schema_name="main",
                    definition=view_sql,
                )
            )
        return views

    def _inspect_table_columns_and_pk(
        self, table_name: str, table_sql: str = ""
    ) -> tuple[list[Column], PrimaryKey | None]:
        """Inspect columns and primary key for a table via PRAGMA table_info."""
        rows = self.connection.execute_query(f'PRAGMA table_info("{table_name}");')
        columns: list[Column] = []
        pk_columns_with_pos: list[tuple[int, str]] = []

        is_autoincrement_table = "AUTOINCREMENT" in table_sql.upper()

        for r in rows:
            col_name = r["name"]
            raw_type = r.get("type", "")
            notnull = bool(r.get("notnull", 0))
            dflt_val = r.get("dflt_value")
            pk_val = int(r.get("pk", 0))

            is_pk = pk_val > 0
            if is_pk:
                pk_columns_with_pos.append((pk_val, col_name))

            is_auto = False
            if (
                is_pk
                and raw_type.upper() in ("INTEGER", "INT")
                and (is_autoincrement_table or len(rows) == 1)
            ):
                is_auto = True

            norm_type = map_sqlite_type_to_normalized(raw_type)

            columns.append(
                Column(
                    name=col_name,
                    native_type=raw_type.upper() if raw_type else "TEXT",
                    normalized_type=norm_type,
                    is_primary_key=is_pk,
                    is_nullable=not notnull and not is_pk,
                    is_auto_increment=is_auto,
                    default_value=str(dflt_val) if dflt_val is not None else None,
                )
            )

        primary_key: PrimaryKey | None = None
        if pk_columns_with_pos:
            pk_columns_with_pos.sort(key=lambda x: x[0])
            pk_cols = [c[1] for c in pk_columns_with_pos]
            primary_key = PrimaryKey(
                name=f"pk_{table_name}",
                column_names=pk_cols,
            )

        return columns, primary_key

    def _inspect_foreign_keys(self, table_name: str) -> list[ForeignKey]:
        """Inspect foreign keys via PRAGMA foreign_key_list."""
        rows = self.connection.execute_query(f'PRAGMA foreign_key_list("{table_name}");')
        # Group by fk id
        fks_by_id: dict[int, dict] = {}
        for r in rows:
            fk_id = r["id"]
            if fk_id not in fks_by_id:
                fks_by_id[fk_id] = {
                    "target_table": r["table"],
                    "mappings": [],
                    "on_update": self._map_fk_action(r.get("on_update")),
                    "on_delete": self._map_fk_action(r.get("on_delete")),
                }
            fks_by_id[fk_id]["mappings"].append(
                ForeignKeyColumnMapping(
                    source_column=r["from"],
                    target_column=r["to"],
                )
            )

        foreign_keys: list[ForeignKey] = []
        for fk_id, data in fks_by_id.items():
            foreign_keys.append(
                ForeignKey(
                    name=f"fk_{table_name}_{data['target_table']}_{fk_id}",
                    source_schema="main",
                    source_table=table_name,
                    target_schema="main",
                    target_table=data["target_table"],
                    column_mappings=data["mappings"],
                    on_update=data["on_update"],
                    on_delete=data["on_delete"],
                )
            )
        return foreign_keys

    def _inspect_indexes_and_uniques(
        self, table_name: str
    ) -> tuple[list[Index], list[UniqueConstraint]]:
        """Inspect indexes and unique constraints via PRAGMA index_list."""
        rows = self.connection.execute_query(f'PRAGMA index_list("{table_name}");')
        indexes: list[Index] = []
        unique_constraints: list[UniqueConstraint] = []

        for r in rows:
            idx_name = r["name"]
            is_unique = bool(r.get("unique", 0))
            origin = r.get("origin", "")

            # Get index columns
            col_rows = self.connection.execute_query(f'PRAGMA index_info("{idx_name}");')
            col_names = [cr["name"] for cr in sorted(col_rows, key=lambda x: x.get("seqno", 0))]

            if is_unique and origin == "u":
                unique_constraints.append(
                    UniqueConstraint(
                        name=idx_name,
                        column_names=col_names,
                    )
                )
            elif origin != "pk":
                indexes.append(
                    Index(
                        name=idx_name,
                        table_name=table_name,
                        column_names=col_names,
                        is_unique=is_unique,
                        index_type=IndexType.BTREE,
                    )
                )

        return indexes, unique_constraints

    def _map_fk_action(self, action_str: str | None) -> ForeignKeyAction:
        """Map SQLite FK action string to ForeignKeyAction enum."""
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
