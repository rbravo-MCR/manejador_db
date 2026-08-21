"""FastAPI Full REST Scaffolding Generator (Pydantic v2 + SQLAlchemy 2.0 + Routers)."""

from __future__ import annotations

from backend_ide.domain.schema.models import DatabaseSchema, Table
from backend_ide.generators.contracts import (
    CodeGenerator,
    GeneratedFile,
    GeneratedProject,
    GenerationRequest,
    GenerationTarget,
    GeneratorCategory,
    Language,
)
from backend_ide.generators.naming import pluralize, table_to_class_name, to_snake_case
from backend_ide.generators.type_mappers.python_types import PythonTypeMapper


class FastAPIScaffoldGenerator(CodeGenerator):
    """Generates complete production-ready FastAPI REST APIs (Schemas, Routers, Services)."""

    @property
    def target(self) -> GenerationTarget:
        return GenerationTarget.FASTAPI_SCAFFOLD

    @property
    def language(self) -> Language:
        return Language.PYTHON

    @property
    def category(self) -> GeneratorCategory:
        return GeneratorCategory.BACKEND_SCAFFOLD

    @property
    def display_name(self) -> str:
        return "FastAPI (Full REST API Scaffolding)"

    @property
    def description(self) -> str:
        return (
            "Genera Schemas Pydantic v2, Routers REST (CRUD endpoints) y bootstrapping de FastAPI."
        )

    def generate(self, schema: DatabaseSchema, request: GenerationRequest) -> GeneratedProject:
        files: list[GeneratedFile] = []
        tables = self._filter_tables(schema, request)

        for table in tables:
            files.append(self._generate_pydantic_schema(table, request))
            files.append(self._generate_fastapi_router(table, request))

        files.append(self._generate_main_app(tables))

        return GeneratedProject(
            target=self.target,
            language=self.language,
            files=files,
            root_dir="app",
        )

    def _generate_pydantic_schema(self, table: Table, request: GenerationRequest) -> GeneratedFile:
        """Generate Pydantic v2 schemas (Base, Create, Update, Read)."""
        pascal_name = table_to_class_name(table.name)
        snake_name = to_snake_case(table.name)

        fields_base: list[str] = []
        for col in table.columns:
            if col.is_primary_key or col.is_auto_increment:
                continue
            py_type = PythonTypeMapper.to_python_type(col)
            default = " = None" if col.is_nullable else ""
            fields_base.append(f"    {col.name}: {py_type}{default}")

        fields_read: list[str] = []
        for col in table.columns:
            py_type = PythonTypeMapper.to_python_type(col)
            fields_read.append(f"    {col.name}: {py_type}")

        body_base = "\n".join(fields_base) if fields_base else "    pass"
        body_read = "\n".join(fields_read) if fields_read else "    pass"

        code = f"""\"\"\"Pydantic v2 Schemas for '{table.name}' table.\"\"\"

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class {pascal_name}Base(BaseModel):
    \"\"\"Shared base properties.\"\"\"
{body_base}


class {pascal_name}Create({pascal_name}Base):
    \"\"\"Properties required for creation.\"\"\"
    pass


class {pascal_name}Update(BaseModel):
    \"\"\"Properties allowed for partial update.\"\"\"
{body_base}


class {pascal_name}Read({pascal_name}Base):
    \"\"\"Properties returned in API responses.\"\"\"
    model_config = ConfigDict(from_attributes=True)

{body_read}
"""
        return GeneratedFile(
            path=f"schemas/{snake_name}.py",
            content=code,
            language=self.language,
        )

    def _generate_fastapi_router(self, table: Table, request: GenerationRequest) -> GeneratedFile:
        """Generate FastAPI APIRouter with standard CRUD endpoints."""
        pascal_name = table_to_class_name(table.name)
        snake_name = to_snake_case(table.name)
        singular_name = to_snake_case(pascal_name)
        plural_name = pluralize(singular_name)
        pk_col = (
            table.primary_key.column_names[0]
            if table.primary_key and table.primary_key.column_names
            else "id"
        )

        code = f"""\"\"\"FastAPI REST API endpoints for {pascal_name}.\"\"\"

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.{snake_name} import (
    {pascal_name}Create,
    {pascal_name}Read,
    {pascal_name}Update,
)

router = APIRouter(prefix="/{plural_name}", tags=["{pluralize(pascal_name)}"])


@router.get("/", response_model=list[{pascal_name}Read])
async def list_{plural_name}(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Any:
    \"\"\"Retrieve paginated list of {plural_name} records.\"\"\"
    # TODO: Query database session
    return []


@router.get("/{{{pk_col}}}", response_model={pascal_name}Read)
async def get_{singular_name}({pk_col}: int) -> Any:
    \"\"\"Get single {singular_name} by ID.\"\"\"
    # TODO: Fetch from database
    return {{}}


@router.post("/", response_model={pascal_name}Read, status_code=status.HTTP_201_CREATED)
async def create_{singular_name}(payload: {pascal_name}Create) -> Any:
    \"\"\"Create new {singular_name} record.\"\"\"
    # TODO: Insert into database
    return {{}}


@router.put("/{{{pk_col}}}", response_model={pascal_name}Read)
async def update_{singular_name}({pk_col}: int, payload: {pascal_name}Update) -> Any:
    \"\"\"Update existing {singular_name} record.\"\"\"
    # TODO: Update in database
    return {{}}


@router.delete("/{{{pk_col}}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_{singular_name}({pk_col}: int) -> None:
    \"\"\"Delete {singular_name} record.\"\"\"
    # TODO: Delete from database
    return None
"""
        return GeneratedFile(
            path=f"routers/{snake_name}_router.py",
            content=code,
            language=self.language,
        )

    def _generate_main_app(self, tables: list[Table]) -> GeneratedFile:
        """Generate main FastAPI application bootstrapping file."""
        imports: list[str] = []
        includes: list[str] = []

        for t in tables:
            snake = to_snake_case(t.name)
            imports.append(f"from app.routers.{snake}_router import router as {snake}_router")
            includes.append(f"app.include_router({snake}_router)")

        imports_str = "\n".join(imports)
        includes_str = "\n".join(includes)

        code = f"""\"\"\"FastAPI Application Entry Point.\"\"\"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

{imports_str}

app = FastAPI(
    title="Backend REST API",
    version="1.0.0",
    description="Auto-generated FastAPI REST API from Database Schema",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

{includes_str}


@app.get("/health", tags=["Health"])
async def health_check():
    return {{"status": "healthy"}}
"""
        return GeneratedFile(
            path="main.py",
            content=code,
            language=self.language,
        )

    def _filter_tables(self, schema: DatabaseSchema, request: GenerationRequest) -> list[Table]:
        all_tables = [t for s in schema.schemas for t in s.tables]
        if not request.selected_tables:
            return all_tables
        selected_set = set(request.selected_tables)
        return [t for t in all_tables if t.name in selected_set]
