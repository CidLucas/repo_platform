import asyncio
from typing import Any

from .base import OAuth2Provider
from .models import OAuthConfig, TokenResponse


class GoogleOAuth2Provider(OAuth2Provider):
    """Google OAuth2 provider using `google-auth-oauthlib` lazily.

    Methods are async but internally call synchronous google functions;
    we keep the async API for compatibility with the rest of the codebase.
    """

    def _make_client_config(self, config: OAuthConfig) -> dict[str, Any]:
        return {
            "web": {
                "client_id": config.client_id,
                "client_secret": config.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [config.redirect_uri],
            }
        }

    async def get_authorization_url(self, config: OAuthConfig, state: str, **kwargs: Any) -> str:
        try:
            from google_auth_oauthlib.flow import Flow  # type: ignore
        except Exception:
            raise ImportError("google-auth-oauthlib is required to build the authorization URL")

        flow = Flow.from_client_config(self._make_client_config(config), scopes=config.scopes)
        flow.redirect_uri = config.redirect_uri

        # include prompt=consent to ensure refresh_token is returned for new grants
        auth_url, _ = flow.authorization_url(access_type="offline", include_granted_scopes="true", state=state, prompt="consent")
        return auth_url

    async def exchange_code_for_tokens(self, config: OAuthConfig, code: str, **kwargs: Any) -> TokenResponse:
        try:
            import os

            from google_auth_oauthlib.flow import Flow  # type: ignore
        except Exception:
            raise ImportError("google-auth-oauthlib is required to exchange code for tokens")

        # Disable oauthlib's scope change warning (Google returns equivalent scopes with different names)
        os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

        flow = Flow.from_client_config(self._make_client_config(config), scopes=config.scopes)
        flow.redirect_uri = config.redirect_uri
        # This call is synchronous; run in thread to avoid blocking if called from async loop
        def fetch():
            flow.fetch_token(code=code)
            creds = flow.credentials
            return TokenResponse(
                access_token=creds.token,
                refresh_token=getattr(creds, "refresh_token", None),
                expires_in=getattr(creds, "expiry", None) and 3600,
                token_type=getattr(creds, "token_type", None),
                scope=" ".join(getattr(creds, "scopes", []) or []),
            )

        return await asyncio.to_thread(fetch)

    async def refresh_access_token(self, config: OAuthConfig, refresh_token: str) -> TokenResponse:
        try:
            from google.auth.transport.requests import Request  # type: ignore
            from google.oauth2.credentials import Credentials  # type: ignore
        except Exception:
            raise ImportError("google-auth is required to refresh access tokens")

        def refresh():
            creds = Credentials(token=None, refresh_token=refresh_token, client_id=config.client_id, client_secret=config.client_secret, token_uri="https://oauth2.googleapis.com/token")
            creds.refresh(Request())
            return TokenResponse(
                access_token=creds.token,
                refresh_token=refresh_token,
                expires_in=3600,
                token_type=getattr(creds, "token_type", None),
                scope=None,
            )

        return await asyncio.to_thread(refresh)

    async def revoke_token(self, token: str) -> bool:
        try:
            import httpx
        except Exception:
            raise ImportError("httpx is required to revoke tokens")

        revoke_url = "https://oauth2.googleapis.com/revoke"
        async with httpx.AsyncClient() as client:
            resp = await client.post(revoke_url, params={"token": token}, headers={"content-type": "application/x-www-form-urlencoded"})
            return resp.status_code in (200, 204)
