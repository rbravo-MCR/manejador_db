"""Background worker for discovering databases and inspecting live PostgreSQL schemas."""

from dataclasses import dataclass

from PySide6.QtCore import QObject, QRunnable, Signal

from backend_ide.domain.schema import DatabaseSchema
from backend_ide.infrastructure.database.contracts import DatabaseConnection
from backend_ide.infrastructure.database.postgresql import PostgreSQLInspector
from backend_ide.infrastructure.database.sqlite import SQLiteMetadataProvider
from backend_ide.infrastructure.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class DatabaseInspectionResult:
    """Database selector values and the inspected model for the active database."""

    database_names: tuple[str, ...]
    schema: DatabaseSchema


class SchemaInspectionSignals(QObject):
    """Qt signals emitted by a schema inspection task."""

    succeeded = Signal(object)
    failed = Signal(str)
    finished = Signal()


class SchemaInspectionWorker(QRunnable):
    """Discover and inspect PostgreSQL metadata outside the Qt UI thread."""

    def __init__(
        self,
        connection: DatabaseConnection,
        database_names: tuple[str, ...] | None = None,
    ) -> None:
        super().__init__()
        self.connection = connection
        self.database_names = database_names
        self.signals = SchemaInspectionSignals()

    def run(self) -> None:
        """Inspect the candidate connection and emit an atomic result."""
        try:
            engine = getattr(getattr(self.connection, "config", None), "engine", "postgresql")
            if engine == "sqlite":
                schema = SQLiteMetadataProvider(self.connection).inspect_database()
                self.signals.succeeded.emit(
                    DatabaseInspectionResult((schema.database_name,), schema)
                )
                return
            inspector = PostgreSQLInspector(self.connection)
            names = self.database_names
            if names is None:
                names = tuple(inspector.list_databases())
            schema = inspector.inspect_completion_metadata()
            self.signals.succeeded.emit(DatabaseInspectionResult(tuple(names), schema))
        except Exception as err:
            message = self._sanitize_error(str(err))
            try:
                self.connection.disconnect()
            except Exception as disconnect_error:
                logger.warning(
                    "Failed to close rejected database connection",
                    error=self._sanitize_error(str(disconnect_error)),
                )
            self.signals.failed.emit(message)
        finally:
            self.signals.finished.emit()

    def _sanitize_error(self, message: str) -> str:
        """Remove the candidate password if a driver includes it in an error."""
        config = getattr(self.connection, "config", None)
        password = getattr(config, "password", None)
        if password:
            return message.replace(password, "••••")
        return message
