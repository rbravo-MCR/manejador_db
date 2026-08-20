"""Extensible built-in SQL snippets."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SQLSnippet:
    trigger: str
    body: str
    detail: str


class SnippetProvider:
    """Provide the small first-delivery snippet catalog."""

    _snippets = (
        SQLSnippet("sel", "SELECT *\nFROM table_name;", "SELECT query"),
        SQLSnippet(
            "ins",
            "INSERT INTO table_name (\n    column\n)\nVALUES (\n    value\n);",
            "INSERT statement",
        ),
        SQLSnippet(
            "upd", "UPDATE table_name\nSET column = value\nWHERE condition;", "UPDATE statement"
        ),
        SQLSnippet(
            "ct",
            "CREATE TABLE table_name (\n    id BIGINT PRIMARY KEY\n);",
            "CREATE TABLE statement",
        ),
    )

    def complete(self, prefix: str) -> tuple[SQLSnippet, ...]:
        prefix = prefix.lower()
        return tuple(item for item in self._snippets if item.trigger.startswith(prefix))
