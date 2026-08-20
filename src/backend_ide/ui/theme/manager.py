"""Theme Manager for PySide6 Desktop UI with Modern QSS Design System."""

from __future__ import annotations

from PySide6.QtCore import QObject, QSettings, Qt, Signal
from PySide6.QtWidgets import QApplication

from backend_ide.ui.theme.tokens import DARK_PALETTE, LIGHT_PALETTE, ThemeMode, ThemePalette


class ThemeManager(QObject):
    """Central manager for application dark/light appearance and QSS styling."""

    theme_changed = Signal(str)  # Emits new mode name ("light" or "dark")

    _instance: ThemeManager | None = None
    SETTINGS_KEY = "appearance/theme"

    def __init__(self, settings: QSettings | None = None) -> None:
        super().__init__()
        self._settings = settings or QSettings("BackendIDE", "BackendIDE")
        saved_mode = self._settings.value(self.SETTINGS_KEY, ThemeMode.SYSTEM.value, type=str)
        try:
            self._mode = ThemeMode(saved_mode)
        except ValueError:
            self._mode = ThemeMode.SYSTEM
        self._resolved_mode = self._resolve_mode(self._mode)
        self._palette = self._palette_for(self._resolved_mode)

        app = QApplication.instance()
        if isinstance(app, QApplication):
            app.styleHints().colorSchemeChanged.connect(self._on_system_color_scheme_changed)

    @classmethod
    def get_instance(cls) -> ThemeManager:
        """Get singleton instance of ThemeManager."""
        if cls._instance is None:
            cls._instance = ThemeManager()
        return cls._instance

    @property
    def current_mode(self) -> ThemeMode:
        """Return current theme mode."""
        return self._mode

    @property
    def current_palette(self) -> ThemePalette:
        """Return current color palette."""
        return self._palette

    @property
    def resolved_mode(self) -> ThemeMode:
        """Return the concrete Light or Dark mode currently being rendered."""
        return self._resolved_mode

    def _resolve_mode(self, mode: ThemeMode) -> ThemeMode:
        if mode != ThemeMode.SYSTEM:
            return mode
        app = QApplication.instance()
        if not isinstance(app, QApplication):
            return ThemeMode.DARK
        scheme = app.styleHints().colorScheme()
        return ThemeMode.LIGHT if scheme == Qt.ColorScheme.Light else ThemeMode.DARK

    @staticmethod
    def _palette_for(mode: ThemeMode) -> ThemePalette:
        return LIGHT_PALETTE if mode == ThemeMode.LIGHT else DARK_PALETTE

    def _on_system_color_scheme_changed(self, _scheme: Qt.ColorScheme) -> None:
        if self._mode == ThemeMode.SYSTEM:
            self.set_mode(ThemeMode.SYSTEM, persist=False)

    def set_mode(self, mode: ThemeMode, *, persist: bool = True) -> None:
        """Set theme mode and apply stylesheet."""
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
            padding: 6px 10px;
        }}

        /* Breadcrumb Bar */
        #breadcrumb_bar {{
            background-color: {p.bg_sidebar};
            border-bottom: 1px solid {p.border};
            padding: 4px 10px;
            font-size: 12px;
            color: {p.text_secondary};
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

        QToolButton#theme_toggle_btn, QToolButton#icon_button {{
            padding: 5px;
            border-radius: 6px;
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

        /* Tree Widget */
        QTreeWidget {{
            background-color: {p.bg_sidebar};
            border: 1px solid {p.border};
            border-radius: 6px;
            padding: 4px;
        }}

        QTreeWidget::item {{
            padding: 5px;
            border-radius: 4px;
        }}

        QTreeWidget::item:hover {{
            background-color: {p.bg_hover};
        }}

        QTreeWidget::item:selected {{
            background-color: {p.bg_input};
            color: {p.accent};
            font-weight: bold;
        }}

        /* Table View Grid */
        QTableView {{
            background-color: {p.bg_surface};
            gridline-color: {p.border};
            border: 1px solid {p.border};
            border-radius: 6px;
            selection-background-color: {p.bg_input};
            selection-color: {p.accent};
        }}

        QHeaderView::section {{
            background-color: {p.bg_sidebar};
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
