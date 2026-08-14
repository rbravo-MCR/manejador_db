"""Non-blocking background Query Worker for PySide6 using QRunnable."""

import time

from PySide6.QtCore import QObject, QRunnable, Signal

from backend_ide.domain.sql import ColumnMetadata, QueryRequest, QueryResult
from backend_ide.infrastructure.database.contracts import DatabaseConnection
from backend_ide.infrastructure.logging import get_logger

logger = get_logger(__name__)


class QueryWorkerSignals(QObject):
    """Qt signals for background QueryWorker."""

    finished = Signal(QueryResult)
    failed = Signal(str)


class QueryWorker(QRunnable):
    """Worker task executing database queries off the Qt UI thread."""

    def __init__(self, connection: DatabaseConnection, request: QueryRequest) -> None:
        super().__init__()
        self.connection = connection
        self.request = request
        self.signals = QueryWorkerSignals()

    def run(self) -> None:
        """Execute database query in background worker thread."""
        logger.info("Executing background query", sql=self.request.sql[:100])
        start_time = time.perf_counter()

        try:
            raw_results = self.connection.execute_query(self.request.sql, self.request.params)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            columns: list[ColumnMetadata] = []
            if raw_results and len(raw_results) > 0:
                first_row = raw_results[0]
                columns = [ColumnMetadata(name=k) for k in first_row.keys()]

            result = QueryResult(
                columns=columns,
                rows=raw_results,
                execution_time_ms=round(elapsed_ms, 2),
                rows_affected=len(raw_results),
                has_error=False,
            )
            self.signals.finished.emit(result)

        except Exception as err:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            error_msg = str(err)
            logger.error("Query execution error", error=error_msg)

            result = QueryResult(
                columns=[],
                rows=[],
                execution_time_ms=round(elapsed_ms, 2),
                rows_affected=0,
                has_error=True,
                error_message=error_msg,
            )
            self.signals.finished.emit(result)
            self.signals.failed.emit(error_msg)
