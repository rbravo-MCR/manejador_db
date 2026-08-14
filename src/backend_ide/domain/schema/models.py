"""Universal Schema Model Pydantic Data Structures.

This module represents a database-agnostic, framework-agnostic schema model.
It contains NO PySide6, NO database driver, and NO framework-specific dependencies.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend_ide.domain.schema.enums import (
    ForeignKeyAction,
    IndexType,
    NormalizedDataType,
)


class Column(BaseModel):
    """Represents a database table column."""

    model_config = ConfigDict(frozen=True)

    name: str
    native_type: str
    normalized_type: NormalizedDataType = NormalizedDataType.UNKNOWN
    is_nullable: bool = True
    is_primary_key: bool = False
    is_auto_increment: bool = False
    default_value: str | None = None
    precision: int | None = None
    scale: int | None = None
    length: int | None = None
    comment: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class PrimaryKey(BaseModel):
    """Represents a primary key constraint (supports single or composite keys)."""

    model_config = ConfigDict(frozen=True)

    name: str | None = None
    column_names: list[str]


class ForeignKeyColumnMapping(BaseModel):
    """Maps a source column to a target column in a foreign key."""

    model_config = ConfigDict(frozen=True)

    source_column: str
    target_column: str


class ForeignKey(BaseModel):
    """Represents a foreign key constraint (supports single or composite keys)."""

    model_config = ConfigDict(frozen=True)

    name: str | None = None
    source_schema: str = "public"
    source_table: str
    target_schema: str = "public"
    target_table: str
    column_mappings: list[ForeignKeyColumnMapping]
    on_delete: ForeignKeyAction = ForeignKeyAction.NO_ACTION
    on_update: ForeignKeyAction = ForeignKeyAction.NO_ACTION

    @property
    def source_columns(self) -> list[str]:
        """List of source column names."""
        return [m.source_column for m in self.column_mappings]

    @property
    def target_columns(self) -> list[str]:
        """List of target column names."""
        return [m.target_column for m in self.column_mappings]


class Index(BaseModel):
    """Represents a database index."""

    model_config = ConfigDict(frozen=True)

    name: str
    is_unique: bool = False
    columns: list[str]
    index_type: IndexType = IndexType.BTREE
    filter_condition: str | None = None


class UniqueConstraint(BaseModel):
    """Represents a unique constraint."""

    model_config = ConfigDict(frozen=True)

    name: str | None = None
    column_names: list[str]


class CheckConstraint(BaseModel):
    """Represents a check constraint."""

    model_config = ConfigDict(frozen=True)

    name: str | None = None
    expression: str


class Sequence(BaseModel):
    """Represents a database sequence."""

    model_config = ConfigDict(frozen=True)

    name: str
    schema_name: str = "public"
    start_value: int = 1
    increment_by: int = 1


class View(BaseModel):
    """Represents a database view or materialized view."""

    model_config = ConfigDict(frozen=True)

    name: str
    schema_name: str = "public"
    definition: str | None = None
    is_materialized: bool = False
    comment: str | None = None


class Trigger(BaseModel):
    """Represents a database trigger."""

    model_config = ConfigDict(frozen=True)

    name: str
    schema_name: str = "public"
    table_name: str
    timing: str  # BEFORE, AFTER, INSTEAD OF
    event: str  # INSERT, UPDATE, DELETE
    definition: str | None = None


class RoutineParameter(BaseModel):
    """Represents a parameter for a function or stored procedure."""

    model_config = ConfigDict(frozen=True)

    name: str
    data_type: str
    mode: str = "IN"  # IN, OUT, INOUT


class Function(BaseModel):
    """Represents a database function."""

    model_config = ConfigDict(frozen=True)

    name: str
    schema_name: str = "public"
    return_type: str = "void"
    parameters: list[RoutineParameter] = Field(default_factory=list)
    definition: str | None = None
    language: str | None = None


class Procedure(BaseModel):
    """Represents a stored procedure."""

    model_config = ConfigDict(frozen=True)

    name: str
    schema_name: str = "public"
    parameters: list[RoutineParameter] = Field(default_factory=list)
    definition: str | None = None
    language: str | None = None


class Relationship(BaseModel):
    """High-level entity relationship derived from foreign keys for ERD and JOINs."""

    model_config = ConfigDict(frozen=True)

    name: str | None = None
    source_table_qualified: str
    target_table_qualified: str
    column_mappings: list[tuple[str, str]]
    is_identifying: bool = False


class Table(BaseModel):
    """Represents a database table."""

    name: str
    schema_name: str = "public"
    columns: list[Column] = Field(default_factory=list)
    primary_key: PrimaryKey | None = None
    foreign_keys: list[ForeignKey] = Field(default_factory=list)
    indexes: list[Index] = Field(default_factory=list)
    unique_constraints: list[UniqueConstraint] = Field(default_factory=list)
    check_constraints: list[CheckConstraint] = Field(default_factory=list)
    comment: str | None = None

    @property
    def qualified_name(self) -> str:
        """Return schema-qualified table name (e.g., 'public.users')."""
        return f"{self.schema_name}.{self.name}"

    def get_column(self, name: str) -> Column | None:
        """Find column by name (case-insensitive)."""
        name_lower = name.lower()
        for col in self.columns:
            if col.name.lower() == name_lower:
                return col
        return None

    @model_validator(mode="after")
    def sync_primary_key_columns(self) -> Table:
        """Ensure column.is_primary_key is True for columns in primary_key."""
        if self.primary_key:
            pk_cols = set(self.primary_key.column_names)
            updated_cols = []
            for col in self.columns:
                if col.name in pk_cols and not col.is_primary_key:
                    updated_cols.append(col.model_copy(update={"is_primary_key": True}))
                else:
                    updated_cols.append(col)
            object.__setattr__(self, "columns", updated_cols)
        return self


class Schema(BaseModel):
    """Represents a database schema containing tables, views, routines, etc."""

    name: str = "public"
    tables: list[Table] = Field(default_factory=list)
    views: list[View] = Field(default_factory=list)
    sequences: list[Sequence] = Field(default_factory=list)
    functions: list[Function] = Field(default_factory=list)
    procedures: list[Procedure] = Field(default_factory=list)
    triggers: list[Trigger] = Field(default_factory=list)

    def get_table(self, name: str) -> Table | None:
        """Find table by name in this schema (case-insensitive)."""
        name_lower = name.lower()
        for table in self.tables:
            if table.name.lower() == name_lower:
                return table
        return None


class DatabaseSchema(BaseModel):
    """Universal Schema Model representing an entire database."""

    engine_name: str = "generic"
    version: str | None = None
    database_name: str = "defaultdb"
    schemas: list[Schema] = Field(default_factory=list)

    def get_schema(self, name: str) -> Schema | None:
        """Find schema by name (case-insensitive)."""
        name_lower = name.lower()
        for s in self.schemas:
            if s.name.lower() == name_lower:
                return s
        return None

    def find_table(self, table_name: str, schema_name: str | None = None) -> Table | None:
        """Find table across schemas or in specific schema."""
        if schema_name:
            s = self.get_schema(schema_name)
            return s.get_table(table_name) if s else None

        for s in self.schemas:
            table = s.get_table(table_name)
            if table:
                return table
        return None

    def extract_all_relationships(self) -> list[Relationship]:
        """Extract high-level Relationship entities from all foreign keys."""
        relationships = []
        for s in self.schemas:
            for t in s.tables:
                for fk in t.foreign_keys:
                    mappings = [(m.source_column, m.target_column) for m in fk.column_mappings]
                    source_qual = f"{fk.source_schema}.{fk.source_table}"
                    target_qual = f"{fk.target_schema}.{fk.target_table}"
                    relationships.append(
                        Relationship(
                            name=fk.name,
                            source_table_qualified=source_qual,
                            target_table_qualified=target_qual,
                            column_mappings=mappings,
                        )
                    )
        return relationships
