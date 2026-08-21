"""Interactive PySide6 Dialog for Legacy DBF Inspection, Record Counting, and Migration."""

from __future__ import annotations

import os

import qtawesome as qta
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from backend_ide.legacy.dbf.inspector import DBFInspector
from backend_ide.legacy.dbf.migration import DBFMigrationOptions, DBFMigrationService
from backend_ide.legacy.dbf.models import DBFTableSummary
from backend_ide.legacy.dbf.parser import DBFParser


class DBFMigrationWorker(QThread):
    """Background worker to migrate DBF tables without freezing the GUI."""

    progress = Signal(str, int, int)  # table_name, current, total
    finished_migration = Signal(list)  # list[DBFMigrationResult]
    error = Signal(str)

    def __init__(
        self,
        directory: str,
        output_sqlite: str,
        options: DBFMigrationOptions,
    ) -> None:
        super().__init__()
        self.directory = directory
        self.output_sqlite = output_sqlite
        self.options = options

    def run(self) -> None:
        """Execute migration in worker thread."""
        try:
            results = DBFMigrationService.migrate_directory_to_sqlite_file(
                self.directory,
                self.output_sqlite,
                options=self.options,
                progress_callback=self._on_progress,
            )
            self.finished_migration.emit(results)
        except Exception as e:
            self.error.emit(str(e))

    def _on_progress(self, table: str, curr: int, tot: int) -> None:
        self.progress.emit(table, curr, tot)


