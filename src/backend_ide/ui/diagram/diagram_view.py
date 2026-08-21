"""Interactive QGraphicsView with Smooth Zoom, Pan, and Minimap Overlay."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QGraphicsView

from backend_ide.ui.diagram.diagram_scene import ERDiagramScene
from backend_ide.ui.diagram.minimap import ERDiagramMinimap


class ERDiagramView(QGraphicsView):
    """Zoomable, pannable view for ER Diagram with embedded minimap."""

    zoom_changed = Signal(float)

    def __init__(self, scene: ERDiagramScene | None = None, parent=None) -> None:
        super().__init__(scene or ERDiagramScene(), parent)
        self._current_zoom = 1.0

        # View rendering options
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.SmartViewportUpdate)

        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setStyleSheet("border: none; background-color: #f8fafc;")

        # Floating Minimap
        self.minimap = ERDiagramMinimap(self, self)
        self.minimap.hide()

    def set_minimap_visible(self, visible: bool) -> None:
        """Toggle floating minimap visibility."""
        if visible:
            self.minimap.show()
            self._reposition_minimap()
            self.minimap.update()
        else:
            self.minimap.hide()

    def resizeEvent(self, event) -> None:
        """Keep minimap anchored in the bottom right on viewport resize."""
        super().resizeEvent(event)
        self._reposition_minimap()

    def _reposition_minimap(self) -> None:
        """Position minimap at bottom-right corner with 16px margin."""
        if self.minimap.isVisible():
            margin = 16
            x = self.width() - self.minimap.width() - margin
            y = self.height() - self.minimap.height() - margin
            self.minimap.move(max(0, x), max(0, y))

    def wheelEvent(self, event) -> None:
        """Zoom in or out centered at mouse cursor on wheel scroll."""
        zoom_factor = 1.15
        if event.angleDelta().y() > 0:
            if self._current_zoom < 4.0:
                self.scale(zoom_factor, zoom_factor)
                self._current_zoom *= zoom_factor
        else:
            if self._current_zoom > 0.05:
                self.scale(1.0 / zoom_factor, 1.0 / zoom_factor)
                self._current_zoom /= zoom_factor

        self.zoom_changed.emit(self._current_zoom)
        self.minimap.update()

    def zoom_in(self) -> None:
        """Increase canvas zoom level."""
        if self._current_zoom < 4.0:
            self.scale(1.2, 1.2)
            self._current_zoom *= 1.2
            self.zoom_changed.emit(self._current_zoom)
            self.minimap.update()

    def zoom_out(self) -> None:
        """Decrease canvas zoom level."""
        if self._current_zoom > 0.05:
            self.scale(1.0 / 1.2, 1.0 / 1.2)
            self._current_zoom /= 1.2
            self.zoom_changed.emit(self._current_zoom)
            self.minimap.update()

    def zoom_reset(self) -> None:
        """Reset zoom transformation to 100%."""
        self.resetTransform()
        self._current_zoom = 1.0
        self.zoom_changed.emit(self._current_zoom)
        self.minimap.update()

    def zoom_fit(self) -> None:
        """Fit all scene items within viewable canvas bounds."""
        if self.scene():
            items_rect = self.scene().itemsBoundingRect()
            if not items_rect.isEmpty():
                self.fitInView(
                    items_rect.adjusted(-60, -60, 60, 60),
                    Qt.AspectRatioMode.KeepAspectRatio,
                )
                self._current_zoom = self.transform().m11()
                self.zoom_changed.emit(self._current_zoom)
                self.minimap.update()
