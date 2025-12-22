"""
vizu_auth - Centralized authentication library for Vizu services.

Exports core helpers without bringing in FastAPI unless requested via extras.
"""

__version__ = "0.1.0"

# Re-export core items lazily (core package will exist once implemented)
try:
    from vizu_auth.core import (
        AuthDisabledError,
        AuthError,
        AuthMethod,
        AuthRequest,
        AuthResult,
        AuthSettings,
        ClientNotFoundError,
        InvalidApiKeyError,
        InvalidSignatureError,
        InvalidTokenError,
        JWTClaims,
        MissingCredentialsError,
        SecretManager,
        TokenExpiredError,
        clear_auth_settings_cache,
        decode_jwt,
        extract_cliente_vizu_id_from_jwt,
        get_auth_settings,
        validate_jwt,
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
