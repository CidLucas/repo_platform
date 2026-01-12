"""
Estratégia de autenticação via API-Key.
"""

import logging
from collections.abc import Awaitable, Callable
from uuid import UUID

from vizu_auth.core.exceptions import InvalidApiKeyError
from vizu_auth.core.models import AuthMethod, AuthRequest, AuthResult
from vizu_auth.strategies.base import AuthStrategy

logger = logging.getLogger(__name__)

# Type alias
ApiKeyLookupFn = Callable[[str], Awaitable[UUID | None]]


class ApiKeyStrategy(AuthStrategy):
    def __init__(self, api_key_lookup_fn: ApiKeyLookupFn):
        if not api_key_lookup_fn:
            raise ValueError("api_key_lookup_fn is required for ApiKeyStrategy")
        self._api_key_lookup_fn = api_key_lookup_fn

    def can_handle(self, request: AuthRequest) -> bool:
        return bool(request.api_key)

    async def authenticate(self, request: AuthRequest) -> AuthResult | None:
        if not request.api_key:
            return None

        api_key = request.api_key.strip()
        if not api_key:
            raise InvalidApiKeyError("Empty API key provided")

        client_id = await self._api_key_lookup_fn(api_key)
        if not client_id:
            key_suffix = api_key[-4:] if len(api_key) >= 4 else "****"
            logger.warning(f"Invalid API key ending in ... {key_suffix}")
            raise InvalidApiKeyError("Invalid or expired API key")

        return AuthResult(
            client_id=client_id,
            auth_method=AuthMethod.API_KEY,
            raw_claims={"api_key_suffix": api_key[-4:]},
        )
