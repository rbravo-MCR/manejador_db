"""UI Shell Unit Tests for Phase 3 - PySide6 Application Shell."""

import os
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QDialog, QWidget

from backend_ide.domain.connection import ConnectionProfile
from backend_ide.domain.schema import DatabaseSchema, Schema, Table
from backend_ide.infrastructure.database.schema_inspection_worker import DatabaseInspectionResult
from backend_ide.ui.app import create_app
from backend_ide.ui.theme import DARK_PALETTE, LIGHT_PALETTE, ThemeManager, ThemeMode
from backend_ide.ui.views.main_window import MainWindow

# Set offscreen platform plugin for headless CI testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture
def app_instance():
    """Fixture providing initialized QApplication and MainWindow."""
    app, window = create_app([], auto_load_profile=False)
    yield app, window
    window.close()


def test_main_window_creation(app_instance, qtbot):
    """Test MainWindow initialization and essential widget hierarchy."""
    app, window = app_instance
    qtbot.addWidget(window)

    assert window.windowTitle().startswith("Backend Development IDE")
    assert window.conn_selector is not None
    assert window.theme_toggle is not None
    assert window.explorer_widget is not None
    assert window.explorer_widget.minimumWidth() == 280
    assert window.tabs_workspace.count() == 1
    assert window.status_bar is not None


def test_header_rows_stay_compact_and_controls_are_vertically_aligned(app_instance, qtbot):
    """Prevent toolbar labels from stretching into oversized vertical blocks."""
    app, window = app_instance
    qtbot.addWidget(window)
    window.show()
    app.processEvents()

    top_bar = window.findChild(QWidget, "top_bar")
    assert top_bar is not None
    assert top_bar.height() <= 56
    assert window.breadcrumb_bar.height() <= 36

    controls = [
        window.conn_selector.btn_new,
        window.conn_selector.combo,
        window.conn_selector.env_badge,
        window.conn_selector.btn_edit,
    ]
    assert all(control.height() <= 36 for control in controls)

    vertical_centers = [control.mapTo(top_bar, control.rect().center()).y() for control in controls]
    assert max(vertical_centers) - min(vertical_centers) <= 2


def test_top_bar_groups_controls_by_documented_function(app_instance, qtbot):
    """Flattening or misordering the three documented toolbar zones must fail."""
    app, window = app_instance
    qtbot.addWidget(window)
    window.show()
    app.processEvents()

    assert window.minimumSize().width() == 1100
    assert window.minimumSize().height() == 700
    assert window.top_bar.layout().columnCount() == 3
    assert window.top_bar.layout().itemAtPosition(0, 0).widget() is window.conn_selector
    assert window.top_bar.layout().itemAtPosition(0, 1).widget() is window.query_toolbar
    assert window.top_bar.layout().itemAtPosition(0, 2).widget() is window.theme_toggle
    assert window.btn_execute.height() == 32
    assert window.btn_new_query.height() == 32
    assert window.btn_er_diagram.height() == 32
    assert not window.btn_er_diagram.isEnabled()


def test_connection_controls_follow_context_then_actions(app_instance, qtbot):
    """Moving profile actions ahead of their context must fail."""
    _, window = app_instance
    qtbot.addWidget(window)
    layout = window.conn_selector.layout()
    widgets = [layout.itemAt(index).widget() for index in range(layout.count())]

    assert widgets == [
        window.conn_selector.lbl_profile,
        window.conn_selector.combo,
        window.conn_selector.env_badge,
        window.conn_selector.btn_new,
        window.conn_selector.btn_edit,
    ]
    assert window.conn_selector.combo.minimumWidth() == 180


def test_theme_toggle_functionality(app_instance, qtbot):
    """The quick toggle must change mode and refresh its accessible description."""
    _, window = app_instance
    qtbot.addWidget(window)

    manager = ThemeManager.get_instance()
    manager.set_mode(ThemeMode.DARK)

    assert manager.current_mode == ThemeMode.DARK
    assert "Oscuro" in window.theme_toggle.toolTip()
    assert not window.theme_toggle.icon().isNull()

    # Click toggle button
    qtbot.mouseClick(
        window.theme_toggle, pytest.importorskip("PySide6.QtCore").Qt.MouseButton.LeftButton
    )

    assert manager.current_mode == ThemeMode.LIGHT
    assert "Claro" in window.theme_toggle.toolTip()


