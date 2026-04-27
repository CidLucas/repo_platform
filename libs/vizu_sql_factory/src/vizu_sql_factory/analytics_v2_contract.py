"""
Frozen analytics_v2 view contract for LLM-callable SQL (Phase 0 / F0.2).

This module is the single source of truth for which analytics_v2 views and
columns the SQL-generation tools (`executar_sql_agent`, RFQ analytics,
report templates) are allowed to reference. It is consumed:

- as `ExecutionConfig.allowed_views` / `allowed_columns` by
  `vizu_sql_factory.TextToSqlExecutor` in any new code path that needs an
  in-memory contract instead of `config/allowlist.json`;
- as the authoritative reference cited from
  `docs/internal/llm-sql-allowlist.md` and `docs/internal/kpi-catalog.md`.

The tables backing these views are NOT directly exposed to LLM-generated
SQL — only the views below are. Materialized views (`mv_*`) are reachable
solely through their `security_invoker` `v_*` wrappers.

Adding a column or view here requires a roadmap entry + RLS review + a
migration that creates/updates the `security_invoker` view on the database
side. See roadmap §6 (KPI catalog) and Phase 0 / F0.2.
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# View contract — analytics_v2 (LLM-callable)
# ---------------------------------------------------------------------------

#: Star-schema fact table. All financial / commercial / inventory KPIs roll up
#: from this table. ``valor`` is the canonical revenue column (NOT
#: ``valor_total``). Date filters MUST go through ``dim_datas``.
FATO_TRANSACOES = "analytics_v2.fato_transacoes"

#: Customer dimension — geography (``endereco_cidade``, ``endereco_uf``) and
#: cluster scoring (``pontuacao_cluster``, ``nivel_cluster``).
DIM_CLIENTES = "analytics_v2.dim_clientes"

#: Supplier dimension — analogous to dim_clientes but for ``fornecedor_id``.
DIM_FORNECEDORES = "analytics_v2.dim_fornecedores"

#: SKU/product dimension — searchable by ``nome ILIKE`` for product lookups.
DIM_INVENTORY = "analytics_v2.dim_inventory"

#: Calendar dimension. JOIN via ``ON ft.data_competencia_id = dd.data_id``
#: (the FK column names differ → ``USING`` does not work).
DIM_DATAS = "analytics_v2.dim_datas"

#: Transaction-type dimension (``categoria``, ``natureza_operacional``,
#: ``impacto_caixa``).
DIM_TIPO_TRANSACAO = "analytics_v2.dim_tipo_transacao"

#: Free-form category dimension (only present on a subset of rows).
DIM_CATEGORIA = "analytics_v2.dim_categoria"

#: ``security_invoker`` summary view used by HomePage. RLS-scoped to
#: ``public.get_my_client_id()``.
V_RESUMO_DASHBOARD = "analytics_v2.v_resumo_dashboard"

#: ``security_invoker`` time-series view (revenue / orders by day).
V_SERIES_TEMPORAL = "analytics_v2.v_series_temporal"

#: ``security_invoker`` regional distribution view (UF/cidade rollup).
V_DISTRIBUICAO_REGIONAL = "analytics_v2.v_distribuicao_regional"

#: ``security_invoker`` last-orders view used by Pedidos page.
V_ULTIMOS_PEDIDOS = "analytics_v2.v_ultimos_pedidos"

# Frozen, alphabetically-stable list of LLM-callable views.
ALLOWED_VIEWS: list[str] = [
    FATO_TRANSACOES,
    DIM_CLIENTES,
    DIM_FORNECEDORES,
    DIM_INVENTORY,
    DIM_DATAS,
    DIM_TIPO_TRANSACAO,
    DIM_CATEGORIA,
    V_RESUMO_DASHBOARD,
    V_SERIES_TEMPORAL,
    V_DISTRIBUICAO_REGIONAL,
    V_ULTIMOS_PEDIDOS,
]

# ---------------------------------------------------------------------------
# Column contract — only columns listed here are LLM-callable.
# ``["*"]`` is intentionally NOT used: every column must be enumerated so
# that adding one is a deliberate review step.
# ---------------------------------------------------------------------------

ALLOWED_COLUMNS: dict[str, list[str]] = {
    FATO_TRANSACOES: [
        "transacao_id",
        "documento",
        "quantidade",
        "valor_unitario",
        "valor",
        "cliente_id",
        "fornecedor_id",
        "inventory_id",
        "data_competencia_id",
        "tipo_id",
        "categoria_id",
        "nf_numero",
        "valor_nf",
        "status",
        "movement_type",
    ],
    DIM_CLIENTES: [
        "cliente_id",
        "nome",
        "cpf_cnpj",
        "endereco_cidade",
        "endereco_uf",
        "receita_total",
        "total_pedidos",
        "ticket_medio",
        "dias_recencia",
        "frequencia_mensal",
        "pontuacao_cluster",
        "nivel_cluster",
        "nome_fantasia",
        "cnae",
    ],
    DIM_FORNECEDORES: [
        "fornecedor_id",
        "nome",
        "cnpj",
        "endereco_cidade",
        "endereco_uf",
        "receita_total",
        "total_pedidos_recebidos",
        "ticket_medio",
        "dias_recencia",
        "frequencia_mensal",
        "pontuacao_cluster",
        "nivel_cluster",
    ],
    DIM_INVENTORY: [
        "inventory_id",
        "nome",
        "sku",
        "ncm",
        "unidade_comercial",
        "receita_total",
        "quantidade_total_vendida",
        "preco_medio",
        "total_pedidos",
        "current_stock",
    ],
    DIM_DATAS: [
        "data_id",
        "data",
        "ano",
        "mes",
        "nome_mes",
        "trimestre",
        "dia_da_semana",
        "e_fim_de_semana",
    ],
    DIM_TIPO_TRANSACAO: [
        "tipo_id",
        "descricao",
        "categoria",
        "natureza_operacional",
        "impacto_caixa",
    ],
    DIM_CATEGORIA: [
        "categoria_id",
        "nome",
        "tipo",
        "grupo",
    ],
    V_RESUMO_DASHBOARD: [
        "total_clientes",
        "total_fornecedores",
        "total_produtos",
        "total_pedidos",
        "receita_total",
        "ticket_medio",
        "quantidade_total_vendida",
        "receita_mes_atual",
        "quantidade_mes_atual",
        "clientes_mes_atual",
        "produtos_mes_atual",
        "fornecedores_mes_atual",
        "crescimento_receita",
        "crescimento_clientes",
        "crescimento_produtos",
        "crescimento_quantidade",
        "frequencia_media_fornecedores",
        "total_regioes",
        "ultimo_mes",
        "clientes_ativos",
        "clientes_novos",
        "gerado_em",
    ],
    V_SERIES_TEMPORAL: [
        "data",
        "ano",
        "mes",
        "receita",
        "quantidade",
        "pedidos",
    ],
    V_DISTRIBUICAO_REGIONAL: [
        "endereco_uf",
        "endereco_cidade",
        "receita",
        "clientes",
        "pedidos",
    ],
    V_ULTIMOS_PEDIDOS: [
        "documento",
        "data",
        "cliente_nome",
        "fornecedor_nome",
        "valor",
        "quantidade",
        "status",
    ],
}

# ---------------------------------------------------------------------------
# Aggregate + safety contract
# ---------------------------------------------------------------------------

#: Aggregates the LLM may emit in generated SQL.
ALLOWED_AGGREGATES: list[str] = ["COUNT", "SUM", "AVG", "MIN", "MAX"]

#: Mandatory tenancy filter — `vizu_sql_factory.SqlRewriter` enforces this
#: column on every generated query.
CLIENT_COLUMN: str = "client_id"

#: Hard cap on rows returned by an LLM query. Per-role overrides live in
#: `vizu_sql_factory.config.allowlist.json` for legacy code paths.
DEFAULT_MAX_ROWS: int = 1000


@dataclass(frozen=True)
class AnalyticsV2Contract:
    """Immutable bundle of the analytics_v2 LLM contract."""

    allowed_views: list[str]
    allowed_columns: dict[str, list[str]]
    allowed_aggregates: list[str]
    client_column: str
    max_rows: int

    def to_execution_config_kwargs(self, *, client_id: str) -> dict:
        """Render kwargs for `vizu_sql_factory.ExecutionConfig`."""
        return {
            "client_id": client_id,
            "allowed_views": list(self.allowed_views),
            "allowed_columns": {k: list(v) for k, v in self.allowed_columns.items()},
            "max_rows": self.max_rows,
            "mandatory_filters": [self.client_column],
            "allowed_aggregates": list(self.allowed_aggregates),
            "allow_rewrites": True,
            "client_column": self.client_column,
        }


ANALYTICS_V2_CONTRACT = AnalyticsV2Contract(
    allowed_views=ALLOWED_VIEWS,
    allowed_columns=ALLOWED_COLUMNS,
    allowed_aggregates=ALLOWED_AGGREGATES,
    client_column=CLIENT_COLUMN,
    max_rows=DEFAULT_MAX_ROWS,
)


__all__ = [
    "ALLOWED_AGGREGATES",
    "ALLOWED_COLUMNS",
    "ALLOWED_VIEWS",
    "ANALYTICS_V2_CONTRACT",
    "AnalyticsV2Contract",
    "CLIENT_COLUMN",
    "DEFAULT_MAX_ROWS",
    "DIM_CATEGORIA",
    "DIM_CLIENTES",
    "DIM_DATAS",
    "DIM_FORNECEDORES",
    "DIM_INVENTORY",
    "DIM_TIPO_TRANSACAO",
    "FATO_TRANSACOES",
    "V_DISTRIBUICAO_REGIONAL",
    "V_RESUMO_DASHBOARD",
    "V_SERIES_TEMPORAL",
    "V_ULTIMOS_PEDIDOS",
]
