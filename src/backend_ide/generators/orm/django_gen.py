"""Django ORM Model Generator."""

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


class DjangoModelGenerator(CodeGenerator):
    """Generates standard Django models.Model definitions."""

    target = GenerationTarget.DJANGO
    name = "Django ORM"
    language = Language.PYTHON
    category = GeneratorCategory.ORM_MODEL
    description = "Django ORM models with fields, relations, and Meta class"

    def generate_table(
        self,
        table: Table,
        schema: DatabaseSchema | None = None,
        request: GenerationRequest | None = None,
    ) -> str:
        """Generate a single Django model class."""
        class_name = table_to_class_name(table.name)
        lines: list[str] = [
            f"class {class_name}(models.Model):",
        ]

        fk_columns: dict[str, str] = {}
        for fk in table.foreign_keys:
            for mapping in fk.column_mappings:
                fk_columns[mapping.source_column] = table_to_class_name(fk.target_table)

        for col in table.columns:
            field_name = sanitize_identifier(col.name, Language.PYTHON)

            if col.name in fk_columns and request and request.include_relationships:
                target_model = fk_columns[col.name]
                rel_name = (
                    field_name.removesuffix("_id") if field_name.endswith("_id") else field_name
                )
                null_opt = "null=True, blank=True" if col.is_nullable else "null=False"
                lines.append(
                    f"    {rel_name} = models.ForeignKey("
                    f"'{target_model}', on_delete=models.CASCADE, {null_opt})"
                )
            else:
                field_def = PythonTypeMapper.to_django_field(col)
                lines.append(f"    {field_name} = {field_def}")

        lines.extend(
            [
                "",
                "    class Meta:",
                f"        db_table = '{table.name}'",
                "        managed = True",
            ]
        )

        if table.comment:
            lines.append(f"        verbose_name = '{table.comment}'")

        return "\n".join(lines)

    def generate(
        self,
        schema: DatabaseSchema,
        request: GenerationRequest,
    ) -> GeneratedProject:
        """Generate full Django models.py module."""
        tables_to_generate = filter_tables(schema, request)

        header_lines = [
            '"""Django Database Models."""',
            "",
            "from django.db import models",
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
