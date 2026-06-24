import logging

logger = logging.getLogger(__name__)
#!/usr/bin/env python3
import asyncio
import os
import uuid
from datetime import datetime, timedelta

from cryptography.fernet import Fernet
from redis import Redis

from blu_auth.oauth2.models import TokenResponse
from blu_context_service.context_service import ContextService
from blu_context_service.redis_service import RedisService
from blu_supabase_client import get_supabase_client


async def main():
    key = os.environ.get("CREDENTIALS_ENCRYPTION_KEY")
    if not key:
        key = Fernet.generate_key().decode()
        os.environ["CREDENTIALS_ENCRYPTION_KEY"] = key
    logger.info("Using CREDENTIALS_ENCRYPTION_KEY (len):", len(key))

    redis_client = Redis(host="redis", port=6379, db=0, decode_responses=False)
    cache = RedisService(redis_client)
    ctx = ContextService(cache_service=cache)

    # Pick an existing client_id from clientes_blu via Supabase
    supabase = get_supabase_client()
    row = supabase.table("clientes_blu").select("client_id").limit(1).execute()
    if not row.data:
        logger.info("No existing clientes_blu found. Please seed a client first.")
        return

    client_id = uuid.UUID(row.data[0]["client_id"])
    logger.info("Using existing client_id:", client_id)

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/gmail.readonly",
        "openid",
        "email",
    ]

    await ctx.save_integration_config(
        client_id=client_id,
        provider="google",
        config_type="oauth2_client",
        oauth_client_id="test-client-id",
        client_secret="test-client-secret",
        redirect_uri="http://localhost/integrations/google/callback",
        scopes=scopes,
    )
    logger.info("Saved integration config")

    tokens = TokenResponse(
        access_token="access_test_123",
        refresh_token="refresh_test_456",
        expires_in=3600,
        token_type="Bearer",
        scope=" ".join(scopes),
    )

    expires_at = datetime.utcnow() + timedelta(seconds=tokens.expires_in or 0)

    await ctx.save_integration_tokens(
        client_id=client_id,
        provider="google",
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_at=expires_at,
        scopes=scopes,
        metadata={"test": True},
    )
    logger.info("Saved integration tokens")

    wrapper = await ctx.get_integration_tokens(client_id, "google", auto_refresh=False)
    if not wrapper:
        logger.error("ERROR: tokens not found")
        return

    logger.info("Token is_valid():", wrapper.is_valid())
    dec = wrapper.get_decrypted_tokens()
    logger.info(        "Decrypted tokens:",
        {
            k: (v if k not in ["access_token", "refresh_token"] else str(v)[:20])
            for k, v in dec.items()
        })


if __name__ == "__main__":
    asyncio.run(main())

