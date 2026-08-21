"""C# Entity Framework Core Model and DbContext Generator."""

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
from backend_ide.generators.naming import table_to_class_name, to_pascal_case
from backend_ide.generators.type_mappers.csharp_types import CSharpTypeMapper


class EFCoreGenerator(CodeGenerator):
    """Generates modern C# Entity Framework Core POCOs and DbContext."""

    target = GenerationTarget.EF_CORE
    name = "Entity Framework Core"
    language = Language.CSHARP
    category = GeneratorCategory.ORM_MODEL
    description = "C# .NET EF Core entity models with Data Annotations and DbContext"

    def generate_table(
        self,
        table: Table,
        schema: DatabaseSchema | None = None,
        request: GenerationRequest | None = None,
    ) -> str:
        """Generate a single C# entity class file."""
        class_name = table_to_class_name(table.name)

        lines: list[str] = [
            "namespace App.Domain.Entities;",
            "",
            "using System;",
            "using System.ComponentModel.DataAnnotations;",
            "using System.ComponentModel.DataAnnotations.Schema;",
            "",
            f'[Table("{table.name}", Schema = "{table.schema_name}")]',
            f"public class {class_name}",
            "{",
        ]

        for col in table.columns:
            cs_type = CSharpTypeMapper.to_csharp_type(col)
            prop_name = to_pascal_case(col.name)

            if col.is_primary_key:
                lines.append("    [Key]")
            if col.length and col.length > 0:
                lines.append(f"    [MaxLength({col.length})]")
            if not col.is_nullable and not col.is_primary_key and "string" in cs_type:
                lines.append("    [Required]")

            lines.append(f'    [Column("{col.name}")]')
            if "string" in cs_type and not col.is_nullable:
                lines.append(f"    public {cs_type} {prop_name} {{ get; set; }} = string.Empty;")
            else:
                lines.append(f"    public {cs_type} {prop_name} {{ get; set; }}")
            lines.append("")

        lines.append("}")
        return "\n".join(lines)

    def generate(
        self,
        schema: DatabaseSchema,
        request: GenerationRequest,
    ) -> GeneratedProject:
        """Generate full C# EF Core entities and DbContext project."""
        tables_to_generate = filter_tables(schema, request)

        files: list[GeneratedFile] = []
        for table in tables_to_generate:
            class_name = table_to_class_name(table.name)
            content = self.generate_table(table, schema, request)
            files.append(
                GeneratedFile(
                    path=f"Entities/{class_name}.cs",
                    content=content,
                    language=Language.CSHARP,
                )
            )

        # Generate DbContext
        db_context_lines: list[str] = [
            "namespace App.Infrastructure.Data;",
            "",
            "using Microsoft.EntityFrameworkCore;",
            "using App.Domain.Entities;",
            "",
            "public class ApplicationDbContext : DbContext",
            "{",
            "    public ApplicationDbContext("
            "DbContextOptions<ApplicationDbContext> options) : base(options)",
            "    {",
            "    }",
            "",
        ]

        for table in tables_to_generate:
            class_name = table_to_class_name(table.name)
            prop_name = to_pascal_case(table.name)
            db_context_lines.append(f"    public DbSet<{class_name}> {prop_name} {{ get; set; }}")

        db_context_lines.append("}")

        files.append(
            GeneratedFile(
                path="Data/ApplicationDbContext.cs",
                content="\n".join(db_context_lines),
                language=Language.CSHARP,
            )
        )

        return GeneratedProject(
            target=self.target,
            files=files,
            metadata={"table_count": len(tables_to_generate)},
        )
