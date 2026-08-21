"""Python, SQLAlchemy, SQLModel, and Django Type Mapping."""

from __future__ import annotations

from backend_ide.domain.schema.enums import NormalizedDataType
from backend_ide.domain.schema.models import Column


class PythonTypeMapper:
    """Maps universal database types to Python types and ORM representations."""

    @staticmethod
    def to_python_type(col: Column) -> str:
        """Return native Python type annotation string (e.g. 'int', 'str | None')."""
        type_map: dict[NormalizedDataType, str] = {
            NormalizedDataType.INTEGER: "int",
            NormalizedDataType.BIGINT: "int",
            NormalizedDataType.SMALLINT: "int",
            NormalizedDataType.DECIMAL: "Decimal",
            NormalizedDataType.FLOAT: "float",
            NormalizedDataType.BOOLEAN: "bool",
            NormalizedDataType.VARCHAR: "str",
            NormalizedDataType.TEXT: "str",
            NormalizedDataType.CHAR: "str",
            NormalizedDataType.DATE: "date",
            NormalizedDataType.TIME: "time",
            NormalizedDataType.DATETIME: "datetime",
            NormalizedDataType.TIMESTAMP: "datetime",
            NormalizedDataType.TIMESTAMPTZ: "datetime",
            NormalizedDataType.UUID: "UUID",
            NormalizedDataType.JSON: "dict[str, Any]",
            NormalizedDataType.JSONB: "dict[str, Any]",
            NormalizedDataType.BINARY: "bytes",
            NormalizedDataType.ARRAY: "list[Any]",
            NormalizedDataType.ENUM: "str",
            NormalizedDataType.UNKNOWN: "Any",
        }
        base_type = type_map.get(col.normalized_type, "Any")
        return f"{base_type} | None" if col.is_nullable else base_type

    @staticmethod
    def to_sqlalchemy_type(col: Column) -> str:
        """Return SQLAlchemy 2.0 column type string."""
        nt = col.normalized_type

        if nt == NormalizedDataType.VARCHAR:
            length = col.length or 255
            return f"String({length})"
        elif nt == NormalizedDataType.CHAR:
            length = col.length or 1
            return f"CHAR({length})"
        elif nt == NormalizedDataType.TEXT:
            return "Text()"
        elif nt == NormalizedDataType.INTEGER:
            return "Integer()"
        elif nt == NormalizedDataType.BIGINT:
            return "BigInteger()"
        elif nt == NormalizedDataType.SMALLINT:
            return "SmallInteger()"
        elif nt == NormalizedDataType.DECIMAL:
            p = col.precision or 10
            s = col.scale or 2
            return f"Numeric({p}, {s})"
        elif nt == NormalizedDataType.FLOAT:
            return "Float()"
        elif nt == NormalizedDataType.BOOLEAN:
            return "Boolean()"
        elif nt == NormalizedDataType.DATE:
            return "Date()"
        elif nt == NormalizedDataType.TIME:
            return "Time()"
        elif nt in (NormalizedDataType.DATETIME, NormalizedDataType.TIMESTAMP):
            return "DateTime(timezone=False)"
        elif nt == NormalizedDataType.TIMESTAMPTZ:
            return "DateTime(timezone=True)"
        elif nt == NormalizedDataType.UUID:
            return "Uuid()"
        elif nt in (NormalizedDataType.JSON, NormalizedDataType.JSONB):
            return "JSON()"
        elif nt == NormalizedDataType.BINARY:
            return "LargeBinary()"
        elif nt == NormalizedDataType.ARRAY:
            return "ARRAY(String)"
        elif nt == NormalizedDataType.ENUM:
            return f"Enum(name='{col.name}_enum')"

        return "String(255)"

    @staticmethod
    def to_django_field(col: Column) -> str:
        """Return Django ORM field instantiation string."""
        nt = col.normalized_type
        args: list[str] = []

        if col.is_primary_key:
            args.append("primary_key=True")
        if col.is_nullable:
            args.append("null=True, blank=True")
        if col.default_value and not col.is_auto_increment:
            val = col.default_value
            if val.startswith("'") and val.endswith("'"):
                args.append(f"default={val}")

        args_str = f"({', '.join(args)})" if args else "()"

        if nt in (NormalizedDataType.VARCHAR, NormalizedDataType.CHAR):
            length = col.length or (255 if nt == NormalizedDataType.VARCHAR else 1)
            extra = f", {', '.join(args)}" if args else ""
            return f"models.CharField(max_length={length}{extra})"
        elif nt == NormalizedDataType.TEXT:
            return f"models.TextField{args_str}"
        elif nt == NormalizedDataType.INTEGER:
            if col.is_auto_increment or col.is_primary_key:
                return f"models.AutoField{args_str}"
            return f"models.IntegerField{args_str}"
        elif nt == NormalizedDataType.BIGINT:
            if col.is_auto_increment or col.is_primary_key:
                return f"models.BigAutoField{args_str}"
            return f"models.BigIntegerField{args_str}"
        elif nt == NormalizedDataType.SMALLINT:
            return f"models.SmallIntegerField{args_str}"
        elif nt == NormalizedDataType.DECIMAL:
            p = col.precision or 10
            s = col.scale or 2
            extra = f", {', '.join(args)}" if args else ""
            return f"models.DecimalField(max_digits={p}, decimal_places={s}{extra})"
        elif nt == NormalizedDataType.FLOAT:
            return f"models.FloatField{args_str}"
        elif nt == NormalizedDataType.BOOLEAN:
            return f"models.BooleanField{args_str}"
        elif nt == NormalizedDataType.DATE:
            return f"models.DateField{args_str}"
        elif nt == NormalizedDataType.TIME:
            return f"models.TimeField{args_str}"
        elif nt in (
            NormalizedDataType.DATETIME,
            NormalizedDataType.TIMESTAMP,
            NormalizedDataType.TIMESTAMPTZ,
        ):
            return f"models.DateTimeField{args_str}"
        elif nt == NormalizedDataType.UUID:
            return f"models.UUIDField{args_str}"
        elif nt in (NormalizedDataType.JSON, NormalizedDataType.JSONB):
            return f"models.JSONField{args_str}"
        elif nt == NormalizedDataType.BINARY:
            return f"models.BinaryField{args_str}"

        extra = f", {', '.join(args)}" if args else ""
        return f"models.CharField(max_length=255{extra})"
