"""Integration tests for analytics_v2.get_context_metrics_for_client.

Covers:
  - Response shape (all expected columns present, correct types)
  - Value invariants (non-negative totals, pct within plausible range)
  - Tenant isolation (p_client_id scopes results; unknown client returns empty)
  - Edge case: client with no series data returns empty result set
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.integration

EXPECTED_COLUMNS = {
    "dimension",
    "kpi",
    "label",
    "unit",
    "current_value",
    "prev_month_value",
    "avg_6m",
    "mom_pct",
    "vs_6m_avg_pct",
    "streak_months",
}

EXPECTED_DIMENSIONS = {"finance", "commercial", "inventory", "supply"}

EXPECTED_KPIS = {
    # Finance (3)
    "receita_liquida",
    "ticket_medio",
    "total_pedidos",
    # Commercial (6)
    "clientes_unicos",
    "clientes_novos",
    "clientes_recorrentes",
    "taxa_recorrencia_perc",
    "receita_por_cliente",
    "frequencia_media",
    # Inventory (3)
    "skus_ativos",
    "quantidade_vendida",
    "receita_por_sku",
    # Supply (3)
    "fornecedores_ativos",
    "receita_por_fornecedor",
    "concentracao_top1_fornecedor_perc",
}

VALID_UNITS = {"BRL", "count", "%", "days"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def db():
    """Service-role Supabase client — bypasses RLS."""
    from blu_supabase_client import get_supabase_client

    return get_supabase_client()


@pytest.fixture(scope="module")
def primary_client_id() -> str:
    return os.getenv("TEST_CLIENT_ID", "e0e9c949-18fe-4d9a-9295-d5dfb2cc9723")


@pytest.fixture(scope="module")
def unknown_client_id() -> str:
    """A UUID that has no data in the analytics schema."""
    return "00000000-0000-0000-0000-000000000000"


def _call(db, client_id: str) -> list[dict]:
    resp = (
        db.schema("analytics_v2")
        .rpc("get_context_metrics_for_client", {"p_client_id": client_id})
        .execute()
    )
    return resp.data or []


# ---------------------------------------------------------------------------
# Shape tests
# ---------------------------------------------------------------------------


def test_returns_list(db, primary_client_id):
    rows = _call(db, primary_client_id)
    assert isinstance(rows, list)


def test_columns_present(db, primary_client_id):
    rows = _call(db, primary_client_id)
    if not rows:
        pytest.skip("No series data for test client — skipping column checks")
    for row in rows:
        missing = EXPECTED_COLUMNS - set(row.keys())
        assert not missing, f"Missing columns: {missing}"


def test_all_expected_kpis_returned(db, primary_client_id):
    """All 5 KPIs are returned when the client has any series data."""
    rows = _call(db, primary_client_id)
    if not rows:
        pytest.skip("No series data for test client")
    returned_kpis = {r["kpi"] for r in rows}
    assert EXPECTED_KPIS == returned_kpis


def test_dimension_values(db, primary_client_id):
    rows = _call(db, primary_client_id)
    if not rows:
        pytest.skip("No series data for test client")
    for row in rows:
        assert row["dimension"] in EXPECTED_DIMENSIONS, (
            f"Unexpected dimension: {row['dimension']!r}"
        )


def test_unit_values(db, primary_client_id):
    rows = _call(db, primary_client_id)
    if not rows:
        pytest.skip("No series data for test client")
    for row in rows:
        assert row["unit"] in VALID_UNITS, f"Unexpected unit: {row['unit']!r}"


# ---------------------------------------------------------------------------
# Value invariants
# ---------------------------------------------------------------------------


def test_current_value_non_negative(db, primary_client_id):
    rows = _call(db, primary_client_id)
    for row in rows:
        val = row["current_value"]
        assert val is None or val >= 0, (
            f"{row['kpi']}: current_value should be non-negative, got {val}"
        )


def test_avg_6m_non_negative(db, primary_client_id):
    rows = _call(db, primary_client_id)
    for row in rows:
        val = row["avg_6m"]
        assert val is None or val >= 0, (
            f"{row['kpi']}: avg_6m should be non-negative, got {val}"
        )


def test_mom_pct_plausible(db, primary_client_id):
    """MoM % should be either NULL (no prev month) or within ±10 000 %."""
    rows = _call(db, primary_client_id)
    for row in rows:
        pct = row["mom_pct"]
        if pct is not None:
            assert -10_000 <= pct <= 10_000, (
                f"{row['kpi']}: mom_pct out of plausible range: {pct}"
            )


def test_streak_is_integer(db, primary_client_id):
    rows = _call(db, primary_client_id)
    for row in rows:
        assert isinstance(row["streak_months"], int), (
            f"{row['kpi']}: streak_months must be int, got {type(row['streak_months'])}"
        )


# ---------------------------------------------------------------------------
# Tenant isolation
# ---------------------------------------------------------------------------


def test_unknown_client_returns_empty(db, unknown_client_id):
    """A client with no data should produce an empty result set, not an error."""
    rows = _call(db, unknown_client_id)
    assert rows == [], f"Expected empty list for unknown client, got {rows}"


def test_results_are_scoped_to_client(db, primary_client_id, unknown_client_id):
    """Results for two different clients must not bleed across."""
    rows_a = _call(db, primary_client_id)
    rows_b = _call(db, unknown_client_id)

    # If client A has data, client B (no data) must have none
    if rows_a:
        assert rows_b == [], "Unknown client must not receive another client's metrics"
