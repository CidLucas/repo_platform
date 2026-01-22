#!/usr/bin/env python3
import asyncio
import os
import uuid
from datetime import datetime, timedelta

from cryptography.fernet import Fernet
from redis import Redis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from vizu_auth.oauth2.models import TokenResponse
from vizu_context_service.context_service import ContextService
from vizu_context_service.redis_service import RedisService


async def main():
    # Ensure we have an encryption key for this test run
    key = os.environ.get("CREDENTIALS_ENCRYPTION_KEY")
    if not key:
        key = Fernet.generate_key().decode()
        os.environ["CREDENTIALS_ENCRYPTION_KEY"] = key
    print("Using CREDENTIALS_ENCRYPTION_KEY (len):", len(key))

    # Redis client pointing to the compose service name
    redis_client = Redis(host="redis", port=6379, db=0, decode_responses=False)
    cache = RedisService(redis_client)

    # SQLAlchemy session to local Postgres (compose service)
    DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@postgres:5432/vizu_db")
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db_session = SessionLocal()

    # Instantiate ContextService using the SQLAlchemy backend
    ctx = ContextService(cache_service=cache, db_session=db_session, use_supabase=False)

    cliente_id = uuid.uuid4()
    print("Test client_id:", cliente_id)

    # Save a fake integration config
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/gmail.readonly",
        "openid",
        "email",
    ]
    client_id = "test-client-id"
    client_secret = "test-client-secret"
    redirect_uri = "http://localhost/integrations/google/callback"

    await ctx.save_integration_config(
        client_id=cliente_id,
        provider="google",
        config_type="oauth2_client",
        oauth_client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scopes=scopes,
    )
    print("Saved integration config")

    # Simulate OAuth token exchange (mocked)
    tokens = TokenResponse(
        access_token="access_test_123",
        refresh_token="refresh_test_456",
        expires_in=3600,
        token_type="Bearer",
        scope=" ".join(scopes),
    )

    expires_at = datetime.utcnow() + timedelta(seconds=tokens.expires_in or 0)

    await ctx.save_integration_tokens(
        client_id=cliente_id,
        provider="google",
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_at=expires_at,
        scopes=scopes,
        metadata={"test": True},
    )
    print("Saved integration tokens")

    # Retrieve persisted tokens and validate
    wrapper = await ctx.get_integration_tokens(cliente_id, "google", auto_refresh=False)
    if not wrapper:
        print("ERROR: tokens not found")
        return

    print("Token is_valid():", wrapper.is_valid())
    dec = wrapper.get_decrypted_tokens()
    print("Decrypted tokens:", {k: (v if k not in ["access_token", "refresh_token"] else str(v)[:20]) for k, v in dec.items()})


if __name__ == "__main__":
    asyncio.run(main())
