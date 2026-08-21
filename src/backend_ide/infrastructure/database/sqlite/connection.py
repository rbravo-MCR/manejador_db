"""SQLite Database Connection Adapter using standard library sqlite3."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from backend_ide.infrastructure.database.contracts import ConnectionConfig
from backend_ide.infrastructure.logging import get_logger

logger = get_logger(__name__)


class SQLiteConnection:
    """Connection manager for SQLite databases using Python sqlite3."""

    def __init__(self, config: ConnectionConfig) -> None:
        self.config = config
        self._connection: sqlite3.Connection | None = None

    def _get_db_path(self) -> str:
        """Resolve database file path from config."""
        db_path = self.config.database
        if db_path == ":memory:":
            return ":memory:"
        return str(Path(db_path).expanduser().resolve())

    def connect(self) -> None:
        """Establish connection to SQLite."""
        if self.is_connected():
            return

        db_path = self._get_db_path()
        logger.info("Connecting to SQLite database", database=db_path)
        self._connection = sqlite3.connect(
            db_path,
            autocommit=True,
            timeout=8.0,
            check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        # Enable foreign keys enforcement
        self._connection.execute("PRAGMA foreign_keys = ON;")

    def disconnect(self) -> None:
        """Close connection to SQLite."""
        if self._connection is not None:
            logger.info("Closing SQLite connection", database=self.config.database)
            try:
                self._connection.close()
            except Exception as err:
                logger.warning("Error closing SQLite connection", error=str(err))
        self._connection = None

    def is_connected(self) -> bool:
        """Check if connection is open."""
        return self._connection is not None

    def execute_query(
        self, query: str, params: tuple[Any, ...] | dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute a SQL query and return results as list of dicts."""
        if not self.is_connected() or self._connection is None:
            self.connect()

        assert self._connection is not None
        cursor = self._connection.cursor()
        if params is not None:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        if cursor.description is None:
            return []

        rows = cursor.fetchall()
        return [dict(r) for r in rows]

    def test_connection(self) -> bool:
        """Test whether connection can be established."""
        try:
            self.connect()
            res = self.execute_query("SELECT 1 AS alive")
            return len(res) == 1 and res[0].get("alive") == 1
        except Exception as err:
            logger.warning("SQLite connection test failed", error=str(err))
            return False
        finally:
            self.disconnect()
