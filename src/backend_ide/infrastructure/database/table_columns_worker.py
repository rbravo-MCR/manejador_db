"""Background worker for lazily loading a single PostgreSQL table's fields."""

from PySide6.QtCore import QObject, QRunnable, Signal

from backend_ide.infrastructure.database.contracts import DatabaseConnection
from backend_ide.infrastructure.database.postgresql import PostgreSQLInspector
from backend_ide.infrastructure.logging import get_logger

logger = get_logger(__name__)


class TableColumnsSignals(QObject):
    """Signals for table-column loading results."""

    succeeded = Signal(str, str, object)
    failed = Signal(str, str, str)
    finished = Signal(str, str)


class TableColumnsWorker(QRunnable):
    """Load one table's fields through a short-lived database adapter."""

    def __init__(self, connection: DatabaseConnection, schema_name: str, table_name: str) -> None:
        super().__init__()
        self.connection = connection
        self.schema_name = schema_name
        self.table_name = table_name
        self.signals = TableColumnsSignals()

    def run(self) -> None:
        """Inspect fields and always release the transient connection."""
        try:
            columns = PostgreSQLInspector(self.connection).inspect_table_columns(
                self.schema_name,
                self.table_name,
            )
            self.signals.succeeded.emit(self.schema_name, self.table_name, columns)
        except Exception as err:
            self.signals.failed.emit(self.schema_name, self.table_name, self._sanitize(str(err)))
        finally:
            try:
                self.connection.disconnect()
            except Exception as err:
                logger.warning(
                    "Failed to close table metadata connection", error=self._sanitize(str(err))
                )
            self.signals.finished.emit(self.schema_name, self.table_name)

    def _sanitize(self, message: str) -> str:
        """Remove a password if a database driver included it in its error."""
        config = getattr(self.connection, "config", None)
        password = getattr(config, "password", None)
        return (
            message.replace(password, "••••") if isinstance(password, str) and password else message
        )
