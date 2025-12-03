from abc import ABC
from datetime import datetime, timedelta
from typing import Optional, Callable, Awaitable
import asyncio

try:
    # Import Google auth libraries lazily to avoid hard dependency at import time
    from google.oauth2.credentials import Credentials as GoogleCredentials  # type: ignore
    from google.auth.transport.requests import Request  # type: ignore
except Exception:
    GoogleCredentials = None  # type: ignore
    Request = None  # type: ignore


class BaseGoogleClient(ABC):
    """Base client for Google APIs with token storage and optional refresh callback.

    This implementation avoids importing Google-specific libraries at module import time
    so the package can be used in environments where `google-auth` is not installed.
    """

    def __init__(
        self,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        token_refresh_callback: Optional[Callable[[str, Optional[str]], Awaitable[None]]] = None,
    ) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_at = expires_at or (datetime.utcnow() + timedelta(hours=1))
        self.token_refresh_callback = token_refresh_callback
        self._credentials = None

    def _is_expired(self) -> bool:
        if not self.expires_at:
            return True
        return datetime.utcnow() >= self.expires_at

    def _get_credentials(self):
        """Return google Credentials object, refreshing if necessary.

        This method imports Google libs lazily and will raise an informative
        ImportError if the `google-auth` libraries are missing.
        """
        if GoogleCredentials is None:
            raise ImportError("google-auth not installed. Install google-auth to use Google clients.")

        if self._credentials is None:
            self._credentials = GoogleCredentials(
                token=self.access_token,
                refresh_token=self.refresh_token,
            )

        if getattr(self._credentials, "expired", False) and getattr(self._credentials, "refresh_token", None):
            if Request is None:
                raise ImportError("google-auth transport not available; cannot refresh token")
            self._credentials.refresh(Request())
            # persist refreshed token asynchronously if callback provided
            if self.token_refresh_callback:
                try:
                    asyncio.create_task(self.token_refresh_callback(self._credentials.token, getattr(self._credentials, "refresh_token", None)))
                except RuntimeError:
                    # No running event loop; ignore scheduling
                    pass

        return self._credentials

    def get_access_token(self) -> str:
        """Return current access token (may raise if google libs missing)."""
        if self._is_expired():
            # attempt refresh via credentials if available
            self._get_credentials()

        return getattr(self._credentials, "token", self.access_token)
