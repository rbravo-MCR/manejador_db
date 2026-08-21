"""Unit tests for FK-based JOIN resolution, generation, and autocompletion."""

from __future__ import annotations

from backend_ide.domain.schema import (
    Column,
    DatabaseSchema,
    ForeignKey,
    ForeignKeyColumnMapping,
    NormalizedDataType,
    PrimaryKey,
    Schema,
    Table,
)
from backend_ide.domain.sql.completer import CompletionKind, SqlCompletionEngine
from backend_ide.domain.sql.joins import JoinEngine


def create_ecommerce_schema() -> DatabaseSchema:
    """Helper creating customers, reservations, and payments schema with FKs."""
    customers_table = Table(
        name="customers",
        schema_name="public",
        columns=[
            Column(
                name="id",
                native_type="INT",
                normalized_type=NormalizedDataType.INTEGER,
                is_primary_key=True,
            ),
            Column(
                name="name",
                native_type="VARCHAR(100)",
                normalized_type=NormalizedDataType.VARCHAR,
            ),
            Column(
                name="email",
                native_type="VARCHAR(255)",
                normalized_type=NormalizedDataType.VARCHAR,
            ),
        ],
        primary_key=PrimaryKey(column_names=["id"]),
    )

    reservations_table = Table(
        name="reservations",
        schema_name="public",
        columns=[
            Column(
                name="id",
                native_type="INT",
                normalized_type=NormalizedDataType.INTEGER,
                is_primary_key=True,
            ),
            Column(
                name="customer_id",
                native_type="INT",
                normalized_type=NormalizedDataType.INTEGER,
            ),
            Column(
                name="code",
                native_type="VARCHAR(20)",
                normalized_type=NormalizedDataType.VARCHAR,
            ),
        ],
        primary_key=PrimaryKey(column_names=["id"]),
        foreign_keys=[
            ForeignKey(
                name="fk_reservations_customer",
                source_schema="public",
                source_table="reservations",
                target_schema="public",
                target_table="customers",
                column_mappings=[
                    ForeignKeyColumnMapping(source_column="customer_id", target_column="id")
                ],
            )
        ],
    )

    payments_table = Table(
        name="payments",
        schema_name="public",
        columns=[
            Column(
                name="id",
                native_type="INT",
                normalized_type=NormalizedDataType.INTEGER,
                is_primary_key=True,
            ),
            Column(
                name="reservation_id",
                native_type="INT",
                normalized_type=NormalizedDataType.INTEGER,
            ),
            Column(
                name="amount",
                native_type="DECIMAL(10,2)",
                normalized_type=NormalizedDataType.DECIMAL,
            ),
        ],
        primary_key=PrimaryKey(column_names=["id"]),
        foreign_keys=[
            ForeignKey(
                name="fk_payments_reservation",
                source_schema="public",
                source_table="payments",
                target_schema="public",
                target_table="reservations",
                column_mappings=[
                    ForeignKeyColumnMapping(source_column="reservation_id", target_column="id")
                ],
            )
        ],
    )

    return DatabaseSchema(
        engine_name="postgresql",
        database_name="travel_db",
        schemas=[
            Schema(
                name="public",
                tables=[customers_table, reservations_table, payments_table],
            )
        ],
    )


def test_join_engine_finds_direct_and_reverse_joins():
    """JoinEngine must find both outbound and inbound joins for reservations."""
    schema = create_ecommerce_schema()
    joins = JoinEngine.find_joins_for_table(schema, "reservations", source_alias="r")

    assert len(joins) == 2
    # Outbound join (to customers)
    cust_join = next(j for j in joins if j.target_table == "customers")
    assert cust_join.is_outbound is True
    assert "c.id = r.customer_id" in cust_join.on_clause
    assert "customers c ON c.id = r.customer_id" in cust_join.completion_text

    # Inbound join (from payments)
    pay_join = next(j for j in joins if j.target_table == "payments")
    assert pay_join.is_outbound is False
    assert "p.reservation_id = r.id" in pay_join.on_clause


def test_join_engine_generates_complete_select_with_joins():
    """JoinEngine must produce a runnable multi-table SELECT statement."""
    schema = create_ecommerce_schema()
    sql = JoinEngine.generate_select_with_joins(schema, "reservations", "public")

    assert "SELECT" in sql
    assert "FROM reservations" in sql
    assert "LEFT JOIN customers" in sql
    assert "LEFT JOIN payments" in sql
    assert "ON c.id = r.customer_id" in sql or "ON customers.id = reservations.customer_id"
    assert "LIMIT 100;" in sql


def test_sql_completion_engine_suggests_fk_joins_in_join_context():
    """SqlCompletionEngine must suggest FK-aware table and ON joins when typing JOIN."""
    schema = create_ecommerce_schema()
    engine = SqlCompletionEngine(schema_model=schema)

    completions = engine.get_completions(
        prefix="", context_text="SELECT * FROM reservations r JOIN "
    )

    join_items = [c for c in completions if c.kind == CompletionKind.JOIN]
    assert len(join_items) >= 2

    # Should suggest customers and payments with their exact ON clauses
    cust_item = next(c for c in join_items if "customers" in c.text)
    assert "ON c.id = r.customer_id" in cust_item.text

    pay_item = next(c for c in join_items if "payments" in c.text)
    assert "ON p.reservation_id = r.id" in pay_item.text


def test_extract_context_table_and_alias():
    """Context parser must correctly isolate table and alias from preceding SQL."""
    tbl, alias = JoinEngine.extract_context_table_and_alias("SELECT u.id FROM reservations r JOIN ")
    assert tbl == "reservations"
    assert alias == "r"

    tbl2, alias2 = JoinEngine.extract_context_table_and_alias("SELECT * FROM public.orders JOIN ")
    assert tbl2 == "orders"
    assert alias2 is None
