"""MySQL Data Type to NormalizedDataType Mapper."""

from __future__ import annotations

import re

from backend_ide.domain.schema.enums import NormalizedDataType


def map_mysql_type_to_normalized(raw_type: str | None) -> NormalizedDataType:
    """Map MySQL raw data type to NormalizedDataType."""
    if not raw_type:
        return NormalizedDataType.TEXT

    clean = raw_type.strip().upper()
    base_type = re.sub(r"\(.*\)", "", clean).strip()

    # Boolean convention in MySQL
    if clean.startswith("TINYINT(1)") or clean == "BOOL" or clean == "BOOLEAN":
        return NormalizedDataType.BOOLEAN

    # Exact matches
    exact_map: dict[str, NormalizedDataType] = {
        "INT": NormalizedDataType.INTEGER,
        "INTEGER": NormalizedDataType.INTEGER,
        "SMALLINT": NormalizedDataType.SMALLINT,
        "TINYINT": NormalizedDataType.SMALLINT,
        "MEDIUMINT": NormalizedDataType.INTEGER,
        "BIGINT": NormalizedDataType.BIGINT,
        "SERIAL": NormalizedDataType.BIGINT,
        "VARCHAR": NormalizedDataType.VARCHAR,
        "CHAR": NormalizedDataType.CHAR,
        "TEXT": NormalizedDataType.TEXT,
        "TINYTEXT": NormalizedDataType.TEXT,
        "MEDIUMTEXT": NormalizedDataType.TEXT,
        "LONGTEXT": NormalizedDataType.TEXT,
        "FLOAT": NormalizedDataType.FLOAT,
        "DOUBLE": NormalizedDataType.FLOAT,
        "DOUBLE PRECISION": NormalizedDataType.FLOAT,
        "DECIMAL": NormalizedDataType.DECIMAL,
        "NUMERIC": NormalizedDataType.DECIMAL,
        "DATE": NormalizedDataType.DATE,
        "DATETIME": NormalizedDataType.DATETIME,
        "TIMESTAMP": NormalizedDataType.TIMESTAMP,
        "TIME": NormalizedDataType.TIME,
        "YEAR": NormalizedDataType.INTEGER,
        "JSON": NormalizedDataType.JSON,
        "BLOB": NormalizedDataType.BINARY,
        "TINYBLOB": NormalizedDataType.BINARY,
        "MEDIUMBLOB": NormalizedDataType.BINARY,
        "LONGBLOB": NormalizedDataType.BINARY,
        "BINARY": NormalizedDataType.BINARY,
        "VARBINARY": NormalizedDataType.BINARY,
        "ENUM": NormalizedDataType.ENUM,
        "SET": NormalizedDataType.TEXT,
    }

    if base_type in exact_map:
        return exact_map[base_type]

    if "INT" in base_type:
        if "BIG" in base_type:
            return NormalizedDataType.BIGINT
        if "SMALL" in base_type or "TINY" in base_type:
            return NormalizedDataType.SMALLINT
        return NormalizedDataType.INTEGER

    if "CHAR" in base_type or "VARCHAR" in base_type:
        return NormalizedDataType.VARCHAR

    if "TEXT" in base_type:
        return NormalizedDataType.TEXT

    if "DEC" in base_type or "NUM" in base_type:
        return NormalizedDataType.DECIMAL

    if "FLOAT" in base_type or "DOUB" in base_type or "REAL" in base_type:
        return NormalizedDataType.FLOAT

    if "TIME" in base_type or "DATE" in base_type:
        if "DATE" in base_type and "TIME" not in base_type:
            return NormalizedDataType.DATE
        return NormalizedDataType.DATETIME

    return NormalizedDataType.TEXT
