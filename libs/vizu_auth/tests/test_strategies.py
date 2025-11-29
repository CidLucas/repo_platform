import asyncio
from uuid import UUID, uuid4

import pytest

from vizu_auth.core.exceptions import ClientNotFoundError, InvalidApiKeyError
from vizu_auth.core.models import AuthRequest
from vizu_auth.strategies.api_key_strategy import ApiKeyStrategy
from vizu_auth.strategies.authenticator import Authenticator
from vizu_auth.strategies.jwt_strategy import JWTStrategy


class TestJWTStrategy:
    @pytest.fixture
    def jwt_strategy(self):
        return JWTStrategy()

    def test_can_handle_with_jwt(self, jwt_strategy):
        request = AuthRequest(jwt_token="some.token.here")
        assert jwt_strategy.can_handle(request) is True

    def test_can_handle_without_jwt(self, jwt_strategy):
        request = AuthRequest(api_key="some-key")
        assert jwt_strategy.can_handle(request) is False

    @pytest.mark.asyncio
    async def test_authenticate_with_valid_token(self, valid_jwt_token, sample_cliente_vizu_id):
        strategy = JWTStrategy()
        request = AuthRequest(jwt_token=valid_jwt_token)
        result = await strategy.authenticate(request)
        assert result is not None
        assert isinstance(result.cliente_vizu_id, UUID)


class TestApiKeyStrategy:
    @pytest.mark.asyncio
    async def test_constructor_requires_lookup(self):
        with pytest.raises(ValueError):
            ApiKeyStrategy(api_key_lookup_fn=None)  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_authenticate_success_and_failure(self, sample_api_key):
        async def lookup_ok(key: str):
            return uuid4()

        async def lookup_none(key: str):
            return None

        strategy = ApiKeyStrategy(api_key_lookup_fn=lookup_ok)
        request = AuthRequest(api_key=sample_api_key)
        result = await strategy.authenticate(request)
        assert result is not None

        strategy_bad = ApiKeyStrategy(api_key_lookup_fn=lookup_none)
        with pytest.raises(InvalidApiKeyError):
            await strategy_bad.authenticate(request)


class TestAuthenticator:
    @pytest.mark.asyncio
    async def test_authenticator_prefers_jwt(self, valid_jwt_token, sample_api_key):
        # jwt strategy that will succeed
        jwt_strategy = JWTStrategy()

        # api key strategy that would also work
        async def lookup_ok(key: str):
            return uuid4()

        api_strategy = ApiKeyStrategy(api_key_lookup_fn=lookup_ok)

        auth = Authenticator(strategies=[jwt_strategy, api_strategy], allow_auth_disabled=False)

        # Request with JWT should be handled by JWTStrategy
        request = AuthRequest(jwt_token=valid_jwt_token, api_key=sample_api_key)
        result = await auth.authenticate(request)
        assert result is not None

    @pytest.mark.asyncio
    async def test_missing_credentials_raises(self):
        auth = Authenticator(strategies=[], allow_auth_disabled=False)
        with pytest.raises(Exception):
            await auth.authenticate(AuthRequest())
