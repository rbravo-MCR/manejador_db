"""Tests for non-blocking live database schema inspection."""

from unittest.mock import MagicMock, patch

from backend_ide.domain.schema import DatabaseSchema
from backend_ide.infrastructure.database.postgresql import PostgreSQLInspector
from backend_ide.infrastructure.database.schema_inspection_worker import SchemaInspectionWorker
from backend_ide.infrastructure.database.sqlite import SQLiteMetadataProvider


def test_schema_worker_emits_database_names_and_schema(qtbot):
    """A successful inspection returns both selector options and the schema model."""
    connection = MagicMock()
    schema = DatabaseSchema(engine_name="postgresql", database_name="db_outlet")
    worker = SchemaInspectionWorker(connection)
    results = []
    worker.signals.succeeded.connect(results.append)

    with (
        patch.object(PostgreSQLInspector, "list_databases", return_value=["db_outlet"]),
        patch.object(PostgreSQLInspector, "inspect_completion_metadata", return_value=schema),
    ):
        worker.run()

    assert results[0].database_names == ("db_outlet",)
    assert results[0].schema is schema


def test_schema_worker_reuses_known_database_names(qtbot):
    """Switching databases should not query the database catalog again."""
    connection = MagicMock()
    schema = DatabaseSchema(engine_name="postgresql", database_name="analytics")
    worker = SchemaInspectionWorker(connection, ("analytics", "db_outlet"))
    results = []
    worker.signals.succeeded.connect(results.append)

    with (
        patch.object(PostgreSQLInspector, "list_databases") as list_databases,
        patch.object(PostgreSQLInspector, "inspect_completion_metadata", return_value=schema),
    ):
        worker.run()

    list_databases.assert_not_called()
    assert results[0].database_names == ("analytics", "db_outlet")


def test_schema_worker_disconnects_candidate_and_emits_failure(qtbot):
    """A failed candidate must be closed and report its useful driver message."""
    connection = MagicMock()
    connection.config.password = "never-log-this"
    worker = SchemaInspectionWorker(connection)
    errors = []
    worker.signals.failed.connect(errors.append)

    with patch.object(
        PostgreSQLInspector,
        "list_databases",
        side_effect=RuntimeError("permission denied for never-log-this"),
    ):
        worker.run()

    connection.disconnect.assert_called_once()
    assert errors == ["permission denied for ••••"]


def test_schema_worker_uses_sqlite_metadata_without_postgresql_catalog_queries(qtbot):
    connection = MagicMock()
    connection.config.engine = "sqlite"
    schema = DatabaseSchema(engine_name="sqlite", database_name="local.sqlite3")
    worker = SchemaInspectionWorker(connection)
    results = []
    worker.signals.succeeded.connect(results.append)

    with (
        patch.object(SQLiteMetadataProvider, "inspect_database", return_value=schema),
        patch.object(PostgreSQLInspector, "list_databases") as postgres_catalog,
    ):
        worker.run()

    postgres_catalog.assert_not_called()
    assert results[0].database_names == ("local.sqlite3",)
    assert results[0].schema is schema
