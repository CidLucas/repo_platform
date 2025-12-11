"""
vizu_auth.core - Core authentication components.
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
    InvalidApiKeyError,
    InvalidSignatureError,
    InvalidTokenError,
    MissingCredentialsError,
    TokenExpiredError,
)
from vizu_auth.core.jwt_decoder import (
    decode_jwt,
    extract_cliente_vizu_id_from_jwt,
    validate_jwt,
)
from vizu_auth.core.models import (
    AuthMethod,
    AuthRequest,
    AuthResult,
    JWTClaims,
)

__all__ = [
    "AuthSettings",
    "get_auth_settings",
    "clear_auth_settings_cache",
    "AuthError",
    "MissingCredentialsError",
    "InvalidTokenError",
    "TokenExpiredError",
    "InvalidSignatureError",
    "InvalidApiKeyError",
    "ClientNotFoundError",
    "AuthDisabledError",
    "decode_jwt",
    "validate_jwt",
    "extract_cliente_vizu_id_from_jwt",
    "AuthMethod",
    "AuthRequest",
    "AuthResult",
    "JWTClaims",
]
