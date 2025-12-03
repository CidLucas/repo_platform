from abc import ABC, abstractmethod
from typing import Any

from ..oauth2.models import OAuthConfig, TokenResponse  # type: ignore


class OAuth2Provider(ABC):
    """Abstract interface for an OAuth2 provider implementation."""

    @abstractmethod
    async def get_authorization_url(self, config: OAuthConfig, state: str, **kwargs: Any) -> str:
        """Return an authorization URL that the user can visit to grant consent."""

    @abstractmethod
    async def exchange_code_for_tokens(self, config: OAuthConfig, code: str, **kwargs: Any) -> TokenResponse:
        """Exchange an authorization code for tokens."""

    @abstractmethod
    async def refresh_access_token(self, config: OAuthConfig, refresh_token: str) -> TokenResponse:
        """Refresh an access token using a refresh token."""

    @abstractmethod
    async def revoke_token(self, token: str) -> bool:
        """Revoke a token at the provider. Return True if revoked successfully."""
