"""C# Dapper POCO and Async Repository Generator."""

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


class DapperGenerator(CodeGenerator):
    """Generates high-performance C# POCO records and Dapper async repositories."""

    target = GenerationTarget.DAPPER
    name = "C# Dapper (Micro-ORM)"
    language = Language.CSHARP
    category = GeneratorCategory.NON_ORM
    description = "High-performance C# POCO models and asynchronous Dapper repositories"

    def generate_table(
        self,
        table: Table,
        schema: DatabaseSchema | None = None,
        request: GenerationRequest | None = None,
    ) -> str:
        """Generate a single C# POCO entity and Dapper repository."""
        class_name = table_to_class_name(table.name)
        repo_name = f"{class_name}Repository"
        pk_col = next((c for c in table.columns if c.is_primary_key), None)
        pk_name = pk_col.name if pk_col else "id"
        pk_cs_type = CSharpTypeMapper.to_csharp_type(pk_col) if pk_col else "int"

        col_names = [c.name for c in table.columns]
        col_list_str = ", ".join(col_names)
        insert_cols = [c.name for c in table.columns if not c.is_auto_increment]
        insert_cols_str = ", ".join(insert_cols)
        dapper_params = ", ".join(f"@{to_pascal_case(c)}" for c in insert_cols)

        lines: list[str] = [
            "namespace App.Domain.Entities;",
            "",
            "using System;",
            "",
            f"public record {class_name}",
            "{",
        ]

        for col in table.columns:
            cs_type = CSharpTypeMapper.to_csharp_type(col)
            prop_name = to_pascal_case(col.name)
            if "string" in cs_type and not col.is_nullable:
                lines.append(f"    public {cs_type} {prop_name} {{ get; init; }} = string.Empty;")
            else:
                lines.append(f"    public {cs_type} {prop_name} {{ get; init; }}")

        lines.extend(
            [
                "}",
                "",
                "namespace App.Infrastructure.Repositories;",
                "",
                "using System.Data;",
                "using System.Collections.Generic;",
                "using System.Threading.Tasks;",
                "using Dapper;",
                "using App.Domain.Entities;",
                "",
                f"public class {repo_name}",
                "{",
                "    private readonly IDbConnection _db;",
                "",
                f"    public {repo_name}(IDbConnection db)",
                "    {",
                "        _db = db;",
                "    }",
                "",
                f"    public async Task<{class_name}?> GetByIdAsync({pk_cs_type} {pk_name})",
                "    {",
                f'        const string sql = "SELECT {col_list_str} FROM {table.qualified_name} '
                f'WHERE {pk_name} = @Id;";',
                f"        return await _db.QuerySingleOrDefaultAsync<{class_name}>("
                f"sql, new {{ Id = {pk_name} }});",
                "    }",
                "",
                "    public async Task<IEnumerable<"
                f"{class_name}>> GetAllAsync(int limit = 100, int offset = 0)",
                "    {",
                f'        const string sql = "SELECT {col_list_str} FROM {table.qualified_name} '
                'LIMIT @Limit OFFSET @Offset;";',
                f"        return await _db.QueryAsync<{class_name}>("
                "sql, new { Limit = limit, Offset = offset });",
                "    }",
                "",
                f"    public async Task<{pk_cs_type}> InsertAsync({class_name} entity)",
                "    {",
                f'        const string sql = @"INSERT INTO {table.qualified_name} '
                f"({insert_cols_str})",
                f"                             VALUES ({dapper_params})",
                f'                             RETURNING {pk_name};";',
                f"        return await _db.ExecuteScalarAsync<{pk_cs_type}>(sql, entity);",
                "    }",
                "",
                f"    public async Task<bool> DeleteAsync({pk_cs_type} {pk_name})",
                "    {",
                f'        const string sql = "DELETE FROM {table.qualified_name} '
                f'WHERE {pk_name} = @Id;";',
                f"        var affected = await _db.ExecuteAsync(sql, new {{ Id = {pk_name} }});",
                "        return affected > 0;",
                "    }",
                "}",
            ]
        )

        return "\n".join(lines)

    def generate(
        self,
        schema: DatabaseSchema,
        request: GenerationRequest,
    ) -> GeneratedProject:
        """Generate C# Dapper repositories and POCOs."""
        tables_to_generate = filter_tables(schema, request)

        files: list[GeneratedFile] = []
        for table in tables_to_generate:
            class_name = table_to_class_name(table.name)
            content = self.generate_table(table, schema, request)
            files.append(
                GeneratedFile(
                    path=f"Repositories/{class_name}Repository.cs",
                    content=content,
                    language=Language.CSHARP,
                )
            )

        return GeneratedProject(
            target=self.target,
            files=files,
            metadata={"table_count": len(tables_to_generate)},
        )
