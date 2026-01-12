"""
Orquestrador de autenticação - tenta estratégias em ordem.
"""

import logging

from vizu_auth.core.config import get_auth_settings
from vizu_auth.core.exceptions import AuthDisabledError, AuthError, MissingCredentialsError
from vizu_auth.core.models import AuthRequest, AuthResult
from vizu_auth.strategies.base import AuthStrategy

logger = logging.getLogger(__name__)


class Authenticator:
    def __init__(self, strategies: list[AuthStrategy], *, allow_auth_disabled: bool = False):
        self._strategies = strategies
        self._allow_auth_disabled = allow_auth_disabled

    async def authenticate(self, request: AuthRequest, *, require_auth: bool = True) -> AuthResult | None:
        settings = get_auth_settings()

        if not settings.auth_enabled:
            if self._allow_auth_disabled:
                logger.warning("AUTH DISABLED - returning dev mock result")
                from uuid import UUID

                return AuthResult(
                    client_id=UUID("00000000-0000-0000-0000-000000000001"),
                    auth_method="none",
                    external_user_id="dev-user",
                    email="dev@vizu.local",
                    raw_claims={"dev_mode": True},
                )
            else:
                raise AuthDisabledError("Authentication is disabled but allow_auth_disabled=False")

        if not request.has_credentials():
            if require_auth:
                raise MissingCredentialsError()
            return None

        last_error: AuthError | None = None
        for strategy in self._strategies:
            if not strategy.can_handle(request):
                continue
            try:
                result = await strategy.authenticate(request)
                if result:
                    logger.info(f"Authentication successful via {result.auth_method} for cliente: {result.client_id}")
                    return result
            except AuthError as e:
                last_error = e

        if last_error:
            raise last_error

        if require_auth:
            raise MissingCredentialsError("No valid credentials provided")

        return None
