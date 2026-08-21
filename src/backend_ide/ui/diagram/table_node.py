"""Visual Database Table Node for Entity-Relationship Diagrams with Clean Modern Light Styling."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QObject, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QGuiApplication,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject, QMenu

if TYPE_CHECKING:
    from backend_ide.domain.schema.models import Table
    from backend_ide.ui.diagram.relationship_edge import ERRelationshipEdge


class ERTableDisplayMode(StrEnum):
    """Display level of detail for table nodes."""

    FULL = "full"  # Columns with data types and icons
    COMPACT = "compact"  # Columns with icons only
    MINIMAL = "minimal"  # Header only


class ERTableNodeSignals(QObject):
    """Signals for table node user interactions."""

    view_data_requested = Signal(str)
    generate_joins_requested = Signal(str)
    generate_code_requested = Signal(str)
    center_view_requested = Signal(object)
    hide_requested = Signal(object)
    isolate_requested = Signal(str)
    isolate_extended_requested = Signal(str)


class ERTableNode(QGraphicsObject):
    """Visual table card in ER diagram with headers, columns, and precision anchor points."""

    def __init__(
        self,
        table: Table,
        display_mode: ERTableDisplayMode = ERTableDisplayMode.FULL,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.table = table
        self.display_mode = display_mode
        self.signals = ERTableNodeSignals()

        self.edges: list[ERRelationshipEdge] = []
        self.is_adjacent = False

        # Interaction flags
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

        # Geometry dimensions
        self.node_width = 240.0
        self.header_height = 36.0
        self.row_height = 24.0
        self.node_height = 100.0

        self.setToolTip(
            f"Tabla: {table.name}\n"
            f"Esquema: {table.schema_name or 'default'}\n"
            f"Columnas: {len(table.columns)}"
        )
        self._recalculate_dimensions()

    def set_display_mode(self, mode: ERTableDisplayMode) -> None:
        """Update node detail level and trigger layout adjustment."""
        self.prepareGeometryChange()
        self.display_mode = mode
        self._recalculate_dimensions()
        self.update()
        for edge in self.edges:
            edge.update_path()

    def _recalculate_dimensions(self) -> None:
        """Calculate card height and width based on display mode and column text lengths."""
        if self.display_mode == ERTableDisplayMode.MINIMAL:
            self.node_height = self.header_height
            self.node_width = max(180.0, len(self.table.name) * 11.0 + 50.0)
            return

        cols_count = len(self.table.columns) if self.table.columns else 1
        self.node_height = self.header_height + (cols_count * self.row_height) + 8.0

        if self.display_mode == ERTableDisplayMode.COMPACT:
            self.node_width = 190.0
        else:  # FULL
            max_col_len = max([len(c.name) for c in self.table.columns], default=10)
            self.node_width = max(240.0, min(360.0, 160.0 + (max_col_len * 8.0)))

    def boundingRect(self) -> QRectF:
        """Return boundary rectangle with border padding."""
        return QRectF(0, 0, self.node_width, self.node_height)

    def shape(self) -> QPainterPath:
        """Precise shape for selection and collision."""
        path = QPainterPath()
        path.addRoundedRect(self.boundingRect(), 8, 8)
        return path

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        """Handle position changes to dynamically update connected relationship edges."""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for edge in self.edges:
                edge.update_path()
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self._update_neighborhood_highlight(bool(value))
        return super().itemChange(change, value)

    def _update_neighborhood_highlight(self, selected: bool) -> None:
        """Highlight directly connected tables and relationships when selected."""
        for edge in self.edges:
            edge.setSelected(selected)
            neighbor = edge.target_node if edge.source_node == self else edge.source_node
            neighbor.is_adjacent = selected
            neighbor.update()

    def get_column_anchor_y(self, column_name: str) -> float:
        """Return vertical scene Y position for a column attachment."""
        if self.display_mode == ERTableDisplayMode.MINIMAL:
            return self.scenePos().y() + (self.header_height / 2.0)

        for idx, col in enumerate(self.table.columns):
            if col.name == column_name:
                return (
                    self.scenePos().y()
                    + self.header_height
                    + 4.0
                    + (idx * self.row_height)
                    + (self.row_height / 2.0)
                )

        return self.scenePos().y() + (self.node_height / 2.0)

    def mouseDoubleClickEvent(self, event) -> None:
        """Execute default action: query table preview data."""
        self.signals.view_data_requested.emit(self.table.name)
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event) -> None:
        """Display right-click context menu with actionable commands."""
        menu = QMenu()
        menu.setStyleSheet(
            "QMenu { background-color: #ffffff; color: #0f172a; "
            "border: 1px solid #cbd5e1; font-size: 12px; }\n"
            "QMenu::item:selected { background-color: #eff6ff; color: #2563eb; }"
        )

        act_view = menu.addAction(f"📊 Consultar Datos (SELECT * FROM {self.table.name})")
        act_joins = menu.addAction("🔗 Generar SELECT con JOINs")
        act_code = menu.addAction("⚡ Generar Código Backend...")
        menu.addSeparator()
        act_isolate = menu.addAction(f"🎯 Aislar '{self.table.name}' y sus relaciones")
        act_isolate_ext = menu.addAction(
            f"🌐 Aislar '{self.table.name}' y relaciones extendidas (Nivel 2)"
        )
        menu.addSeparator()
        act_center = menu.addAction("🎯 Centrar Vista en Tabla")
        act_copy = menu.addAction("📋 Copiar Nombre de Tabla")
        menu.addSeparator()
        act_hide = menu.addAction("👁️ Ocultar del Diagrama")

        action = menu.exec(event.screenPos())
        if action == act_view:
            self.signals.view_data_requested.emit(self.table.name)
        elif action == act_joins:
            self.signals.generate_joins_requested.emit(self.table.name)
        elif action == act_code:
            self.signals.generate_code_requested.emit(self.table.name)
        elif action == act_isolate:
            self.signals.isolate_requested.emit(self.table.name)
        elif action == act_isolate_ext:
            self.signals.isolate_extended_requested.emit(self.table.name)
        elif action == act_center:
            self.signals.center_view_requested.emit(self)
        elif action == act_copy:
            QGuiApplication.clipboard().setText(self.table.name)
        elif action == act_hide:
            self.signals.hide_requested.emit(self)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        """Draw clean, modern white table card, blue header, crisp dark text, and icons."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.boundingRect()
        if self.isSelected():
            border_color = QColor("#2563eb")  # Vibrant Blue outline
            border_width = 2.5
        elif self.is_adjacent:
            border_color = QColor("#16a34a")  # Green outline for connected neighbors
            border_width = 2.0
        else:
            border_color = QColor("#cbd5e1")  # Clean subtle light gray border
            border_width = 1.0

        bg_color = QColor("#ffffff")  # Crisp Pure White
        header_color = QColor("#2563eb") if not self.isSelected() else QColor("#1d4ed8")

        # 1. Main Card Body (White)
        card_path = QPainterPath()
        card_path.addRoundedRect(rect, 8, 8)
        painter.fillPath(card_path, QBrush(bg_color))
        painter.setPen(QPen(border_color, border_width))
        painter.drawPath(card_path)

        # 2. Header Area (Vibrant Royal Blue)
        header_rect = QRectF(rect.x(), rect.y(), rect.width(), self.header_height)
        header_path = QPainterPath()
        header_path.addRoundedRect(header_rect, 8, 8)

        painter.save()
        painter.setClipRect(header_rect)
        painter.fillPath(header_path, QBrush(header_color))
        painter.restore()

        # Header Title (Bold Crisp White)
        header_font = QFont("Fira Code", 10, QFont.Weight.Bold)
        painter.setFont(header_font)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(
            QRectF(10, 8, self.node_width - 20, 20),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            f"📋 {self.table.name}",
        )

        if self.display_mode == ERTableDisplayMode.MINIMAL:
            return

        # 3. Column Rows
        col_font = QFont("Fira Code", 9)
        painter.setFont(col_font)

        fk_columns = {m.source_column for fk in self.table.foreign_keys for m in fk.column_mappings}

        y_offset = self.header_height + 4.0
        if not self.table.columns:
            painter.setPen(QColor("#94a3b8"))
            painter.drawText(
                QRectF(10, y_offset, self.node_width - 20, self.row_height),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                "Sin columnas cargadas",
            )
            return

        for col in self.table.columns:
            is_pk = col.is_primary_key or (
                self.table.primary_key and col.name in self.table.primary_key.column_names
            )
            is_fk = col.name in fk_columns

            if is_pk:
                icon_str = "🔑"
                name_color = QColor("#b45309")  # Amber / Dark Gold
            elif is_fk:
                icon_str = "🔗"
                name_color = QColor("#0284c7")  # Cyan / Blue
            else:
                icon_str = "🔹"
                name_color = QColor("#1e293b")  # Dark Slate (High contrast)

            # Column Name
            name_width = (
                self.node_width - 20
                if self.display_mode == ERTableDisplayMode.COMPACT
                else (self.node_width - 95)
            )
            painter.setPen(name_color)
            painter.drawText(
                QRectF(10, y_offset, name_width, self.row_height),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                f"{icon_str} {col.name}",
            )

            # Native Data Type (Right-aligned muted gray)
            if self.display_mode == ERTableDisplayMode.FULL:
                type_font = QFont("Fira Code", 8)
                painter.setFont(type_font)
                painter.setPen(QColor("#64748b"))
                painter.drawText(
                    QRectF(
                        self.node_width - 95,
                        y_offset,
                        85,
                        self.row_height,
                    ),
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    col.native_type.lower(),
                )
                painter.setFont(col_font)

            y_offset += self.row_height
