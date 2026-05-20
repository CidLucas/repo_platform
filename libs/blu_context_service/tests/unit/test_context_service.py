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


def test_get_client_context_cache_hit(mocker, mock_client_id, mock_blu_client_context_dict):
    """Cache hit: DB is never called."""
    service, mock_redis = _make_service(mocker)
    mock_redis.get_json.return_value = mock_blu_client_context_dict

    result = asyncio.get_event_loop().run_until_complete(
        service.get_client_context_by_id(mock_client_id)
    )

    mock_redis.get_json.assert_called_once()
    service._supabase_crud.get_cliente_blu_by_id.assert_not_called()
    assert isinstance(result, BluClientContext)


def test_get_client_context_cache_miss(mocker, mock_client_id, mock_cliente_blu_row):
    """Cache miss: context is fetched from Supabase, then cached."""
    service, mock_redis = _make_service(mocker)
    mock_redis.get_json.return_value = None
    service._supabase_crud.get_cliente_blu_by_id.return_value = mock_cliente_blu_row

    # Prevent sql_table_config enrichment from making real calls
    mocker.patch.object(service, "get_sql_table_configs", return_value=[])

    result = asyncio.get_event_loop().run_until_complete(
        service.get_client_context_by_id(mock_client_id)
    )

    service._supabase_crud.get_cliente_blu_by_id.assert_called_once_with(mock_client_id)
    mock_redis.set_json.assert_called_once()
    assert isinstance(result, BluClientContext)


def test_get_client_context_not_found(mocker, mock_client_id):
    """Client missing from both cache and DB returns None without caching."""
    service, mock_redis = _make_service(mocker)
    mock_redis.get_json.return_value = None
    service._supabase_crud.get_cliente_blu_by_id.return_value = None

    result = asyncio.get_event_loop().run_until_complete(
        service.get_client_context_by_id(mock_client_id)
    )

    mock_redis.set_json.assert_not_called()
    assert result is None


# ---------------------------------------------------------------------------
# get_domain_projection tests
# ---------------------------------------------------------------------------

def _make_full_context(mock_client_id) -> BluClientContext:
    """BluClientContext with all sections populated."""
    return BluClientContext(
        id=mock_client_id,
        nome_empresa="Acme Corp",
        tier="BASIC",
        company_profile={"legal_name": "Acme Corp"},
        brand_voice={"tone": "professional"},
        team_structure={"business_hours": "9-18"},
        policies={"return_policy": "30 days"},
        data_schema={"available_tables": ["orders"]},
        available_tools={"enabled_tool_names": ["execute_sql"]},
        credenciais=[],
    )


def test_domain_projection_analytics_includes_data_sections(mocker, mock_client_id):
    """'analytics' domain returns data_schema + available_tools + company_profile."""
    service, _ = _make_service(mocker)
    mocker.patch.object(
        service, "get_client_context_by_id",
        return_value=_make_full_context(mock_client_id)
    )

    result = asyncio.get_event_loop().run_until_complete(
        service.get_domain_projection("analytics", mock_client_id)
    )

    assert "data_schema" in result
    assert "available_tools" in result
    assert "company_profile" in result
    # Communication sections must be excluded
    assert "brand_voice" not in result
    assert "policies" not in result
    assert "team_structure" not in result


def test_domain_projection_rfq_includes_communication_sections(mocker, mock_client_id):
    """'rfq' domain returns brand_voice + policies + team_structure + company_profile."""
    service, _ = _make_service(mocker)
    mocker.patch.object(
        service, "get_client_context_by_id",
        return_value=_make_full_context(mock_client_id)
    )

    result = asyncio.get_event_loop().run_until_complete(
        service.get_domain_projection("rfq", mock_client_id)
    )

    assert "brand_voice" in result
    assert "policies" in result
    assert "team_structure" in result
    assert "company_profile" in result
    assert "data_schema" not in result


def test_domain_projection_unknown_domain_returns_all_sections(mocker, mock_client_id):
    """Unknown domain includes all loaded sections."""
    service, _ = _make_service(mocker)
    mocker.patch.object(
        service, "get_client_context_by_id",
        return_value=_make_full_context(mock_client_id)
    )

    result = asyncio.get_event_loop().run_until_complete(
        service.get_domain_projection("unknown-domain", mock_client_id)
    )

    for section in ("company_profile", "brand_voice", "team_structure",
                    "policies", "data_schema", "available_tools"):
        assert section in result


def test_domain_projection_always_includes_identity(mocker, mock_client_id):
    """id, nome_empresa, and tier are always in the projection."""
    service, _ = _make_service(mocker)
    mocker.patch.object(
        service, "get_client_context_by_id",
        return_value=_make_full_context(mock_client_id)
    )

    result = asyncio.get_event_loop().run_until_complete(
        service.get_domain_projection("analytics", mock_client_id)
    )

    assert result["nome_empresa"] == "Acme Corp"
    assert result["tier"] == "BASIC"
    assert result["id"] == str(mock_client_id)


def test_domain_projection_empty_sections_are_excluded(mocker, mock_client_id):
    """Sections with None value are not included in the projection."""
    service, _ = _make_service(mocker)
    ctx = BluClientContext(
        id=mock_client_id,
        nome_empresa="Acme Corp",
        tier="BASIC",
        # data_schema and available_tools are None
        company_profile={"legal_name": "Acme Corp"},
        credenciais=[],
    )
    mocker.patch.object(service, "get_client_context_by_id", return_value=ctx)

    result = asyncio.get_event_loop().run_until_complete(
        service.get_domain_projection("analytics", mock_client_id)
    )

    assert "data_schema" not in result
    assert "available_tools" not in result
    assert "company_profile" in result


def test_domain_projection_returns_empty_when_context_not_found(mocker, mock_client_id):
    """Returns empty dict when client context is unavailable."""
    service, _ = _make_service(mocker)
    mocker.patch.object(service, "get_client_context_by_id", return_value=None)

    result = asyncio.get_event_loop().run_until_complete(
        service.get_domain_projection("analytics", mock_client_id)
    )

    assert result == {}


def test_domain_projection_case_insensitive(mocker, mock_client_id):
    """Domain matching is case-insensitive."""
    service, _ = _make_service(mocker)
    mocker.patch.object(
        service, "get_client_context_by_id",
        return_value=_make_full_context(mock_client_id)
    )

    result = asyncio.get_event_loop().run_until_complete(
        service.get_domain_projection("ANALYTICS", mock_client_id)
    )

    assert "data_schema" in result
    assert "brand_voice" not in result
