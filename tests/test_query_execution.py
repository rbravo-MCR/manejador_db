"""Unit and Integration tests for Phase 6 - Query Execution, Worker, and Results Grid."""

import os
from unittest.mock import MagicMock

from PySide6.QtCore import QThreadPool

from backend_ide.application.query_service import ExecuteQueryService
from backend_ide.domain.sql import ColumnMetadata, QueryRequest, QueryResult
from backend_ide.infrastructure.database.query_worker import QueryWorker
from backend_ide.ui.results import ResultsWidget

os.environ["QT_QPA_PLATFORM"] = "offscreen"


def test_query_request_and_result_models():
    """Test QueryRequest and QueryResult models and properties."""
    req = QueryRequest(sql="SELECT * FROM users WHERE active = :status", params={"status": True})
    assert req.sql.startswith("SELECT")
    assert req.params == {"status": True}

    res = QueryResult(
        columns=[ColumnMetadata(name="id"), ColumnMetadata(name="name")],
        rows=[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
        execution_time_ms=15.2,
        rows_affected=2,
    )
    assert res.row_count == 2
    assert res.execution_time_ms == 15.2
    assert res.has_error is False


def test_execute_query_service_sync_and_export(tmp_path):
    """Test ExecuteQueryService sync execution and exporting to CSV/JSON."""
    service = ExecuteQueryService()
    mock_conn = MagicMock()
    mock_conn.execute_query.return_value = [
        {"id": 1, "email": "alice@example.com"},
        {"id": 2, "email": "bob@example.com"},
    ]

    req = QueryRequest(sql="SELECT id, email FROM users;")
    result = service.execute_sync(mock_conn, req)

    assert result.has_error is False
    assert result.row_count == 2
    assert len(result.columns) == 2

    # Test CSV export
    csv_file = tmp_path / "export.csv"
    service.export_to_csv(result, csv_file)
    assert csv_file.exists()
    csv_content = csv_file.read_text()
    assert "id,email" in csv_content
    assert "alice@example.com" in csv_content

    # Test JSON export
    json_file = tmp_path / "export.json"
    service.export_to_json(result, json_file)
    assert json_file.exists()
    json_content = json_file.read_text()
    assert "bob@example.com" in json_content


def test_query_worker_background_execution(qtbot):
    """Test QueryWorker executing in QThreadPool and emitting signals without blocking UI."""
    mock_conn = MagicMock()
    mock_conn.execute_query.return_value = [{"col1": "val1"}]

    req = QueryRequest(sql="SELECT 1;")
    worker = QueryWorker(mock_conn, req)

    finished_result: list[QueryResult] = []

    def handle_finished(res: QueryResult):
        finished_result.append(res)

    worker.signals.finished.connect(handle_finished)

    pool = QThreadPool.globalInstance()
    pool.start(worker)
    pool.waitForDone(2000)

    # Wait for Qt event loop to deliver cross-thread signal
    qtbot.waitUntil(lambda: len(finished_result) == 1, timeout=2000)

    assert len(finished_result) == 1
    assert finished_result[0].row_count == 1
    assert finished_result[0].rows[0]["col1"] == "val1"


def test_results_widget_grid_and_error_display(qtbot):
    """Test ResultsWidget table model population and error view switching."""
    results_widget = ResultsWidget()
    qtbot.addWidget(results_widget)

    # 1. Success Result
    success_res = QueryResult(
        columns=[ColumnMetadata(name="id"), ColumnMetadata(name="title")],
        rows=[{"id": 100, "title": "First Post"}],
        execution_time_ms=8.5,
    )
    results_widget.display_result(success_res)

    assert results_widget.results_tabs.currentWidget() == results_widget.table_view
    assert results_widget.table_model.rowCount() == 1
    assert results_widget.table_model.columnCount() == 2
    assert "8.5 ms" in results_widget.lbl_stats.text()

    # 2. Error Result
    error_res = QueryResult(
        columns=[],
        rows=[],
        execution_time_ms=4.1,
        has_error=True,
        error_message="relation 'invalid_table' does not exist",
    )
    results_widget.display_result(error_res)

    assert results_widget.results_tabs.currentWidget() == results_widget.txt_messages
    assert "invalid_table" in results_widget.txt_messages.toPlainText()


def test_results_actions_are_aligned_and_emoji_free(qtbot):
    """Adding extra action rows or emoji labels must fail."""
    results = ResultsWidget()
    qtbot.addWidget(results)
    layout = results.action_bar.layout()

    assert layout.itemAt(0).widget() is results.lbl_stats
    assert layout.itemAt(layout.count() - 2).widget() is results.txt_filter_grid
    assert layout.itemAt(layout.count() - 1).widget() is results.btn_export
    assert results.txt_filter_grid.height() == 32
    assert results.btn_export.height() == 32
    assert "📥" not in results.btn_export.text()
