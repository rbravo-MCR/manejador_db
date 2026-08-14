"""Quick Theme Toggle Button Component (☀️ / 🌙)."""

from PySide6.QtWidgets import QPushButton

from backend_ide.ui.theme import ThemeManager, ThemeMode


class ThemeToggleButton(QPushButton):
    """Compact toggle button for switching Dark/Light appearance."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("theme_toggle_btn")
        self.setFixedHeight(30)
        self.setToolTip("Quick Light/Dark Theme Toggle (☀️ / 🌙)")
        self.clicked.connect(self._on_clicked)

        self._theme_manager = ThemeManager.get_instance()
        self._theme_manager.theme_changed.connect(self._update_icon)
        self._update_icon(self._theme_manager.current_mode.value)

    def _on_clicked(self) -> None:
        """Handle button click to switch theme."""
        self._theme_manager.toggle_theme()

    def _update_icon(self, mode_str: str) -> None:
        """Update button text icon according to active mode."""
        if mode_str == ThemeMode.DARK.value:
            self.setText("☀️ Light")
        else:
            self.setText("🌙 Dark")
