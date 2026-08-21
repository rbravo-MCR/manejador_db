"""UI Tests for CodeGenerationDialog."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QPlainTextEdit

from backend_ide.domain.schema.enums import NormalizedDataType
from backend_ide.domain.schema.models import Column, DatabaseSchema, PrimaryKey, Schema, Table
from backend_ide.generators.contracts import GenerationTarget
from backend_ide.ui.dialogs.code_generation_dialog import CodeGenerationDialog


@pytest.fixture
def sample_schema_for_dialog() -> DatabaseSchema:
    """Fixture providing sample schema for dialog testing."""
    users_table = Table(
        name="users",
        schema_name="public",
        columns=[
            Column(
                name="id",
                native_type="INT",
                normalized_type=NormalizedDataType.INTEGER,
                is_primary_key=True,
                is_auto_increment=True,
            ),
            Column(
                name="email",
                native_type="VARCHAR(255)",
                normalized_type=NormalizedDataType.VARCHAR,
                length=255,
            ),
        ],
        primary_key=PrimaryKey(column_names=["id"]),
    )

    orders_table = Table(
        name="orders",
        schema_name="public",
        columns=[
            Column(
                name="id",
                native_type="INT",
                normalized_type=NormalizedDataType.INTEGER,
                is_primary_key=True,
                is_auto_increment=True,
            ),
            Column(
                name="total",
                native_type="DECIMAL(10,2)",
                normalized_type=NormalizedDataType.DECIMAL,
                precision=10,
                scale=2,
            ),
        ],
        primary_key=PrimaryKey(column_names=["id"]),
    )

    return DatabaseSchema(
        engine_name="postgresql",
        database_name="shop_db",
        schemas=[Schema(name="public", tables=[users_table, orders_table])],
    )


def test_code_generation_dialog_initialization(qtbot, sample_schema_for_dialog):
    """Dialog must initialize with targets, table list, and initial code preview."""
    dialog = CodeGenerationDialog(sample_schema_for_dialog, selected_table_name="users")
    qtbot.addWidget(dialog)

    assert dialog.cmb_target.count() >= 10
    assert dialog.lst_tables.count() == 2
    assert dialog.tab_files.count() >= 1

    # Current preview should contain SQLAlchemy User model by default
    current_editor = dialog.tab_files.currentWidget()
    assert isinstance(current_editor, QPlainTextEdit)
    assert "class User(Base):" in current_editor.toPlainText()


def test_code_generation_dialog_target_switch(qtbot, sample_schema_for_dialog):
    """Switching target dropdown dynamically re-renders preview in new language/ORM."""
    dialog = CodeGenerationDialog(sample_schema_for_dialog)
    qtbot.addWidget(dialog)

    # Switch to Prisma
    idx = dialog.cmb_target.findData(GenerationTarget.PRISMA)
    assert idx >= 0
    dialog.cmb_target.setCurrentIndex(idx)

    current_editor = dialog.tab_files.currentWidget()
    assert "model User {" in current_editor.toPlainText()
    assert "model Order {" in current_editor.toPlainText()


def test_code_generation_dialog_export_to_directory(qtbot, sample_schema_for_dialog, tmp_path):
    """Export button must write generated files to disk in destination folder."""
    dialog = CodeGenerationDialog(sample_schema_for_dialog)
    qtbot.addWidget(dialog)

    # Switch to Eloquent (multi-file generator)
    idx = dialog.cmb_target.findData(GenerationTarget.ELOQUENT)
    dialog.cmb_target.setCurrentIndex(idx)

    export_dir = str(tmp_path / "exported_backend")

    with (
        patch("PySide6.QtWidgets.QFileDialog.getExistingDirectory", return_value=export_dir),
        patch("PySide6.QtWidgets.QMessageBox.information") as mock_msg,
    ):
        dialog._export_to_directory()

        user_file = os.path.join(export_dir, "app/Models/User.php")
        order_file = os.path.join(export_dir, "app/Models/Order.php")

        assert os.path.exists(user_file)
        assert os.path.exists(order_file)

        with open(user_file, encoding="utf-8") as f:
            assert "class User extends Model" in f.read()

        assert mock_msg.called
