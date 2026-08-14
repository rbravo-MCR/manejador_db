"""UI Shell Unit Tests for Phase 3 - PySide6 Application Shell."""

import os

import pytest
from PySide6.QtWidgets import QDialog, QWidget

from backend_ide.ui.app import create_app
from backend_ide.ui.theme import ThemeManager, ThemeMode

# Set offscreen platform plugin for headless CI testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture
def app_instance():
    """Fixture providing initialized QApplication and MainWindow."""
    app, window = create_app([])
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


def test_theme_toggle_functionality(app_instance, qtbot):
    """Test switching Dark/Light theme updates ThemeManager and ToggleButton text."""
    _, window = app_instance
    qtbot.addWidget(window)

    manager = ThemeManager.get_instance()
    manager.set_mode(ThemeMode.DARK)

    assert manager.current_mode == ThemeMode.DARK
    assert "Light" in window.theme_toggle.text()

    # Click toggle button
    qtbot.mouseClick(
        window.theme_toggle, pytest.importorskip("PySide6.QtCore").Qt.MouseButton.LeftButton
    )

    assert manager.current_mode == ThemeMode.LIGHT
    assert "Dark" in window.theme_toggle.text()


def test_workspace_tabs_management(app_instance, qtbot):
    """Test adding and closing tabs in workspace area."""
    _, window = app_instance
    qtbot.addWidget(window)

    initial_count = window.tabs_workspace.count()
    assert initial_count == 1

    # Close sole tab (should be prevented)
    window._on_tab_close_requested(0)
    assert window.tabs_workspace.count() == 1


def test_opening_new_connection_keeps_main_window_alive(app_instance, qtbot, monkeypatch):
    """Opening and cancelling the modal must never close the desktop application."""
    app, window = app_instance
    qtbot.addWidget(window)
    window.show()
    app.processEvents()

    monkeypatch.setattr(QDialog, "exec", lambda _dialog: QDialog.DialogCode.Rejected)
    window.open_new_connection_dialog()

    assert window.isVisible()
