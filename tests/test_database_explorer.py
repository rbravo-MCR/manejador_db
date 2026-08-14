"""Unit and GUI integration tests for Phase 5 - Database Explorer."""

import os

from backend_ide.domain.schema import (
    Column,
    DatabaseSchema,
    NormalizedDataType,
    PrimaryKey,
    Schema,
    Table,
)
from backend_ide.ui.explorer import DatabaseExplorerWidget

os.environ["QT_QPA_PLATFORM"] = "offscreen"


def create_sample_schema() -> DatabaseSchema:
    """Helper to create sample DatabaseSchema for explorer testing."""
    users_table = Table(
        name="users",
        schema_name="public",
        columns=[
            Column(
                name="id",
                native_type="INT",
                normalized_type=NormalizedDataType.INTEGER,
                is_nullable=False,
                is_auto_increment=True,
                is_primary_key=True,
            ),
            Column(
                name="email",
                native_type="VARCHAR(255)",
                normalized_type=NormalizedDataType.VARCHAR,
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
                native_type="BIGINT",
                normalized_type=NormalizedDataType.BIGINT,
                is_nullable=False,
                is_primary_key=True,
            ),
            Column(
                name="total",
                native_type="DECIMAL(10,2)",
                normalized_type=NormalizedDataType.DECIMAL,
            ),
        ],
        primary_key=PrimaryKey(column_names=["id"]),
    )

    return DatabaseSchema(
        engine_name="postgresql",
        database_name="shop_db",
        schemas=[Schema(name="public", tables=[users_table, orders_table])],
    )


def test_explorer_widget_initialization(qtbot):
    """Test DatabaseExplorerWidget creation and components."""
    explorer = DatabaseExplorerWidget()
    qtbot.addWidget(explorer)

    assert explorer.txt_filter is not None
    assert explorer.tree is not None
    assert explorer.tree.topLevelItemCount() == 0


def test_explorer_model_loading_and_lazy_loading(qtbot):
    """Test loading Universal Schema Model into explorer and expanding nodes dynamically."""
    explorer = DatabaseExplorerWidget()
    qtbot.addWidget(explorer)

    sample_db = create_sample_schema()
    explorer.load_schema_model("Test Connection", sample_db)

    assert explorer.tree.topLevelItemCount() == 1
    conn_item = explorer.tree.topLevelItem(0)
    assert "Test Connection" in conn_item.text(0)

    db_item = conn_item.child(0)
    assert "shop_db" in db_item.text(0)

    schema_item = db_item.child(0)
    assert "public" in schema_item.text(0)

    # Expand schema item to trigger lazy loading
    explorer._on_item_expanded(schema_item)
    assert schema_item.is_loaded is True
    assert schema_item.childCount() == 1  # Tables Group

    tables_group = schema_item.child(0)
    assert tables_group.childCount() == 2  # users, orders


def test_explorer_search_filtering(qtbot):
    """Test typing into filter search box hides non-matching items."""
    explorer = DatabaseExplorerWidget()
    qtbot.addWidget(explorer)

    sample_db = create_sample_schema()
    explorer.load_schema_model("Test Connection", sample_db)

    # Expand nodes
    db_item = explorer.tree.topLevelItem(0).child(0)
    schema_item = db_item.child(0)
    explorer._on_item_expanded(schema_item)

    # Filter for 'orders'
    explorer.filter_items("orders")

    tables_group = schema_item.child(0)
    users_item = tables_group.child(0)
    orders_item = tables_group.child(1)

    assert users_item.isHidden() is True
    assert orders_item.isHidden() is False


def test_explorer_sql_generation_helpers(qtbot):
    """Test SQL query generation for SELECT, INSERT, and UPDATE."""
    explorer = DatabaseExplorerWidget()
    qtbot.addWidget(explorer)

    sample_db = create_sample_schema()
    explorer.load_schema_model("Test Connection", sample_db)

    select_sql = explorer._generate_select_sql("public", "users")
    assert "SELECT" in select_sql
    assert "id,\n    email" in select_sql
    assert "FROM public.users" in select_sql

    insert_sql = explorer._generate_insert_sql("public", "users")
    assert "INSERT INTO public.users" in insert_sql
    assert "(email)" in insert_sql

    update_sql = explorer._generate_update_sql("public", "users")
    assert "UPDATE public.users" in update_sql
    assert "SET" in update_sql
    assert "WHERE id = :id" in update_sql
