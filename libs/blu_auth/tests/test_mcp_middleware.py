from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from blu_auth.mcp.auth_middleware import mcp_inject_client_id


@pytest.mark.asyncio
async def test_middleware_injects_client_id_when_token_and_mapping_present():
    # Arrange
    mock_ctx_service = MagicMock()

    access_token = SimpleNamespace(claims={"sub": "external-123"})

    async def lookup_fn(external_id: str):
        assert external_id == "external-123"
        return "client-abc"

    # Tool to decorate
    async def tool(ctx, client_id: str | None = None):
        return client_id

    decorator = mcp_inject_client_id(lambda: mock_ctx_service)

    # Patch get_access_token and the adapter lookup used inside the middleware
    with patch("blu_auth.mcp.auth_middleware.get_access_token", return_value=access_token), \
         patch("blu_auth.mcp.auth_middleware.external_user_lookup_from_context_service", return_value=lookup_fn):

        decorated = decorator(tool)

        # Act
        result = await decorated(None)

        # Assert
        assert result == "client-abc"


@pytest.mark.asyncio
async def test_middleware_leaves_kwargs_when_token_but_no_mapping():
    mock_ctx_service = MagicMock()
    access_token = SimpleNamespace(claims={"sub": "external-999"})

    async def lookup_none(external_id: str):
        return None

    async def tool(ctx, client_id: str | None = None):
        return client_id

    decorator = mcp_inject_client_id(lambda: mock_ctx_service)

    with patch("blu_auth.mcp.auth_middleware.get_access_token", return_value=access_token), \
         patch("blu_auth.mcp.auth_middleware.external_user_lookup_from_context_service", return_value=lookup_none):

        decorated = decorator(tool)
        result = await decorated(None)
        assert result is None


@pytest.mark.asyncio
async def test_middleware_preserves_provided_client_id_when_no_token():
    mock_ctx_service = MagicMock()

    async def tool(ctx, client_id: str | None = None):
        return client_id

    decorator = mcp_inject_client_id(lambda: mock_ctx_service)

    # Simulate get_access_token raising (no token in context)
    with patch("blu_auth.mcp.auth_middleware.get_access_token", side_effect=Exception("no token")):
        decorated = decorator(tool)
        result = await decorated(None, client_id="provided-1")
        assert result == "provided-1"
