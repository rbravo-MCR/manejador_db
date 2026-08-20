"""Thread-safe SQLite database adapter using the Python standard library."""

from __future__ import annotations

import sqlite3
from threading import RLock
from typing import Any

from backend_ide.infrastructure.database.contracts import ConnectionConfig


class SQLiteConnection:
    """Connection adapter compatible with background query and metadata workers."""

    def __init__(self, config: ConnectionConfig) -> None:
        self.config = config
        self.database_name = config.database
        self._connection: sqlite3.Connection | None = None
        self._lock = RLock()

    def connect(self) -> None:
        with self._lock:
            if self._connection is not None:
                return
            self._connection = sqlite3.connect(
                self.config.database,
                isolation_level=None,
                check_same_thread=False,
            )
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA foreign_keys = ON")

    def disconnect(self) -> None:
        with self._lock:
            if self._connection is not None:
                self._connection.close()
            self._connection = None

    def is_connected(self) -> bool:
        return self._connection is not None

    def execute_query(
        self,
        query: str,
        params: tuple[Any, ...] | dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        with self._lock:
            self.connect()
            assert self._connection is not None
            cursor = self._connection.execute(query, params or ())
            if cursor.description is None:
                return []
            return [dict(row) for row in cursor.fetchall()]

    def test_connection(self) -> bool:
        try:
            return self.execute_query("SELECT 1 AS alive") == [{"alive": 1}]
        except sqlite3.Error:
            return False
        finally:
            self.disconnect()
