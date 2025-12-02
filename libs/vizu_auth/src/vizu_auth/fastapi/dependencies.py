"""
FastAPI dependencies for vizu_auth.
"""

import logging
from typing import Callable, Optional, Awaitable
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from vizu_auth.core.exceptions import (
    AuthDisabledError,
    AuthError,
    ClientNotFoundError,
    InvalidApiKeyError,
    InvalidTokenError,
    MissingCredentialsError,
    TokenExpiredError,
)
from vizu_auth.core.models import AuthRequest, AuthResult
from vizu_auth.strategies.api_key_strategy import ApiKeyStrategy
from vizu_auth.strategies.authenticator import Authenticator
from vizu_auth.strategies.jwt_strategy import JWTStrategy

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)

# Type aliases
ApiKeyLookupFn = Callable[[str], Awaitable[Optional[UUID]]]
ExternalUserLookupFn = Callable[[str], Awaitable[Optional[UUID]]]


class AuthDependencyFactory:
    def __init__(
        self,
        api_key_lookup_fn: ApiKeyLookupFn,
        external_user_lookup_fn: Optional[ExternalUserLookupFn] = None,
        *,
        allow_auth_disabled: bool = False,
    ):
        self._api_key_lookup_fn = api_key_lookup_fn
        self._external_user_lookup_fn = external_user_lookup_fn
        self._allow_auth_disabled = allow_auth_disabled

        self._jwt_strategy = JWTStrategy(cliente_lookup_fn=external_user_lookup_fn)
        self._api_key_strategy = ApiKeyStrategy(api_key_lookup_fn=api_key_lookup_fn)

        self._authenticator = Authenticator(
            strategies=[self._jwt_strategy, self._api_key_strategy],
            allow_auth_disabled=allow_auth_disabled,
        )

    async def get_auth_result(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
        x_api_key: Optional[str] = Header(None, alias="X-API-KEY"),
    ) -> AuthResult:
        auth_request = AuthRequest(
            jwt_token=credentials.credentials if credentials else None,
            api_key=x_api_key,
        )

        try:
            result = await self._authenticator.authenticate(auth_request)
            if not result:
                raise MissingCredentialsError()
            return result

        except MissingCredentialsError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required. Provide Bearer token or X-API-KEY.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except TokenExpiredError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired. Please refresh your authentication.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except (InvalidTokenError, InvalidApiKeyError) as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"},
            )
        except ClientNotFoundError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        except AuthDisabledError:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Authentication service is disabled.")
        except AuthError as e:
            logger.error(f"Unexpected auth error: {e}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed.")

    async def get_optional_auth_result(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
        x_api_key: Optional[str] = Header(None, alias="X-API-KEY"),
    ) -> Optional[AuthResult]:
        auth_request = AuthRequest(
            jwt_token=credentials.credentials if credentials else None,
            api_key=x_api_key,
        )
        try:
            return await self._authenticator.authenticate(auth_request, require_auth=False)
        except AuthError:
            logger.debug("Optional auth failed")
            return None


def create_auth_dependency(api_key_lookup_fn: ApiKeyLookupFn, external_user_lookup_fn: Optional[ExternalUserLookupFn] = None, *, allow_auth_disabled: bool = False) -> AuthDependencyFactory:
    return AuthDependencyFactory(
        api_key_lookup_fn=api_key_lookup_fn,
        external_user_lookup_fn=external_user_lookup_fn,
        allow_auth_disabled=allow_auth_disabled,
    )
