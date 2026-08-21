"""Unit tests for the Inferred / Virtual Foreign Keys Engine."""

from __future__ import annotations

from backend_ide.domain.schema.enums import NormalizedDataType
from backend_ide.domain.schema.inferred_relations import InferredRelationsEngine
from backend_ide.domain.schema.models import (
    Column,
    DatabaseSchema,
    PrimaryKey,
    Schema,
    Table,
)


def test_inferred_relations_discovery():
    """Verify detection of implicit foreign keys based on naming conventions."""
    customers_table = Table(
        name="customers",
        columns=[
            Column(
                name="id",
                native_type="INT",
                normalized_type=NormalizedDataType.INTEGER,
                is_primary_key=True,
            ),
            Column(name="name", native_type="VARCHAR", normalized_type=NormalizedDataType.VARCHAR),
        ],
        primary_key=PrimaryKey(column_names=["id"]),
    )

    orders_table = Table(
        name="orders",
        columns=[
            Column(
                name="id",
                native_type="INT",
                normalized_type=NormalizedDataType.INTEGER,
                is_primary_key=True,
            ),
            Column(
                name="customer_id", native_type="INT", normalized_type=NormalizedDataType.INTEGER
            ),
            Column(name="total", native_type="DECIMAL", normalized_type=NormalizedDataType.DECIMAL),
        ],
        primary_key=PrimaryKey(column_names=["id"]),
        foreign_keys=[],  # No explicit FK constraints
    )

    schema = DatabaseSchema(
        database_name="legacy_db",
        engine_name="mysql",
        schemas=[Schema(name="default", tables=[customers_table, orders_table])],
    )

    relations = InferredRelationsEngine.discover_relations(schema)
    assert len(relations) == 1
    assert relations[0].source_table == "orders"
    assert relations[0].source_column == "customer_id"
    assert relations[0].target_table == "customers"
    assert relations[0].target_column == "id"
    assert relations[0].confidence >= 0.9

    # Apply to schema
    augmented = InferredRelationsEngine.apply_to_schema(schema)
    aug_orders = next(t for t in augmented.schemas[0].tables if t.name == "orders")
    assert len(aug_orders.foreign_keys) == 1
    assert aug_orders.foreign_keys[0].target_table == "customers"
