"""Unit tests for Microsoft SQL Server (T-SQL) type mapper, connection, and inspector."""

from __future__ import annotations

from unittest.mock import MagicMock

from backend_ide.domain.schema.enums import ForeignKeyAction, NormalizedDataType
from backend_ide.infrastructure.database.contracts import ConnectionConfig
from backend_ide.infrastructure.database.inspector_factory import InspectorFactory
from backend_ide.infrastructure.database.mssql.connection import MSSQLConnection
from backend_ide.infrastructure.database.mssql.inspector import MSSQLInspector
from backend_ide.infrastructure.database.mssql.type_mapper import MSSQLTypeMapper


def test_mssql_type_mapper_data_types():
    """Verify mapping of T-SQL native data types to universal normalized types."""
    assert MSSQLTypeMapper.map_native_type("INT") == NormalizedDataType.INTEGER
    assert MSSQLTypeMapper.map_native_type("BIGINT IDENTITY(1,1)") == NormalizedDataType.BIGINT
    assert MSSQLTypeMapper.map_native_type("NVARCHAR(255)") == NormalizedDataType.VARCHAR
    assert MSSQLTypeMapper.map_native_type("BIT") == NormalizedDataType.BOOLEAN
    assert MSSQLTypeMapper.map_native_type("DECIMAL(18,2)") == NormalizedDataType.DECIMAL
    assert MSSQLTypeMapper.map_native_type("MONEY") == NormalizedDataType.DECIMAL
    assert MSSQLTypeMapper.map_native_type("DATETIME2(7)") == NormalizedDataType.TIMESTAMP
    assert MSSQLTypeMapper.map_native_type("UNIQUEIDENTIFIER") == NormalizedDataType.UUID
    assert MSSQLTypeMapper.map_native_type("VARBINARY(MAX)") == NormalizedDataType.BINARY
    assert MSSQLTypeMapper.map_native_type("XML") == NormalizedDataType.TEXT
    assert MSSQLTypeMapper.map_native_type("UNKNOWN_TYPE") == NormalizedDataType.UNKNOWN


def test_mssql_inspector_factory_resolution():
    """Verify InspectorFactory creates MSSQLInspector when engine is sqlserver or mssql."""
    config = ConnectionConfig(name="MSSQL Test", engine="sqlserver", database="testdb")
    mock_conn = MagicMock()
    mock_conn.config = config

    inspector = InspectorFactory.create_inspector(mock_conn)
    assert isinstance(inspector, MSSQLInspector)


def test_mssql_inspector_mocked_summary():
    """Test MSSQLInspector parsing table, PK, and FK metadata into DatabaseSchema."""
    mock_conn = MagicMock(spec=MSSQLConnection)
    mock_conn.config = ConnectionConfig(name="MSSQL", engine="sqlserver", database="ecommerce")

    def mock_query(sql: str, params=None):
        if "sys.databases" in sql:
            return [{"name": "ecommerce"}, {"name": "crm"}]
        elif "sys.key_constraints" in sql:
            return [
                {
                    "schema_name": "dbo",
                    "table_name": "customers",
                    "constraint_name": "PK_customers",
                    "column_name": "id",
                    "ordinal_position": 1,
                },
                {
                    "schema_name": "dbo",
                    "table_name": "orders",
                    "constraint_name": "PK_orders",
                    "column_name": "id",
                    "ordinal_position": 1,
                },
            ]
        elif "sys.foreign_keys" in sql:
            return [
                {
                    "source_schema": "dbo",
                    "source_table": "orders",
                    "constraint_name": "FK_orders_customers",
                    "source_column": "customer_id",
                    "target_schema": "dbo",
                    "target_table": "customers",
                    "target_column": "id",
                    "on_update": "CASCADE",
                    "on_delete": "SET NULL",
                }
            ]
        elif "sys.columns" in sql:
            return [
                {
                    "column_name": "id",
                    "data_type": "BIGINT",
                    "is_nullable": 0,
                    "is_auto_increment": 1,
                    "column_default": None,
                },
                {
                    "column_name": "email",
                    "data_type": "NVARCHAR",
                    "is_nullable": 0,
                    "is_auto_increment": 0,
                    "column_default": None,
                },
            ]
        elif "sys.tables" in sql:
            return [
                {"schema_name": "dbo", "table_name": "orders", "table_type": "USER_TABLE"},
                {"schema_name": "dbo", "table_name": "customers", "table_type": "USER_TABLE"},
            ]
        return []

    mock_conn.execute_query.side_effect = mock_query
    inspector = MSSQLInspector(mock_conn)

    dbs = inspector.list_databases()
    assert dbs == ["ecommerce", "crm"]

    schema = inspector.inspect_database_summary()
    assert schema.database_name == "ecommerce"
    assert len(schema.schemas) == 1
    assert schema.schemas[0].name == "dbo"
    assert len(schema.schemas[0].tables) == 2

    orders_table = next(t for t in schema.schemas[0].tables if t.name == "orders")
    assert orders_table.primary_key is not None
    assert orders_table.primary_key.column_names == ["id"]
    assert len(orders_table.foreign_keys) == 1
    assert orders_table.foreign_keys[0].target_table == "customers"
    assert orders_table.foreign_keys[0].on_update == ForeignKeyAction.CASCADE
    assert orders_table.foreign_keys[0].on_delete == ForeignKeyAction.SET_NULL

    # Column level test
    columns = inspector.inspect_table_columns("dbo", "customers")
    assert len(columns) == 2
    assert columns[0].name == "id"
    assert columns[0].normalized_type == NormalizedDataType.BIGINT
    assert columns[0].is_auto_increment is True