def test_theme_manager_persists_all_documented_modes(qapp, tmp_path):
    """Removing persistence for any documented appearance mode must fail."""
    settings_path = tmp_path / "theme.ini"
    settings = QSettings(str(settings_path), QSettings.Format.IniFormat)
    manager = ThemeManager(settings=settings)

    for mode in (ThemeMode.SYSTEM, ThemeMode.LIGHT, ThemeMode.DARK):
        manager.set_mode(mode)
        assert manager.current_mode == mode
        assert settings.value("appearance/theme") == mode.value

    restored = ThemeManager(settings=QSettings(str(settings_path), QSettings.Format.IniFormat))
    assert restored.current_mode == ThemeMode.DARK


def test_system_theme_resolves_to_a_concrete_palette(qapp, tmp_path):
    """Treating System as a stored Dark choice must fail this behavior contract."""
    settings = QSettings(str(tmp_path / "system.ini"), QSettings.Format.IniFormat)
    manager = ThemeManager(settings=settings)

    manager.set_mode(ThemeMode.SYSTEM)

    assert manager.current_mode == ThemeMode.SYSTEM
    assert manager.resolved_mode in (ThemeMode.LIGHT, ThemeMode.DARK)
    expected = LIGHT_PALETTE if manager.resolved_mode == ThemeMode.LIGHT else DARK_PALETTE
    assert manager.current_palette == expected


def test_theme_control_exposes_system_light_and_dark(app_instance, qtbot):
    """Dropping a documented mode or quick-toggle behavior must fail."""
    _, window = app_instance
    qtbot.addWidget(window)
    manager = ThemeManager.get_instance()
    manager.set_mode(ThemeMode.SYSTEM)

    assert window.theme_toggle.height() == 32
    assert [action.data() for action in window.theme_toggle.menu().actions()] == [
        ThemeMode.SYSTEM,
        ThemeMode.LIGHT,
        ThemeMode.DARK,
    ]

    dark_action = next(
        action for action in window.theme_toggle.menu().actions() if action.data() == ThemeMode.DARK
    )
    dark_action.trigger()
    assert manager.current_mode == ThemeMode.DARK
    assert dark_action.isChecked()

    qtbot.mouseClick(window.theme_toggle, Qt.MouseButton.LeftButton)
    assert manager.current_mode == ThemeMode.LIGHT


def test_workspace_tabs_management(app_instance, qtbot):
    """Test adding and closing tabs in workspace area."""
    _, window = app_instance
    qtbot.addWidget(window)

    initial_count = window.tabs_workspace.count()
    assert initial_count == 1

    # Close sole tab (should be prevented)
    window._on_tab_close_requested(0)
    assert window.tabs_workspace.count() == 1


def test_execute_uses_active_connection_and_displays_real_rows(qtbot):
    """Executing SQL must show rows returned by the active database, never demo data."""
    pool = RecordingThreadPool()
    window = MainWindow(thread_pool=pool, auto_load_profile=False)
    qtbot.addWidget(window)
    connection = MagicMock()
    connection.execute_query.return_value = [{"answer": 42}]
    window._active_connection = connection
    editor = window.tabs_workspace.currentWidget()
    editor.set_sql_text("SELECT 42 AS answer;")

    window.execute_current_query()

    assert pool.worker is not None
    pool.worker.run()
    assert window.results_widget.table_model.rowCount() == 1
    assert window.results_widget.table_model.item(0, 0).text() == "42"


def test_opening_new_connection_keeps_main_window_alive(app_instance, qtbot, monkeypatch):
    """Opening and cancelling the modal must never close the desktop application."""
    app, window = app_instance
    qtbot.addWidget(window)
    window.show()
    app.processEvents()

    monkeypatch.setattr(QDialog, "exec", lambda _dialog: QDialog.DialogCode.Rejected)
    window.open_new_connection_dialog()

    assert window.isVisible()


def create_live_schema(database_name: str = "db_outlet") -> DatabaseSchema:
    """Build a small live-looking schema for main-window integration tests."""
    return DatabaseSchema(
        engine_name="postgresql",
        database_name=database_name,
        schemas=[Schema(name="public", tables=[Table(name="customers", schema_name="public")])],
    )


