"""
Decodificador e validador de tokens JWT para vizu_auth.
"""

import logging
from uuid import UUID

import jwt

from vizu_auth.core.config import get_auth_settings
from vizu_auth.core.exceptions import (
    AuthError,
    InvalidSignatureError,
    InvalidTokenError,
    TokenExpiredError,
)
from vizu_auth.core.models import JWTClaims

logger = logging.getLogger(__name__)


def decode_jwt(
    token: str,
    *,
    verify_exp: bool = True,
    verify_aud: bool = True,
) -> JWTClaims:
    settings = get_auth_settings()

    if not settings.has_jwt_secret:
        logger.error("JWT secret not configured")
        raise AuthError(
            "JWT authentication not configured. Set SUPABASE_JWT_SECRET.",
            code="CONFIG_ERROR",
        )

    if token.lower().startswith("bearer "):
        token = token[7:]

    token = token.strip()

    if not token:
        raise InvalidTokenError("Empty token provided")

    options = {
        "verify_exp": verify_exp,
        "verify_aud": verify_aud and bool(settings.jwt_audience),
        "verify_signature": True,
    }

    audience = settings.jwt_audience if verify_aud else None

    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience=audience,
            options=options,
        )

        cliente_id_claim = settings.jwt_cliente_vizu_id_claim
        if cliente_id_claim in payload:
            raw_id = payload[cliente_id_claim]
            try:
                payload[cliente_id_claim] = UUID(str(raw_id))
            except (ValueError, TypeError):
                logger.warning(f"Invalid cliente_vizu_id in token: {raw_id}")
                payload[cliente_id_claim] = None

        logger.debug(f"JWT decoded successfully for sub: {payload.get('sub', 'unknown')}")
        return JWTClaims(**payload)

    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        raise TokenExpiredError()

    except jwt.InvalidSignatureError:
        logger.warning("JWT signature verification failed")
        raise InvalidSignatureError()

    except jwt.InvalidAudienceError as e:
        logger.warning(f"JWT audience invalid: {e}")
        raise InvalidTokenError(f"Invalid token audience: {e}")

    except jwt.DecodeError as e:
        logger.warning(f"JWT decode error: {e}")
        raise InvalidTokenError(f"Failed to decode token: {e}")

    except jwt.InvalidTokenError as e:
        logger.warning(f"JWT invalid: {e}")
        raise InvalidTokenError(f"Invalid token: {e}")


def extract_cliente_vizu_id_from_jwt(token: str) -> UUID | None:
    try:
        claims = decode_jwt(token)
        return claims.cliente_vizu_id
    except AuthError:
        return None


def validate_jwt(token: str) -> bool:
    try:
        decode_jwt(token)
        return True
    except AuthError:
        return False
