"""Database Explorer Widget with Search Filter, Header Action Bar, and Context Actions."""

import qtawesome as qta
from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from backend_ide.domain.schema import Column, DatabaseSchema
from backend_ide.ui.explorer.tree_items import ExplorerNodeType, ExplorerTreeItem
from backend_ide.ui.theme import ThemeManager


class DatabaseExplorerWidget(QWidget):
    """Sidebar Widget for inspecting database hierarchy with filtering and context menus."""

    query_requested = Signal(str)  # Emits generated SQL query string
    structure_requested = Signal(str, str)  # Emits (schema_name, table_name)
    refresh_requested = Signal()
    database_changed = Signal(str)
    add_connection_requested = Signal()
    table_expansion_requested = Signal(str, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar_container")
        self.setMinimumWidth(280)
        self._schema_model: DatabaseSchema | None = None
        self._theme_manager = ThemeManager.get_instance()
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Construct Explorer layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # 1. Header Toolbar Bar
        self.header = QWidget()
        self.header.setObjectName("sidebar_header")
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(4, 2, 4, 2)
        header_layout.setSpacing(6)

        self.lbl_title = QLabel("DATABASE EXPLORER")
        self.lbl_title.setObjectName("sidebar_title")
        self.lbl_entities_count = QLabel("0")
        self.lbl_entities_count.setObjectName("count_badge")
        self.lbl_entities_count.setAlignment(Qt.AlignmentFlag.AlignCenter)

        header_layout.addWidget(self.lbl_title)
        header_layout.addWidget(self.lbl_entities_count)
        header_layout.addStretch()

        # 2. Active database selector
        self.database_row = QWidget()
        database_layout = QHBoxLayout(self.database_row)
        database_layout.setContentsMargins(0, 0, 0, 0)
        database_layout.setSpacing(4)

        self.cmb_database = QComboBox()
        self.cmb_database.setFixedHeight(32)
        self.cmb_database.setToolTip("Cambiar la base de datos activa")
        self.cmb_database.currentTextChanged.connect(self._emit_database_changed)

        self.btn_refresh = QPushButton()
        self.btn_refresh.setObjectName("icon_button")
        self.btn_refresh.setFixedSize(32, 32)
        self.btn_refresh.setToolTip("Refrescar estructura")
        self.btn_refresh.clicked.connect(self.refresh_requested.emit)

        self.btn_add = QPushButton()
        self.btn_add.setObjectName("icon_button")
        self.btn_add.setFixedSize(32, 32)
        self.btn_add.setToolTip("Nueva conexión")
        self.btn_add.clicked.connect(self.add_connection_requested.emit)

        database_layout.addWidget(self.cmb_database, 1)
        header_layout.addWidget(self.btn_refresh)
        header_layout.addWidget(self.btn_add)

        # 3. Filter Search Box
        self.txt_filter = QLineEdit()
        self.txt_filter.setObjectName("search_explorer")
        self.txt_filter.setFixedHeight(32)
        self.txt_filter.setPlaceholderText("Filtrar tablas…")
        self.txt_filter.setClearButtonEnabled(True)
        self._filter_action = self.txt_filter.addAction(
            qta.icon("fa6s.filter"), QLineEdit.ActionPosition.TrailingPosition
        )
        self.txt_filter.textChanged.connect(self.filter_items)

        # 4. State feedback
        self.lbl_state = QLabel()
        self.lbl_state.setWordWrap(True)
        self.lbl_state.hide()

        # 5. Tree Widget
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(16)
        self.tree.setStyleSheet(
            "QTreeWidget { border: none; border-radius: 0; padding: 2px; }"
            "QTreeWidget::item { padding: 2px 3px; min-height: 18px; }"
        )
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.itemExpanded.connect(self._on_item_expanded)

        layout.addWidget(self.header)
        layout.addWidget(self.database_row)
        layout.addWidget(self.txt_filter)
        layout.addWidget(self.lbl_state)
        layout.addWidget(self.tree)

        self._theme_manager.theme_changed.connect(self._update_icons)
        self._update_icons()

    def _update_icons(self, _mode: str | None = None) -> None:
        """Regenerate compact icons from the active centralized palette."""
        palette = self._theme_manager.current_palette
        self.btn_refresh.setIcon(qta.icon("fa6s.arrows-rotate", color=palette.text_secondary))
        self.btn_add.setIcon(qta.icon("fa6s.plus", color=palette.text_secondary))
        self._filter_action.setIcon(qta.icon("fa6s.filter", color=palette.text_muted))

    def _set_state_status(self, status: str) -> None:
        """Apply a semantic state property so global QSS owns its colors."""
        self.lbl_state.setProperty("status", status)
        self.lbl_state.style().unpolish(self.lbl_state)
        self.lbl_state.style().polish(self.lbl_state)

    def _emit_database_changed(self, database_name: str) -> None:
        """Emit only meaningful database selections."""
        if database_name:
            self.database_changed.emit(database_name)

    def set_databases(self, database_names: list[str] | tuple[str, ...], selected: str) -> None:
        """Replace database selector values without triggering a connection switch."""
        self.cmb_database.blockSignals(True)
        self.cmb_database.clear()
        self.cmb_database.addItems(list(database_names))
        selected_index = self.cmb_database.findText(selected)
        if selected_index >= 0:
            self.cmb_database.setCurrentIndex(selected_index)
        self.cmb_database.blockSignals(False)

    def set_controls_enabled(self, enabled: bool) -> None:
        """Prevent overlapping refreshes and database switches."""
        self.cmb_database.setEnabled(enabled)
        self.btn_refresh.setEnabled(enabled)
        self.btn_add.setEnabled(enabled)

    def set_loading(self, preserve_tree: bool = False) -> None:
        """Show progress during first load while preserving useful refreshed data."""
        self.lbl_state.setText("Cargando estructura…")
        self._set_state_status("loading")
        self.lbl_state.show()
        if not preserve_tree:
            self.tree.clear()
            QTreeWidgetItem(self.tree, ["Cargando estructura…"])
            self.lbl_entities_count.setText("0")

    def show_error(self, message: str, preserve_tree: bool = False) -> None:
        """Show an actionable failure without erasing the last successful tree."""
        self.lbl_state.setText(message)
        self._set_state_status("error")
        self.lbl_state.show()
        if not preserve_tree:
            self.tree.clear()
            QTreeWidgetItem(self.tree, [message])
            self.lbl_entities_count.setText("0")

    def load_schema_model(self, connection_name: str, schema_model: DatabaseSchema) -> None:
        """Populate explorer tree from Universal Schema Model."""
        self._schema_model = schema_model
        self.tree.clear()
        self.lbl_state.hide()
        table_count = sum(len(schema.tables) for schema in schema_model.schemas)
        self.lbl_entities_count.setText(str(table_count))

        for s in schema_model.schemas:
            schema_item = ExplorerTreeItem(
                ExplorerNodeType.SCHEMA,
                s.name,
                node_data={"schema_name": s.name},
            )
            schema_item.is_loaded = True
            for table in s.tables:
                table_item = ExplorerTreeItem(
                    ExplorerNodeType.TABLE,
                    table.name,
                    node_data={"schema": s.name, "table": table.name},
                    parent=schema_item,
                )
                QTreeWidgetItem(table_item, ["Expandir para ver campos"])
            self.tree.addTopLevelItem(schema_item)

        if self.tree.topLevelItemCount() == 0:
            QTreeWidgetItem(self.tree, ["No hay esquemas visibles"])
        else:
            self.tree.topLevelItem(0).setExpanded(True)

    def _on_item_expanded(self, item: QTreeWidgetItem) -> None:
        """Handle lazy loading on item expansion."""
        if not isinstance(item, ExplorerTreeItem) or item.is_loaded:
            return

        if item.node_type == ExplorerNodeType.TABLE:
            item.takeChildren()
            QTreeWidgetItem(item, ["Cargando campos…"])
            schema_name = item.node_data.get("schema", "public")
            table_name = item.node_data.get("table", "")
            self.table_expansion_requested.emit(schema_name, table_name)
            return

        if item.node_type == ExplorerNodeType.SCHEMA and self._schema_model:
            item.takeChildren()  # Remove dummy child
            schema_name = item.node_data.get("schema_name", "public")
            schema_obj = self._schema_model.get_schema(schema_name)

            if schema_obj:
                # 1. Tables Group
                tables_group = ExplorerTreeItem(ExplorerNodeType.TABLE_GROUP, "Tables", parent=item)
                for t in schema_obj.tables:
                    ExplorerTreeItem(
                        ExplorerNodeType.TABLE,
                        t.name,
                        node_data={"schema": schema_name, "table": t.name},
                        parent=tables_group,
                    )

                # 2. Views Group
                if schema_obj.views:
                    views_group = ExplorerTreeItem(
                        ExplorerNodeType.VIEW_GROUP, "Views", parent=item
                    )
                    for v in schema_obj.views:
                        ExplorerTreeItem(
                            ExplorerNodeType.VIEW,
                            v.name,
                            node_data={"schema": schema_name, "view": v.name},
                            parent=views_group,
                        )

                # 3. Functions Group
                if schema_obj.functions:
                    fn_group = ExplorerTreeItem(
                        ExplorerNodeType.FUNCTION_GROUP, "Functions", parent=item
                    )
                    for fn in schema_obj.functions:
                        ExplorerTreeItem(
                            ExplorerNodeType.FUNCTION,
                            fn.name,
                            node_data={"schema": schema_name, "function": fn.name},
                            parent=fn_group,
                        )

            item.is_loaded = True

    def load_table_columns(
        self,
        schema_name: str,
        table_name: str,
        columns: list[Column],
    ) -> None:
        """Replace a table's loading row with typed column entries."""
        table_item = self._find_table_item(schema_name, table_name)
        if table_item is None:
            return
        table_item.takeChildren()
        for column in columns:
            attributes = [column.native_type]
            if column.is_primary_key:
                attributes.append("PK")
            if not column.is_nullable:
                attributes.append("NOT NULL")
            column_item = ExplorerTreeItem(
                ExplorerNodeType.COLUMN,
                f"{column.name}   {' · '.join(attributes)}",
                node_data={"schema": schema_name, "table": table_name, "column": column.name},
                parent=table_item,
            )
            column_item.setToolTip(0, f"{column.name}: {' · '.join(attributes)}")
        if not columns:
            QTreeWidgetItem(table_item, ["Sin campos visibles"])
        table_item.is_loaded = True
        table_item.setExpanded(True)

    def show_table_columns_error(self, schema_name: str, table_name: str, message: str) -> None:
        """Keep a field-loading error scoped to its table row."""
        table_item = self._find_table_item(schema_name, table_name)
        if table_item is None:
            return
        table_item.takeChildren()
        QTreeWidgetItem(table_item, [f"Error: {message}"])
        table_item.is_loaded = False

    def _find_table_item(self, schema_name: str, table_name: str) -> ExplorerTreeItem | None:
        """Find one table node in the compact schema/table tree."""
        for schema_index in range(self.tree.topLevelItemCount()):
            schema_item = self.tree.topLevelItem(schema_index)
            if not isinstance(schema_item, ExplorerTreeItem):
                continue
            if schema_item.node_data.get("schema_name") != schema_name:
                continue
            for table_index in range(schema_item.childCount()):
                table_item = schema_item.child(table_index)
                if (
                    isinstance(table_item, ExplorerTreeItem)
                    and table_item.node_type == ExplorerNodeType.TABLE
                    and table_item.node_data.get("table") == table_name
                ):
                    return table_item
        return None

    def filter_items(self, text: str) -> None:
        """Filter tree items by matching search text."""
        query_text = text.lower().strip()

        def set_visible_recursive(item: QTreeWidgetItem) -> bool:
            match = False
            item_text = item.text(0).lower()

            if not query_text or query_text in item_text:
                match = True

            child_match = False
            for i in range(item.childCount()):
                if set_visible_recursive(item.child(i)):
                    child_match = True

            is_visible = match or child_match
            item.setHidden(not is_visible)
            if is_visible and query_text and item.childCount() > 0:
                item.setExpanded(True)
            return is_visible

        for idx in range(self.tree.topLevelItemCount()):
            set_visible_recursive(self.tree.topLevelItem(idx))

    def _show_context_menu(self, pos: QPoint) -> None:
        """Display context menu for selected tree item."""
        item = self.tree.itemAt(pos)
        if not isinstance(item, ExplorerTreeItem):
            return

        menu = QMenu(self)
        palette = self._theme_manager.current_palette

        if item.node_type == ExplorerNodeType.TABLE:
            schema_name = item.node_data.get("schema", "public")
            table_name = item.node_data.get("table", "")
            qual_name = f"{schema_name}.{table_name}"

            act_open_data = menu.addAction(
                qta.icon("fa6s.table", color=palette.accent), "Abrir datos (SELECT 100)"
            )
            act_open_struct = menu.addAction(
                qta.icon("fa6s.circle-info", color=palette.text_secondary), "Ver estructura"
            )
            menu.addSeparator()

            menu_gen = QMenu("Generar consulta SQL", menu)
            menu_gen.setIcon(qta.icon("fa6s.code", color=palette.info))
            menu.addMenu(menu_gen)
            act_gen_select = menu_gen.addAction("SELECT")
            act_gen_insert = menu_gen.addAction("INSERT")
            act_gen_update = menu_gen.addAction("UPDATE")
            act_gen_delete = menu_gen.addAction("DELETE")

            menu.addSeparator()
            act_copy = menu.addAction(
                qta.icon("fa6s.copy", color=palette.text_secondary), "Copiar nombre de tabla"
            )

            action = menu.exec(self.tree.viewport().mapToGlobal(pos))

            if action == act_open_data:
                self.query_requested.emit(f"SELECT * FROM {qual_name} LIMIT 100;")
            elif action == act_open_struct:
                self.structure_requested.emit(schema_name, table_name)
            elif action == act_gen_select:
                self.query_requested.emit(self._generate_select_sql(schema_name, table_name))
            elif action == act_gen_insert:
                self.query_requested.emit(self._generate_insert_sql(schema_name, table_name))
            elif action == act_gen_update:
                self.query_requested.emit(self._generate_update_sql(schema_name, table_name))
            elif action == act_gen_delete:
                self.query_requested.emit(f"DELETE FROM {qual_name} WHERE id = 1;")
            elif action == act_copy:
                QApplication.clipboard().setText(qual_name)

        elif item.node_type in (ExplorerNodeType.CONNECTION, ExplorerNodeType.SCHEMA):
            act_refresh = menu.addAction(
                qta.icon("fa6s.arrows-rotate", color=palette.text_secondary),
                "Refrescar metadatos",
            )
            action = menu.exec(self.tree.viewport().mapToGlobal(pos))
            if action == act_refresh:
                self.refresh_requested.emit()

    def _generate_select_sql(self, schema_name: str, table_name: str) -> str:
        """Generate formatted SELECT query for table."""
        if not self._schema_model:
            return f"SELECT * FROM {schema_name}.{table_name};"

        t = self._schema_model.find_table(table_name, schema_name)
        if not t:
            return f"SELECT * FROM {schema_name}.{table_name};"

        cols_str = ",\n    ".join([c.name for c in t.columns])
        return f"SELECT\n    {cols_str}\nFROM {schema_name}.{table_name};"

    def _generate_insert_sql(self, schema_name: str, table_name: str) -> str:
        """Generate formatted INSERT template query for table."""
        if not self._schema_model:
            return f"INSERT INTO {schema_name}.{table_name} DEFAULT VALUES;"

        t = self._schema_model.find_table(table_name, schema_name)
        if not t:
            return f"INSERT INTO {schema_name}.{table_name} DEFAULT VALUES;"

        cols = [c.name for c in t.columns if not c.is_auto_increment]
        cols_str = ", ".join(cols)
        vals_str = ", ".join([f":{c}" for c in cols])
        return f"INSERT INTO {schema_name}.{table_name} ({cols_str})\nVALUES ({vals_str});"

    def _generate_update_sql(self, schema_name: str, table_name: str) -> str:
        """Generate formatted UPDATE template query for table."""
        if not self._schema_model:
            return f"UPDATE {schema_name}.{table_name} SET column = value WHERE condition;"

        t = self._schema_model.find_table(table_name, schema_name)
        if not t:
            return f"UPDATE {schema_name}.{table_name} SET column = value WHERE condition;"

        cols = [c.name for c in t.columns if not c.is_primary_key]
        set_str = ",\n    ".join([f"{c} = :{c}" for c in cols])
        pk_cols = t.primary_key.column_names if t.primary_key else ["id"]
        where_str = " AND ".join([f"{pk} = :{pk}" for pk in pk_cols])
        return f"UPDATE {schema_name}.{table_name}\nSET\n    {set_str}\nWHERE {where_str};"
