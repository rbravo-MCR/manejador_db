"""SQLModel / Pydantic v2 Model Generator for FastAPI and modern Python."""

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
    filter_tables,
)
from backend_ide.generators.naming import sanitize_identifier, table_to_class_name
from backend_ide.generators.type_mappers.python_types import PythonTypeMapper


class SQLModelGenerator(CodeGenerator):
    """Generates SQLModel classes combining Pydantic validation and SQLAlchemy table definitions."""

    target = GenerationTarget.SQLMODEL
    name = "SQLModel"
    language = Language.PYTHON
    category = GeneratorCategory.ORM_MODEL
    description = (
        "FastAPI-ready SQLModel classes with Pydantic validation and SQLAlchemy capabilities"
    )

    def generate_table(
        self,
        table: Table,
        schema: DatabaseSchema | None = None,
        request: GenerationRequest | None = None,
    ) -> str:
        """Generate a single SQLModel table class."""
        class_name = table_to_class_name(table.name)
        lines: list[str] = [
            f"class {class_name}(SQLModel, table=True):",
            f'    __tablename__ = "{table.name}"',
        ]

        if table.schema_name and table.schema_name != "public":
            lines.append(f'    __table_args__ = {{"schema": "{table.schema_name}"}}')

        lines.append("")

        for col in table.columns:
            py_type = PythonTypeMapper.to_python_type(col)
            field_name = sanitize_identifier(col.name, Language.PYTHON)

            field_args: list[str] = []

            if col.is_primary_key:
                field_args.append("primary_key=True")
                if col.is_auto_increment or col.is_nullable:
                    field_args.append("default=None")
                    if "None" not in py_type:
                        py_type = f"{py_type} | None"
            elif col.is_nullable:
                field_args.append("default=None")

            if col.length and col.length > 0:
                field_args.append(f"max_length={col.length}")

            if col.default_value and not col.is_auto_increment:
                if col.default_value.isdigit():
                    field_args.append(f"default={col.default_value}")
                elif col.default_value.lower() in ("true", "false"):
                    field_args.append(f"default={col.default_value.capitalize()}")

            # Foreign key
            for fk in table.foreign_keys:
                for mapping in fk.column_mappings:
                    if mapping.source_column == col.name:
                        target_ref = f"{fk.target_table}.{mapping.target_column}"
                        field_args.append(f'foreign_key="{target_ref}"')

            if field_args:
                args_str = ", ".join(field_args)
                lines.append(f"    {field_name}: {py_type} = Field({args_str})")
            else:
                lines.append(f"    {field_name}: {py_type}")

        return "\n".join(lines)

    def generate(
        self,
        schema: DatabaseSchema,
        request: GenerationRequest,
    ) -> GeneratedProject:
        """Generate full SQLModel models module."""
        tables_to_generate = filter_tables(schema, request)

        header_lines = [
            '"""SQLModel Database Models."""',
            "",
            "from __future__ import annotations",
            "",
            "from datetime import date, datetime, time",
            "from decimal import Decimal",
            "from typing import Any, Optional",
            "from uuid import UUID",
            "",
            "from sqlmodel import Field, Relationship, SQLModel",
            "",
        ]

        class_blocks: list[str] = []
        for table in tables_to_generate:
            class_blocks.append(self.generate_table(table, schema, request))

        content = "\n".join(header_lines) + "\n\n" + "\n\n\n".join(class_blocks) + "\n"

        file = GeneratedFile(
            path="models.py",
            content=content,
            language=Language.PYTHON,
        )

        return GeneratedProject(
            target=self.target,
            files=[file],
            metadata={"table_count": len(tables_to_generate)},
        )
