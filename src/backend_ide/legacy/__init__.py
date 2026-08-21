"""Legacy Layer - DBF data processing, record counting, and modern SQL migration."""

from __future__ import annotations

from backend_ide.legacy.dbf import (
    DBFField,
    DBFFieldType,
    DBFHeader,
    DBFInspector,
    DBFMigrationOptions,
    DBFMigrationResult,
    DBFMigrationService,
    DBFParser,
    DBFTableSummary,
    DBFTypeMapper,
)

__all__ = [
    "DBFField",
    "DBFFieldType",
    "DBFHeader",
    "DBFInspector",
    "DBFMigrationOptions",
    "DBFMigrationResult",
    "DBFMigrationService",
    "DBFParser",
    "DBFTableSummary",
    "DBFTypeMapper",
]
