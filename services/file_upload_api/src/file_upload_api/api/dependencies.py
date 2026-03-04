"""Authentication dependencies for file_upload_api."""

import logging
import uuid

from fastapi import HTTPException, Request, status

from vizu_auth import (
    AuthError,
    InvalidTokenError,
    TokenExpiredError,
    extract_client_id_from_jwt,
)

logger = logging.getLogger(__name__)


async def get_client_id_from_token(request: Request) -> uuid.UUID:
    """Extract client_id from JWT Bearer token.

    Reads the Authorization header, decodes the JWT using vizu_auth,
    and returns the client_id claim as a UUID.

    Args:
        request: The incoming FastAPI request.

    Returns:
        The authenticated client's UUID.

    Raises:
        HTTPException: 401 if token is missing/invalid/expired.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header. Expected: Bearer <token>",
        )

    token = auth_header.split(" ", 1)[1]

    try:
        client_id = extract_client_id_from_jwt(token)
    except (TokenExpiredError, InvalidTokenError, AuthError) as e:
        logger.warning(f"JWT authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {e}",
        )

    if client_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token does not contain a valid client_id claim.",
        )

    logger.debug(f"Authenticated client_id: {client_id}")
    return client_id
