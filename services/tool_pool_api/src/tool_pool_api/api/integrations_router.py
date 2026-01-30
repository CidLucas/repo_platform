import asyncio
import logging
import secrets
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from tool_pool_api.core.config import get_settings
from tool_pool_api.server.dependencies import get_context_service

from vizu_auth.core.exceptions import (
    AuthError,
    InvalidTokenError,
    TokenExpiredError,
)
from vizu_auth.core.jwt_decoder import decode_jwt
from vizu_auth.core.models import AuthMethod, AuthResult
from vizu_auth.oauth2.models import OAuthConfig
from vizu_auth.oauth2.oauth_manager import OAuthManager
from vizu_context_service.context_service import ContextService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["Integrations"])


def _extract_oauth_config(
    cfg_row, context: ContextService
) -> tuple[str, str, str, list[str]]:
    """
    Extract and decrypt OAuth config from database row.

    Args:
        cfg_row: Database row (dict or object)
        context: ContextService for decryption

    Returns:
        Tuple of (client_id, client_secret, redirect_uri, scopes)

    Raises:
        HTTPException: If extraction or decryption fails
    """

    def _get(key: str):
        return cfg_row.get(key) if isinstance(cfg_row, dict) else getattr(cfg_row, key)

    try:
        client_id = context._decrypt(_get("client_id_encrypted"))
        client_secret = context._decrypt(_get("client_secret_encrypted"))
        redirect_uri = _get("redirect_uri")
        scopes = _get("scopes")
        return client_id, client_secret, redirect_uri, scopes
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to read integration config: {e}"
        )

bearer_scheme = HTTPBearer(auto_error=False)


class GoogleClientConfig(BaseModel):
    client_id: str
    client_secret: str


class SetDefaultAccountRequest(BaseModel):
    account_email: str


class RevokeAccountRequest(BaseModel):
    account_email: str | None = None  # If None, revokes all accounts


class GoogleAccountInfo(BaseModel):
    id: str
    account_email: str
    account_name: str | None
    is_default: bool
    expires_at: datetime | None = None
    scopes: list[str] | None = None
    created_at: datetime | None = None


