"""C#, Entity Framework Core, and Dapper Type Mapping."""

from __future__ import annotations

from backend_ide.domain.schema.enums import NormalizedDataType
from backend_ide.domain.schema.models import Column


class CSharpTypeMapper:
    """Maps universal database types to C# / .NET types."""

    @staticmethod
    def to_csharp_type(col: Column) -> str:
        """Return C# type string (e.g. 'int', 'string?', 'DateTime', 'Guid?')."""
        type_map: dict[NormalizedDataType, tuple[str, bool]] = {
            # (Type name, is_value_type)
            NormalizedDataType.INTEGER: ("int", True),
            NormalizedDataType.BIGINT: ("long", True),
            NormalizedDataType.SMALLINT: ("short", True),
            NormalizedDataType.DECIMAL: ("decimal", True),
            NormalizedDataType.FLOAT: ("double", True),
            NormalizedDataType.BOOLEAN: ("bool", True),
            NormalizedDataType.VARCHAR: ("string", False),
            NormalizedDataType.TEXT: ("string", False),
            NormalizedDataType.CHAR: ("string", False),
            NormalizedDataType.DATE: ("DateOnly", True),
            NormalizedDataType.TIME: ("TimeOnly", True),
            NormalizedDataType.DATETIME: ("DateTime", True),
            NormalizedDataType.TIMESTAMP: ("DateTime", True),
            NormalizedDataType.TIMESTAMPTZ: ("DateTimeOffset", True),
            NormalizedDataType.UUID: ("Guid", True),
            NormalizedDataType.JSON: ("string", False),
            NormalizedDataType.JSONB: ("string", False),
            NormalizedDataType.BINARY: ("byte[]", False),
            NormalizedDataType.ARRAY: ("string[]", False),
            NormalizedDataType.ENUM: ("string", False),
            NormalizedDataType.UNKNOWN: ("object", False),
        }

        type_name, is_value_type = type_map.get(col.normalized_type, ("object", False))

        if col.is_nullable:
            return f"{type_name}?"

        return type_name
