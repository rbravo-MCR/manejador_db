"""Connection Selector Dropdown Component with Profile Management Actions."""

import qtawesome as qta
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QWidget

from backend_ide.application.connection_service import ConnectionService
from backend_ide.domain.connection import ConnectionProfile, Environment
from backend_ide.ui.theme import ThemeManager


class ConnectionSelector(QWidget):
    """Toolbar connection selector widget with environment indicator and profile dialog launcher."""

    connection_changed = Signal(str)  # Emits selected profile_id
    new_connection_requested = Signal()
    edit_connection_requested = Signal()

    def __init__(self, connection_service: ConnectionService | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(36)
        self.service = connection_service or ConnectionService()
        self._profiles: list[ConnectionProfile] = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._theme_manager = ThemeManager.get_instance()

        self.btn_new = QPushButton("Nueva conexión")
        self.btn_new.setObjectName("secondary_button")
        self.btn_new.setFixedHeight(32)
        self.btn_new.setToolTip("Abrir diálogo para crear una nueva conexión a base de datos")

        self.lbl_profile = QLabel("Perfil:")
        self.combo = QComboBox()
        self.combo.setFixedHeight(32)
        self.combo.setMinimumWidth(180)
        self.combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.env_badge = QLabel(" [DEV] ")
        self.env_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.env_badge.setFixedSize(58, 24)

        self.btn_edit = QPushButton("Editar")
        self.btn_edit.setFixedHeight(32)
        self.btn_edit.setToolTip("Editar parámetros de la conexión seleccionada")

        self.btn_new.clicked.connect(self.new_connection_requested.emit)
        self.btn_edit.clicked.connect(self.edit_connection_requested.emit)
        self.combo.currentIndexChanged.connect(self._on_connection_changed)

        layout.addWidget(self.lbl_profile, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.combo, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.env_badge, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.btn_new, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.btn_edit, alignment=Qt.AlignmentFlag.AlignVCenter)

        self._theme_manager.theme_changed.connect(self._update_action_icons)
        self._update_action_icons()
        self.refresh_profiles()

    def _update_action_icons(self, _mode: str | None = None) -> None:
        """Keep connection action icons readable in the active palette."""
        color = self._theme_manager.current_palette.text_primary
        self.btn_new.setIcon(qta.icon("fa6s.plug-circle-plus", color=color))
        self.btn_edit.setIcon(qta.icon("fa6s.pen-to-square", color=color))
        profile = self.get_selected_profile()
        if profile is not None:
            self._update_badge_style(profile)

    def _update_badge_style(self, profile: ConnectionProfile) -> None:
        """Style the environment badge from semantic theme tokens or user color."""
        palette = self._theme_manager.current_palette
        color_map = {
            Environment.DEVELOPMENT: palette.accent,
            Environment.TESTING: palette.success,
            Environment.STAGING: palette.warning,
            Environment.PRODUCTION: palette.danger,
        }
        bg_color = profile.color or color_map.get(profile.environment, palette.accent)
        self.env_badge.setStyleSheet(
            f"background-color: {bg_color}; color: {palette.text_on_accent}; "
            "font-weight: bold; border-radius: 4px; padding: 2px 6px;"
        )

    def refresh_profiles(self) -> None:
        """Reload saved profiles into combo box."""
        self.combo.blockSignals(True)
        self.combo.clear()

        self._profiles = self.service.list_profiles()
        if not self._profiles:
            # Fallback default profile if empty
            default_p = ConnectionProfile(
                name="PostgreSQL Local", engine="postgresql", environment=Environment.DEVELOPMENT
            )
            self._profiles = [default_p]

        for p in self._profiles:
            self.combo.addItem(f"{p.name} ({p.engine})", p.id)

        self.combo.blockSignals(False)
        self._on_connection_changed(self.combo.currentIndex())

    def get_selected_profile(self) -> ConnectionProfile | None:
        """Return currently selected ConnectionProfile object."""
        idx = self.combo.currentIndex()
        if 0 <= idx < len(self._profiles):
            return self._profiles[idx]
        return None

    def select_profile(self, profile_id: str) -> bool:
        """Select a saved profile by ID and emit the normal change signal."""
        index = self.combo.findData(profile_id)
        if index < 0:
            return False
        self.combo.setCurrentIndex(index)
        return True

    def _on_connection_changed(self, index: int) -> None:
        """Update environment badge styling when selection changes."""
        profile = self.get_selected_profile()
        if not profile:
            return

        env_val = profile.environment.value.upper()
        self.env_badge.setText(f" [{env_val[:4]}] ")

        self._update_badge_style(profile)

        self.connection_changed.emit(profile.id)
