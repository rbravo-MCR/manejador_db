"""Connection Selector Dropdown Component with Profile Management Actions."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QWidget

from backend_ide.application.connection_service import ConnectionService
from backend_ide.domain.connection import ConnectionProfile, Environment


class ConnectionSelector(QWidget):
    """Toolbar connection selector widget with environment indicator and profile dialog launcher."""

    connection_changed = Signal(str)  # Emits selected profile_id
    new_connection_requested = Signal()
    edit_connection_requested = Signal()

    def __init__(self, connection_service: ConnectionService | None = None, parent=None) -> None:
        super().__init__(parent)
        self.service = connection_service or ConnectionService()
        self._profiles: list[ConnectionProfile] = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(6)

        self.btn_new = QPushButton("🔌 Nueva Conexión")
        self.btn_new.setObjectName("btn_new_conn")
        self.btn_new.setToolTip("Abrir diálogo para crear una nueva conexión a base de datos")

        label = QLabel("Perfil:")
        self.combo = QComboBox()
        self.env_badge = QLabel(" [DEV] ")

        badge_style = (
            "background-color: #89b4fa; color: #181825; "
            "font-weight: bold; border-radius: 4px; padding: 2px 6px;"
        )
        self.env_badge.setStyleSheet(badge_style)

        self.btn_edit = QPushButton("⚙️ Editar")
        self.btn_edit.setToolTip("Editar parámetros de la conexión seleccionada")

        self.btn_new.clicked.connect(self.new_connection_requested.emit)
        self.btn_edit.clicked.connect(self.edit_connection_requested.emit)
        self.combo.currentIndexChanged.connect(self._on_connection_changed)

        layout.addWidget(self.btn_new)
        layout.addWidget(label)
        layout.addWidget(self.combo)
        layout.addWidget(self.env_badge)
        layout.addWidget(self.btn_edit)

        self.refresh_profiles()

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

    def _on_connection_changed(self, index: int) -> None:
        """Update environment badge styling when selection changes."""
        profile = self.get_selected_profile()
        if not profile:
            return

        env_val = profile.environment.value.upper()
        self.env_badge.setText(f" [{env_val[:4]}] ")

        color_map = {
            Environment.DEVELOPMENT: "#89b4fa",
            Environment.TESTING: "#a6e3a1",
            Environment.STAGING: "#f9e2af",
            Environment.PRODUCTION: "#f38ba8",
        }
        bg_color = profile.color or color_map.get(profile.environment, "#89b4fa")
        style = (
            f"background-color: {bg_color}; color: #11111b; "
            "font-weight: bold; border-radius: 4px; padding: 2px 6px;"
        )
        self.env_badge.setStyleSheet(style)

        self.connection_changed.emit(profile.id)
