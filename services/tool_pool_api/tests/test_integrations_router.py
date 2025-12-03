import asyncio
import uuid
from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tool_pool_api.api import integrations_router


class FakeCacheClient:
    def __init__(self):
        self.store = {}

    def setex(self, name, time, value):
        self.store[name] = value

    def get(self, name):
        return self.store.get(name)

    def delete(self, name):
        self.store.pop(name, None)


class FakeContext:
    def __init__(self):
        self.cache = type("c", (), {"client": FakeCacheClient()})()
        self.saved_config = None
        self.saved_tokens = None

    async def save_integration_config(self, cliente_vizu_id, provider, config_type, client_id, client_secret, redirect_uri, scopes):
        self.saved_config = {
            "cliente_vizu_id": cliente_vizu_id,
            "provider": provider,
            "config_type": config_type,
            "client_id_encrypted": f"enc:{client_id}",
            "client_secret_encrypted": f"enc:{client_secret}",
            "redirect_uri": redirect_uri,
            "scopes": scopes,
        }
        return self.saved_config

    async def get_integration_config(self, cliente_vizu_id, provider):
        return self.saved_config

    async def save_integration_tokens(self, cliente_vizu_id, provider, access_token, refresh_token, token_type, expires_at, scopes, metadata):
        self.saved_tokens = {
            "access_token_encrypted": f"enc:{access_token}",
            "refresh_token_encrypted": f"enc:{refresh_token}",
            "token_type": token_type,
            "expires_at": expires_at,
            "scopes": scopes,
            "metadata": metadata,
        }
        return self.saved_tokens

    async def get_integration_tokens(self, cliente_vizu_id, provider, auto_refresh=True):
        if not self.saved_tokens:
            return None

        class Wrapper:
            def __init__(self, row):
                self._row = row

            def is_valid(self):
                exp = self._row.get("expires_at")
                if not exp:
                    return True
                return exp > datetime.utcnow()

            def get_decrypted_tokens(self):
                return {
                    "access_token": self._row.get("access_token_encrypted").replace("enc:", ""),
                    "refresh_token": self._row.get("refresh_token_encrypted").replace("enc:", ""),
                    "token_type": self._row.get("token_type"),
                    "expires_at": self._row.get("expires_at"),
                    "scopes": self._row.get("scopes"),
                    "metadata": self._row.get("metadata"),
                }

        return Wrapper(self.saved_tokens)

    async def revoke_integration(self, cliente_vizu_id, provider):
        self.saved_config = None
        self.saved_tokens = None
        return True

    def _decrypt(self, v):
        # simple passthrough for tests where we stored enc:... values
        if not v:
            return v
        return v.replace("enc:", "")


class FakeAuthResult:
    def __init__(self, cliente_vizu_id):
        self.cliente_vizu_id = cliente_vizu_id


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(integrations_router.router)
    return app


@pytest.fixture
def client(app, monkeypatch):
    fake_ctx = FakeContext()

    async def fake_get_ctx():
        return fake_ctx

    async def fake_auth_result(*args, **kwargs):
        return FakeAuthResult(cliente_vizu_id=uuid.uuid4())

    # Patch the dependency used in the router
    monkeypatch.setattr(integrations_router, "get_context_service", lambda: fake_ctx)
    monkeypatch.setattr(integrations_router, "_get_auth_result", lambda *a, **k: FakeAuthResult(cliente_vizu_id=uuid.uuid4()))

    # Patch OAuthManager methods to avoid external calls
    from vizu_auth.oauth2.oauth_manager import OAuthManager

    async def fake_get_authorization_url(self, config, state):
        return f"https://auth.example/?state={state}"

    async def fake_exchange_code(self, config, code):
        return type("T", (), {"access_token": "access_mock", "refresh_token": "refresh_mock", "expires_in": 3600, "token_type": "Bearer", "scope": "s1 s2"})()

    monkeypatch.setattr(OAuthManager, "get_authorization_url", fake_get_authorization_url)
    monkeypatch.setattr(OAuthManager, "exchange_code", fake_exchange_code)

    return TestClient(app)


def test_configure_and_status(client):
    # Configure integration
    resp = client.post("/integrations/google/config", json={"client_id": "cid", "client_secret": "csecret"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "configured"


def test_initiate_and_callback_flow(client):
    # Initiate auth
    resp = client.post("/integrations/google/auth/initiate")
    assert resp.status_code == 200
    body = resp.json()
    assert "auth_url" in body and "state" in body

    state = body["state"]
    # Simulate callback with code
    resp2 = client.get(f"/integrations/google/callback?code=testcode&state={state}")
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2.get("status") == "ok"
