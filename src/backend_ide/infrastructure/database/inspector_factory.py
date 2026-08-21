"""Polymorphic Database Inspector Factory for Multi-Engine Architecture."""

from __future__ import annotations

from backend_ide.infrastructure.database.contracts import (
    DatabaseConnection,
    DatabaseInspector,
)
from backend_ide.infrastructure.database.postgresql.inspector import PostgreSQLInspector
from backend_ide.infrastructure.database.sqlite.inspector import SQLiteInspector


class InspectorFactory:
    """Creates the appropriate DatabaseInspector instance for a given DatabaseConnection."""

    @staticmethod
    def create_inspector(connection: DatabaseConnection) -> DatabaseInspector:
        """Instantiate dialect-specific inspector matching connection config engine."""
        engine = getattr(connection.config, "engine", "postgresql").lower()
        if engine == "sqlite":
            return SQLiteInspector(connection)
        elif engine in ("mysql", "mariadb"):
            try:
                from backend_ide.infrastructure.database.mysql.inspector import (
                    MySQLInspector,
                )

                return MySQLInspector(connection)
            except ImportError:
                return PostgreSQLInspector(connection)
        elif engine in ("mssql", "sqlserver", "sql_server"):
            try:
                from backend_ide.infrastructure.database.mssql.inspector import (
                    MSSQLInspector,
                )

                return MSSQLInspector(connection)
            except ImportError:
                return PostgreSQLInspector(connection)
        else:
            return PostgreSQLInspector(connection)
