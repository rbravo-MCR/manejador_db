"""Intelligent Context-Aware Completion Engine for SQL Editor with Priority Ranking."""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from backend_ide.domain.schema import DatabaseSchema
from backend_ide.domain.sql.constants import SQL_KEYWORDS, SQL_TYPES
from backend_ide.domain.sql.joins import JoinEngine


class CompletionKind(StrEnum):
    """Completion suggestion types."""

    JOIN = "join"
    KEYWORD = "keyword"
    TYPE = "type"
    SCHEMA = "schema"
    TABLE = "table"
    VIEW = "view"
    COLUMN = "column"
    FUNCTION = "function"


class CompletionItem(BaseModel):
    """Completion item entry."""

    model_config = ConfigDict(frozen=True)

    text: str
    kind: CompletionKind
    detail: str | None = None

    @property
    def icon_prefix(self) -> str:
        """Icon emoji prefix for UI display."""
        prefix_map = {
            CompletionKind.JOIN: "🔗 ",
            CompletionKind.KEYWORD: "🔑 ",
            CompletionKind.TYPE: "🏷️ ",
            CompletionKind.SCHEMA: "📦 ",
            CompletionKind.TABLE: "📋 ",
            CompletionKind.VIEW: "👁️ ",
            CompletionKind.COLUMN: "🔹 ",
            CompletionKind.FUNCTION: "⚡ ",
        }
        return prefix_map.get(self.kind, "• ")


def extract_table_aliases(sql_text: str) -> dict[str, str]:
    """Extract mapping of {alias_or_table_lower: real_table_name} from SQL text.

    Examples:
        'SELECT * FROM reservations r' -> {'r': 'reservations', 'reservations': 'reservations'}
        'SELECT * FROM customers AS c' -> {'c': 'customers', 'customers': 'customers'}
    """
    aliases: dict[str, str] = {}
    pattern = (
        r"\b(?:FROM|(?:(?:LEFT|RIGHT|INNER|FULL|CROSS)\s+)?JOIN|INTO|UPDATE)\s+"
        r"(?:([a-zA-Z_][\w]*)\.)?([a-zA-Z_][\w]*)(?:\s+(?:AS\s+)?([a-zA-Z_][\w]*))?"
    )
    keywords = {
        "WHERE",
        "JOIN",
        "LEFT",
        "RIGHT",
        "INNER",
        "CROSS",
        "FULL",
        "ON",
        "GROUP",
        "ORDER",
        "LIMIT",
        "SET",
        "SELECT",
        "HAVING",
        "UNION",
        "VALUES",
        "AND",
        "OR",
        "NOT",
        "IS",
        "NULL",
        "BY",
        "AS",
    }
    for match in re.finditer(pattern, sql_text, re.IGNORECASE):
        _schema_name, table_name, alias = match.groups()
        if table_name and table_name.upper() not in keywords:
            aliases[table_name.lower()] = table_name
            if alias and alias.upper() not in keywords:
                aliases[alias.lower()] = table_name
    return aliases


