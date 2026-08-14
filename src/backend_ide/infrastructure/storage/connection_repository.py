"""Connection Profile Storage Repository with Keyring Security."""

import json
from pathlib import Path

import keyring

from backend_ide.domain.connection import ConnectionProfile
from backend_ide.infrastructure.logging import get_logger

logger = get_logger(__name__)

KEYRING_SERVICE_NAME = "backend-development-ide"


class ConnectionRepository:
    """Repository for managing saved connection profiles and secure credentials."""

    def __init__(self, storage_path: Path | None = None) -> None:
        if storage_path is None:
            config_dir = Path.home() / ".backendide"
            config_dir.mkdir(parents=True, exist_ok=True)
            storage_path = config_dir / "connections.json"

        self.storage_path = storage_path

    def load_all_profiles(self) -> list[ConnectionProfile]:
        """Load all connection profiles from storage (without secrets)."""
        if not self.storage_path.exists():
            return []

        try:
            content = self.storage_path.read_text(encoding="utf-8")
            if not content.strip():
                return []
            data = json.loads(content)
            return [ConnectionProfile.model_validate(item) for item in data]
        except Exception as err:
            logger.error("Failed to load connection profiles", error=str(err))
            return []

    def save_profile(self, profile: ConnectionProfile, password: str | None = None) -> None:
        """Save connection profile and store password securely in OS keyring."""
        profiles = self.load_all_profiles()

        # Update or append profile
        existing_index = next((i for i, p in enumerate(profiles) if p.id == profile.id), None)
        profile.update_timestamp()

        if existing_index is not None:
            profiles[existing_index] = profile
        else:
            profiles.append(profile)

        # Store password in keyring if provided
        if password is not None:
            try:
                keyring.set_password(KEYRING_SERVICE_NAME, profile.id, password)
                logger.info("Stored credential in keyring", profile_id=profile.id)
            except Exception as err:
                logger.warning("Failed to store credential in keyring", error=str(err))

        self._flush_profiles(profiles)

    def delete_profile(self, profile_id: str) -> bool:
        """Delete a connection profile and remove its password from keyring."""
        profiles = self.load_all_profiles()
        new_profiles = [p for p in profiles if p.id != profile_id]

        if len(new_profiles) == len(profiles):
            return False

        # Delete password from keyring
        try:
            keyring.delete_password(KEYRING_SERVICE_NAME, profile_id)
        except Exception as err:
            logger.warning("Could not delete keyring credential or none existed", error=str(err))

        self._flush_profiles(new_profiles)
        return True

    def get_password(self, profile_id: str) -> str | None:
        """Retrieve password for profile from OS keyring."""
        try:
            return keyring.get_password(KEYRING_SERVICE_NAME, profile_id)
        except Exception as err:
            logger.warning("Failed to retrieve password from keyring", error=str(err))
            return None

    def _flush_profiles(self, profiles: list[ConnectionProfile]) -> None:
        """Flush profiles list to JSON storage."""
        data = [p.model_dump(mode="json") for p in profiles]
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
