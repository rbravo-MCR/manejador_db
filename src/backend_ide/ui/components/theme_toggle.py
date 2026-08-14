"""Compact quick toggle and menu for System, Light, and Dark appearance."""

import qtawesome as qta
from PySide6.QtCore import QSize
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMenu, QToolButton

from backend_ide.ui.theme import ThemeManager, ThemeMode


class ThemeToggleButton(QToolButton):
    """Switch Light/Dark quickly and expose every documented appearance mode."""

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

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("theme_toggle_btn")
        self.setFixedSize(32, 32)
        self.setIconSize(QSize(16, 16))
        self.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)

        self._theme_manager = ThemeManager.get_instance()
        self._mode_actions: dict[ThemeMode, QAction] = {}
        self._setup_menu()

        self.clicked.connect(self._on_clicked)
        self._theme_manager.theme_changed.connect(self._update_icon)
        self._update_icon(self._theme_manager.current_mode.value)

    def _setup_menu(self) -> None:
        """Build one exclusive menu action per documented mode."""
        menu = QMenu(self)
        group = QActionGroup(menu)
        group.setExclusive(True)
        for mode in ThemeMode:
            action = menu.addAction(self.MODE_LABELS[mode])
            action.setCheckable(True)
            action.setData(mode)
            action.triggered.connect(
                lambda _checked=False, selected_mode=mode: self._theme_manager.set_mode(
                    selected_mode
                )
            )
            group.addAction(action)
            self._mode_actions[mode] = action
        self.setMenu(menu)

    def _on_clicked(self) -> None:
        """Toggle quickly between concrete Light and Dark modes."""
        self._theme_manager.toggle_theme()

    def _update_icon(self, mode_str: str) -> None:
        """Refresh icons, tooltip, and checked menu state from the selected theme."""
        mode = ThemeMode(mode_str)
        palette = self._theme_manager.current_palette
        icon_color = palette.text_primary
        self.setIcon(qta.icon(self.MODE_ICONS[mode], color=icon_color))
        self.setToolTip(f"Tema: {self.MODE_LABELS[mode]}. Clic para alternar Claro/Oscuro.")
        for action_mode, action in self._mode_actions.items():
            action.setChecked(action_mode == mode)
            action.setIcon(qta.icon(self.MODE_ICONS[action_mode], color=icon_color))
