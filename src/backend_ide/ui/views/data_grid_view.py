"""Live Table Data Viewer and Editor Widget with Paging and Inline Modifications."""

from __future__ import annotations

import csv
import json
from typing import TYPE_CHECKING, Any

import qtawesome as qta
from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from backend_ide.domain.schema.models import Table
    from backend_ide.infrastructure.database.contracts import DatabaseConnection


class DataGridWidget(QWidget):
    """Interactive paginated data grid for browsing and editing database table records."""

    query_executed = Signal(str)

    def __init__(
        self,
        table: Table,
        connection: DatabaseConnection | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.table = table
        self.connection = connection

        self.current_page = 1
        self.page_size = 50
        self.total_rows = 0
        self.loaded_data: list[dict[str, Any]] = []
        self.pending_updates: dict[int, dict[str, Any]] = {}

        self._setup_ui()
        self.load_data()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Top Action Toolbar
        top_bar = QWidget()
        top_bar.setStyleSheet(
            "background-color: #ffffff; border-bottom: 1px solid #e2e8f0; padding: 4px;"
        )
        tb_layout = QHBoxLayout(top_bar)
        tb_layout.setContentsMargins(8, 4, 8, 4)
        tb_layout.setSpacing(6)

        btn_style = (
            "QPushButton { background-color: #f8fafc; border: 1px solid #cbd5e1; "
            "border-radius: 4px; padding: 4px 8px; color: #334155; font-size: 12px; }\n"
            "QPushButton:hover { background-color: #f1f5f9; color: #0f172a; }\n"
        )

        title_lbl = QLabel(f"📋 {self.table.name}")
        title_lbl.setStyleSheet(
            "font-weight: bold; font-size: 13px; color: #1e293b; margin-right: 8px;"
        )
        tb_layout.addWidget(title_lbl)

        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText("🔍 Filtrar en esta página…")
        self.txt_filter.setMaximumWidth(200)
        self.txt_filter.setFixedHeight(28)
        self.txt_filter.setStyleSheet(
            "QLineEdit { background-color: #f8fafc; border: 1px solid #cbd5e1; "
            "border-radius: 4px; padding: 2px 6px; color: #0f172a; }"
        )
        self.txt_filter.textChanged.connect(self._on_filter_changed)
        tb_layout.addWidget(self.txt_filter)

        self.btn_refresh = QPushButton("Refrescar")
        self.btn_refresh.setIcon(qta.icon("fa6s.arrows-rotate", color="#475569"))
        self.btn_refresh.setStyleSheet(btn_style)
        self.btn_refresh.clicked.connect(self.load_data)
        tb_layout.addWidget(self.btn_refresh)

        self.btn_save = QPushButton("💾 Guardar Cambios")
        self.btn_save.setStyleSheet(
            "QPushButton { background-color: #eff6ff; border: 1px solid #bfdbfe; "
            "border-radius: 4px; padding: 4px 10px; color: #1d4ed8; "
            "font-weight: 600; font-size: 12px; }\n"
            "QPushButton:hover { background-color: #dbeafe; }"
        )
        self.btn_save.clicked.connect(self._on_save_changes)
        tb_layout.addWidget(self.btn_save)

        self.btn_export_csv = QPushButton("CSV")
        self.btn_export_csv.setStyleSheet(btn_style)
        self.btn_export_csv.clicked.connect(self._export_csv)
        tb_layout.addWidget(self.btn_export_csv)

        self.btn_export_json = QPushButton("JSON")
        self.btn_export_json.setStyleSheet(btn_style)
        self.btn_export_json.clicked.connect(self._export_json)
        tb_layout.addWidget(self.btn_export_json)

        tb_layout.addStretch()
        layout.addWidget(top_bar)

        # 2. Main Data Table
        self.table_widget = QTableWidget()
        self.table_widget.setStyleSheet(
            "QTableWidget { background-color: #ffffff; alternate-background-color: #f8fafc; "
            "gridline-color: #e2e8f0; color: #0f172a; font-size: 12px; }\n"
            "QHeaderView::section { background-color: #f1f5f9; color: #334155; "
            "font-weight: 600; border: 1px solid #e2e8f0; padding: 4px; }\n"
            "QTableWidget::item:selected { background-color: #eff6ff; color: #2563eb; }"
        )
        self.table_widget.setAlternatingRowColors(True)
        self.table_widget.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        self.table_widget.itemChanged.connect(self._on_cell_changed)
        layout.addWidget(self.table_widget)

        # 3. Bottom Paging Toolbar
        bottom_bar = QWidget()
        bottom_bar.setStyleSheet(
            "background-color: #ffffff; border-top: 1px solid #e2e8f0; padding: 4px;"
        )
        bb_layout = QHBoxLayout(bottom_bar)
        bb_layout.setContentsMargins(8, 4, 8, 4)
        bb_layout.setSpacing(6)

        self.btn_first = QPushButton("⏮️")
        self.btn_first.setStyleSheet(btn_style)
        self.btn_first.clicked.connect(self._go_first)

        self.btn_prev = QPushButton("◀ Anterior")
        self.btn_prev.setStyleSheet(btn_style)
        self.btn_prev.clicked.connect(self._go_prev)

        self.lbl_page = QLabel("Página 1")
        self.lbl_page.setStyleSheet(
            "color: #475569; font-weight: 500; font-size: 12px; margin: 0 4px;"
        )

        self.btn_next = QPushButton("Siguiente ▶")
        self.btn_next.setStyleSheet(btn_style)
        self.btn_next.clicked.connect(self._go_next)

        self.cmb_page_size = QComboBox()
        self.cmb_page_size.setStyleSheet(
            "QComboBox { background-color: #f8fafc; border: 1px solid #cbd5e1; "
            "border-radius: 4px; padding: 2px 6px; color: #0f172a; font-size: 12px; }"
        )
        self.cmb_page_size.addItems(["50 filas", "100 filas", "250 filas", "500 filas"])
        self.cmb_page_size.currentIndexChanged.connect(self._on_page_size_changed)

        self.lbl_total = QLabel("0 filas")
        self.lbl_total.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 500;")

        bb_layout.addWidget(self.btn_first)
        bb_layout.addWidget(self.btn_prev)
        bb_layout.addWidget(self.lbl_page)
        bb_layout.addWidget(self.btn_next)
        bb_layout.addSpacing(12)
        bb_layout.addWidget(QLabel("Por página:"))
        bb_layout.addWidget(self.cmb_page_size)
        bb_layout.addStretch()
        bb_layout.addWidget(self.lbl_total)

        layout.addWidget(bottom_bar)

    def load_data(self) -> None:
        """Fetch records from database with LIMIT and OFFSET."""
        if not self.connection:
            return

        s_name = self.table.schema_name
        schema_prefix = f"{s_name}." if s_name and s_name != "public" else ""
        full_table = f"{schema_prefix}{self.table.name}"

        offset = (self.current_page - 1) * self.page_size

        try:
            # Query count
            count_sql = f"SELECT COUNT(*) AS total FROM {full_table};"
            count_res = self.connection.execute_query(count_sql)
            if count_res:
                self.total_rows = list(count_res[0].values())[0]

            # Query page
            sql = f"SELECT * FROM {full_table} LIMIT {self.page_size} OFFSET {offset};"
            rows = self.connection.execute_query(sql)
            self.loaded_data = rows
            self.pending_updates.clear()
            self._render_rows(rows)

            max_pages = max(1, (self.total_rows + self.page_size - 1) // self.page_size)
            self.lbl_page.setText(f"Página {self.current_page} de {max_pages}")
            self.lbl_total.setText(f"Mostrando {len(rows)} de {self.total_rows} filas totales")
            self.btn_prev.setEnabled(self.current_page > 1)
            self.btn_next.setEnabled(self.current_page < max_pages)

        except Exception as err:
            QMessageBox.critical(
                self, "Error al Cargar Datos", f"No se pudieron leer los datos:\n{err}"
            )

    def _render_rows(self, rows: list[dict[str, Any]]) -> None:
        self.table_widget.blockSignals(True)
        self.table_widget.clear()

        if not rows and not self.table.columns:
            self.table_widget.setRowCount(0)
            self.table_widget.setColumnCount(0)
            self.table_widget.blockSignals(False)
            return

        if self.table.columns:
            headers = [c.name for c in self.table.columns]
        elif rows:
            headers = list(rows[0].keys())
        else:
            headers = []

        self.table_widget.setColumnCount(len(headers))
        self.table_widget.setHorizontalHeaderLabels(headers)
        self.table_widget.setRowCount(len(rows))

        for row_idx, row in enumerate(rows):
            for col_idx, col_name in enumerate(headers):
                val = row.get(col_name)
                str_val = "NULL" if val is None else str(val)
                item = QTableWidgetItem(str_val)
                if val is None:
                    item.setForeground(QColor("#94a3b8"))
                self.table_widget.setItem(row_idx, col_idx, item)

        self.table_widget.blockSignals(False)

    def _on_cell_changed(self, item: QTableWidgetItem) -> None:
        row = item.row()
        col_name = self.table_widget.horizontalHeaderItem(item.column()).text()
        new_value = item.text()

        self.pending_updates.setdefault(row, {})[col_name] = new_value
        item.setBackground(QColor("#fef3c7"))

    def _on_save_changes(self) -> None:
        if not self.pending_updates:
            QMessageBox.information(
                self, "Sin Cambios", "No hay modificaciones pendientes para guardar."
            )
            return

        if not self.connection or not self.table.primary_key:
            QMessageBox.warning(
                self,
                "Sin Clave Primaria",
                "Se requiere clave primaria para actualizar registros.",
            )
            return

        pk_col = self.table.primary_key.column_names[0]
        s_name = self.table.schema_name
        schema_prefix = f"{s_name}." if s_name and s_name != "public" else ""
        full_table = f"{schema_prefix}{self.table.name}"

        success_count = 0
        try:
            for row_idx, changes in self.pending_updates.items():
                orig_row = self.loaded_data[row_idx]
                pk_val = orig_row.get(pk_col)

                set_clauses = []
                for k, v in changes.items():
                    if v == "NULL":
                        set_clauses.append(f"{k} = NULL")
                    else:
                        safe_v = v.replace("'", "''")
                        set_clauses.append(f"{k} = '{safe_v}'")

                set_str = ", ".join(set_clauses)
                update_sql = f"UPDATE {full_table} SET {set_str} WHERE {pk_col} = '{pk_val}';"
                self.connection.execute_non_query(update_sql)
                success_count += 1

            QMessageBox.information(
                self,
                "Guardado Exitoso",
                f"Se actualizaron {success_count} registro(s) correctamente en la base de datos.",
            )
            self.load_data()

        except Exception as err:
            QMessageBox.critical(
                self,
                "Error al Guardar",
                f"Ocurrió un error al persistir los cambios:\n{err}",
            )

    def _on_filter_changed(self, query: str) -> None:
        clean = query.strip().lower()
        for r in range(self.table_widget.rowCount()):
            row_matches = False
            for c in range(self.table_widget.columnCount()):
                item = self.table_widget.item(r, c)
                if item and clean in item.text().lower():
                    row_matches = True
                    break
            self.table_widget.setRowHidden(r, not row_matches)

    def _go_first(self) -> None:
        if self.current_page != 1:
            self.current_page = 1
            self.load_data()

    def _go_prev(self) -> None:
        if self.current_page > 1:
            self.current_page -= 1
            self.load_data()

    def _go_next(self) -> None:
        self.current_page += 1
        self.load_data()

    def _on_page_size_changed(self) -> None:
        sizes = [50, 100, 250, 500]
        self.page_size = sizes[self.cmb_page_size.currentIndex()]
        self.current_page = 1
        self.load_data()

    def _export_csv(self) -> None:
        if not self.loaded_data:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar Datos CSV", f"{self.table.name}.csv", "Archivos CSV (*.csv)"
        )
        if path:
            headers = list(self.loaded_data[0].keys())
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(self.loaded_data)
            QMessageBox.information(self, "Exportado", f"Datos exportados a CSV en:\n{path}")

    def _export_json(self) -> None:
        if not self.loaded_data:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Datos JSON",
            f"{self.table.name}.json",
            "Archivos JSON (*.json)",
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.loaded_data, f, indent=2, default=str)
            QMessageBox.information(self, "Exportado", f"Datos exportados a JSON en:\n{path}")
