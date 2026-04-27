"""Phase 4 (R4.1) — Report template catalog.

Static metadata for the four MVP-blessed templates referenced in the
roadmap:

    - mensal_comercial   — sales / commercial monthly readout
    - estoque_critico    — inventory health snapshot
    - cotacoes_do_mes    — RFQ / supply procurement digest
    - caixa_semanal      — finance / cash position weekly

Each template declares which Postgres RPC produces its KPI block and a
short LLM system prompt that explains tone & structure. Anything richer
(per-tenant overrides, Langfuse-managed prompts) can be layered on top
later — the loader in :mod:`report_module` will prefer Langfuse when a
matching prompt exists.

Public surface:

    REPORT_TEMPLATES: dict[str, ReportTemplate]
    list_templates() -> list[dict[str, Any]]
    get_template(template_id: str) -> ReportTemplate
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ────────────────────────────────────────────────────────────────────────
# Template definitions
# ────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ReportTemplate:
    id: str
    title: str
    description: str
    domain: str  # comercial | estoque | supply | financeiro
    indicator_rpc: str
    rpc_schema: str = "analytics_v2"
    default_period: str = "30d"
    default_format: str = "pdf"
    tier_required: str = "BASIC"
    system_prompt: str = ""
    sections: list[str] = field(default_factory=list)
    # Optional: include a knowledge-base snippet pulled from
    # `kb_documents` (category='agent_summary' / 'analysis') for the same
    # period so the report can reference recent agent observations.
    include_kb_summaries: bool = True


_PROMPT_MENSAL_COMERCIAL = """\
Você é um analista comercial sênior produzindo um relatório mensal para
um SMB brasileiro. Use português do Brasil, tom executivo e direto. A
saída deve ser Markdown bem estruturado com cabeçalhos H2/H3, parágrafos
curtos e listas. Inclua:
1. Sumário executivo (3 frases)
2. Indicadores chave (tabela markdown)
3. Destaques e alertas
4. Recomendações para o próximo período (máx. 5 itens acionáveis)
Não invente números — use apenas os indicadores fornecidos.
"""


_PROMPT_ESTOQUE_CRITICO = """\
Você é um especialista em supply chain produzindo um diagnóstico de
estoque crítico para um SMB brasileiro. Use português do Brasil. A
saída deve ser Markdown com:
1. Resumo da saúde do estoque (1 parágrafo)
2. Indicadores chave (tabela markdown — cobertura, giro, stockout)
3. SKUs em risco (se houver no contexto)
4. Recomendações operacionais (até 5 itens)
Não invente SKUs ou números — use apenas o que foi fornecido.
"""


_PROMPT_COTACOES_DO_MES = """\
Você é um analista de procurement produzindo um digest mensal de
cotações e compras para um SMB brasileiro. Use português do Brasil. A
saída em Markdown deve conter:
1. Sumário (1 parágrafo)
2. Indicadores chave (tabela: RFQs abertas, taxa de resposta, lead-time
   médio, concentração top-5)
3. Movimentações relevantes do período
4. Próximos passos / recomendações
Use apenas os indicadores fornecidos.
"""


_PROMPT_CAIXA_SEMANAL = """\
Você é um controller financeiro produzindo um relatório semanal de
posição de caixa para um SMB brasileiro. Use português do Brasil. A
saída em Markdown deve conter:
1. Resumo executivo (3 frases sobre fluxo da semana)
2. Indicadores chave (tabela: receita líquida, custo total, margem,
   ticket médio)
3. Alertas e variações relevantes vs. período anterior
4. Recomendações (até 5 itens acionáveis)
Use apenas os indicadores fornecidos.
"""


REPORT_TEMPLATES: dict[str, ReportTemplate] = {
    "mensal_comercial": ReportTemplate(
        id="mensal_comercial",
        title="Mensal Comercial",
        description="Relatório mensal de vendas, ticket, retenção e churn.",
        domain="comercial",
        indicator_rpc="get_commercial_indicators",
        default_period="30d",
        default_format="pdf",
        tier_required="BASIC",
        system_prompt=_PROMPT_MENSAL_COMERCIAL,
        sections=["sumario", "indicadores", "destaques", "recomendacoes"],
    ),
    "estoque_critico": ReportTemplate(
        id="estoque_critico",
        title="Estoque Crítico",
        description="Diagnóstico de saúde de estoque, cobertura e SKUs em risco.",
        domain="estoque",
        indicator_rpc="get_inventory_indicators",
        default_period="30d",
        default_format="pdf",
        tier_required="BASIC",
        system_prompt=_PROMPT_ESTOQUE_CRITICO,
        sections=["sumario", "indicadores", "skus_risco", "recomendacoes"],
    ),
    "cotacoes_do_mes": ReportTemplate(
        id="cotacoes_do_mes",
        title="Cotações do Mês",
        description="Digest de RFQs, fornecedores e compras do período.",
        domain="supply",
        indicator_rpc="get_supply_indicators",
        default_period="30d",
        default_format="pdf",
        tier_required="BASIC",
        system_prompt=_PROMPT_COTACOES_DO_MES,
        sections=["sumario", "indicadores", "movimentacoes", "proximos_passos"],
    ),
    "caixa_semanal": ReportTemplate(
        id="caixa_semanal",
        title="Caixa Semanal",
        description="Posição de caixa semanal: receita, custos, margem e alertas.",
        domain="financeiro",
        indicator_rpc="get_finance_indicators",
        default_period="7d",
        default_format="pdf",
        tier_required="BASIC",
        system_prompt=_PROMPT_CAIXA_SEMANAL,
        sections=["sumario", "indicadores", "alertas", "recomendacoes"],
    ),
}


def list_templates() -> list[dict[str, Any]]:
    """Public-facing template catalog (used by REST + MCP)."""
    return [
        {
            "id":            t.id,
            "title":         t.title,
            "description":   t.description,
            "domain":        t.domain,
            "default_period": t.default_period,
            "default_format": t.default_format,
            "tier_required": t.tier_required,
            "sections":      list(t.sections),
        }
        for t in REPORT_TEMPLATES.values()
    ]


def get_template(template_id: str) -> ReportTemplate:
    tpl = REPORT_TEMPLATES.get(template_id)
    if tpl is None:
        raise KeyError(f"Unknown report template '{template_id}'")
    return tpl


SUPPORTED_FORMATS = ("markdown", "pdf", "xlsx", "gdoc", "gsheet")


def validate_format(fmt: str) -> str:
    f = (fmt or "").strip().lower()
    if f not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported format '{fmt}'. Supported: {SUPPORTED_FORMATS}")
    return f
