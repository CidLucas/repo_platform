from pydantic import BaseModel
from typing import List, Optional


class OAuthConfig(BaseModel):
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: List[str]


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str]
    expires_in: Optional[int]
    token_type: Optional[str]
    scope: Optional[str]
