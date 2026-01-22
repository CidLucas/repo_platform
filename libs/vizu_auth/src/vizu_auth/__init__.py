"""
vizu_auth - Centralized authentication library for Vizu services.

JWT-only authentication using Supabase tokens.
"""

__version__ = "0.2.0"

# Re-export core items
try:
    from vizu_auth.core import (
        AuthDisabledError,
        AuthError,
        AuthMethod,
        AuthResult,
        AuthSettings,
        ClientNotFoundError,
        InvalidTokenError,
        JWTClaims,
        MissingCredentialsError,
        SecretManager,
        TokenExpiredError,
        clear_auth_settings_cache,
        decode_jwt,
        extract_client_id_from_jwt,
        get_auth_settings,
        validate_jwt,
    )
except Exception:
    # Imports will be available after core is implemented and package installed in env
    pass

__all__ = [
    "__version__",
    # Core
    "AuthDisabledError",
    "AuthError",
    "AuthMethod",
    "AuthResult",
    "AuthSettings",
    "ClientNotFoundError",
    "InvalidTokenError",
    "JWTClaims",
    "MissingCredentialsError",
    "SecretManager",
    "TokenExpiredError",
    "clear_auth_settings_cache",
    "decode_jwt",
    "extract_client_id_from_jwt",
    "get_auth_settings",
    "validate_jwt",
]
