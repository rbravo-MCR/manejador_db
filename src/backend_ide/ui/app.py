"""PySide6 Application Launcher and Entry Point."""

import sys

from PySide6.QtWidgets import QApplication

from backend_ide.infrastructure.logging import configure_logging, get_logger
from backend_ide.ui.views.main_window import MainWindow

logger = get_logger(__name__)


def create_app(argv: list[str] | None = None) -> tuple[QApplication, MainWindow]:
    """Create and configure QApplication and MainWindow."""
    configure_logging("INFO")
    logger.info("Initializing Backend IDE PySide6 Application")

    app = QApplication.instance()
    if app is None:
        app = QApplication(argv or sys.argv)

    window = MainWindow()
    return app, window


def main() -> None:
    """Main CLI entry point."""
    app, window = create_app()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
