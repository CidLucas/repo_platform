"""OAuth2 provider interfaces and helpers for vizu_auth.

This package provides an abstract `OAuth2Provider` and a Google
implementation (`GoogleOAuth2Provider`) plus a simple `OAuthManager`
that orchestrates authorization URL creation and token exchange.

Google libs are imported lazily so environments without google packages
can still import the package (they'll get informative ImportError when
trying to use provider methods that require google libs).
"""

from .base import OAuth2Provider
from .google_provider import GoogleOAuth2Provider
from .models import OAuthConfig, TokenResponse
from .oauth_manager import OAuthManager

__all__ = [
    "OAuthConfig",
    "TokenResponse",
    "OAuth2Provider",
    "GoogleOAuth2Provider",
    "OAuthManager",
]
