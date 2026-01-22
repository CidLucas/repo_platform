"""
Modelos Pydantic para autenticação JWT.
"""

from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AuthMethod(str, Enum):
    JWT = "jwt"
    NONE = "none"


class JWTClaims(BaseModel):
    sub: str = Field(..., description="Subject - Supabase user ID")
    aud: str | None = None
    exp: int | None = None
    iat: int | None = None
    email: str | None = None
    phone: str | None = None
    role: str | None = None
    client_id: UUID | None = None

    class Config:
        extra = "allow"


class AuthResult(BaseModel):
    client_id: UUID
    auth_method: AuthMethod
    external_user_id: str | None = None
    email: str | None = None
    raw_claims: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_jwt_auth(self) -> bool:
        return self.auth_method == AuthMethod.JWT
