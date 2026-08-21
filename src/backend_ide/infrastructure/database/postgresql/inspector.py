"""PostgreSQL Schema Inspector.

Inspects live PostgreSQL system catalogs (information_schema and pg_catalog)
and converts the database structure into the Universal Schema Model (DatabaseSchema).
"""

from typing import Any

from backend_ide.domain.schema.enums import (
    ForeignKeyAction,
    IndexType,
)
from backend_ide.domain.schema.models import (
    CheckConstraint,
    Column,
    DatabaseSchema,
    ForeignKey,
    ForeignKeyColumnMapping,
    Function,
    Index,
    PrimaryKey,
    Procedure,
    Schema,
    Sequence,
    Table,
    Trigger,
    UniqueConstraint,
    View,
)
from backend_ide.infrastructure.database.contracts import DatabaseConnection
from backend_ide.infrastructure.database.postgresql.type_mapper import (
    map_pg_type_to_normalized,
)
from backend_ide.infrastructure.logging import get_logger

logger = get_logger(__name__)


class PostgreSQLInspector:
    """Inspector for PostgreSQL databases."""

    def __init__(self, connection: DatabaseConnection) -> None:
        self.connection = connection

    def list_databases(self) -> list[str]:
        """List non-template databases the current PostgreSQL user may connect to."""
        rows = self.connection.execute_query(
            """
            SELECT datname
            FROM pg_database
            WHERE NOT datistemplate
              AND datallowconn
              AND has_database_privilege(datname, 'CONNECT')
            ORDER BY datname;
            """
        )
        return [row["datname"] for row in rows]

    def get_schemas(self) -> list[str]:
        """Return user schemas through the shared metadata-provider contract."""
        return self._get_schemas()

    def get_tables(self, schema: str | None = None) -> list[Table]:
        """Return fully described tables for one or all user schemas."""
        schemas = [schema] if schema else self._get_schemas()
        return [table for schema_name in schemas for table in self._inspect_tables(schema_name)]

    def get_views(self, schema: str | None = None) -> list[View]:
        """Return views for one or all user schemas."""
        schemas = [schema] if schema else self._get_schemas()
        return [view for schema_name in schemas for view in self._inspect_views(schema_name)]

    def get_columns(self, table: str, schema: str | None = None) -> list[Column]:
        """Return columns for a table through the shared metadata-provider contract."""
        return self.inspect_table_columns(schema or "public", table)

    def get_foreign_keys(self, table: str, schema: str | None = None) -> list[ForeignKey]:
        """Return foreign keys for a table through the shared metadata-provider contract."""
        return self._inspect_foreign_keys(schema or "public", table)

    def get_functions(self) -> list[Function]:
        """Return functions from all user schemas."""
        return [
            function
            for schema_name in self._get_schemas()
            for function in self._inspect_routines(schema_name)[0]
        ]

    def inspect_database_summary(self) -> DatabaseSchema:
        """Build the schema, table, column, and foreign key model for Explorer and IntelliSense."""
        rows = self.connection.execute_query(
            """
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_type = 'BASE TABLE'
              AND table_schema NOT IN ('information_schema', 'pg_catalog')
              AND table_schema NOT LIKE 'pg_toast%'
            ORDER BY table_schema, table_name;
            """
        )
        if not rows:
            return DatabaseSchema(
                engine_name="postgresql",
                database_name=self._get_current_database_name(),
                schemas=[],
            )

        col_rows = self.connection.execute_query(
            """
            SELECT
                table_schema,
                table_name,
                column_name,
                data_type,
                udt_name,
                is_nullable,
                column_default,
                character_maximum_length,
                numeric_precision,
                numeric_scale,
                is_identity
            FROM information_schema.columns
            WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
              AND table_schema NOT LIKE 'pg_toast%'
            ORDER BY table_schema, table_name, ordinal_position;
            """
        )

        cols_by_table: dict[tuple[str, str], list[Column]] = {}
        for r in col_rows:
            key = (r["table_schema"], r["table_name"])
            raw_type = r["data_type"]
            if raw_type == "USER-DEFINED":
                raw_type = r["udt_name"]
            col_default = r["column_default"]
            is_auto = r.get("is_identity") == "YES" or (
                col_default is not None and "nextval" in str(col_default).lower()
            )
            norm_type = map_pg_type_to_normalized(raw_type)
            cols_by_table.setdefault(key, []).append(
                Column(
                    name=r["column_name"],
                    native_type=raw_type.upper(),
                    normalized_type=norm_type,
                    is_nullable=r["is_nullable"] == "YES",
                    is_auto_increment=is_auto,
                    default_value=str(col_default) if col_default is not None else None,
                    precision=r.get("numeric_precision"),
                    scale=r.get("numeric_scale"),
                    length=r.get("character_maximum_length"),
                )
            )

        fk_rows = self.connection.execute_query(
            """
            SELECT
                tc.constraint_name,
                tc.table_schema AS source_schema,
                tc.table_name AS source_table,
                kcu.column_name AS source_column,
                ccu.table_schema AS target_schema,
                ccu.table_name AS target_table,
                ccu.column_name AS target_column
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
             AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema NOT IN ('information_schema', 'pg_catalog')
              AND tc.table_schema NOT LIKE 'pg_toast%';
            """
        )
        fks_by_table: dict[tuple[str, str], list[ForeignKey]] = {}
        for r in fk_rows:
            key = (r["source_schema"], r["source_table"])
            fks_by_table.setdefault(key, []).append(
                ForeignKey(
                    name=r["constraint_name"],
                    source_schema=r["source_schema"],
                    source_table=r["source_table"],
                    target_schema=r["target_schema"],
                    target_table=r["target_table"],
                    column_mappings=[
                        ForeignKeyColumnMapping(
                            source_column=r["source_column"],
                            target_column=r["target_column"],
                        )
                    ],
                )
            )

        tables_by_schema: dict[str, list[Table]] = {}
        for row in rows:
            schema_name = row["table_schema"]
            tbl_name = row["table_name"]
            key = (schema_name, tbl_name)
            tables_by_schema.setdefault(schema_name, []).append(
                Table(
                    name=tbl_name,
                    schema_name=schema_name,
                    columns=cols_by_table.get(key, []),
                    foreign_keys=fks_by_table.get(key, []),
                )
            )

        return DatabaseSchema(
            engine_name="postgresql",
            database_name=self._get_current_database_name(),
            schemas=[
                Schema(name=schema_name, tables=tables)
                for schema_name, tables in tables_by_schema.items()
            ],
        )

    def inspect_completion_metadata(self) -> DatabaseSchema:
        """Load completion metadata in bounded bulk catalog queries."""
        object_rows = self.connection.execute_query(
            """
            SELECT table_schema AS schema_name,
                   table_name AS object_name,
                   CASE WHEN table_type = 'VIEW' THEN 'view' ELSE 'table' END AS object_kind
            FROM information_schema.tables
            WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
              AND table_schema NOT LIKE 'pg_toast%'
            ORDER BY table_schema, table_name;
            """
        )
        column_rows = self.connection.execute_query(
            """
            SELECT table_schema, table_name, column_name, data_type, udt_name,
                   is_nullable, column_default, character_maximum_length,
                   numeric_precision, numeric_scale, is_identity
            FROM information_schema.columns
            WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
              AND table_schema NOT LIKE 'pg_toast%'
            ORDER BY table_schema, table_name, ordinal_position;
            """
        )
        routine_rows = self.connection.execute_query(
            """
            SELECT n.nspname AS schema_name,
                   p.proname AS routine_name,
                   p.prokind AS routine_kind,
                   pg_get_function_result(p.oid) AS return_type,
                   pg_get_functiondef(p.oid) AS definition,
                   l.lanname AS language
            FROM pg_proc p
            JOIN pg_namespace n ON n.oid = p.pronamespace
            JOIN pg_language l ON l.oid = p.prolang
            WHERE n.nspname NOT IN ('information_schema', 'pg_catalog')
              AND n.nspname NOT LIKE 'pg_toast%'
            ORDER BY n.nspname, p.proname;
            """
        )

        schemas: dict[str, Schema] = {}
        columns_by_table: dict[tuple[str, str], list[Column]] = {}
        for row in column_rows:
            key = (row["table_schema"], row["table_name"])
            columns_by_table.setdefault(key, []).append(self._column_from_catalog_row(row))

        for row in object_rows:
            schema_name = row["schema_name"]
            schema = schemas.setdefault(schema_name, Schema(name=schema_name))
            if row["object_kind"] == "view":
                schema.views.append(View(name=row["object_name"], schema_name=schema_name))
            else:
                schema.tables.append(
                    Table(
                        name=row["object_name"],
                        schema_name=schema_name,
                        columns=columns_by_table.get(
                            (schema_name, row["object_name"]),
                            [],
                        ),
                    )
                )

        for row in routine_rows:
            schema_name = row["schema_name"]
            schema = schemas.setdefault(schema_name, Schema(name=schema_name))
            common = {
                "name": row["routine_name"],
                "schema_name": schema_name,
                "definition": row.get("definition"),
                "language": row.get("language"),
            }
            if row.get("routine_kind") == "p":
                schema.procedures.append(Procedure(**common))
            else:
                schema.functions.append(
                    Function(return_type=row.get("return_type") or "void", **common)
                )

        return DatabaseSchema(
            engine_name="postgresql",
            database_name=self._get_current_database_name(),
            schemas=list(schemas.values()),
        )

    def inspect_table_columns(self, schema_name: str, table_name: str) -> list[Column]:
        """Inspect fields for one expanded explorer table, including primary-key markers."""
        columns = self._inspect_columns(schema_name, table_name)
        primary_key = self._inspect_primary_key(schema_name, table_name)
        primary_names = set(primary_key.column_names if primary_key else [])
        return [
            column.model_copy(update={"is_primary_key": column.name in primary_names})
            for column in columns
        ]

    def inspect_database(
        self, schema_names: list[str] | None = None, include_views: bool = True
    ) -> DatabaseSchema:
        """Inspect PostgreSQL database and construct DatabaseSchema instance."""
        target_schemas = schema_names or self._get_schemas()
        logger.info("Starting PostgreSQL inspection", schemas=target_schemas)

        schemas: list[Schema] = []
        for schema_name in target_schemas:
            tables = self._inspect_tables(schema_name)
            views = self._inspect_views(schema_name) if include_views else []
            sequences = self._inspect_sequences(schema_name)
            functions, procedures = self._inspect_routines(schema_name)
            triggers = self._inspect_triggers(schema_name)

            schemas.append(
                Schema(
                    name=schema_name,
                    tables=tables,
                    views=views,
                    sequences=sequences,
                    functions=functions,
                    procedures=procedures,
                    triggers=triggers,
                )
            )

        return DatabaseSchema(
            engine_name="postgresql",
            database_name=self._get_current_database_name(),
            schemas=schemas,
        )

    def _get_current_database_name(self) -> str:
        """Get current database name."""
        res = self.connection.execute_query("SELECT current_database() AS db_name;")
        return res[0]["db_name"] if res else "postgres"

    def _get_schemas(self) -> list[str]:
        """Fetch list of user schemas."""
        query = """
        SELECT nspname
        FROM pg_namespace
        WHERE nspname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
          AND nspname NOT LIKE 'pg_temp_%'
          AND nspname NOT LIKE 'pg_toast_temp_%'
        ORDER BY nspname;
        """
        rows = self.connection.execute_query(query)
        return [row["nspname"] for row in rows]

    def _inspect_tables(self, schema_name: str) -> list[Table]:
        """Inspect all tables in a schema."""
        query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = %s AND table_type = 'BASE TABLE'
        ORDER BY table_name;
        """
        rows = self.connection.execute_query(query, (schema_name,))
        tables: list[Table] = []

        for row in rows:
            table_name = row["table_name"]
            columns = self._inspect_columns(schema_name, table_name)
            primary_key = self._inspect_primary_key(schema_name, table_name)
            foreign_keys = self._inspect_foreign_keys(schema_name, table_name)
            indexes = self._inspect_indexes(schema_name, table_name)
            unique_constraints = self._inspect_unique_constraints(schema_name, table_name)
            check_constraints = self._inspect_check_constraints(schema_name, table_name)

            tables.append(
                Table(
                    name=table_name,
                    schema_name=schema_name,
                    columns=columns,
                    primary_key=primary_key,
                    foreign_keys=foreign_keys,
                    indexes=indexes,
                    unique_constraints=unique_constraints,
                    check_constraints=check_constraints,
                )
            )

        return tables

    def _inspect_columns(self, schema_name: str, table_name: str) -> list[Column]:
        """Inspect columns for a table."""
        query = """
        SELECT
            column_name,
            data_type,
            udt_name,
            is_nullable,
            column_default,
            character_maximum_length,
            numeric_precision,
            numeric_scale,
            is_identity
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position;
        """
        rows = self.connection.execute_query(query, (schema_name, table_name))
        return [self._column_from_catalog_row(row) for row in rows]

    @staticmethod
    def _column_from_catalog_row(row: dict[str, Any]) -> Column:
        """Map a bulk or table-scoped information_schema row to the domain model."""
        raw_type = row["data_type"]
        if raw_type == "USER-DEFINED":
            raw_type = row["udt_name"]
        col_default = row.get("column_default")
        is_auto = row.get("is_identity") == "YES" or (
            col_default is not None and "nextval" in str(col_default).lower()
        )
        return Column(
            name=row["column_name"],
            native_type=raw_type.upper(),
            normalized_type=map_pg_type_to_normalized(raw_type),
            is_nullable=row["is_nullable"] == "YES",
            is_auto_increment=is_auto,
            default_value=str(col_default) if col_default is not None else None,
            precision=row.get("numeric_precision"),
            scale=row.get("numeric_scale"),
            length=row.get("character_maximum_length"),
        )

    def _inspect_primary_key(self, schema_name: str, table_name: str) -> PrimaryKey | None:
        """Inspect primary key for a table."""
        query = """
        SELECT tc.constraint_name, kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        WHERE tc.table_schema = %s
          AND tc.table_name = %s
          AND tc.constraint_type = 'PRIMARY KEY'
        ORDER BY kcu.ordinal_position;
        """
        rows = self.connection.execute_query(query, (schema_name, table_name))
        if not rows:
            return None

        pk_name = rows[0]["constraint_name"]
        pk_cols = [row["column_name"] for row in rows]
        return PrimaryKey(name=pk_name, column_names=pk_cols)

    def _inspect_foreign_keys(self, schema_name: str, table_name: str) -> list[ForeignKey]:
        """Inspect foreign keys for a table."""
        query = """
        SELECT
            tc.constraint_name,
            kcu.column_name AS source_column,
            ccu.table_schema AS target_schema,
            ccu.table_name AS target_table,
            ccu.column_name AS target_column,
            rc.update_rule,
            rc.delete_rule
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
          ON ccu.constraint_name = tc.constraint_name
         AND ccu.table_schema = tc.table_schema
        JOIN information_schema.referential_constraints rc
          ON rc.constraint_name = tc.constraint_name
         AND rc.constraint_schema = tc.table_schema
        WHERE tc.table_schema = %s
          AND tc.table_name = %s
          AND tc.constraint_type = 'FOREIGN KEY'
        ORDER BY tc.constraint_name, kcu.ordinal_position;
        """
        rows = self.connection.execute_query(query, (schema_name, table_name))

        fk_map: dict[str, dict[str, Any]] = {}
        for row in rows:
            name = row["constraint_name"]
            if name not in fk_map:
                fk_map[name] = {
                    "name": name,
                    "source_schema": schema_name,
                    "source_table": table_name,
                    "target_schema": row["target_schema"],
                    "target_table": row["target_table"],
                    "column_mappings": [],
                    "on_delete": self._parse_fk_action(row.get("delete_rule")),
                    "on_update": self._parse_fk_action(row.get("update_rule")),
                }
            fk_map[name]["column_mappings"].append(
                ForeignKeyColumnMapping(
                    source_column=row["source_column"],
                    target_column=row["target_column"],
                )
            )

        return [ForeignKey(**data) for data in fk_map.values()]

    def _parse_fk_action(self, rule: str | None) -> ForeignKeyAction:
        """Parse PostgreSQL FK referential action string."""
        if not rule:
            return ForeignKeyAction.NO_ACTION
        rule_clean = rule.upper().strip()
        for action in ForeignKeyAction:
            if action.value == rule_clean:
                return action
        return ForeignKeyAction.NO_ACTION

    def _inspect_indexes(self, schema_name: str, table_name: str) -> list[Index]:
        """Inspect indexes for a table."""
        query = """
        SELECT
            i.relname AS index_name,
            idx.indisunique AS is_unique,
            am.amname AS index_type,
            pg_get_expr(idx.indpred, idx.indrelid) AS filter_condition,
            array_to_string(
                array_agg(a.attname ORDER BY array_position(idx.indkey, a.attnum)), ','
            ) AS columns
        FROM pg_index idx
        JOIN pg_class t ON t.oid = idx.indrelid
        JOIN pg_class i ON i.oid = idx.indexrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        JOIN pg_am am ON am.oid = i.relam
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(idx.indkey)
        WHERE n.nspname = %s
          AND t.relname = %s
          AND idx.indisprimary = FALSE
        GROUP BY i.relname, idx.indisunique, am.amname, idx.indpred, idx.indrelid
        ORDER BY i.relname;
        """
        rows = self.connection.execute_query(query, (schema_name, table_name))
        indexes: list[Index] = []

        for row in rows:
            cols = [c.strip() for c in row["columns"].split(",") if c.strip()]
            itype = row.get("index_type", "btree").lower()
            norm_itype = IndexType.BTREE
            if itype == "hash":
                norm_itype = IndexType.HASH
            elif itype == "gin":
                norm_itype = IndexType.GIN
            elif itype == "gist":
                norm_itype = IndexType.GIST

            indexes.append(
                Index(
                    name=row["index_name"],
                    is_unique=bool(row["is_unique"]),
                    columns=cols,
                    index_type=norm_itype,
                    filter_condition=row.get("filter_condition"),
                )
            )

        return indexes

    def _inspect_unique_constraints(
        self, schema_name: str, table_name: str
    ) -> list[UniqueConstraint]:
        """Inspect unique constraints for a table."""
        query = """
        SELECT tc.constraint_name, kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        WHERE tc.table_schema = %s
          AND tc.table_name = %s
          AND tc.constraint_type = 'UNIQUE'
        ORDER BY tc.constraint_name, kcu.ordinal_position;
        """
        rows = self.connection.execute_query(query, (schema_name, table_name))
        uq_map: dict[str, list[str]] = {}
        for row in rows:
            cname = row["constraint_name"]
            uq_map.setdefault(cname, []).append(row["column_name"])

        return [UniqueConstraint(name=name, column_names=cols) for name, cols in uq_map.items()]

    def _inspect_check_constraints(
        self, schema_name: str, table_name: str
    ) -> list[CheckConstraint]:
        """Inspect check constraints for a table."""
        query = """
        SELECT tc.constraint_name, cc.check_clause
        FROM information_schema.table_constraints tc
        JOIN information_schema.check_constraints cc
          ON tc.constraint_name = cc.constraint_name
         AND tc.constraint_schema = cc.constraint_schema
        WHERE tc.table_schema = %s
          AND tc.table_name = %s
          AND tc.constraint_type = 'CHECK';
        """
        rows = self.connection.execute_query(query, (schema_name, table_name))
        return [
            CheckConstraint(name=row["constraint_name"], expression=row["check_clause"])
            for row in rows
        ]

    def _inspect_views(self, schema_name: str) -> list[View]:
        """Inspect views and materialized views in a schema."""
        query = """
        SELECT table_name AS view_name, view_definition, FALSE AS is_materialized
        FROM information_schema.views
        WHERE table_schema = %s
        UNION ALL
        SELECT matviewname AS view_name, definition AS view_definition, TRUE AS is_materialized
        FROM pg_matviews
        WHERE schemaname = %s
        ORDER BY view_name;
        """
        rows = self.connection.execute_query(query, (schema_name, schema_name))
        return [
            View(
                name=row["view_name"],
                schema_name=schema_name,
                definition=row.get("view_definition"),
                is_materialized=bool(row.get("is_materialized")),
            )
            for row in rows
        ]

    def _inspect_sequences(self, schema_name: str) -> list[Sequence]:
        """Inspect sequences in a schema."""
        query = """
        SELECT sequence_name
        FROM information_schema.sequences
        WHERE sequence_schema = %s
        ORDER BY sequence_name;
        """
        rows = self.connection.execute_query(query, (schema_name,))
        return [Sequence(name=row["sequence_name"], schema_name=schema_name) for row in rows]

    def _inspect_routines(self, schema_name: str) -> tuple[list[Function], list[Procedure]]:
        """Inspect functions and stored procedures in a schema."""
        query = """
        SELECT
            p.proname AS routine_name,
            p.prokind AS routine_kind,
            pg_get_function_result(p.oid) AS return_type,
            pg_get_functiondef(p.oid) AS definition,
            l.lanname AS language
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        JOIN pg_language l ON l.oid = p.prolang
        WHERE n.nspname = %s
        ORDER BY p.proname;
        """
        rows = self.connection.execute_query(query, (schema_name,))
        functions: list[Function] = []
        procedures: list[Procedure] = []

        for row in rows:
            kind = row.get("routine_kind", "f")
            name = row["routine_name"]
            definition = row.get("definition")
            lang = row.get("language")

            if kind == "p":
                procedures.append(
                    Procedure(
                        name=name,
                        schema_name=schema_name,
                        definition=definition,
                        language=lang,
                    )
                )
            else:
                functions.append(
                    Function(
                        name=name,
                        schema_name=schema_name,
                        return_type=row.get("return_type", "void"),
                        definition=definition,
                        language=lang,
                    )
                )

        return functions, procedures

    def _inspect_triggers(self, schema_name: str) -> list[Trigger]:
        """Inspect triggers in a schema."""
        query = """
        SELECT
            trigger_name,
            event_object_table AS table_name,
            action_timing AS timing,
            event_manipulation AS event
        FROM information_schema.triggers
        WHERE trigger_schema = %s
        ORDER BY trigger_name;
        """
        rows = self.connection.execute_query(query, (schema_name,))
        return [
            Trigger(
                name=row["trigger_name"],
                schema_name=schema_name,
                table_name=row["table_name"],
                timing=row["timing"],
                event=row["event"],
            )
            for row in rows
        ]
