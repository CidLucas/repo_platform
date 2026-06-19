"""
Tests unitários para memory_post_flight (T1.2e).

Testa:
  - _shared_memory_post_flight_logic com dados de agent_result
  - Noise suppression (múltiplas escritas)
  - Naming convention (prefixos)
  - Fire-and-forget (não testado aqui — validado em service.py)
  - Migration CHECK constraint (validado em migração separada)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_db(upsert_result=None, insert_result=None):
    """Cria um mock do Supabase client com tabelas encadeadas."""
    mock_db = AsyncMock()
    mock_table = MagicMock()
    mock_upsert = AsyncMock()
    mock_insert = AsyncMock()

    if upsert_result is None:
        upsert_result = MagicMock(data=[{"id": "test-1"}])
    if insert_result is None:
        insert_result = MagicMock(data=[{"id": "link-1"}])

    mock_upsert.return_value = mock_upsert
    mock_upsert.execute = AsyncMock(return_value=upsert_result)

    mock_insert.return_value = mock_insert
    mock_insert.execute = AsyncMock(return_value=insert_result)

    mock_table.upsert.return_value = mock_upsert
    mock_table.insert.return_value = mock_insert

    mock_db.schema.return_value.table.return_value = mock_table
    return mock_db


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_flight_agent_result_summary():
    """Persiste agent_result com summary e tool_calls."""
    mock_db = _make_mock_db()

    with patch(
        "src.tool_pool_api.server.tool_modules.memory_post_flight.get_supabase_client",
        return_value=mock_db,
    ):
        from src.tool_pool_api.server.tool_modules.memory_post_flight import (
            _shared_memory_post_flight_logic,
        )

        result = await _shared_memory_post_flight_logic(
            client_id="550e8400-e29b-41d4-a716-446655440000",
            agent_slug="crm",
            session_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            agent_result={
                "summary": "Cliente X está 3 meses atrasado. Recomendo follow-up.",
                "tool_calls": ["execute_sql", "executar_rag_cliente"],
            },
        )

        assert result["agent_result_entries"] == 3  # 1 summary + 2 tool_usage
        assert result["agent_metadata_entries"] == 0
        assert result["links_created"] == 0


@pytest.mark.asyncio
async def test_post_flight_agent_metadata():
    """Persiste agent_metadata com session_id, elapsed, agent_slug."""
    mock_db = _make_mock_db()

    with patch(
        "src.tool_pool_api.server.tool_modules.memory_post_flight.get_supabase_client",
        return_value=mock_db,
    ):
        from src.tool_pool_api.server.tool_modules.memory_post_flight import (
            _shared_memory_post_flight_logic,
        )

        result = await _shared_memory_post_flight_logic(
            client_id="550e8400-e29b-41d4-a716-446655440000",
            agent_slug="estrategia",
            session_id="b2c3d4e5-f6a7-8901-bcde-f12345678901",
            agent_metadata={
                "session_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                "agent_slug": "estrategia",
                "elapsed_seconds": 12.5,
            },
        )

        assert result["agent_metadata_entries"] == 3  # session_id, elapsed_seconds, agent_slug
        assert result["agent_result_entries"] == 0
        assert result["links_created"] == 0


@pytest.mark.asyncio
async def test_post_flight_naming_convention_prefixes():
    """Valida que keys de tool_usage usam prefixo tool_usage:."""
    mock_db = _make_mock_db()

    with patch(
        "src.tool_pool_api.server.tool_modules.memory_post_flight.get_supabase_client",
        return_value=mock_db,
    ):
        from src.tool_pool_api.server.tool_modules.memory_post_flight import (
            _shared_memory_post_flight_logic,
        )

        await _shared_memory_post_flight_logic(
            client_id="550e8400-e29b-41d4-a716-446655440000",
            agent_slug="crm",
            session_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            agent_result={
                "summary": "test",
                "tool_calls": ["execute_sql", "google_calendar_write"],
            },
        )

        # Verifica que o upsert foi chamado com keys usando prefixo tool_usage:
        calls = mock_db.schema.return_value.table.return_value.upsert.call_args_list
        tool_keys = [
            c[0][0]["key"]
            for c in calls
            if "tool_usage:" in str(c[0][0].get("key", ""))
        ]
        assert len(tool_keys) == 2
        assert "tool_usage:execute_sql" in tool_keys
        assert "tool_usage:google_calendar_write" in tool_keys


@pytest.mark.asyncio
async def test_post_flight_suggested_links():
    """Persiste agent_link_pending links com source='agent_pending'."""
    mock_db = _make_mock_db()

    with patch(
        "src.tool_pool_api.server.tool_modules.memory_post_flight.get_supabase_client",
        return_value=mock_db,
    ):
        from src.tool_pool_api.server.tool_modules.memory_post_flight import (
            _shared_memory_post_flight_logic,
        )

        result = await _shared_memory_post_flight_logic(
            client_id="550e8400-e29b-41d4-a716-446655440000",
            agent_slug="crm",
            session_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            suggested_links=[
                {
                    "source_entity_type": "client",
                    "source_entity_name": "acme_corp",
                    "target_entity_type": "contact",
                    "target_entity_name": "joao_silva",
                    "link_type": "works_for",
                },
            ],
        )

        assert result["links_created"] == 1

        # Verifica que source='agent_pending'
        insert_call = mock_db.schema.return_value.table.return_value.insert.call_args
        payload = insert_call[0][0]
        assert payload["source"] == "agent_pending"
        assert payload["confidence"] == 0.5


@pytest.mark.asyncio
async def test_post_flight_noise_suppression():
    """Múltiplas chamadas com mesma key sobrescrevem (upsert)."""
    mock_db = _make_mock_db()

    with patch(
        "src.tool_pool_api.server.tool_modules.memory_post_flight.get_supabase_client",
        return_value=mock_db,
    ):
        from src.tool_pool_api.server.tool_modules.memory_post_flight import (
            _shared_memory_post_flight_logic,
        )

        # Primeira execução
        await _shared_memory_post_flight_logic(
            client_id="550e8400-e29b-41d4-a716-446655440000",
            agent_slug="crm",
            session_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            agent_result={"summary": "Primeiro resultado", "tool_calls": ["tool_a"]},
        )

        # Segunda execução — mesma session, deve sobrescrever
        await _shared_memory_post_flight_logic(
            client_id="550e8400-e29b-41d4-a716-446655440000",
            agent_slug="crm",
            session_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            agent_result={"summary": "Resultado atualizado", "tool_calls": ["tool_b"]},
        )

        # Verifica que upsert foi chamado (não insert)
        upsert_calls = mock_db.schema.return_value.table.return_value.upsert.call_count
        assert upsert_calls >= 4  # 2 x (1 summary + 1 tool) = 4 chamadas minimum


@pytest.mark.asyncio
async def test_post_flight_empty_result():
    """Resultado vazio não deve causar erro."""
    mock_db = _make_mock_db()

    with patch(
        "src.tool_pool_api.server.tool_modules.memory_post_flight.get_supabase_client",
        return_value=mock_db,
    ):
        from src.tool_pool_api.server.tool_modules.memory_post_flight import (
            _shared_memory_post_flight_logic,
        )

        result = await _shared_memory_post_flight_logic(
            client_id="550e8400-e29b-41d4-a716-446655440000",
            agent_slug="frontdesk",
            session_id="c3d4e5f6-a7b8-9012-cdef-123456789012",
        )

        assert result["agent_result_entries"] == 0
        assert result["agent_metadata_entries"] == 0
        assert result["links_created"] == 0


@pytest.mark.asyncio
async def test_post_flight_duplicate_link_handled():
    """Link duplicado não causa erro — loga debug e continua."""
    mock_db = _make_mock_db()
    # Simula duplicate key error no insert do link
    mock_table = mock_db.schema.return_value.table.return_value
    mock_table.insert.return_value.execute = AsyncMock(
        side_effect=Exception("duplicate key uq_shared_memory_link")
    )

    with patch(
        "src.tool_pool_api.server.tool_modules.memory_post_flight.get_supabase_client",
        return_value=mock_db,
    ):
        from src.tool_pool_api.server.tool_modules.memory_post_flight import (
            _shared_memory_post_flight_logic,
        )

        result = await _shared_memory_post_flight_logic(
            client_id="550e8400-e29b-41d4-a716-446655440000",
            agent_slug="crm",
            session_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            suggested_links=[
                {
                    "source_entity_type": "client",
                    "source_entity_name": "acme",
                    "target_entity_type": "contact",
                    "target_entity_name": "joao",
                    "link_type": "works_for",
                },
            ],
        )

        # Link duplicado é silenciosamente ignorado
        assert result["links_created"] == 0


@pytest.mark.asyncio
async def test_post_flight_incomplete_link_skipped():
    """Link com campos faltando é pulado."""
    mock_db = _make_mock_db()

    with patch(
        "src.tool_pool_api.server.tool_modules.memory_post_flight.get_supabase_client",
        return_value=mock_db,
    ):
        from src.tool_pool_api.server.tool_modules.memory_post_flight import (
            _shared_memory_post_flight_logic,
        )

        result = await _shared_memory_post_flight_logic(
            client_id="550e8400-e29b-41d4-a716-446655440000",
            agent_slug="crm",
            session_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            suggested_links=[
                {
                    "source_entity_type": "",  # vazio — inválido
                    "source_entity_name": "acme",
                    "target_entity_type": "contact",
                    "target_entity_name": "joao",
                    "link_type": "works_for",
                },
            ],
        )

        assert result["links_created"] == 0
