"""Non-blocking worker used to test a database connection from the desktop UI."""

from collections.abc import Callable

from PySide6.QtCore import QObject, QRunnable, Signal


class ConnectionTestSignals(QObject):
    """Signals emitted when a connection test finishes."""

    finished = Signal(bool)


class ConnectionTestWorker(QRunnable):
    """Run a potentially slow connection attempt outside the Qt UI thread."""

    def __init__(self, test_connection: Callable[[], bool]) -> None:
        super().__init__()
        self._test_connection = test_connection
        self.signals = ConnectionTestSignals()

    def run(self) -> None:
        """Execute the supplied connection test and always return a safe result."""
        try:
            succeeded = self._test_connection()
        except Exception:
            succeeded = False
        self.signals.finished.emit(succeeded)
