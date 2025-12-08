"""
JWT token validation and claims extraction for MCP services.

Provides standardized token handling across all Vizu MCP services.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID

import jwt

from vizu_mcp_commons.exceptions import MCPAuthError

logger = logging.getLogger(__name__)


@dataclass
class TokenClaims:
    """Validated JWT token claims."""

    sub: str  # Subject (external user ID)
    email: Optional[str] = None
    name: Optional[str] = None
    cliente_id: Optional[UUID] = None  # Resolved Vizu client ID
    scopes: List[str] = field(default_factory=list)
    exp: Optional[datetime] = None
    iat: Optional[datetime] = None
    raw_claims: dict = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        if not self.exp:
            return False
        return datetime.now(timezone.utc) > self.exp

    @property
    def external_user_id(self) -> str:
        """Alias for sub - the external identity provider user ID."""
        return self.sub


class TokenValidator:
    """
    Validate JWT tokens and extract claims.

    Supports multiple algorithms and issuers for flexibility
    with different identity providers (Google, Auth0, custom).
    """

    def __init__(
        self,
        jwt_secret: Optional[str] = None,
        algorithms: Optional[List[str]] = None,
        verify_exp: bool = True,
        issuer: Optional[str] = None,
        audience: Optional[str] = None,
    ):
        """
        Initialize token validator.

        Args:
            jwt_secret: Secret key for HS256/HS384/HS512 algorithms
            algorithms: Allowed JWT algorithms (default: ["HS256"])
            verify_exp: Whether to verify token expiration
            issuer: Expected issuer (iss claim)
            audience: Expected audience (aud claim)
        """
        self.jwt_secret = jwt_secret
        self.algorithms = algorithms or ["HS256"]
        self.verify_exp = verify_exp
        self.issuer = issuer
        self.audience = audience

    def validate(self, token: str) -> TokenClaims:
        """
        Validate a JWT token and return claims.

        Args:
            token: JWT token string

        Returns:
            TokenClaims with validated data

        Raises:
            MCPAuthError: If token is invalid or expired
        """
        if not token:
            raise MCPAuthError("Token não fornecido")

        # Remove 'Bearer ' prefix if present
        if token.startswith("Bearer "):
            token = token[7:]

        try:
            options = {
                "verify_exp": self.verify_exp,
                "verify_iss": bool(self.issuer),
                "verify_aud": bool(self.audience),
            }

            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=self.algorithms,
                options=options,
                issuer=self.issuer,
                audience=self.audience,
            )

            return self._parse_claims(payload)

        except jwt.ExpiredSignatureError:
            logger.warning("Token expirado")
            raise MCPAuthError("Token expirado", code="TOKEN_EXPIRED")

        except jwt.InvalidSignatureError:
            logger.warning("Assinatura do token inválida")
            raise MCPAuthError("Token com assinatura inválida", code="INVALID_SIGNATURE")

        except jwt.InvalidTokenError as e:
            logger.warning(f"Token inválido: {e}")
            raise MCPAuthError(f"Token inválido: {e}", code="INVALID_TOKEN")

    def _parse_claims(self, payload: dict) -> TokenClaims:
        """Parse raw JWT payload into TokenClaims."""
        sub = payload.get("sub")
        if not sub:
            raise MCPAuthError("Token sem claim 'sub' (subject)", code="MISSING_SUB")

        # Parse exp/iat as datetime
        exp = None
        if "exp" in payload:
            exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

        iat = None
        if "iat" in payload:
            iat = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)

        # Parse scopes (can be space-separated string or list)
        scopes = payload.get("scope", payload.get("scopes", []))
        if isinstance(scopes, str):
            scopes = scopes.split()

        # Parse cliente_id if present
        cliente_id = None
        raw_cliente_id = payload.get("cliente_id") or payload.get("vizu_cliente_id")
        if raw_cliente_id:
            try:
                cliente_id = UUID(raw_cliente_id)
            except (ValueError, TypeError):
                logger.warning(f"cliente_id inválido no token: {raw_cliente_id}")

        return TokenClaims(
            sub=sub,
            email=payload.get("email"),
            name=payload.get("name"),
            cliente_id=cliente_id,
            scopes=scopes,
            exp=exp,
            iat=iat,
            raw_claims=payload,
        )

    def validate_without_verification(self, token: str) -> TokenClaims:
        """
        Decode token without signature verification.

        WARNING: Only use for debugging or when signature is verified elsewhere.

        Args:
            token: JWT token string

        Returns:
            TokenClaims (unverified)
        """
        if token.startswith("Bearer "):
            token = token[7:]

        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            return self._parse_claims(payload)
        except jwt.DecodeError as e:
            raise MCPAuthError(f"Token malformado: {e}", code="MALFORMED_TOKEN")


class MCPTokenExtractor:
    """
    Extract tokens from various MCP transport contexts.

    Supports:
    - FastMCP AccessToken context variable
    - HTTP Authorization header
    - Query parameter (for SSE fallback)
    """

    @staticmethod
    def extract_from_fastmcp_context() -> Optional[str]:
        """
        Extract token from FastMCP context variable.

        Returns:
            Token string if available, None otherwise
        """
        try:
            from fastmcp.server.dependencies import get_access_token
            access_token = get_access_token()
            if access_token:
                # FastMCP AccessToken stores raw token
                return getattr(access_token, "token", None)
        except Exception:
            pass
        return None

    @staticmethod
    def extract_claims_from_fastmcp_context() -> Optional[dict]:
        """
        Extract claims dict from FastMCP AccessToken.

        Returns:
            Claims dict if available, None otherwise
        """
        try:
            from fastmcp.server.dependencies import get_access_token
            access_token = get_access_token()
            if access_token and hasattr(access_token, "claims"):
                return access_token.claims
        except Exception:
            pass
        return None

    @staticmethod
    def extract_external_user_id() -> Optional[str]:
        """
        Extract external user ID from FastMCP context.

        Returns:
            External user ID (sub claim) if available
        """
        claims = MCPTokenExtractor.extract_claims_from_fastmcp_context()
        if claims:
            return claims.get("sub")
        return None

    @staticmethod
    def extract_email() -> Optional[str]:
        """
        Extract user email from FastMCP context.

        Returns:
            Email if available
        """
        claims = MCPTokenExtractor.extract_claims_from_fastmcp_context()
        if claims:
            return claims.get("email")
        return None
