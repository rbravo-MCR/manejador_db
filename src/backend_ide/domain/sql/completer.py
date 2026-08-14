"""Intelligent Context-Aware Completion Engine for SQL Editor."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from backend_ide.domain.schema import DatabaseSchema
from backend_ide.domain.sql.constants import SQL_KEYWORDS, SQL_TYPES


class CompletionKind(StrEnum):
    """Completion suggestion types."""

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
            CompletionKind.KEYWORD: "🔑 ",
            CompletionKind.TYPE: "🏷️ ",
            CompletionKind.SCHEMA: "📦 ",
            CompletionKind.TABLE: "📋 ",
            CompletionKind.VIEW: "👁️ ",
            CompletionKind.COLUMN: "🔹 ",
            CompletionKind.FUNCTION: "⚡ ",
        }
        return prefix_map.get(self.kind, "• ")


class SqlCompletionEngine:
    """Provides SQL keywords, types, schemas, tables, and columns completion suggestions."""

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

    def get_completions(self, prefix: str = "", context_text: str = "") -> list[CompletionItem]:
        """Return completion suggestions matching prefix and context."""
        prefix_clean = prefix.strip().lower()
        results: list[CompletionItem] = []

        # Check if dot context (e.g. "users.")
        dot_table_match = self._find_dot_table_context(context_text)
        if dot_table_match and self.schema_model:
            # Suggest columns for specified table
            cols = self._get_table_columns(dot_table_match)
            for c in cols:
                if not prefix_clean or c.lower().startswith(prefix_clean):
                    results.append(
                        CompletionItem(
                            text=c,
                            kind=CompletionKind.COLUMN,
                            detail=f"Column ({dot_table_match})",
                        )
                    )
            return results

        # 1. Database Schema objects (Schemas, Tables, Views, Columns)
        if self.schema_model:
            for schema in self.schema_model.schemas:
                if not prefix_clean or schema.name.lower().startswith(prefix_clean):
                    results.append(
                        CompletionItem(
                            text=schema.name,
                            kind=CompletionKind.SCHEMA,
                            detail="Schema",
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

                    # Add columns
                    for col in table.columns:
                        if not prefix_clean or col.name.lower().startswith(prefix_clean):
                            results.append(
                                CompletionItem(
                                    text=col.name,
                                    kind=CompletionKind.COLUMN,
                                    detail=f"Column ({table.name})",
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

        # 2. SQL Keywords
        for item in self._keyword_items:
            if not prefix_clean or item.text.lower().startswith(prefix_clean):
                results.append(item)

        # 3. Data Types
        for item in self._type_items:
            if not prefix_clean or item.text.lower().startswith(prefix_clean):
                results.append(item)

        # Deduplicate while preserving order
        seen = set()
        unique_results = []
        for item in results:
            key = (item.text, item.kind)
            if key not in seen:
                seen.add(key)
                unique_results.append(item)

        return unique_results

    def _find_dot_table_context(self, context_text: str) -> str | None:
        """Extract table name preceding a dot (e.g., 'SELECT users.' -> 'users')."""
        clean = context_text.strip()
        if "." in clean:
            parts = clean.split(".")
            if len(parts) >= 2:
                candidate = parts[-2].split()[-1]
                return candidate
        return None

    def _get_table_columns(self, table_name: str) -> list[str]:
        """Find column names for specified table name across schemas."""
        if not self.schema_model:
            return []

        for schema in self.schema_model.schemas:
            t = schema.get_table(table_name)
            if t:
                return [c.name for c in t.columns]
        return []
