"""Lightweight, Modern Light Minimap Widget for ER Diagrams."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

if TYPE_CHECKING:
    from backend_ide.ui.diagram.diagram_view import ERDiagramView


class ERDiagramMinimap(QWidget):
    """Floating thumbnail minimap with draggable viewport frustum."""

    def __init__(self, main_view: ERDiagramView, parent=None) -> None:
        super().__init__(parent)
        self.main_view = main_view
        self._is_dragging = False

        self.setFixedSize(190, 130)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        # Connect scrollbars to repaint minimap
        self.main_view.horizontalScrollBar().valueChanged.connect(self.update)
        self.main_view.verticalScrollBar().valueChanged.connect(self.update)

    def paintEvent(self, event) -> None:
        """Paint mini preview of the scene nodes and the active camera viewport."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Background (Clean White with subtle border)
        bg_path = QPainterPath()
        bg_path.addRoundedRect(QRectF(0, 0, self.width(), self.height()), 6, 6)
        painter.fillPath(bg_path, QBrush(QColor(255, 255, 255, 235)))
        painter.setPen(QPen(QColor("#cbd5e1"), 1.5))
        painter.drawPath(bg_path)

        scene = self.main_view.scene()
        if not scene:
            return

        items_rect = scene.itemsBoundingRect()
        if items_rect.isEmpty():
            return

        # 2. Scale factor mapping scene to minimap interior
        margin = 8.0
        avail_w = self.width() - (margin * 2)
        avail_h = self.height() - (margin * 2)

        scale_x = avail_w / max(1.0, items_rect.width())
        scale_y = avail_h / max(1.0, items_rect.height())
        scale = min(scale_x, scale_y)

        offset_x = margin + (avail_w - (items_rect.width() * scale)) / 2.0
        offset_y = margin + (avail_h - (items_rect.height() * scale)) / 2.0

        def scene_to_mini(x: float, y: float) -> QPointF:
            return QPointF(
                offset_x + ((x - items_rect.left()) * scale),
                offset_y + ((y - items_rect.top()) * scale),
            )

        # 3. Draw miniature table cards
        painter.setPen(Qt.PenStyle.NoPen)
        for node in getattr(scene, "nodes", {}).values():
            if not node.isVisible():
                continue
            pos = node.pos()
            mini_top_left = scene_to_mini(pos.x(), pos.y())
            mini_w = max(4.0, node.node_width * scale)
            mini_h = max(3.0, node.node_height * scale)

            color = QColor("#2563eb") if node.isSelected() else QColor("#94a3b8")
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(
                QRectF(mini_top_left.x(), mini_top_left.y(), mini_w, mini_h), 1, 1
            )

        # 4. Draw camera frustum rectangle
        visible_tl = self.main_view.mapToScene(0, 0)
        visible_br = self.main_view.mapToScene(
            self.main_view.viewport().width(), self.main_view.viewport().height()
        )

        m_tl = scene_to_mini(visible_tl.x(), visible_tl.y())
        m_br = scene_to_mini(visible_br.x(), visible_br.y())

        frustum_rect = QRectF(m_tl, m_br).intersected(QRectF(0, 0, self.width(), self.height()))

        painter.setPen(QPen(QColor("#2563eb"), 1.5))
        painter.setBrush(QBrush(QColor(37, 99, 235, 45)))
        painter.drawRect(frustum_rect)

    def _mini_to_scene(self, pt: QPointF) -> QPointF:
        """Convert minimap coordinates back to scene coordinates."""
        scene = self.main_view.scene()
        if not scene:
            return QPointF(0, 0)
        items_rect = scene.itemsBoundingRect()
        if items_rect.isEmpty():
            return QPointF(0, 0)

        margin = 8.0
        avail_w = self.width() - (margin * 2)
        avail_h = self.height() - (margin * 2)
        scale = min(
            avail_w / max(1.0, items_rect.width()),
            avail_h / max(1.0, items_rect.height()),
        )
        offset_x = margin + (avail_w - (items_rect.width() * scale)) / 2.0
        offset_y = margin + (avail_h - (items_rect.height() * scale)) / 2.0

        scene_x = items_rect.left() + ((pt.x() - offset_x) / max(0.0001, scale))
        scene_y = items_rect.top() + ((pt.y() - offset_y) / max(0.0001, scale))
        return QPointF(scene_x, scene_y)

    def mousePressEvent(self, event) -> None:
        """Center view camera on clicked position."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            scene_pos = self._mini_to_scene(event.position())
            self.main_view.centerOn(scene_pos)
            self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        """Pan view on mouse drag."""
        if self._is_dragging:
            scene_pos = self._mini_to_scene(event.position())
            self.main_view.centerOn(scene_pos)
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        """End pan drag."""
        self._is_dragging = False
        super().mouseReleaseEvent(event)
