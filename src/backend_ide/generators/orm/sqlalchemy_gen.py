"""SQLAlchemy 2.0 Declarative Mapped Model Generator."""

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


class SQLAlchemyGenerator(CodeGenerator):
    """Generates modern SQLAlchemy 2.0 Declarative Models using Mapped and mapped_column."""

    target = GenerationTarget.SQLALCHEMY
    name = "SQLAlchemy 2.0"
    language = Language.PYTHON
    category = GeneratorCategory.ORM_MODEL
    description = "Modern Python ORM models with SQLAlchemy 2.0 type-safe Mapped[] annotations"

    def generate_table(
        self,
        table: Table,
        schema: DatabaseSchema | None = None,
        request: GenerationRequest | None = None,
    ) -> str:
        """Generate a single SQLAlchemy model class."""
        class_name = table_to_class_name(table.name)
        lines: list[str] = [
            f"class {class_name}(Base):",
            f'    __tablename__ = "{table.name}"',
        ]

        if table.schema_name and table.schema_name != "public":
            lines.append(f'    __table_args__ = {{"schema": "{table.schema_name}"}}')

        lines.append("")

        for col in table.columns:
            py_type = PythonTypeMapper.to_python_type(col)
            sa_type = PythonTypeMapper.to_sqlalchemy_type(col)
            field_name = sanitize_identifier(col.name, Language.PYTHON)

            attrs: list[str] = [sa_type]
            if col.is_primary_key:
                attrs.append("primary_key=True")
            if col.is_auto_increment:
                attrs.append("autoincrement=True")
            if not col.is_nullable and not col.is_primary_key:
                attrs.append("nullable=False")
            elif col.is_nullable:
                attrs.append("nullable=True")

            if col.default_value and not col.is_auto_increment:
                attrs.append(f"server_default='{col.default_value}'")

            # Foreign key handling
            for fk in table.foreign_keys:
                for mapping in fk.column_mappings:
                    if mapping.source_column == col.name:
                        target_ref = f"{fk.target_table}.{mapping.target_column}"
                        if fk.target_schema != "public":
                            target_ref = f"{fk.target_schema}.{target_ref}"
                        attrs.append(f'ForeignKey("{target_ref}")')

            attr_str = ", ".join(attrs)
            lines.append(f"    {field_name}: Mapped[{py_type}] = mapped_column({attr_str})")

        return "\n".join(lines)

    def generate(
        self,
        schema: DatabaseSchema,
        request: GenerationRequest,
    ) -> GeneratedProject:
        """Generate full models module for requested tables."""
        tables_to_generate = filter_tables(schema, request)

        header_lines = [
            '"""SQLAlchemy 2.0 Database Models."""',
            "",
            "from __future__ import annotations",
            "",
            "from datetime import date, datetime, time",
            "from decimal import Decimal",
            "from typing import Any",
            "from uuid import UUID",
            "",
            "from sqlalchemy import (",
            "    CHAR, JSON, Numeric, String, Text, Boolean, Date, DateTime,",
            "    Enum, Float, ForeignKey, Integer, BigInteger, SmallInteger,",
            "    Time, Uuid, LargeBinary,",
            ")",
            "from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship",
            "",
            "",
            "class Base(DeclarativeBase):",
            "    pass",
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
