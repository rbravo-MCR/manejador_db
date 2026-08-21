"""Visual Foreign Key Relationship Connector with Column Anchors and Crow's Foot Cardinality."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsPathItem

if TYPE_CHECKING:
    from backend_ide.domain.schema.models import ForeignKey
    from backend_ide.ui.diagram.table_node import ERTableNode


class EREdgeStyle(StrEnum):
    """Line geometry rendering style."""

    BEZIER = "bezier"
    ORTHOGONAL = "orthogonal"


class ERRelationshipEdge(QGraphicsPathItem):
    """Connects source table column to target table primary key with Crow's Foot cardinality."""

    def __init__(
        self,
        fk: ForeignKey,
        source_node: ERTableNode,
        target_node: ERTableNode,
        style: EREdgeStyle = EREdgeStyle.BEZIER,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.fk = fk
        self.source_node = source_node
        self.target_node = target_node
        self.style = style
        self.is_hovered = False

        self._start_pt = QPointF(0, 0)
        self._end_pt = QPointF(0, 0)
        self._dir_src = 1.0
        self._dir_tgt = -1.0

        # Register with nodes
        self.source_node.edges.append(self)
        self.target_node.edges.append(self)

        self.setZValue(-1)  # Behind nodes
        self.setAcceptHoverEvents(True)
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)

        # Determine cardinality notation
        self._is_nullable = self._detect_if_nullable()
        self._src_cardinality_text = "0..N" if self._is_nullable else "1..N"
        self._tgt_cardinality_text = "1"

        # Build detailed tooltip
        col_mappings_str = ", ".join(
            f"{m.source_column} -> {m.target_column}" for m in fk.column_mappings
        )
        card_line = f"1 ({fk.target_table}) ─── {self._src_cardinality_text} ({fk.source_table})"
        tip = (
            "Relación: 1 a N (Muchos a Uno)\n"
            f"Cardinalidad: {card_line}\n"
            f"Clave Foránea: {fk.name or 'FK'}\n"
            f"Mapeo: {col_mappings_str}\n"
            f"ON UPDATE: {fk.on_update}\n"
            f"ON DELETE: {fk.on_delete}"
        )
        self.setToolTip(tip)

        self.update_path()

    def _detect_if_nullable(self) -> bool:
        """Check if source FK column is nullable in source table definition."""
        if not self.fk.column_mappings:
            return True
        col_name = self.fk.column_mappings[0].source_column
        for col in self.source_node.table.columns:
            if col.name == col_name:
                return col.is_nullable
        return False

    def set_edge_style(self, style: EREdgeStyle) -> None:
        """Update line drawing style and redraw path."""
        self.style = style
        self.update_path()

    def update_path(self) -> None:
        """Calculate and set connector line geometry from source anchor to target anchor."""
        if not self.source_node or not self.target_node:
            return

        src_col = self.fk.column_mappings[0].source_column if self.fk.column_mappings else ""
        tgt_col = self.fk.column_mappings[0].target_column if self.fk.column_mappings else ""

        src_rect = self.source_node.sceneBoundingRect()
        tgt_rect = self.target_node.sceneBoundingRect()

        src_y = self.source_node.get_column_anchor_y(src_col)
        tgt_y = self.target_node.get_column_anchor_y(tgt_col)

        # Decide whether to attach to left or right sides
        if src_rect.center().x() < tgt_rect.center().x():
            start_pt = QPointF(src_rect.right(), src_y)
            end_pt = QPointF(tgt_rect.left(), tgt_y)
            dir_src = 1.0
            dir_tgt = -1.0
        else:
            start_pt = QPointF(src_rect.left(), src_y)
            end_pt = QPointF(tgt_rect.right(), tgt_y)
            dir_src = -1.0
            dir_tgt = 1.0

        self._start_pt = start_pt
        self._end_pt = end_pt
        self._dir_src = dir_src
        self._dir_tgt = dir_tgt

        path = QPainterPath(start_pt)

        if self.style == EREdgeStyle.ORTHOGONAL:
            # Stepwise orthogonal routing
            mid_x = (start_pt.x() + end_pt.x()) / 2.0
            path.lineTo(mid_x, start_pt.y())
            path.lineTo(mid_x, end_pt.y())
            path.lineTo(end_pt.x(), end_pt.y())
        else:
            # Smooth cubic bezier
            dx = max(50.0, abs(end_pt.x() - start_pt.x()) * 0.5)
            ctrl1 = QPointF(start_pt.x() + (dir_src * dx), start_pt.y())
            ctrl2 = QPointF(end_pt.x() + (dir_tgt * dx), end_pt.y())
            path.cubicTo(ctrl1, ctrl2, end_pt)

        self.setPath(path)

    def hoverEnterEvent(self, event) -> None:
        """Enlarge and highlight on hover."""
        self.is_hovered = True
        self.setZValue(0)
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        """Reset appearance on hover leave."""
        self.is_hovered = False
        self.setZValue(-1)
        self.update()
        super().hoverLeaveEvent(event)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        """Paint anti-aliased path, Crow's foot symbols, and 1:N cardinality badges."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.isSelected() or self.is_hovered:
            color = QColor("#ea580c")  # Vibrant Orange
            line_width = 3.0
            badge_bg = QColor("#fff7ed")
            badge_border = QColor("#ea580c")
            text_color = QColor("#9a3412")
        else:
            color = QColor("#2563eb")  # Clear Royal Blue
            line_width = 2.0
            badge_bg = QColor("#ffffff")
            badge_border = QColor("#93c5fd")
            text_color = QColor("#1d4ed8")

        # 1. Main connector path
        pen = QPen(color, line_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self.path())

        # 2. Draw Crow's Foot Notation at Source (N side)
        # Three divergent prongs touching the source table anchor
        cf_len = 14.0
        cf_spread = 8.0
        s_pt = self._start_pt
        s_dir = self._dir_src

        prong_base = s_pt + QPointF(s_dir * cf_len, 0)
        prong_top = s_pt + QPointF(0, -cf_spread)
        prong_bot = s_pt + QPointF(0, cf_spread)

        cf_pen = QPen(color, max(1.5, line_width - 0.5))
        painter.setPen(cf_pen)
        painter.drawLine(prong_base, prong_top)
        painter.drawLine(prong_base, prong_bot)
        painter.drawLine(prong_base, s_pt)

        # 3. Draw Exactly-One Double Bar at Target (1 side)
        t_pt = self._end_pt
        t_dir = self._dir_tgt
        bar_len = 8.0

        bar1_x = t_pt.x() + (t_dir * 6.0)
        bar2_x = t_pt.x() + (t_dir * 12.0)

        painter.drawLine(
            QPointF(bar1_x, t_pt.y() - bar_len),
            QPointF(bar1_x, t_pt.y() + bar_len),
        )
        painter.drawLine(
            QPointF(bar2_x, t_pt.y() - bar_len),
            QPointF(bar2_x, t_pt.y() + bar_len),
        )

        # 4. Draw Clean Cardinality Badges (N and 1)
        font = QFont("Fira Code", 8, QFont.Weight.Bold)
        painter.setFont(font)

        # Source Badge (N side)
        src_badge_w = 26.0 if len(self._src_cardinality_text) > 1 else 18.0
        src_badge_h = 16.0
        src_bx = s_pt.x() + (s_dir * 24.0) - (src_badge_w / 2.0)
        src_by = s_pt.y() - 20.0
        src_rect = QRectF(src_bx, src_by, src_badge_w, src_badge_h)

        # Draw rounded badge background
        b_path = QPainterPath()
        b_path.addRoundedRect(src_rect, 4, 4)
        painter.fillPath(b_path, QBrush(badge_bg))
        painter.setPen(QPen(badge_border, 1.2))
        painter.drawPath(b_path)

        painter.setPen(text_color)
        painter.drawText(src_rect, Qt.AlignmentFlag.AlignCenter, self._src_cardinality_text)

        # Target Badge (1 side)
        tgt_badge_w = 18.0
        tgt_badge_h = 16.0
        tgt_bx = t_pt.x() + (t_dir * 24.0) - (tgt_badge_w / 2.0)
        tgt_by = t_pt.y() - 20.0
        tgt_rect = QRectF(tgt_bx, tgt_by, tgt_badge_w, tgt_badge_h)

        tb_path = QPainterPath()
        tb_path.addRoundedRect(tgt_rect, 4, 4)
        painter.fillPath(tb_path, QBrush(badge_bg))
        painter.setPen(QPen(badge_border, 1.2))
        painter.drawPath(tb_path)

        painter.setPen(text_color)
        painter.drawText(tgt_rect, Qt.AlignmentFlag.AlignCenter, self._tgt_cardinality_text)
