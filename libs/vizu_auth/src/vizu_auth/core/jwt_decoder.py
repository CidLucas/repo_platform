"""
Decodificador e validador de tokens JWT para vizu_auth.
"""

import json
import logging
from uuid import UUID

import jwt
from jwt.algorithms import ECAlgorithm, RSAAlgorithm

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
            "JWT authentication not configured. Set SUPABASE_JWT_SECRET or SUPABASE_JWT_JWK.",
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

    # Determine the key to use based on algorithm
    key = None
    algorithm = settings.jwt_algorithm

    if algorithm in ("ES256", "ES384", "ES512"):
        # Elliptic Curve - use JWK
        if not settings.supabase_jwt_jwk:
            raise AuthError("SUPABASE_JWT_JWK required for ES256/ES384/ES512", code="CONFIG_ERROR")
        try:
            jwk_data = json.loads(settings.supabase_jwt_jwk)
            key = ECAlgorithm.from_jwk(json.dumps(jwk_data))
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Failed to parse JWK: {e}")
            raise AuthError(f"Invalid JWK format: {e}", code="CONFIG_ERROR")

    elif algorithm in ("RS256", "RS384", "RS512"):
        # RSA - use JWK or PEM
        if settings.supabase_jwt_jwk:
            try:
                jwk_data = json.loads(settings.supabase_jwt_jwk)
                key = RSAAlgorithm.from_jwk(json.dumps(jwk_data))
            except (json.JSONDecodeError, Exception) as e:
                logger.error(f"Failed to parse RSA JWK: {e}")
                raise AuthError(f"Invalid RSA JWK format: {e}", code="CONFIG_ERROR")
        else:
            # Fallback to secret (PEM format)
            key = settings.supabase_jwt_secret

    else:
        # HS256/HS384/HS512 - use secret
        key = settings.supabase_jwt_secret

    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=[algorithm],
            audience=audience,
            options=options,
        )

        cliente_id_claim = settings.jwt_client_id_claim
        if cliente_id_claim in payload:
            raw_id = payload[cliente_id_claim]
            try:
                payload[cliente_id_claim] = UUID(str(raw_id))
            except (ValueError, TypeError):
                logger.warning(f"Invalid client_id in token: {raw_id}")
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


def extract_client_id_from_jwt(token: str) -> UUID | None:
    try:
        claims = decode_jwt(token)
        return claims.client_id
    except AuthError:
        return None


def validate_jwt(token: str) -> bool:
    try:
        decode_jwt(token)
        return True
    except AuthError:
        return False
