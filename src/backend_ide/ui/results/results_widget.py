"""PySide6 Results Widget displaying Tabbed Query Results Grid, Execution Stats, and Data Export."""

from pathlib import Path

import qtawesome as qta
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QTableView,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from backend_ide.application.query_service import ExecuteQueryService
from backend_ide.domain.sql import QueryResult
from backend_ide.ui.theme import ThemeManager


class ResultsWidget(QWidget):
    """Widget displaying tabular query results, execution stats, and CSV/JSON export."""

    def __init__(self, query_service: ExecuteQueryService | None = None, parent=None) -> None:
        super().__init__(parent)
        self.query_service = query_service or ExecuteQueryService()
        self.current_result: QueryResult | None = None
        self._theme_manager = ThemeManager.get_instance()
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Construct Results UI layout with tabbed views and action controls."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # 1. Action & Filter Bar
        self.action_bar = QWidget()
        action_layout = QHBoxLayout(self.action_bar)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(8)

        self.lbl_stats = QLabel("Listo")
        self.lbl_stats.setObjectName("results_stats")

        self.txt_filter_grid = QLineEdit()
        self.txt_filter_grid.setFixedHeight(32)
        self.txt_filter_grid.setPlaceholderText("Filtrar resultados…")
        self.txt_filter_grid.setMaximumWidth(240)
        self._search_action = self.txt_filter_grid.addAction(
            qta.icon("fa6s.magnifying-glass"), QLineEdit.ActionPosition.TrailingPosition
        )
        self.txt_filter_grid.textChanged.connect(self._filter_grid_rows)

        # Export Menu Button
        self.btn_export = QPushButton("Exportar")
        self.btn_export.setFixedHeight(32)
        self.btn_export.setEnabled(False)

        export_menu = QMenu(self.btn_export)
        self.act_csv = export_menu.addAction("Exportar a CSV")
        self.act_json = export_menu.addAction("Exportar a JSON")
        self.act_csv.triggered.connect(self._on_export_csv)
        self.act_json.triggered.connect(self._on_export_json)

        self.btn_export.setMenu(export_menu)

        action_layout.addWidget(self.lbl_stats)
        action_layout.addStretch()
        action_layout.addWidget(self.txt_filter_grid)
        action_layout.addWidget(self.btn_export)

        layout.addWidget(self.action_bar)

        # 2. Main Tabbed Results & Messages View
        self.results_tabs = QTabWidget()

        # Grid View Tab
        self.table_view = QTableView()
        self.table_model = QStandardItemModel()
        self.table_view.setModel(self.table_model)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_view.setAlternatingRowColors(True)

        # Messages & Error View Tab
        self.txt_messages = QTextEdit()
        self.txt_messages.setObjectName("monospace_output")
        self.txt_messages.setReadOnly(True)

        self.results_tabs.addTab(self.table_view, "Datos")
        self.results_tabs.addTab(self.txt_messages, "Mensajes")

        layout.addWidget(self.results_tabs)

        self._theme_manager.theme_changed.connect(self._update_icons)
        self._update_icons()

    def _update_icons(self, _mode: str | None = None) -> None:
        """Keep result actions and tabs readable in the selected theme."""
        color = self._theme_manager.current_palette.text_primary
        muted = self._theme_manager.current_palette.text_muted
        self.btn_export.setIcon(qta.icon("fa6s.download", color=color))
        self.act_csv.setIcon(qta.icon("fa6s.file-csv", color=color))
        self.act_json.setIcon(qta.icon("fa6s.file-code", color=color))
        self._search_action.setIcon(qta.icon("fa6s.magnifying-glass", color=muted))
        self.results_tabs.setTabIcon(0, qta.icon("fa6s.table", color=color))
        self.results_tabs.setTabIcon(1, qta.icon("fa6s.rectangle-list", color=color))

    def display_result(self, result: QueryResult) -> None:
        """Populate grid model or error view from QueryResult instance."""
        self.current_result = result
        self.table_model.clear()

        if result.has_error:
            self.results_tabs.setCurrentWidget(self.txt_messages)
            msg = (
                f"Error de ejecución SQL ({result.execution_time_ms} ms):\n\n{result.error_message}"
            )
            self.txt_messages.setPlainText(msg)
            self.lbl_stats.setText(f"Error en {result.execution_time_ms} ms")
            self.btn_export.setEnabled(False)
            return

        self.results_tabs.setCurrentWidget(self.table_view)
        self.btn_export.setEnabled(len(result.rows) > 0)

        # Set Header Labels
        headers = [c.name for c in result.columns]
        self.table_model.setHorizontalHeaderLabels(headers)

        # Populate Rows
        for row_data in result.rows:
            items = []
            for col in result.columns:
                val = row_data.get(col.name)
                val_str = str(val) if val is not None else "NULL"
                item = QStandardItem(val_str)
                items.append(item)
            self.table_model.appendRow(items)

        self.lbl_stats.setText(
            f"{result.execution_time_ms} ms  ·  {result.row_count} filas devueltas"
        )
        msg_ok = (
            "Consulta ejecutada correctamente.\n"
            f"Tiempo: {result.execution_time_ms} ms\n"
            f"Filas: {result.row_count}"
        )
        self.txt_messages.setPlainText(msg_ok)

    def _filter_grid_rows(self, text: str) -> None:
        """Filter visible rows in table view based on quick search text."""
        filter_text = text.lower().strip()
        for row_idx in range(self.table_model.rowCount()):
            match = False
            for col_idx in range(self.table_model.columnCount()):
                item = self.table_model.item(row_idx, col_idx)
                if item and filter_text in item.text().lower():
                    match = True
                    break
            self.table_view.setRowHidden(row_idx, not match)

    def _on_export_csv(self) -> None:
        """Open file dialog and export results to CSV."""
        if not self.current_result or not self.current_result.rows:
            return
        path_str, _ = QFileDialog.getSaveFileName(
            self, "Exportar a CSV", "resultado_consulta.csv", "Archivos CSV (*.csv)"
        )
        if path_str:
            self.query_service.export_to_csv(self.current_result, Path(path_str))

    def _on_export_json(self) -> None:
        """Open file dialog and export results to JSON."""
        if not self.current_result or not self.current_result.rows:
            return
        path_str, _ = QFileDialog.getSaveFileName(
            self, "Exportar a JSON", "resultado_consulta.json", "Archivos JSON (*.json)"
        )
        if path_str:
            self.query_service.export_to_json(self.current_result, Path(path_str))
