"""TypeScript, Prisma, and Drizzle ORM Type Mapping."""

from __future__ import annotations

from backend_ide.domain.schema.enums import NormalizedDataType
from backend_ide.domain.schema.models import Column


class TypeScriptTypeMapper:
    """Maps universal database types to TypeScript, Prisma, and Drizzle types."""

    @staticmethod
    def to_ts_type(col: Column) -> str:
        """Return TypeScript type annotation string (e.g. 'number', 'string | null')."""
        type_map: dict[NormalizedDataType, str] = {
            NormalizedDataType.INTEGER: "number",
            NormalizedDataType.BIGINT: "number",
            NormalizedDataType.SMALLINT: "number",
            NormalizedDataType.DECIMAL: "number",
            NormalizedDataType.FLOAT: "number",
            NormalizedDataType.BOOLEAN: "boolean",
            NormalizedDataType.VARCHAR: "string",
            NormalizedDataType.TEXT: "string",
            NormalizedDataType.CHAR: "string",
            NormalizedDataType.DATE: "Date",
            NormalizedDataType.TIME: "string",
            NormalizedDataType.DATETIME: "Date",
            NormalizedDataType.TIMESTAMP: "Date",
            NormalizedDataType.TIMESTAMPTZ: "Date",
            NormalizedDataType.UUID: "string",
            NormalizedDataType.JSON: "Record<string, unknown>",
            NormalizedDataType.JSONB: "Record<string, unknown>",
            NormalizedDataType.BINARY: "Buffer",
            NormalizedDataType.ARRAY: "unknown[]",
            NormalizedDataType.ENUM: "string",
            NormalizedDataType.UNKNOWN: "unknown",
        }
        base_type = type_map.get(col.normalized_type, "unknown")
        return f"{base_type} | null" if col.is_nullable else base_type

    @staticmethod
    def to_prisma_type(col: Column) -> str:
        """Return Prisma schema scalar type (e.g. 'Int', 'String', 'DateTime?')."""
        type_map: dict[NormalizedDataType, str] = {
            NormalizedDataType.INTEGER: "Int",
            NormalizedDataType.BIGINT: "BigInt",
            NormalizedDataType.SMALLINT: "Int",
            NormalizedDataType.DECIMAL: "Decimal",
            NormalizedDataType.FLOAT: "Float",
            NormalizedDataType.BOOLEAN: "Boolean",
            NormalizedDataType.VARCHAR: "String",
            NormalizedDataType.TEXT: "String",
            NormalizedDataType.CHAR: "String",
            NormalizedDataType.DATE: "DateTime",
            NormalizedDataType.TIME: "String",
            NormalizedDataType.DATETIME: "DateTime",
            NormalizedDataType.TIMESTAMP: "DateTime",
            NormalizedDataType.TIMESTAMPTZ: "DateTime",
            NormalizedDataType.UUID: "String",
            NormalizedDataType.JSON: "Json",
            NormalizedDataType.JSONB: "Json",
            NormalizedDataType.BINARY: "Bytes",
            NormalizedDataType.ARRAY: "String[]",
            NormalizedDataType.ENUM: "String",
            NormalizedDataType.UNKNOWN: "String",
        }
        base_type = type_map.get(col.normalized_type, "String")
        return f"{base_type}?" if col.is_nullable and not col.is_primary_key else base_type

    @staticmethod
    def to_drizzle_column(col: Column) -> str:
        """Return Drizzle ORM column builder string for PostgreSQL/Generic dialect."""
        nt = col.normalized_type
        field_name = col.name

        if nt == NormalizedDataType.INTEGER:
            if col.is_auto_increment and col.is_primary_key:
                return f'serial("{field_name}").primaryKey()'
            builder = f'integer("{field_name}")'
        elif nt == NormalizedDataType.BIGINT:
            if col.is_auto_increment and col.is_primary_key:
                return f'bigserial("{field_name}", {{ mode: "number" }}).primaryKey()'
            builder = f'bigint("{field_name}", {{ mode: "number" }})'
        elif nt == NormalizedDataType.SMALLINT:
            if col.is_auto_increment and col.is_primary_key:
                return f'smallserial("{field_name}").primaryKey()'
            builder = f'smallint("{field_name}")'
        elif nt == NormalizedDataType.VARCHAR:
            length = col.length or 255
            builder = f'varchar("{field_name}", {{ length: {length} }})'
        elif nt == NormalizedDataType.CHAR:
            length = col.length or 1
            builder = f'char("{field_name}", {{ length: {length} }})'
        elif nt == NormalizedDataType.TEXT:
            builder = f'text("{field_name}")'
        elif nt == NormalizedDataType.BOOLEAN:
            builder = f'boolean("{field_name}")'
        elif nt == NormalizedDataType.DECIMAL:
            p = col.precision or 10
            s = col.scale or 2
            builder = f'decimal("{field_name}", {{ precision: {p}, scale: {s} }})'
        elif nt in (
            NormalizedDataType.DATETIME,
            NormalizedDataType.TIMESTAMP,
            NormalizedDataType.TIMESTAMPTZ,
        ):
            builder = f'timestamp("{field_name}", {{ withTimezone: true }})'
        elif nt == NormalizedDataType.DATE:
            builder = f'date("{field_name}")'
        elif nt == NormalizedDataType.UUID:
            builder = f'uuid("{field_name}")'
        elif nt in (NormalizedDataType.JSON, NormalizedDataType.JSONB):
            builder = f'jsonb("{field_name}")'
        else:
            builder = f'text("{field_name}")'

        # Modifiers
        if col.is_primary_key and "primaryKey" not in builder:
            builder += ".primaryKey()"
        if not col.is_nullable:
            builder += ".notNull()"
        if col.default_value and not col.is_auto_increment:
            if col.default_value.lower() in ("now()", "current_timestamp"):
                builder += ".defaultNow()"
            elif col.default_value.lower() == "true":
                builder += ".default(true)"
            elif col.default_value.lower() == "false":
                builder += ".default(false)"
            elif col.default_value.isdigit():
                builder += f".default({col.default_value})"

        return builder
