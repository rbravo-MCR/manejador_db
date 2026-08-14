"""Main Application Window for PySide6 Desktop Shell."""

import qtawesome as qta
from PySide6.QtCore import Qt, QThreadPool, QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QGridLayout,
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
from backend_ide.domain.connection import ConnectionProfile
from backend_ide.domain.sql import QueryRequest, QueryResult
from backend_ide.infrastructure.database.contracts import DatabaseConnection
from backend_ide.infrastructure.database.schema_inspection_worker import (
    DatabaseInspectionResult,
    SchemaInspectionWorker,
)
from backend_ide.infrastructure.database.table_columns_worker import TableColumnsWorker
from backend_ide.infrastructure.logging import get_logger
from backend_ide.ui.components import BreadcrumbWidget, ConnectionSelector, ThemeToggleButton
from backend_ide.ui.dialogs import ConnectionDialog
from backend_ide.ui.editor import SqlEditorWidget
from backend_ide.ui.explorer import DatabaseExplorerWidget
from backend_ide.ui.results import ResultsWidget
from backend_ide.ui.theme import ThemeManager

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """Main desktop application window."""

    def __init__(
        self,
        parent=None,
        *,
        connection_service: ConnectionService | None = None,
        thread_pool: QThreadPool | None = None,
        auto_load_profile: bool = True,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Backend Development IDE v{__version__}")
        self.resize(1340, 840)
        self.setMinimumSize(1100, 700)

        self._thread_pool = thread_pool or QThreadPool.globalInstance()
        self.connection_service = connection_service or ConnectionService()
        self.query_service = ExecuteQueryService(self._thread_pool)
        self._active_profile: ConnectionProfile | None = None
        self._active_database: str | None = None
        self._active_connection: DatabaseConnection | None = None
        self._candidate_profile: ConnectionProfile | None = None
        self._candidate_database: str | None = None
        self._candidate_connection: DatabaseConnection | None = None
        self._database_names: tuple[str, ...] = ()
        self._inspection_worker: SchemaInspectionWorker | None = None
        self._column_workers: dict[tuple[str, str], TableColumnsWorker] = {}
        self._query_worker = None
        self._is_inspecting = False
        self._theme_manager = ThemeManager.get_instance()
        self._setup_ui()
        self._theme_manager.apply_theme()
        if auto_load_profile:
            QTimer.singleShot(0, self._load_initial_profile)

    def _setup_ui(self) -> None:
        """Construct application layout and widgets."""
        main_container = QWidget()
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Segmented Top Bar Toolbar
        self.top_bar = QWidget()
        self.top_bar.setObjectName("top_bar")
        self.top_bar.setFixedHeight(52)
        top_layout = QGridLayout(self.top_bar)
        top_layout.setContentsMargins(12, 8, 12, 8)
        top_layout.setHorizontalSpacing(12)
        top_layout.setVerticalSpacing(0)
        top_layout.setColumnStretch(0, 1)
        top_layout.setColumnStretch(1, 0)
        top_layout.setColumnStretch(2, 1)

        # Left Connection Group
        self.conn_selector = ConnectionSelector(self.connection_service)
        self.conn_selector.new_connection_requested.connect(self.open_new_connection_dialog)
        self.conn_selector.edit_connection_requested.connect(self.open_edit_connection_dialog)

        # Center Execution Group
        self.query_toolbar = QWidget()
        self.query_toolbar.setObjectName("toolbar_group")
        self.query_toolbar.setFixedHeight(36)
        center_layout = QHBoxLayout(self.query_toolbar)
        center_layout.setContentsMargins(3, 2, 3, 2)
        center_layout.setSpacing(6)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.btn_execute = QPushButton("Ejecutar")
        self.btn_execute.setObjectName("btn_execute")
        self.btn_execute.setFixedHeight(32)
        self.btn_execute.setToolTip("Ejecutar consulta activa (Ctrl+Enter)")

        self.btn_new_query = QPushButton("Nueva consulta")
        self.btn_er_diagram = QPushButton("Diagrama ER")
        self.btn_new_query.setFixedHeight(32)
        self.btn_er_diagram.setFixedHeight(32)
        self.btn_er_diagram.setEnabled(False)
        self.btn_er_diagram.setToolTip("Disponible cuando se implemente el flujo de diagramas ER")

        self.btn_execute.clicked.connect(self.execute_current_query)
        self.btn_new_query.clicked.connect(self.add_new_query_tab)

        center_layout.addWidget(self.btn_execute)
        center_layout.addWidget(self.btn_new_query)
        center_layout.addWidget(self.btn_er_diagram)

        # Right Theme & Settings Group
        self.theme_toggle = ThemeToggleButton()

        top_layout.addWidget(
            self.conn_selector,
            0,
            0,
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        top_layout.addWidget(self.query_toolbar, 0, 1, alignment=Qt.AlignmentFlag.AlignCenter)
        top_layout.addWidget(
            self.theme_toggle,
            0,
            2,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        self._theme_manager.theme_changed.connect(self._update_toolbar_icons)
        self._update_toolbar_icons()

        main_layout.addWidget(self.top_bar)

        # 2. Breadcrumb Navigation Context Bar
        self.breadcrumb_bar = BreadcrumbWidget()
        main_layout.addWidget(self.breadcrumb_bar)

        # 3. Main Horizontal Splitter (Sidebar Explorer | Workspace)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Sidebar (Database Explorer Widget)
        self.explorer_widget = DatabaseExplorerWidget()
        self.explorer_widget.query_requested.connect(self._on_query_requested)
        self.explorer_widget.database_changed.connect(self._on_database_changed)
        self.explorer_widget.refresh_requested.connect(self._refresh_active_database)
        self.explorer_widget.add_connection_requested.connect(self.open_new_connection_dialog)
        self.explorer_widget.table_expansion_requested.connect(self._on_table_expansion_requested)
        self.explorer_widget.setMinimumWidth(280)

        # Right Area (Workspace Tabs + Results Splitter)
        self.workspace_splitter = QSplitter(Qt.Orientation.Vertical)

        self.tabs_workspace = QTabWidget()
        self.tabs_workspace.setMinimumHeight(240)
        self.tabs_workspace.setTabsClosable(True)
        self.tabs_workspace.tabCloseRequested.connect(self._on_tab_close_requested)

        # Initial SQL tab with QScintilla / SqlEditorWidget
        self.add_new_query_tab(
            initial_sql="-- Bienvenido a Backend Development IDE\nSELECT * FROM customers LIMIT 10;"
        )

        # Bottom Results Panel (ResultsWidget)
        self.results_widget = ResultsWidget(self.query_service)
        self.results_widget.setMinimumHeight(180)

        self.workspace_splitter.addWidget(self.tabs_workspace)
        self.workspace_splitter.addWidget(self.results_widget)
        self.workspace_splitter.setSizes([455, 245])
        self.workspace_splitter.setStretchFactor(0, 13)
        self.workspace_splitter.setStretchFactor(1, 7)
        self.workspace_splitter.setCollapsible(0, False)
        self.workspace_splitter.setCollapsible(1, False)

        self.main_splitter.addWidget(self.explorer_widget)
        self.main_splitter.addWidget(self.workspace_splitter)
        self.main_splitter.setSizes([340, 1000])
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setCollapsible(0, False)
        self.main_splitter.setCollapsible(1, False)

        main_layout.addWidget(self.main_splitter)
        self.setCentralWidget(main_container)

        # 4. Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_lbl_conn = QLabel(" Sin conexión ")
        self.status_lbl_python = QLabel(" Python 3.14.4 ")
        self.status_bar.addWidget(self.status_lbl_conn)
        self.status_bar.addPermanentWidget(self.status_lbl_python)

        self.breadcrumb_bar.set_path("Sin conexión", "—", "—")
        self.conn_selector.connection_changed.connect(self._on_profile_changed)

    def _update_toolbar_icons(self, _mode: str | None = None) -> None:
        """Keep command icons readable when the centralized theme changes."""
        palette = self._theme_manager.current_palette
        self.btn_execute.setIcon(qta.icon("fa6s.play", color="#11111b"))
        self.btn_new_query.setIcon(qta.icon("fa6s.file-circle-plus", color=palette.text_primary))
        self.btn_er_diagram.setIcon(qta.icon("fa6s.diagram-project", color=palette.text_muted))

    def _load_initial_profile(self) -> None:
        """Inspect the first saved profile when the desktop starts."""
        if not self.connection_service.list_profiles():
            return
        profile = self.conn_selector.get_selected_profile()
        if profile:
            self._load_profile(profile)

    def _on_profile_changed(self, profile_id: str) -> None:
        """Load the database stored in a user-selected profile."""
        if self._is_inspecting:
            return
        profile = self.connection_service.get_profile(profile_id)
        if profile:
            self._load_profile(profile)

    def _load_profile(self, profile: ConnectionProfile) -> None:
        """Start initial database discovery for a profile."""
        self._start_inspection(profile, profile.database, discover_databases=True)

    def _start_inspection(
        self,
        profile: ConnectionProfile,
        database_name: str,
        *,
        discover_databases: bool,
    ) -> None:
        """Queue a candidate connection and metadata inspection."""
        if self._is_inspecting:
            return

        self._is_inspecting = True
        self._candidate_profile = profile
        self._candidate_database = database_name
        self._candidate_connection = self.connection_service.build_connection(
            profile,
            database_name=database_name,
        )
        preserve_tree = self._active_connection is not None
        self.explorer_widget.set_loading(preserve_tree=preserve_tree)
        self.explorer_widget.set_controls_enabled(False)
        self.conn_selector.setEnabled(False)
        self.status_lbl_conn.setText(f" Cargando: {profile.name} / {database_name} ")

        known_names = None if discover_databases else self._database_names
        worker = SchemaInspectionWorker(self._candidate_connection, known_names)
        worker.signals.succeeded.connect(self._on_inspection_succeeded)
        worker.signals.failed.connect(self._on_inspection_failed)
        worker.signals.finished.connect(self._on_inspection_finished)
        self._inspection_worker = worker
        self._thread_pool.start(worker)

    def _on_inspection_succeeded(self, result: DatabaseInspectionResult) -> None:
        """Atomically promote inspected metadata and its candidate connection."""
        profile = self._candidate_profile
        candidate = self._candidate_connection
        if profile is None or candidate is None:
            return

        previous_connection = self._active_connection
        self._active_profile = profile
        self._active_database = result.schema.database_name
        self._active_connection = candidate
        names = result.database_names
        if result.schema.database_name not in names:
            names = tuple(sorted((*names, result.schema.database_name)))
        self._database_names = names

        self.explorer_widget.set_databases(names, result.schema.database_name)
        self.explorer_widget.load_schema_model(profile.name, result.schema)
        first_schema = result.schema.schemas[0].name if result.schema.schemas else "—"
        self.breadcrumb_bar.set_path(profile.name, result.schema.database_name, first_schema)
        environment = profile.environment.value.capitalize()
        self.status_lbl_conn.setText(
            f" Conectado: {profile.name} / {result.schema.database_name} ({environment}) "
        )

        self._candidate_connection = None
        if previous_connection is not None and previous_connection is not candidate:
            try:
                previous_connection.disconnect()
            except Exception as err:
                logger.warning("Failed to close previous database connection", error=str(err))

    def _on_inspection_failed(self, message: str) -> None:
        """Keep the previous database visible when a candidate cannot be inspected."""
        preserve_tree = self._active_connection is not None
        self.explorer_widget.show_error(
            f"No se pudo cargar la estructura: {message}",
            preserve_tree=preserve_tree,
        )
        self.status_lbl_conn.setText(f" Error de conexión: {message} ")
        if self._active_database:
            self.explorer_widget.set_databases(self._database_names, self._active_database)
        if self._active_profile:
            self.conn_selector.blockSignals(True)
            self.conn_selector.select_profile(self._active_profile.id)
            self.conn_selector.blockSignals(False)

    def _on_inspection_finished(self) -> None:
        """Restore controls after either inspection outcome."""
        self._candidate_profile = None
        self._candidate_database = None
        self._candidate_connection = None
        self._inspection_worker = None
        self._is_inspecting = False
        self.explorer_widget.set_controls_enabled(True)
        self.conn_selector.setEnabled(True)

    def _on_database_changed(self, database_name: str) -> None:
        """Inspect a newly selected database using the active profile credentials."""
        if (
            self._is_inspecting
            or self._active_profile is None
            or database_name == self._active_database
        ):
            return
        self._start_inspection(
            self._active_profile,
            database_name,
            discover_databases=False,
        )

    def _refresh_active_database(self) -> None:
        """Refresh database choices and metadata through a new candidate connection."""
        if self._active_profile is None or self._active_database is None:
            return
        self._start_inspection(
            self._active_profile,
            self._active_database,
            discover_databases=True,
        )

    def _on_table_expansion_requested(self, schema_name: str, table_name: str) -> None:
        """Load one expanded table's fields through a transient adapter."""
        if self._active_profile is None or self._active_database is None:
            return
        key = (schema_name, table_name)
        if key in self._column_workers:
            return
        connection = self.connection_service.build_connection(
            self._active_profile,
            database_name=self._active_database,
        )
        worker = TableColumnsWorker(connection, schema_name, table_name)
        worker.signals.succeeded.connect(self.explorer_widget.load_table_columns)
        worker.signals.failed.connect(self.explorer_widget.show_table_columns_error)
        worker.signals.finished.connect(self._on_table_columns_finished)
        self._column_workers[key] = worker
        self._thread_pool.start(worker)

    def _on_table_columns_finished(self, schema_name: str, table_name: str) -> None:
        """Release the retained Qt worker after its signals have been delivered."""
        self._column_workers.pop((schema_name, table_name), None)

    def open_new_connection_dialog(self) -> None:
        """Open ConnectionDialog to create a new profile."""
        dialog = ConnectionDialog(
            profile=None, connection_service=self.connection_service, parent=self
        )
        if dialog.exec() == ConnectionDialog.DialogCode.Accepted:
            self.conn_selector.blockSignals(True)
            self.conn_selector.refresh_profiles()
            self.conn_selector.select_profile(dialog.profile.id)
            self.conn_selector.blockSignals(False)
            self._load_profile(dialog.profile)

    def open_edit_connection_dialog(self) -> None:
        """Open ConnectionDialog to edit selected profile."""
        profile = self.conn_selector.get_selected_profile()
        if not profile:
            return
        dialog = ConnectionDialog(
            profile=profile, connection_service=self.connection_service, parent=self
        )
        if dialog.exec() == ConnectionDialog.DialogCode.Accepted:
            self.conn_selector.blockSignals(True)
            self.conn_selector.refresh_profiles()
            self.conn_selector.select_profile(dialog.profile.id)
            self.conn_selector.blockSignals(False)
            self._load_profile(dialog.profile)

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
        if self._active_connection is None:
            self.results_widget.display_result(
                QueryResult(has_error=True, error_message="Selecciona una conexión activa.")
            )
            return

        self.btn_execute.setEnabled(False)
        self.results_widget.lbl_stats.setText("⏳ Ejecutando consulta…")
        self._query_worker = self.query_service.execute_async(
            self._active_connection,
            QueryRequest(sql=sql_text),
            self._on_query_finished,
        )

    def _on_query_finished(self, result: QueryResult) -> None:
        """Render a real query result and restore the execution action."""
        self.results_widget.display_result(result)
        self.btn_execute.setEnabled(True)
        self._query_worker = None

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

    def closeEvent(self, event: QCloseEvent) -> None:
        """Release live database adapters before closing the desktop."""
        connections = (self._candidate_connection, self._active_connection)
        disconnected_ids: set[int] = set()
        for connection in connections:
            if connection is None or id(connection) in disconnected_ids:
                continue
            try:
                connection.disconnect()
                disconnected_ids.add(id(connection))
            except Exception as err:
                logger.warning("Failed to close database connection", error=str(err))
        super().closeEvent(event)
