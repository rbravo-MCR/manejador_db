"""Compact Three-Mode Theme Control Component (Sistema, Claro, Oscuro)."""

from __future__ import annotations

import qtawesome as qta
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMenu, QToolButton

from backend_ide.ui.theme import ThemeManager, ThemeMode

MODE_ICONS = {
    ThemeMode.SYSTEM: "fa6s.desktop",
    ThemeMode.LIGHT: "fa6s.sun",
    ThemeMode.DARK: "fa6s.moon",
}

MODE_LABELS = {
    ThemeMode.SYSTEM: "Sistema",
    ThemeMode.LIGHT: "Claro",
    ThemeMode.DARK: "Oscuro",
}


class ThemeToggleButton(QToolButton):
    """Compact 3-mode theme switcher tool button with menu and quick toggle."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("theme_toggle_btn")
        self.setFixedSize(32, 32)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        self.clicked.connect(self._on_clicked)

        self._theme_manager = ThemeManager.get_instance()
        self._actions: dict[ThemeMode, QAction] = {}
        self._build_menu()

        self._theme_manager.theme_changed.connect(self._update_appearance)
        self._update_appearance(self._theme_manager.current_mode.value)

    def _build_menu(self) -> None:
        menu = QMenu(self)
        group = QActionGroup(self)
        group.setExclusive(True)

        for mode in (ThemeMode.SYSTEM, ThemeMode.LIGHT, ThemeMode.DARK):
            action = QAction(MODE_LABELS[mode], self)
            action.setData(mode)
            action.setCheckable(True)
            action.setIcon(qta.icon(MODE_ICONS[mode]))
            action.triggered.connect(lambda checked=False, m=mode: self._theme_manager.set_mode(m))
            group.addAction(action)
            menu.addAction(action)
            self._actions[mode] = action

        self.setMenu(menu)

    def _on_clicked(self) -> None:
        """Handle button click to switch theme."""
        self._theme_manager.toggle_theme()

    def _update_appearance(self, _mode_str: str) -> None:
        """Update button icon, tooltip, and checked menu action."""
        current_mode = self._theme_manager.current_mode
        resolved_mode = self._theme_manager.resolved_mode
        palette = self._theme_manager.current_palette

        icon_name = MODE_ICONS.get(resolved_mode, "fa6s.moon")
        self.setIcon(qta.icon(icon_name, color=palette.text_primary))
        self.setToolTip(f"Tema: {MODE_LABELS.get(current_mode, 'Oscuro')}")

        for mode, action in self._actions.items():
            action.setChecked(mode == current_mode)
