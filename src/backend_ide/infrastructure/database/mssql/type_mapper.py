"""T-SQL / Microsoft SQL Server Data Type to Universal Normalized Type Mapper."""

from __future__ import annotations

import re

from backend_ide.domain.schema.enums import NormalizedDataType


class MSSQLTypeMapper:
    """Converts native SQL Server T-SQL data types into NormalizedDataType."""

    @classmethod
    def map_native_type(cls, native_type: str) -> NormalizedDataType:
        """Map native T-SQL type (e.g., 'NVARCHAR(255)', 'BIGINT') to NormalizedDataType."""
        if not native_type:
            return NormalizedDataType.UNKNOWN

        clean_type = re.split(r"[\s(]", native_type.strip().upper())[0]

        type_map: dict[str, NormalizedDataType] = {
            # Integers
            "INT": NormalizedDataType.INTEGER,
            "INTEGER": NormalizedDataType.INTEGER,
            "BIGINT": NormalizedDataType.BIGINT,
            "SMALLINT": NormalizedDataType.SMALLINT,
            "TINYINT": NormalizedDataType.SMALLINT,
            # Booleans
            "BIT": NormalizedDataType.BOOLEAN,
            # Decimals / Numeric / Money
            "DECIMAL": NormalizedDataType.DECIMAL,
            "NUMERIC": NormalizedDataType.DECIMAL,
            "MONEY": NormalizedDataType.DECIMAL,
            "SMALLMONEY": NormalizedDataType.DECIMAL,
            "FLOAT": NormalizedDataType.FLOAT,
            "REAL": NormalizedDataType.FLOAT,
            # Strings / Text / Unicode
            "VARCHAR": NormalizedDataType.VARCHAR,
            "NVARCHAR": NormalizedDataType.VARCHAR,
            "CHAR": NormalizedDataType.CHAR,
            "NCHAR": NormalizedDataType.CHAR,
            "TEXT": NormalizedDataType.TEXT,
            "NTEXT": NormalizedDataType.TEXT,
            "SYSNAME": NormalizedDataType.VARCHAR,
            # Dates & Times
            "DATE": NormalizedDataType.DATE,
            "DATETIME": NormalizedDataType.TIMESTAMP,
            "DATETIME2": NormalizedDataType.TIMESTAMP,
            "SMALLDATETIME": NormalizedDataType.TIMESTAMP,
            "DATETIMEOFFSET": NormalizedDataType.TIMESTAMP,
            "TIME": NormalizedDataType.TIME,
            # UUID / Guid
            "UNIQUEIDENTIFIER": NormalizedDataType.UUID,
            # Binary
            "BINARY": NormalizedDataType.BINARY,
            "VARBINARY": NormalizedDataType.BINARY,
            "IMAGE": NormalizedDataType.BINARY,
            # JSON / XML
            "XML": NormalizedDataType.TEXT,
            "JSON": NormalizedDataType.JSON,
        }

        return type_map.get(clean_type, NormalizedDataType.UNKNOWN)
