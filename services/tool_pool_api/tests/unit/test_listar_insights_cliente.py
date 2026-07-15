# tests/unit/test_listar_insights_cliente.py
"""Unit tests for _listar_insights_cliente_logic (F2 — leitura dos cards de rotinas).

O cliente Supabase é síncrono — os mocks refletem esse contrato (MagicMock,
nunca AsyncMock nos builders/execute).
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastmcp.exceptions import ToolError
from tool_pool_api.server.tool_modules.routines_module import (
    _listar_insights_cliente_logic,
)

TEST_CLIENT_ID = str(uuid.uuid4())

_SAMPLE_ROWS = [
    {
        "id": "ins-1",
        "room": "financeiro",
        "kpi": "saldo_caixa",
        "title": "Saldo em queda",
        "body": "Saldo caiu 18% na semana.",
        "observation": "Queda concentrada em fornecedores.",
        "recommendation": "Revisar pagamentos programados.",
        "severity": "warning",
        "metric_value": 42000.0,
        "baseline_value": 51000.0,
        "variance_pct": -17.6,
        "run_date": "2026-07-14",
        "generated_at": "2026-07-14T06:00:00+00:00",
        "dismissed": False,
    },
]


def _make_mock_db(rows=None, capture: dict | None = None):
    """Chainable sync Supabase mock; registra filtros aplicados em `capture`."""
    chain = MagicMock()
    for method in ("select", "order", "limit"):
        getattr(chain, method).return_value = chain

    def _eq(col, val):
        if capture is not None:
            capture.setdefault("eq", []).append((col, val))
        return chain

    chain.eq.side_effect = _eq
    chain.execute.return_value = MagicMock(data=rows if rows is not None else [])

    db = MagicMock()
    db.table.return_value = chain
    return db, chain


@pytest.mark.asyncio
async def test_listar_insights_happy_path():
    db, chain = _make_mock_db(rows=_SAMPLE_ROWS)
    with patch(
        "tool_pool_api.server.tool_modules.routines_module.get_supabase_client",
        return_value=db,
    ):
        result = await _listar_insights_cliente_logic(ctx=None, client_id=TEST_CLIENT_ID)

    assert result["total"] == 1
    assert result["insights"][0]["title"] == "Saldo em queda"
    db.table.assert_called_once_with("client_insights")


@pytest.mark.asyncio
async def test_listar_insights_exclui_dispensados_por_default():
    capture: dict = {}
    db, chain = _make_mock_db(rows=[], capture=capture)
    with patch(
        "tool_pool_api.server.tool_modules.routines_module.get_supabase_client",
        return_value=db,
    ):
        await _listar_insights_cliente_logic(ctx=None, client_id=TEST_CLIENT_ID)

    assert ("dismissed", False) in capture["eq"]


@pytest.mark.asyncio
async def test_listar_insights_incluir_dispensados_remove_filtro():
    capture: dict = {}
    db, chain = _make_mock_db(rows=[], capture=capture)
    with patch(
        "tool_pool_api.server.tool_modules.routines_module.get_supabase_client",
        return_value=db,
    ):
        await _listar_insights_cliente_logic(
            ctx=None, client_id=TEST_CLIENT_ID, incluir_dispensados=True
        )

    assert ("dismissed", False) not in capture.get("eq", [])


@pytest.mark.asyncio
async def test_listar_insights_filtros_room_e_severity():
    capture: dict = {}
    db, chain = _make_mock_db(rows=[], capture=capture)
    with patch(
        "tool_pool_api.server.tool_modules.routines_module.get_supabase_client",
        return_value=db,
    ):
        await _listar_insights_cliente_logic(
            ctx=None, client_id=TEST_CLIENT_ID, room="financeiro", severity="warning"
        )

    assert ("room", "financeiro") in capture["eq"]
    assert ("severity", "warning") in capture["eq"]


@pytest.mark.asyncio
async def test_listar_insights_severity_invalida():
    with pytest.raises(ToolError, match="severity inválida"):
        await _listar_insights_cliente_logic(
            ctx=None, client_id=TEST_CLIENT_ID, severity="critical"
        )


@pytest.mark.asyncio
async def test_listar_insights_limite_com_teto_de_50():
    db, chain = _make_mock_db(rows=[])
    with patch(
        "tool_pool_api.server.tool_modules.routines_module.get_supabase_client",
        return_value=db,
    ):
        await _listar_insights_cliente_logic(
            ctx=None, client_id=TEST_CLIENT_ID, limite=500
        )

    chain.limit.assert_called_once_with(50)


@pytest.mark.asyncio
async def test_listar_insights_sem_client_id():
    with pytest.raises(ToolError, match="client_id"):
        await _listar_insights_cliente_logic(ctx=None, client_id=None)


@pytest.mark.asyncio
async def test_listar_insights_erro_db_vira_tool_error():
    db, chain = _make_mock_db()
    chain.execute.side_effect = Exception("connection reset")
    with patch(
        "tool_pool_api.server.tool_modules.routines_module.get_supabase_client",
        return_value=db,
    ):
        with pytest.raises(ToolError, match="Erro ao listar insights"):
            await _listar_insights_cliente_logic(ctx=None, client_id=TEST_CLIENT_ID)
