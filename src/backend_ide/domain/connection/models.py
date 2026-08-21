"""Domain models for Database Connection Profiles."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Environment(StrEnum):
    """Connection environment classification."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class ConnectionProfile(BaseModel):
    """Saved database connection profile."""

    model_config = ConfigDict(frozen=False)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    engine: str  # postgresql, mysql, sqlite, sqlserver
    host: str = "localhost"
    port: int = 5432
    database: str = "postgres"
    username: str = "postgres"
    environment: Environment = Environment.DEVELOPMENT
    color: str | None = None  # Optional UI accent color
    group_name: str | None = None
    ssl_mode: str = "prefer"
    options: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    def update_timestamp(self) -> None:
        """Update last modified timestamp."""
        self.updated_at = datetime.now(UTC).isoformat()
