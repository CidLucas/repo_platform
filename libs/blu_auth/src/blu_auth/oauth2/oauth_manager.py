
from .google_provider import GoogleOAuth2Provider
from .models import OAuthConfig, TokenResponse


class OAuthManager:
    """Small orchestrator that selects provider implementations.

    Currently only Google is supported; this class centralizes calls
    so callers can depend on a single manager instead of provider
    classes directly.
    """

    def __init__(self, provider_name: str = "google"):
        self.provider_name = provider_name
        if self.provider_name == "google":
            self._provider = GoogleOAuth2Provider()
        else:
            raise ValueError("Unsupported provider")

    async def get_authorization_url(self, config: OAuthConfig, state: str) -> str:
        return await self._provider.get_authorization_url(config, state)

    async def exchange_code(self, config: OAuthConfig, code: str) -> TokenResponse:
        return await self._provider.exchange_code_for_tokens(config, code)

    async def refresh(self, config: OAuthConfig, refresh_token: str) -> TokenResponse:
        return await self._provider.refresh_access_token(config, refresh_token)

    async def revoke(self, token: str) -> bool:
        return await self._provider.revoke_token(token)
