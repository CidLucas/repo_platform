"""
Pytest fixtures for vizu_auth tests.
"""

import os
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import jwt
import pytest

# Configure env before importing vizu_auth modules in tests
TEST_JWT_SECRET = "test-secret-key-must-be-at-least-32-characters-long!"
os.environ["SUPABASE_JWT_SECRET"] = TEST_JWT_SECRET
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_AUDIENCE"] = "authenticated"
os.environ["AUTH_ENABLED"] = "true"

from vizu_auth.core.config import clear_auth_settings_cache


@pytest.fixture(autouse=True)
def reset_settings():
    clear_auth_settings_cache()
    yield
    clear_auth_settings_cache()


@pytest.fixture
def jwt_secret() -> str:
    return TEST_JWT_SECRET


@pytest.fixture
def sample_client_id():
    return uuid4()


@pytest.fixture
def sample_external_user_id() -> str:
    return f"supabase-user-{uuid4()}"


@pytest.fixture
def valid_jwt_payload(sample_external_user_id: str, sample_client_id) -> dict[str, Any]:
    now = datetime.now(UTC)
    return {
        "sub": sample_external_user_id,
        "email": "test@example.com",
        "role": "authenticated",
        "aud": "authenticated",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "client_id": str(sample_client_id),
    }


@pytest.fixture
def valid_jwt_token(jwt_secret: str, valid_jwt_payload: dict[str, Any]) -> str:
    return jwt.encode(valid_jwt_payload, jwt_secret, algorithm="HS256")


@pytest.fixture
def jwt_without_cliente_id(jwt_secret: str, sample_external_user_id: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": sample_external_user_id,
        "email": "test@example.com",
        "aud": "authenticated",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    return jwt.encode(payload, jwt_secret, algorithm="HS256")


@pytest.fixture
def expired_jwt_token(jwt_secret: str, sample_external_user_id: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": sample_external_user_id,
        "aud": "authenticated",
        "iat": int((now - timedelta(hours=2)).timestamp()),
        "exp": int((now - timedelta(hours=1)).timestamp()),
    }
    return jwt.encode(payload, jwt_secret, algorithm="HS256")


@pytest.fixture
def invalid_signature_token(valid_jwt_payload: dict[str, Any]) -> str:
    return jwt.encode(valid_jwt_payload, "wrong-secret-32-chars-long-xxxxx", algorithm="HS256")


@pytest.fixture
def sample_api_key() -> str:
    return f"vizu_key_{uuid4().hex}"
