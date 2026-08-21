"""Unit tests for MySQL Inspector, Type Mapper, and Connection Adapter."""

from __future__ import annotations

from unittest.mock import MagicMock

from backend_ide.domain.schema.enums import ForeignKeyAction, NormalizedDataType
from backend_ide.infrastructure.database.contracts import ConnectionConfig
from backend_ide.infrastructure.database.mysql.connection import MySQLConnection
from backend_ide.infrastructure.database.mysql.inspector import MySQLInspector
from backend_ide.infrastructure.database.mysql.type_mapper import (
    map_mysql_type_to_normalized,
)


def test_mysql_type_mapper():
    """Verify MySQL types mapping to NormalizedDataType."""
    assert map_mysql_type_to_normalized("INT") == NormalizedDataType.INTEGER
    assert map_mysql_type_to_normalized("BIGINT") == NormalizedDataType.BIGINT
    assert map_mysql_type_to_normalized("VARCHAR(100)") == NormalizedDataType.VARCHAR
    assert map_mysql_type_to_normalized("LONGTEXT") == NormalizedDataType.TEXT
    assert map_mysql_type_to_normalized("TINYINT(1)") == NormalizedDataType.BOOLEAN
    assert map_mysql_type_to_normalized("DATETIME") == NormalizedDataType.DATETIME
    assert map_mysql_type_to_normalized("TIMESTAMP") == NormalizedDataType.TIMESTAMP
    assert map_mysql_type_to_normalized("DECIMAL(10,2)") == NormalizedDataType.DECIMAL
    assert map_mysql_type_to_normalized("DOUBLE") == NormalizedDataType.FLOAT
    assert map_mysql_type_to_normalized("JSON") == NormalizedDataType.JSON
    assert map_mysql_type_to_normalized("ENUM('a','b')") == NormalizedDataType.ENUM


def test_mysql_inspector_summary_with_mock():
    """Verify MySQLInspector builds Universal Schema with tables, columns, PKs and FKs."""
    connection = MagicMock()
    connection.config = ConnectionConfig(
        name="Test MySQL",
        engine="mysql",
        host="localhost",
        port=3306,
        database="shop_db",
        username="root",
    )

    def execute(query, params=None):
        if "information_schema.schemata" in query:
            return [{"schema_name": "shop_db"}, {"schema_name": "analytics"}]
        if "information_schema.tables" in query:
            return [
                {"table_name": "users", "table_type": "BASE TABLE"},
                {"table_name": "orders", "table_type": "BASE TABLE"},
                {"table_name": "v_user_orders", "table_type": "VIEW"},
            ]
        if "information_schema.columns" in query:
            return [
                {
                    "table_name": "users",
                    "column_name": "id",
                    "data_type": "int",
                    "column_type": "int(11)",
                    "is_nullable": "NO",
                    "column_default": None,
                    "character_maximum_length": None,
                    "numeric_precision": 10,
                    "numeric_scale": 0,
                    "extra": "auto_increment",
                    "column_key": "PRI",
                },
                {
                    "table_name": "users",
                    "column_name": "username",
                    "data_type": "varchar",
                    "column_type": "varchar(50)",
                    "is_nullable": "NO",
                    "column_default": None,
                    "character_maximum_length": 50,
                    "numeric_precision": None,
                    "numeric_scale": None,
                    "extra": "",
                    "column_key": "UNI",
                },
                {
                    "table_name": "orders",
                    "column_name": "id",
                    "data_type": "int",
                    "column_type": "int(11)",
                    "is_nullable": "NO",
                    "column_default": None,
                    "character_maximum_length": None,
                    "numeric_precision": 10,
                    "numeric_scale": 0,
                    "extra": "auto_increment",
                    "column_key": "PRI",
                },
                {
                    "table_name": "orders",
                    "column_name": "user_id",
                    "data_type": "int",
                    "column_type": "int(11)",
                    "is_nullable": "NO",
                    "column_default": None,
                    "character_maximum_length": None,
                    "numeric_precision": 10,
                    "numeric_scale": 0,
                    "extra": "",
                    "column_key": "MUL",
                },
            ]
        if "information_schema.key_column_usage" in query:
            return [
                {
                    "constraint_name": "fk_orders_user",
                    "source_table": "orders",
                    "source_column": "user_id",
                    "target_schema": "shop_db",
                    "target_table": "users",
                    "target_column": "id",
                    "update_rule": "NO ACTION",
                    "delete_rule": "CASCADE",
                }
            ]
        return []

    connection.execute_query.side_effect = execute

    inspector = MySQLInspector(connection)
    db_list = inspector.list_databases()
    assert db_list == ["shop_db", "analytics"]

    schema = inspector.inspect_database_summary()
    assert schema.engine_name == "mysql"
    assert schema.database_name == "shop_db"

    main_schema = schema.schemas[0]
    assert main_schema.name == "shop_db"
    assert len(main_schema.tables) == 2
    assert len(main_schema.views) == 1

    users_tbl = main_schema.get_table("users")
    assert users_tbl is not None
    assert users_tbl.primary_key is not None
    assert users_tbl.primary_key.column_names == ["id"]

    orders_tbl = main_schema.get_table("orders")
    assert orders_tbl is not None
    assert len(orders_tbl.foreign_keys) == 1
    fk = orders_tbl.foreign_keys[0]
    assert fk.target_table == "users"
    assert fk.column_mappings[0].source_column == "user_id"
    assert fk.column_mappings[0].target_column == "id"
    assert fk.on_delete == ForeignKeyAction.CASCADE


def test_mysql_connection_lifecycle_mocked(monkeypatch):
    """Verify MySQLConnection connect and disconnect calls."""
    mock_connect = MagicMock()
    monkeypatch.setattr("pymysql.connect", mock_connect)

    config = ConnectionConfig(
        name="Test MySQL",
        engine="mysql",
        host="127.0.0.1",
        port=3306,
        database="test_db",
        username="user",
        password="pwd",
    )
    conn = MySQLConnection(config)
    conn.connect()
    assert mock_connect.called is True
    assert conn.is_connected() is True

    conn.disconnect()
    assert conn.is_connected() is False
