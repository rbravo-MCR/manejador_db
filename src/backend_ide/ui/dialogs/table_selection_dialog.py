"""Interactive Table Selection Dialog for ER Diagram Filtering."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

if TYPE_CHECKING:
    from backend_ide.domain.schema.models import DatabaseSchema


class TableSelectionDialog(QDialog):
    """Dialog allowing users to filter and pick specific tables to display in the ER diagram."""

    def __init__(
        self,
        schema: DatabaseSchema,
        selected_tables: set[str] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.schema = schema
        self.setWindowTitle("Seleccionar Tablas para el Diagrama ER")
        self.resize(520, 560)
        self.setStyleSheet(
            "QDialog { background-color: #ffffff; color: #0f172a; }\n"
            "QLabel { color: #334155; font-size: 12px; }\n"
            "QLineEdit { background-color: #f8fafc; border: 1px solid #cbd5e1; "
            "border-radius: 4px; padding: 4px 8px; color: #0f172a; }\n"
            "QListWidget { background-color: #f8fafc; border: 1px solid #cbd5e1; "
            "border-radius: 6px; padding: 4px; color: #0f172a; }\n"
            "QListWidget::item { padding: 4px; border-radius: 4px; }\n"
            "QListWidget::item:hover { background-color: #eff6ff; }\n"
            "QPushButton { background-color: #f8fafc; border: 1px solid #cbd5e1; "
            "border-radius: 4px; padding: 4px 10px; color: #334155; font-size: 12px; }\n"
            "QPushButton:hover { background-color: #f1f5f9; color: #0f172a; }\n"
        )

        self._all_tables = [t for s in schema.schemas for t in s.tables]
        self._table_map = {t.name: t for t in self._all_tables}
        self._initial_selected = (
            selected_tables if selected_tables is not None else {t.name for t in self._all_tables}
        )

        self._setup_ui()
        self._populate_list()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Header Info
        header_lbl = QLabel(
            "Selecciona qué tablas deseas visualizar en el diagrama ER.\n"
            "Puedes aislar módulos específicos (ej. oficinas, reservas, clientes)."
        )
        header_lbl.setStyleSheet("color: #64748b; font-size: 12px;")
        layout.addWidget(header_lbl)

        # Search filter
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Filtrar tablas por nombre...")
        self.txt_search.textChanged.connect(self._filter_list)
        layout.addWidget(self.txt_search)

        # Quick action buttons
        actions_layout = QHBoxLayout()
        self.btn_select_all = QPushButton("Seleccionar Todas")
        self.btn_select_all.clicked.connect(self._select_all)

        self.btn_select_none = QPushButton("Deseleccionar Todas")
        self.btn_select_none.clicked.connect(self._select_none)

        self.btn_select_fk_only = QPushButton("Solo con Relaciones (FK)")
        self.btn_select_fk_only.clicked.connect(self._select_fks_only)

        actions_layout.addWidget(self.btn_select_all)
        actions_layout.addWidget(self.btn_select_none)
        actions_layout.addWidget(self.btn_select_fk_only)
        layout.addLayout(actions_layout)

        # Tables List
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        # Include connected tables helper checkbox
        self.chk_auto_include_fks = QCheckBox(
            "🔗 Incluir automáticamente tablas relacionadas (padres e hijas)"
        )
        self.chk_auto_include_fks.setStyleSheet(
            "QCheckBox { color: #2563eb; font-weight: 500; font-size: 12px; }"
        )
        self.chk_auto_include_fks.setChecked(True)
        layout.addWidget(self.chk_auto_include_fks)

        # Stats label
        self.lbl_count = QLabel()
        self.lbl_count.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 500;")
        layout.addWidget(self.lbl_count)

        # Dialog Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Aplicar al Diagrama")
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _populate_list(self) -> None:
        self.list_widget.clear()

        # Build FK connection map
        fks_count: dict[str, int] = {t.name: len(t.foreign_keys) for t in self._all_tables}
        for t in self._all_tables:
            for fk in t.foreign_keys:
                if fk.target_table in fks_count:
                    fks_count[fk.target_table] += 1

        for table in sorted(self._all_tables, key=lambda t: t.name):
            fk_num = fks_count.get(table.name, 0)
            fk_badge = f"({fk_num} relaciones)" if fk_num > 0 else "(aislada)"

            cols_count = len(table.columns)
            display_text = f"📋 {table.name}  —  {cols_count} cols, {fk_badge}"

            item = QListWidgetItem(display_text, self.list_widget)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setData(Qt.ItemDataRole.UserRole, table.name)

            if table.name in self._initial_selected:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)

        self.list_widget.itemChanged.connect(self._on_item_changed)
        self._update_counter()

    def _filter_list(self, query: str) -> None:
        clean = query.strip().lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            table_name = item.data(Qt.ItemDataRole.UserRole)
            matches = clean in table_name.lower()
            item.setHidden(not matches)

    def _select_all(self) -> None:
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if not item.isHidden():
                item.setCheckState(Qt.CheckState.Checked)
        self._update_counter()

    def _select_none(self) -> None:
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if not item.isHidden():
                item.setCheckState(Qt.CheckState.Unchecked)
        self._update_counter()

    def _select_fks_only(self) -> None:
        relational_tables: set[str] = set()
        for t in self._all_tables:
            if t.foreign_keys:
                relational_tables.add(t.name)
                for fk in t.foreign_keys:
                    relational_tables.add(fk.target_table)

        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            name = item.data(Qt.ItemDataRole.UserRole)
            if name in relational_tables:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)
        self._update_counter()

    def _on_item_changed(self, item: QListWidgetItem) -> None:
        self._update_counter()

    def _update_counter(self) -> None:
        checked = 0
        total = self.list_widget.count()
        for i in range(total):
            if self.list_widget.item(i).checkState() == Qt.CheckState.Checked:
                checked += 1
        self.lbl_count.setText(f"Tablas seleccionadas: {checked} de {total}")

    def get_selected_table_names(self) -> set[str]:
        """Return the set of selected table names, including FK neighbors if requested."""
        selected: set[str] = set()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected.add(item.data(Qt.ItemDataRole.UserRole))

        if self.chk_auto_include_fks.isChecked():
            # Include direct parents and children
            expanded = set(selected)
            for t in self._all_tables:
                if t.name in selected:
                    for fk in t.foreign_keys:
                        expanded.add(fk.target_table)
                else:
                    for fk in t.foreign_keys:
                        if fk.target_table in selected:
                            expanded.add(t.name)
            return expanded

        return selected
