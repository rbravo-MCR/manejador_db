"""Connection-scoped metadata cache behavior."""

from backend_ide.application.metadata_cache import ConnectionMetadataCache
from backend_ide.domain.schema import Column, DatabaseSchema, Schema, Table


def schema_for(database: str) -> DatabaseSchema:
    return DatabaseSchema(
        engine_name="postgresql",
        database_name=database,
        schemas=[Schema(name="public", tables=[Table(name="users")])],
    )


def test_cache_isolates_database_snapshots_and_returns_no_cross_connection_data():
    cache = ConnectionMetadataCache()
    first = schema_for("app")
    second = schema_for("analytics")

    cache.put("profile-a/app", first)
    cache.put("profile-a/analytics", second)

    assert cache.get("profile-a/app").database_name == "app"
    assert cache.get("profile-a/analytics").database_name == "analytics"
    assert cache.get("missing") is None


def test_column_update_replaces_snapshot_atomically():
    cache = ConnectionMetadataCache()
    original = cache.put("profile/app", schema_for("app"))
    columns = [Column(name="email", native_type="TEXT")]

    updated = cache.update_columns("profile/app", "public", "users", columns)

    assert original.find_table("users", "public").columns == []
    assert [column.name for column in updated.find_table("users", "public").columns] == ["email"]
    assert cache.get("profile/app") is updated


def test_cache_invalidation_removes_only_the_requested_connection():
    cache = ConnectionMetadataCache()
    cache.put("a/app", schema_for("app"))
    cache.put("b/app", schema_for("app"))

    cache.invalidate("a/app")

    assert cache.get("a/app") is None
    assert cache.get("b/app") is not None
