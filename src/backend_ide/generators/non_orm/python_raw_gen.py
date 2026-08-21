"""Python Direct SQL / psycopg3 / asyncpg Repository Generator."""

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
from backend_ide.generators.naming import (
    sanitize_identifier,
    table_to_class_name,
)
from backend_ide.generators.type_mappers.python_types import PythonTypeMapper


class PythonRawGenerator(CodeGenerator):
    """Generates pure Python @dataclass entities and async parameterized SQL Repositories."""

    target = GenerationTarget.PYTHON_RAW
    name = "Python Native SQL (psycopg/asyncpg)"
    language = Language.PYTHON
    category = GeneratorCategory.NON_ORM
    description = "Zero-ORM Python dataclasses and type-safe async SQL repositories"

    def generate_table(
        self,
        table: Table,
        schema: DatabaseSchema | None = None,
        request: GenerationRequest | None = None,
    ) -> str:
        """Generate Dataclass and Repository for a single table."""
        class_name = table_to_class_name(table.name)
        repo_name = f"{class_name}Repository"
        pk_col = next((c for c in table.columns if c.is_primary_key), None)
        pk_name = pk_col.name if pk_col else "id"
        pk_py_type = PythonTypeMapper.to_python_type(pk_col) if pk_col else "int"

        col_names = [c.name for c in table.columns]
        col_list_str = ", ".join(col_names)
        insert_cols = [c.name for c in table.columns if not c.is_auto_increment]
        insert_cols_str = ", ".join(insert_cols)
        placeholders = ", ".join(f"%({c})s" for c in insert_cols)

        lines: list[str] = [
            "@dataclass(frozen=True)",
            f"class {class_name}:",
            f'    """Data transfer model for table {table.name}."""',
        ]

        for col in table.columns:
            py_type = PythonTypeMapper.to_python_type(col)
            field_name = sanitize_identifier(col.name, Language.PYTHON)
            if col.is_nullable or col.is_auto_increment:
                lines.append(f"    {field_name}: {py_type} = None")
            else:
                lines.append(f"    {field_name}: {py_type}")

        lines.extend(
            [
                "",
                "",
                f"class {repo_name}:",
                f'    """Type-safe direct SQL repository for table {table.name}."""',
                "",
                "    def __init__(self, connection: Any) -> None:",
                "        self._conn = connection",
                "",
                f"    async def get_by_{pk_name}("
                f"self, {pk_name}: {pk_py_type}) -> Optional[{class_name}]:",
                '        """Fetch a single record by its primary key."""',
                f'        query = "SELECT {col_list_str} FROM {table.qualified_name} '
                f'WHERE {pk_name} = %s;"',
                f"        cursor = await self._conn.execute(query, ({pk_name},))",
                "        row = await cursor.fetchone()",
                "        if not row:",
                "            return None",
                f"        return {class_name}(**row)",
                "",
                f"    async def list_all("
                f"self, limit: int = 100, offset: int = 0) -> list[{class_name}]:",
                '        """Fetch paginated records."""',
                f'        query = "SELECT {col_list_str} FROM {table.qualified_name} '
                'LIMIT %s OFFSET %s;"',
                "        cursor = await self._conn.execute(query, (limit, offset))",
                "        rows = await cursor.fetchall()",
                f"        return [{class_name}(**r) for r in rows]",
                "",
                f"    async def insert(self, entity: {class_name}) -> {pk_py_type}:",
                '        """Insert record with parameterized attributes."""',
                '        query = """',
                f"            INSERT INTO {table.qualified_name} ({insert_cols_str})",
                f"            VALUES ({placeholders})",
                f"            RETURNING {pk_name};",
                '        """',
                "        cursor = await self._conn.execute(query, asdict(entity))",
                "        result = await cursor.fetchone()",
                f'        return result["{pk_name}"]',
                "",
                f"    async def delete_by_{pk_name}(self, {pk_name}: {pk_py_type}) -> bool:",
                '        """Delete record by primary key."""',
                f'        query = "DELETE FROM {table.qualified_name} WHERE {pk_name} = %s;"',
                f"        cursor = await self._conn.execute(query, ({pk_name},))",
                "        return bool(cursor.rowcount and cursor.rowcount > 0)",
            ]
        )

        return "\n".join(lines)

    def generate(
        self,
        schema: DatabaseSchema,
        request: GenerationRequest,
    ) -> GeneratedProject:
        """Generate pure Python entities and repositories."""
        tables_to_generate = filter_tables(schema, request)

        header_lines = [
            '"""Pure Python Data Access Layer with Type-Safe Direct SQL Repositories."""',
            "",
            "from __future__ import annotations",
            "",
            "from dataclasses import asdict, dataclass",
            "from datetime import date, datetime, time",
            "from decimal import Decimal",
            "from typing import Any, Optional",
            "from uuid import UUID",
            "",
        ]

        blocks: list[str] = []
        for table in tables_to_generate:
            blocks.append(self.generate_table(table, schema, request))

        content = "\n".join(header_lines) + "\n\n" + "\n\n\n".join(blocks) + "\n"

        file = GeneratedFile(
            path="repositories.py",
            content=content,
            language=Language.PYTHON,
        )

        return GeneratedProject(
            target=self.target,
            files=[file],
            metadata={"table_count": len(tables_to_generate)},
        )
