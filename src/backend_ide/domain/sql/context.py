"""Lightweight, cursor-aware SQL context analysis for completion."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SQLContext:
    """Relevant facts about the SQL statement containing the cursor."""

    statement: str
    clause: str | None = None
    current_token: str = ""
    qualifier: str | None = None
    schema_qualifier: str | None = None
    aliases: dict[str, str] = field(default_factory=dict)
    tables: tuple[str, ...] = ()
    expects_relation: bool = False


class SQLContextAnalyzer:
    """Analyze common SQL completion contexts without depending on Qt or a database."""

    _identifier = r'(?:"[^"]+"|`[^`]+`|\[[^\]]+\]|[A-Za-z_][\w$]*)'
    _ignored_aliases = {
        "as",
        "cross",
        "full",
        "group",
        "having",
        "inner",
        "join",
        "left",
        "limit",
        "offset",
        "on",
        "order",
        "outer",
        "returning",
        "right",
        "set",
        "union",
        "values",
        "where",
    }
    _clause_patterns = (
        ("INSERT_INTO", r"\bINSERT\s+INTO\b"),
        ("DELETE_FROM", r"\bDELETE\s+FROM\b"),
        ("GROUP_BY", r"\bGROUP\s+BY\b"),
        ("ORDER_BY", r"\bORDER\s+BY\b"),
        ("UPDATE", r"\bUPDATE\b"),
        ("SELECT", r"\bSELECT\b"),
        ("FROM", r"\bFROM\b"),
        ("JOIN", r"\bJOIN\b"),
        ("ON", r"\bON\b"),
        ("WHERE", r"\bWHERE\b"),
        ("HAVING", r"\bHAVING\b"),
        ("SET", r"\bSET\b"),
        ("VALUES", r"\bVALUES\b"),
        ("RETURNING", r"\bRETURNING\b"),
    )

    def analyze(self, sql: str, cursor_position: int) -> SQLContext:
        """Return context for the statement at ``cursor_position``."""
        cursor_position = max(0, min(cursor_position, len(sql)))
        masked = self._mask_literals_and_comments(sql)
        statement_start = masked.rfind(";", 0, cursor_position) + 1
        statement_end = masked.find(";", cursor_position)
        if statement_end < 0:
            statement_end = len(sql)

        statement = sql[statement_start:statement_end]
        before_cursor = sql[statement_start:cursor_position]
        masked_statement = masked[statement_start:statement_end]
        masked_before = masked[statement_start:cursor_position]
        aliases, tables = self._find_sources(masked_statement)
        clause = self._find_clause(masked_before)

        insert_match = re.search(
            rf"\bINSERT\s+INTO\s+({self._identifier}(?:\s*\.\s*{self._identifier})?)\s*\([^)]*$",
            masked_before,
            re.IGNORECASE,
        )
        if insert_match:
            clause = "INSERT_COLUMNS"

        current_token = self._current_token(before_cursor)
        qualifier = self._qualifier_at_cursor(masked_before)
        expects_relation = clause in {"FROM", "JOIN", "UPDATE", "INSERT_INTO", "DELETE_FROM"}
        schema_qualifier = qualifier if qualifier and expects_relation else None

        return SQLContext(
            statement=statement,
            clause=clause,
            current_token=current_token,
            qualifier=qualifier,
            schema_qualifier=schema_qualifier,
            aliases=aliases,
            tables=tuple(tables),
            expects_relation=expects_relation,
        )

    def _find_sources(self, text: str) -> tuple[dict[str, str], list[str]]:
        aliases: dict[str, str] = {}
        tables: list[str] = []
        relation_pattern = re.compile(
            rf"\b(?:FROM|JOIN)\s+({self._identifier}(?:\s*\.\s*{self._identifier})?)"
            rf"(?:\s+(?:AS\s+)?({self._identifier}))?",
            re.IGNORECASE,
        )
        for table_reference, alias in relation_pattern.findall(text):
            normalized = self._normalize_identifier(table_reference)
            self._append_unique(tables, normalized)
            clean_alias = self._normalize_identifier(alias) if alias else ""
            if clean_alias and clean_alias.lower() not in self._ignored_aliases:
                aliases[clean_alias] = normalized

        target_pattern = re.compile(
            rf"\b(?:UPDATE|INSERT\s+INTO|DELETE\s+FROM)\s+"
            rf"({self._identifier}(?:\s*\.\s*{self._identifier})?)",
            re.IGNORECASE,
        )
        for table_reference in target_pattern.findall(text):
            self._append_unique(tables, self._normalize_identifier(table_reference))
        return aliases, tables

    def _find_clause(self, text: str) -> str | None:
        matches: list[tuple[int, str]] = []
        for name, pattern in self._clause_patterns:
            matches.extend((match.start(), name) for match in re.finditer(pattern, text, re.I))
        return max(matches)[1] if matches else None

    @staticmethod
    def _current_token(text: str) -> str:
        match = re.search(r"([A-Za-z_][\w$]*)$", text)
        return match.group(1) if match else ""

    @staticmethod
    def _qualifier_at_cursor(text: str) -> str | None:
        match = re.search(r"([A-Za-z_][\w$]*)\s*\.\s*(?:[A-Za-z_][\w$]*)?$", text)
        return match.group(1) if match else None

    @staticmethod
    def _append_unique(items: list[str], item: str) -> None:
        if item and item not in items:
            items.append(item)

    @staticmethod
    def _normalize_identifier(value: str) -> str:
        return re.sub(r"\s*\.\s*", ".", value).replace('"', "").replace("`", "").strip("[]")

    @staticmethod
    def _mask_literals_and_comments(sql: str) -> str:
        """Replace comments and string literals with spaces while preserving offsets."""
        chars = list(sql)
        index = 0
        while index < len(chars):
            if sql.startswith("--", index):
                end = sql.find("\n", index)
                end = len(sql) if end < 0 else end
                chars[index:end] = " " * (end - index)
                index = end
                continue
            if sql.startswith("/*", index):
                end = sql.find("*/", index + 2)
                end = len(sql) if end < 0 else end + 2
                chars[index:end] = " " * (end - index)
                index = end
                continue
            if sql[index] == "'":
                end = index + 1
                while end < len(sql):
                    if sql[end] == "'" and end + 1 < len(sql) and sql[end + 1] == "'":
                        end += 2
                        continue
                    if sql[end] == "'":
                        end += 1
                        break
                    end += 1
                chars[index:end] = " " * (end - index)
                index = end
                continue
            index += 1
        return "".join(chars)
