"""SQLite metadata adapter."""

from backend_ide.infrastructure.database.sqlite.connection import SQLiteConnection
from backend_ide.infrastructure.database.sqlite.metadata import SQLiteMetadataProvider

__all__ = ["SQLiteConnection", "SQLiteMetadataProvider"]
