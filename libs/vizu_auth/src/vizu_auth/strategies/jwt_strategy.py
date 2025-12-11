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

        cliente_vizu_id = claims.cliente_vizu_id

        if not cliente_vizu_id and self._cliente_lookup_fn:
            cliente_vizu_id = await self._cliente_lookup_fn(claims.sub)

        if not cliente_vizu_id:
            logger.warning(f"Could not resolve cliente_vizu_id for user {claims.sub}")
            raise ClientNotFoundError(f"No Vizu client associated with user: {claims.sub}")

        return AuthResult(
            cliente_vizu_id=cliente_vizu_id,
            auth_method=AuthMethod.JWT,
            external_user_id=claims.sub,
            email=claims.email,
            raw_claims=claims.model_dump(exclude_none=True),
        )
