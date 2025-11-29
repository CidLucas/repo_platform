"""
Modelos Pydantic para autenticação.
"""

from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AuthMethod(str, Enum):
    JWT = "jwt"
    API_KEY = "api_key"
    NONE = "none"


class JWTClaims(BaseModel):
    sub: str = Field(..., description="Subject - Supabase user ID")
    aud: Optional[str] = None
    exp: Optional[int] = None
    iat: Optional[int] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    cliente_vizu_id: Optional[UUID] = None

    class Config:
        extra = "allow"


class AuthResult(BaseModel):
    cliente_vizu_id: UUID
    auth_method: AuthMethod
    external_user_id: Optional[str] = None
    email: Optional[str] = None
    raw_claims: Dict[str, Any] = Field(default_factory=dict)

    @property
    def is_jwt_auth(self) -> bool:
        return self.auth_method == AuthMethod.JWT

    @property
    def is_api_key_auth(self) -> bool:
        return self.auth_method == AuthMethod.API_KEY


class AuthRequest(BaseModel):
    jwt_token: Optional[str] = None
    api_key: Optional[str] = None

    def has_credentials(self) -> bool:
        return bool(self.jwt_token or self.api_key)
