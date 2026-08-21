"""Dialogs Layer for Backend Development IDE."""

from __future__ import annotations

from backend_ide.ui.dialogs.code_generation_dialog import CodeGenerationDialog
from backend_ide.ui.dialogs.connection_dialog import ConnectionDialog
from backend_ide.ui.dialogs.dbf_migration_dialog import DBFMigrationDialog

__all__ = [
    "CodeGenerationDialog",
    "ConnectionDialog",
    "DBFMigrationDialog",
]
