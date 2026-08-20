"""Unit and Mock Integration tests for Phase 2 - PostgreSQL Inspector."""

from typing import Any
from unittest.mock import MagicMock, patch

from backend_ide.domain.schema.enums import ForeignKeyAction, NormalizedDataType
from backend_ide.infrastructure.database.contracts import ConnectionConfig, MetadataProvider
from backend_ide.infrastructure.database.postgresql import (
    PostgreSQLConnection,
    PostgreSQLInspector,
    map_pg_type_to_normalized,
)


def test_type_mapper_postgresql_types():
    """Verify PostgreSQL type mapper converts PostgreSQL types to NormalizedDataType."""
    assert map_pg_type_to_normalized("integer") == NormalizedDataType.INTEGER
    assert map_pg_type_to_normalized("bigint") == NormalizedDataType.BIGINT
    assert map_pg_type_to_normalized("character varying(255)") == NormalizedDataType.VARCHAR
    assert map_pg_type_to_normalized("text") == NormalizedDataType.TEXT
    assert map_pg_type_to_normalized("timestamp with time zone") == NormalizedDataType.TIMESTAMPTZ
    assert map_pg_type_to_normalized("uuid") == NormalizedDataType.UUID
    assert map_pg_type_to_normalized("jsonb") == NormalizedDataType.JSONB
    assert map_pg_type_to_normalized("boolean") == NormalizedDataType.BOOLEAN
    assert map_pg_type_to_normalized("numeric(10, 2)") == NormalizedDataType.DECIMAL
    assert map_pg_type_to_normalized("integer[]") == NormalizedDataType.ARRAY


def test_postgresql_connection_dsn_building():
    """Test PostgreSQLConnection DSN construction."""
    config = ConnectionConfig(
        name="Test DB",
        engine="postgresql",
        host="db.example.com",
        port=5433,
        database="app_db",
        username="db_user",
        password="secret_password",
        ssl_mode="require",
    )
    conn = PostgreSQLConnection(config)
    dsn = conn._build_dsn()

    assert "host=db.example.com" in dsn
    assert "port=5433" in dsn
    assert "dbname=app_db" in dsn
    assert "user=db_user" in dsn
    assert "password=secret_password" in dsn
    assert "sslmode=require" in dsn


def test_postgresql_connection_uses_a_bounded_connect_timeout():
    """A dead host must stop trying quickly instead of freezing the desktop UI."""
    config = ConnectionConfig(engine="postgresql", host="db.example.com")
    conn = PostgreSQLConnection(config)
    driver_connection = MagicMock()
    driver_connection.closed = False

    with patch(
        "backend_ide.infrastructure.database.postgresql.connection.psycopg.connect",
        return_value=driver_connection,
    ) as connect:
        conn.connect()

    assert connect.call_args.kwargs["connect_timeout"] == 8


def test_postgresql_inspector_lists_connectable_databases():
    """Only user-connectable, non-template databases should reach the selector."""
    connection = MagicMock()
    connection.execute_query.return_value = [
        {"datname": "analytics"},
        {"datname": "db_outlet"},
    ]

    databases = PostgreSQLInspector(connection).list_databases()

    assert databases == ["analytics", "db_outlet"]
    sql = connection.execute_query.call_args.args[0]
    assert "NOT datistemplate" in sql
    assert "datallowconn" in sql
    assert "has_database_privilege" in sql


def test_postgresql_inspector_exposes_the_shared_metadata_provider_contract():
    assert isinstance(PostgreSQLInspector(MagicMock()), MetadataProvider)


def test_postgresql_inspector_builds_explorer_summary_in_two_queries():
    """The explorer must not issue several catalog queries for each table."""
    connection = MagicMock()

    def execute(query, _params=None):
        if "current_database()" in query:
            return [{"db_name": "db_outlet"}]
        return [
            {"table_schema": "public", "table_name": "customers"},
            {"table_schema": "public", "table_name": "orders"},
            {"table_schema": "supplier_service", "table_name": "suppliers"},
        ]

    connection.execute_query.side_effect = execute

    schema = PostgreSQLInspector(connection).inspect_database_summary()

    assert schema.database_name == "db_outlet"
    assert [item.name for item in schema.schemas] == ["public", "supplier_service"]
    assert [table.name for table in schema.schemas[0].tables] == ["customers", "orders"]
    assert connection.execute_query.call_count == 2


