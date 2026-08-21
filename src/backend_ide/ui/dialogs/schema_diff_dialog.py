"""Interactive Schema Comparison and DDL Migration Dialog."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from backend_ide.domain.diff.engine import SchemaDiffEngine
from backend_ide.domain.diff.models import SchemaDiffResult

if TYPE_CHECKING:
    from backend_ide.domain.schema.models import DatabaseSchema


class SchemaDiffDialog(QDialog):
    """Dialog displaying schema differences and generating executable DDL migrations."""

    open_in_editor_requested = Signal(str)

    def __init__(
        self,
        source_schema: DatabaseSchema,
        target_schema: DatabaseSchema,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.source_schema = source_schema
        self.target_schema = target_schema

        self.diff_result: SchemaDiffResult = SchemaDiffEngine.compare(source_schema, target_schema)

        self.setWindowTitle("Comparador de Esquemas y Generador de Migraciones DDL")
        self.resize(1000, 650)
        self.setStyleSheet(
            "QDialog { background-color: #ffffff; color: #0f172a; }\n"
            "QLabel { color: #334155; font-size: 12px; }\n"
            "QTreeWidget { background-color: #f8fafc; border: 1px solid #cbd5e1; "
            "border-radius: 6px; color: #0f172a; font-size: 12px; }\n"
            "QPlainTextEdit { background-color: #f8fafc; border: 1px solid #cbd5e1; "
            "border-radius: 6px; font-family: 'Fira Code', monospace; font-size: 12px; "
            "color: #0f172a; }\n"
            "QPushButton { background-color: #f8fafc; border: 1px solid #cbd5e1; "
            "border-radius: 4px; padding: 5px 12px; color: #334155; font-size: 12px; "
            "font-weight: 500; }\n"
            "QPushButton:hover { background-color: #f1f5f9; color: #0f172a; }\n"
        )

        self._setup_ui()
        self._populate_tree()
        self._generate_sql()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Header Info
        hdr_lbl = QLabel(
            f"<b>Base de Datos Origen:</b> {self.source_schema.database_name} ➔ "
            f"<b>Destino:</b> {self.target_schema.database_name}"
        )
        hdr_lbl.setStyleSheet("font-size: 13px; color: #1e293b;")
        layout.addWidget(hdr_lbl)

        # Splitter: Left Changes Tree / Right SQL Preview
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Panel (Diff Tree)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(8)

        lbl_tree = QLabel("Árbol de Diferencias Estructurales:")
        lbl_tree.setStyleSheet("font-weight: 600;")
        left_layout.addWidget(lbl_tree)

        self.tree_diff = QTreeWidget()
        self.tree_diff.setHeaderLabels(["Elemento", "Tipo de Cambio"])
        self.tree_diff.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        left_layout.addWidget(self.tree_diff)

        self.chk_safe_mode = QCheckBox("🛡️ Modo Seguro (Comentar comandos DROP destructivos)")
        self.chk_safe_mode.setChecked(True)
        self.chk_safe_mode.toggled.connect(self._generate_sql)
        left_layout.addWidget(self.chk_safe_mode)

        splitter.addWidget(left_widget)

        # Right Panel (SQL DDL Script Preview)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(8)

        lbl_sql = QLabel("Script SQL de Migración DDL Generado:")
        lbl_sql.setStyleSheet("font-weight: 600;")
        right_layout.addWidget(lbl_sql)

        self.txt_sql = QPlainTextEdit()
        self.txt_sql.setFont(QFont("Fira Code", 10))
        right_layout.addWidget(self.txt_sql)

        actions_layout = QHBoxLayout()
        self.btn_copy_sql = QPushButton("📋 Copiar SQL")
        self.btn_copy_sql.clicked.connect(self._copy_sql)

        self.btn_save_sql = QPushButton("💾 Guardar Archivo .sql")
        self.btn_save_sql.clicked.connect(self._save_sql_file)

        self.btn_open_editor = QPushButton("⚡ Abrir en Editor SQL")
        self.btn_open_editor.setStyleSheet(
            "QPushButton { background-color: #eff6ff; border: 1px solid #bfdbfe; "
            "color: #1d4ed8; font-weight: 600; }\n"
            "QPushButton:hover { background-color: #dbeafe; }"
        )
        self.btn_open_editor.clicked.connect(self._on_open_in_editor)

        actions_layout.addWidget(self.btn_copy_sql)
        actions_layout.addWidget(self.btn_save_sql)
        actions_layout.addStretch()
        actions_layout.addWidget(self.btn_open_editor)
        right_layout.addLayout(actions_layout)

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)

        layout.addWidget(splitter)

    def _populate_tree(self) -> None:
        self.tree_diff.clear()

        # Added tables
        if self.diff_result.added_tables:
            item_added = QTreeWidgetItem(
                self.tree_diff,
                [f"Tablas Nuevas ({len(self.diff_result.added_tables)})", "CREATE"],
            )
            item_added.setForeground(0, QColor("#16a34a"))
            for t in self.diff_result.added_tables:
                child = QTreeWidgetItem(item_added, [f"📋 {t.name}", f"+{len(t.columns)} columnas"])
                child.setForeground(0, QColor("#16a34a"))
            item_added.setExpanded(True)

        # Modified tables
        if self.diff_result.modified_tables:
            item_mod = QTreeWidgetItem(
                self.tree_diff,
                [
                    f"Tablas Modificadas ({len(self.diff_result.modified_tables)})",
                    "ALTER",
                ],
            )
            item_mod.setForeground(0, QColor("#d97706"))
            for t_diff in self.diff_result.modified_tables:
                t_child = QTreeWidgetItem(item_mod, [f"📋 {t_diff.table_name}", "MODIFICADA"])
                for col in t_diff.added_columns:
                    c_item = QTreeWidgetItem(
                        t_child, [f"+ {col.name}", f"Agregar ({col.native_type})"]
                    )
                    c_item.setForeground(0, QColor("#16a34a"))
                for c_diff in t_diff.modified_columns:
                    c_item = QTreeWidgetItem(
                        t_child,
                        [f"~ {c_diff.column_name}", "; ".join(c_diff.details)],
                    )
                    c_item.setForeground(0, QColor("#d97706"))
                for col in t_diff.dropped_columns:
                    c_item = QTreeWidgetItem(t_child, [f"- {col.name}", "Eliminar"])
                    c_item.setForeground(0, QColor("#dc2626"))
                t_child.setExpanded(True)
            item_mod.setExpanded(True)

        # Dropped tables
        if self.diff_result.dropped_tables:
            item_dropped = QTreeWidgetItem(
                self.tree_diff,
                [
                    f"Tablas a Eliminar ({len(self.diff_result.dropped_tables)})",
                    "DROP",
                ],
            )
            item_dropped.setForeground(0, QColor("#dc2626"))
            for t in self.diff_result.dropped_tables:
                child = QTreeWidgetItem(item_dropped, [f"🗑️ {t.name}", "ELIMINAR"])
                child.setForeground(0, QColor("#dc2626"))
            item_dropped.setExpanded(True)

        if not self.diff_result.has_differences:
            empty_item = QTreeWidgetItem(
                self.tree_diff,
                ["✅ Los esquemas son idénticos. No hay cambios.", ""],
            )
            empty_item.setForeground(0, QColor("#16a34a"))

    def _generate_sql(self) -> None:
        if not self.diff_result.has_differences:
            self.txt_sql.setPlainText(
                "-- Ambos esquemas son idénticos.\n-- No se requieren sentencias DDL de migración."
            )
            return

        ddl = SchemaDiffEngine.generate_migration_ddl(
            self.diff_result,
            dialect=self.target_schema.engine_name or "postgresql",
            safe_mode=self.chk_safe_mode.isChecked(),
        )
        self.txt_sql.setPlainText(ddl)

    def _copy_sql(self) -> None:
        QGuiApplication.clipboard().setText(self.txt_sql.toPlainText())
        QMessageBox.information(self, "Copiado", "Script DDL de migración copiado al portapapeles.")

    def _save_sql_file(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Script de Migración",
            "migration_diff.sql",
            "Archivos SQL (*.sql)",
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.txt_sql.toPlainText())
            QMessageBox.information(self, "Guardado", f"Script guardado exitosamente en:\n{path}")

    def _on_open_in_editor(self) -> None:
        sql = self.txt_sql.toPlainText()
        self.open_in_editor_requested.emit(sql)
        self.accept()
