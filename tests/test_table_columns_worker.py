"""Tests for lazy table-column loading."""

from unittest.mock import MagicMock, patch

from backend_ide.domain.schema import Column, NormalizedDataType
from backend_ide.infrastructure.database.postgresql import PostgreSQLInspector
from backend_ide.infrastructure.database.table_columns_worker import TableColumnsWorker


def test_table_columns_worker_emits_fields_and_closes_transient_connection(qtbot):
    """A table expansion returns fields and releases its short-lived adapter."""
    connection = MagicMock()
    columns = [Column(name="id", native_type="INTEGER", normalized_type=NormalizedDataType.INTEGER)]
    worker = TableColumnsWorker(connection, "public", "customers")
    results = []
    worker.signals.succeeded.connect(
        lambda schema, table, items: results.append((schema, table, items))
    )

    with patch.object(PostgreSQLInspector, "inspect_table_columns", return_value=columns):
        worker.run()

    assert results == [("public", "customers", columns)]
    connection.disconnect.assert_called_once()


def test_table_columns_worker_reports_failure_and_closes_connection(qtbot):
    """Column permission failures remain local to the expanded table."""
    connection = MagicMock()
    worker = TableColumnsWorker(connection, "private", "secrets")
    errors = []
    worker.signals.failed.connect(
        lambda schema, table, message: errors.append((schema, table, message))
    )

    with patch.object(
        PostgreSQLInspector,
        "inspect_table_columns",
        side_effect=RuntimeError("permission denied"),
    ):
        worker.run()

    assert errors == [("private", "secrets", "permission denied")]
    connection.disconnect.assert_called_once()
