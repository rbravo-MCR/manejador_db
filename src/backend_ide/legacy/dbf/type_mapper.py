"""Type Mapper for converting Legacy DBF Field descriptors to Universal Schema Model Types."""

from __future__ import annotations

from backend_ide.domain.schema.enums import NormalizedDataType
from backend_ide.domain.schema.models import Column
from backend_ide.legacy.dbf.models import DBFField, DBFFieldType


class DBFTypeMapper:
    """Maps DBF field descriptors to normalized database data types and Column models."""

    @staticmethod
    def to_normalized_type(field: DBFField) -> NormalizedDataType:
        """Map DBF field type character to neutral NormalizedDataType."""
        ft = field.field_type

        if ft == DBFFieldType.CHARACTER:
            return NormalizedDataType.VARCHAR
        elif ft == DBFFieldType.VARCHAR:
            return NormalizedDataType.VARCHAR
        elif ft == DBFFieldType.MEMO:
            return NormalizedDataType.TEXT
        elif ft == DBFFieldType.LOGICAL:
            return NormalizedDataType.BOOLEAN
        elif ft == DBFFieldType.DATE:
            return NormalizedDataType.DATE
        elif ft == DBFFieldType.DATETIME:
            return NormalizedDataType.DATETIME
        elif ft == DBFFieldType.FLOAT:
            return NormalizedDataType.FLOAT
        elif ft == DBFFieldType.DOUBLE:
            return NormalizedDataType.FLOAT
        elif ft == DBFFieldType.INTEGER:
            return NormalizedDataType.INTEGER
        elif ft == DBFFieldType.CURRENCY:
            return NormalizedDataType.DECIMAL
        elif ft == DBFFieldType.VARBINARY:
            return NormalizedDataType.BINARY
        elif ft == DBFFieldType.NUMERIC:
            if field.decimal_count > 0:
                return NormalizedDataType.DECIMAL
            if field.length > 9:
                return NormalizedDataType.BIGINT
            return NormalizedDataType.INTEGER

        return NormalizedDataType.VARCHAR

    @classmethod
    def to_column_model(cls, field: DBFField, *, sanitize_name: bool = True) -> Column:
        """Convert a DBFField to a Universal Schema Model Column."""
        norm_type = cls.to_normalized_type(field)
        col_name = field.name.lower() if sanitize_name else field.name

        native_type = f"DBF_{field.field_type.value}"
        if field.length:
            native_type += f"({field.length}"
            if field.decimal_count:
                native_type += f",{field.decimal_count}"
            native_type += ")"

        precision = field.length if norm_type == NormalizedDataType.DECIMAL else None
        scale = field.decimal_count if norm_type == NormalizedDataType.DECIMAL else None
        length = (
            field.length
            if norm_type in (NormalizedDataType.VARCHAR, NormalizedDataType.CHAR)
            else None
        )

        return Column(
            name=col_name,
            native_type=native_type,
            normalized_type=norm_type,
            is_nullable=True,
            is_primary_key=False,
            is_auto_increment=False,
            length=length,
            precision=precision,
            scale=scale,
        )
