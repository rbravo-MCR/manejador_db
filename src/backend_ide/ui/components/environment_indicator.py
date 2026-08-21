"""Non-interactive semantic indicator for a connection environment."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget

from backend_ide.domain.connection import Environment

ENVIRONMENT_LABELS = {
    Environment.DEVELOPMENT: "Desarrollo",
    Environment.TESTING: "Pruebas",
    Environment.STAGING: "Preproducción",
    Environment.PRODUCTION: "Producción",
}


def environment_label(environment: Environment | None) -> str:
    """Return the presentation label shared by connection context surfaces."""
    return ENVIRONMENT_LABELS.get(environment, "Sin entorno")


class EnvironmentIndicator(QWidget):
    """Display connection context as a semantic dot and an explicit label."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("environment_indicator")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(24)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.dot = QLabel()
        self.dot.setObjectName("environment_dot")
        self.dot.setFixedSize(8, 8)
        self.dot.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.text_label = QLabel()
        self.text_label.setObjectName("environment_text")
        self.text_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        layout.addWidget(self.dot, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.text_label, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.set_environment(None)

    def set_environment(self, environment: Environment | None) -> None:
        """Update semantic state without making the context look interactive."""
        state = environment.value if environment is not None else "none"
        label = environment_label(environment)
        self.dot.setProperty("environment", state)
        self.text_label.setText(label)
        self.setAccessibleName(f"Entorno: {label}")
        self.setToolTip(f"Entorno de conexión: {label}")
        self.dot.style().unpolish(self.dot)
        self.dot.style().polish(self.dot)
