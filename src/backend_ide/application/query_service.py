"""Application Service for SQL Query Execution and Data Export."""

import csv
import json
import time
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QThreadPool

from backend_ide.domain.sql import ColumnMetadata, QueryRequest, QueryResult
from backend_ide.infrastructure.database.contracts import DatabaseConnection
from backend_ide.infrastructure.database.query_worker import QueryWorker
from backend_ide.infrastructure.logging import get_logger

logger = get_logger(__name__)


class ExecuteQueryService:
    """Service orchestrating non-blocking query execution and CSV/JSON data exports."""

    def __init__(self, thread_pool: QThreadPool | None = None) -> None:
        self.thread_pool = thread_pool or QThreadPool.globalInstance()

    def execute_async(
        self,
        connection: DatabaseConnection,
        request: QueryRequest,
        on_finished: Callable[[QueryResult], None],
        on_failed: Callable[[str], None] | None = None,
    ) -> QueryWorker:
        """Dispatch query execution to background thread pool."""
        worker = QueryWorker(connection, request)
        worker.signals.finished.connect(on_finished)
        if on_failed:
            worker.signals.failed.connect(on_failed)

        self.thread_pool.start(worker)
        return worker

    def execute_sync(self, connection: DatabaseConnection, request: QueryRequest) -> QueryResult:
        """Execute query synchronously (for testing or CLI batch processing)."""
        start_time = time.perf_counter()
        try:
            raw_results = connection.execute_query(request.sql, request.params)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            columns: list[ColumnMetadata] = []
            if raw_results and len(raw_results) > 0:
                first_row = raw_results[0]
                columns = [ColumnMetadata(name=k) for k in first_row.keys()]

            return QueryResult(
                columns=columns,
                rows=raw_results,
                execution_time_ms=round(elapsed_ms, 2),
                rows_affected=len(raw_results),
                has_error=False,
            )
        except Exception as err:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            error_msg = str(err)
            return QueryResult(
                columns=[],
                rows=[],
                execution_time_ms=round(elapsed_ms, 2),
                rows_affected=0,
                has_error=True,
                error_message=error_msg,
            )

    def export_to_csv(self, result: QueryResult, file_path: Path) -> None:
        """Export query result dataset to CSV file."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if not result.rows:
            file_path.write_text("", encoding="utf-8")
            return

        headers = [c.name for c in result.columns]
        with file_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(result.rows)

        logger.info("Exported query results to CSV", path=str(file_path), count=len(result.rows))

    def export_to_json(self, result: QueryResult, file_path: Path) -> None:
        """Export query result dataset to JSON file."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(result.rows, f, indent=2, default=str)

        logger.info("Exported query results to JSON", path=str(file_path), count=len(result.rows))
