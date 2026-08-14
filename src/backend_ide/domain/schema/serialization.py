"""Serialization and Deserialization utilities for Universal Schema Model."""

from typing import Any

from backend_ide.domain.schema.models import DatabaseSchema


def schema_to_dict(schema: DatabaseSchema) -> dict[str, Any]:
    """Serialize DatabaseSchema instance to python dict."""
    return schema.model_dump(mode="json")


def schema_from_dict(data: dict[str, Any]) -> DatabaseSchema:
    """Deserialize python dict to DatabaseSchema instance."""
    return DatabaseSchema.model_validate(data)


def schema_to_json(schema: DatabaseSchema, indent: int = 2) -> str:
    """Serialize DatabaseSchema instance to JSON string."""
    return schema.model_dump_json(indent=indent)


def schema_from_json(json_str: str) -> DatabaseSchema:
    """Deserialize JSON string to DatabaseSchema instance."""
    return DatabaseSchema.model_validate_json(json_str)
