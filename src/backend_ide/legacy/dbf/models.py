"""Data models and structures for Legacy DBF files and datasets."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DBFFieldType(StrEnum):
    """DBF data types (dBase III, IV, FoxPro, Clipper)."""

    CHARACTER = "C"
    NUMERIC = "N"
    FLOAT = "F"
    DATE = "D"
    LOGICAL = "L"
    MEMO = "M"
    DOUBLE = "B"
    INTEGER = "I"
    CURRENCY = "Y"
    DATETIME = "T"
    GENERAL = "G"
    PICTURE = "P"
    VARBINARY = "Q"
    VARCHAR = "V"
    UNKNOWN = "?"


class DBFField(BaseModel):
    """Metadata descriptor for an individual field in a DBF table."""

    model_config = ConfigDict(frozen=True)

    name: str
    field_type: DBFFieldType
    length: int
    decimal_count: int = 0
    offset: int = 0


class DBFHeader(BaseModel):
    """Parsed binary header of a DBF file."""

    model_config = ConfigDict(frozen=True)

    version: int
    last_update: date | None = None
    record_count: int  # Instant count from header
    header_length: int
    record_length: int
    encoding: str = "cp1252"
    has_memo: bool = False
    fields: list[DBFField] = Field(default_factory=list)


class DBFTableSummary(BaseModel):
    """Summary of a DBF table including record counts, file size and field count."""

    model_config = ConfigDict(frozen=True)

    table_name: str
    file_path: str
    record_count: int
    active_record_count: int | None = None  # Non-deleted count if scanned
    deleted_record_count: int | None = None
    field_count: int
    file_size_bytes: int
    last_modified: str | None = None
    fields: list[DBFField] = Field(default_factory=list)
    has_memo: bool = False


class DBFMigrationOptions(BaseModel):
    """Configuration options for migrating DBF datasets to modern SQL."""

    model_config = ConfigDict(frozen=True)

    target_schema: str = "public"
    include_deleted_records: bool = False
    deleted_column_name: str = "_is_deleted"
    batch_size: int = 1000
    create_tables: bool = True
    truncate_tables: bool = False
    sanitize_column_names: bool = True
    encoding: str = "cp1252"
    add_auto_increment_pk: bool = True
    pk_column_name: str = "id"


class DBFMigrationResult(BaseModel):
    """Results summary of a DBF migration operation."""

    model_config = ConfigDict(frozen=True)

    table_name: str
    total_records: int
    migrated_records: int
    skipped_deleted_records: int = 0
    duration_ms: float = 0.0
    has_error: bool = False
    error_message: str | None = None
