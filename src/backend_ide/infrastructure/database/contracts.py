"""Database Abstraction Contracts and Protocols.

Defines the interfaces for Database Connections, Database Inspectors, and SQL Dialects.
"""

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from backend_ide.domain.schema.models import DatabaseSchema


class ConnectionConfig(BaseModel):
    """Configuration details for a database connection."""

    model_config = ConfigDict(frozen=True)

    name: str = "Default Connection"
    engine: str  # postgresql, mysql, sqlite, sqlserver
    host: str = "localhost"
    port: int = 5432
    database: str = "postgres"
    username: str = "postgres"
    password: str | None = None
    ssl_mode: str = "prefer"
    options: dict[str, Any] = {}


@runtime_checkable
class DatabaseConnection(Protocol):
    """Protocol for active database connections."""

    def connect(self) -> None:
        """Establish database connection."""
        ...

    def disconnect(self) -> None:
        """Close database connection."""
        ...

    def is_connected(self) -> bool:
        """Return True if connection is active."""
        ...

    def execute_query(
        self, query: str, params: tuple[Any, ...] | dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute a read-only query and return results as list of dicts."""
        ...

    def test_connection(self) -> bool:
        """Test if the connection can be successfully established."""
        ...


@runtime_checkable
class DatabaseInspector(Protocol):
    """Protocol for database schema inspectors."""

    def inspect_database(
        self, schema_names: list[str] | None = None, include_views: bool = True
    ) -> DatabaseSchema:
        """Inspect target database and return a Universal Schema Model."""
        ...


@runtime_checkable
class SQLDialect(Protocol):
    """Protocol for database SQL dialect specifics."""

    @property
    def name(self) -> str:
        """Dialect name."""
        ...

    def quote_identifier(self, identifier: str) -> str:
        """Quote a schema/table/column identifier for this dialect."""
        ...

    def get_keywords(self) -> set[str]:
        """Return set of reserved keywords for this dialect."""
        ...
