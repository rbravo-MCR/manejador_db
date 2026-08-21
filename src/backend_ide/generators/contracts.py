"""Contracts and Protocols for the Code Generation Subsystem."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from backend_ide.domain.schema.models import DatabaseSchema, Table


class Language(StrEnum):
    """Supported target programming languages."""

    PYTHON = "python"
    TYPESCRIPT = "typescript"
    PHP = "php"
    CSHARP = "csharp"
    GO = "go"
    SQL = "sql"


class GeneratorCategory(StrEnum):
    """Classification of code generator targets."""

    ORM_MODEL = "orm_model"
    NON_ORM = "non_orm"
    BACKEND_SCAFFOLD = "backend_scaffold"


class GenerationTarget(StrEnum):
    """Unique identifier for specific ORM, framework, or data access target."""

    SQLALCHEMY = "sqlalchemy"
    SQLMODEL = "sqlmodel"
    DJANGO = "django"
    FASTAPI_SCAFFOLD = "fastapi_scaffold"
    PRISMA = "prisma"
    DRIZZLE = "drizzle"
    ELOQUENT = "eloquent"
    EF_CORE = "ef_core"
    GO_STRUCTS = "go_structs"
    PYTHON_RAW = "python_raw"
    TS_RAW = "ts_raw"
    PHP_PDO = "php_pdo"
    DAPPER = "dapper"


class GenerationRequest(BaseModel):
    """Parameters and preferences for a code generation execution."""

    model_config = ConfigDict(frozen=True)

    target: GenerationTarget
    selected_tables: list[str] = Field(default_factory=list)  # Empty means all tables in schema
    schema_name: str | None = None  # None means all schemas or primary schema
    include_relationships: bool = True
    include_type_hints: bool = True
    use_async: bool = True
    output_dir: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)


class GeneratedFile(BaseModel):
    """An individual generated source file."""

    model_config = ConfigDict(frozen=True)

    path: str
    content: str
    language: Language


class GeneratedProject(BaseModel):
    """Container for the output of a multi-file or single-file generation run."""

    model_config = ConfigDict(frozen=True)

    target: GenerationTarget
    files: list[GeneratedFile] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def primary_file_content(self) -> str:
        """Helper to get content of the first or primary generated file."""
        if not self.files:
            return ""
        return self.files[0].content


@runtime_checkable
class CodeGenerator(Protocol):
    """Protocol for all code generators in the system."""

    @property
    def target(self) -> GenerationTarget:
        """Target identifier."""
        ...

    @property
    def name(self) -> str:
        """Human-readable generator name."""
        ...

    @property
    def language(self) -> Language:
        """Target programming language."""
        ...

    @property
    def category(self) -> GeneratorCategory:
        """Category of generator."""
        ...

    @property
    def description(self) -> str:
        """Description of the generated stack/flavor."""
        ...

    def generate_table(
        self,
        table: Table,
        schema: DatabaseSchema | None = None,
        request: GenerationRequest | None = None,
    ) -> str:
        """Generate code for a single table in isolation."""
        ...

    def generate(
        self,
        schema: DatabaseSchema,
        request: GenerationRequest,
    ) -> GeneratedProject:
        """Generate full output project/files from Universal Schema Model."""
        ...


def filter_tables(schema: DatabaseSchema, request: GenerationRequest) -> list[Table]:
    """Filter schema tables matching the generation request."""
    result: list[Table] = []
    for s in schema.schemas:
        if request.schema_name and s.name != request.schema_name:
            continue
        for t in s.tables:
            if not request.selected_tables:
                result.append(t)
            elif t.name in request.selected_tables or t.qualified_name in request.selected_tables:
                result.append(t)
    return result
