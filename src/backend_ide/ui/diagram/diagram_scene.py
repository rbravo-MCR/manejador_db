"""Interactive QGraphicsScene for Entity-Relationship Diagrams with Clean Light Canvas."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPixmap
from PySide6.QtWidgets import QGraphicsScene

from backend_ide.ui.diagram.layout_engine import ERLayoutEngine
from backend_ide.ui.diagram.relationship_edge import EREdgeStyle, ERRelationshipEdge
from backend_ide.ui.diagram.table_node import (
    ERTableDisplayMode,
    ERTableNode,
)

if TYPE_CHECKING:
    from backend_ide.domain.schema.models import DatabaseSchema


class ERDiagramSceneSignals(QObject):
    """Signals forwarded from table nodes inside the scene."""

    view_data_requested = Signal(str)
    generate_joins_requested = Signal(str)
    generate_code_requested = Signal(str)
    table_focused = Signal(object)
    isolate_requested = Signal(str)
    isolate_extended_requested = Signal(str)


class ERDiagramScene(QGraphicsScene):
    """Scene managing ER table nodes, edges, tiled grid pattern, and display modes."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.nodes: dict[str, ERTableNode] = {}
        self.edges: list[ERRelationshipEdge] = []
        self.display_mode = ERTableDisplayMode.FULL
        self.edge_style = EREdgeStyle.BEZIER
        self.signals = ERDiagramSceneSignals()

        # Clean, bright light canvas with subtle gray grid pattern
        tile = QPixmap(24, 24)
        tile.fill(QColor("#f8fafc"))
        painter = QPainter(tile)
        painter.setPen(QColor("#cbd5e1"))
        painter.drawPoint(0, 0)
        painter.end()
        self.setBackgroundBrush(QBrush(tile))

    def load_schema(self, schema: DatabaseSchema) -> None:
        """Populate scene with table nodes and relationship edges from DatabaseSchema."""
        self.clear()
        self.nodes.clear()
        self.edges.clear()

        # 1. Create table nodes
        for s in schema.schemas:
            for table in s.tables:
                node = ERTableNode(table, display_mode=self.display_mode)
                node.signals.view_data_requested.connect(self.signals.view_data_requested.emit)
                node.signals.generate_joins_requested.connect(
                    self.signals.generate_joins_requested.emit
                )
                node.signals.generate_code_requested.connect(
                    self.signals.generate_code_requested.emit
                )
                node.signals.center_view_requested.connect(self.signals.table_focused.emit)
                node.signals.hide_requested.connect(self.hide_table)
                node.signals.isolate_requested.connect(self.isolate_table_network)
                node.signals.isolate_extended_requested.connect(
                    lambda name: self.isolate_table_network(name, depth=2)
                )

                self.addItem(node)
                self.nodes[table.name] = node

        # 2. Create relationship edges
        for s in schema.schemas:
            for table in s.tables:
                source_node = self.nodes.get(table.name)
                if not source_node:
                    continue

                for fk in table.foreign_keys:
                    target_node = self.nodes.get(fk.target_table)
                    if target_node:
                        edge = ERRelationshipEdge(
                            fk, source_node, target_node, style=self.edge_style
                        )
                        self.addItem(edge)
                        self.edges.append(edge)

        # 3. Default auto-layout
        self.auto_layout("hierarchical")

    def auto_layout(self, layout_type: str = "hierarchical") -> None:
        """Run chosen layout algorithm on current visible nodes."""
        node_list = [n for n in self.nodes.values() if n.isVisible()]
        if not node_list:
            return

        visible_edges = [
            e for e in self.edges if e.source_node.isVisible() and e.target_node.isVisible()
        ]

        if layout_type == "hierarchical":
            ERLayoutEngine.layout_hierarchical(node_list, visible_edges)
        elif layout_type == "force":
            ERLayoutEngine.layout_force_directed(node_list, visible_edges)
        elif layout_type == "circular":
            ERLayoutEngine.layout_circular(node_list)
        else:  # grid
            ERLayoutEngine.layout_grid(node_list)

        self.update_scene_rect()

    def set_display_mode(self, mode: ERTableDisplayMode) -> None:
        """Update display detail on all table nodes."""
        self.display_mode = mode
        for node in self.nodes.values():
            node.set_display_mode(mode)
        self.update_scene_rect()

    def set_edge_style(self, style: EREdgeStyle) -> None:
        """Update connector line geometry style."""
        self.edge_style = style
        for edge in self.edges:
            edge.set_edge_style(style)

    def hide_table(self, node: ERTableNode) -> None:
        """Hide table node and its attached relationship edges."""
        node.setVisible(False)
        for edge in node.edges:
            edge.setVisible(False)
        self.update_scene_rect()

    def show_all_tables(self) -> None:
        """Unhide all table nodes and edges."""
        for node in self.nodes.values():
            node.setVisible(True)
            node.setOpacity(1.0)
        for edge in self.edges:
            edge.setVisible(True)
        self.auto_layout("hierarchical")

    def set_visible_tables(self, table_names: set[str]) -> None:
        """Set visible only the specified table names and their interconnecting edges."""
        for name, node in self.nodes.items():
            is_vis = name in table_names
            node.setVisible(is_vis)
            node.setOpacity(1.0)

        for edge in self.edges:
            edge.setVisible(edge.source_node.isVisible() and edge.target_node.isVisible())

        self.auto_layout("hierarchical")

    def isolate_table_network(self, table_name: str, depth: int = 1) -> set[str]:
        """Isolate a specific table and all its connected relationships at given depth."""
        target_node = self.nodes.get(table_name)
        if not target_node:
            return set()

        current_layer = {table_name}
        all_connected = {table_name}

        for _ in range(depth):
            next_layer = set()
            for t_name in current_layer:
                node = self.nodes.get(t_name)
                if not node:
                    continue
                for edge in node.edges:
                    next_layer.add(edge.source_node.table.name)
                    next_layer.add(edge.target_node.table.name)
            new_additions = next_layer - all_connected
            all_connected.update(new_additions)
            current_layer = new_additions

        self.set_visible_tables(all_connected)
        return all_connected

    def isolate_table(self, table_name: str) -> None:
        """Highlight given table and direct relations while dimming others."""
        target_node = self.nodes.get(table_name)
        if not target_node:
            return

        neighbor_tables = {table_name}
        for edge in target_node.edges:
            neighbor_tables.add(edge.source_node.table.name)
            neighbor_tables.add(edge.target_node.table.name)

        for name, node in self.nodes.items():
            if name in neighbor_tables:
                node.setOpacity(1.0)
            else:
                node.setOpacity(0.2)

    def update_scene_rect(self) -> None:
        """Recalculate scene bounds with padding."""
        items_rect = self.itemsBoundingRect()
        if not items_rect.isEmpty():
            self.setSceneRect(items_rect.adjusted(-100, -100, 100, 100))
