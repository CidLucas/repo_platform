
from pydantic import BaseModel


class OAuthConfig(BaseModel):
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: list[str]


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None
    expires_in: int | None
    token_type: str | None
    scope: str | None