def test_postgresql_inspector_builds_completion_metadata_with_bulk_queries():
    """IntelliSense metadata must include columns, views, and routines without per-key I/O."""
    connection = MagicMock()

    def execute(query, _params=None):
        if "current_database()" in query:
            return [{"db_name": "app"}]
        if "object_kind" in query:
            return [
                {"schema_name": "public", "object_name": "users", "object_kind": "table"},
                {
                    "schema_name": "public",
                    "object_name": "active_users",
                    "object_kind": "view",
                },
            ]
        if "information_schema.columns" in query:
            return [
                {
                    "table_schema": "public",
                    "table_name": "users",
                    "column_name": "id",
                    "data_type": "integer",
                    "udt_name": "int4",
                    "is_nullable": "NO",
                    "column_default": None,
                    "character_maximum_length": None,
                    "numeric_precision": 32,
                    "numeric_scale": 0,
                    "is_identity": "YES",
                }
            ]
        return [
            {
                "schema_name": "public",
                "routine_name": "calculate_total",
                "routine_kind": "f",
                "return_type": "numeric",
                "definition": None,
                "language": "sql",
            }
        ]

    connection.execute_query.side_effect = execute

    schema = PostgreSQLInspector(connection).inspect_completion_metadata()

    public = schema.get_schema("public")
    assert [table.name for table in public.tables] == ["users"]
    assert [column.name for column in public.tables[0].columns] == ["id"]
    assert [view.name for view in public.views] == ["active_users"]
    assert [function.name for function in public.functions] == ["calculate_total"]
    assert connection.execute_query.call_count == 4


def test_postgresql_inspector_loads_table_columns_and_marks_primary_key():
    """Expanded tables need typed fields with primary-key metadata."""
    connection = MagicMock()

    def execute(query, _params=None):
        if "information_schema.columns" in query:
            return [
                {
                    "column_name": "id",
                    "data_type": "integer",
                    "udt_name": "int4",
                    "is_nullable": "NO",
                    "column_default": None,
                    "character_maximum_length": None,
                    "numeric_precision": 32,
                    "numeric_scale": 0,
                    "is_identity": "NO",
                },
                {
                    "column_name": "email",
                    "data_type": "character varying",
                    "udt_name": "varchar",
                    "is_nullable": "YES",
                    "column_default": None,
                    "character_maximum_length": 255,
                    "numeric_precision": None,
                    "numeric_scale": None,
                    "is_identity": "NO",
                },
            ]
        return [{"constraint_name": "customers_pkey", "column_name": "id"}]

    connection.execute_query.side_effect = execute

    columns = PostgreSQLInspector(connection).inspect_table_columns("public", "customers")

    assert [column.name for column in columns] == ["id", "email"]
    assert columns[0].is_primary_key is True
    assert columns[1].is_primary_key is False


