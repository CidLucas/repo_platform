"""
Estratégia de autenticação via JWT (Supabase).
"""

import logging
from collections.abc import Awaitable, Callable
from uuid import UUID

from vizu_auth.core.exceptions import ClientNotFoundError
from vizu_auth.core.jwt_decoder import decode_jwt
from vizu_auth.core.models import AuthMethod, AuthRequest, AuthResult, JWTClaims
from vizu_auth.strategies.base import AuthStrategy

logger = logging.getLogger(__name__)

# Type alias
ClienteLookupFn = Callable[[str], Awaitable[UUID | None]]


class JWTStrategy(AuthStrategy):
    def __init__(self, cliente_lookup_fn: ClienteLookupFn | None = None):
        self._cliente_lookup_fn = cliente_lookup_fn

    def can_handle(self, request: AuthRequest) -> bool:
        return bool(request.jwt_token)

    async def authenticate(self, request: AuthRequest) -> AuthResult | None:
        if not request.jwt_token:
            return None

        claims: JWTClaims = decode_jwt(request.jwt_token)

        client_id = claims.client_id

        if not client_id and self._cliente_lookup_fn:
            client_id = await self._cliente_lookup_fn(claims.sub)

        # If still no client_id, use the Supabase user ID (sub claim) directly
        # This allows users to authenticate without needing a pre-existing database record
        if not client_id:
            logger.info(f"Using Supabase user ID as client_id for user {claims.sub}")
            try:
                client_id = UUID(claims.sub)
            except (ValueError, TypeError) as e:
                logger.error(f"Invalid UUID in JWT sub claim: {claims.sub}, error: {e}")
                raise ClientNotFoundError(f"Invalid user ID format: {claims.sub}")

        return AuthResult(
            client_id=client_id,
            auth_method=AuthMethod.JWT,
            external_user_id=claims.sub,
            email=claims.email,
            raw_claims=claims.model_dump(exclude_none=True),
        )
