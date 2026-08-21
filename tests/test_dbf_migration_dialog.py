"""GUI tests for DBFMigrationDialog."""

from __future__ import annotations

import os

import pytest

from backend_ide.ui.dialogs.dbf_migration_dialog import DBFMigrationDialog
from tests.test_legacy_dbf import create_sample_dbf_file


@pytest.fixture
def dialog_dbf_directory(tmp_path: os.PathLike) -> str:
    """Fixture providing DBF files for dialog testing."""
    folder = str(tmp_path)
    clients_data = [
        {"ID": 101, "NAME": "Acme Corp", "BALANCE": 1500.50, "ACTIVE": True, "CREATED": "20250115"},
        {
            "ID": 102,
            "NAME": "Globex Inc",
            "BALANCE": 340.00,
            "ACTIVE": False,
            "CREATED": "20250220",
        },
        {"ID": 103, "NAME": "Initech LLC", "BALANCE": 0.00, "ACTIVE": True, "CREATED": "20250310"},
    ]
    create_sample_dbf_file(os.path.join(folder, "CLIENTES.DBF"), clients_data)

    products_data = [
        {
            "ID": 501,
            "NAME": "Laptop Pro 15",
            "BALANCE": 1299.99,
            "ACTIVE": True,
            "CREATED": "20241101",
        },
        {
            "ID": 502,
            "NAME": "Wireless Mouse",
            "BALANCE": 29.50,
            "ACTIVE": True,
            "CREATED": "20241115",
        },
    ]
    create_sample_dbf_file(os.path.join(folder, "PRODUCTOS.DBF"), products_data)
    return folder


def test_dbf_migration_dialog_init(qtbot, dialog_dbf_directory: str):
    """Dialog must initialize cleanly and scan tables upon request."""
    dialog = DBFMigrationDialog()
    qtbot.addWidget(dialog)

    assert dialog.windowTitle() == "Migrador de Tablas DBF (dBase / FoxPro / Clipper)"
    assert dialog.table_grid.columnCount() == 6

    # Set directory and scan
    dialog.txt_folder.setText(dialog_dbf_directory)
    dialog._scan_directory()

    assert dialog.table_grid.rowCount() == 2

    # Check table 0
    t0_name = dialog.table_grid.item(0, 0).text()
    t0_count = dialog.table_grid.item(0, 1).text()
    assert t0_name == "CLIENTES"
    assert t0_count == "3"

    # Check table 1
    t1_name = dialog.table_grid.item(1, 0).text()
    t1_count = dialog.table_grid.item(1, 1).text()
    assert t1_name == "PRODUCTOS"
    assert t1_count == "2"
