"""Interactive PySide6 Dialog for Polyglot ORM and Non-ORM Code Generation."""

from __future__ import annotations

import os

import qtawesome as qta
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from backend_ide.domain.schema.models import DatabaseSchema
from backend_ide.generators.contracts import (
    GeneratedProject,
    GenerationRequest,
    GenerationTarget,
    GeneratorCategory,
)
from backend_ide.generators.registry import GeneratorRegistry


class CodeGenerationDialog(QDialog):
    """Modal dialog allowing selection of target language/ORM and real-time code preview."""

    def __init__(
        self,
        schema: DatabaseSchema,
        selected_table_name: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.schema = schema
        self.selected_table_name = selected_table_name
        self.registry = GeneratorRegistry.get_instance()
        self.current_project: GeneratedProject | None = None

        self.setWindowTitle("Generador de Modelos y Código de Backend")
        self.setMinimumSize(960, 640)
        self.resize(1100, 720)

        self._init_ui()
        self._populate_targets()
        self._populate_tables()
        self._on_target_changed()

    def _init_ui(self) -> None:
        """Construct the split view dialog interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header Title
        hdr_layout = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon("fa6s.laptop-code", color="#89b4fa").pixmap(24, 24))
        hdr_layout.addWidget(icon_lbl)

        title = QLabel("Generador Polyglot de Código (ORM & SQL Directo)")
        title.setStyleSheet("font-size: 15px; font-weight: bold;")
        hdr_layout.addWidget(title)
        hdr_layout.addStretch()
        main_layout.addLayout(hdr_layout)

        # Horizontal Splitter: Left Options / Right Preview
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Panel (Options & Table Selection)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(10)

        # Target Selector
        lbl_target = QLabel("Framework / Destino:")
        lbl_target.setStyleSheet("font-weight: 600;")
        left_layout.addWidget(lbl_target)

        self.cmb_target = QComboBox()
        self.cmb_target.setFixedHeight(32)
        self.cmb_target.currentIndexChanged.connect(self._on_target_changed)
        left_layout.addWidget(self.cmb_target)

        self.lbl_target_desc = QLabel()
        self.lbl_target_desc.setStyleSheet("color: #a6adc8; font-size: 11px;")
        self.lbl_target_desc.setWordWrap(True)
        left_layout.addWidget(self.lbl_target_desc)

        # Tables Selector
        lbl_tables = QLabel("Tablas a generar:")
        lbl_tables.setStyleSheet("font-weight: 600; margin-top: 8px;")
        left_layout.addWidget(lbl_tables)

        self.lst_tables = QListWidget()
        self.lst_tables.itemChanged.connect(self._regenerate_preview)
        self.lst_tables.itemSelectionChanged.connect(self._regenerate_preview)
        left_layout.addWidget(self.lst_tables)

        # Quick Select/Deselect buttons for table list
        sel_btn_row = QHBoxLayout()
        self.btn_select_all = QPushButton("Todas")
        self.btn_select_all.setFixedHeight(24)
        self.btn_select_all.clicked.connect(self._select_all_tables)
        sel_btn_row.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton("Ninguna")
        self.btn_deselect_all.setFixedHeight(24)
        self.btn_deselect_all.clicked.connect(self._deselect_all_tables)
        sel_btn_row.addWidget(self.btn_deselect_all)
        left_layout.addLayout(sel_btn_row)

        # Options Checkboxes
        self.chk_relationships = QCheckBox("Incluir Relaciones (FKs)")
        self.chk_relationships.setChecked(True)
        self.chk_relationships.stateChanged.connect(self._regenerate_preview)
        left_layout.addWidget(self.chk_relationships)

        self.chk_type_hints = QCheckBox("Tipado estricto")
        self.chk_type_hints.setChecked(True)
        self.chk_type_hints.stateChanged.connect(self._regenerate_preview)
        left_layout.addWidget(self.chk_type_hints)

        left_layout.addStretch()
        left_panel.setMinimumWidth(280)
        left_panel.setMaximumWidth(360)
        splitter.addWidget(left_panel)

        # Right Panel (Code Preview & File Tabs)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(8)

        lbl_preview = QLabel("Vista Previa del Código Generado:")
        lbl_preview.setStyleSheet("font-weight: 600;")
        right_layout.addWidget(lbl_preview)

        self.tab_files = QTabWidget()
        self.tab_files.setDocumentMode(True)
        right_layout.addWidget(self.tab_files)

        splitter.addWidget(right_panel)
        splitter.setSizes([320, 680])
        main_layout.addWidget(splitter, 1)

        # Bottom Button Bar
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)

        self.btn_copy = QPushButton("Copiar al Portapapeles")
        self.btn_copy.setIcon(qta.icon("fa6s.copy"))
        self.btn_copy.setFixedHeight(34)
        self.btn_copy.clicked.connect(self._copy_to_clipboard)
        btn_bar.addWidget(self.btn_copy)

        self.btn_export = QPushButton("Exportar Archivos a Carpeta...")
        self.btn_export.setIcon(qta.icon("fa6s.folder-open"))
        self.btn_export.setFixedHeight(34)
        self.btn_export.clicked.connect(self._export_to_directory)
        btn_bar.addWidget(self.btn_export)

        btn_bar.addStretch()

        self.btn_close = QPushButton("Cerrar")
        self.btn_close.setFixedHeight(34)
        self.btn_close.clicked.connect(self.accept)
        btn_bar.addWidget(self.btn_close)

        main_layout.addLayout(btn_bar)

    def _select_all_tables(self) -> None:
        """Check all tables in the list."""
        self.lst_tables.blockSignals(True)
        for i in range(self.lst_tables.count()):
            self.lst_tables.item(i).setCheckState(Qt.CheckState.Checked)
        self.lst_tables.blockSignals(False)
        self._regenerate_preview()

    def _deselect_all_tables(self) -> None:
        """Uncheck all tables in the list."""
        self.lst_tables.blockSignals(True)
        for i in range(self.lst_tables.count()):
            self.lst_tables.item(i).setCheckState(Qt.CheckState.Unchecked)
        self.lst_tables.blockSignals(False)
        self._regenerate_preview()

    def _populate_tables(self) -> None:
        """Populate the table list from schema with checkable items."""
        self.lst_tables.blockSignals(True)
        self.lst_tables.clear()

        for schema_item in self.schema.schemas:
            for table in schema_item.tables:
                item = QListWidgetItem(table.name)
                item.setData(Qt.ItemDataRole.UserRole, table.name)
                item.setIcon(qta.icon("fa6s.table"))
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)

                is_target = (
                    not self.selected_table_name
                    or table.name.lower() == self.selected_table_name.lower()
                )
                item.setCheckState(Qt.CheckState.Checked if is_target else Qt.CheckState.Unchecked)
                self.lst_tables.addItem(item)

        self.lst_tables.blockSignals(False)

    def _populate_targets(self) -> None:
        """Populate available generator targets in the dropdown."""
        self.cmb_target.clear()
        generators = self.registry.list_all()

        for gen in generators:
            cat_label = "ORM" if gen.category == GeneratorCategory.ORM_MODEL else "SQL Directo"
            display_text = f"{gen.name} [{cat_label}]"
            self.cmb_target.addItem(display_text, gen.target)

    def _on_target_changed(self) -> None:
        """Update description and regenerate code on target switch."""
        target = self.cmb_target.currentData()
        if target:
            gen = self.registry.get(target)
            if gen:
                self.lbl_target_desc.setText(gen.description)
        self._regenerate_preview()

    def _get_selected_tables(self) -> list[str]:
        """Return list of selected table names."""
        selected: list[str] = []
        for i in range(self.lst_tables.count()):
            item = self.lst_tables.item(i)
            if item.checkState() == Qt.CheckState.Checked or item.isSelected():
                tbl = item.data(Qt.ItemDataRole.UserRole)
                if tbl not in selected:
                    selected.append(tbl)

        if not selected:
            for item in self.lst_tables.selectedItems():
                tbl = item.data(Qt.ItemDataRole.UserRole)
                if tbl not in selected:
                    selected.append(tbl)

        return selected

    def _regenerate_preview(self) -> None:
        """Execute code generator and display files in tabs."""
        target: GenerationTarget | None = self.cmb_target.currentData()
        if not target:
            return

        selected_tables = self._get_selected_tables()
        request = GenerationRequest(
            target=target,
            selected_tables=selected_tables,
            include_relationships=self.chk_relationships.isChecked(),
            include_type_hints=self.chk_type_hints.isChecked(),
        )

        try:
            self.current_project = self.registry.generate(self.schema, request)
        except Exception as e:
            self.tab_files.clear()
            err_view = QPlainTextEdit(f"Error generando código:\n{e}")
            self.tab_files.addTab(err_view, "Error")
            return

        self.tab_files.clear()
        mono_font = QFont("Monospace", 10)
        mono_font.setStyleHint(QFont.StyleHint.Monospace)

        for file in self.current_project.files:
            editor = QPlainTextEdit()
            editor.setReadOnly(True)
            editor.setFont(mono_font)
            editor.setPlainText(file.content)
            tab_title = os.path.basename(file.path)
            self.tab_files.addTab(editor, tab_title)

    def _copy_to_clipboard(self) -> None:
        """Copy active tab code to system clipboard."""
        current_widget = self.tab_files.currentWidget()
        if isinstance(current_widget, QPlainTextEdit):
            text = current_widget.toPlainText()
            QGuiApplication.clipboard().setText(text)

    def _export_to_directory(self) -> None:
        """Export all generated files to a selected disk directory."""
        if not self.current_project or not self.current_project.files:
            QMessageBox.warning(self, "Exportar", "No hay archivos generados para exportar.")
            return

        target_dir = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar Carpeta de Destino",
            os.path.expanduser("~"),
        )
        if not target_dir:
            return

        try:
            for file in self.current_project.files:
                dest_path = os.path.join(target_dir, file.path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                with open(dest_path, "w", encoding="utf-8") as f:
                    f.write(file.content)

            QMessageBox.information(
                self,
                "Exportación Exitosa",
                f"Se exportaron {len(self.current_project.files)} archivos a:\n{target_dir}",
            )
        except Exception as err:
            QMessageBox.critical(
                self,
                "Error de Exportación",
                f"No se pudieron exportar los archivos:\n{err}",
            )
