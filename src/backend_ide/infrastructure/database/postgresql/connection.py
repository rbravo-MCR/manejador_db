"""PostgreSQL Connection Adapter using psycopg (v3)."""

from typing import Any

import psycopg
from psycopg.rows import dict_row

from backend_ide.infrastructure.database.contracts import ConnectionConfig
from backend_ide.infrastructure.logging import get_logger

logger = get_logger(__name__)


class PostgreSQLConnection:
    """Connection manager for PostgreSQL databases using psycopg v3."""

    def __init__(self, config: ConnectionConfig) -> None:
        self.config = config
        self._connection: psycopg.Connection[dict[str, Any]] | None = None

    def _build_dsn(self) -> str:
        """Build connection DSN string."""
        dsn_parts = [
            f"host={self.config.host}",
            f"port={self.config.port}",
            f"dbname={self.config.database}",
            f"user={self.config.username}",
        ]
        if self.config.password:
            dsn_parts.append(f"password={self.config.password}")
        if self.config.ssl_mode:
            dsn_parts.append(f"sslmode={self.config.ssl_mode}")
        return " ".join(dsn_parts)

    def connect(self) -> None:
        """Establish connection to PostgreSQL."""
        if self.is_connected():
            return

        dsn = self._build_dsn()
        logger.info(
            "Connecting to PostgreSQL",
            host=self.config.host,
            port=self.config.port,
            database=self.config.database,
        )
        self._connection = psycopg.connect(
            dsn,
            row_factory=dict_row,
            autocommit=True,
            connect_timeout=8,
        )

    def disconnect(self) -> None:
        """Close connection to PostgreSQL."""
        if self._connection and not self._connection.closed:
            logger.info("Closing PostgreSQL connection", database=self.config.database)
            self._connection.close()
        self._connection = None

    def is_connected(self) -> bool:
        """Check if connection is open and active."""
        return self._connection is not None and not self._connection.closed

    def execute_query(
        self, query: str, params: tuple[Any, ...] | dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute a SQL query and return results as list of dicts."""
        if not self.is_connected() or self._connection is None:
            self.connect()

        assert self._connection is not None
        with self._connection.cursor() as cursor:
            cursor.execute(query, params)
            if cursor.description is None:
                return []
            return list(cursor.fetchall())

    def test_connection(self) -> bool:
        """Test whether connection can be established."""
        try:
            self.connect()
            res = self.execute_query("SELECT 1 AS alive")
            return len(res) == 1 and res[0].get("alive") == 1
        except Exception as err:
            logger.warning("PostgreSQL connection test failed", error=str(err))
            return False
        finally:
            self.disconnect()
