"""context_schemas.py — Shared Memory & Snapshot Context Schemas

Defines typed schemas (TypedDict / dataclass) for representing
snapshot dimensions and shared-memory facts consumed by the
BLU Context Service.

Status: IMPLEMENTED — Issue #22 (Snapshot Templates T2.2c-T2.2e).
"""

from __future__ import annotations

from typing import TypedDict


# =============================================================================
# Shared Memory Entry
# =============================================================================


class MemoryEntry(TypedDict, total=False):
    """A single row from shared_business_memory."""

    id: str
    client_id: str
    entity_type: str
    entity_name: str
    key: str
    value: dict
    version: int
    source: str
    confidence: float
    metadata: dict
    created_at: str
    updated_at: str


class SnapshotDimension(TypedDict, total=False):
    """Dimensional snapshot — template structure (Fase 1)."""

    dimension: str
    label: str
    keys: list[str]
    template: dict
    version: int


class SnapshotTemplate(TypedDict, total=False):
    """Aggregate snapshot template (Fase 1)."""

    snapshot_id: str
    client_id: str
    dimensions: list[SnapshotDimension]
    created_at: str
    updated_at: str


# =============================================================================
# Snapshot Indicator Definitions (T2.2c, T2.2d, T2.2e)
# =============================================================================


class _SnapshotIndicator(TypedDict):
    """Definition of a single indicator within a dimension."""

    nome: str
    descricao: str
    unidade: str
    required: bool


class _SnapshotDimensionSpec(TypedDict):
    """Specification for a snapshot dimension."""

    label: str
    indicadores: list[_SnapshotIndicator]
    tendencias: list[str]
    alertas: list[dict[str, str]]
    agrupamentos: list[str]
    queries_referencia: list[str]


# ── Financeiro (T2.2c) ────────────────────────────────────────────────────

