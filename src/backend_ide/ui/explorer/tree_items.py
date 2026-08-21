"""Tree Item definitions for Database Explorer."""

from enum import StrEnum
from typing import Any

import qtawesome as qta
from PySide6.QtWidgets import QTreeWidgetItem

from backend_ide.ui.theme import ThemeManager


class ExplorerNodeType(StrEnum):
    """Explorer tree node types."""

    CONNECTION = "connection"
    DATABASE = "database"
    SCHEMA = "schema"
    TABLE_GROUP = "table_group"
    TABLE = "table"
    VIEW_GROUP = "view_group"
    VIEW = "view"
    FUNCTION_GROUP = "function_group"
    FUNCTION = "function"
    PROCEDURE_GROUP = "procedure_group"
    PROCEDURE = "procedure"
    TRIGGER_GROUP = "trigger_group"
    TRIGGER = "trigger"
    COLUMN = "column"


class ExplorerTreeItem(QTreeWidgetItem):
    """Custom QTreeWidgetItem for Database Explorer with node metadata and lazy loading state."""

    def __init__(
        self,
        node_type: ExplorerNodeType,
        label: str,
        node_data: dict[str, Any] | None = None,
        parent: QTreeWidgetItem | None = None,
    ) -> None:
        super().__init__(parent, [label])
        self.node_type = node_type
        self.node_data = node_data or {}
        self.is_loaded = False
        self._setup_appearance()

    def _setup_appearance(self) -> None:
        """Assign compact library icons matching a professional database navigator."""
        icon_map = {
            ExplorerNodeType.CONNECTION: ("fa6s.plug", "accent"),
            ExplorerNodeType.DATABASE: ("fa6s.database", "accent"),
            ExplorerNodeType.SCHEMA: ("fa6s.folder", "text_secondary"),
            ExplorerNodeType.TABLE_GROUP: ("fa6s.folder", "text_secondary"),
            ExplorerNodeType.TABLE: ("fa6s.table-cells", "warning"),
            ExplorerNodeType.VIEW_GROUP: ("fa6s.folder", "text_secondary"),
            ExplorerNodeType.VIEW: ("fa6s.eye", "accent"),
            ExplorerNodeType.FUNCTION_GROUP: ("fa6s.folder", "text_secondary"),
            ExplorerNodeType.FUNCTION: ("fa6s.bolt", "warning"),
            ExplorerNodeType.PROCEDURE_GROUP: ("fa6s.folder", "text_secondary"),
            ExplorerNodeType.PROCEDURE: ("fa6s.gears", "text_secondary"),
            ExplorerNodeType.TRIGGER_GROUP: ("fa6s.folder", "text_secondary"),
            ExplorerNodeType.TRIGGER: ("fa6s.bell", "warning"),
            ExplorerNodeType.COLUMN: ("fa6s.grip-lines-vertical", "text_muted"),
        }
        icon_spec = icon_map.get(self.node_type)
        if icon_spec:
            icon_name, color_token = icon_spec
            color = getattr(ThemeManager.get_instance().current_palette, color_token)
            self.setIcon(0, qta.icon(icon_name, color=color))

    def refresh_appearance(self) -> None:
        """Repaint the node icon after an application theme change."""
        self._setup_appearance()
