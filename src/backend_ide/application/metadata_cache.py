"""Connection-scoped in-memory metadata snapshots for editor completion."""

from backend_ide.domain.schema import Column, DatabaseSchema


class ConnectionMetadataCache:
    """Own isolated metadata snapshots and replace them atomically on refresh."""

    def __init__(self) -> None:
        self._snapshots: dict[str, DatabaseSchema] = {}

    def put(self, key: str, schema: DatabaseSchema) -> DatabaseSchema:
        snapshot = schema.model_copy(deep=True)
        self._snapshots[key] = snapshot
        return snapshot

    def get(self, key: str) -> DatabaseSchema | None:
        return self._snapshots.get(key)

    def update_columns(
        self,
        key: str,
        schema_name: str,
        table_name: str,
        columns: list[Column],
    ) -> DatabaseSchema:
        current = self._snapshots.get(key)
        if current is None:
            raise KeyError(key)
        updated = current.model_copy(deep=True)
        table = updated.find_table(table_name, schema_name)
        if table is None:
            raise KeyError(f"{schema_name}.{table_name}")
        table.columns = [column.model_copy(deep=True) for column in columns]
        self._snapshots[key] = updated
        return updated

    def invalidate(self, key: str) -> None:
        self._snapshots.pop(key, None)

    def clear(self) -> None:
        self._snapshots.clear()
