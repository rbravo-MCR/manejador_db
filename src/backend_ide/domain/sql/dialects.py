"""SQL language providers isolated by database dialect."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from backend_ide.domain.sql.constants import SQL_KEYWORDS, SQL_TYPES


class SQLDialectProvider(Protocol):
    """Language facts required by completion and syntax tooling."""

    name: str

    def keywords(self) -> tuple[str, ...]: ...

    def functions(self) -> tuple[str, ...]: ...

    def data_types(self) -> tuple[str, ...]: ...


@dataclass(frozen=True, slots=True)
class BaseDialectProvider:
    """Shared implementation for static language catalogs."""

    name: str
    _functions: tuple[str, ...]
    _extra_keywords: tuple[str, ...] = ()
    _extra_types: tuple[str, ...] = ()

    def keywords(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys((*SQL_KEYWORDS, *self._extra_keywords)))

    def functions(self) -> tuple[str, ...]:
        return self._functions

    def data_types(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys((*SQL_TYPES, *self._extra_types)))


POSTGRESQL = BaseDialectProvider(
    "postgresql",
    (
        "COUNT",
        "SUM",
        "AVG",
        "MIN",
        "MAX",
        "COALESCE",
        "NULLIF",
        "DATE_TRUNC",
        "NOW",
        "CURRENT_DATE",
        "STRING_AGG",
        "JSON_AGG",
        "JSONB_BUILD_OBJECT",
    ),
    ("ILIKE", "RETURNING", "LATERAL"),
    ("SERIAL", "BIGSERIAL", "JSONB", "UUID"),
)
MYSQL = BaseDialectProvider(
    "mysql",
    (
        "COUNT",
        "SUM",
        "AVG",
        "MIN",
        "MAX",
        "IFNULL",
        "CONCAT",
        "NOW",
        "DATE_FORMAT",
        "GROUP_CONCAT",
        "JSON_OBJECT",
    ),
    ("REPLACE", "SHOW", "DESCRIBE"),
    ("TINYINT", "MEDIUMINT", "DATETIME", "ENUM"),
)
SQLITE = BaseDialectProvider(
    "sqlite",
    (
        "COUNT",
        "SUM",
        "AVG",
        "MIN",
        "MAX",
        "COALESCE",
        "IFNULL",
        "NULLIF",
        "DATE",
        "TIME",
        "DATETIME",
        "JULIANDAY",
        "STRFTIME",
        "JSON_OBJECT",
        "GROUP_CONCAT",
    ),
    ("PRAGMA", "GLOB"),
    ("BLOB",),
)
SQLSERVER = BaseDialectProvider(
    "sqlserver",
    (
        "COUNT",
        "SUM",
        "AVG",
        "MIN",
        "MAX",
        "ISNULL",
        "GETDATE",
        "DATEADD",
        "DATEDIFF",
        "STRING_AGG",
    ),
    ("TOP", "APPLY", "MERGE"),
    ("NVARCHAR", "DATETIME2", "UNIQUEIDENTIFIER"),
)

_PROVIDERS = {
    "postgres": POSTGRESQL,
    "postgresql": POSTGRESQL,
    "mysql": MYSQL,
    "mariadb": MYSQL,
    "sqlite": SQLITE,
    "sqlserver": SQLSERVER,
    "mssql": SQLSERVER,
}


def get_dialect_provider(engine_name: str | None) -> SQLDialectProvider:
    """Return a dialect provider, defaulting safely to PostgreSQL-like SQL."""
    return _PROVIDERS.get((engine_name or "").lower(), POSTGRESQL)