class DBFMigrationDialog(QDialog):
    """Dialog to inspect DBF folders, display record counts per table, and run migrations."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Migrador de Tablas DBF (dBase / FoxPro / Clipper)")
        self.setMinimumSize(950, 650)
        self.resize(1050, 700)

        self._summaries: list[DBFTableSummary] = []
        self._worker: DBFMigrationWorker | None = None

        self._init_ui()

    def _init_ui(self) -> None:
        """Construct dialog layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header Title
        hdr_layout = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon("fa6s.box-archive", color="#f9e2af").pixmap(24, 24))
        hdr_layout.addWidget(icon_lbl)

        title = QLabel("Explorador y Migrador de Bases de Datos Legacy DBF")
        title.setStyleSheet("font-size: 15px; font-weight: bold;")
        hdr_layout.addWidget(title)
        hdr_layout.addStretch()
        layout.addLayout(hdr_layout)

        # Folder Selection Row
        folder_row = QHBoxLayout()
        folder_row.setSpacing(8)

        lbl_folder = QLabel("Carpeta DBF:")
        lbl_folder.setStyleSheet("font-weight: 600;")
        folder_row.addWidget(lbl_folder)

        self.txt_folder = QLineEdit()
        self.txt_folder.setPlaceholderText("Selecciona la carpeta contenedora de archivos .DBF...")
        self.txt_folder.setFixedHeight(32)
        folder_row.addWidget(self.txt_folder, 1)

        self.btn_browse = QPushButton("Examinar...")
        self.btn_browse.setIcon(qta.icon("fa6s.folder-open"))
        self.btn_browse.setFixedHeight(32)
        self.btn_browse.clicked.connect(self._browse_directory)
        folder_row.addWidget(self.btn_browse)

        lbl_enc = QLabel("Codificación:")
        folder_row.addWidget(lbl_enc)

        self.cmb_encoding = QComboBox()
        self.cmb_encoding.setFixedHeight(32)
        self.cmb_encoding.addItems(["cp1252", "latin1", "cp850", "cp437", "utf-8"])
        folder_row.addWidget(self.cmb_encoding)

        self.btn_scan = QPushButton("Escanear")
        self.btn_scan.setIcon(qta.icon("fa6s.magnifying-glass"))
        self.btn_scan.setFixedHeight(32)
        self.btn_scan.clicked.connect(self._scan_directory)
        folder_row.addWidget(self.btn_scan)

        layout.addLayout(folder_row)

        # Tables Grid Summary
        self.table_grid = QTableWidget()
        self.table_grid.setColumnCount(6)
        self.table_grid.setHorizontalHeaderLabels(
            [
                "Tabla DBF",
                "Registros Totales",
                "Campos",
                "Tamaño",
                "Tiene Memo",
                "Última Modificación",
            ]
        )
        self.table_grid.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_grid.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table_grid.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table_grid, 1)

        # Migration Options Row
        opts_box = QHBoxLayout()
        self.chk_add_pk = QCheckBox("Agregar ID Auto-Incremental")
        self.chk_add_pk.setChecked(True)
        opts_box.addWidget(self.chk_add_pk)

        self.chk_sanitize = QCheckBox("Sanitizar Nombres a snake_case")
        self.chk_sanitize.setChecked(True)
        opts_box.addWidget(self.chk_sanitize)

        self.chk_inc_deleted = QCheckBox("Incluir Registros Marcados como Eliminados")
        opts_box.addWidget(self.chk_inc_deleted)
        opts_box.addStretch()

        layout.addLayout(opts_box)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(18)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.lbl_progress_status = QLabel("")
        self.lbl_progress_status.hide()
        layout.addWidget(self.lbl_progress_status)

        # Bottom Button Bar
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)

        self.btn_migrate_sqlite = QPushButton("Migrar todo a SQLite...")
        self.btn_migrate_sqlite.setIcon(qta.icon("fa6s.database", color="#a6e3a1"))
        self.btn_migrate_sqlite.setFixedHeight(34)
        self.btn_migrate_sqlite.clicked.connect(self._migrate_to_sqlite)
        btn_bar.addWidget(self.btn_migrate_sqlite)

        self.btn_view_records = QPushButton("Ver Registros")
        self.btn_view_records.setIcon(qta.icon("fa6s.table"))
        self.btn_view_records.setFixedHeight(34)
        self.btn_view_records.clicked.connect(self._view_selected_records)
        btn_bar.addWidget(self.btn_view_records)

        btn_bar.addStretch()

        self.btn_close = QPushButton("Cerrar")
        self.btn_close.setFixedHeight(34)
        self.btn_close.clicked.connect(self.accept)
        btn_bar.addWidget(self.btn_close)

        layout.addLayout(btn_bar)

    def _browse_directory(self) -> None:
        """Open file dialog to pick folder containing DBF files."""
        dir_path = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta con Archivos DBF")
        if dir_path:
            self.txt_folder.setText(dir_path)
            self._scan_directory()

    def _scan_directory(self) -> None:
        """Scan directory and display record counts for each DBF table."""
        folder = self.txt_folder.text().strip()
        if not folder or not os.path.isdir(folder):
            QMessageBox.warning(
                self,
                "Carpeta Inválida",
                "Selecciona una carpeta válida que contenga archivos .DBF.",
            )
            return

        encoding = self.cmb_encoding.currentText()
        try:
            self._summaries = DBFInspector.inspect_directory(folder, encoding=encoding)
        except Exception as e:
            QMessageBox.critical(
                self, "Error de Inspección", f"Error al escanear archivos DBF:\n{e}"
            )
            return

        self.table_grid.setRowCount(0)
        total_rows = 0

        for i, s in enumerate(self._summaries):
            self.table_grid.insertRow(i)
            total_rows += s.record_count

            # Table name
            item_name = QTableWidgetItem(s.table_name)
            item_name.setIcon(qta.icon("fa6s.table", color="#cdd6f4"))
            self.table_grid.setItem(i, 0, item_name)

            # Record count
            item_count = QTableWidgetItem(f"{s.record_count:,}")
            item_count.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table_grid.setItem(i, 1, item_count)

            # Fields
            item_fields = QTableWidgetItem(str(s.field_count))
            item_fields.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_grid.setItem(i, 2, item_fields)

            # Size
            size_mb = s.file_size_bytes / (1024 * 1024)
            size_str = (
                f"{size_mb:.2f} MB" if size_mb >= 1.0 else f"{s.file_size_bytes / 1024:.1f} KB"
            )
            item_size = QTableWidgetItem(size_str)
            item_size.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table_grid.setItem(i, 3, item_size)

            # Memo
            item_memo = QTableWidgetItem("Sí" if s.has_memo else "No")
            item_memo.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_grid.setItem(i, 4, item_memo)

            # Modified
            item_mod = QTableWidgetItem(s.last_modified or "—")
            self.table_grid.setItem(i, 5, item_mod)

        if not self._summaries:
            QMessageBox.information(
                self, "Sin Tablas", "No se encontraron archivos .DBF en la carpeta especificada."
            )

    def _view_selected_records(self) -> None:
        """Quickly view first 50 records of the selected DBF table."""
        row = self.table_grid.currentRow()
        if row < 0 or row >= len(self._summaries):
            QMessageBox.information(
                self, "Selección", "Selecciona una tabla de la lista para ver sus registros."
            )
            return

        summary = self._summaries[row]
        encoding = self.cmb_encoding.currentText()

        try:
            records = DBFParser.read_records(summary.file_path, limit=50, encoding=encoding)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron leer los registros:\n{e}")
            return

        # Show in a quick dialog
        dlg = QDialog(self)
        dlg.setWindowTitle(
            f"Vista Previa: {summary.table_name} ({len(records)}/{summary.record_count:,} filas)"
        )
        dlg.resize(800, 500)
        vbox = QVBoxLayout(dlg)

        preview_grid = QTableWidget(dlg)
        if records:
            headers = list(records[0].keys())
            preview_grid.setColumnCount(len(headers))
            preview_grid.setHorizontalHeaderLabels(headers)
            preview_grid.setRowCount(len(records))

            for r_idx, r_data in enumerate(records):
                for c_idx, h in enumerate(headers):
                    val = r_data.get(h)
                    preview_grid.setItem(
                        r_idx, c_idx, QTableWidgetItem(str(val) if val is not None else "")
                    )

        vbox.addWidget(preview_grid)
        dlg.exec()

    def _migrate_to_sqlite(self) -> None:
        """Migrate all discovered DBF tables to a SQLite database file."""
        if not self._summaries:
            QMessageBox.warning(self, "Sin tablas", "Primero escanea una carpeta con tablas DBF.")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Base de Datos SQLite",
            os.path.join(self.txt_folder.text(), "migracion_dbf.sqlite"),
            "SQLite Database (*.sqlite *.db)",
        )
        if not save_path:
            return

        opts = DBFMigrationOptions(
            add_auto_increment_pk=self.chk_add_pk.isChecked(),
            sanitize_column_names=self.chk_sanitize.isChecked(),
            include_deleted_records=self.chk_inc_deleted.isChecked(),
            encoding=self.cmb_encoding.currentText(),
        )

        self.progress_bar.show()
        self.progress_bar.setValue(0)
        self.lbl_progress_status.show()
        self.btn_migrate_sqlite.setEnabled(False)

        self._worker = DBFMigrationWorker(
            self.txt_folder.text(),
            save_path,
            opts,
        )
        self._worker.progress.connect(self._on_migration_progress)
        self._worker.finished_migration.connect(self._on_migration_finished)
        self._worker.error.connect(self._on_migration_error)
        self._worker.start()

    def _on_migration_progress(self, table: str, curr: int, tot: int) -> None:
        """Update progress bar during background migration."""
        self.lbl_progress_status.setText(
            f"Migrando tabla '{table}': {curr:,} de {tot:,} registros..."
        )
        if tot > 0:
            self.progress_bar.setValue(int((curr / tot) * 100))

    def _on_migration_finished(self, results: list) -> None:
        """Display migration summary when completed."""
        self.progress_bar.hide()
        self.lbl_progress_status.hide()
        self.btn_migrate_sqlite.setEnabled(True)

        total_migrated = sum(r.migrated_records for r in results if not r.has_error)
        msg = (
            f"Se migraron exitosamente {len(results)} tablas con un "
            f"total de {total_migrated:,} registros."
        )
        QMessageBox.information(
            self,
            "Migración Completa",
            msg,
        )

    def _on_migration_error(self, err_msg: str) -> None:
        """Display error message if migration fails."""
        self.progress_bar.hide()
        self.lbl_progress_status.hide()
        self.btn_migrate_sqlite.setEnabled(True)
        QMessageBox.critical(self, "Error en Migración", f"Ocurrió un error al migrar:\n{err_msg}")
