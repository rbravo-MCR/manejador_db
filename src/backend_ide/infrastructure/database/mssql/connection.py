"""Microsoft SQL Server (T-SQL) Connection Adapter."""

from __future__ import annotations

from typing import Any

from backend_ide.infrastructure.database.contracts import ConnectionConfig
from backend_ide.infrastructure.logging import get_logger

logger = get_logger(__name__)


class MSSQLConnection:
    """Connection manager for Microsoft SQL Server databases."""

    def __init__(self, config: ConnectionConfig) -> None:
        self.config = config
        self._connection: Any = None

    def connect(self) -> None:
        """Establish connection to SQL Server via pymssql or pyodbc."""
        if self.is_connected():
            return

        logger.info(
            "Connecting to SQL Server",
            host=self.config.host,
            port=self.config.port or 1433,
            database=self.config.database,
        )

        try:
            import pymssql

            self._connection = pymssql.connect(
                server=self.config.host,
                port=self.config.port or 1433,
                user=self.config.username,
                password=self.config.password or "",
                database=self.config.database,
                as_dict=True,
                autocommit=True,
                login_timeout=8,
                timeout=30,
            )
            return
        except ImportError:
            pass

        try:
            import pyodbc

            driver = "{ODBC Driver 18 for SQL Server}"
            trust_cert = "yes" if self.config.ssl_mode in ("require", "allow") else "no"
            conn_str = (
                f"DRIVER={driver};SERVER={self.config.host},{self.config.port or 1433};"
                f"DATABASE={self.config.database};UID={self.config.username};PWD={self.config.password};"
                f"TrustServerCertificate={trust_cert};"
            )
            self._connection = pyodbc.connect(conn_str, timeout=8, autocommit=True)
            return
        except ImportError:
            pass

        raise RuntimeError(
            "No se encontró un driver compatible de SQL Server. "
            "Por favor instala 'pymssql' o 'pyodbc' para conectar a SQL Server."
        )

    def disconnect(self) -> None:
        """Close connection to SQL Server."""
        if self._connection is not None:
            logger.info("Closing SQL Server connection", database=self.config.database)
            try:
                self._connection.close()
            except Exception as err:
                logger.warning("Error closing SQL Server connection", error=str(err))
        self._connection = None

    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connection is not None

    def execute_query(self, query: str, params: tuple | None = None) -> list[dict[str, Any]]:
        """Execute query returning dictionaries."""
        if not self.is_connected():
            self.connect()

        with self._connection.cursor() as cursor:
            cursor.execute(query, params or ())
            if cursor.description:
                if hasattr(cursor, "fetchall"):
                    rows = cursor.fetchall()
                    if rows and isinstance(rows[0], dict):
                        return list(rows)
                    elif rows and isinstance(rows[0], (tuple, list)):
                        col_names = [d[0] for d in cursor.description]
                        return [dict(zip(col_names, row, strict=False)) for row in rows]
            return []

    def execute_non_query(self, query: str, params: tuple | None = None) -> int:
        """Execute DDL/DML statement."""
        if not self.is_connected():
            self.connect()

        with self._connection.cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.rowcount if hasattr(cursor, "rowcount") else 0
