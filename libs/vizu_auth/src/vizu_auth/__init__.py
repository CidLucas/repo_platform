"""
vizu_auth - Centralized authentication library for Vizu services.

Exports core helpers without bringing in FastAPI unless requested via extras.
"""

__version__ = "0.1.0"

# Re-export core items lazily (core package will exist once implemented)
try:
    from vizu_auth.core import (
        AuthSettings,
        get_auth_settings,
        clear_auth_settings_cache,
        AuthError,
        MissingCredentialsError,
        InvalidTokenError,
        TokenExpiredError,
        InvalidSignatureError,
        InvalidApiKeyError,
        ClientNotFoundError,
        AuthDisabledError,
        decode_jwt,
        validate_jwt,
        extract_cliente_vizu_id_from_jwt,
        AuthMethod,
        AuthRequest,
        AuthResult,
        JWTClaims,
    )
except Exception:
    # Imports will be available after core is implemented and package installed in env
    pass

from vizu_auth.adapters.context_service_adapter import (
    api_key_lookup_from_context_service,
    external_user_lookup_from_context_service,
)

__all__ = [
    "__version__",
    # adapters
    "api_key_lookup_from_context_service",
    "external_user_lookup_from_context_service",
]