def test_postgresql_inspector_mocked_inspection():
    """Test PostgreSQLInspector converts catalog queries into Universal Schema Model."""
    mock_conn = MagicMock()

    def query_dispatcher(query: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        q = query.lower()

        if "current_database()" in q:
            return [{"db_name": "test_ecom"}]

        if "pg_namespace" in q and "routine_name" not in q and "relname" not in q:
            return [{"nspname": "public"}]

        if "information_schema.tables" in q:
            return [{"table_name": "users"}, {"table_name": "orders"}]

        if "information_schema.columns" in q:
            schema, table = params if params else ("public", "users")
            if table == "users":
                return [
                    {
                        "column_name": "id",
                        "data_type": "integer",
                        "udt_name": "int4",
                        "is_nullable": "NO",
                        "column_default": "nextval('users_id_seq'::regclass)",
                        "character_maximum_length": None,
                        "numeric_precision": 32,
                        "numeric_scale": 0,
                        "is_identity": "NO",
                    },
                    {
                        "column_name": "email",
                        "data_type": "character varying",
                        "udt_name": "varchar",
                        "is_nullable": "NO",
                        "column_default": None,
                        "character_maximum_length": 255,
                        "numeric_precision": None,
                        "numeric_scale": None,
                        "is_identity": "NO",
                    },
                ]
            else:  # orders
                return [
                    {
                        "column_name": "id",
                        "data_type": "bigint",
                        "udt_name": "int8",
                        "is_nullable": "NO",
                        "column_default": None,
                        "character_maximum_length": None,
                        "numeric_precision": 64,
                        "numeric_scale": 0,
                        "is_identity": "YES",
                    },
                    {
                        "column_name": "user_id",
                        "data_type": "integer",
                        "udt_name": "int4",
                        "is_nullable": "NO",
                        "column_default": None,
                        "character_maximum_length": None,
                        "numeric_precision": 32,
                        "numeric_scale": 0,
                        "is_identity": "NO",
                    },
                ]

        if "constraint_type = 'primary key'" in q:
            table = params[1] if params else "users"
            if table == "users":
                return [{"constraint_name": "pk_users", "column_name": "id"}]
            return [{"constraint_name": "pk_orders", "column_name": "id"}]

        if "constraint_type = 'foreign key'" in q:
            table = params[1] if params else "users"
            if table == "orders":
                return [
                    {
                        "constraint_name": "fk_orders_user",
                        "source_column": "user_id",
                        "target_schema": "public",
                        "target_table": "users",
                        "target_column": "id",
                        "update_rule": "NO ACTION",
                        "delete_rule": "CASCADE",
                    }
                ]
            return []

        if "pg_index idx" in q:
            table = params[1] if params else "users"
            if table == "users":
                return [
                    {
                        "index_name": "idx_users_email",
                        "is_unique": True,
                        "index_type": "btree",
                        "filter_condition": None,
                        "columns": "email",
                    }
                ]
            return []

        if "constraint_type = 'unique'" in q:
            return []

        if "constraint_type = 'check'" in q:
            return []

        if "information_schema.views" in q:
            return [
                {
                    "view_name": "v_user_orders",
                    "view_definition": "SELECT * FROM orders",
                    "is_materialized": False,
                }
            ]

        if "information_schema.sequences" in q:
            return [{"sequence_name": "users_id_seq"}]

        if "pg_proc p" in q:
            return [
                {
                    "routine_name": "calculate_tax",
                    "routine_kind": "f",
                    "return_type": "numeric",
                    "definition": "CREATE FUNCTION calculate_tax()...",
                    "language": "plpgsql",
                }
            ]

        if "information_schema.triggers" in q:
            return []

        return []

    mock_conn.execute_query.side_effect = query_dispatcher

    inspector = PostgreSQLInspector(mock_conn)
    schema_model = inspector.inspect_database(schema_names=["public"])

    assert schema_model.engine_name == "postgresql"
    assert schema_model.database_name == "test_ecom"
    assert len(schema_model.schemas) == 1

    public_schema = schema_model.get_schema("public")
    assert public_schema is not None
    assert len(public_schema.tables) == 2

    users_table = public_schema.get_table("users")
    assert users_table is not None
    assert len(users_table.columns) == 2

    id_col = users_table.get_column("id")
    assert id_col is not None
    assert id_col.is_auto_increment is True
    assert id_col.is_primary_key is True

    orders_table = public_schema.get_table("orders")
    assert orders_table is not None
    assert len(orders_table.foreign_keys) == 1

    fk = orders_table.foreign_keys[0]
    assert fk.name == "fk_orders_user"
    assert fk.target_table == "users"
    assert fk.on_delete == ForeignKeyAction.CASCADE

    relationships = schema_model.extract_all_relationships()
    assert len(relationships) == 1
    assert relationships[0].source_table_qualified == "public.orders"
    assert relationships[0].target_table_qualified == "public.users"
