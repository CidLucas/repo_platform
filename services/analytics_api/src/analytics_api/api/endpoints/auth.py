import os

from analytics_api.core.config import settings
from fastapi import APIRouter, Depends, HTTPException, Request, status

from vizu_auth.oauth2.models import OAuthConfig
from vizu_auth.oauth2.oauth_manager import OAuthManager

router = APIRouter()


def get_google_oauth_config() -> OAuthConfig:
    return OAuthConfig(
        client_id=os.environ.get("GOOGLE_CLIENT_ID", settings.GOOGLE_CLIENT_ID),
        client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", settings.GOOGLE_CLIENT_SECRET),
        redirect_uri=os.environ.get("GOOGLE_REDIRECT_URI", settings.GOOGLE_REDIRECT_URI),
        scopes=["openid", "email", "profile"],
    )


oauth_manager = OAuthManager("google")


@router.get("/auth/google/login", summary="Inicia login social Google", tags=["auth"])
async def google_login(request: Request):
    state = ""  # Você pode gerar um state seguro para CSRF
    config = get_google_oauth_config()
    url = await oauth_manager.get_authorization_url(config, state)
    return {"auth_url": url}


@router.get("/auth/google/callback", summary="Callback do Google OAuth", tags=["auth"])
async def google_callback(code: str, state: str = ""):
    config = get_google_oauth_config()
    try:
        token_response = await oauth_manager.exchange_code(config, code)
        # Aqui você pode buscar/criar usuário no Supabase e gerar sessão/JWT
        # Exemplo: user_info = ...
        return {
            "access_token": token_response.access_token,
            "refresh_token": token_response.refresh_token,
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
