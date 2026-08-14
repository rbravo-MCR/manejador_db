"""PostgreSQL Data Type Mapper to NormalizedDataType."""

from backend_ide.domain.schema.enums import NormalizedDataType

_PG_TYPE_MAP: dict[str, NormalizedDataType] = {
    "integer": NormalizedDataType.INTEGER,
    "int": NormalizedDataType.INTEGER,
    "int4": NormalizedDataType.INTEGER,
    "bigint": NormalizedDataType.BIGINT,
    "int8": NormalizedDataType.BIGINT,
    "smallint": NormalizedDataType.SMALLINT,
    "int2": NormalizedDataType.SMALLINT,
    "serial": NormalizedDataType.INTEGER,
    "bigserial": NormalizedDataType.BIGINT,
    "smallserial": NormalizedDataType.SMALLINT,
    "decimal": NormalizedDataType.DECIMAL,
    "numeric": NormalizedDataType.DECIMAL,
    "real": NormalizedDataType.FLOAT,
    "float4": NormalizedDataType.FLOAT,
    "double precision": NormalizedDataType.FLOAT,
    "float8": NormalizedDataType.FLOAT,
    "boolean": NormalizedDataType.BOOLEAN,
    "bool": NormalizedDataType.BOOLEAN,
    "character varying": NormalizedDataType.VARCHAR,
    "varchar": NormalizedDataType.VARCHAR,
    "character": NormalizedDataType.CHAR,
    "char": NormalizedDataType.CHAR,
    "text": NormalizedDataType.TEXT,
    "date": NormalizedDataType.DATE,
    "time": NormalizedDataType.TIME,
    "time without time zone": NormalizedDataType.TIME,
    "time with time zone": NormalizedDataType.TIME,
    "timestamp": NormalizedDataType.TIMESTAMP,
    "timestamp without time zone": NormalizedDataType.TIMESTAMP,
    "timestamp with time zone": NormalizedDataType.TIMESTAMPTZ,
    "timestamptz": NormalizedDataType.TIMESTAMPTZ,
    "uuid": NormalizedDataType.UUID,
    "json": NormalizedDataType.JSON,
    "jsonb": NormalizedDataType.JSONB,
    "bytea": NormalizedDataType.BINARY,
    "user-defined": NormalizedDataType.ENUM,
    "ARRAY": NormalizedDataType.ARRAY,
}


def map_pg_type_to_normalized(raw_type: str) -> NormalizedDataType:
    """Map PostgreSQL data type string to NormalizedDataType."""
    clean_type = raw_type.lower().strip()
    if clean_type.endswith("[]") or "array" in clean_type:
        return NormalizedDataType.ARRAY

    # Extract base type before modifiers like (255)
    base_type = clean_type.split("(")[0].strip()
    return _PG_TYPE_MAP.get(base_type, NormalizedDataType.UNKNOWN)
