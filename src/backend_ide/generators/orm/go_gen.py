"""Golang Structs and Repository Code Generator."""

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
from backend_ide.generators.naming import table_to_class_name, to_pascal_case, to_snake_case
from backend_ide.generators.type_mappers.go_types import GoTypeMapper


class GoGenerator(CodeGenerator):
    """Generates idiomatic Go struct models and CRUD repository interfaces."""

    @property
    def target(self) -> GenerationTarget:
        return GenerationTarget.GO_STRUCTS

    @property
    def language(self) -> Language:
        return Language.GO

    @property
    def category(self) -> GeneratorCategory:
        return GeneratorCategory.ORM_MODEL

    @property
    def display_name(self) -> str:
        return "Go (Structs & Repositories)"

    @property
    def description(self) -> str:
        return "Estructuras Go con tags json/db y repositorios CRUD con database/sql / sqlx."

    def generate(self, schema: DatabaseSchema, request: GenerationRequest) -> GeneratedProject:
        files: list[GeneratedFile] = []
        tables = self._filter_tables(schema, request)

        for table in tables:
            files.append(self.generate_table_model(table, request))
            files.append(self._generate_repository(table, request))

        return GeneratedProject(
            target=self.target,
            language=self.language,
            files=files,
            root_dir="models",
        )

    def generate_table_model(self, table: Table, request: GenerationRequest) -> GeneratedFile:
        """Generate Go struct file for a single table."""
        struct_name = table_to_class_name(table.name)
        lines: list[str] = [
            "package models",
            "",
            'import "time"',
            "",
            f"// {struct_name} represents the '{table.name}' database table.",
            f"type {struct_name} struct {{",
        ]

        has_time = False
        for col in table.columns:
            go_type = GoTypeMapper.map_type(col.normalized_type, col.is_nullable)
            if "time.Time" in go_type:
                has_time = True
            field_name = to_pascal_case(col.name)
            pk_tag = ' gorm:"primaryKey"' if col.is_primary_key else ""
            tag = f'`json:"{col.name}" db:"{col.name}"{pk_tag}`'
            lines.append(f"\t{field_name} {go_type} {tag}")

        lines.append("}")

        if not has_time:
            # Remove unused time import
            lines = [line for line in lines if line != 'import "time"']

        code = "\n".join(lines) + "\n"
        return GeneratedFile(
            path=f"{to_snake_case(table.name)}.go",
            content=code,
            language=self.language,
        )

    def _generate_repository(self, table: Table, request: GenerationRequest) -> GeneratedFile:
        """Generate Go CRUD Repository interface and methods."""
        struct_name = table_to_class_name(table.name)
        repo_name = f"{struct_name}Repository"
        table_snake = to_snake_case(table.name)

        pk_col = (
            table.primary_key.column_names[0]
            if table.primary_key and table.primary_key.column_names
            else "id"
        )
        pk_go_type = "int64"

        for col in table.columns:
            if col.name == pk_col:
                pk_go_type = GoTypeMapper.map_type(col.normalized_type, False)
                break

        code = f"""package repository

import (
\t"context"
\t"database/sql"
\t"fmt"

\t"models"
)

// {repo_name} defines data access operations for {struct_name}.
type {repo_name} interface {{
\tCreate(ctx context.Context, item *models.{struct_name}) error
\tGetByID(ctx context.Context, {pk_col} {pk_go_type}) (*models.{struct_name}, error)
\tList(ctx context.Context, limit, offset int) ([]*models.{struct_name}, error)
\tUpdate(ctx context.Context, item *models.{struct_name}) error
\tDelete(ctx context.Context, {pk_col} {pk_go_type}) error
}}

type sql{repo_name} struct {{
\tdb *sql.DB
}}

// New{repo_name} creates a new SQL instance of {repo_name}.
func New{repo_name}(db *sql.DB) {repo_name} {{
\treturn &sql{repo_name}{{db: db}}
}}

func (r *sql{repo_name}) GetByID(
\tctx context.Context,
\t{pk_col} {pk_go_type},
) (*models.{struct_name}, error) {{
\tquery := `SELECT * FROM {table.name} WHERE {pk_col} = $1 LIMIT 1`
\t_ = query
\t// TODO: Scan struct fields
\treturn nil, fmt.Errorf("not implemented")
}}

func (r *sql{repo_name}) Create(ctx context.Context, item *models.{struct_name}) error {{
\t// TODO: Execute INSERT statement
\treturn nil
}}

func (r *sql{repo_name}) List(
\tctx context.Context,
\tlimit, offset int,
) ([]*models.{struct_name}, error) {{
\t// TODO: Execute SELECT with LIMIT/OFFSET
\treturn nil, nil
}}

func (r *sql{repo_name}) Update(ctx context.Context, item *models.{struct_name}) error {{
\t// TODO: Execute UPDATE statement
\treturn nil
}}

func (r *sql{repo_name}) Delete(ctx context.Context, {pk_col} {pk_go_type}) error {{
\tquery := `DELETE FROM {table.name} WHERE {pk_col} = $1`
\t_, err := r.db.ExecContext(ctx, query, {pk_col})
\treturn err
}}
"""
        return GeneratedFile(
            path=f"repository/{table_snake}_repo.go",
            content=code,
            language=self.language,
        )

    def _filter_tables(self, schema: DatabaseSchema, request: GenerationRequest) -> list[Table]:
        all_tables = [t for s in schema.schemas for t in s.tables]
        if not request.selected_tables:
            return all_tables
        selected_set = set(request.selected_tables)
        return [t for t in all_tables if t.name in selected_set]
