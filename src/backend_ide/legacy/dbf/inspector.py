"""Legacy DBF Directory and File Inspector."""

from __future__ import annotations

import datetime
import os

from backend_ide.domain.schema.models import DatabaseSchema, Schema, Table
from backend_ide.legacy.dbf.models import DBFTableSummary
from backend_ide.legacy.dbf.parser import DBFParser
from backend_ide.legacy.dbf.type_mapper import DBFTypeMapper


class DBFInspector:
    """Inspects legacy DBF files and folders, computing record counts and building schemas."""

    @classmethod
    def inspect_file(
        cls,
        filepath: str,
        *,
        scan_deleted: bool = False,
        encoding: str = "cp1252",
    ) -> DBFTableSummary:
        """Inspect a single DBF file, extract instant record counts and metadata."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"DBF file not found: {filepath}")

        header = DBFParser.read_header(filepath, encoding=encoding)
        stat = os.stat(filepath)
        mod_time = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        table_name = os.path.splitext(os.path.basename(filepath))[0]

        active_count = None
        deleted_count = None
        if scan_deleted:
            active_count, deleted_count = DBFParser.count_active_records(filepath, header)

        return DBFTableSummary(
            table_name=table_name,
            file_path=filepath,
            record_count=header.record_count,
            active_record_count=active_count,
            deleted_record_count=deleted_count,
            field_count=len(header.fields),
            file_size_bytes=stat.st_size,
            last_modified=mod_time,
            fields=header.fields,
            has_memo=header.has_memo,
        )

    @classmethod
    def inspect_directory(
        cls,
        directory_path: str,
        *,
        scan_deleted: bool = False,
        encoding: str = "cp1252",
    ) -> list[DBFTableSummary]:
        """Scan directory and return table summaries with record counts for all DBF files."""
        if not os.path.isdir(directory_path):
            raise NotADirectoryError(f"Directory not found: {directory_path}")

        summaries: list[DBFTableSummary] = []
        for filename in sorted(os.listdir(directory_path)):
            if filename.lower().endswith(".dbf"):
                full_path = os.path.join(directory_path, filename)
                try:
                    summary = cls.inspect_file(
                        full_path,
                        scan_deleted=scan_deleted,
                        encoding=encoding,
                    )
                    summaries.append(summary)
                except Exception:
                    # Skip corrupt non-DBF files gracefully
                    continue

        return summaries

    @classmethod
    def to_database_schema(
        cls,
        directory_path: str,
        database_name: str = "legacy_dbf",
        *,
        sanitize_names: bool = True,
        encoding: str = "cp1252",
    ) -> DatabaseSchema:
        """Convert a directory of DBF files into the Universal Schema Model."""
        summaries = cls.inspect_directory(directory_path, encoding=encoding)
        tables: list[Table] = []

        for summary in summaries:
            table_name = summary.table_name.lower() if sanitize_names else summary.table_name
            cols = [
                DBFTypeMapper.to_column_model(f, sanitize_name=sanitize_names)
                for f in summary.fields
            ]
            tables.append(
                Table(
                    name=table_name,
                    schema_name="public",
                    columns=cols,
                    comment=f"Legacy DBF Table ({summary.record_count} records)",
                )
            )

        return DatabaseSchema(
            engine_name="dbf",
            database_name=database_name,
            schemas=[Schema(name="public", tables=tables)],
        )
