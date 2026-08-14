"""Application service for Database Connection Profile management."""

from backend_ide.domain.connection import ConnectionProfile
from backend_ide.infrastructure.database.contracts import ConnectionConfig, DatabaseConnection
from backend_ide.infrastructure.database.postgresql import PostgreSQLConnection
from backend_ide.infrastructure.storage.connection_repository import ConnectionRepository


class ConnectionService:
    """Orchestrates connection profile lifecycle and database connection creation."""

    def __init__(self, repository: ConnectionRepository | None = None) -> None:
        self.repository = repository or ConnectionRepository()

    def list_profiles(self) -> list[ConnectionProfile]:
        """List all saved connection profiles."""
        return self.repository.load_all_profiles()

    def get_profile(self, profile_id: str) -> ConnectionProfile | None:
        """Find a profile by ID."""
        for p in self.list_profiles():
            if p.id == profile_id:
                return p
        return None

    def save_profile(self, profile: ConnectionProfile, password: str | None = None) -> None:
        """Save profile metadata and credential."""
        self.repository.save_profile(profile, password)

    def delete_profile(self, profile_id: str) -> bool:
        """Delete profile by ID."""
        return self.repository.delete_profile(profile_id)

    def get_password(self, profile_id: str) -> str | None:
        """Get password for profile."""
        return self.repository.get_password(profile_id)

    def build_connection(
        self,
        profile: ConnectionProfile,
        password: str | None = None,
        database_name: str | None = None,
    ) -> DatabaseConnection:
        """Build database connection adapter from profile."""
        effective_pwd = password if password is not None else self.get_password(profile.id)

        config = ConnectionConfig(
            name=profile.name,
            engine=profile.engine,
            host=profile.host,
            port=profile.port,
            database=database_name or profile.database,
            username=profile.username,
            password=effective_pwd,
            ssl_mode=profile.ssl_mode,
            options=profile.options,
        )

        if profile.engine == "postgresql":
            return PostgreSQLConnection(config)

        # Fallback or generic connection handler
        return PostgreSQLConnection(config)

    def test_connection(self, profile: ConnectionProfile, password: str | None = None) -> bool:
        """Test database connection for profile."""
        adapter = self.build_connection(profile, password)
        return adapter.test_connection()