async def _get_auth_result(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthResult:
    """JWT-only authentication for integrations API."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = decode_jwt(credentials.credentials)

        try:
            client_id = UUID(claims.sub)
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid UUID in JWT sub claim: {claims.sub}, error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user ID format in token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return AuthResult(
            client_id=client_id,
            auth_method=AuthMethod.JWT,
            external_user_id=claims.sub,
            email=claims.email,
            raw_claims=claims.model_dump(exclude_none=True),
        )

    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please refresh your authentication.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except AuthError as e:
        logger.error(f"Auth error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed.",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/google/config")
async def configure_google_integration(
    payload: GoogleClientConfig | None = Body(None),
    client_id: str | None = Query(None),
    client_secret: str | None = Query(None),
    auth: AuthResult = Depends(_get_auth_result),
    context: ContextService = Depends(get_context_service),
):
    settings = get_settings()
    # Allow either JSON body (preferred) or legacy query params
    final_client_id = payload.client_id if payload else client_id
    final_client_secret = payload.client_secret if payload else client_secret

    if not final_client_id or not final_client_secret:
        raise HTTPException(
            status_code=400, detail="client_id and client_secret are required"
        )

    # Persist encrypted config via ContextService
    await context.save_integration_config(
        client_id=auth.client_id,
        provider="google",
        config_type="oauth2_client",
        oauth_client_id=final_client_id,
        client_secret=final_client_secret,
        redirect_uri=f"{settings.MCP_AUTH_BASE_URL}/integrations/google/callback",
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/calendar.events",
            "openid",
            "email",
            "profile",
        ],
    )

    return {"status": "configured", "provider": "google"}


@router.post("/google/auth/initiate")
async def initiate_google_auth(
    auth: AuthResult = Depends(_get_auth_result),
    context: ContextService = Depends(get_context_service),
):
    # Retrieve saved config
    cfg_row = await context.get_integration_config(auth.client_id, "google")
    if not cfg_row:
        raise HTTPException(status_code=400, detail="Google integration not configured")

    client_id, client_secret, redirect_uri, scopes = _extract_oauth_config(cfg_row, context)

    oauth_config = OAuthConfig(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scopes=scopes,
    )

    state = secrets.token_urlsafe(32)

    # Save state in redis (use low-level client for simple string)
    await asyncio.to_thread(
        context.cache.client.setex,
        f"oauth_state:{state}",
        300,
        str(auth.client_id),
    )

    manager = OAuthManager("google")
    auth_url = await manager.get_authorization_url(oauth_config, state=state)

    return {"auth_url": auth_url, "state": state, "expires_in": 300}


@router.get("/google/callback")
async def google_auth_callback(
    code: str = Query(...),
    state: str = Query(...),
    context: ContextService = Depends(get_context_service),
):
    # Validate state
    client_id_str = await asyncio.to_thread(
        context.cache.client.get, f"oauth_state:{state}"
    )
    if not client_id_str:
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    client_id = UUID(
        client_id_str.decode()
        if isinstance(client_id_str, bytes)
        else client_id_str
    )

    # Remove state
    await asyncio.to_thread(context.cache.client.delete, f"oauth_state:{state}")

    # Load integration config
    cfg_row = await context.get_integration_config(client_id, "google")
    if not cfg_row:
        raise HTTPException(status_code=400, detail="Google integration not configured")

    oauth_client_id, client_secret, redirect_uri, scopes = _extract_oauth_config(cfg_row, context)

    oauth_config = OAuthConfig(
        client_id=oauth_client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scopes=scopes,
    )

    manager = OAuthManager("google")
    tokens = await manager.exchange_code(oauth_config, code)

    expires_at = None
    if tokens.expires_in:
        expires_at = datetime.utcnow() + timedelta(seconds=tokens.expires_in)

    # Get user info to determine account email
    account_email = None
    account_name = None
    try:
        import httpx

        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {tokens.access_token}"},
            )
            if resp.status_code == 200:
                user_info = resp.json()
                account_email = user_info.get("email")
                account_name = (
                    user_info.get("name") or user_info.get("email", "").split("@")[0]
                )
    except Exception as e:
        # If we can't get user info, use a fallback
        logger.warning(f"Failed to get Google user info: {e}")
        account_email = f"account_{secrets.token_hex(4)}@unknown.com"
        account_name = "Google Account"

    # Check if this is the first account (make it default)
    existing_accounts = await context.list_integration_accounts(
        client_id, "google"
    )
    is_default = len(existing_accounts) == 0

    # Persist tokens with account info
    await context.save_integration_tokens(
        client_id=client_id,
        provider="google",
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_at=expires_at,
        scopes=(tokens.scope.split() if tokens.scope else scopes),
        metadata=None,
        account_email=account_email,
        account_name=account_name,
        is_default=is_default,
    )

    # Return success - in a real app this would redirect to frontend
    return {
        "status": "ok",
        "message": "Google integration connected successfully!",
        "provider": "google",
        "account_email": account_email,
        "account_name": account_name,
        "is_default": is_default,
    }


@router.get("/google/accounts", response_model=list[GoogleAccountInfo])
async def list_google_accounts(
    auth: AuthResult = Depends(_get_auth_result),
    context: ContextService = Depends(get_context_service),
):
    """List all connected Google accounts for the authenticated cliente."""
    accounts = await context.list_integration_accounts(auth.client_id, "google")
    return accounts


@router.post("/google/accounts/default")
async def set_default_google_account(
    payload: SetDefaultAccountRequest,
    auth: AuthResult = Depends(_get_auth_result),
    context: ContextService = Depends(get_context_service),
):
    """Set a specific Google account as the default."""
    success = await context.set_default_account(
        auth.client_id, "google", payload.account_email
    )
    if not success:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"status": "ok", "default_account": payload.account_email}


@router.delete("/google/auth/revoke")
async def revoke_google_auth(
    payload: RevokeAccountRequest = Body(None),
    account_email: str | None = Query(None),
    auth: AuthResult = Depends(_get_auth_result),
    context: ContextService = Depends(get_context_service),
):
    """Revoke Google integration.

    If account_email is provided (via body or query), only that account is revoked.
    Otherwise, all accounts are revoked.
    """
    target_email = payload.account_email if payload else account_email

    if target_email:
        # Revoke specific account
        tokens = await context.get_integration_tokens(
            auth.client_id,
            "google",
            auto_refresh=False,
            account_email=target_email,
        )
        if tokens:
            try:
                manager = OAuthManager("google")
                await manager.revoke(tokens.get_decrypted_tokens()["access_token"])
            except Exception as e:
                logger.warning(f"Failed to revoke Google token: {e}")
        await context.revoke_integration(
            auth.client_id, "google", account_email=target_email
        )
        return {
            "status": "revoked",
            "provider": "google",
            "account_email": target_email,
        }
    else:
        # Revoke all accounts
        accounts = await context.list_integration_accounts(
            auth.client_id, "google"
        )
        for account in accounts:
            try:
                tokens = await context.get_integration_tokens(
                    auth.client_id,
                    "google",
                    auto_refresh=False,
                    account_email=account.get("account_email"),
                )
                if tokens:
                    manager = OAuthManager("google")
                    await manager.revoke(tokens.get_decrypted_tokens()["access_token"])
            except Exception as e:
                logger.warning(f"Failed to revoke Google token for account: {e}")
        await context.revoke_integration(auth.client_id, "google")
        return {"status": "revoked", "provider": "google", "all_accounts": True}


@router.get("/google/status")
async def get_google_status(
    account_email: str | None = Query(
        None, description="Specific account to check status for"
    ),
    auth: AuthResult = Depends(_get_auth_result),
    context: ContextService = Depends(get_context_service),
):
    """Get Google integration status.

    If account_email is provided, returns status for that specific account.
    Otherwise, returns overall status and list of all accounts.
    """
    config = await context.get_integration_config(auth.client_id, "google")

    if account_email:
        # Status for specific account
        tokens = await context.get_integration_tokens(
            auth.client_id,
            "google",
            auto_refresh=False,
            account_email=account_email,
        )
        return {
            "configured": config is not None,
            "connected": tokens is not None and tokens.is_valid() if tokens else False,
            "account_email": account_email,
            "expires_at": tokens._get("expires_at") if tokens else None,
            "is_expiring_soon": tokens.is_expiring_soon() if tokens else None,
        }
    else:
        # Overall status with all accounts
        accounts = await context.list_integration_accounts(
            auth.client_id, "google"
        )
        default_tokens = await context.get_integration_tokens(
            auth.client_id, "google", auto_refresh=False
        )

        return {
            "configured": config is not None,
            "connected": default_tokens is not None and default_tokens.is_valid()
            if default_tokens
            else False,
            "scopes": config.get("scopes")
            if isinstance(config, dict)
            else (getattr(config, "scopes", None) if config else []),
            "accounts": accounts,
            "default_account": default_tokens._get("account_email")
            if default_tokens
            else None,
            "expires_at": default_tokens._get("expires_at") if default_tokens else None,
        }