_SNAPSHOT_DIMENSION_FIELDS: dict[str, _SnapshotDimensionSpec] = {
    "financeiro": {
        "label": "Financeiro",
        "indicadores": [
            {
                "nome": "saldo_atual",
                "descricao": "Saldo atual em caixa",
                "unidade": "BRL",
                "required": True,
            },
            {
                "nome": "receita_periodo",
                "descricao": "Receita total no período",
                "unidade": "BRL",
                "required": True,
            },
            {
                "nome": "despesa_periodo",
                "descricao": "Despesa total no período",
                "unidade": "BRL",
                "required": True,
            },
            {
                "nome": "fluxo_liquido",
                "descricao": "Fluxo de caixa líquido (receita - despesa)",
                "unidade": "BRL",
                "required": True,
            },
            {
                "nome": "contas_a_pagar",
                "descricao": "Total de contas a pagar em aberto",
                "unidade": "BRL",
                "required": False,
            },
            {
                "nome": "contas_a_receber",
                "descricao": "Total de contas a receber em aberto",
                "unidade": "BRL",
                "required": False,
            },
            {
                "nome": "inadimplencia_percentual",
                "descricao": "Percentual de inadimplência no período",
                "unidade": "%",
                "required": False,
            },
        ],
        "tendencias": ["receita_tendencia", "despesa_tendencia"],
        "alertas": [
            {
                "nome": "estoque_caixa_baixo",
                "descricao": "Saldo de caixa abaixo do mínimo recomendado",
            },
            {
                "nome": "contas_vencendo_proximos_7d",
                "descricao": "Contas a pagar vencendo nos próximos 7 dias",
            },
        ],
        "agrupamentos": [],
        "queries_referencia": [
            "get_cash_position",
            "get_recent_transactions",
            "get_aging_accounts",
        ],
    },

    # ── Clientes (T2.2d) ──────────────────────────────────────────────────

    "clientes": {
        "label": "Clientes",
        "indicadores": [
            {
                "nome": "total_clientes_ativos",
                "descricao": "Número total de clientes ativos",
                "unidade": "count",
                "required": True,
            },
            {
                "nome": "novos_clientes_periodo",
                "descricao": "Novos clientes no período",
                "unidade": "count",
                "required": True,
            },
            {
                "nome": "churn_periodo",
                "descricao": "Clientes perdidos (churn) no período",
                "unidade": "count",
                "required": False,
            },
            {
                "nome": "nps_medio",
                "descricao": "Net Promoter Score médio",
                "unidade": "score",
                "required": False,
            },
            {
                "nome": "ltv_medio",
                "descricao": "Lifetime Value médio por cliente",
                "unidade": "BRL",
                "required": False,
            },
            {
                "nome": "ticket_medio",
                "descricao": "Ticket médio por transação",
                "unidade": "BRL",
                "required": False,
            },
        ],
        "tendencias": [],
        "alertas": [
            {
                "nome": "churn_acelerado",
                "descricao": "Taxa de churn acima do limite aceitável",
            },
            {
                "nome": "nps_critico",
                "descricao": "NPS abaixo do nível crítico",
            },
        ],
        "agrupamentos": ["segmentacao", "status"],
        "queries_referencia": [
            "get_active_clients",
            "get_churn_metrics",
            "get_nps_scores",
            "get_client_ltv",
        ],
    },

    # ── Agenda (T2.2e) ────────────────────────────────────────────────────

    "agenda": {
        "label": "Agenda",
        "indicadores": [
            {
                "nome": "reunioes_hoje",
                "descricao": "Reuniões agendadas para hoje",
                "unidade": "count",
                "required": True,
            },
            {
                "nome": "reunioes_semana",
                "descricao": "Reuniões agendadas para esta semana",
                "unidade": "count",
                "required": True,
            },
            {
                "nome": "followups_pendentes",
                "descricao": "Follow-ups pendentes de ação",
                "unidade": "count",
                "required": False,
            },
            {
                "nome": "contatos_a_cobrar",
                "descricao": "Contatos que precisam de follow-up de cobrança",
                "unidade": "count",
                "required": False,
            },
        ],
        "tendencias": [],
        "alertas": [],
        "agrupamentos": [],
        "queries_referencia": [
            "get_today_meetings",
            "get_weekly_meetings",
            "get_pending_followups",
            "get_collection_contacts",
        ],
    },

    # ── Compras (T2.2e) ───────────────────────────────────────────────────

    "compras": {
        "label": "Compras / Inventory",
        "indicadores": [
            {
                "nome": "total_pos_abertas",
                "descricao": "Total de pedidos de compra em aberto",
                "unidade": "count",
                "required": True,
            },
            {
                "nome": "estoque_critico",
                "descricao": "Itens com estoque abaixo do nível crítico",
                "unidade": "count",
                "required": False,
            },
            {
                "nome": "fornecedores_com_pendencia",
                "descricao": "Fornecedores com entregas pendentes",
                "unidade": "count",
                "required": False,
            },
            {
                "nome": "pedidos_em_analise",
                "descricao": "Pedidos aguardando aprovação",
                "unidade": "count",
                "required": False,
            },
        ],
        "tendencias": [],
        "alertas": [],
        "agrupamentos": [],
        "queries_referencia": [
            "get_open_purchase_orders",
            "get_critical_stock",
            "get_pending_suppliers",
            "get_pending_approval_orders",
        ],
    },
}


# =============================================================================
# Helper functions
# =============================================================================


def get_dimension_spec(dimension: str) -> _SnapshotDimensionSpec | None:
    """Get the specification for a snapshot dimension.

    Args:
        dimension: One of 'financeiro', 'clientes', 'agenda', 'compras'.

    Returns:
        The dimension spec dict, or None if not found.
    """
    return _SNAPSHOT_DIMENSION_FIELDS.get(dimension)


def get_required_indicators(dimension: str) -> list[str]:
    """Get the list of required indicator names for a dimension."""
    spec = _SNAPSHOT_DIMENSION_FIELDS.get(dimension)
    if spec is None:
        return []
    return [ind["nome"] for ind in spec["indicadores"] if ind.get("required", False)]


def get_all_indicator_names(dimension: str) -> list[str]:
    """Get all indicator names (required + optional) for a dimension."""
    spec = _SNAPSHOT_DIMENSION_FIELDS.get(dimension)
    if spec is None:
        return []
    return [ind["nome"] for ind in spec["indicadores"]]
