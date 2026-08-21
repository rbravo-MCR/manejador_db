"""Laravel Eloquent PHP Model Generator."""

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
    singularize,
    table_to_class_name,
    to_camel_case,
)
from backend_ide.generators.type_mappers.php_types import PHPTypeMapper


class EloquentGenerator(CodeGenerator):
    """Generates PHP 8.2+ Laravel Eloquent Model classes."""

    target = GenerationTarget.ELOQUENT
    name = "Laravel Eloquent"
    language = Language.PHP
    category = GeneratorCategory.ORM_MODEL
    description = "PHP 8.2+ Laravel Eloquent Models with $fillable, $casts, and typed relationships"

    def generate_table(
        self,
        table: Table,
        schema: DatabaseSchema | None = None,
        request: GenerationRequest | None = None,
    ) -> str:
        """Generate a single Eloquent Model file content."""
        class_name = table_to_class_name(table.name)
        pk_col = next((c for c in table.columns if c.is_primary_key), None)
        pk_name = pk_col.name if pk_col else "id"
        is_auto_inc = pk_col.is_auto_increment if pk_col else True

        fillable_cols = [
            c.name for c in table.columns if not c.is_primary_key or not c.is_auto_increment
        ]
        casts: list[tuple[str, str]] = []
        for c in table.columns:
            cast = PHPTypeMapper.to_eloquent_cast(c)
            if cast:
                casts.append((c.name, cast))

        lines: list[str] = [
            "<?php",
            "",
            "namespace App\\Models;",
            "",
            "use Illuminate\\Database\\Eloquent\\Factories\\HasFactory;",
            "use Illuminate\\Database\\Eloquent\\Model;",
            "use Illuminate\\Database\\Eloquent\\Relations\\BelongsTo;",
            "use Illuminate\\Database\\Eloquent\\Relations\\HasMany;",
            "",
            f"class {class_name} extends Model",
            "{",
            "    use HasFactory;",
            "",
            f"    protected $table = '{table.name}';",
            f"    protected $primaryKey = '{pk_name}';",
        ]

        if not is_auto_inc:
            lines.append("    public $incrementing = false;")
        if pk_col and pk_col.normalized_type not in ("integer", "bigint", "smallint"):
            lines.append("    protected $keyType = 'string';")

        # Fillable
        lines.append("")
        lines.append("    protected $fillable = [")
        for col_name in fillable_cols:
            lines.append(f"        '{col_name}',")
        lines.append("    ];")

        # Casts
        if casts:
            lines.append("")
            lines.append("    protected $casts = [")
            for col_name, cast_val in casts:
                lines.append(f"        '{col_name}' => {cast_val},")
            lines.append("    ];")

        # Relationships
        if request is None or request.include_relationships:
            for fk in table.foreign_keys:
                for mapping in fk.column_mappings:
                    target_class = table_to_class_name(fk.target_table)
                    method_name = to_camel_case(singularize(fk.target_table))
                    lines.extend(
                        [
                            "",
                            f"    public function {method_name}(): BelongsTo",
                            "    {",
                            f"        return $this->belongsTo({target_class}::class, "
                            f"'{mapping.source_column}', '{mapping.target_column}');",
                            "    }",
                        ]
                    )

        lines.append("}")
        return "\n".join(lines)

    def generate(
        self,
        schema: DatabaseSchema,
        request: GenerationRequest,
    ) -> GeneratedProject:
        """Generate multi-file Eloquent models project."""
        tables_to_generate = filter_tables(schema, request)

        files: list[GeneratedFile] = []
        for table in tables_to_generate:
            class_name = table_to_class_name(table.name)
            content = self.generate_table(table, schema, request)
            files.append(
                GeneratedFile(
                    path=f"app/Models/{class_name}.php",
                    content=content,
                    language=Language.PHP,
                )
            )

        return GeneratedProject(
            target=self.target,
            files=files,
            metadata={"table_count": len(tables_to_generate)},
        )
