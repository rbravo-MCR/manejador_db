"""Compact application appearance control."""

import qtawesome as qta
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QToolButton

from backend_ide.ui.theme import ThemeManager, ThemeMode

MODE_LABELS = {
    ThemeMode.SYSTEM: "Sistema",
    ThemeMode.LIGHT: "Claro",
    ThemeMode.DARK: "Oscuro",
}

MODE_ICONS = {
    ThemeMode.SYSTEM: "fa6s.desktop",
    ThemeMode.LIGHT: "fa6s.sun",
    ThemeMode.DARK: "fa6s.moon",
}


class ThemeToggleButton(QToolButton):
    """Quick Light/Dark toggle with explicit System, Light, and Dark choices."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("theme_toggle_btn")
        self.setFixedSize(32, 32)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        self.clicked.connect(self._on_clicked)

        self._theme_manager = ThemeManager.get_instance()
        self.setMenu(self._build_menu())
        self._theme_manager.theme_changed.connect(self._refresh_appearance)
        self._refresh_appearance(self._theme_manager.current_mode.value)

    def _build_menu(self) -> QMenu:
        menu = QMenu(self)
        for mode in ThemeMode:
            action = QAction(MODE_LABELS[mode], menu)
            action.setCheckable(True)
            action.setData(mode)
            action.triggered.connect(lambda _checked=False, value=mode: self._select_mode(value))
            menu.addAction(action)
        return menu

    def _select_mode(self, mode: ThemeMode) -> None:
        self._theme_manager.set_mode(mode)

    def _on_clicked(self) -> None:
        """Handle button click to switch theme."""
        self._theme_manager.toggle_theme()

    def _refresh_appearance(self, _mode_str: str) -> None:
        """Refresh icon, tooltip, and checked menu state from the selected mode."""
        mode = self._theme_manager.current_mode
        color = self._theme_manager.current_palette.text_primary
        self.setIcon(qta.icon(MODE_ICONS[mode], color=color))
        self.setToolTip(f"Tema: {MODE_LABELS[mode]}")

        for action in self.menu().actions():
            action_mode = ThemeMode(action.data())
            action.setIcon(qta.icon(MODE_ICONS[action_mode], color=color))
            action.setChecked(action_mode == mode)
