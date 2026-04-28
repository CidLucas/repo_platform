"""Phase 6 — §6 KPI Catalog smoke tests.

These tests are intentionally migration-static: they don't spin up Postgres,
they assert that the migration file ships the contract the dashboard expects:

  • `public.kpi_catalog` table is created with the canonical CHECK lists
    (units, data_status, tier_required, dimensions).
  • Every §6 KPI has a catalog row (≥ expected count per dimension).
  • Each dimension RPC is replaced and returns the full §6 column surface.
  • `analytics_v2.get_admin_indicators` is created (§6.6).
  • `public.list_kpi_catalog` exists and is granted to authenticated.

The migration drift on the remote (Apr-2026 ~150 missing local migrations)
means we cannot apply this against a real db here. When that drift is
resolved, swap these regex checks for an integration test that calls
`select * from analytics_v2.get_*_indicators('30d')` on a seeded fixture.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_MIGRATION = (
    Path(__file__).resolve().parent.parent
    / "supabase"
    / "migrations"
    / "20260427210000_phase6_kpi_catalog.sql"
)


@pytest.fixture(scope="module")
def sql() -> str:
    assert _MIGRATION.exists(), f"Phase 6 migration missing: {_MIGRATION}"
    return _MIGRATION.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Table + helper + list RPC
# ---------------------------------------------------------------------------


def test_kpi_catalog_table_created(sql: str) -> None:
    assert "CREATE TABLE IF NOT EXISTS public.kpi_catalog" in sql
    # Canonical CHECK constraints (must match analyticsService.ts unions).
    assert "CHECK (unit IN ('number','currency','percent','days','hours','ratio','count'))" in sql
    assert (
        "CHECK (data_status IN ('live','proxy','external','pending_data'))" in sql
    )
    assert (
        "CHECK (tier_required IN ('BASIC','SME','PRO','PREMIUM','ENTERPRISE','ADMIN'))"
        in sql
    )
    assert (
        "CHECK (dimension IN" in sql
        and "'finance'" in sql
        and "'admin'" in sql
    )


def test_kpi_tier_rank_helper(sql: str) -> None:
    assert "CREATE OR REPLACE FUNCTION public.kpi_tier_rank(p_tier text)" in sql
    # Numeric ranks must agree with blu_agent_framework.approval._TIER_DEFAULTS.
    for tier, rank in [
        ("BASIC", 10),
        ("SME", 20),
        ("PRO", 20),
        ("PREMIUM", 30),
        ("ENTERPRISE", 40),
        ("ADMIN", 99),
    ]:
        assert re.search(rf"WHEN '{tier}'\s+THEN {rank}", sql), tier


def test_list_kpi_catalog_rpc(sql: str) -> None:
    assert "CREATE OR REPLACE FUNCTION public.list_kpi_catalog" in sql
    assert "GRANT EXECUTE ON FUNCTION public.list_kpi_catalog(text, boolean) TO authenticated" in sql
    assert "is_enabled" in sql


# ---------------------------------------------------------------------------
# 2. Catalog seed coverage per §6 dimension
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "prefix, minimum",
    [
        ("'fin.", 14),  # §6.1
        ("'com.", 16),  # §6.2
        ("'inv.", 14),  # §6.3
        ("'sup.", 17),  # §6.4
        ("'mkt.", 11),  # §6.5
        ("'adm.", 7),   # §6.6
    ],
)
def test_catalog_has_rows_per_dimension(sql: str, prefix: str, minimum: int) -> None:
    count = sql.count(prefix)
    assert count >= minimum, f"{prefix}* expected ≥ {minimum} catalog rows, found {count}"


# ---------------------------------------------------------------------------
# 3. Dimension RPCs replaced with full §6 surface
# ---------------------------------------------------------------------------


_FINANCE_COLS = (
    "receita_liquida custo_total margem_bruta_perc margem_operacional_perc "
    "ticket_medio receita_yoy_perc crescimento_receita_perc total_pedidos "
    "dso_dias dpo_dias ccc_dias working_capital_ratio burn_rate_mensal "
    "runway_meses cash_flow_30d period"
).split()

_COMMERCIAL_COLS = (
    "pedidos_periodo receita_periodo ticket_medio clientes_unicos clientes_novos "
    "clientes_recorrentes recencia_media_dias frequencia_media_mensal churn_60d_perc "
    "crescimento_receita_perc win_rate_perc ciclo_venda_dias nrr_perc clv "
    "checkout_conversion_perc nps period"
).split()

_INVENTORY_COLS = (
    "skus_ativos skus_total quantidade_vendida_periodo receita_skus_periodo "
    "giro_estimado ticket_medio_sku cobertura_top20_perc stockout_rate_perc "
    "crescimento_quantidade_perc dio_dias cobertura_dias fill_rate_perc "
    "sell_through_perc gmroi acuracidade_perc period"
).split()

_SUPPLY_COLS = (
    "rfqs_abertas rfqs_enviadas rfqs_respondidas taxa_resposta_perc "
    "tempo_resposta_medio_h pos_aprovadas pos_pendentes_aprovacao spend_periodo "
    "fornecedores_ativos concentracao_top_perc cycle_time_medio_h "
    "cost_savings_perc ppv otif_perc lead_time_medio_dias maverick_spend_perc "
    "spend_under_management_perc period"
).split()

_MARKETING_COLS = (
    "novos_clientes_periodo receita_novos_clientes conversao_campanha_perc "
    "engajamento_whatsapp_perc taxa_optout_perc cac ltv_cac_ratio cac_payback_meses "
    "roas ctr_perc share_of_voice_perc period"
).split()

_ADMIN_COLS = (
    "aprovacoes_pendentes lead_time_aprovacao_h sla_aprovacao_perc "
    "documentos_pendentes cobertura_rotinas_perc frescor_dados_h "
    "audit_coverage_perc period"
).split()


def _rpc_block(sql: str, fn: str) -> str:
    """Return the body between `CREATE FUNCTION analytics_v2.<fn>` and the next ';'-terminated block."""
    pat = re.compile(
        rf"CREATE (?:OR REPLACE )?FUNCTION analytics_v2\.{re.escape(fn)}\b.*?\$\$;",
        re.DOTALL,
    )
    m = pat.search(sql)
    assert m, f"RPC {fn} not found in migration"
    return m.group(0)


@pytest.mark.parametrize(
    "fn, cols",
    [
        ("get_finance_indicators", _FINANCE_COLS),
        ("get_commercial_indicators", _COMMERCIAL_COLS),
        ("get_inventory_indicators", _INVENTORY_COLS),
        ("get_supply_indicators", _SUPPLY_COLS),
        ("get_marketing_indicators", _MARKETING_COLS),
        ("get_admin_indicators", _ADMIN_COLS),
    ],
)
def test_rpc_returns_full_kpi_surface(sql: str, fn: str, cols: list[str]) -> None:
    block = _rpc_block(sql, fn)
    missing = [c for c in cols if c not in block]
    assert not missing, f"{fn} missing columns: {missing}"
    assert (
        f"GRANT EXECUTE ON FUNCTION analytics_v2.{fn}" in sql
    ), f"missing GRANT for {fn}"


def test_commercial_groupby_rpcs(sql: str) -> None:
    for fn in (
        "get_commercial_revenue_by_channel",
        "get_commercial_top_clients",
    ):
        assert (
            f"CREATE OR REPLACE FUNCTION analytics_v2.{fn}" in sql
        ), f"missing RPC {fn}"
        assert f"GRANT EXECUTE ON FUNCTION analytics_v2.{fn}" in sql


def test_security_invoker_and_search_path(sql: str) -> None:
    # Every analytics_v2 RPC in this migration must be SECURITY INVOKER and pin
    # the search_path so RLS via public.get_my_client_id() is honored.
    invoker_count = len(re.findall(r"SECURITY INVOKER", sql))
    search_path_count = len(re.findall(r"SET search_path = analytics_v2, public", sql))
    # 6 dim RPCs + 2 commercial groupby = 8 analytics_v2 RPCs in this file.
    assert invoker_count >= 8
    assert search_path_count >= 8
