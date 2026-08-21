"""SQLite Data Type to NormalizedDataType Mapper."""

import re

from backend_ide.domain.schema.enums import NormalizedDataType


def map_sqlite_type_to_normalized(raw_type: str | None) -> NormalizedDataType:
    """Map SQLite raw type string or affinity to NormalizedDataType.

    Rules follow SQLite 3 type affinity logic:
    1. If the declared type contains "INT", it is mapped to INTEGER or BIGINT.
    2. If the declared type contains "CHAR", "CLOB", or "TEXT", it is mapped to TEXT / VARCHAR.
    3. If the declared type contains "BLOB" or if no type is specified, it is mapped to BINARY.
    4. If the declared type contains "REAL", "FLOA", or "DOUB", it is mapped to FLOAT.
    5. If the declared type contains "DECIMAL" or "NUMERIC", it is mapped to DECIMAL.
    6. Date/time/JSON/boolean types are recognized explicitly.
    """
    if not raw_type:
        return NormalizedDataType.TEXT

    clean = raw_type.strip().upper()
    base_type = re.sub(r"\(.*\)", "", clean).strip()

    # Exact matches
    exact_map: dict[str, NormalizedDataType] = {
        "INT": NormalizedDataType.INTEGER,
        "INTEGER": NormalizedDataType.INTEGER,
        "TINYINT": NormalizedDataType.SMALLINT,
        "SMALLINT": NormalizedDataType.SMALLINT,
        "MEDIUMINT": NormalizedDataType.INTEGER,
        "BIGINT": NormalizedDataType.BIGINT,
        "UNSIGNED BIG INT": NormalizedDataType.BIGINT,
        "INT2": NormalizedDataType.SMALLINT,
        "INT8": NormalizedDataType.BIGINT,
        "TEXT": NormalizedDataType.TEXT,
        "CLOB": NormalizedDataType.TEXT,
        "VARCHAR": NormalizedDataType.VARCHAR,
        "NVARCHAR": NormalizedDataType.VARCHAR,
        "CHAR": NormalizedDataType.CHAR,
        "NCHAR": NormalizedDataType.CHAR,
        "BLOB": NormalizedDataType.BINARY,
        "REAL": NormalizedDataType.FLOAT,
        "DOUBLE": NormalizedDataType.FLOAT,
        "DOUBLE PRECISION": NormalizedDataType.FLOAT,
        "FLOAT": NormalizedDataType.FLOAT,
        "DECIMAL": NormalizedDataType.DECIMAL,
        "NUMERIC": NormalizedDataType.DECIMAL,
        "BOOLEAN": NormalizedDataType.BOOLEAN,
        "BOOL": NormalizedDataType.BOOLEAN,
        "DATE": NormalizedDataType.DATE,
        "DATETIME": NormalizedDataType.DATETIME,
        "TIMESTAMP": NormalizedDataType.TIMESTAMP,
        "TIME": NormalizedDataType.TIME,
        "JSON": NormalizedDataType.JSON,
        "UUID": NormalizedDataType.UUID,
    }

    if base_type in exact_map:
        return exact_map[base_type]

    # Pattern matches
    if "INT" in base_type:
        if "BIG" in base_type or "8" in base_type:
            return NormalizedDataType.BIGINT
        if "SMALL" in base_type or "TINY" in base_type or "2" in base_type:
            return NormalizedDataType.SMALLINT
        return NormalizedDataType.INTEGER

    if "CHAR" in base_type or "VARCHAR" in base_type:
        return NormalizedDataType.VARCHAR

    if "TEXT" in base_type or "CLOB" in base_type:
        return NormalizedDataType.TEXT

    if "BLOB" in base_type or "BIN" in base_type:
        return NormalizedDataType.BINARY

    if "REAL" in base_type or "FLOA" in base_type or "DOUB" in base_type:
        return NormalizedDataType.FLOAT

    if "DEC" in base_type or "NUM" in base_type:
        return NormalizedDataType.DECIMAL

    if "TIME" in base_type or "DATE" in base_type:
        if "DATE" in base_type and "TIME" not in base_type:
            return NormalizedDataType.DATE
        return NormalizedDataType.DATETIME

    if "BOOL" in base_type:
        return NormalizedDataType.BOOLEAN

    if "JSON" in base_type:
        return NormalizedDataType.JSON

    return NormalizedDataType.TEXT
