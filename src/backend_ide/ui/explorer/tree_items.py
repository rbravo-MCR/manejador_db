"""Tree Item definitions for Database Explorer."""

from enum import StrEnum
from typing import Any

from PySide6.QtWidgets import QTreeWidgetItem


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
        """Assign icons or prefixes based on node type."""
        label = self.text(0)
        prefix_map = {
            ExplorerNodeType.CONNECTION: "🔌 ",
            ExplorerNodeType.DATABASE: "🗄️ ",
            ExplorerNodeType.SCHEMA: "📦 ",
            ExplorerNodeType.TABLE_GROUP: "📁 Tables",
            ExplorerNodeType.TABLE: "📋 ",
            ExplorerNodeType.VIEW_GROUP: "📁 Views",
            ExplorerNodeType.VIEW: "👁️ ",
            ExplorerNodeType.FUNCTION_GROUP: "📁 Functions",
            ExplorerNodeType.FUNCTION: "⚡ ",
            ExplorerNodeType.PROCEDURE_GROUP: "📁 Procedures",
            ExplorerNodeType.PROCEDURE: "⚙️ ",
            ExplorerNodeType.TRIGGER_GROUP: "📁 Triggers",
            ExplorerNodeType.TRIGGER: "🔔 ",
        }

        prefix = prefix_map.get(self.node_type)
        if prefix and not label.startswith(prefix):
            if self.node_type in (
                ExplorerNodeType.TABLE_GROUP,
                ExplorerNodeType.VIEW_GROUP,
                ExplorerNodeType.FUNCTION_GROUP,
                ExplorerNodeType.PROCEDURE_GROUP,
                ExplorerNodeType.TRIGGER_GROUP,
            ):
                self.setText(0, prefix)
            else:
                self.setText(0, f"{prefix}{label}")
