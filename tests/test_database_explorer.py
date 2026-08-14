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
    assert explorer.cmb_database is not None
    assert explorer.lbl_entities_count.text() == "0"
    assert explorer.tree is not None
    assert explorer.tree.indentation() <= 18
    assert explorer.tree.topLevelItemCount() == 0


def test_explorer_model_loading_uses_dense_schema_table_hierarchy(qtbot):
    """Show tables directly below schemas like the selected visual reference."""
    explorer = DatabaseExplorerWidget()
    qtbot.addWidget(explorer)

    sample_db = create_sample_schema()
    explorer.load_schema_model("Test Connection", sample_db)

    assert explorer.tree.topLevelItemCount() == 1
    schema_item = explorer.tree.topLevelItem(0)
    assert "public" in schema_item.text(0)
    assert schema_item.isExpanded()
    assert schema_item.childCount() == 2
    assert "users" in schema_item.child(0).text(0)
    assert "orders" in schema_item.child(1).text(0)
    assert not schema_item.icon(0).isNull()
    assert not schema_item.child(0).icon(0).isNull()
    assert explorer.lbl_entities_count.text() == "2"


def test_database_dropdown_is_above_filter_and_emits_selection(qtbot):
    """Database switching stays compact at the top of the explorer."""
    explorer = DatabaseExplorerWidget()
    qtbot.addWidget(explorer)
    selected = []
    explorer.database_changed.connect(selected.append)

    explorer.set_databases(["analytics", "db_outlet"], "db_outlet")
    explorer.cmb_database.setCurrentText("analytics")

    layout = explorer.layout()
    assert layout.indexOf(explorer.database_row) < layout.indexOf(explorer.txt_filter)
    assert explorer.cmb_database.currentText() == "analytics"
    assert selected == ["analytics"]


def test_explorer_loading_and_preserved_error_states(qtbot):
    """Initial loading is visible and refresh failures keep the useful old tree."""
    explorer = DatabaseExplorerWidget()
    qtbot.addWidget(explorer)

    explorer.set_loading()
    assert "Cargando" in explorer.tree.topLevelItem(0).text(0)

    explorer.load_schema_model("Test Connection", create_sample_schema())
    old_schema = explorer.tree.topLevelItem(0)
    explorer.show_error("Sin permiso", preserve_tree=True)

    assert explorer.tree.topLevelItem(0) is old_schema
    assert "Sin permiso" in explorer.lbl_state.text()


def test_expanding_table_requests_and_displays_typed_columns(qtbot):
    """Table chevrons lazily reveal field names, types, nullability, and PK status."""
    explorer = DatabaseExplorerWidget()
    qtbot.addWidget(explorer)
    explorer.load_schema_model("Test Connection", create_sample_schema())
    requested = []
    explorer.table_expansion_requested.connect(
        lambda schema, table: requested.append((schema, table))
    )
    table_item = explorer.tree.topLevelItem(0).child(0)

    table_item.setExpanded(True)

    assert requested == [("public", "users")]
    assert "Cargando" in table_item.child(0).text(0)

    users = create_sample_schema().schemas[0].tables[0]
    explorer.load_table_columns("public", "users", users.columns)

    assert table_item.childCount() == 2
    assert "id" in table_item.child(0).text(0)
    assert "INT" in table_item.child(0).text(0)
    assert "PK" in table_item.child(0).text(0)
    assert not table_item.child(0).icon(0).isNull()


def test_explorer_search_filtering(qtbot):
    """Test typing into filter search box hides non-matching items."""
    explorer = DatabaseExplorerWidget()
    qtbot.addWidget(explorer)

    sample_db = create_sample_schema()
    explorer.load_schema_model("Test Connection", sample_db)

    schema_item = explorer.tree.topLevelItem(0)

    # Filter for 'orders'
    explorer.filter_items("orders")

    users_item = schema_item.child(0)
    orders_item = schema_item.child(1)

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