class SqlCompletionEngine:
    """Provides SQL keywords, types, schemas, tables, columns, and FK JOIN suggestions."""

    def __init__(self, schema_model: DatabaseSchema | None = None) -> None:
        self.schema_model: DatabaseSchema | None = schema_model
        self._keyword_items = [
            CompletionItem(text=kw, kind=CompletionKind.KEYWORD, detail="SQL Keyword")
            for kw in SQL_KEYWORDS
        ]
        self._type_items = [
            CompletionItem(text=tp, kind=CompletionKind.TYPE, detail="Data Type")
            for tp in SQL_TYPES
        ]

    def set_schema_model(self, schema_model: DatabaseSchema) -> None:
        """Update active DatabaseSchema model for IntelliSense."""
        self.schema_model = schema_model

    def get_completions(
        self,
        prefix: str = "",
        context_text: str = "",
        full_text: str = "",
    ) -> list[CompletionItem]:
        """Return completion suggestions matching prefix, context, and document text."""
        prefix_clean = prefix.strip().lower()
        results: list[CompletionItem] = []
        effective_sql = f"{full_text}\n{context_text}" if full_text else context_text

        # 1. Dot context with Alias Resolution (e.g. "r.", "c.", "reservations.", "public.")
        dot_qualifier = self._find_dot_qualifier(context_text)
        if dot_qualifier and self.schema_model:
            alias_map = extract_table_aliases(effective_sql)
            real_table_name = alias_map.get(dot_qualifier.lower(), dot_qualifier)

            # Check if qualifier refers to a table (directly or through an alias)
            table = self.schema_model.find_table(real_table_name)
            if table:
                for col in table.columns:
                    if not prefix_clean or col.name.lower().startswith(prefix_clean):
                        results.append(
                            CompletionItem(
                                text=col.name,
                                kind=CompletionKind.COLUMN,
                                detail=f"{col.native_type} ({table.name}.{col.name})",
                            )
                        )
                return results

            # Check if qualifier refers to a schema (e.g. "public.users")
            schema = self.schema_model.get_schema(dot_qualifier)
            if schema:
                for t in schema.tables:
                    if not prefix_clean or t.name.lower().startswith(prefix_clean):
                        results.append(
                            CompletionItem(
                                text=t.name,
                                kind=CompletionKind.TABLE,
                                detail=f"Table ({schema.name})",
                            )
                        )
                for v in schema.views:
                    if not prefix_clean or v.name.lower().startswith(prefix_clean):
                        results.append(
                            CompletionItem(
                                text=v.name,
                                kind=CompletionKind.VIEW,
                                detail=f"View ({schema.name})",
                            )
                        )
                return results

        # 2. Table Context (e.g. "FROM ", "FROM res", "INTO ", "UPDATE ")
        # Prioritize table names!
        if self._is_table_context(context_text) and self.schema_model:
            for schema in self.schema_model.schemas:
                for table in schema.tables:
                    if not prefix_clean or table.name.lower().startswith(prefix_clean):
                        results.append(
                            CompletionItem(
                                text=table.name,
                                kind=CompletionKind.TABLE,
                                detail=f"Table ({schema.name})",
                            )
                        )
                for view in schema.views:
                    if not prefix_clean or view.name.lower().startswith(prefix_clean):
                        results.append(
                            CompletionItem(
                                text=view.name,
                                kind=CompletionKind.VIEW,
                                detail=f"View ({schema.name})",
                            )
                        )
                if not prefix_clean or schema.name.lower().startswith(prefix_clean):
                    results.append(
                        CompletionItem(
                            text=schema.name,
                            kind=CompletionKind.SCHEMA,
                            detail="Schema",
                        )
                    )

        # 3. JOIN Context (e.g. "FROM reservations r JOIN ")
        if self._is_join_context(context_text) and self.schema_model:
            tbl_name, tbl_alias = JoinEngine.extract_context_table_and_alias(context_text)
            if tbl_name:
                join_rels = JoinEngine.find_joins_for_table(
                    self.schema_model, tbl_name, source_alias=tbl_alias
                )
                for j in join_rels:
                    if not prefix_clean or j.target_table.lower().startswith(prefix_clean):
                        direction = "FK →" if j.is_outbound else "← FK"
                        results.append(
                            CompletionItem(
                                text=j.completion_text,
                                kind=CompletionKind.JOIN,
                                detail=f"{direction} {j.target_table} ({j.on_clause})",
                            )
                        )
            for schema in self.schema_model.schemas:
                for table in schema.tables:
                    if not prefix_clean or table.name.lower().startswith(prefix_clean):
                        results.append(
                            CompletionItem(
                                text=table.name,
                                kind=CompletionKind.TABLE,
                                detail=f"Table ({schema.name})",
                            )
                        )

        # 4. Context with Active Tables (e.g. in SELECT, WHERE, ON)
        # Prioritize columns of tables that are active in the query!
        if self.schema_model:
            alias_map = extract_table_aliases(effective_sql)
            for _table_alias, real_tbl_name in alias_map.items():
                ref_table = self.schema_model.find_table(real_tbl_name)
                if ref_table:
                    for col in ref_table.columns:
                        if not prefix_clean or col.name.lower().startswith(prefix_clean):
                            results.append(
                                CompletionItem(
                                    text=col.name,
                                    kind=CompletionKind.COLUMN,
                                    detail=f"{col.native_type} ({ref_table.name}.{col.name})",
                                )
                            )

            # All other columns across all tables
            for schema in self.schema_model.schemas:
                for table in schema.tables:
                    for col in table.columns:
                        if not prefix_clean or col.name.lower().startswith(prefix_clean):
                            results.append(
                                CompletionItem(
                                    text=col.name,
                                    kind=CompletionKind.COLUMN,
                                    detail=f"{col.native_type} ({table.name}.{col.name})",
                                )
                            )

                for table in schema.tables:
                    if not prefix_clean or table.name.lower().startswith(prefix_clean):
                        results.append(
                            CompletionItem(
                                text=table.name,
                                kind=CompletionKind.TABLE,
                                detail=f"Table ({schema.name})",
                            )
                        )

                for schema_item in self.schema_model.schemas:
                    if not prefix_clean or schema_item.name.lower().startswith(prefix_clean):
                        results.append(
                            CompletionItem(
                                text=schema_item.name,
                                kind=CompletionKind.SCHEMA,
                                detail="Schema",
                            )
                        )

        # 5. SQL Keywords
        for item in self._keyword_items:
            if not prefix_clean or item.text.lower().startswith(prefix_clean):
                results.append(item)

        # 6. Data Types
        for item in self._type_items:
            if not prefix_clean or item.text.lower().startswith(prefix_clean):
                results.append(item)

        # Deduplicate while strictly preserving priority order
        seen: set[tuple[str, CompletionKind]] = set()
        unique_results: list[CompletionItem] = []
        for item in results:
            key = (item.text, item.kind)
            if key not in seen:
                seen.add(key)
                unique_results.append(item)

        return unique_results

    def _is_table_context(self, context_text: str) -> bool:
        """Determine if cursor is right after FROM, INTO, UPDATE, TABLE keyword."""
        return bool(
            re.search(r"\b(?:FROM|INTO|UPDATE|TABLE)\s+[\w]*$", context_text, re.IGNORECASE)
        )

    def _is_column_context(self, context_text: str) -> bool:
        """Determine if cursor is in SELECT, WHERE, ON, ORDER BY, GROUP BY, SET context."""
        return bool(
            re.search(
                r"\b(?:SELECT|WHERE|ON|SET|GROUP\s+BY|ORDER\s+BY|HAVING|AND|OR)\s+[\w,\s]*$",
                context_text,
                re.IGNORECASE,
            )
        )

    def _is_join_context(self, context_text: str) -> bool:
        """Determine if context precedes or starts a JOIN clause."""
        return bool(
            re.search(
                r"\b(?:(?:LEFT|RIGHT|INNER|FULL|CROSS)\s+)?JOIN\s*[\w]*$",
                context_text,
                re.IGNORECASE,
            )
        )

    def _find_dot_qualifier(self, context_text: str) -> str | None:
        """Extract identifier preceding a dot (e.g. 'SELECT r.' -> 'r', 'WHERE c.' -> 'c')."""
        match = re.search(r"([a-zA-Z_][\w]*)\.[\w]*$", context_text.strip())
        if match:
            return match.group(1)
        return None
