"""Unit tests for Phase 1 - Universal Schema Model."""

import subprocess
import sys

import pytest
from pydantic import ValidationError

from backend_ide.domain.schema import (
    CheckConstraint,
    Column,
    DatabaseSchema,
    ForeignKey,
    ForeignKeyAction,
    ForeignKeyColumnMapping,
    Function,
    Index,
    IndexType,
    NormalizedDataType,
    PrimaryKey,
    Procedure,
    RoutineParameter,
    Schema,
    Sequence,
    Table,
    Trigger,
    UniqueConstraint,
    View,
    schema_from_json,
    schema_to_json,
)


def test_no_pyside_or_db_driver_imports():
    """Verify Phase 1 domain layer has NO PySide6 or DB driver imports in a fresh process."""
    check_script = """
import sys
import backend_ide.domain.schema

forbidden_modules = [
    "PySide6",
    "PyQt6",
    "psycopg",
    "psycopg2",
    "pymysql",
    "pyodbc",
    "sqlite3",
]
loaded_forbidden = [mod for mod in forbidden_modules if mod in sys.modules]
if loaded_forbidden:
    print(f"FORBIDDEN_LOADED: {loaded_forbidden}")
    sys.exit(1)
sys.exit(0)
"""
    result = subprocess.run(
        [sys.executable, "-c", check_script],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"Domain package loaded forbidden modules: {result.stdout}"


def test_create_complex_table_with_composite_keys():
    """Test table creation with composite primary keys and composite foreign keys."""
    order_items = Table(
        name="order_items",
        schema_name="sales",
        columns=[
            Column(
                name="order_id",
                native_type="BIGINT",
                normalized_type=NormalizedDataType.BIGINT,
                is_nullable=False,
            ),
            Column(
                name="item_id",
                native_type="INTEGER",
                normalized_type=NormalizedDataType.INTEGER,
                is_nullable=False,
            ),
            Column(
                name="product_sku",
                native_type="VARCHAR(50)",
                normalized_type=NormalizedDataType.VARCHAR,
                length=50,
                is_nullable=False,
            ),
            Column(
                name="quantity",
                native_type="INTEGER",
                normalized_type=NormalizedDataType.INTEGER,
                default_value="1",
                is_nullable=False,
            ),
            Column(
                name="price",
                native_type="DECIMAL(10, 2)",
                normalized_type=NormalizedDataType.DECIMAL,
                precision=10,
                scale=2,
                is_nullable=False,
            ),
        ],
        primary_key=PrimaryKey(name="pk_order_items", column_names=["order_id", "item_id"]),
        foreign_keys=[
            ForeignKey(
                name="fk_order_items_orders",
                source_schema="sales",
                source_table="order_items",
                target_schema="sales",
                target_table="orders",
                column_mappings=[
                    ForeignKeyColumnMapping(source_column="order_id", target_column="id")
                ],
                on_delete=ForeignKeyAction.CASCADE,
            ),
            ForeignKey(
                name="fk_order_items_inventory",
                source_schema="sales",
                source_table="order_items",
                target_schema="inventory",
                target_table="products",
                column_mappings=[
                    ForeignKeyColumnMapping(source_column="product_sku", target_column="sku_code")
                ],
            ),
        ],
        indexes=[
            Index(
                name="idx_order_items_sku",
                is_unique=False,
                columns=["product_sku"],
                index_type=IndexType.BTREE,
            )
        ],
        check_constraints=[
            CheckConstraint(name="chk_quantity_positive", expression="quantity > 0")
        ],
    )

    assert order_items.qualified_name == "sales.order_items"
    assert len(order_items.columns) == 5
    assert order_items.get_column("ORDER_ID").is_primary_key is True
    assert order_items.get_column("item_id").is_primary_key is True
    assert order_items.get_column("quantity").is_primary_key is False
    assert len(order_items.foreign_keys) == 2


def test_cross_schema_references_and_database_model():
    """Test multi-schema database with cross-schema foreign keys."""
    auth_users = Table(
        name="users",
        schema_name="auth",
        columns=[
            Column(
                name="id",
                native_type="UUID",
                normalized_type=NormalizedDataType.UUID,
                is_nullable=False,
                is_primary_key=True,
            ),
            Column(
                name="email",
                native_type="VARCHAR(255)",
                normalized_type=NormalizedDataType.VARCHAR,
                length=255,
                is_nullable=False,
            ),
        ],
        primary_key=PrimaryKey(name="pk_users", column_names=["id"]),
        unique_constraints=[UniqueConstraint(name="uq_users_email", column_names=["email"])],
    )

    sales_orders = Table(
        name="orders",
        schema_name="sales",
        columns=[
            Column(
                name="id",
                native_type="BIGINT",
                normalized_type=NormalizedDataType.BIGINT,
                is_nullable=False,
                is_primary_key=True,
            ),
            Column(
                name="user_id",
                native_type="UUID",
                normalized_type=NormalizedDataType.UUID,
                is_nullable=False,
            ),
            Column(
                name="total",
                native_type="NUMERIC(12, 2)",
                normalized_type=NormalizedDataType.DECIMAL,
                precision=12,
                scale=2,
            ),
        ],
        primary_key=PrimaryKey(name="pk_orders", column_names=["id"]),
        foreign_keys=[
            ForeignKey(
                name="fk_orders_user",
                source_schema="sales",
                source_table="orders",
                target_schema="auth",
                target_table="users",
                column_mappings=[
                    ForeignKeyColumnMapping(source_column="user_id", target_column="id")
                ],
            )
        ],
    )

    db_schema = DatabaseSchema(
        engine_name="postgresql",
        version="16.1",
        database_name="production_db",
        schemas=[
            Schema(name="auth", tables=[auth_users]),
            Schema(name="sales", tables=[sales_orders]),
        ],
    )

    assert db_schema.find_table("users", "auth") is not None
    assert db_schema.find_table("orders") is not None
    assert db_schema.find_table("non_existent") is None

    relationships = db_schema.extract_all_relationships()
    assert len(relationships) == 1
    rel = relationships[0]
    assert rel.source_table_qualified == "sales.orders"
    assert rel.target_table_qualified == "auth.users"
    assert rel.column_mappings == [("user_id", "id")]


def test_schema_json_serialization_roundtrip():
    """Test serializing DatabaseSchema to JSON and back without data loss."""
    original_schema = DatabaseSchema(
        engine_name="mysql",
        version="8.0.35",
        database_name="ecommerce",
        schemas=[
            Schema(
                name="public",
                tables=[
                    Table(
                        name="customers",
                        columns=[
                            Column(
                                name="id",
                                native_type="INT",
                                normalized_type=NormalizedDataType.INTEGER,
                                is_nullable=False,
                                is_auto_increment=True,
                            ),
                            Column(
                                name="name",
                                native_type="VARCHAR(100)",
                                normalized_type=NormalizedDataType.VARCHAR,
                                length=100,
                            ),
                        ],
                        primary_key=PrimaryKey(column_names=["id"]),
                    )
                ],
                views=[
                    View(
                        name="v_active_customers",
                        definition="SELECT * FROM customers WHERE is_active = 1",
                    )
                ],
                sequences=[Sequence(name="seq_customer_id", start_value=1000)],
                functions=[
                    Function(
                        name="fn_customer_count",
                        return_type="INTEGER",
                        parameters=[RoutineParameter(name="status_code", data_type="VARCHAR")],
                        definition="SELECT count(*) FROM customers",
                    )
                ],
                procedures=[
                    Procedure(
                        name="sp_cleanup",
                        parameters=[],
                        definition="DELETE FROM temp_logs",
                    )
                ],
                triggers=[
                    Trigger(
                        name="trg_audit",
                        table_name="customers",
                        timing="AFTER",
                        event="UPDATE",
                        definition="CALL log_changes()",
                    )
                ],
            )
        ],
    )

    json_data = schema_to_json(original_schema)
    restored_schema = schema_from_json(json_data)

    assert restored_schema.engine_name == "mysql"
    assert restored_schema.database_name == "ecommerce"
    table = restored_schema.find_table("customers", "public")
    assert table is not None
    assert len(table.columns) == 2
    assert table.get_column("id").is_auto_increment is True
    schema_public = restored_schema.get_schema("public")
    assert len(schema_public.views) == 1
    assert len(schema_public.functions) == 1
    assert len(schema_public.procedures) == 1
    assert len(schema_public.triggers) == 1


def test_invalid_models_raise_validation_error():
    """Verify Pydantic validation kicks in for malformed schema models."""
    with pytest.raises(ValidationError):
        # ForeignKey missing required source_table / column_mappings
        ForeignKey(source_schema="public", target_table="target")  # type: ignore[call-arg]
