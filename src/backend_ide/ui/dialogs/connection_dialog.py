"""PySide6 Dialog for Creating and Editing Database Connection Profiles."""

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from backend_ide.application.connection_service import ConnectionService
from backend_ide.domain.connection import ConnectionProfile, Environment


class ConnectionDialog(QDialog):
    """Dialog for editing or creating database connection profiles."""

    def __init__(
        self,
        profile: ConnectionProfile | None = None,
        connection_service: ConnectionService | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.profile = profile or ConnectionProfile(name="Nueva Conexión", engine="postgresql")
        self.service = connection_service or ConnectionService()
        self.password: str | None = None

        self.setWindowTitle(
            "Editar Conexión a Base de Datos" if profile else "Nueva Conexión a Base de Datos"
        )
        self.resize(500, 440)
        self._setup_ui()
        self._load_profile_data()

    def _setup_ui(self) -> None:
        """Construct dialog form layout with Spanish labels."""
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("Ej. Mi PostgreSQL Local")

        self.cmb_engine = QComboBox()
        self.cmb_engine.addItems(["postgresql", "mysql", "sqlite", "sqlserver"])

        self.txt_host = QLineEdit()
        self.txt_host.setPlaceholderText("localhost o 127.0.0.1")

        self.txt_port = QLineEdit()
        self.txt_port.setPlaceholderText("5432")

        self.txt_database = QLineEdit()
        self.txt_database.setPlaceholderText("postgres")

        self.txt_username = QLineEdit()
        self.txt_username.setPlaceholderText("postgres")

        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password.setPlaceholderText("••••••••")

        self.cmb_env = QComboBox()
        self.cmb_env.addItem("Desarrollo (Development)", Environment.DEVELOPMENT.value)
        self.cmb_env.addItem("Pruebas (Testing)", Environment.TESTING.value)
        self.cmb_env.addItem("Staging (Pre-producción)", Environment.STAGING.value)
        self.cmb_env.addItem("Producción (Production)", Environment.PRODUCTION.value)

        self.cmb_color = QComboBox()
        self.cmb_color.addItem("Azul (#89b4fa)", "#89b4fa")
        self.cmb_color.addItem("Verde (#a6e3a1)", "#a6e3a1")
        self.cmb_color.addItem("Amarillo (#f9e2af)", "#f9e2af")
        self.cmb_color.addItem("Rojo (#f38ba8)", "#f38ba8")
        self.cmb_color.addItem("Púrpura (#cba6f7)", "#cba6f7")

        form_layout.addRow("Nombre de Conexión:", self.txt_name)
        form_layout.addRow("Motor de Base de Datos:", self.cmb_engine)
        form_layout.addRow("Host / Servidor:", self.txt_host)
        form_layout.addRow("Puerto:", self.txt_port)
        form_layout.addRow("Base de Datos:", self.txt_database)
        form_layout.addRow("Usuario:", self.txt_username)
        form_layout.addRow("Contraseña:", self.txt_password)
        form_layout.addRow("Entorno:", self.cmb_env)
        form_layout.addRow("Color de Etiqueta:", self.cmb_color)

        layout.addLayout(form_layout)

        # Feedback label
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.lbl_status)

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.btn_test = QPushButton("⚡ Probar Conexión")
        self.btn_save = QPushButton("💾 Guardar Conexión")
        self.btn_cancel = QPushButton("Cancelar")

        self.btn_save.setObjectName("btn_execute")  # Styled as primary action

        self.btn_test.clicked.connect(self._on_test_clicked)
        self.btn_save.clicked.connect(self._on_save_clicked)
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_test)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def _load_profile_data(self) -> None:
        """Load values from profile object into UI controls."""
        self.txt_name.setText(self.profile.name)
        self.txt_host.setText(self.profile.host)
        self.txt_port.setText(str(self.profile.port))
        self.txt_database.setText(self.profile.database)
        self.txt_username.setText(self.profile.username)

        # Select engine index
        idx_engine = self.cmb_engine.findText(self.profile.engine)
        if idx_engine >= 0:
            self.cmb_engine.setCurrentIndex(idx_engine)

        # Select env index
        idx_env = self.cmb_env.findData(self.profile.environment.value)
        if idx_env >= 0:
            self.cmb_env.setCurrentIndex(idx_env)

        existing_pwd = self.service.get_password(self.profile.id)
        if existing_pwd:
            self.txt_password.setText(existing_pwd)

    def _extract_profile_data(self) -> ConnectionProfile:
        """Extract data from UI input fields into ConnectionProfile object."""
        self.profile.name = self.txt_name.text().strip() or "Nueva Conexión"
        self.profile.engine = self.cmb_engine.currentText()
        self.profile.host = self.txt_host.text().strip() or "localhost"

        try:
            self.profile.port = int(self.txt_port.text().strip())
        except ValueError:
            self.profile.port = 5432

        self.profile.database = self.txt_database.text().strip() or "postgres"
        self.profile.username = self.txt_username.text().strip() or "postgres"
        self.profile.environment = Environment(self.cmb_env.currentData())
        self.profile.color = self.cmb_color.currentData()
        self.password = self.txt_password.text()

        return self.profile

    def _on_test_clicked(self) -> None:
        """Execute connection health test."""
        profile = self._extract_profile_data()
        self.lbl_status.setText("Probando conexión...")
        self.lbl_status.setStyleSheet("color: #89b4fa; font-weight: bold;")

        ok = self.service.test_connection(profile, self.password)
        if ok:
            self.lbl_status.setText("✅ ¡Conexión Exitosa!")
            self.lbl_status.setStyleSheet("color: #a6e3a1; font-weight: bold;")
        else:
            self.lbl_status.setText("❌ ¡Error de Conexión! (Revisar host/puerto/credenciales)")
            self.lbl_status.setStyleSheet("color: #f38ba8; font-weight: bold;")

    def _on_save_clicked(self) -> None:
        """Save connection profile and close dialog."""
        profile = self._extract_profile_data()
        self.service.save_profile(profile, self.password)
        self.accept()
