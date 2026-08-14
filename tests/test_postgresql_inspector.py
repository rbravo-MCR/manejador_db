"""Unit and Mock Integration tests for Phase 2 - PostgreSQL Inspector."""

from typing import Any
from unittest.mock import MagicMock, patch

from backend_ide.domain.schema.enums import ForeignKeyAction, NormalizedDataType
from backend_ide.infrastructure.database.contracts import ConnectionConfig
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
