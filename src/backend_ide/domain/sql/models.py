"""Domain models for SQL Query Execution, Results, and Export."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class QueryRequest(BaseModel):
    """Encapsulates a database query execution request."""

    model_config = ConfigDict(frozen=True)

    sql: str
    params: tuple[Any, ...] | dict[str, Any] | None = None
    connection_id: str | None = None
    timeout_seconds: int = 30
    limit: int | None = 1000
    offset: int = 0


class ColumnMetadata(BaseModel):
    """Column header metadata in query results."""

    model_config = ConfigDict(frozen=True)

    name: str
    data_type: str = "VARCHAR"


class QueryResult(BaseModel):
    """Encapsulates query execution output, results, and timing metrics."""

    model_config = ConfigDict(frozen=True)

    columns: list[ColumnMetadata] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    execution_time_ms: float = 0.0
    rows_affected: int = 0
    has_error: bool = False
    error_message: str | None = None

    @property
    def row_count(self) -> int:
        """Return number of returned rows."""
        return len(self.rows)
