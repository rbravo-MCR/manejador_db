"""PHP and Laravel Eloquent Type Mapping."""

from __future__ import annotations

from backend_ide.domain.schema.enums import NormalizedDataType
from backend_ide.domain.schema.models import Column


class PHPTypeMapper:
    """Maps universal database types to PHP and Laravel Eloquent representations."""

    @staticmethod
    def to_php_type(col: Column) -> str:
        """Return PHP 8+ property type hint string (e.g. '?int', 'string')."""
        type_map: dict[NormalizedDataType, str] = {
            NormalizedDataType.INTEGER: "int",
            NormalizedDataType.BIGINT: "int",
            NormalizedDataType.SMALLINT: "int",
            NormalizedDataType.DECIMAL: "float",
            NormalizedDataType.FLOAT: "float",
            NormalizedDataType.BOOLEAN: "bool",
            NormalizedDataType.VARCHAR: "string",
            NormalizedDataType.TEXT: "string",
            NormalizedDataType.CHAR: "string",
            NormalizedDataType.DATE: "\\DateTimeInterface",
            NormalizedDataType.TIME: "string",
            NormalizedDataType.DATETIME: "\\DateTimeInterface",
            NormalizedDataType.TIMESTAMP: "\\DateTimeInterface",
            NormalizedDataType.TIMESTAMPTZ: "\\DateTimeInterface",
            NormalizedDataType.UUID: "string",
            NormalizedDataType.JSON: "array",
            NormalizedDataType.JSONB: "array",
            NormalizedDataType.BINARY: "string",
            NormalizedDataType.ARRAY: "array",
            NormalizedDataType.ENUM: "string",
            NormalizedDataType.UNKNOWN: "mixed",
        }
        base_type = type_map.get(col.normalized_type, "mixed")
        return f"?{base_type}" if col.is_nullable else base_type

    @staticmethod
    def to_eloquent_cast(col: Column) -> str | None:
        """Return Eloquent $casts array value string or None if implicit."""
        nt = col.normalized_type

        if nt in (
            NormalizedDataType.INTEGER,
            NormalizedDataType.BIGINT,
            NormalizedDataType.SMALLINT,
        ):
            return "'integer'"
        elif nt == NormalizedDataType.BOOLEAN:
            return "'boolean'"
        elif nt == NormalizedDataType.DECIMAL:
            scale = col.scale or 2
            return f"'decimal:{scale}'"
        elif nt == NormalizedDataType.FLOAT:
            return "'float'"
        elif nt in (
            NormalizedDataType.DATETIME,
            NormalizedDataType.TIMESTAMP,
            NormalizedDataType.TIMESTAMPTZ,
        ):
            return "'datetime'"
        elif nt == NormalizedDataType.DATE:
            return "'date'"
        elif nt in (NormalizedDataType.JSON, NormalizedDataType.JSONB, NormalizedDataType.ARRAY):
            return "'array'"

        return None
