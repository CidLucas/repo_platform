from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class IntegrationProvider(str):
    """Simple enum-like constants for providers"""

    GOOGLE = "google"


class IntegrationConfig(SQLModel, table=True):
    __tablename__ = "integration_configs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    cliente_vizu_id: UUID = Field(foreign_key="cliente_vizu.id", index=True)

    provider: str = Field(index=True)
    config_type: str

    # Encrypted storage (encrypted by application code)
    client_id_encrypted: str
    client_secret_encrypted: str

    # Public configuration
    redirect_uri: str
    scopes: list[str] = Field(sa_column=Column(JSON))

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class IntegrationTokens(SQLModel, table=True):
    __tablename__ = "integration_tokens"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    cliente_vizu_id: UUID = Field(foreign_key="cliente_vizu.id", index=True)
    provider: str = Field(index=True)

    access_token_encrypted: str
    refresh_token_encrypted: str | None = None
    token_type: str | None = None
    expires_at: datetime | None = None
    scopes: list[str] = Field(sa_column=Column(JSON))
    # 'metadata' is a reserved attribute on SQLAlchemy declarative classes.
    # Use `metadata_json` in the Python model but map it to the DB column name 'metadata'.
    metadata_json: dict[str, Any] | None = Field(
        sa_column=Column("metadata", JSON), default=None
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# Lightweight Pydantic helpers used by application code (not mapped tables)


class OAuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None
    expires_in: int | None
    token_type: str | None
    scope: str | None


__all__ = [
    "IntegrationConfig",
    "IntegrationTokens",
    "OAuthTokenResponse",
    "IntegrationProvider",
]
from sqlmodel import Column, SQLModel
