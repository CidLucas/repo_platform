import asyncio
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from blu_context_service.context_service import ContextService
from blu_context_service.redis_service import RedisService
from blu_models.blu_client_context import BluClientContext


def _make_service(mocker) -> ContextService:
    mock_redis = mocker.MagicMock(spec=RedisService)
    # Patch SupabaseCRUD construction so no real Supabase client is needed
    mocker.patch("blu_context_service.context_service.SupabaseCRUD")
    mocker.patch("blu_context_service.context_service.get_supabase_client")
    mocker.patch("blu_context_service.context_service.supabase_set_rls")
    return ContextService(cache_service=mock_redis), mock_redis


def test_get_client_context_cache_hit(mocker, mock_cliente_id, mock_blu_client_context_dict):
    """Cache hit: DB is never called."""
    service, mock_redis = _make_service(mocker)
    mock_redis.get_json.return_value = mock_blu_client_context_dict

    result = asyncio.get_event_loop().run_until_complete(
        service.get_client_context_by_id(mock_cliente_id)
    )

    mock_redis.get_json.assert_called_once()
    service._supabase_crud.get_cliente_blu_by_id.assert_not_called()
    assert isinstance(result, BluClientContext)


def test_get_client_context_cache_miss(mocker, mock_cliente_id, mock_cliente_blu_row):
    """Cache miss: context is fetched from Supabase, then cached."""
    service, mock_redis = _make_service(mocker)
    mock_redis.get_json.return_value = None
    service._supabase_crud.get_cliente_blu_by_id.return_value = mock_cliente_blu_row

    # Prevent sql_table_config enrichment from making real calls
    mocker.patch.object(service, "get_sql_table_configs", return_value=[])

    result = asyncio.get_event_loop().run_until_complete(
        service.get_client_context_by_id(mock_cliente_id)
    )

    service._supabase_crud.get_cliente_blu_by_id.assert_called_once_with(mock_cliente_id)
    mock_redis.set_json.assert_called_once()
    assert isinstance(result, BluClientContext)


def test_get_client_context_not_found(mocker, mock_cliente_id):
    """Client missing from both cache and DB returns None without caching."""
    service, mock_redis = _make_service(mocker)
    mock_redis.get_json.return_value = None
    service._supabase_crud.get_cliente_blu_by_id.return_value = None

    result = asyncio.get_event_loop().run_until_complete(
        service.get_client_context_by_id(mock_cliente_id)
    )

    mock_redis.set_json.assert_not_called()
    assert result is None
