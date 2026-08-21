"""Type mapper for Universal Normalized Types to Go (Golang) types."""

from __future__ import annotations

from backend_ide.domain.schema.enums import NormalizedDataType


class GoTypeMapper:
    """Maps NormalizedDataType to idiomatic Go types and pointer nullables."""

    @classmethod
    def map_type(cls, norm_type: NormalizedDataType, is_nullable: bool = False) -> str:
        """Return idiomatic Go type string."""
        type_map: dict[NormalizedDataType, str] = {
            NormalizedDataType.INTEGER: "int",
            NormalizedDataType.BIGINT: "int64",
            NormalizedDataType.SMALLINT: "int16",
            NormalizedDataType.DECIMAL: "float64",
            NormalizedDataType.FLOAT: "float64",
            NormalizedDataType.BOOLEAN: "bool",
            NormalizedDataType.VARCHAR: "string",
            NormalizedDataType.TEXT: "string",
            NormalizedDataType.CHAR: "string",
            NormalizedDataType.DATE: "time.Time",
            NormalizedDataType.TIME: "string",
            NormalizedDataType.DATETIME: "time.Time",
            NormalizedDataType.TIMESTAMP: "time.Time",
            NormalizedDataType.TIMESTAMPTZ: "time.Time",
            NormalizedDataType.UUID: "string",
            NormalizedDataType.JSON: "[]byte",
            NormalizedDataType.JSONB: "[]byte",
            NormalizedDataType.BINARY: "[]byte",
            NormalizedDataType.ARRAY: "[]string",
            NormalizedDataType.ENUM: "string",
            NormalizedDataType.UNKNOWN: "any",
        }

        base = type_map.get(norm_type, "any")
        if is_nullable and base not in ("any", "[]byte", "[]string"):
            return f"*{base}"
        return base
