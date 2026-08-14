"""Enumerations for the Universal Schema Model."""

from enum import StrEnum


class NormalizedDataType(StrEnum):
    """Normalized database-agnostic data types."""

    INTEGER = "integer"
    BIGINT = "bigint"
    SMALLINT = "smallint"
    DECIMAL = "decimal"
    FLOAT = "float"
    BOOLEAN = "boolean"
    VARCHAR = "varchar"
    TEXT = "text"
    CHAR = "char"
    DATE = "date"
    TIME = "time"
    DATETIME = "datetime"
    TIMESTAMP = "timestamp"
    TIMESTAMPTZ = "timestamptz"
    UUID = "uuid"
    JSON = "json"
    JSONB = "jsonb"
    BINARY = "binary"
    ARRAY = "array"
    ENUM = "enum"
    UNKNOWN = "unknown"


class ForeignKeyAction(StrEnum):
    """Referential action for foreign keys."""

    NO_ACTION = "NO ACTION"
    RESTRICT = "RESTRICT"
    CASCADE = "CASCADE"
    SET_NULL = "SET NULL"
    SET_DEFAULT = "SET DEFAULT"


class IndexType(StrEnum):
    """Index algorithm / type."""

    BTREE = "btree"
    HASH = "hash"
    GIN = "gin"
    GIST = "gist"
    FULLTEXT = "fulltext"
    UNIQUE = "unique"
    OTHER = "other"


class RoutineType(StrEnum):
    """Database routine type."""

    FUNCTION = "function"
    PROCEDURE = "procedure"