class RecordingThreadPool:
    """Capture queued QRunnables without starting real background work."""

    def __init__(self):
        self.worker = None

    def start(self, worker):
        self.worker = worker


def test_inspection_success_updates_explorer_database_breadcrumb_and_status(qtbot):
    """A worker result should replace every hard-coded connection label."""
    pool = RecordingThreadPool()
    window = MainWindow(thread_pool=pool, auto_load_profile=False)
    qtbot.addWidget(window)
    profile = ConnectionProfile(name="B2B_OUTLET", engine="postgresql", database="db_outlet")
    candidate = MagicMock()
    window._candidate_connection = candidate
    window._candidate_profile = profile
    window._candidate_database = "db_outlet"

    window._on_inspection_succeeded(
        DatabaseInspectionResult(("analytics", "db_outlet"), create_live_schema())
    )

    assert window.explorer_widget.cmb_database.currentText() == "db_outlet"
    assert "public" in window.explorer_widget.tree.topLevelItem(0).text(0)
    assert "db_outlet" in window.breadcrumb_bar.lbl_db.text()
    assert "B2B_OUTLET" in window.breadcrumb_bar.lbl_conn.text()
    assert "Conectado" in window.status_lbl_conn.text()


def test_database_selection_queues_candidate_for_selected_database(qtbot):
    """Selecting a dropdown item should inspect that database off the UI thread."""
    pool = RecordingThreadPool()
    window = MainWindow(thread_pool=pool, auto_load_profile=False)
    qtbot.addWidget(window)
    profile = ConnectionProfile(name="B2B_OUTLET", engine="postgresql", database="db_outlet")
    candidate = MagicMock()
    window._active_profile = profile
    window._active_database = "db_outlet"
    window._database_names = ("analytics", "db_outlet")

    with patch.object(
        window.connection_service, "build_connection", return_value=candidate
    ) as build:
        window._on_database_changed("analytics")

    build.assert_called_once_with(profile, database_name="analytics")
    assert pool.worker.connection is candidate
    assert pool.worker.database_names == ("analytics", "db_outlet")


def test_failed_database_switch_preserves_previous_tree_and_selection(qtbot):
    """A rejected candidate cannot erase the last useful database metadata."""
    window = MainWindow(thread_pool=RecordingThreadPool(), auto_load_profile=False)
    qtbot.addWidget(window)
    profile = ConnectionProfile(name="B2B_OUTLET", engine="postgresql", database="db_outlet")
    active = MagicMock()
    window._active_profile = profile
    window._active_connection = active
    window._active_database = "db_outlet"
    window._database_names = ("analytics", "db_outlet")
    window.explorer_widget.set_databases(window._database_names, "db_outlet")
    window.explorer_widget.load_schema_model(profile.name, create_live_schema())
    old_schema = window.explorer_widget.tree.topLevelItem(0)

    window._on_inspection_failed("permission denied")

    assert window.explorer_widget.cmb_database.currentText() == "db_outlet"
    assert window.explorer_widget.tree.topLevelItem(0) is old_schema
    assert "permission denied" in window.explorer_widget.lbl_state.text()
    assert window._active_connection is active


def test_closing_main_window_disconnects_active_database(qtbot):
    """Closing the desktop must release the active PostgreSQL adapter."""
    window = MainWindow(thread_pool=RecordingThreadPool(), auto_load_profile=False)
    qtbot.addWidget(window)
    active = MagicMock()
    window._active_connection = active

    window.close()

    active.disconnect.assert_called_once()


def test_table_expansion_queues_lazy_column_worker(qtbot):
    """The main window should load one table's fields without reinspecting the database."""
    pool = RecordingThreadPool()
    window = MainWindow(thread_pool=pool, auto_load_profile=False)
    qtbot.addWidget(window)
    profile = ConnectionProfile(name="B2B_OUTLET", engine="postgresql", database="db_outlet")
    window._active_profile = profile
    window._active_database = "db_outlet"
    candidate = MagicMock()

    with patch.object(window.connection_service, "build_connection", return_value=candidate):
        window._on_table_expansion_requested("public", "customers")

    assert pool.worker.connection is candidate
    assert pool.worker.schema_name == "public"
    assert pool.worker.table_name == "customers"
