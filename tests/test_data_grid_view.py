"""Unit tests for the DataGridWidget live table data viewer."""

from __future__ import annotations

from unittest.mock import MagicMock

from backend_ide.domain.schema.enums import NormalizedDataType
from backend_ide.domain.schema.models import Column, PrimaryKey, Table
from backend_ide.ui.views.data_grid_view import DataGridWidget


def test_data_grid_widget_initialization(qtbot):
    """Verify DataGridWidget loads rows, headers, and paging controls."""
    table = Table(
        name="users",
        columns=[
            Column(
                name="id",
                native_type="INT",
                normalized_type=NormalizedDataType.INTEGER,
                is_primary_key=True,
            ),
            Column(
                name="email",
                native_type="VARCHAR",
                normalized_type=NormalizedDataType.VARCHAR,
            ),
        ],
        primary_key=PrimaryKey(column_names=["id"]),
    )

    mock_conn = MagicMock()
    mock_conn.execute_query.side_effect = lambda sql: (
        [{"total": 2}]
        if "COUNT" in sql
        else [
            {"id": 1, "email": "alice@example.com"},
            {"id": 2, "email": "bob@example.com"},
        ]
    )

    widget = DataGridWidget(table, connection=mock_conn)
    qtbot.addWidget(widget)

    assert widget.table_widget.rowCount() == 2
    assert widget.table_widget.columnCount() == 2
    assert widget.table_widget.item(0, 1).text() == "alice@example.com"
    assert "Página 1" in widget.lbl_page.text()
    assert "2 filas totales" in widget.lbl_total.text()
