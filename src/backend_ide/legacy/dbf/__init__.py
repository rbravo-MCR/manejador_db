"""Legacy DBF Subsystem - Header inspection, record counting and SQL migration."""

from __future__ import annotations

from backend_ide.legacy.dbf.inspector import DBFInspector
from backend_ide.legacy.dbf.migration import DBFMigrationService
from backend_ide.legacy.dbf.models import (
    DBFField,
    DBFFieldType,
    DBFHeader,
    DBFMigrationOptions,
    DBFMigrationResult,
    DBFTableSummary,
)
from backend_ide.legacy.dbf.parser import DBFParser
from backend_ide.legacy.dbf.type_mapper import DBFTypeMapper

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
