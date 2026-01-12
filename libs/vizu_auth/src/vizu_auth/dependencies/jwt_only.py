"""
JWT-only authentication dependency that doesn't require client_id lookup.
Use this for endpoints that need to bootstrap user data (like /me).
"""

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from vizu_auth.core.exceptions import AuthError
from vizu_auth.core.jwt_decoder import decode_jwt
from vizu_auth.core.models import JWTClaims

bearer_scheme = HTTPBearer(auto_error=False)


async def get_jwt_claims(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> JWTClaims:
    """
    Validates JWT token and returns claims WITHOUT requiring client_id.

    Returns JWTClaims with:
    - sub: Supabase user ID (external_user_id)
    - email: User email
    - Other JWT claims

    Raises AuthError if token is invalid or missing.
    """
    if not credentials:
        raise AuthError("Missing Authorization header", code="MISSING_TOKEN")

    token = credentials.credentials
    claims = decode_jwt(token)  # This validates signature, expiry, etc.

    return claims
