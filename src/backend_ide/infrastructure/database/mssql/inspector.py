"""Microsoft SQL Server (T-SQL) Database Inspector."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from backend_ide.domain.schema.enums import ForeignKeyAction
from backend_ide.domain.schema.models import (
    Column,
    DatabaseSchema,
    ForeignKey,
    ForeignKeyColumnMapping,
    PrimaryKey,
    Schema,
    Table,
)
from backend_ide.infrastructure.database.mssql.type_mapper import MSSQLTypeMapper

if TYPE_CHECKING:
    from backend_ide.infrastructure.database.mssql.connection import MSSQLConnection


class MSSQLInspector:
    """Introspects SQL Server metadata using sys views and INFORMATION_SCHEMA."""

    def __init__(self, connection: MSSQLConnection) -> None:
        self.connection = connection

    def list_databases(self) -> list[str]:
        """List online, user-accessible databases in SQL Server instance."""
        sql = """
            SELECT name
            FROM sys.databases
            WHERE state_desc = 'ONLINE'
              AND name NOT IN ('master', 'tempdb', 'model', 'msdb')
            ORDER BY name;
        """
        rows = self.connection.execute_query(sql)
        return [row["name"] for row in rows if "name" in row]

    def inspect_database_summary(self) -> DatabaseSchema:
        """Inspect all user schemas, tables, primary keys, and foreign keys."""
        db_name = self.connection.config.database or "database"

        # 1. Fetch tables
        tables_sql = """
            SELECT
                s.name AS schema_name,
                t.name AS table_name,
                t.type_desc AS table_type
            FROM sys.tables t
            INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE t.is_ms_shipped = 0
            ORDER BY s.name, t.name;
        """
        table_rows = self.connection.execute_query(tables_sql)

        # 2. Fetch PKs
        pks_sql = """
            SELECT
                s.name AS schema_name,
                t.name AS table_name,
                kc.name AS constraint_name,
                c.name AS column_name,
                ic.key_ordinal AS ordinal_position
            FROM sys.key_constraints kc
            INNER JOIN sys.tables t ON kc.parent_object_id = t.object_id
            INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
            INNER JOIN sys.index_columns ic
                ON kc.parent_object_id = ic.object_id AND kc.unique_index_id = ic.index_id
            INNER JOIN sys.columns c
                ON ic.object_id = c.object_id AND ic.column_id = c.column_id
            WHERE kc.type = 'PK'
            ORDER BY s.name, t.name, ic.key_ordinal;
        """
        pk_rows = self.connection.execute_query(pks_sql)

        # 3. Fetch FKs
        fks_sql = """
            SELECT
                s_src.name AS source_schema,
                t_src.name AS source_table,
                fk.name AS constraint_name,
                c_src.name AS source_column,
                s_tgt.name AS target_schema,
                t_tgt.name AS target_table,
                c_tgt.name AS target_column,
                fk.update_referential_action_desc AS on_update,
                fk.delete_referential_action_desc AS on_delete
            FROM sys.foreign_keys fk
            INNER JOIN sys.tables t_src ON fk.parent_object_id = t_src.object_id
            INNER JOIN sys.schemas s_src ON t_src.schema_id = s_src.schema_id
            INNER JOIN sys.tables t_tgt ON fk.referenced_object_id = t_tgt.object_id
            INNER JOIN sys.schemas s_tgt ON t_tgt.schema_id = s_tgt.schema_id
            INNER JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
            INNER JOIN sys.columns c_src
                ON fkc.parent_object_id = c_src.object_id AND fkc.parent_column_id = c_src.column_id
            INNER JOIN sys.columns c_tgt
                ON fkc.referenced_object_id = c_tgt.object_id
                AND fkc.referenced_column_id = c_tgt.column_id
            ORDER BY fk.name, fkc.constraint_column_id;
        """
        fk_rows = self.connection.execute_query(fks_sql)

        # 4. Process PKs
        pks_by_table: dict[tuple[str, str], list[str]] = {}
        pk_name_by_table: dict[tuple[str, str], str] = {}
        for r in pk_rows:
            key = (r["schema_name"], r["table_name"])
            pks_by_table.setdefault(key, []).append(r["column_name"])
            pk_name_by_table[key] = r["constraint_name"]

        # 5. Process FKs
        fks_by_table: dict[tuple[str, str], dict[str, Any]] = {}
        for r in fk_rows:
            src_key = (r["source_schema"], r["source_table"])
            fk_name = r["constraint_name"]

            if src_key not in fks_by_table:
                fks_by_table[src_key] = {}

            if fk_name not in fks_by_table[src_key]:
                fks_by_table[src_key][fk_name] = {
                    "target_schema": r["target_schema"],
                    "target_table": r["target_table"],
                    "mappings": [],
                    "on_update": self._map_action(r.get("on_update", "")),
                    "on_delete": self._map_action(r.get("on_delete", "")),
                }

            fks_by_table[src_key][fk_name]["mappings"].append(
                ForeignKeyColumnMapping(
                    source_column=r["source_column"],
                    target_column=r["target_column"],
                )
            )

        # 6. Group tables into Schemas
        schema_tables: dict[str, list[Table]] = {}
        for r in table_rows:
            s_name = r["schema_name"]
            t_name = r["table_name"]
            key = (s_name, t_name)

            pk_cols = pks_by_table.get(key, [])
            pk = (
                PrimaryKey(
                    name=pk_name_by_table.get(key, f"PK_{t_name}"),
                    column_names=pk_cols,
                )
                if pk_cols
                else None
            )

            table_fks: list[ForeignKey] = []
            if key in fks_by_table:
                for fk_name, fk_data in fks_by_table[key].items():
                    table_fks.append(
                        ForeignKey(
                            name=fk_name,
                            source_table=t_name,
                            target_table=fk_data["target_table"],
                            target_schema=fk_data["target_schema"],
                            column_mappings=fk_data["mappings"],
                            on_update=fk_data["on_update"],
                            on_delete=fk_data["on_delete"],
                        )
                    )

            table_obj = Table(
                name=t_name,
                schema_name=s_name,
                primary_key=pk,
                foreign_keys=table_fks,
            )
            schema_tables.setdefault(s_name, []).append(table_obj)

        schemas = [Schema(name=name, tables=tables) for name, tables in schema_tables.items()]
        if not schemas:
            schemas = [Schema(name="dbo", tables=[])]

        return DatabaseSchema(
            database_name=db_name,
            engine_name="mssql",
            schemas=schemas,
        )

    def inspect_table_columns(self, schema_name: str, table_name: str) -> list[Column]:
        """Fetch full column metadata for specific table."""
        sql = """
            SELECT
                c.name AS column_name,
                tp.name AS data_type,
                c.max_length,
                c.precision,
                c.scale,
                c.is_nullable,
                c.is_identity AS is_auto_increment,
                OBJECT_DEFINITION(c.default_object_id) AS column_default
            FROM sys.columns c
            INNER JOIN sys.tables t ON c.object_id = t.object_id
            INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
            INNER JOIN sys.types tp ON c.user_type_id = tp.user_type_id
            WHERE s.name = %s AND t.name = %s
            ORDER BY c.column_id;
        """
        rows = self.connection.execute_query(sql, (schema_name, table_name))
        columns: list[Column] = []

        for r in rows:
            native_type = r["data_type"]
            norm_type = MSSQLTypeMapper.map_native_type(native_type)

            columns.append(
                Column(
                    name=r["column_name"],
                    native_type=native_type,
                    normalized_type=norm_type,
                    is_nullable=bool(r["is_nullable"]),
                    is_auto_increment=bool(r["is_auto_increment"]),
                    default_value=r.get("column_default"),
                )
            )

        return columns

    @staticmethod
    def _map_action(action: str) -> ForeignKeyAction:
        clean = (action or "").upper().replace("_", " ").strip()
        if "CASCADE" in clean:
            return ForeignKeyAction.CASCADE
        if "SET NULL" in clean:
            return ForeignKeyAction.SET_NULL
        if "SET DEFAULT" in clean:
            return ForeignKeyAction.SET_DEFAULT
        if "RESTRICT" in clean:
            return ForeignKeyAction.RESTRICT
        return ForeignKeyAction.NO_ACTION
