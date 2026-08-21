"""MySQL Connection Adapter using pymysql."""

from __future__ import annotations

from typing import Any

import pymysql
import pymysql.cursors

from backend_ide.infrastructure.database.contracts import ConnectionConfig
from backend_ide.infrastructure.logging import get_logger

logger = get_logger(__name__)


class MySQLConnection:
    """Connection manager for MySQL and MariaDB databases using pymysql."""

    def __init__(self, config: ConnectionConfig) -> None:
        self.config = config
        self._connection: pymysql.Connection | None = None

    def connect(self) -> None:
        """Establish connection to MySQL."""
        if self.is_connected():
            return

        logger.info(
            "Connecting to MySQL",
            host=self.config.host,
            port=self.config.port,
            database=self.config.database,
        )

        ssl_config = None
        if self.config.ssl_mode in ("require", "verify-ca", "verify-full"):
            ssl_config = {"check_hostname": False}

        self._connection = pymysql.connect(
            host=self.config.host,
            port=self.config.port or 3306,
            user=self.config.username,
            password=self.config.password or "",
            database=self.config.database,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
            connect_timeout=8,
            ssl=ssl_config,
            charset="utf8mb4",
        )

    def disconnect(self) -> None:
        """Close connection to MySQL."""
        if self._connection is not None:
            logger.info("Closing MySQL connection", database=self.config.database)
            try:
                self._connection.close()
            except Exception as err:
                logger.warning("Error closing MySQL connection", error=str(err))
        self._connection = None

    def is_connected(self) -> bool:
        """Check if connection is open."""
        if self._connection is None:
            return False
        try:
            self._connection.ping(reconnect=False)
            return True
        except Exception:
            return False

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
            logger.warning("MySQL connection test failed", error=str(err))
            return False
        finally:
            self.disconnect()
