"""Contextual, cached-metadata SQL completion engine."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator
from rapidfuzz import fuzz

from backend_ide.domain.schema import DatabaseSchema, Schema, Table
from backend_ide.domain.sql.context import SQLContext, SQLContextAnalyzer
from backend_ide.domain.sql.dialects import SQLDialectProvider, get_dialect_provider
from backend_ide.domain.sql.snippets import SnippetProvider


class CompletionKind(StrEnum):
    """Semantic kinds rendered by the completion popup."""

    KEYWORD = "keyword"
    TABLE = "table"
    VIEW = "view"
    COLUMN = "column"
    SCHEMA = "schema"
    FUNCTION = "function"
    PROCEDURE = "procedure"
    DATA_TYPE = "data_type"
    TYPE = "data_type"
    ALIAS = "alias"
    SNIPPET = "snippet"


class CompletionItem(BaseModel):
    """One ranked completion candidate."""

    model_config = ConfigDict(frozen=True)

    text: str
    insert_text: str | None = None
    kind: CompletionKind
    detail: str | None = None
    documentation: str | None = None
    score: float = 0

    @model_validator(mode="before")
    @classmethod
    def default_insert_text(cls, values: Any) -> Any:
        if isinstance(values, dict) and values.get("insert_text") is None:
            values = {**values, "insert_text": values.get("text", "")}
        return values

    @property
    def label(self) -> str:
        return self.text


class SqlCompletionEngine:
    """Complete SQL from cursor context using only an in-memory schema snapshot."""

    _max_results = 200
    _column_clauses = {
        "SELECT",
        "ON",
        "WHERE",
        "HAVING",
        "GROUP_BY",
        "ORDER_BY",
        "SET",
        "INSERT_COLUMNS",
        "RETURNING",
    }

    def __init__(self, schema_model: DatabaseSchema | None = None) -> None:
        self.schema_model = schema_model
        self.analyzer = SQLContextAnalyzer()
        self.snippets = SnippetProvider()

    def set_schema_model(self, schema_model: DatabaseSchema) -> None:
        self.schema_model = schema_model

    def complete(
        self,
        sql: str,
        cursor_position: int,
        metadata: DatabaseSchema | None = None,
        dialect: SQLDialectProvider | None = None,
    ) -> list[CompletionItem]:
        """Return ranked candidates for the exact cursor position."""
        schema_model = metadata if metadata is not None else self.schema_model
        context = self.analyzer.analyze(sql, cursor_position)
        provider = dialect or get_dialect_provider(
            schema_model.engine_name if schema_model is not None else None
        )
        prefix = context.current_token

        if context.qualifier and schema_model:
            if context.schema_qualifier:
                schema = schema_model.get_schema(context.schema_qualifier)
                return self._rank(self._relation_items(schema), prefix, context)
            table_reference = context.aliases.get(context.qualifier, context.qualifier)
            table = self._find_table(schema_model, table_reference)
            return self._rank(self._column_items(table), prefix, context)

        candidates: list[CompletionItem] = []
        if schema_model:
            if context.clause in self._column_clauses:
                candidates.extend(self._context_columns(schema_model, context))
            if context.expects_relation:
                candidates.extend(self._all_relations(schema_model))
            else:
                candidates.extend(self._all_schema_objects(schema_model))
            candidates.extend(self._metadata_routines(schema_model))

        candidates.extend(
            CompletionItem(
                text=name, kind=CompletionKind.FUNCTION, detail=f"{provider.name} function"
            )
            for name in provider.functions()
        )
        candidates.extend(
            CompletionItem(text=name, kind=CompletionKind.KEYWORD, detail="SQL keyword")
            for name in provider.keywords()
        )
        candidates.extend(
            CompletionItem(text=name, kind=CompletionKind.DATA_TYPE, detail="Data type")
            for name in provider.data_types()
        )
        candidates.extend(
            CompletionItem(
                text=snippet.trigger,
                insert_text=snippet.body,
                kind=CompletionKind.SNIPPET,
                detail=snippet.detail,
            )
            for snippet in self.snippets.complete(prefix)
        )
        return self._rank(candidates, prefix, context)

    def get_completions(self, prefix: str = "", context_text: str = "") -> list[CompletionItem]:
        """Compatibility wrapper for the original prefix-based API."""
        sql = context_text or prefix
        cursor_position = len(sql)
        if context_text and prefix:
            dot_match = re.search(rf"\.\s*{re.escape(prefix)}\b", context_text, re.I)
            if dot_match:
                cursor_position = dot_match.end()
        return self.complete(sql, cursor_position)

    def _rank(
        self, candidates: list[CompletionItem], prefix: str, context: SQLContext
    ) -> list[CompletionItem]:
        unique: dict[tuple[str, CompletionKind, str | None], CompletionItem] = {}
        for item in candidates:
            match_score = self._match_score(prefix, item.text)
            if match_score < 55:
                continue
            scored = item.model_copy(
                update={"score": match_score + self._context_score(item.kind, context)}
            )
            key = (item.text.lower(), item.kind, item.insert_text)
            previous = unique.get(key)
            if previous is None or scored.score > previous.score:
                unique[key] = scored
        ranked = sorted(unique.values(), key=lambda item: item.score, reverse=True)
        return ranked[: self._max_results]

    @staticmethod
    def _match_score(prefix: str, candidate: str) -> float:
        if not prefix:
            return 100
        prefix_lower = prefix.lower()
        candidate_lower = candidate.lower()
        if candidate_lower == prefix_lower:
            return 130
        if candidate_lower.startswith(prefix_lower):
            return 120 - min(len(candidate_lower) - len(prefix_lower), 20) / 10
        return float(fuzz.WRatio(prefix_lower, candidate_lower))

    def _context_score(self, kind: CompletionKind, context: SQLContext) -> float:
        if context.qualifier and kind == CompletionKind.COLUMN:
            return 100
        if context.clause in self._column_clauses and kind == CompletionKind.COLUMN:
            return 80
        if context.expects_relation and kind in {CompletionKind.TABLE, CompletionKind.VIEW}:
            return 80
        if context.expects_relation and kind == CompletionKind.SCHEMA:
            return 50
        if kind == CompletionKind.SNIPPET:
            return 40
        if kind == CompletionKind.KEYWORD:
            return -10
        return 0

    def _context_columns(
        self, schema_model: DatabaseSchema, context: SQLContext
    ) -> list[CompletionItem]:
        results: list[CompletionItem] = []
        alias_by_table = {table: alias for alias, table in context.aliases.items()}
        for table_reference in context.tables:
            table = self._find_table(schema_model, table_reference)
            if table is None:
                continue
            alias = alias_by_table.get(table_reference)
            for item in self._column_items(table):
                if len(context.tables) > 1 and alias:
                    item = item.model_copy(
                        update={
                            "text": f"{alias}.{item.text}",
                            "insert_text": f"{alias}.{item.text}",
                        }
                    )
                results.append(item)
        return results

    @staticmethod
    def _column_items(table: Table | None) -> list[CompletionItem]:
        if table is None:
            return []
        return [
            CompletionItem(
                text=column.name,
                kind=CompletionKind.COLUMN,
                detail=f"{column.native_type} · {table.qualified_name}",
                documentation=SqlCompletionEngine._column_documentation(column),
            )
            for column in table.columns
        ]

    @staticmethod
    def _column_documentation(column) -> str:
        properties = [column.native_type, "NULL" if column.is_nullable else "NOT NULL"]
        if column.is_primary_key:
            properties.append("PRIMARY KEY")
        if column.is_auto_increment:
            properties.append("AUTO GENERATED")
        return " · ".join(properties)

    @staticmethod
    def _relation_items(schema: Schema | None) -> list[CompletionItem]:
        if schema is None:
            return []
        return [
            *(
                CompletionItem(
                    text=table.name, kind=CompletionKind.TABLE, detail=f"Table ({schema.name})"
                )
                for table in schema.tables
            ),
            *(
                CompletionItem(
                    text=view.name, kind=CompletionKind.VIEW, detail=f"View ({schema.name})"
                )
                for view in schema.views
            ),
        ]

    def _all_relations(self, schema_model: DatabaseSchema) -> list[CompletionItem]:
        return [item for schema in schema_model.schemas for item in self._relation_items(schema)]

    def _all_schema_objects(self, schema_model: DatabaseSchema) -> list[CompletionItem]:
        results: list[CompletionItem] = []
        for schema in schema_model.schemas:
            results.append(
                CompletionItem(text=schema.name, kind=CompletionKind.SCHEMA, detail="Schema")
            )
            results.extend(self._relation_items(schema))
        return results

    @staticmethod
    def _metadata_routines(schema_model: DatabaseSchema) -> list[CompletionItem]:
        results: list[CompletionItem] = []
        for schema in schema_model.schemas:
            results.extend(
                CompletionItem(
                    text=function.name,
                    kind=CompletionKind.FUNCTION,
                    detail=f"{function.return_type} · {schema.name}",
                    documentation=function.definition,
                )
                for function in schema.functions
            )
            results.extend(
                CompletionItem(
                    text=procedure.name,
                    kind=CompletionKind.PROCEDURE,
                    detail=f"Procedure ({schema.name})",
                    documentation=procedure.definition,
                )
                for procedure in schema.procedures
            )
        return results

    @staticmethod
    def _find_table(schema_model: DatabaseSchema, reference: str) -> Table | None:
        if "." in reference:
            schema_name, table_name = reference.rsplit(".", 1)
            return schema_model.find_table(table_name, schema_name)
        return schema_model.find_table(reference)
