"""PySide6 Dialog for Creating and Editing Database Connection Profiles."""

from __future__ import annotations

from pathlib import Path

import qtawesome as qta
from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from backend_ide.application.connection_service import ConnectionService
from backend_ide.domain.connection import ConnectionProfile, Environment
from backend_ide.infrastructure.database.connection_test_worker import ConnectionTestWorker


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
        self._thread_pool = QThreadPool.globalInstance()
        self._connection_test_worker: ConnectionTestWorker | None = None

        self.setWindowTitle(
            "Editar Conexión a Base de Datos" if profile else "Nueva Conexión a Base de Datos"
        )
        self.resize(540, 520)
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
        self.cmb_engine.addItems(["postgresql", "sqlite", "mysql", "sqlserver"])
        self.cmb_engine.currentTextChanged.connect(self._on_engine_changed)

        self.txt_host = QLineEdit()
        self.txt_host.setPlaceholderText("localhost o 127.0.0.1")

        self.txt_port = QLineEdit()
        self.txt_port.setPlaceholderText("5432")

        # Database field with file browse button for SQLite
        db_layout = QHBoxLayout()
        self.txt_database = QLineEdit()
        self.txt_database.setPlaceholderText("postgres")
        self.btn_browse_db = QPushButton("Examinar…")
        self.btn_browse_db.setIcon(qta.icon("fa6s.folder-open"))
        self.btn_browse_db.clicked.connect(self._on_browse_db_file)
        self.btn_browse_db.setVisible(False)
        db_layout.addWidget(self.txt_database)
        db_layout.addWidget(self.btn_browse_db)

        self.txt_username = QLineEdit()
        self.txt_username.setPlaceholderText("postgres")

        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password.setPlaceholderText("••••••••")
        self.password_visibility_action = self.txt_password.addAction(
            qta.icon("fa6s.eye-slash", color="#a6adc8"),
            QLineEdit.ActionPosition.TrailingPosition,
        )
        self.password_visibility_action.setText("Mostrar contraseña")
        self.password_visibility_action.setToolTip("Mostrar contraseña")
        self.password_visibility_action.triggered.connect(self._toggle_password_visibility)

        self.cmb_ssl = QComboBox()
        self.cmb_ssl.addItem("Require — SSL obligatorio", "require")
        self.cmb_ssl.addItem("Prefer — usar SSL si está disponible", "prefer")
        self.cmb_ssl.addItem("None — sin SSL", "disable")
        self.cmb_ssl.setToolTip(
            "Amazon RDS normalmente requiere 'Require'. 'None' se envía como sslmode=disable."
        )

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
        form_layout.addRow("Base de Datos:", db_layout)
        form_layout.addRow("Usuario:", self.txt_username)
        form_layout.addRow("Contraseña:", self.txt_password)
        form_layout.addRow("SSL mode:", self.cmb_ssl)
        form_layout.addRow("Entorno:", self.cmb_env)
        form_layout.addRow("Color de Etiqueta:", self.cmb_color)

        layout.addLayout(form_layout)

        # Feedback label
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("font-weight: bold;")
        self.lbl_status.setWordWrap(True)
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

    def _on_engine_changed(self, engine: str) -> None:
        """Adjust UI controls based on selected database engine."""
        is_sqlite = engine == "sqlite"
        self.btn_browse_db.setVisible(is_sqlite)
        self.txt_host.setEnabled(not is_sqlite)
        self.txt_port.setEnabled(not is_sqlite)
        self.txt_username.setEnabled(not is_sqlite)
        self.txt_password.setEnabled(not is_sqlite)
        self.cmb_ssl.setEnabled(not is_sqlite)

        if is_sqlite:
            self.txt_database.setPlaceholderText("/ruta/a/base_datos.sqlite o :memory:")
        elif engine == "mysql":
            self.txt_database.setPlaceholderText("mi_base_de_datos")
            if not self.txt_port.text() or self.txt_port.text() in ("5432", "1433"):
                self.txt_port.setText("3306")
        elif engine == "sqlserver":
            self.txt_database.setPlaceholderText("mi_base_de_datos")
            if not self.txt_port.text() or self.txt_port.text() in ("5432", "3306"):
                self.txt_port.setText("1433")
        else:  # postgresql
            self.txt_database.setPlaceholderText("postgres")
            if not self.txt_port.text() or self.txt_port.text() in ("3306", "1433"):
                self.txt_port.setText("5432")

    def _on_browse_db_file(self) -> None:
        """Browse SQLite database file on disk."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Base de Datos SQLite",
            "",
            "Bases de Datos SQLite (*.sqlite *.db *.sqlite3 *.s3db);;Todos los archivos (*)",
        )
        if file_path:
            self.txt_database.setText(file_path)
            if not self.txt_name.text() or self.txt_name.text() == "Nueva Conexión":
                self.txt_name.setText(Path(file_path).stem)

    def _toggle_password_visibility(self) -> None:
        """Reveal or protect the password and keep the action state synchronized."""
        is_protected = self.txt_password.echoMode() == QLineEdit.EchoMode.Password
        if is_protected:
            self.txt_password.setEchoMode(QLineEdit.EchoMode.Normal)
            label = "Ocultar contraseña"
            icon_name = "fa6s.eye"
        else:
            self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
            label = "Mostrar contraseña"
            icon_name = "fa6s.eye-slash"

        self.password_visibility_action.setIcon(qta.icon(icon_name, color="#a6adc8"))
        self.password_visibility_action.setText(label)
        self.password_visibility_action.setToolTip(label)

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

        self._on_engine_changed(self.profile.engine)

        # Select env index
        idx_env = self.cmb_env.findData(self.profile.environment.value)
        if idx_env >= 0:
            self.cmb_env.setCurrentIndex(idx_env)

        idx_ssl = self.cmb_ssl.findData(self.profile.ssl_mode)
        if idx_ssl >= 0:
            self.cmb_ssl.setCurrentIndex(idx_ssl)

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
        self.profile.ssl_mode = self.cmb_ssl.currentData()
        self.profile.environment = Environment(self.cmb_env.currentData())
        self.profile.color = self.cmb_color.currentData()
        self.password = self.txt_password.text()

        return self.profile

    def _validate_required_fields(self) -> bool:
        """Mark missing or invalid connection values before any network operation."""
        engine = self.cmb_engine.currentText()
        if engine == "sqlite":
            required_fields = (
                ("Nombre de Conexión", self.txt_name),
                ("Base de Datos", self.txt_database),
            )
        else:
            required_fields = (
                ("Nombre de Conexión", self.txt_name),
                ("Host / Servidor", self.txt_host),
                ("Puerto", self.txt_port),
                ("Base de Datos", self.txt_database),
                ("Usuario", self.txt_username),
            )

        invalid_names: list[str] = []
        invalid_style = "border: 1px solid #f38ba8;"

        for label, field in required_fields:
            field.setStyleSheet("")
            if not field.text().strip():
                invalid_names.append(label)
                field.setStyleSheet(invalid_style)

        if engine != "sqlite":
            port_text = self.txt_port.text().strip()
            if port_text:
                try:
                    port = int(port_text)
                    port_is_valid = 1 <= port <= 65535
                except ValueError:
                    port_is_valid = False
                if not port_is_valid:
                    if "Puerto" not in invalid_names:
                        invalid_names.append("Puerto")
                    self.txt_port.setStyleSheet(invalid_style)

        if not invalid_names:
            return True

        self.lbl_status.setText(f"Completa o corrige: {', '.join(invalid_names)}.")
        self.lbl_status.setStyleSheet("color: #f38ba8; font-weight: bold;")
        return False

    def _on_test_clicked(self) -> None:
        """Execute the connection health test without blocking the desktop UI."""
        if not self._validate_required_fields():
            return
        profile = self._extract_profile_data()
        self.lbl_status.setText("Probando conexión...")
        self.lbl_status.setStyleSheet("color: #89b4fa; font-weight: bold;")
        self.btn_test.setEnabled(False)
        self.btn_test.setText("Probando…")

        worker = ConnectionTestWorker(lambda: self.service.test_connection(profile, self.password))
        worker.signals.finished.connect(self._on_test_finished)
        self._connection_test_worker = worker
        self._thread_pool.start(worker)

    def _on_test_finished(self, ok: bool) -> None:
        """Restore controls and show the connection test result."""
        self.btn_test.setEnabled(True)
        self.btn_test.setText("⚡ Probar Conexión")
        if ok:
            self.lbl_status.setText("✅ ¡Conexión Exitosa!")
            self.lbl_status.setStyleSheet("color: #a6e3a1; font-weight: bold;")
        else:
            self.lbl_status.setText("❌ ¡Error de Conexión! (Revisar host/puerto/credenciales)")
            self.lbl_status.setStyleSheet("color: #f38ba8; font-weight: bold;")
        self._connection_test_worker = None

    def _on_save_clicked(self) -> None:
        """Save connection profile and close dialog."""
        if not self._validate_required_fields():
            return
        profile = self._extract_profile_data()
        self.service.save_profile(profile, self.password)
        self.accept()
