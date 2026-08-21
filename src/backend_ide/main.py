"""Main application entry point for Backend Development IDE."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from backend_ide.ui.views.main_window import MainWindow


def main() -> int:
    """Initialize Qt Application and show MainWindow."""
    app = QApplication(sys.argv)
    app.setApplicationName("Backend Development IDE")
    app.setOrganizationName("BackendIDE")

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
