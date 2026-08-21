"""Visual Entity-Relationship Diagram Workspace Widget with Clean Modern Light Design."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import qtawesome as qta
from PySide6.QtCore import QRectF, Signal
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from backend_ide.domain.diagram.exporters import (
    ERDbmLExporter,
    ERMermaidExporter,
    ERPlantUMLExporter,
)
from backend_ide.ui.diagram.diagram_scene import ERDiagramScene
from backend_ide.ui.diagram.diagram_view import ERDiagramView
from backend_ide.ui.diagram.relationship_edge import EREdgeStyle
from backend_ide.ui.diagram.table_node import ERTableDisplayMode
from backend_ide.ui.dialogs.table_selection_dialog import TableSelectionDialog

if TYPE_CHECKING:
    from backend_ide.domain.schema.models import DatabaseSchema


class ERDiagramWidget(QWidget):
    """Complete visual Entity-Relationship diagram surface with rich interactive tools."""

    view_data_requested = Signal(str)
    generate_joins_requested = Signal(str)
    generate_code_requested = Signal(str)

    def __init__(self, schema: DatabaseSchema | None = None, parent=None) -> None:
        super().__init__(parent)
        self.schema = schema
        self.scene = ERDiagramScene(self)
        self.view = ERDiagramView(self.scene, self)

        # Forward scene signals
        self.scene.signals.view_data_requested.connect(self.view_data_requested.emit)
        self.scene.signals.generate_joins_requested.connect(self.generate_joins_requested.emit)
        self.scene.signals.generate_code_requested.connect(self.generate_code_requested.emit)
        self.scene.signals.table_focused.connect(self._on_table_focused)
        self.scene.signals.isolate_requested.connect(self._on_isolated_from_scene)
        self.scene.signals.isolate_extended_requested.connect(self._on_isolated_from_scene)

        self._setup_ui()
        if schema:
            self.load_schema(schema)

    def _setup_ui(self) -> None:
        """Construct toolbar, search filter, layout choices, and graphics canvas."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Clean, modern light toolbar
        toolbar = QWidget()
        toolbar.setStyleSheet(
            "background-color: #ffffff; border-bottom: 1px solid #e2e8f0; padding: 4px;"
        )
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(8, 4, 8, 4)
        tb_layout.setSpacing(6)

        # 1. Search Box
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Filtrar tablas o columnas…")
        self.txt_search.setMaximumWidth(190)
        self.txt_search.setFixedHeight(28)
        self.txt_search.setStyleSheet(
            "QLineEdit { background-color: #f8fafc; border: 1px solid #cbd5e1; "
            "border-radius: 4px; padding: 2px 6px; color: #0f172a; }\n"
            "QLineEdit:focus { border: 1px solid #2563eb; }"
        )
        self.txt_search.textChanged.connect(self._on_search_changed)

        btn_style = (
            "QPushButton { background-color: #f8fafc; border: 1px solid #cbd5e1; "
            "border-radius: 4px; padding: 4px 9px; color: #334155; font-size: 12px; "
            "font-weight: 500; }\n"
            "QPushButton:hover { background-color: #f1f5f9; border-color: #94a3b8; "
            "color: #0f172a; }\n"
            "QPushButton:pressed { background-color: #e2e8f0; }\n"
            "QPushButton:checked { background-color: #eff6ff; border-color: #2563eb; "
            "color: #2563eb; }"
        )

        combo_style = (
            "QComboBox { background-color: #f8fafc; border: 1px solid #cbd5e1; "
            "border-radius: 4px; padding: 2px 8px; color: #0f172a; font-size: 12px; }\n"
            "QComboBox:hover { border: 1px solid #94a3b8; }\n"
            "QComboBox::drop-down { border: none; }\n"
            "QComboBox QAbstractItemView { background-color: #ffffff; color: #0f172a; "
            "selection-background-color: #eff6ff; selection-color: #2563eb; }"
        )

        # 2. Select Tables Dialog Button
        self.btn_select_tables = QPushButton("📋 Seleccionar Tablas…")
        self.btn_select_tables.setIcon(qta.icon("fa6s.list-check", color="#2563eb"))
        self.btn_select_tables.setStyleSheet(
            "QPushButton { background-color: #eff6ff; border: 1px solid #bfdbfe; "
            "border-radius: 4px; padding: 4px 9px; color: #1d4ed8; font-size: 12px; "
            "font-weight: 600; }\n"
            "QPushButton:hover { background-color: #dbeafe; border-color: #3b82f6; }\n"
        )
        self.btn_select_tables.setToolTip(
            "Seleccionar qué tablas y relaciones visualizar en el diagrama"
        )
        self.btn_select_tables.clicked.connect(self._open_table_selection_dialog)

        # 3. Filter only tables with relationships
        self.chk_fks_only = QCheckBox("🔗 Solo con relaciones")
        self.chk_fks_only.setStyleSheet(
            "QCheckBox { color: #334155; font-size: 12px; font-weight: 500; }"
        )
        self.chk_fks_only.setToolTip(
            "Ocultar tablas aisladas sin claves foráneas para esquemas grandes"
        )
        self.chk_fks_only.toggled.connect(self._on_fks_only_toggled)

        # 4. Show all tables button
        self.btn_show_all = QPushButton("👁️ Mostrar Todas")
        self.btn_show_all.setStyleSheet(btn_style)
        self.btn_show_all.setToolTip(
            "Restablecer el diagrama y mostrar todas las tablas del esquema"
        )
        self.btn_show_all.clicked.connect(self._on_show_all_clicked)

        # 5. Infer Virtual Foreign Keys button
        self.btn_infer_fks = QPushButton("✨ Inferir Relaciones")
        self.btn_infer_fks.setStyleSheet(btn_style)
        self.btn_infer_fks.setToolTip(
            "Descubrir relaciones implícitas basadas en nombres de columnas"
        )
        self.btn_infer_fks.clicked.connect(self._on_infer_fks_clicked)

        # 6. Layout Selector
        self.cmb_layout = QComboBox()
        self.cmb_layout.setFixedHeight(28)
        self.cmb_layout.setStyleSheet(combo_style)
        self.cmb_layout.addItem("🌲 Jerárquico (Árbol FK)", "hierarchical")
        self.cmb_layout.addItem("▦ Cuadrícula (Grid)", "grid")
        self.cmb_layout.addItem("⚛️ Orgánico (Fuerzas)", "force")
        self.cmb_layout.addItem("⚪ Circular", "circular")
        self.cmb_layout.currentIndexChanged.connect(self._on_layout_changed)

        # 7. Detail Mode Selector
        self.cmb_detail = QComboBox()
        self.cmb_detail.setFixedHeight(28)
        self.cmb_detail.setStyleSheet(combo_style)
        self.cmb_detail.addItem("📋 Detallado", ERTableDisplayMode.FULL)
        self.cmb_detail.addItem("🔹 Compacto", ERTableDisplayMode.COMPACT)
        self.cmb_detail.addItem("🏷️ Solo Nombres", ERTableDisplayMode.MINIMAL)
        self.cmb_detail.currentIndexChanged.connect(self._on_detail_mode_changed)

        # 8. Connector Line Style
        self.cmb_style = QComboBox()
        self.cmb_style.setFixedHeight(28)
        self.cmb_style.setStyleSheet(combo_style)
        self.cmb_style.addItem("〰️ Curva Bézier", EREdgeStyle.BEZIER)
        self.cmb_style.addItem("📐 Ortogonal", EREdgeStyle.ORTHOGONAL)
        self.cmb_style.currentIndexChanged.connect(self._on_edge_style_changed)

        # 9. Zoom & View Controls
        self.btn_zoom_in = QPushButton()
        self.btn_zoom_in.setIcon(qta.icon("fa6s.magnifying-glass-plus", color="#475569"))
        self.btn_zoom_in.setStyleSheet(btn_style)
        self.btn_zoom_in.setToolTip("Acercar Zoom")
        self.btn_zoom_in.clicked.connect(self.view.zoom_in)

        self.btn_zoom_out = QPushButton()
        self.btn_zoom_out.setIcon(qta.icon("fa6s.magnifying-glass-minus", color="#475569"))
        self.btn_zoom_out.setStyleSheet(btn_style)
        self.btn_zoom_out.setToolTip("Alejar Zoom")
        self.btn_zoom_out.clicked.connect(self.view.zoom_out)

        self.btn_zoom_fit = QPushButton("Ajustar")
        self.btn_zoom_fit.setIcon(qta.icon("fa6s.expand", color="#475569"))
        self.btn_zoom_fit.setStyleSheet(btn_style)
        self.btn_zoom_fit.setToolTip("Ajustar vista a todas las tablas")
        self.btn_zoom_fit.clicked.connect(self.view.zoom_fit)

        self.btn_zoom_reset = QPushButton("100%")
        self.btn_zoom_reset.setStyleSheet(btn_style)
        self.btn_zoom_reset.setToolTip("Restablecer Zoom a 100%")
        self.btn_zoom_reset.clicked.connect(self.view.zoom_reset)

        # 10. Minimap Toggle
        self.btn_minimap = QPushButton()
        self.btn_minimap.setIcon(qta.icon("fa6s.map", color="#475569"))
        self.btn_minimap.setStyleSheet(btn_style)
        self.btn_minimap.setCheckable(True)
        self.btn_minimap.setToolTip("Mostrar/Ocultar Minimapa de navegación")
        self.btn_minimap.toggled.connect(self.view.set_minimap_visible)

        # 11. Export Dropdown Menu
        self.btn_export = QPushButton("Exportar ▾")
        self.btn_export.setIcon(qta.icon("fa6s.share-from-square", color="#475569"))
        self.btn_export.setStyleSheet(btn_style)
        self.btn_export.clicked.connect(self._show_export_menu)

        self.lbl_stats = QLabel("0 tablas")
        self.lbl_stats.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 500;")

        tb_layout.addWidget(self.txt_search)
        tb_layout.addWidget(self.btn_select_tables)
        tb_layout.addWidget(self.chk_fks_only)
        tb_layout.addWidget(self.btn_show_all)
        tb_layout.addWidget(self.btn_infer_fks)
        tb_layout.addWidget(self.cmb_layout)
        tb_layout.addWidget(self.cmb_detail)
        tb_layout.addWidget(self.cmb_style)
        tb_layout.addWidget(self.btn_zoom_in)
        tb_layout.addWidget(self.btn_zoom_out)
        tb_layout.addWidget(self.btn_zoom_fit)
        tb_layout.addWidget(self.btn_zoom_reset)
        tb_layout.addWidget(self.btn_minimap)
        tb_layout.addStretch()
        tb_layout.addWidget(self.lbl_stats)
        tb_layout.addWidget(self.btn_export)

        layout.addWidget(toolbar)
        layout.addWidget(self.view)

    def load_schema(self, schema: DatabaseSchema) -> None:
        """Load and display DatabaseSchema tables and foreign key relationships."""
        self.schema = schema
        self.scene.load_schema(schema)

        total_tables = sum(len(s.tables) for s in schema.schemas)
        total_fks = sum(len(t.foreign_keys) for s in schema.schemas for t in s.tables)
        self._update_stats_label()

        # For large databases (> 60 tables), enable FKs only filter by default for responsiveness
        if total_tables > 60 and total_fks > 0:
            self.chk_fks_only.blockSignals(True)
            self.chk_fks_only.setChecked(True)
            self.chk_fks_only.blockSignals(False)
            self._apply_fks_only_filter(True)
        else:
            self.view.zoom_fit()

    def _open_table_selection_dialog(self) -> None:
        """Open interactive dialog to pick which tables to view in the ER diagram."""
        if not self.schema:
            return

        visible_tables = {name for name, node in self.scene.nodes.items() if node.isVisible()}
        dialog = TableSelectionDialog(self.schema, selected_tables=visible_tables, parent=self)
        if dialog.exec() == TableSelectionDialog.DialogCode.Accepted:
            chosen = dialog.get_selected_table_names()
            self.scene.set_visible_tables(chosen)
            self._update_stats_label()
            self.view.zoom_fit()

    def _on_show_all_clicked(self) -> None:
        """Unhide all tables and reset filters."""
        self.chk_fks_only.blockSignals(True)
        self.chk_fks_only.setChecked(False)
        self.chk_fks_only.blockSignals(False)
        self.txt_search.clear()
        self.scene.show_all_tables()
        self._update_stats_label()
        self.view.zoom_fit()

    def _on_infer_fks_clicked(self) -> None:
        """Discover implicit relationships by convention and prompt to apply them."""
        if not self.schema:
            return

        from backend_ide.domain.schema.inferred_relations import (
            InferredRelationsEngine,
        )

        discovered = InferredRelationsEngine.discover_relations(self.schema)
        if not discovered:
            QMessageBox.information(
                self,
                "Inferir Relaciones",
                "No se encontraron relaciones implícitas adicionales por convención de nombres.",
            )
            return

        reply = QMessageBox.question(
            self,
            "Relaciones Implícitas Encontradas",
            f"Se descubrieron {len(discovered)} relaciones implícitas entre tablas.\n\n"
            "¿Deseas agregarlas como claves foráneas virtuales al diagrama ER?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.schema = InferredRelationsEngine.apply_to_schema(self.schema)
            self.load_schema(self.schema)
            QMessageBox.information(
                self,
                "Relaciones Aplicadas",
                f"Se han incorporado {len(discovered)} relaciones virtuales al diagrama.",
            )

    def _on_isolated_from_scene(self, table_name: str) -> None:
        """Handle isolation triggered from table context menu."""
        self._update_stats_label()
        self.view.zoom_fit()

    def _update_stats_label(self) -> None:
        """Update visible and total tables counters in toolbar."""
        total_tables = len(self.scene.nodes)
        visible_tables = sum(1 for n in self.scene.nodes.values() if n.isVisible())
        visible_fks = sum(1 for e in self.scene.edges if e.isVisible())
        if visible_tables < total_tables:
            self.lbl_stats.setText(
                f"Mostrando {visible_tables} de {total_tables} tablas ({visible_fks} relaciones)"
            )
        else:
            self.lbl_stats.setText(f"{total_tables} tablas, {visible_fks} relaciones")

    def _on_fks_only_toggled(self, checked: bool) -> None:
        """Filter isolated tables without FKs."""
        self._apply_fks_only_filter(checked)

    def _apply_fks_only_filter(self, fks_only: bool) -> None:
        """Show only tables with FKs or all tables."""
        if not fks_only:
            self.scene.show_all_tables()
        else:
            relational_tables: set[str] = set()
            for edge in self.scene.edges:
                relational_tables.add(edge.source_node.table.name)
                relational_tables.add(edge.target_node.table.name)

            self.scene.set_visible_tables(relational_tables)

        self._update_stats_label()
        self.view.zoom_fit()

    def _on_layout_changed(self) -> None:
        """Apply chosen layout algorithm."""
        layout_type = self.cmb_layout.currentData()
        self.scene.auto_layout(layout_type)
        self.view.zoom_fit()

    def _on_detail_mode_changed(self) -> None:
        """Apply chosen detail display mode."""
        mode = self.cmb_detail.currentData()
        self.scene.set_display_mode(mode)

    def _on_edge_style_changed(self) -> None:
        """Apply chosen connector line style."""
        style = self.cmb_style.currentData()
        self.scene.set_edge_style(style)

    def _on_table_focused(self, node) -> None:
        """Center view camera on specified table node."""
        self.view.centerOn(node)

    def _on_search_changed(self, query: str) -> None:
        """Filter and highlight table nodes matching table name or column names."""
        clean = query.strip().lower()
        for name, node in self.scene.nodes.items():
            if not clean:
                node.setOpacity(1.0)
                node.setSelected(False)
            else:
                matches_table = clean in name.lower()
                matches_col = any(clean in c.name.lower() for c in node.table.columns)
                if matches_table or matches_col:
                    node.setOpacity(1.0)
                    node.setSelected(True)
                else:
                    node.setOpacity(0.2)
                    node.setSelected(False)

    def _show_export_menu(self) -> None:
        """Display options for image and text format exports."""
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background-color: #ffffff; color: #0f172a; "
            "border: 1px solid #cbd5e1; font-size: 12px; }\n"
            "QMenu::item:selected { background-color: #eff6ff; color: #2563eb; }"
        )

        act_png_1x = menu.addAction("🖼️ Imagen PNG (1x)")
        act_png_2x = menu.addAction("🖼️ Imagen PNG (2x Alta Resolución)")
        act_png_4x = menu.addAction("🖼️ Imagen PNG (4x Ultra HD)")
        menu.addSeparator()
        act_mermaid = menu.addAction("📋 Copiar Diagrama Mermaid.js al Portapapeles")
        act_dbml = menu.addAction("📋 Copiar Diagrama DBML al Portapapeles")
        act_plantuml = menu.addAction("📋 Copiar Diagrama PlantUML al Portapapeles")

        action = menu.exec(self.btn_export.mapToGlobal(self.btn_export.rect().bottomLeft()))
        if action == act_png_1x:
            self._prompt_export_png(scale=1.0)
        elif action == act_png_2x:
            self._prompt_export_png(scale=2.0)
        elif action == act_png_4x:
            self._prompt_export_png(scale=4.0)
        elif action == act_mermaid:
            if self.schema:
                code = ERMermaidExporter.export(self.schema)
                QGuiApplication.clipboard().setText(code)
                QMessageBox.information(
                    self,
                    "Copiado",
                    "Código Mermaid.js copiado al portapapeles con éxito.",
                )
        elif action == act_dbml:
            if self.schema:
                code = ERDbmLExporter.export(self.schema)
                QGuiApplication.clipboard().setText(code)
                QMessageBox.information(
                    self, "Copiado", "Código DBML copiado al portapapeles con éxito."
                )
        elif action == act_plantuml:
            if self.schema:
                code = ERPlantUMLExporter.export(self.schema)
                QGuiApplication.clipboard().setText(code)
                QMessageBox.information(
                    self,
                    "Copiado",
                    "Código PlantUML copiado al portapapeles con éxito.",
                )

    def _prompt_export_png(self, scale: float = 1.0) -> None:
        """Prompt file save dialog and render PNG with given resolution scale."""
        if not self.scene.nodes:
            QMessageBox.information(self, "Diagrama Vacío", "No hay tablas para exportar.")
            return

        db_name = self.schema.database_name if self.schema else "db"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Diagrama ER como Imagen",
            f"diagrama_er_{db_name}_{int(scale)}x.png",
            "Imágenes PNG (*.png)",
        )
        if file_path:
            self.export_image(file_path, scale=scale)
            QMessageBox.information(
                self,
                "Exportación Exitosa",
                f"Diagrama guardado correctamente en:\n{file_path}",
            )

    def export_image(self, file_path: str, scale: float = 1.0) -> bool:
        """Render high-resolution raster image of the entire diagram."""
        items_rect = self.scene.itemsBoundingRect().adjusted(-40, -40, 40, 40)
        if items_rect.isEmpty():
            items_rect = QRectF(0, 0, 800, 600)

        width = int(items_rect.width() * scale)
        height = int(items_rect.height() * scale)

        image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(QColor("#f8fafc"))

        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        self.scene.render(painter, QRectF(0, 0, width, height), items_rect)
        painter.end()

        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        return image.save(file_path, "PNG")
