"""Main Application Window for PySide6 Desktop Shell."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from backend_ide import __version__
from backend_ide.application.connection_service import ConnectionService
from backend_ide.application.query_service import ExecuteQueryService
from backend_ide.domain.sql import ColumnMetadata, QueryResult
from backend_ide.ui.components import BreadcrumbWidget, ConnectionSelector, ThemeToggleButton
from backend_ide.ui.dialogs import ConnectionDialog
from backend_ide.ui.editor import SqlEditorWidget
from backend_ide.ui.explorer import DatabaseExplorerWidget
from backend_ide.ui.results import ResultsWidget
from backend_ide.ui.theme import ThemeManager


class MainWindow(QMainWindow):
    """Main desktop application window."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Backend Development IDE v{__version__}")
        self.resize(1340, 840)

        self.connection_service = ConnectionService()
        self.query_service = ExecuteQueryService()
        self._theme_manager = ThemeManager.get_instance()
        self._setup_ui()
        self._theme_manager.apply_theme()

    def _setup_ui(self) -> None:
        """Construct application layout and widgets."""
        main_container = QWidget()
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Segmented Top Bar Toolbar
        top_bar = QWidget()
        top_bar.setObjectName("top_bar")
        top_bar.setFixedHeight(52)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(12, 8, 12, 8)
        top_layout.setSpacing(12)
        top_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Left Connection Group
        self.conn_selector = ConnectionSelector(self.connection_service)
        self.conn_selector.new_connection_requested.connect(self.open_new_connection_dialog)
        self.conn_selector.edit_connection_requested.connect(self.open_edit_connection_dialog)

        # Center Execution Group
        center_toolbar = QWidget()
        center_toolbar.setObjectName("toolbar_group")
        center_toolbar.setFixedHeight(36)
        center_layout = QHBoxLayout(center_toolbar)
        center_layout.setContentsMargins(3, 2, 3, 2)
        center_layout.setSpacing(6)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        btn_execute = QPushButton("▶️ Ejecutar")
        btn_execute.setObjectName("btn_execute")
        btn_execute.setFixedHeight(30)
        btn_execute.setToolTip("Ejecutar consulta activa (Ctrl+Enter)")

        btn_new_query = QPushButton("➕ Nueva Consulta")
        btn_er_diagram = QPushButton("🗺️ Diagrama ER")
        btn_new_query.setFixedHeight(30)
        btn_er_diagram.setFixedHeight(30)

        btn_execute.clicked.connect(self.execute_current_query)
        btn_new_query.clicked.connect(self.add_new_query_tab)

        center_layout.addWidget(btn_execute)
        center_layout.addWidget(btn_new_query)
        center_layout.addWidget(btn_er_diagram)

        # Right Theme & Settings Group
        self.theme_toggle = ThemeToggleButton()

        top_layout.addWidget(self.conn_selector)
        top_layout.addWidget(center_toolbar)
        top_layout.addStretch()
        top_layout.addWidget(self.theme_toggle)

        main_layout.addWidget(top_bar)

        # 2. Breadcrumb Navigation Context Bar
        self.breadcrumb_bar = BreadcrumbWidget()
        main_layout.addWidget(self.breadcrumb_bar)

        # 3. Main Horizontal Splitter (Sidebar Explorer | Workspace)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Sidebar (Database Explorer Widget)
        self.explorer_widget = DatabaseExplorerWidget()
        self.explorer_widget.query_requested.connect(self._on_query_requested)
        self.explorer_widget.setMinimumWidth(260)

        # Right Area (Workspace Tabs + Results Splitter)
        workspace_splitter = QSplitter(Qt.Orientation.Vertical)

        self.tabs_workspace = QTabWidget()
        self.tabs_workspace.setTabsClosable(True)
        self.tabs_workspace.tabCloseRequested.connect(self._on_tab_close_requested)

        # Initial SQL tab with QScintilla / SqlEditorWidget
        self.add_new_query_tab(
            initial_sql="-- Bienvenido a Backend Development IDE\nSELECT * FROM customers LIMIT 10;"
        )

        # Bottom Results Panel (ResultsWidget)
        self.results_widget = ResultsWidget(self.query_service)

        workspace_splitter.addWidget(self.tabs_workspace)
        workspace_splitter.addWidget(self.results_widget)
        workspace_splitter.setSizes([460, 260])

        main_splitter.addWidget(self.explorer_widget)
        main_splitter.addWidget(workspace_splitter)
        main_splitter.setSizes([280, 1060])

        main_layout.addWidget(main_splitter)
        self.setCentralWidget(main_container)

        # 4. Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_lbl_conn = QLabel(" Conectado: PostgreSQL Local (Desarrollo) ")
        self.status_lbl_python = QLabel(" Python 3.14.4 ")
        self.status_bar.addWidget(self.status_lbl_conn)
        self.status_bar.addPermanentWidget(self.status_lbl_python)

    def open_new_connection_dialog(self) -> None:
        """Open ConnectionDialog to create a new profile."""
        dialog = ConnectionDialog(
            profile=None, connection_service=self.connection_service, parent=self
        )
        if dialog.exec() == ConnectionDialog.DialogCode.Accepted:
            self.conn_selector.refresh_profiles()

    def open_edit_connection_dialog(self) -> None:
        """Open ConnectionDialog to edit selected profile."""
        profile = self.conn_selector.get_selected_profile()
        if not profile:
            return
        dialog = ConnectionDialog(
            profile=profile, connection_service=self.connection_service, parent=self
        )
        if dialog.exec() == ConnectionDialog.DialogCode.Accepted:
            self.conn_selector.refresh_profiles()

    def add_new_query_tab(self, initial_sql: str = "") -> SqlEditorWidget:
        """Add a new QScintilla SQL query editor tab to workspace."""
        tab_index = self.tabs_workspace.count() + 1
        base_title = f"Consulta-{tab_index}.sql"

        editor = SqlEditorWidget(initial_text=initial_sql)

        def on_modified(modified: bool) -> None:
            idx = self.tabs_workspace.indexOf(editor)
            if idx >= 0:
                title = f"{base_title} *" if modified else base_title
                self.tabs_workspace.setTabText(idx, title)

        editor.text_modified.connect(on_modified)

        self.tabs_workspace.addTab(editor, base_title)
        self.tabs_workspace.setCurrentWidget(editor)
        return editor

    def execute_current_query(self) -> None:
        """Execute SQL query from active workspace tab."""
        current_widget = self.tabs_workspace.currentWidget()
        if not isinstance(current_widget, SqlEditorWidget):
            return

        sql_text = current_widget.get_sql_text()
        if not sql_text:
            return

        self.results_output = sql_text
        dummy_result = QueryResult(
            columns=[
                ColumnMetadata(name="id", data_type="INT"),
                ColumnMetadata(name="name", data_type="VARCHAR"),
                ColumnMetadata(name="email", data_type="VARCHAR"),
            ],
            rows=[
                {"id": 1, "name": "Alice Developer", "email": "alice@example.com"},
                {"id": 2, "name": "Bob Architect", "email": "bob@example.com"},
            ],
            execution_time_ms=11.8,
            rows_affected=2,
            has_error=False,
        )
        self.results_widget.display_result(dummy_result)

    def _on_query_requested(self, sql_query: str) -> None:
        """Handle generated SQL query emitted by Explorer."""
        current_widget = self.tabs_workspace.currentWidget()
        if isinstance(current_widget, SqlEditorWidget):
            current_widget.set_sql_text(sql_query)
        else:
            self.add_new_query_tab(initial_sql=sql_query)

    def _on_tab_close_requested(self, index: int) -> None:
        """Close tab at requested index if more than 1 tab exists."""
        if self.tabs_workspace.count() > 1:
            self.tabs_workspace.removeTab(index)
