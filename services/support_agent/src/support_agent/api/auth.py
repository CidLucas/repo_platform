"""
JWT-only authentication for support_agent using vizu_auth.

This module provides the `get_auth_result` dependency that validates
JWT tokens from Supabase and returns an AuthResult.
"""

import logging
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from vizu_auth.core.exceptions import (
    AuthError,
    InvalidTokenError,
    TokenExpiredError,
)
from vizu_auth.core.jwt_decoder import decode_jwt
from vizu_auth.core.models import AuthMethod, AuthResult

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


async def get_auth_result(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthResult:
    """
    JWT-only authentication dependency.

    Validates the Bearer token and returns an AuthResult with:
    - client_id: UUID from JWT (Supabase user ID)
    - auth_method: JWT
    - external_user_id: Supabase user ID (sub claim)
    - email: User email from JWT

    Raises HTTPException 401 if token is missing or invalid.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = decode_jwt(credentials.credentials)

        # Use Supabase user ID (sub) as client_id
        try:
            client_id = UUID(claims.sub)
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid UUID in JWT sub claim: {claims.sub}, error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user ID format in token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.info(f"JWT auth successful for user: {claims.sub}")

        return AuthResult(
            client_id=client_id,
            auth_method=AuthMethod.JWT,
            external_user_id=claims.sub,
            email=claims.email,
            raw_claims=claims.model_dump(exclude_none=True),
        )

    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please refresh your authentication.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except AuthError as e:
        logger.error(f"Auth error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed.",
            headers={"WWW-Authenticate": "Bearer"},
        )
