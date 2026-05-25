import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

import blu_context_service.context_service as context_service_module
from blu_context_service.context_service import ContextService
from blu_context_service.redis_service import RedisService
from blu_models.blu_client_context import BluClientContext


def _make_service(mocker) -> tuple[ContextService, MagicMock]:
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


@pytest.fixture(autouse=True)
def _reset_google_oauth_cache():
    """Garantir cache módulo-level limpo entre testes."""
    cache_backup = context_service_module._GOOGLE_OAUTH_CONFIG_CACHE
    cache_exp_backup = context_service_module._GOOGLE_OAUTH_CONFIG_CACHE_EXPIRES_AT
    context_service_module._GOOGLE_OAUTH_CONFIG_CACHE = None
    context_service_module._GOOGLE_OAUTH_CONFIG_CACHE_EXPIRES_AT = None
    try:
        yield
    finally:
        context_service_module._GOOGLE_OAUTH_CONFIG_CACHE = cache_backup
        context_service_module._GOOGLE_OAUTH_CONFIG_CACHE_EXPIRES_AT = cache_exp_backup


def test_get_google_oauth_config_cached_uses_vault_and_ttl_cache(mocker):
    """Google OAuth config should be fetched from Vault once and cached in-process."""
    service, _ = _make_service(mocker)

    service_client = MagicMock()
    service_crud = MagicMock()
    service_crud.get_platform_oauth_config.return_value = {
        "client_id": "vault-client-id",
        "client_secret": "vault-client-secret",
    }

    # NOTA: _make_service já fez patch global de SupabaseCRUD/get_supabase_client.
    # Aqui sobrescrevemos somente para a chamada do _fetch_google_oauth_config_from_vault,
    # devolvendo sempre o mesmo service_crud configurado (return_value, não side_effect),
    # já que o construtor de ContextService não chama mais SupabaseCRUD depois deste ponto.
    get_client_mock = mocker.patch(
        "blu_context_service.context_service.get_supabase_client",
        return_value=service_client,
    )
    crud_ctor_mock = mocker.patch(
        "blu_context_service.context_service.SupabaseCRUD",
        return_value=service_crud,
    )

    first = asyncio.get_event_loop().run_until_complete(service._get_google_oauth_config_cached())
    second = asyncio.get_event_loop().run_until_complete(service._get_google_oauth_config_cached())

    assert first == {"client_id": "vault-client-id", "client_secret": "vault-client-secret"}
    assert second == first
    # Vault/RPC só deve ser consultado uma vez graças ao TTL cache
    get_client_mock.assert_called_once_with(use_service_role=True)
    crud_ctor_mock.assert_called_once_with(client=service_client)
    assert service_crud.get_platform_oauth_config.call_count == 1
    service_crud.get_platform_oauth_config.assert_called_with("google")


def test_refresh_google_token_raises_when_vault_config_missing(mocker, mock_client_id):
    """Refresh must raise clearly when Vault config is empty/invalid."""
    service, _ = _make_service(mocker)

    mocker.patch.object(service, "_get_google_oauth_config_cached", AsyncMock(return_value=None))

    with pytest.raises(RuntimeError, match="Google OAuth config"):
        asyncio.get_event_loop().run_until_complete(
            service._refresh_google_token(mock_client_id, "refresh-token")
        )
