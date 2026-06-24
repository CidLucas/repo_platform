"""OAuth2 provider interfaces and helpers for blu_auth.

This package provides an abstract `OAuth2Provider` and a Google
implementation (`GoogleOAuth2Provider`) plus a simple `OAuthManager`
that orchestrates authorization URL creation and token exchange.

Google libs are imported lazily so environments without google packages
can still import the package (they'll get informative ImportError when
trying to use provider methods that require google libs).
"""

from blu_auth.oauth2.base import OAuth2Provider
from blu_auth.oauth2.google_provider import GoogleOAuth2Provider
from blu_auth.oauth2.models import OAuthConfig, TokenResponse
from blu_auth.oauth2.oauth_manager import OAuthManager

__all__ = [
    "OAuthConfig",
    "TokenResponse",
    "OAuth2Provider",
    "GoogleOAuth2Provider",
    "OAuthManager",
]
