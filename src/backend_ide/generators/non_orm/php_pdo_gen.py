"""PHP Direct PDO Data Access Generator."""

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
from backend_ide.generators.naming import table_to_class_name
from backend_ide.generators.type_mappers.php_types import PHPTypeMapper


class PHPPdoGenerator(CodeGenerator):
    """Generates PHP DTO and Repository classes using native PDO prepared statements."""

    target = GenerationTarget.PHP_PDO
    name = "PHP Native PDO"
    language = Language.PHP
    category = GeneratorCategory.NON_ORM
    description = "Type-safe PHP DTO classes and direct PDO parameterized SQL repositories"

    def generate_table(
        self,
        table: Table,
        schema: DatabaseSchema | None = None,
        request: GenerationRequest | None = None,
    ) -> str:
        """Generate a single PHP DTO and PDO Repository file."""
        dto_name = f"{table_to_class_name(table.name)}DTO"
        repo_name = f"{table_to_class_name(table.name)}Repository"
        pk_col = next((c for c in table.columns if c.is_primary_key), None)
        pk_name = pk_col.name if pk_col else "id"
        pk_php_type = PHPTypeMapper.to_php_type(pk_col).removeprefix("?") if pk_col else "int"

        col_names = [c.name for c in table.columns]
        col_list_str = ", ".join(col_names)
        insert_cols = [c.name for c in table.columns if not c.is_auto_increment]
        insert_cols_str = ", ".join(insert_cols)
        colon_placeholders = ", ".join(f":{c}" for c in insert_cols)

        lines: list[str] = [
            "<?php",
            "",
            "namespace App\\Infrastructure\\Repositories;",
            "",
            "use PDO;",
            "",
            f"readonly class {dto_name}",
            "{",
            "    public function __construct(",
        ]

        for col in table.columns:
            php_type = PHPTypeMapper.to_php_type(col)
            lines.append(f"        public {php_type} ${col.name},")

        lines.extend(
            [
                "    ) {}",
                "}",
                "",
                f"class {repo_name}",
                "{",
                "    public function __construct(private readonly PDO $pdo) {}",
                "",
                f"    public function findById({pk_php_type} ${pk_name}): ?{dto_name}",
                "    {",
                f'        $stmt = $this->pdo->prepare("SELECT {col_list_str} '
                f'FROM {table.qualified_name} WHERE {pk_name} = :id LIMIT 1");',
                f'        $stmt->execute(["id" => ${pk_name}]);',
                "        $row = $stmt->fetch(PDO::FETCH_ASSOC);",
                "        if (!$row) {",
                "            return null;",
                "        }",
                f"        return new {dto_name}(...$row);",
                "    }",
                "",
                "    public function listAll(int $limit = 100, int $offset = 0): array",
                "    {",
                f'        $stmt = $this->pdo->prepare("SELECT {col_list_str} '
                f'FROM {table.qualified_name} LIMIT :limit OFFSET :offset");',
                '        $stmt->bindValue(":limit", $limit, PDO::PARAM_INT);',
                '        $stmt->bindValue(":offset", $offset, PDO::PARAM_INT);',
                "        $stmt->execute();",
                "        $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);",
                f"        return array_map(fn($r) => new {dto_name}(...$r), $rows);",
                "    }",
                "",
                f"    public function insert({dto_name} $dto): {pk_php_type}",
                "    {",
                f'        $sql = "INSERT INTO {table.qualified_name} ({insert_cols_str}) '
                f'VALUES ({colon_placeholders})";',
                "        $stmt = $this->pdo->prepare($sql);",
                "        $stmt->execute([",
            ]
        )

        for col in insert_cols:
            lines.append(f'            "{col}" => $dto->{col},')

        lines.extend(
            [
                "        ]);",
                f"        return ({pk_php_type}) $this->pdo->lastInsertId();",
                "    }",
                "",
                f"    public function delete({pk_php_type} ${pk_name}): bool",
                "    {",
                f'        $stmt = $this->pdo->prepare("DELETE FROM {table.qualified_name} '
                f'WHERE {pk_name} = :id");',
                f'        return $stmt->execute(["id" => ${pk_name}]);',
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
        """Generate PHP PDO repository project."""
        tables_to_generate = filter_tables(schema, request)

        files: list[GeneratedFile] = []
        for table in tables_to_generate:
            class_name = table_to_class_name(table.name)
            content = self.generate_table(table, schema, request)
            files.append(
                GeneratedFile(
                    path=f"Repositories/{class_name}Repository.php",
                    content=content,
                    language=Language.PHP,
                )
            )

        return GeneratedProject(
            target=self.target,
            files=files,
            metadata={"table_count": len(tables_to_generate)},
        )
