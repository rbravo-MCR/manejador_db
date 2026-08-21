"""DBF Migration Service for migrating legacy tables to PostgreSQL, SQLite, or MySQL."""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Callable

from backend_ide.domain.schema.enums import NormalizedDataType
from backend_ide.legacy.dbf.inspector import DBFInspector
from backend_ide.legacy.dbf.models import (
    DBFMigrationOptions,
    DBFMigrationResult,
    DBFTableSummary,
)
from backend_ide.legacy.dbf.parser import DBFParser
from backend_ide.legacy.dbf.type_mapper import DBFTypeMapper


class DBFMigrationService:
    """Service for migrating DBF structures and data batches to modern SQL databases."""

    @classmethod
    def generate_create_table_sql(
        cls,
        summary: DBFTableSummary,
        dialect: str = "postgresql",
        options: DBFMigrationOptions | None = None,
    ) -> str:
        """Generate DDL CREATE TABLE statement from DBF metadata."""
        opts = options or DBFMigrationOptions()
        table_name = (
            summary.table_name.lower() if opts.sanitize_column_names else summary.table_name
        )
        lines: list[str] = []

        existing_col_names = {
            f.name.lower() if opts.sanitize_column_names else f.name for f in summary.fields
        }
        has_matching_pk = opts.pk_column_name.lower() in existing_col_names

        for f in summary.fields:
            col = DBFTypeMapper.to_column_model(f, sanitize_name=opts.sanitize_column_names)
            sql_type = cls._to_sql_column_type(
                col.normalized_type, col.length, col.precision, col.scale, dialect
            )
            if opts.add_auto_increment_pk and col.name.lower() == opts.pk_column_name.lower():
                if dialect == "sqlite":
                    lines.append(f"    {col.name} INTEGER PRIMARY KEY AUTOINCREMENT")
                elif dialect == "postgresql":
                    lines.append(f"    {col.name} SERIAL PRIMARY KEY")
                else:
                    lines.append(f"    {col.name} INT AUTO_INCREMENT PRIMARY KEY")
            else:
                lines.append(f"    {col.name} {sql_type}")

        if opts.add_auto_increment_pk and not has_matching_pk:
            if dialect == "postgresql":
                lines.insert(0, f"    {opts.pk_column_name} SERIAL PRIMARY KEY")
            elif dialect == "sqlite":
                lines.insert(0, f"    {opts.pk_column_name} INTEGER PRIMARY KEY AUTOINCREMENT")
            else:
                lines.insert(0, f"    {opts.pk_column_name} INT AUTO_INCREMENT PRIMARY KEY")

        if opts.include_deleted_records:
            lines.append(f"    {opts.deleted_column_name} BOOLEAN DEFAULT FALSE")

        cols_str = ",\n".join(lines)
        qual_table = (
            f"{opts.target_schema}.{table_name}"
            if dialect == "postgresql" and opts.target_schema
            else table_name
        )
        return f"CREATE TABLE IF NOT EXISTS {qual_table} (\n{cols_str}\n);"

    @classmethod
    def migrate_table_to_sqlite(
        cls,
        sqlite_conn: sqlite3.Connection,
        summary: DBFTableSummary,
        options: DBFMigrationOptions | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> DBFMigrationResult:
        """Migrate a single DBF table and stream data batches into a SQLite connection."""
        opts = options or DBFMigrationOptions()
        start_time = time.perf_counter()
        table_name = (
            summary.table_name.lower() if opts.sanitize_column_names else summary.table_name
        )

        try:
            # 1. Create table DDL
            if opts.create_tables:
                ddl = cls.generate_create_table_sql(summary, dialect="sqlite", options=opts)
                sqlite_conn.execute(ddl)

            if opts.truncate_tables:
                sqlite_conn.execute(f"DELETE FROM {table_name};")

            # 2. Prepare Insert SQL
            cols = [
                f.name.lower() if opts.sanitize_column_names else f.name for f in summary.fields
            ]
            if opts.include_deleted_records:
                cols.append(opts.deleted_column_name)

            col_list = ", ".join(cols)
            placeholders = ", ".join("?" for _ in cols)
            insert_sql = f"INSERT INTO {table_name} ({col_list}) VALUES ({placeholders});"

            # 3. Stream data in batches
            migrated = 0
            header = DBFParser.read_header(summary.file_path, encoding=opts.encoding)

            for batch in DBFParser.stream_batches(
                summary.file_path,
                header=header,
                batch_size=opts.batch_size,
                include_deleted=opts.include_deleted_records,
                encoding=opts.encoding,
            ):
                rows_to_insert = []
                for row_dict in batch:
                    row_tuple = []
                    for f in summary.fields:
                        val = row_dict.get(f.name)
                        row_tuple.append(
                            str(val)
                            if val is not None and not isinstance(val, (int, float, bool))
                            else val
                        )
                    if opts.include_deleted_records:
                        row_tuple.append(row_dict.get("_is_deleted", False))
                    rows_to_insert.append(row_tuple)

                sqlite_conn.executemany(insert_sql, rows_to_insert)
                sqlite_conn.commit()
                migrated += len(rows_to_insert)

                if progress_callback:
                    progress_callback(migrated, summary.record_count)

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return DBFMigrationResult(
                table_name=summary.table_name,
                total_records=summary.record_count,
                migrated_records=migrated,
                duration_ms=elapsed_ms,
            )

        except Exception as err:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return DBFMigrationResult(
                table_name=summary.table_name,
                total_records=summary.record_count,
                migrated_records=0,
                duration_ms=elapsed_ms,
                has_error=True,
                error_message=str(err),
            )

    @classmethod
    def migrate_directory_to_sqlite_file(
        cls,
        directory_path: str,
        output_sqlite_path: str,
        options: DBFMigrationOptions | None = None,
        progress_callback: Callable[[str, int, int], None] | None = None,
    ) -> list[DBFMigrationResult]:
        """Migrate all DBF tables in a folder into a single SQLite database file."""
        opts = options or DBFMigrationOptions()
        summaries = DBFInspector.inspect_directory(directory_path, encoding=opts.encoding)
        results: list[DBFMigrationResult] = []

        conn = sqlite3.connect(output_sqlite_path)
        try:
            for summary in summaries:
                tbl_name = summary.table_name

                def make_progress(t_name: str):
                    def table_progress(curr: int, tot: int) -> None:
                        if progress_callback:
                            progress_callback(t_name, curr, tot)

                    return table_progress

                res = cls.migrate_table_to_sqlite(
                    conn, summary, opts, progress_callback=make_progress(tbl_name)
                )
                results.append(res)
        finally:
            conn.close()

        return results

    @staticmethod
    def _to_sql_column_type(
        nt: NormalizedDataType,
        length: int | None,
        precision: int | None,
        scale: int | None,
        dialect: str,
    ) -> str:
        """Convert normalized type to dialect-specific SQL column type."""
        if dialect == "sqlite":
            if nt in (
                NormalizedDataType.INTEGER,
                NormalizedDataType.BIGINT,
                NormalizedDataType.SMALLINT,
            ):
                return "INTEGER"
            elif nt in (NormalizedDataType.DECIMAL, NormalizedDataType.FLOAT):
                return "REAL"
            elif nt == NormalizedDataType.BOOLEAN:
                return "INTEGER"
            elif nt == NormalizedDataType.BINARY:
                return "BLOB"
            return "TEXT"

        # PostgreSQL default
        if nt == NormalizedDataType.VARCHAR:
            col_len = length or 255
            return f"VARCHAR({col_len})"
        elif nt == NormalizedDataType.TEXT:
            return "TEXT"
        elif nt == NormalizedDataType.INTEGER:
            return "INTEGER"
        elif nt == NormalizedDataType.BIGINT:
            return "BIGINT"
        elif nt == NormalizedDataType.DECIMAL:
            p = precision or 12
            s = scale or 2
            return f"NUMERIC({p}, {s})"
        elif nt == NormalizedDataType.FLOAT:
            return "DOUBLE PRECISION"
        elif nt == NormalizedDataType.BOOLEAN:
            return "BOOLEAN"
        elif nt == NormalizedDataType.DATE:
            return "DATE"
        elif nt in (
            NormalizedDataType.DATETIME,
            NormalizedDataType.TIMESTAMP,
            NormalizedDataType.TIMESTAMPTZ,
        ):
            return "TIMESTAMP"
        elif nt == NormalizedDataType.BINARY:
            return "BYTEA"

        return "VARCHAR(255)"
