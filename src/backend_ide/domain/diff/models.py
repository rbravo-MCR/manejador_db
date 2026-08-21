"""Data Models for Schema Comparison and DDL Migration Scripts."""

from __future__ import annotations

from dataclasses import dataclass, field

from backend_ide.domain.schema.models import Column, ForeignKey, Table


@dataclass
class ColumnDiff:
    """Represents changes in a table column."""

    column_name: str
    diff_type: str  # 'added', 'dropped', 'modified'
    old_column: Column | None = None
    new_column: Column | None = None
    details: list[str] = field(default_factory=list)


@dataclass
class TableDiff:
    """Represents differences within a single database table."""

    table_name: str
    schema_name: str
    diff_type: str  # 'added', 'dropped', 'modified'
    added_columns: list[Column] = field(default_factory=list)
    dropped_columns: list[Column] = field(default_factory=list)
    modified_columns: list[ColumnDiff] = field(default_factory=list)
    added_fks: list[ForeignKey] = field(default_factory=list)
    dropped_fks: list[ForeignKey] = field(default_factory=list)
    pk_changed: bool = False


@dataclass
class SchemaDiffResult:
    """Complete summary of all structural differences between two database schemas."""

    source_db_name: str
    target_db_name: str
    added_tables: list[Table] = field(default_factory=list)
    dropped_tables: list[Table] = field(default_factory=list)
    modified_tables: list[TableDiff] = field(default_factory=list)

    @property
    def has_differences(self) -> bool:
        return bool(self.added_tables or self.dropped_tables or self.modified_tables)
