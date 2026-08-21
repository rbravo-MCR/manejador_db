"""Theme Manager for PySide6 Desktop UI with Modern QSS Design System."""

from __future__ import annotations

import os

from PySide6.QtCore import QObject, QSettings, Qt, Signal
from PySide6.QtWidgets import QApplication

from backend_ide.ui.theme.tokens import DARK_PALETTE, LIGHT_PALETTE, ThemeMode, ThemePalette

ICONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icons")
CHECKBOX_CHECKED_ICON = os.path.join(ICONS_DIR, "checkbox_checked.svg").replace("\\", "/")
RADIO_CHECKED_ICON = os.path.join(ICONS_DIR, "radio_checked.svg").replace("\\", "/")


class ThemeManager(QObject):
    """Central manager for application dark/light/system appearance and QSS styling."""

    theme_changed = Signal(str)  # Emits new mode name ("system", "light", or "dark")

    SETTINGS_KEY = "appearance/theme"
    _instance: ThemeManager | None = None

    def __init__(self, settings: QSettings | None = None) -> None:
        super().__init__()
        self._settings = settings or QSettings("BackendIDE", "BackendIDE")
        saved = self._settings.value(self.SETTINGS_KEY, ThemeMode.SYSTEM.value, type=str)
        try:
            self._mode: ThemeMode = ThemeMode(saved)
        except ValueError, TypeError:
            self._mode = ThemeMode.SYSTEM

        self._resolved_mode: ThemeMode = self._resolve_mode(self._mode)
        self._palette: ThemePalette = self._palette_for(self._resolved_mode)

        app = QApplication.instance()
        if app is not None and isinstance(app, QApplication):
            hints = app.styleHints()
            hints.colorSchemeChanged.connect(self._on_system_scheme_changed)

    @classmethod
    def get_instance(cls, settings: QSettings | None = None) -> ThemeManager:
        """Get singleton instance of ThemeManager."""
        if cls._instance is None:
            cls._instance = ThemeManager(settings=settings)
        return cls._instance

    @property
    def current_mode(self) -> ThemeMode:
        """Return current user-selected theme mode (system, light, or dark)."""
        return self._mode

    @property
    def resolved_mode(self) -> ThemeMode:
        """Return concrete resolved theme mode (light or dark)."""
        return self._resolved_mode

    @property
    def current_palette(self) -> ThemePalette:
        """Return current active color palette."""
        return self._palette

    def _resolve_mode(self, mode: ThemeMode) -> ThemeMode:
        """Resolve abstract ThemeMode.SYSTEM to either LIGHT or DARK based on OS hints."""
        if mode != ThemeMode.SYSTEM:
            return mode

        app = QApplication.instance()
        if app is not None and isinstance(app, QApplication):
            scheme = app.styleHints().colorScheme()
            return ThemeMode.LIGHT if scheme == Qt.ColorScheme.Light else ThemeMode.DARK

        return ThemeMode.DARK

    def _palette_for(self, mode: ThemeMode) -> ThemePalette:
        """Return color palette for resolved theme mode."""
        return LIGHT_PALETTE if mode == ThemeMode.LIGHT else DARK_PALETTE

    def set_mode(self, mode: ThemeMode, *, persist: bool = True) -> None:
        """Set theme mode, resolve concrete palette, persist and apply stylesheet."""
        self._mode = mode
        self._resolved_mode = self._resolve_mode(mode)
        self._palette = self._palette_for(self._resolved_mode)

        if persist:
            self._settings.setValue(self.SETTINGS_KEY, mode.value)
            self._settings.sync()

        self.apply_theme()
        self.theme_changed.emit(self._mode.value)

    def toggle_theme(self) -> ThemeMode:
        """Toggle between Dark and Light mode and return new mode."""
        new_mode = ThemeMode.LIGHT if self._resolved_mode == ThemeMode.DARK else ThemeMode.DARK
        self.set_mode(new_mode)
        return new_mode

    def _on_system_scheme_changed(self, *args) -> None:
        """Handle OS color scheme changes when mode is SYSTEM."""
        if self._mode == ThemeMode.SYSTEM:
            self._resolved_mode = self._resolve_mode(ThemeMode.SYSTEM)
            self._palette = self._palette_for(self._resolved_mode)
            self.apply_theme()
            self.theme_changed.emit(self._mode.value)

    def apply_theme(self, app: QApplication | None = None) -> None:
        """Apply generated QSS stylesheet to QApplication."""
        target_app = app or QApplication.instance()
        if target_app and isinstance(target_app, QApplication):
            qss = self.generate_stylesheet()
            target_app.setStyleSheet(qss)

    def generate_stylesheet(self) -> str:
        """Generate state-of-the-art Qt Style Sheet (QSS) design system."""
        p = self._palette
        return f"""
        /* Global Reset & Typography */
        QMainWindow, QDialog {{
            background-color: {p.bg_main};
            color: {p.text_primary};
            font-family: 'Inter', 'SF Pro Text', 'Segoe UI', 'Ubuntu', sans-serif;
            font-size: 13px;
        }}

        QWidget {{
            color: {p.text_primary};
            outline: 0;
        }}

        /* Toolbars & Headers */
        #top_bar {{
            background-color: {p.bg_sidebar};
            border-bottom: 1px solid {p.border};
            padding: 4px 8px;
        }}

        #toolbar_group {{
            background-color: {p.bg_surface};
            border: 1px solid {p.border};
            border-radius: 8px;
            padding: 2px;
        }}

        /* Sidebar Container & Headers */
        #sidebar_container {{
            background-color: {p.bg_sidebar};
            border-right: 1px solid {p.border};
        }}

        #sidebar_header {{
            background-color: {p.bg_sidebar};
            border-bottom: 1px solid {p.border};
            padding: 6px 8px;
        }}

        #sidebar_title {{
            font-weight: bold;
            font-size: 11px;
            color: {p.text_secondary};
        }}

        #section_label {{
            font-weight: bold;
            font-size: 12px;
            color: {p.text_primary};
        }}

        #count_badge {{
            background-color: {p.bg_input};
            color: {p.text_secondary};
            border-radius: 10px;
            padding: 1px 7px;
            font-size: 11px;
            font-weight: bold;
        }}

        QLabel[status="loading"] {{
            color: {p.info};
            font-size: 11px;
            font-style: italic;
        }}

        QLabel[status="error"] {{
            color: {p.danger};
            font-size: 11px;
        }}

        /* Breadcrumb Bar */
        #breadcrumb_bar {{
            background-color: {p.bg_sidebar};
            border-bottom: 1px solid {p.border};
            padding: 4px 10px;
            font-size: 12px;
            color: {p.text_secondary};
        }}

        #breadcrumb_conn, #breadcrumb_db {{
            font-weight: 500;
            color: {p.text_primary};
        }}

        #breadcrumb_schema {{
            font-weight: bold;
            color: {p.accent};
        }}

        #breadcrumb_sep {{
            color: {p.text_muted};
            font-size: 14px;
            font-weight: bold;
        }}

        /* Tabs Styling */
        QTabWidget::pane {{
            border: 1px solid {p.border};
            background-color: {p.bg_surface};
            border-radius: 0px 0px 8px 8px;
        }}

        QTabBar::tab {{
            background-color: {p.bg_sidebar};
            color: {p.text_secondary};
            border: 1px solid {p.border};
            border-bottom: None;
            padding: 7px 16px;
            margin-right: 3px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            font-weight: 500;
        }}

        QTabBar::tab:selected {{
            background-color: {p.bg_surface};
            color: {p.accent};
            border-top: 2px solid {p.accent};
            font-weight: bold;
        }}

        QTabBar::tab:hover:!selected {{
            background-color: {p.bg_hover};
            color: {p.text_primary};
        }}

        /* Buttons Design System */
        QPushButton, QToolButton {{
            background-color: {p.bg_surface};
            border: 1px solid {p.border};
            color: {p.text_primary};
            padding: 6px 14px;
            border-radius: 6px;
            font-weight: 500;
            font-size: 12px;
        }}

        QPushButton:hover, QToolButton:hover {{
            background-color: {p.bg_hover};
            border-color: {p.accent};
            color: {p.accent};
        }}

        QPushButton:pressed, QToolButton:pressed {{
            background-color: {p.accent};
            color: #11111b;
        }}

        QPushButton:disabled, QToolButton:disabled {{
            background-color: {p.bg_sidebar};
            color: {p.text_muted};
            border-color: {p.border};
        }}

        /* Primary Action Buttons */
        QPushButton#btn_new_conn {{
            background-color: {p.accent};
            color: #11111b;
            font-weight: bold;
            border: 1px solid {p.accent};
            padding: 6px 16px;
            border-radius: 6px;
        }}

        QPushButton#btn_new_conn:hover {{
            background-color: {p.accent_hover};
            border-color: {p.accent_hover};
            color: #11111b;
        }}

        QPushButton#btn_execute {{
            background-color: {p.success};
            color: #11111b;
            font-weight: bold;
            border: 1px solid {p.success};
            padding: 6px 18px;
            border-radius: 6px;
        }}

        QPushButton#btn_execute:hover {{
            background-color: {p.success_hover};
            border-color: {p.success_hover};
            color: #11111b;
        }}

        /* Icon Buttons */
        QPushButton#icon_button, QToolButton#icon_button {{
            padding: 0px;
            border: 1px solid transparent;
            background-color: transparent;
            border-radius: 4px;
        }}

        QPushButton#icon_button:hover, QToolButton#icon_button:hover {{
            background-color: {p.bg_hover};
            border-color: {p.border};
        }}

        QPushButton#theme_toggle_btn, QToolButton#theme_toggle_btn {{
            font-size: 13px;
            padding: 4px;
            border-radius: 6px;
            background-color: {p.bg_surface};
            border: 1px solid {p.border};
        }}

        QToolButton#theme_toggle_btn::menu-button {{
            border: none;
            width: 14px;
        }}

        /* Menus */
        QMenu {{
            background-color: {p.bg_surface};
            border: 1px solid {p.border};
            border-radius: 6px;
            padding: 4px;
        }}

        QMenu::item {{
            padding: 6px 20px 6px 12px;
            border-radius: 4px;
            color: {p.text_primary};
        }}

        QMenu::item:selected {{
            background-color: {p.bg_hover};
            color: {p.accent};
        }}

        QMenu::item:checked {{
            font-weight: bold;
            color: {p.accent};
        }}

        /* Input Controls & ComboBox */
        QComboBox, QLineEdit {{
            background-color: {p.bg_input};
            border: 1px solid {p.border};
            color: {p.text_primary};
            padding: 5px 10px;
            border-radius: 6px;
            selection-background-color: {p.accent};
        }}

        QComboBox:hover, QLineEdit:focus {{
            border-color: {p.border_active};
        }}

        QComboBox QAbstractItemView {{
            background-color: {p.bg_surface};
            border: 1px solid {p.border};
            selection-background-color: {p.accent};
            selection-color: #11111b;
            padding: 4px;
            border-radius: 6px;
        }}

        /* CheckBoxes & RadioButtons */
        QCheckBox, QRadioButton {{
            color: {p.text_primary};
            spacing: 8px;
            font-size: 13px;
        }}

        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {p.border};
            border-radius: 4px;
            background-color: {p.bg_input};
        }}

        QCheckBox::indicator:hover {{
            border-color: {p.accent};
            background-color: {p.bg_hover};
        }}

        QCheckBox::indicator:checked {{
            background-color: {p.accent};
            border-color: {p.accent};
            image: url("{CHECKBOX_CHECKED_ICON}");
        }}

        QCheckBox::indicator:checked:hover {{
            background-color: {p.accent_hover};
            border-color: {p.accent_hover};
        }}

        QCheckBox::indicator:disabled {{
            border-color: {p.border};
            background-color: {p.bg_sidebar};
        }}

        QRadioButton::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {p.border};
            border-radius: 9px;
            background-color: {p.bg_input};
        }}

        QRadioButton::indicator:hover {{
            border-color: {p.accent};
            background-color: {p.bg_hover};
        }}

        QRadioButton::indicator:checked {{
            background-color: {p.accent};
            border-color: {p.accent};
            image: url("{RADIO_CHECKED_ICON}");
        }}

        /* List Widget & List View */
        QListWidget, QListView {{
            background-color: {p.bg_input};
            border: 1px solid {p.border};
            border-radius: 6px;
            padding: 4px;
            color: {p.text_primary};
        }}

        QListWidget::item, QListView::item {{
            padding: 6px 8px;
            border-radius: 4px;
            color: {p.text_primary};
            margin: 1px 0px;
            border: 1px solid transparent;
        }}

        QListWidget::item:hover, QListView::item:hover {{
            background-color: {p.bg_hover};
            color: {p.text_primary};
        }}

        QListWidget::item:selected, QListView::item:selected {{
            background-color: {p.bg_surface};
            color: {p.accent};
            font-weight: bold;
            border: 1px solid {p.accent};
        }}

        QListWidget::item:selected:hover, QListView::item:selected:hover {{
            background-color: {p.bg_surface};
            color: {p.accent_hover};
            border: 1px solid {p.accent_hover};
        }}

        /* Checkable Indicators for Lists and Trees */
        QListWidget::indicator, QListView::indicator, QTreeWidget::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {p.border};
            border-radius: 4px;
            background-color: {p.bg_surface};
        }}

        QListWidget::indicator:hover,
        QListView::indicator:hover,
        QTreeWidget::indicator:hover {{
            border-color: {p.accent};
            background-color: {p.bg_hover};
        }}

        QListWidget::indicator:checked,
        QListView::indicator:checked,
        QTreeWidget::indicator:checked {{
            background-color: {p.accent};
            border-color: {p.accent};
            image: url("{CHECKBOX_CHECKED_ICON}");
        }}

        QListWidget::indicator:checked:hover,
        QListView::indicator:checked:hover,
        QTreeWidget::indicator:checked:hover {{
            background-color: {p.accent_hover};
            border-color: {p.accent_hover};
        }}

        /* Text Editors & Plain Text */
        QPlainTextEdit, QTextEdit {{
            background-color: {p.bg_input};
            color: {p.text_primary};
            border: 1px solid {p.border};
            border-radius: 6px;
            padding: 8px;
            selection-background-color: {p.accent};
            selection-color: #11111b;
        }}

        QPlainTextEdit:focus, QTextEdit:focus {{
            border-color: {p.border_active};
        }}

        /* Tree Widget */
        QTreeWidget {{
            background-color: {p.bg_surface};
            border: 1px solid {p.border};
            border-radius: 6px;
            padding: 4px;
            color: {p.text_primary};
        }}

        QTreeWidget::item {{
            padding: 5px;
            border-radius: 4px;
            color: {p.text_primary};
        }}

        QTreeWidget::item:hover {{
            background-color: {p.bg_hover};
            color: {p.text_primary};
        }}

        QTreeWidget::item:selected {{
            background-color: {p.bg_input};
            color: {p.accent};
            font-weight: bold;
        }}

        /* Table View Grid */
        QTableView, QTableWidget {{
            background-color: {p.bg_surface};
            alternate-background-color: {p.bg_input};
            gridline-color: {p.border};
            border: 1px solid {p.border};
            border-radius: 6px;
            color: {p.text_primary};
            selection-background-color: {p.bg_hover};
            selection-color: {p.accent};
        }}

        QTableView::item, QTableWidget::item {{
            padding: 4px 6px;
            color: {p.text_primary};
        }}

        QTableView::item:hover, QTableWidget::item:hover {{
            background-color: {p.bg_hover};
            color: {p.text_primary};
        }}

        QTableView::item:selected, QTableWidget::item:selected {{
            background-color: {p.bg_hover};
            color: {p.accent};
            font-weight: bold;
        }}

        QHeaderView::section {{
            background-color: {p.bg_input};
            color: {p.text_primary};
            font-weight: bold;
            padding: 7px;
            border: 1px solid {p.border};
        }}

        /* Splitter Handle */
        QSplitter::handle {{
            background-color: {p.border};
        }}

        QSplitter::handle:hover {{
            background-color: {p.accent};
        }}

        /* Scrollbars */
        QScrollBar:vertical, QScrollBar:horizontal {{
            background: {p.bg_sidebar};
            width: 10px;
            height: 10px;
            margin: 0px;
        }}

        QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
            background: {p.border};
            min-height: 20px;
            min-width: 20px;
            border-radius: 5px;
        }}

        QScrollBar::handle:hover {{
            background: {p.text_muted};
        }}

        QScrollBar::add-line, QScrollBar::sub-line {{
            height: 0px;
            width: 0px;
        }}

        /* Status Bar */
        QStatusBar {{
            background-color: {p.bg_sidebar};
            border-top: 1px solid {p.border};
            color: {p.text_secondary};
            font-size: 12px;
        }}
        """
