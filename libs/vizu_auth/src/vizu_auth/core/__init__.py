"""
vizu_auth.core - Core authentication components (JWT-only).
"""

from vizu_auth.core.config import (
    AuthSettings,
    clear_auth_settings_cache,
    get_auth_settings,
)
from vizu_auth.core.exceptions import (
    AuthDisabledError,
    AuthError,
    ClientNotFoundError,
    InvalidTokenError,
    MissingCredentialsError,
    TokenExpiredError,
)
from vizu_auth.core.jwt_decoder import (
    decode_jwt,
    extract_client_id_from_jwt,
    validate_jwt,
)
from vizu_auth.core.models import (
    AuthMethod,
    AuthResult,
    JWTClaims,
)
from vizu_auth.core.secret_manager import SecretManager

__all__ = [
    "AuthSettings",
    "get_auth_settings",
    "clear_auth_settings_cache",
    "AuthError",
    "MissingCredentialsError",
    "InvalidTokenError",
    "TokenExpiredError",
    "ClientNotFoundError",
    "AuthDisabledError",
    "decode_jwt",
    "validate_jwt",
    "extract_client_id_from_jwt",
    "AuthMethod",
    "AuthResult",
    "JWTClaims",
    "SecretManager",
]
