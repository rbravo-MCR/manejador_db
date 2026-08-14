"""Database Explorer Widget with Search Filter, Header Action Bar, and Context Actions."""

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
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

from backend_ide.domain.schema import DatabaseSchema
from backend_ide.ui.explorer.tree_items import ExplorerNodeType, ExplorerTreeItem


class DatabaseExplorerWidget(QWidget):
    """Sidebar Widget for inspecting database hierarchy with filtering and context menus."""

    query_requested = Signal(str)  # Emits generated SQL query string
    structure_requested = Signal(str, str)  # Emits (schema_name, table_name)
    refresh_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar_container")
        self._schema_model: DatabaseSchema | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Construct Explorer layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # 1. Header Toolbar Bar
        header = QWidget()
        header.setObjectName("sidebar_header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(4, 2, 4, 2)

        lbl_title = QLabel("DATABASE EXPLORER")
        lbl_title.setStyleSheet("font-weight: bold; font-size: 11px; color: #a6adc8;")

        btn_refresh = QPushButton("🔄")
        btn_refresh.setToolTip("Refrescar Esquemas")
        btn_refresh.setStyleSheet("padding: 2px 6px; font-size: 11px;")
        btn_refresh.clicked.connect(self.refresh_requested.emit)

        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(btn_refresh)

        # 2. Filter Search Box
        self.txt_filter = QLineEdit()
        self.txt_filter.setObjectName("search_explorer")
        self.txt_filter.setPlaceholderText("🔍 Filtrar tablas, vistas, columnas...")
        self.txt_filter.setClearButtonEnabled(True)
        self.txt_filter.textChanged.connect(self.filter_items)

        # 3. Tree Widget
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.itemExpanded.connect(self._on_item_expanded)

        layout.addWidget(header)
        layout.addWidget(self.txt_filter)
        layout.addWidget(self.tree)

    def load_schema_model(self, connection_name: str, schema_model: DatabaseSchema) -> None:
        """Populate explorer tree from Universal Schema Model."""
        self._schema_model = schema_model
        self.tree.clear()

        conn_item = ExplorerTreeItem(
            ExplorerNodeType.CONNECTION,
            connection_name,
            node_data={"engine": schema_model.engine_name},
        )
        db_item = ExplorerTreeItem(
            ExplorerNodeType.DATABASE,
            schema_model.database_name,
            parent=conn_item,
        )

        for s in schema_model.schemas:
            schema_item = ExplorerTreeItem(
                ExplorerNodeType.SCHEMA,
                s.name,
                node_data={"schema_name": s.name},
                parent=db_item,
            )
            # Add dummy child to show expand arrow for lazy loading
            QTreeWidgetItem(schema_item, ["Loading..."])

        self.tree.addTopLevelItem(conn_item)
        conn_item.setExpanded(True)
        db_item.setExpanded(True)

    def _on_item_expanded(self, item: QTreeWidgetItem) -> None:
        """Handle lazy loading on item expansion."""
        if not isinstance(item, ExplorerTreeItem) or item.is_loaded:
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

        if item.node_type == ExplorerNodeType.TABLE:
            schema_name = item.node_data.get("schema", "public")
            table_name = item.node_data.get("table", "")
            qual_name = f"{schema_name}.{table_name}"

            act_open_data = menu.addAction("📊 Abrir Datos (SELECT 100)")
            act_open_struct = menu.addAction("🔍 Ver Estructura")
            menu.addSeparator()

            menu_gen = menu.addMenu("📝 Generar Consulta SQL")
            act_gen_select = menu_gen.addAction("SELECT")
            act_gen_insert = menu_gen.addAction("INSERT")
            act_gen_update = menu_gen.addAction("UPDATE")
            act_gen_delete = menu_gen.addAction("DELETE")

            menu.addSeparator()
            act_copy = menu.addAction("📋 Copiar Nombre de Tabla")

            action = menu.exec_(self.tree.viewport().mapToGlobal(pos))

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
            act_refresh = menu.addAction("🔄 Refrescar Metadatos")
            action = menu.exec_(self.tree.viewport().mapToGlobal(pos))
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
