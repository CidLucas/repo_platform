"""
Deterministic function registry for routine step execution.

Each function is async, receives resolved inputs + client_id, and returns
a dict of named outputs that merge into the shared routine execution state.

Registration:
    @register("namespace.function_name")
    async def my_fn(inputs: dict, client_id: str) -> dict: ...

Calling from the runner:
    from agent_api.core.routine_functions import call as call_function
    outputs = await call_function("analytics.query_inactive_clients", inputs, client_id)
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)

# async fn(inputs: dict, client_id: str) -> dict
FunctionHandler = Callable[[dict, str], Awaitable[dict]]

_REGISTRY: dict[str, FunctionHandler] = {}
_METADATA: dict[str, dict] = {}


def _make_label(name: str) -> str:
    ns, _, fn = name.partition(".")
    return f"{ns.title()} › {fn.replace('_', ' ').title()}"


def register(
    name: str,
    *,
    description: str = "",
    inputs: list[dict] | None = None,
    outputs: list[dict] | None = None,
) -> Callable[[FunctionHandler], FunctionHandler]:
    """Decorator to register a deterministic function under a dotted name."""
    def decorator(fn: FunctionHandler) -> FunctionHandler:
        _REGISTRY[name] = fn
        doc_first_line = (fn.__doc__ or "").strip().split("\n")[0].strip()
        _METADATA[name] = {
            "id": name,
            "label": _make_label(name),
            "description": description or doc_first_line,
            "inputs": inputs or [],
            "outputs": outputs or [],
        }
        return fn
    return decorator


async def call(name: str, inputs: dict, client_id: str) -> dict:
    """Call a registered function by name. Raises KeyError if unknown."""
    fn = _REGISTRY.get(name)
    if fn is None:
        raise KeyError(f"Unknown routine function: '{name}'. Available: {list(_REGISTRY)}")
    try:
        result = await fn(inputs, client_id)
        return result if isinstance(result, dict) else {"result": result}
    except Exception:
        logger.exception("[routine_fn] %s failed for client %s", name, client_id)
        raise


def list_functions() -> list[str]:
    return list(_REGISTRY)


def list_functions_with_meta() -> list[dict]:
    return [_METADATA.get(k, {"id": k, "label": k, "description": "", "inputs": [], "outputs": []}) for k in sorted(_REGISTRY)]


# ---------------------------------------------------------------------------
# MCP tool helper — shared by functions that delegate to the tool pool
# ---------------------------------------------------------------------------


async def _call_mcp_tool(tool_name: str, args: dict) -> str:
    """Call an MCP tool and return the text output string."""
    from agent_api.core.factory import get_mcp_executor

    executor = get_mcp_executor()
    mcp_mgr = await executor._get_mcp_manager()  # noqa: SLF001
    raw = await mcp_mgr.call_tool(tool_name, args)

    if hasattr(raw, "content") and raw.content:
        return "\n".join(
            item.text if hasattr(item, "text") else str(item)
            for item in raw.content
        )
    return str(raw)


# ---------------------------------------------------------------------------
# analytics.* — deterministic queries on the analytics schema
# ---------------------------------------------------------------------------


@register(
    "analytics.query_inactive_clients",
    description="Lista clientes ativos nos últimos N meses mas sem compra por M dias — candidatos a reengajamento.",
    inputs=[
        {"key": "lookback_months", "type": "int", "description": "Janela de atividade (meses)", "default": 3, "required": False},
        {"key": "days_inactive", "type": "int", "description": "Mínimo de dias sem pedido", "default": 14, "required": False},
    ],
    outputs=[
        {"key": "client_list", "type": "list", "description": "Lista de clientes inativos da dim_clientes"},
    ],
)
async def _query_inactive_clients(inputs: dict, client_id: str) -> dict:
    """
    Query clients active within the last N months but without a purchase
    in the last M days — the re-engagement candidate list.

    inputs:
        lookback_months (int, default 3)  — activity window
        days_inactive   (int, default 14) — minimum days since last purchase

    outputs:
        client_list — list of client dicts from dim_clientes
    """
    from blu_supabase_client import get_supabase_client

    lookback_months = int(inputs.get("lookback_months", 3))
    days_inactive = int(inputs.get("days_inactive", 14))
    lookback_days = lookback_months * 30

    db = get_supabase_client(use_service_role=True)

    resp = await asyncio.to_thread(
        lambda: db.schema("analytics_v2")
        .table("dim_clientes")
        .select(
            "client_id, nome, telefone, ticket_medio, "
            "dias_recencia, frequencia_mensal, nivel_cluster, total_pedidos, "
            "endereco_cidade, endereco_uf"
        )
        .eq("client_id", client_id)
        .lte("dias_recencia", lookback_days)
        .gte("dias_recencia", days_inactive)
        .order("dias_recencia")
        .limit(200)
        .execute()
    )

    client_list: list[dict[str, Any]] = resp.data or []
    logger.info(
        "[routine_fn] query_inactive_clients: client=%s found=%d "
        "(active<=%dd, inactive>=%dd)",
        client_id, len(client_list), lookback_days, days_inactive,
    )
    return {"client_list": client_list}


@register(
    "analytics.gather_client_context",
    description="Enriquece lista de clientes com rótulo de cluster, ticket formatado e dias sem compra.",
    inputs=[
        {"key": "client_list", "type": "list", "description": "Lista de clientes (use {{client_list}})", "required": True},
    ],
    outputs=[
        {"key": "client_context", "type": "list", "description": "Lista enriquecida com cluster_label, ticket_formatado e dias_inativo"},
    ],
)
async def _gather_client_context(inputs: dict, client_id: str) -> dict:
    """
    Enrich a client_list with human-readable cluster labels and formatted
    ticket values. Fetches no additional DB rows — pure transformation.

    inputs:
        client_list — list of client dicts (from query_inactive_clients)

    outputs:
        client_context — same list, enriched with cluster_label, ticket_formatado,
                         dias_inativo
    """
    client_list: list[dict] = inputs.get("client_list", [])
    if not client_list:
        return {"client_context": []}

    _CLUSTER_LABELS: dict[str, str] = {
        "champions": "cliente fiel de alto valor",
        "loyal_customers": "cliente recorrente",
        "potential_loyalists": "cliente promissor",
        "at_risk": "cliente em risco de churn",
        "cant_lose_them": "cliente valioso perdendo frequência",
        "hibernating": "cliente inativo há muito tempo",
        "new_customers": "cliente novo",
    }

    enriched: list[dict[str, Any]] = []
    for c in client_list:
        cluster = c.get("nivel_cluster") or ""
        ticket = c.get("ticket_medio") or 0
        enriched.append({
            **c,
            "cluster_label": _CLUSTER_LABELS.get(cluster, cluster),
            "dias_inativo": c.get("dias_recencia"),
            "ticket_formatado": f"R$ {ticket:.0f}",
        })

    logger.info("[routine_fn] gather_client_context: enriched %d clients", len(enriched))
    return {"client_context": enriched}


@register(
    "analytics.generate_context_report",
    description="Gera relatório completo de contexto: KPIs, tendências e rankings. Salva em Storage e indexa no RAG.",
    inputs=[],
    outputs=[
        {"key": "context_report_summary", "type": "str", "description": "Resumo legível do relatório gerado"},
        {"key": "report_upserted", "type": "bool", "description": "True se o relatório foi indexado no RAG"},
    ],
)
async def _generate_context_report(inputs: dict, client_id: str) -> dict:
    """
    Run the full context report pipeline for this client (KPI metrics,
    trends, top lists, upload to Storage + embed in RAG).

    outputs:
        context_report_summary — human-readable summary string
        report_upserted        — bool, True if uploaded to vector DB
    """
    from blu_agent_framework.routines.context_report import run_for_client

    result = await run_for_client(client_id)

    if result.error:
        logger.warning(
            "[routine_fn] generate_context_report failed for %s: %s",
            client_id, result.error,
        )
        return {"context_report_summary": f"Falhou: {result.error}", "report_upserted": False}

    summary = (
        f"Context report gerado: {result.report_chars} chars, "
        f"{result.metrics_count} métricas, "
        f"{'indexado no RAG' if result.upserted else 'não indexado'}."
    )
    logger.info("[routine_fn] generate_context_report: %s", summary)
    return {"context_report_summary": summary, "report_upserted": result.upserted}


# ---------------------------------------------------------------------------
# web.* — website crawl via MCP tool pool (crawl4ai + playwright)
# ---------------------------------------------------------------------------


@register(
    "web.extract_company_context",
    description="Faz crawl do site do cliente e extrai informações estruturadas sobre a empresa.",
    inputs=[
        {"key": "url", "type": "str", "description": "URL do site (opcional — usa website_url do CRM se omitido)", "required": False},
    ],
    outputs=[
        {"key": "website_content", "type": "dict", "description": "Informações extraídas do site (nome, produtos, diferenciais, etc.)"},
    ],
)
async def _extract_company_context(inputs: dict, client_id: str) -> dict:
    """
    Crawl the client's website and extract structured company context.
    Delegates to the extract_company_context MCP tool (crawl4ai/playwright).

    If no URL is provided in inputs, falls back to clientes_blu.website_url.

    inputs:
        url (str, optional) — website URL

    outputs:
        website_content — dict with extracted company info
    """
    from blu_supabase_client import get_supabase_client

    url: str = inputs.get("url", "")

    if not url:
        db = get_supabase_client(use_service_role=True)
        row = await asyncio.to_thread(
            lambda: db.table("clientes_blu")
            .select("company_profile")
            .eq("client_id", client_id)
            .maybe_single()
            .execute()
        )
        if row.data:
            profile = row.data.get("company_profile") or {}
            url = profile.get("website") or profile.get("website_url") or profile.get("site") or ""

    if not url:
        logger.warning("[routine_fn] extract_company_context: no URL for client %s", client_id)
        return {"website_content": {}}

    try:
        raw = await _call_mcp_tool("extract_company_context", {"url": url})
        try:
            website_content: dict = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            website_content = {"raw_text": raw, "url": url}

        logger.info("[routine_fn] extract_company_context: crawled %s", url)
        return {"website_content": website_content}

    except Exception as exc:
        logger.warning("[routine_fn] extract_company_context failed for %s: %s", url, exc)
        return {"website_content": {"url": url, "error": str(exc)}}


# ---------------------------------------------------------------------------
# knowledge.* — masterprompt / business context map
# ---------------------------------------------------------------------------

_MASTERPROMPT_TEMPLATE = """\
# Business Context Map

## Identity
<!-- Company name, industry, size, core products/services, differentiators -->

## Key Processes
<!-- Core operational flows: ordering, delivery, billing, etc. -->

## Data & Documents
<!-- Connected data sources, knowledge base documents, key metrics tracked -->

## Communication Preferences
<!-- Language, tone (formal/informal), preferred channels, report preferences -->

## Team & Stakeholders
<!-- Key roles, decision makers, contacts -->

## Context Snippets
<!-- Recent strategic discussions, active projects, known constraints -->

## Agent Interaction Patterns
<!-- Frequently requested analyses, common workflows, custom terminology -->
"""


@register(
    "knowledge.get_masterprompt",
    description="Carrega o Business Context Map do cliente armazenado no Storage. Retorna template vazio se não existir.",
    inputs=[],
    outputs=[
        {"key": "masterprompt", "type": "str", "description": "Conteúdo markdown do Business Context Map"},
        {"key": "masterprompt_exists", "type": "bool", "description": "True se o documento já existe no Storage"},
    ],
)
async def _get_masterprompt(inputs: dict, client_id: str) -> dict:
    """
    Fetch the Business Context Map (masterprompt) from Supabase Storage.
    Returns an empty template if the document does not exist yet.

    outputs:
        masterprompt        — markdown string (existing or empty template)
        masterprompt_exists — bool
    """
    from blu_supabase_client import get_supabase_client

    db = get_supabase_client(use_service_role=True)
    storage_path = f"{client_id}/context_map.md"

    try:
        raw = await asyncio.to_thread(
            lambda: db.storage.from_("knowledge-base").download(storage_path)
        )
        content = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
        logger.info(
            "[routine_fn] get_masterprompt: loaded %d chars for %s",
            len(content), client_id,
        )
        return {"masterprompt": content, "masterprompt_exists": True}

    except Exception:
        logger.info(
            "[routine_fn] get_masterprompt: no existing doc for %s, returning template",
            client_id,
        )
        return {"masterprompt": _MASTERPROMPT_TEMPLATE, "masterprompt_exists": False}


# ---------------------------------------------------------------------------
# insights.* — daily insight generation
# ---------------------------------------------------------------------------

@register(
    "analytics.get_kpi_snapshots",
    description="Busca KPIs MTD (mês até hoje) com comparação ao mesmo período do mês anterior e média dos últimos 3 meses.",
    inputs=[],
    outputs=[
        {"key": "kpi_data", "type": "dict", "description": "KPIs por dimensão com current_value, mom_pct e vs_3m_avg_pct"},
        {"key": "missing_integrations", "type": "list", "description": "Dimensões sem integração conectada"},
        {"key": "kpi_summary", "type": "str", "description": "Resumo markdown formatado para uso em alertas"},
    ],
)
async def _get_kpi_snapshots(inputs: dict, client_id: str) -> dict:
    """
    Fetch MTD KPI comparison via get_kpi_mtd_comparison RPC.

    Compares current-month-to-date against the same day range in each of the
    prior 3 months — proper apples-to-apples, following context_report.py patterns.
    """
    from blu_supabase_client import get_supabase_client

    db = get_supabase_client(use_service_role=True)

    resp = await asyncio.to_thread(
        lambda: db.schema("analytics_v2")
        .rpc("get_kpi_mtd_comparison", {"p_client_id": client_id})
        .execute()
    )
    rows: list[dict] = resp.data or []

    # Pivot rows into dimension → kpi → metrics dict
    kpi_data: dict = {}
    for row in rows:
        dim = row["dimension"]
        kpi = row["kpi"]
        if dim not in kpi_data:
            kpi_data[dim] = {}
        kpi_data[dim][kpi] = {
            "label": row.get("label"),
            "unit": row.get("unit"),
            "current_value": row.get("current_value"),
            "prev_period_value": row.get("prev_period_value"),
            "avg_3m": row.get("avg_3m"),
            "mom_pct": row.get("mom_pct"),
            "vs_3m_avg_pct": row.get("vs_3m_avg_pct"),
        }

    # Inventory and supply have no MTD RPC — mark as integration_missing
    missing_integrations: list[str] = []
    for dim in ("inventory", "supply"):
        if dim not in kpi_data:
            kpi_data[dim] = {"integration_missing": True}
            missing_integrations.append(dim)

    logger.info(
        "[routine_fn] get_kpi_snapshots: client=%s dimensions=%s missing=%s",
        client_id, list(kpi_data), missing_integrations or "none",
    )
    return {
        "kpi_data": kpi_data,
        "missing_integrations": missing_integrations,
        "kpi_summary": _format_kpi_summary(kpi_data),
    }


@register(
    "insights.generate_from_kpis",
    description="Chama o LLM diretamente para gerar uma lista de insights acionáveis a partir dos KPIs. Retorna JSON array sem depender do grafo de agentes.",
    inputs=[
        {"key": "kpi_data",     "type": "dict", "description": "KPIs por dimensão (usa {{kpi_data}})",     "required": True},
        {"key": "nome_empresa", "type": "str",  "description": "Nome da empresa para contexto",            "required": False},
    ],
    outputs=[
        {"key": "insights", "type": "list", "description": "Lista de insights: {dimension, kpi, title, observation, severity, recommendation?, metric_value?, baseline_value?, variance_pct?}"},
    ],
)
async def _generate_insights_from_kpis(inputs: dict, client_id: str) -> dict:
    """
    Direct LLM call to produce a structured JSON array of insights from KPI data.
    Uses a deterministic prompt that enforces JSON-only output — more reliable
    than invoking the financeiro specialist agent for structured data generation.

    outputs:
        insights — list of insight dicts ready for storage.save_insights
    """
    import re

    from blu_llm_service import ModelTier, get_model
    from langchain_core.messages import HumanMessage, SystemMessage

    kpi_data: dict = inputs.get("kpi_data") or {}
    nome_empresa: str = str(inputs.get("nome_empresa") or "a empresa")

    system_prompt = (
        "Você é um analista de negócios. Analise os KPIs fornecidos e gere insights acionáveis.\n\n"
        "Para cada insight inclua TODOS estes campos:\n"
        "  dimension: uma de [finance, commercial, inventory, supply]\n"
        "  kpi: nome do indicador (string curta)\n"
        "  title: título do insight (máx 100 chars)\n"
        "  observation: o que os dados mostram (1-3 frases)\n"
        "  recommendation: ação recomendada (1-2 frases)\n"
        "  severity: info | warning | error\n"
        "  metric_value: valor atual numérico ou null\n"
        "  baseline_value: valor de referência numérico ou null\n"
        "  variance_pct: variação percentual numérica ou null\n\n"
        "Se uma dimensão tiver 'integration_missing: true', gere um insight severity='info' "
        "indicando que aquela integração ainda não foi configurada.\n\n"
        "Gere entre 3 e 8 insights priorizados por impacto.\n"
        "Responda SOMENTE com um JSON array. Nenhum texto antes ou depois."
    )
    user_msg = f"Empresa: {nome_empresa}\n\nKPIs:\n{json.dumps(kpi_data, ensure_ascii=False, indent=2)}"

    llm = get_model(tier=ModelTier.DEFAULT)
    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_msg),
        ])
        result_text: str = response.content if hasattr(response, "content") else str(response)
    except Exception as exc:
        logger.warning("[routine_fn] insights.generate_from_kpis: LLM call failed for %s: %s", client_id, exc)
        return {"insights": []}

    # Try direct JSON parse first
    stripped = result_text.strip()
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, list):
            logger.info("[routine_fn] insights.generate_from_kpis: generated %d insights for %s", len(parsed), client_id)
            return {"insights": parsed}
    except (json.JSONDecodeError, ValueError):
        pass

    # Fall back to regex extraction of JSON array
    arr_match = re.search(r"\[[\s\S]+\]", stripped)
    if arr_match:
        try:
            parsed = json.loads(arr_match.group(0))
            if isinstance(parsed, list):
                logger.info("[routine_fn] insights.generate_from_kpis: extracted %d insights for %s", len(parsed), client_id)
                return {"insights": parsed}
        except (json.JSONDecodeError, ValueError):
            pass

    logger.warning("[routine_fn] insights.generate_from_kpis: could not parse LLM response for %s", client_id)
    return {"insights": []}


def _fmt_currency(val: float | int) -> str:
    """Format a BRL currency value with k/M suffix."""
    if abs(val) >= 1_000_000:
        return f"R$ {val / 1_000_000:.1f}M"
    if abs(val) >= 1_000:
        return f"R$ {val:,.0f}".replace(",", ".")
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_change(pct: float | None) -> str:
    """Format a % change with directional arrow (▲/▼/→)."""
    if pct is None:
        return ""
    arrow = "▲" if pct > 0 else ("▼" if pct < 0 else "→")
    sign = "+" if pct >= 0 else ""
    return f"{arrow}{sign}{pct:.1f}%"


def _format_kpi_summary(kpi_data: dict) -> str:
    """
    Build a compact markdown summary from MTD KPI comparison data.

    Phrase pattern (following context_report.py):
        value · ▲/▼ mom_pct% vs mês ant. (prev_value) · X% acima/abaixo da média 3m (avg_value)
    """
    _DIM_LABELS = {
        "finance": "💰 Financeiro",
        "commercial": "👥 Comercial",
        "inventory": "📦 Estoque",
        "supply": "🚚 Compras",
    }
    lines = ["**KPIs — Mês até hoje (MTD):**"]

    for dim in ("finance", "commercial", "inventory", "supply"):
        data = kpi_data.get(dim, {})
        label = _DIM_LABELS.get(dim, dim.title())

        if not data or data.get("integration_missing"):
            lines.append(f"{label}: integração não conectada")
            continue

        parts: list[str] = []

        if dim == "finance":
            rec = data.get("receita_liquida", {})
            cur = rec.get("current_value")
            if not cur:
                parts.append("sem movimentação no mês")
            else:
                phrase = _fmt_currency(cur)
                mom = rec.get("mom_pct")
                prev = rec.get("prev_period_value")
                vs3 = rec.get("vs_3m_avg_pct")
                avg3 = rec.get("avg_3m")
                if mom is not None and prev is not None:
                    phrase += f" · {_fmt_change(mom)} vs mês ant. ({_fmt_currency(prev)})"
                if vs3 is not None and avg3 is not None:
                    direction = "acima" if vs3 > 0 else "abaixo"
                    phrase += f" · {abs(vs3):.1f}% {direction} da média 3m ({_fmt_currency(avg3)})"
                parts.append(f"{phrase} receita MTD")

            tkt = data.get("ticket_medio", {})
            t_cur = tkt.get("current_value")
            if t_cur:
                t_str = _fmt_currency(t_cur)
                t_mom = tkt.get("mom_pct")
                if t_mom is not None:
                    t_str += f" ({_fmt_change(t_mom)})"
                parts.append(f"{t_str} ticket médio")

        elif dim == "commercial":
            ped = data.get("total_pedidos", {})
            cli = data.get("clientes_ativos", {})
            nov = data.get("novos_clientes", {})
            rec = data.get("taxa_recorrencia_perc", {})

            ped_cur = int(ped.get("current_value") or 0)
            cli_cur = int(cli.get("current_value") or 0)

            if ped_cur == 0 and cli_cur == 0:
                parts.append("sem pedidos no mês")
            else:
                ped_str = f"{ped_cur} pedido{'s' if ped_cur != 1 else ''}"
                ped_mom = ped.get("mom_pct")
                if ped_mom is not None:
                    ped_str += f" ({_fmt_change(ped_mom)})"
                parts.append(ped_str)

                if cli_cur:
                    cli_str = f"{cli_cur} cliente{'s' if cli_cur != 1 else ''} ativo{'s' if cli_cur != 1 else ''}"
                    cli_mom = cli.get("mom_pct")
                    if cli_mom is not None:
                        cli_str += f" ({_fmt_change(cli_mom)})"
                    parts.append(cli_str)

                nov_cur = int(nov.get("current_value") or 0)
                if nov_cur:
                    parts.append(f"{nov_cur} novo{'s' if nov_cur != 1 else ''}")

                rec_cur = rec.get("current_value")
                if rec_cur is not None and cli_cur > 1:
                    parts.append(f"{rec_cur:.1f}% recorrência")

        lines.append(f"{label}: {' | '.join(parts) if parts else 'sem dados'}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# analytics.get_pending_approvals — pending decisions
# ---------------------------------------------------------------------------


@register(
    "analytics.get_pending_approvals",
    description="Lista decisões pendentes no painel do cliente, ignorando itens em snooze.",
    inputs=[
        {"key": "limit", "type": "int", "description": "Máximo de itens retornados", "default": 10, "required": False},
    ],
    outputs=[
        {"key": "pending_count", "type": "int", "description": "Total de itens pendentes"},
        {"key": "pending_items", "type": "list", "description": "Lista de itens pendentes"},
        {"key": "pending_summary", "type": "str", "description": "Resumo markdown formatado para usar no corpo de alertas"},
    ],
)
async def _get_pending_approvals(inputs: dict, client_id: str) -> dict:
    """
    Fetch approval_requests with status='pending', excluding snoozed items.
    Returns a count, raw list, and pre-formatted markdown summary.
    """
    from datetime import datetime, timezone

    from blu_supabase_client import get_supabase_client

    limit = int(inputs.get("limit", 10))
    now_z = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    db = get_supabase_client(use_service_role=True)

    resp = await asyncio.to_thread(
        lambda: db.table("approval_requests")
        .select("id, title, body, priority, action_type, agent_slug, created_at")
        .eq("client_id", client_id)
        .eq("status", "pending")
        .neq("action_type", "routine_alert")
        .or_(f"snooze_until.is.null,snooze_until.lt.{now_z}")
        .order("created_at", desc=False)
        .limit(limit)
        .execute()
    )

    items: list[dict] = resp.data or []
    count = len(items)

    if not count:
        summary = "✅ Nenhuma decisão pendente no momento."
    else:
        _ICONS = {"high": "🔴", "normal": "🟡", "low": "⚪"}
        header = f"**{count} ite{'m' if count == 1 else 'ns'} aguardando decisão:**"
        lines_md = [header]
        for item in items:
            title = item.get("title") or item.get("action_type", "Decisão")
            icon = _ICONS.get(item.get("priority", "normal"), "🟡")
            agent = item.get("agent_slug", "")
            lines_md.append(f"{icon} {title}" + (f" _{agent}_" if agent else ""))
        summary = "\n".join(lines_md)

    logger.info("[routine_fn] get_pending_approvals: client=%s count=%d", client_id, count)
    return {"pending_count": count, "pending_items": items, "pending_summary": summary}


# ---------------------------------------------------------------------------
# analytics.get_overdue_approvals — decisions overdue by N hours
# ---------------------------------------------------------------------------


@register(
    "analytics.get_overdue_approvals",
    description="Lista decisões pendentes há mais de N horas, ignorando snooze. Retorna prioridade do alerta.",
    inputs=[
        {"key": "threshold_hours", "type": "int", "description": "Mínimo de horas sem decisão para considerar atrasado", "default": 24, "required": False},
    ],
    outputs=[
        {"key": "overdue_count", "type": "int", "description": "Total de itens atrasados"},
        {"key": "overdue_items", "type": "list", "description": "Lista de itens atrasados"},
        {"key": "overdue_summary", "type": "str", "description": "Resumo markdown formatado"},
        {"key": "alert_priority", "type": "str", "description": "'high' se há itens, 'low' se nenhum"},
    ],
)
async def _get_overdue_approvals(inputs: dict, client_id: str) -> dict:
    """
    Fetch approval_requests pending longer than threshold_hours, skipping snoozed.
    Returns alert_priority='high' when items exist, 'low' otherwise.
    """
    from datetime import datetime, timedelta, timezone

    from blu_supabase_client import get_supabase_client

    threshold_hours = int(inputs.get("threshold_hours", 24))
    now = datetime.now(timezone.utc)
    cutoff_z = (now - timedelta(hours=threshold_hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    now_z = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    db = get_supabase_client(use_service_role=True)

    resp = await asyncio.to_thread(
        lambda: db.table("approval_requests")
        .select("id, title, body, priority, action_type, agent_slug, created_at")
        .eq("client_id", client_id)
        .eq("status", "pending")
        .lt("created_at", cutoff_z)
        .or_(f"snooze_until.is.null,snooze_until.lt.{now_z}")
        .order("created_at", desc=False)
        .limit(20)
        .execute()
    )

    items: list[dict] = resp.data or []
    count = len(items)

    if not count:
        summary = f"✅ Nenhuma decisão pendente há mais de {threshold_hours}h."
        priority = "low"
    else:
        _ICONS = {"high": "🔴", "normal": "🟡", "low": "⚪"}
        header = f"⏳ **{count} decisã{'o' if count == 1 else 'ões'} aguardando há +{threshold_hours}h:**"
        lines_md = [header]
        for item in items:
            title = item.get("title") or item.get("action_type", "Decisão")
            icon = _ICONS.get(item.get("priority", "normal"), "🟡")
            agent = item.get("agent_slug", "")
            lines_md.append(f"{icon} {title}" + (f" _{agent}_" if agent else ""))
        summary = "\n".join(lines_md)
        priority = "high"

    logger.info("[routine_fn] get_overdue_approvals: client=%s overdue=%d threshold=%dh", client_id, count, threshold_hours)
    return {"overdue_count": count, "overdue_items": items, "overdue_summary": summary, "alert_priority": priority}


# ---------------------------------------------------------------------------
# integrations.check_health — sync status of all connected data sources
# ---------------------------------------------------------------------------


@register(
    "integrations.check_health",
    description="Verifica se todas as fontes de dados estão sincronizadas e sem erros. Retorna relatório e prioridade do alerta.",
    inputs=[
        {"key": "stale_hours", "type": "int", "description": "Horas sem sync para considerar desatualizado", "default": 8, "required": False},
    ],
    outputs=[
        {"key": "healthy_count", "type": "int", "description": "Fontes saudáveis"},
        {"key": "problem_count", "type": "int", "description": "Fontes com problema (erro ou desatualizada)"},
        {"key": "health_report", "type": "str", "description": "Relatório markdown formatado"},
        {"key": "alert_priority", "type": "str", "description": "'high' se há problemas, 'low' se tudo ok"},
    ],
)
async def _check_integration_health(inputs: dict, client_id: str) -> dict:
    """
    Query client_data_sources for sync_status and last_synced_at.
    Flags sources that are errored or stale (last_synced_at older than stale_hours).
    """
    from datetime import datetime, timedelta, timezone

    from blu_supabase_client import get_supabase_client

    stale_hours = int(inputs.get("stale_hours", 8))
    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(hours=stale_hours)
    db = get_supabase_client(use_service_role=True)

    resp = await asyncio.to_thread(
        lambda: db.table("client_data_sources")
        .select("source_type, resource_type, sync_status, last_synced_at, error_message")
        .eq("client_id", client_id)
        .execute()
    )
    sources: list[dict] = resp.data or []

    if not sources:
        return {
            "healthy_count": 0,
            "problem_count": 0,
            "health_report": "ℹ️ Nenhuma fonte de dados conectada.",
            "alert_priority": "low",
        }

    healthy, problems = [], []
    for src in sources:
        label = f"{src.get('source_type', '?')} / {src.get('resource_type', '?')}"
        status = src.get("sync_status", "")
        last_sync_raw = src.get("last_synced_at")
        error = src.get("error_message")

        is_errored = status not in ("success", "ok", None, "")
        is_stale = False
        if last_sync_raw:
            try:
                last_sync = datetime.fromisoformat(last_sync_raw.replace("Z", "+00:00"))
                is_stale = last_sync < stale_cutoff
            except ValueError:
                pass

        if is_errored or is_stale:
            reason = error or ("sem sync há mais de " + str(stale_hours) + "h" if is_stale else status)
            problems.append(f"⚠️ {label}: {reason}")
        else:
            since = ""
            if last_sync_raw:
                try:
                    last_sync = datetime.fromisoformat(last_sync_raw.replace("Z", "+00:00"))
                    mins_ago = int((now - last_sync).total_seconds() / 60)
                    since = f" (há {mins_ago}min)"
                except ValueError:
                    pass
            healthy.append(f"✅ {label}{since}")

    lines_md: list[str] = []
    if problems:
        lines_md.append(f"**🔌 Sincronização — {len(problems)} problema(s):**")
        lines_md.extend(problems)
        if healthy:
            lines_md.append(f"\n_OK: {', '.join(s.replace('✅ ', '') for s in healthy)}_")
        alert_priority = "high"
    else:
        lines_md.append(f"✅ **Todas as {len(healthy)} fonte(s) sincronizadas.**")
        lines_md.extend(healthy)
        alert_priority = "low"

    logger.info(
        "[routine_fn] check_integration_health: client=%s healthy=%d problems=%d",
        client_id, len(healthy), len(problems),
    )
    return {
        "healthy_count": len(healthy),
        "problem_count": len(problems),
        "health_report": "\n".join(lines_md),
        "alert_priority": alert_priority,
    }


# ---------------------------------------------------------------------------
# analytics.get_daily_activity — what happened today
# ---------------------------------------------------------------------------


@register(
    "analytics.get_daily_activity",
    description="Resume a atividade do dia: rotinas concluídas, decisões tomadas e ingestões finalizadas.",
    inputs=[],
    outputs=[
        {"key": "routines_completed", "type": "int", "description": "Rotinas concluídas hoje"},
        {"key": "approvals_resolved", "type": "int", "description": "Decisões tomadas hoje"},
        {"key": "syncs_completed", "type": "int", "description": "Sincronizações de dados finalizadas hoje"},
        {"key": "activity_summary", "type": "str", "description": "Resumo markdown do dia"},
    ],
)
async def _get_daily_activity(inputs: dict, client_id: str) -> dict:
    """
    Count routine executions, resolved approvals, and completed data jobs for today.
    """
    from datetime import datetime, timezone

    from blu_supabase_client import get_supabase_client

    today_z = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00Z")
    db = get_supabase_client(use_service_role=True)

    routines_resp, approvals_resp, jobs_resp = await asyncio.gather(
        asyncio.to_thread(
            lambda: db.table("client_routine_executions")
            .select("id", count="exact")
            .eq("client_id", client_id)
            .eq("status", "completed")
            .gte("completed_at", today_z)
            .execute()
        ),
        asyncio.to_thread(
            lambda: db.table("approval_requests")
            .select("id", count="exact")
            .eq("client_id", client_id)
            .eq("status", "approved")
            .gte("decided_at", today_z)
            .execute()
        ),
        asyncio.to_thread(
            lambda: db.schema("analytics_v2")
            .table("reg_jobs")
            .select("job_id", count="exact")
            .eq("client_id", client_id)
            .eq("status", "completed")
            .gte("completed_at", today_z)
            .execute()
        ),
    )

    routines_done = routines_resp.count or 0
    approvals_done = approvals_resp.count or 0
    syncs_done = jobs_resp.count or 0

    parts = []
    if routines_done:
        parts.append(f"✅ {routines_done} rotina{'s' if routines_done != 1 else ''} concluída{'s' if routines_done != 1 else ''}")
    if approvals_done:
        parts.append(f"✔️ {approvals_done} decisã{'o' if approvals_done == 1 else 'ões'} tomada{'s' if approvals_done != 1 else ''}")
    if syncs_done:
        parts.append(f"🔄 {syncs_done} sincronização{'s' if syncs_done != 1 else ''} de dados")

    summary = "**O que aconteceu hoje:**\n" + ("\n".join(parts) if parts else "📭 Nenhuma atividade registrada ainda.")

    logger.info(
        "[routine_fn] get_daily_activity: client=%s routines=%d approvals=%d syncs=%d",
        client_id, routines_done, approvals_done, syncs_done,
    )
    return {
        "routines_completed": routines_done,
        "approvals_resolved": approvals_done,
        "syncs_completed": syncs_done,
        "activity_summary": summary,
    }


# ---------------------------------------------------------------------------
# analytics.get_weekly_activity — what happened this week
# ---------------------------------------------------------------------------


@register(
    "analytics.get_weekly_activity",
    description="Resume a atividade dos últimos 7 dias: rotinas, decisões, dados ingeridos.",
    inputs=[],
    outputs=[
        {"key": "routines_completed", "type": "int", "description": "Rotinas concluídas na semana"},
        {"key": "approvals_resolved", "type": "int", "description": "Decisões tomadas na semana"},
        {"key": "syncs_completed", "type": "int", "description": "Sincronizações finalizadas na semana"},
        {"key": "weekly_activity_summary", "type": "str", "description": "Resumo markdown da semana"},
    ],
)
async def _get_weekly_activity(inputs: dict, client_id: str) -> dict:
    """
    Count routine executions, resolved approvals, and completed data jobs for the last 7 days.
    """
    from datetime import datetime, timedelta, timezone

    from blu_supabase_client import get_supabase_client

    week_ago_z = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00Z")
    db = get_supabase_client(use_service_role=True)

    routines_resp, approvals_resp, jobs_resp = await asyncio.gather(
        asyncio.to_thread(
            lambda: db.table("client_routine_executions")
            .select("id", count="exact")
            .eq("client_id", client_id)
            .eq("status", "completed")
            .gte("completed_at", week_ago_z)
            .execute()
        ),
        asyncio.to_thread(
            lambda: db.table("approval_requests")
            .select("id", count="exact")
            .eq("client_id", client_id)
            .in_("status", ["approved", "rejected"])
            .gte("decided_at", week_ago_z)
            .execute()
        ),
        asyncio.to_thread(
            lambda: db.schema("analytics_v2")
            .table("reg_jobs")
            .select("rows_inserted")
            .eq("client_id", client_id)
            .eq("status", "completed")
            .gte("completed_at", week_ago_z)
            .execute()
        ),
    )

    routines_done = routines_resp.count or 0
    approvals_done = approvals_resp.count or 0
    rows_ingested = sum(r.get("rows_inserted") or 0 for r in (jobs_resp.data or []))

    parts = [
        f"✅ {routines_done} rotina{'s' if routines_done != 1 else ''} automática{'s' if routines_done != 1 else ''} executada{'s' if routines_done != 1 else ''}",
        f"✔️ {approvals_done} decis{'ão' if approvals_done == 1 else 'ões'} processada{'s' if approvals_done != 1 else ''}",
        f"🔄 {rows_ingested:,} linha{'s' if rows_ingested != 1 else ''} de dados ingerida{'s' if rows_ingested != 1 else ''}",
    ]
    summary = "**Resumo da semana:**\n" + "\n".join(parts)

    logger.info(
        "[routine_fn] get_weekly_activity: client=%s routines=%d approvals=%d rows=%d",
        client_id, routines_done, approvals_done, rows_ingested,
    )
    return {
        "routines_completed": routines_done,
        "approvals_resolved": approvals_done,
        "syncs_completed": len(jobs_resp.data or []),
        "weekly_activity_summary": summary,
    }


# ---------------------------------------------------------------------------
# agenda.* — Google Calendar queries (requires integration_tokens for 'google')
# ---------------------------------------------------------------------------


async def _build_calendar_client(client_id: str):
    """
    Load the Google OAuth token for this client and return a GoogleCalendarClient.
    Returns None if Google is not connected or the token is invalid.
    """
    from uuid import UUID

    from blu_google_suite_client import GoogleCalendarClient

    from agent_api.core.factory import get_context_service

    ctx = get_context_service()
    try:
        wrapper = await ctx.get_integration_tokens(UUID(client_id), "google", auto_refresh=True)
    except Exception as exc:
        logger.warning("[routine_fn] calendar: token lookup failed for %s: %s", client_id, exc)
        return None

    if not wrapper or not wrapper.is_valid():
        logger.info("[routine_fn] calendar: no valid Google token for %s", client_id)
        return None

    tokens = wrapper.get_decrypted_tokens()
    return GoogleCalendarClient(access_token=tokens["access_token"])


async def _get_client_calendar_id(client_id: str) -> str:
    """Return the configured calendar_id for this client, defaulting to 'primary'."""
    from blu_supabase_client import get_supabase_client

    db = get_supabase_client(use_service_role=True)
    row = await asyncio.to_thread(
        lambda: db.table("calendar_settings")
        .select("calendar_id")
        .eq("client_id", client_id)
        .eq("enabled", True)
        .maybe_single()
        .execute()
    )
    return (row.data or {}).get("calendar_id") or "primary"


@register(
    "agenda.get_calendar_events",
    description="Busca eventos do Google Calendar para as próximas N horas. Requer Google Calendar conectado.",
    inputs=[
        {"key": "window_hours", "type": "int", "description": "Janela futura em horas", "default": 18, "required": False},
    ],
    outputs=[
        {"key": "calendar_summary", "type": "str", "description": "Lista markdown de eventos do dia"},
        {"key": "event_count", "type": "int", "description": "Número de eventos encontrados"},
    ],
)
async def _get_calendar_events(inputs: dict, client_id: str) -> dict:
    """
    Fetch upcoming Google Calendar events within window_hours from now.
    Returns a formatted markdown list and event count.
    Falls back gracefully when Google Calendar is not connected.
    """
    from datetime import datetime, timedelta, timezone

    window_hours = int(inputs.get("window_hours", 18))
    cal_client = await _build_calendar_client(client_id)

    if not cal_client:
        return {"calendar_summary": "📅 Google Calendar não conectado.", "event_count": 0}

    now = datetime.now(timezone.utc)
    time_max = now + timedelta(hours=window_hours)
    calendar_id = await _get_client_calendar_id(client_id)

    try:
        events = await cal_client.list_events(calendar_id, now, time_max, max_results=20)
    except Exception as exc:
        logger.warning("[routine_fn] get_calendar_events failed for %s: %s", client_id, exc)
        return {"calendar_summary": "📅 Erro ao buscar agenda.", "event_count": 0}

    if not events:
        return {"calendar_summary": "📅 Nenhum evento agendado para hoje.", "event_count": 0}

    lines_md = [f"**📅 Agenda — próximas {window_hours}h:**"]
    for ev in events:
        start_str = ev.start or ""
        try:
            start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            time_label = start_dt.astimezone(timezone.utc).strftime("%H:%M")
        except (ValueError, AttributeError):
            time_label = start_str[:10]
        title = ev.summary or "(sem título)"
        loc = f" — {ev.location}" if ev.location else ""
        lines_md.append(f"🕐 {time_label} {title}{loc}")

    logger.info("[routine_fn] get_calendar_events: client=%s events=%d", client_id, len(events))
    return {"calendar_summary": "\n".join(lines_md), "event_count": len(events)}


@register(
    "agenda.get_upcoming_deadlines",
    description="Busca eventos do Google Calendar nos próximos N dias e classifica por urgência (3/7/15 dias).",
    inputs=[
        {"key": "days_ahead", "type": "int", "description": "Janela de busca em dias", "default": 15, "required": False},
    ],
    outputs=[
        {"key": "deadline_summary", "type": "str", "description": "Lista markdown de prazos por urgência"},
        {"key": "deadline_count", "type": "int", "description": "Total de eventos encontrados"},
    ],
)
async def _get_upcoming_deadlines(inputs: dict, client_id: str) -> dict:
    """
    Fetch Google Calendar events for the next days_ahead days and bucket them
    into urgency tiers (≤3d, ≤7d, ≤15d) for the deadline radar.
    """
    from datetime import datetime, timedelta, timezone

    days_ahead = int(inputs.get("days_ahead", 15))
    cal_client = await _build_calendar_client(client_id)

    if not cal_client:
        return {"deadline_summary": "📅 Google Calendar não conectado.", "deadline_count": 0}

    now = datetime.now(timezone.utc)
    time_max = now + timedelta(days=days_ahead)
    calendar_id = await _get_client_calendar_id(client_id)

    try:
        events = await cal_client.list_events(calendar_id, now, time_max, max_results=50)
    except Exception as exc:
        logger.warning("[routine_fn] get_upcoming_deadlines failed for %s: %s", client_id, exc)
        return {"deadline_summary": "📅 Erro ao buscar prazos.", "deadline_count": 0}

    if not events:
        return {
            "deadline_summary": f"✅ Nenhum compromisso nos próximos {days_ahead} dias.",
            "deadline_count": 0,
        }

    urgent, soon, later = [], [], []
    for ev in events:
        start_str = ev.start or ""
        try:
            start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            later.append(ev)
            continue
        days_until = (start_dt - now).days
        if days_until <= 3:
            urgent.append((days_until, ev))
        elif days_until <= 7:
            soon.append((days_until, ev))
        else:
            later.append((days_until, ev))

    def _fmt(bucket: list, icon: str) -> list[str]:
        return [
            f"{icon} {ev.summary or '(sem título)'} — em {d}d"
            for d, ev in sorted(bucket, key=lambda x: x[0])
        ]

    lines_md = [f"**📅 Radar de Prazos — próximos {days_ahead} dias:**"]
    if urgent:
        lines_md.append("🔴 **Urgente (≤3 dias):**")
        lines_md.extend(_fmt(urgent, "•"))
    if soon:
        lines_md.append("🟡 **Em breve (≤7 dias):**")
        lines_md.extend(_fmt(soon, "•"))
    if later:
        lines_md.append("⚪ **Mais adiante:**")
        lines_md.extend(_fmt(later, "•"))

    total = len(urgent) + len(soon) + len(later)
    logger.info("[routine_fn] get_upcoming_deadlines: client=%s total=%d", client_id, total)
    return {"deadline_summary": "\n".join(lines_md), "deadline_count": total}


# ---------------------------------------------------------------------------
# analytics.get_daily_schedule — MC-01 Morning Chain
# ---------------------------------------------------------------------------


@register(
    "analytics.get_daily_schedule",
    description="Agrega em paralelo KPIs MTD, agenda do dia, decisões pendentes e saúde das integrações.",
    inputs=[
        {"key": "date", "type": "str", "description": "Data ISO (padrão: hoje)", "required": False},
    ],
    outputs=[
        {"key": "kpis", "type": "dict", "description": "KPIs MTD do dia"},
        {"key": "agenda", "type": "list", "description": "Eventos do calendário para hoje"},
        {"key": "pendencias", "type": "list", "description": "Decisões pendentes"},
        {"key": "alertas_integracao", "type": "list", "description": "Integrações com problema"},
        {"key": "daily_schedule_summary", "type": "str", "description": "Resumo combinado do dia para uso em cards"},
    ],
)
async def _get_daily_schedule(inputs: dict, client_id: str) -> dict:
    """
    Aggregate all morning context in parallel:
    - KPI snapshots (MTD)
    - Calendar events for today (window_hours=18)
    - Pending approvals (top 5)
    - Integration health check

    Returns a unified daily_schedule_summary string plus the raw sub-results.
    """
    kpi_result, calendar_result, pending_result, health_result = await asyncio.gather(
        _get_kpi_snapshots({}, client_id),
        _get_calendar_events({"window_hours": 18}, client_id),
        _get_pending_approvals({"limit": 5}, client_id),
        _check_integration_health({"stale_hours": 8}, client_id),
    )

    kpis: dict = kpi_result.get("kpi_data", {})
    agenda: list = []

    # Parse calendar summary back into list for structured output
    cal_summary = calendar_result.get("calendar_summary", "")
    event_lines = [l for l in cal_summary.split("\n") if l.startswith("🕐")]
    for line in event_lines:
        parts = line.replace("🕐 ", "").split(" ", 1)
        agenda.append({"time": parts[0] if parts else "", "title": parts[1] if len(parts) > 1 else line})

    pendencias: list = pending_result.get("pending_items", [])

    alertas: list = []
    health_report = health_result.get("health_report", "")
    if health_result.get("problem_count", 0) > 0:
        for line in health_report.split("\n"):
            if line.startswith("⚠️"):
                alertas.append(line.replace("⚠️ ", ""))

    # Build a compact combined summary
    summary_parts = [
        kpi_result.get("kpi_summary", ""),
        cal_summary,
        pending_result.get("pending_summary", ""),
    ]
    if alertas:
        summary_parts.append(f"**🔌 Alertas de integração:**\n" + "\n".join(f"⚠️ {a}" for a in alertas))

    logger.info(
        "[routine_fn] get_daily_schedule: client=%s kpi_dims=%d events=%d pending=%d alerts=%d",
        client_id,
        len(kpis),
        len(agenda),
        len(pendencias),
        len(alertas),
    )
    return {
        "kpis": kpis,
        "agenda": agenda,
        "pendencias": pendencias,
        "alertas_integracao": alertas,
        "daily_schedule_summary": "\n\n".join(p for p in summary_parts if p),
    }


# ---------------------------------------------------------------------------
# financeiro.* — Open Finance cash position and transactions (Polp/Pluggy)
# ---------------------------------------------------------------------------


@register(
    "financeiro.get_cash_position",
    description="Lê saldos bancários e de crédito das contas conectadas via Open Finance (Polp).",
    inputs=[],
    outputs=[
        {"key": "saldo_total", "type": "float", "description": "Soma de todos os saldos bancários"},
        {"key": "saldo_conta_corrente", "type": "float", "description": "Saldo de contas correntes"},
        {"key": "limite_credito_disponivel", "type": "float", "description": "Limite de crédito disponível"},
        {"key": "contas", "type": "list", "description": "Lista de contas com id, name, type, balance, updated_at"},
        {"key": "updated_at", "type": "str", "description": "Data/hora da última atualização"},
    ],
)
async def _get_cash_position(inputs: dict, client_id: str) -> dict:
    """
    FIN-01: Read polp_accounts for this client and compute cash position metrics.
    """
    from blu_supabase_client import get_supabase_client

    db = get_supabase_client(use_service_role=True)

    resp = await asyncio.to_thread(
        lambda: db.table("polp_accounts")
        .select("id, name, type, subtype, balance, credit_data, updated_at")
        .eq("client_id", client_id)
        .execute()
    )
    accounts: list[dict] = resp.data or []

    saldo_total = 0.0
    saldo_cc = 0.0
    limite_credito = 0.0
    contas_out: list[dict] = []
    latest_update = ""

    for acct in accounts:
        balance = float(acct.get("balance") or 0)
        atype = (acct.get("type") or "").upper()
        subtype = (acct.get("subtype") or "").upper()
        upd = acct.get("updated_at") or ""

        if atype == "BANK":
            saldo_total += balance
            if "CHECKING" in subtype:
                saldo_cc += balance

        if atype == "CREDIT":
            credit_data = acct.get("credit_data") or {}
            avail = float(credit_data.get("availableCreditLimit") or 0)
            limite_credito += avail

        contas_out.append({
            "id": acct.get("id"),
            "name": acct.get("name"),
            "type": atype,
            "subtype": subtype,
            "balance": balance,
            "updated_at": upd,
        })
        if upd and upd > latest_update:
            latest_update = upd

    logger.info(
        "[routine_fn] get_cash_position: client=%s accounts=%d saldo_total=%.2f cc=%.2f",
        client_id, len(accounts), saldo_total, saldo_cc,
    )
    return {
        "saldo_total": saldo_total,
        "saldo_conta_corrente": saldo_cc,
        "limite_credito_disponivel": limite_credito,
        "contas": contas_out,
        "updated_at": latest_update,
    }


@register(
    "financeiro.get_recent_transactions",
    description="Lê transações recentes do Open Finance, agrupa por categoria e extrai top merchants.",
    inputs=[
        {"key": "days", "type": "int", "description": "Janela em dias (padrão 30)", "default": 30, "required": False},
        {"key": "include_images", "type": "bool", "description": "Incluir logo_url dos merchants", "default": True, "required": False},
    ],
    outputs=[
        {"key": "transacoes", "type": "list", "description": "Lista de transações brutas"},
        {"key": "total_debitos", "type": "float", "description": "Soma dos débitos no período"},
        {"key": "total_creditos", "type": "float", "description": "Soma dos créditos no período"},
        {"key": "por_categoria", "type": "dict", "description": "Totais por categoria de gasto"},
        {"key": "top_merchants", "type": "list", "description": "Top merchants por valor, com logo_url"},
    ],
)
async def _get_recent_transactions(inputs: dict, client_id: str) -> dict:
    """
    FIN-02: Fetch polp_transactions within the window, aggregate by category
    and extract top merchant logos for card display.
    """
    from datetime import datetime, timedelta, timezone

    from blu_supabase_client import get_supabase_client

    days = int(inputs.get("days", 30))
    include_images = bool(inputs.get("include_images", True))
    since = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()

    db = get_supabase_client(use_service_role=True)

    resp = await asyncio.to_thread(
        lambda: db.table("polp_transactions")
        .select("id, description, amount, type, date, category, merchant")
        .eq("client_id", client_id)
        .gte("date", since)
        .order("date", desc=True)
        .limit(500)
        .execute()
    )
    txs: list[dict] = resp.data or []

    total_debits = 0.0
    total_credits = 0.0
    por_cat: dict[str, float] = {}
    merchant_totals: dict[str, dict] = {}

    for tx in txs:
        amount = float(tx.get("amount") or 0)
        tx_type = (tx.get("type") or "DEBIT").upper()
        cat_obj = tx.get("category") or {}
        cat_name = cat_obj.get("description") or "Outros"
        merchant_obj = tx.get("merchant") or {}
        merchant_name = merchant_obj.get("name") or ""
        logo_url = merchant_obj.get("logo_url") or "" if include_images else ""

        if tx_type == "DEBIT":
            total_debits += amount
            por_cat[cat_name] = por_cat.get(cat_name, 0.0) + amount
        else:
            total_credits += amount

        if merchant_name:
            if merchant_name not in merchant_totals:
                merchant_totals[merchant_name] = {"nome": merchant_name, "logo_url": logo_url, "valor": 0.0}
            merchant_totals[merchant_name]["valor"] += amount

    top_merchants = sorted(merchant_totals.values(), key=lambda m: m["valor"], reverse=True)[:10]

    logger.info(
        "[routine_fn] get_recent_transactions: client=%s txs=%d debits=%.2f credits=%.2f",
        client_id, len(txs), total_debits, total_credits,
    )
    return {
        "transacoes": txs,
        "total_debitos": total_debits,
        "total_creditos": total_credits,
        "por_categoria": por_cat,
        "top_merchants": top_merchants,
    }


@register(
    "financeiro.evaluate_cash_alert",
    description="Avalia se o saldo está abaixo do limite configurado e calcula runway em dias.",
    inputs=[
        {"key": "saldo", "type": "float", "description": "Saldo atual (usa {{saldo_conta_corrente}})", "required": True},
        {"key": "threshold", "type": "float", "description": "Saldo mínimo configurado", "required": True},
        {"key": "total_debitos", "type": "float", "description": "Débitos recentes para calcular runway", "default": 0, "required": False},
        {"key": "days", "type": "int", "description": "Janela dos débitos em dias (para média diária)", "default": 30, "required": False},
        {"key": "runway_days_warn", "type": "int", "description": "Alertar se runway < N dias", "default": 15, "required": False},
    ],
    outputs=[
        {"key": "should_alert", "type": "bool", "description": "True se o alerta deve ser emitido"},
        {"key": "severity", "type": "str", "description": "'critical' ou 'warning'"},
        {"key": "runway_days", "type": "float", "description": "Dias estimados de caixa restante"},
        {"key": "mensagem", "type": "str", "description": "Mensagem de alerta formatada"},
    ],
)
async def _evaluate_cash_alert(inputs: dict, client_id: str) -> dict:
    """
    FIN-03: Pure logic — compare saldo against threshold and compute runway.
    """
    saldo = float(inputs.get("saldo", 0))
    threshold = float(inputs.get("threshold", 5000))
    total_debitos = float(inputs.get("total_debitos", 0))
    days = int(inputs.get("days", 30))
    runway_warn = int(inputs.get("runway_days_warn", 15))

    media_saidas_diaria = (total_debitos / days) if days > 0 and total_debitos > 0 else 0.0
    runway_days = (saldo / media_saidas_diaria) if media_saidas_diaria > 0 else float("inf")

    below_threshold = saldo < threshold
    low_runway = runway_days != float("inf") and runway_days < runway_warn

    should_alert = below_threshold or low_runway

    if not should_alert:
        severity = "ok"
        mensagem = f"✅ Saldo em conta corrente R$ {saldo:,.2f} — acima do mínimo configurado (R$ {threshold:,.2f})."
    elif below_threshold and (runway_days != float("inf") and runway_days < 7):
        severity = "critical"
        mensagem = (
            f"🚨 **Caixa crítico!** Saldo R$ {saldo:,.2f} abaixo do mínimo (R$ {threshold:,.2f}). "
            f"Runway estimado: **{runway_days:.0f} dias**."
        )
    else:
        severity = "warning"
        runway_str = f"{runway_days:.0f} dias" if runway_days != float("inf") else "indefinido"
        mensagem = (
            f"⚠️ Saldo R$ {saldo:,.2f} — abaixo do limite de R$ {threshold:,.2f}. "
            f"Runway estimado: {runway_str}."
        )

    logger.info(
        "[routine_fn] evaluate_cash_alert: client=%s saldo=%.2f threshold=%.2f runway=%.1f should_alert=%s",
        client_id, saldo, threshold, runway_days if runway_days != float("inf") else -1, should_alert,
    )
    return {
        "should_alert": should_alert,
        "severity": severity,
        "runway_days": runway_days if runway_days != float("inf") else -1,
        "mensagem": mensagem,
    }


# ---------------------------------------------------------------------------
# analytics.get_overdue_customers — CLI-01
# ---------------------------------------------------------------------------


@register(
    "analytics.get_overdue_customers",
    description="Lista clientes inadimplentes com compras passadas mas sem retorno por N dias.",
    inputs=[
        {"key": "min_dias", "type": "int", "description": "Dias mínimos sem compra para considerar inadimplente", "default": 30, "required": False},
        {"key": "max_results", "type": "int", "description": "Limite de clientes retornados", "default": 50, "required": False},
    ],
    outputs=[
        {"key": "overdue_customers", "type": "list", "description": "Lista de clientes inadimplentes com nome, telefone, dias_recencia, receita_total"},
        {"key": "overdue_count", "type": "int", "description": "Total de clientes inadimplentes encontrados"},
    ],
)
async def _get_overdue_customers(inputs: dict, client_id: str) -> dict:
    """
    CLI-01: Fetch clients from dim_clientes with dias_recencia > min_dias
    and receita_total > 0, ordered by receita_total DESC.
    """
    from blu_supabase_client import get_supabase_client

    min_dias = int(inputs.get("min_dias", 30))
    max_results = int(inputs.get("max_results", 50))

    db = get_supabase_client(use_service_role=True)

    resp = await asyncio.to_thread(
        lambda: db.schema("analytics_v2")
        .table("dim_clientes")
        .select(
            "nome, telefone, dias_recencia, receita_total, ticket_medio, "
            "data_ultima_compra, nivel_cluster"
        )
        .eq("client_id", client_id)
        .gt("dias_recencia", min_dias)
        .gt("receita_total", 0)
        .order("receita_total", desc=True)
        .limit(max_results)
        .execute()
    )

    customers: list[dict] = resp.data or []
    logger.info(
        "[routine_fn] get_overdue_customers: client=%s min_dias=%d found=%d",
        client_id, min_dias, len(customers),
    )
    return {"overdue_customers": customers, "overdue_count": len(customers)}


# ---------------------------------------------------------------------------
# analytics.get_client_pipeline — CLI-04
# ---------------------------------------------------------------------------


@register(
    "analytics.get_client_pipeline",
    description="Segmenta clientes em ativos, em risco, inativos e novos. Inclui NPS quando disponível.",
    inputs=[
        {"key": "segment", "type": "str", "description": "Filtrar por segmento (ativos/em_risco/inativos/novos). Vazio = todos.", "required": False},
    ],
    outputs=[
        {"key": "ativos", "type": "list", "description": "Clientes com compra nos últimos 30 dias"},
        {"key": "em_risco", "type": "list", "description": "Clientes com compra entre 31 e 90 dias atrás"},
        {"key": "inativos", "type": "list", "description": "Clientes sem compra há mais de 90 dias"},
        {"key": "novos", "type": "list", "description": "Clientes com primeira compra nos últimos 60 dias"},
        {"key": "pipeline_summary", "type": "str", "description": "Resumo markdown do pipeline"},
    ],
)
async def _get_client_pipeline(inputs: dict, client_id: str) -> dict:
    """
    CLI-04: Segment dim_clientes by recency and first purchase date.
    Includes NPS fields when populated (INF-06 schema).
    """
    from datetime import datetime, timedelta, timezone

    from blu_supabase_client import get_supabase_client

    segment = str(inputs.get("segment", "")).lower()
    db = get_supabase_client(use_service_role=True)

    resp = await asyncio.to_thread(
        lambda: db.schema("analytics_v2")
        .table("dim_clientes")
        .select(
            "nome, telefone, dias_recencia, receita_total, ticket_medio, "
            "data_primeira_compra, data_ultima_compra, nivel_cluster, "
            "nps_score, nps_data_coletada"
        )
        .eq("client_id", client_id)
        .limit(500)
        .execute()
    )
    customers: list[dict] = resp.data or []

    now = datetime.now(timezone.utc).date()
    cutoff_novo = (now - timedelta(days=60)).isoformat()

    ativos, em_risco, inativos, novos = [], [], [], []
    for c in customers:
        dias = int(c.get("dias_recencia") or 0)
        primeira = c.get("data_primeira_compra") or ""

        if primeira >= cutoff_novo:
            novos.append(c)
        if dias <= 30:
            ativos.append(c)
        elif dias <= 90:
            em_risco.append(c)
        else:
            inativos.append(c)

    summary = (
        f"**Pipeline de Clientes:**\n"
        f"✅ {len(ativos)} ativos · ⚠️ {len(em_risco)} em risco · "
        f"🔴 {len(inativos)} inativos · 🆕 {len(novos)} novos"
    )

    result = {
        "ativos": ativos,
        "em_risco": em_risco,
        "inativos": inativos,
        "novos": novos,
        "pipeline_summary": summary,
    }

    # If segment filter requested, also expose as client_list for skill steps
    if segment in ("ativos", "em_risco", "inativos", "novos"):
        result["client_list"] = result[segment]

    logger.info(
        "[routine_fn] get_client_pipeline: client=%s ativos=%d em_risco=%d inativos=%d novos=%d",
        client_id, len(ativos), len(em_risco), len(inativos), len(novos),
    )
    return result


# ---------------------------------------------------------------------------
# analytics.get_inventory_alerts — OPS-01
# ---------------------------------------------------------------------------


@register(
    "analytics.get_inventory_alerts",
    description="Identifica SKUs com estoque abaixo do mínimo configurado ou próximos de ruptura.",
    inputs=[
        {"key": "threshold_global", "type": "int", "description": "Estoque mínimo global (fallback quando estoque_minimo IS NULL)", "default": 10, "required": False},
    ],
    outputs=[
        {"key": "criticos", "type": "list", "description": "SKUs abaixo do estoque mínimo com dias_ate_ruptura"},
        {"key": "proximos", "type": "list", "description": "SKUs com estoque entre 1x e 2x o mínimo"},
        {"key": "total_ok", "type": "int", "description": "SKUs com estoque saudável"},
        {"key": "inventory_summary", "type": "str", "description": "Resumo markdown para card"},
    ],
)
async def _get_inventory_alerts(inputs: dict, client_id: str) -> dict:
    """
    OPS-01: Read dim_inventory, flag items below estoque_minimo or threshold_global,
    compute estimated days to stockout from frequencia_mensal.
    """
    from blu_supabase_client import get_supabase_client

    threshold_global = int(inputs.get("threshold_global", 10))
    db = get_supabase_client(use_service_role=True)

    resp = await asyncio.to_thread(
        lambda: db.schema("analytics_v2")
        .table("dim_inventory")
        .select(
            "sku, nome, quantidade_total_vendida, frequencia_mensal, "
            "estoque_minimo"
        )
        .eq("client_id", client_id)
        .execute()
    )
    items: list[dict] = resp.data or []

    criticos, proximos, total_ok = [], [], 0

    for item in items:
        qty = float(item.get("quantidade_total_vendida") or 0)
        freq = float(item.get("frequencia_mensal") or 1)
        min_stock = float(item.get("estoque_minimo") or threshold_global)

        daily_rate = freq / 30.0 if freq > 0 else 0.0
        dias_ruptura = int(qty / daily_rate) if daily_rate > 0 else 9999

        entry = {
            "sku": item.get("sku"),
            "nome": item.get("nome"),
            "qty_estimada": qty,
            "qty_minima": min_stock,
            "dias_ate_ruptura": dias_ruptura,
        }

        if qty <= min_stock:
            criticos.append(entry)
        elif qty <= min_stock * 2:
            proximos.append(entry)
        else:
            total_ok += 1

    criticos.sort(key=lambda x: x["dias_ate_ruptura"])

    lines = ["**📦 Alertas de Estoque:**"]
    if criticos:
        lines.append(f"🔴 {len(criticos)} SKU(s) crítico(s):")
        for c in criticos[:5]:
            lines.append(f"  • {c['nome']} — {c['qty_estimada']:.0f} un. (mín {c['qty_minima']:.0f}) · ruptura em ~{c['dias_ate_ruptura']}d")
    if proximos:
        lines.append(f"🟡 {len(proximos)} SKU(s) próximos do limite")
    if total_ok:
        lines.append(f"✅ {total_ok} SKU(s) saudáveis")
    if not criticos and not proximos:
        lines = ["✅ **Estoque saudável** — nenhum SKU abaixo do mínimo."]

    logger.info(
        "[routine_fn] get_inventory_alerts: client=%s criticos=%d proximos=%d ok=%d",
        client_id, len(criticos), len(proximos), total_ok,
    )
    return {
        "criticos": criticos,
        "proximos": proximos,
        "total_ok": total_ok,
        "inventory_summary": "\n".join(lines),
    }


# ---------------------------------------------------------------------------
# analytics.get_supplier_orders — OPS-03
# ---------------------------------------------------------------------------


@register(
    "analytics.get_supplier_orders",
    description="Agrupa pedidos de compra por fornecedor: abertos, atrasados e valor em aberto.",
    inputs=[
        {"key": "days", "type": "int", "description": "Janela em dias para buscar pedidos", "default": 30, "required": False},
    ],
    outputs=[
        {"key": "fornecedores", "type": "list", "description": "Lista de fornecedores com pedidos_abertos, atrasados e valor_aberto"},
        {"key": "supplier_summary", "type": "str", "description": "Resumo markdown para card"},
    ],
)
async def _get_supplier_orders(inputs: dict, client_id: str) -> dict:
    """
    OPS-03: Query fato_transacoes (entry_type='purchase') JOIN dim_fornecedores for recent purchase orders.
    """
    from blu_supabase_client import get_supabase_client

    from datetime import datetime, timedelta, timezone

    days = int(inputs.get("days", 30))
    db = get_supabase_client(use_service_role=True)
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    resp = await asyncio.to_thread(
        lambda: db.schema("analytics_v2")
        .table("fato_transacoes")
        .select(
            "fornecedor_id, valor, quantidade, valor_unitario, status, "
            "dim_fornecedores(nome)"
        )
        .eq("client_id", client_id)
        .eq("entry_type", "purchase")
        .gte("created_at", since)
        .execute()
    )
    rows: list[dict] = resp.data or []

    now = datetime.now(timezone.utc).date()
    by_supplier: dict[str, dict] = {}

    for row in rows:
        forn_id = str(row.get("fornecedor_id", ""))
        forn_data = row.get("dim_fornecedores") or {}
        nome = forn_data.get("nome") or forn_id
        status = (row.get("status") or "").lower()
        # valor pode ser direto ou calculado
        valor = float(row.get("valor") or 0)

        if forn_id not in by_supplier:
            by_supplier[forn_id] = {
                "nome": nome,
                "pedidos_abertos": 0,
                "pedidos_atrasados": 0,
                "valor_aberto": 0.0,
            }

        if status in ("aberto", "pendente", "em_transito", "registered", ""):
            by_supplier[forn_id]["pedidos_abertos"] += 1
            by_supplier[forn_id]["valor_aberto"] += valor

    fornecedores = sorted(by_supplier.values(), key=lambda f: f["valor_aberto"], reverse=True)

    lines = ["**🚚 Gestão de Fornecedores:**"]
    for f in fornecedores[:10]:
        atrasados_str = f" ⚠️ {f['pedidos_atrasados']} atrasado(s)" if f["pedidos_atrasados"] else ""
        lines.append(
            f"• {f['nome']}: {f['pedidos_abertos']} pedido(s) · R$ {f['valor_aberto']:,.0f}{atrasados_str}"
        )
    if not fornecedores:
        lines = ["✅ Nenhum pedido de compra em aberto no período."]

    logger.info(
        "[routine_fn] get_supplier_orders: client=%s suppliers=%d rows=%d",
        client_id, len(fornecedores), len(rows),
    )
    return {"fornecedores": fornecedores, "supplier_summary": "\n".join(lines)}


# ---------------------------------------------------------------------------
# agenda.get_upcoming_meetings — AGD-01
# ---------------------------------------------------------------------------


@register(
    "agenda.get_upcoming_meetings",
    description="Busca reuniões nas próximas 24h e identifica participantes externos.",
    inputs=[
        {"key": "hours_ahead", "type": "int", "description": "Janela em horas (padrão 24)", "default": 24, "required": False},
    ],
    outputs=[
        {"key": "reunioes", "type": "list", "description": "Lista de reuniões com participantes externos identificados"},
        {"key": "meeting_count", "type": "int", "description": "Total de reuniões encontradas"},
    ],
)
async def _get_upcoming_meetings(inputs: dict, client_id: str) -> dict:
    """
    AGD-01: Extend get_calendar_events to filter next 24h and mark external attendees.
    Identifies external participants as emails outside the client's domain.
    """
    from datetime import datetime, timedelta, timezone
    from blu_supabase_client import get_supabase_client

    hours_ahead = int(inputs.get("hours_ahead", 24))
    cal_client = await _build_calendar_client(client_id)

    if not cal_client:
        return {"reunioes": [], "meeting_count": 0}

    now = datetime.now(timezone.utc)
    time_max = now + timedelta(hours=hours_ahead)
    calendar_id = await _get_client_calendar_id(client_id)

    try:
        events = await cal_client.list_events(calendar_id, now, time_max, max_results=20)
    except Exception as exc:
        logger.warning("[routine_fn] get_upcoming_meetings failed for %s: %s", client_id, exc)
        return {"reunioes": [], "meeting_count": 0}

    # Fetch client domain for identifying externals
    db = get_supabase_client(use_service_role=True)
    client_row = await asyncio.to_thread(
        lambda: db.table("clientes_blu")
        .select("email_domain")
        .eq("client_id", client_id)
        .maybe_single()
        .execute()
    )
    domain = (client_row.data or {}).get("email_domain") or ""

    reunioes = []
    for ev in events:
        attendees = getattr(ev, "attendees", []) or []
        externos = [
            a for a in attendees
            if a.get("email") and (not domain or domain not in a.get("email", ""))
        ]
        reunioes.append({
            "id": ev.id,
            "summary": ev.summary or "(sem título)",
            "start": ev.start,
            "location": ev.location,
            "attendees": attendees,
            "externos": externos,
            "has_externals": len(externos) > 0,
        })

    logger.info(
        "[routine_fn] get_upcoming_meetings: client=%s meetings=%d", client_id, len(reunioes)
    )
    return {"reunioes": reunioes, "meeting_count": len(reunioes)}


# ---------------------------------------------------------------------------
# web.get_meeting_participant_context — AGD-02
# ---------------------------------------------------------------------------


@register(
    "web.get_meeting_participant_context",
    description="Para cada participante externo da reunião, busca contexto no CRM ou via web crawl.",
    inputs=[
        {"key": "reunioes", "type": "list", "description": "Lista de reuniões (usa {{reunioes}})", "required": True},
    ],
    outputs=[
        {"key": "participantes_contexto", "type": "list", "description": "Contexto de cada participante externo (empresa, segmento, etc.)"},
    ],
)
async def _get_meeting_participant_context(inputs: dict, client_id: str) -> dict:
    """
    AGD-02: For each external attendee in the meetings list:
    1. Search dim_clientes by email/domain
    2. If not found, web_crawl the participant's domain
    """
    from blu_supabase_client import get_supabase_client

    reunioes: list[dict] = inputs.get("reunioes", [])
    db = get_supabase_client(use_service_role=True)

    seen_domains: set[str] = set()
    contextos: list[dict] = []

    for reuniao in reunioes:
        externos = reuniao.get("externos") or []
        for ext in externos:
            email = ext.get("email", "")
            if not email:
                continue
            domain = email.split("@")[-1] if "@" in email else ""
            if domain in seen_domains:
                continue
            seen_domains.add(domain)

            # 1. Try CRM lookup by email domain
            crm_resp = await asyncio.to_thread(
                lambda d=domain: db.schema("analytics_v2")
                .table("dim_clientes")
                .select("nome, telefone, receita_total, nivel_cluster")
                .eq("client_id", client_id)
                .ilike("email", f"%@{d}")
                .limit(1)
                .execute()
            )
            crm_rows = crm_resp.data or []
            if crm_rows:
                c = crm_rows[0]
                contextos.append({
                    "email": email,
                    "domain": domain,
                    "source": "crm",
                    "nome": c.get("nome"),
                    "receita_total": c.get("receita_total"),
                    "nivel_cluster": c.get("nivel_cluster"),
                })
                continue

            # 2. Web crawl the domain for context
            url = f"https://{domain}"
            try:
                raw = await _call_mcp_tool("web_crawl", {"url": url, "max_depth": 2, "max_pages": 3})
                contextos.append({
                    "email": email,
                    "domain": domain,
                    "source": "web",
                    "raw_content": raw[:2000] if raw else "",
                })
            except Exception as exc:
                logger.debug("[routine_fn] web crawl failed for %s: %s", domain, exc)
                contextos.append({
                    "email": email,
                    "domain": domain,
                    "source": "unknown",
                    "raw_content": "",
                })

    logger.info(
        "[routine_fn] get_meeting_participant_context: client=%s participants=%d",
        client_id, len(contextos),
    )
    return {"participantes_contexto": contextos}


# ---------------------------------------------------------------------------
# web.crawl_competitor_pages — EST-04
# ---------------------------------------------------------------------------


@register(
    "web.crawl_competitor_pages",
    description="Faz crawl dos sites dos concorrentes configurados (até 3) e retorna o conteúdo markdown.",
    inputs=[
        {"key": "concorrentes", "type": "dict", "description": "Dict {nome: url} dos concorrentes (usa {{config.concorrentes}})", "required": True},
    ],
    outputs=[
        {"key": "concorrentes_conteudo", "type": "dict", "description": "Dict {nome: conteúdo markdown} por concorrente"},
    ],
)
async def _crawl_competitor_pages(inputs: dict, client_id: str) -> dict:
    """
    EST-04: Crawl up to 3 competitor URLs and return markdown content per competitor.
    """
    concorrentes: dict = inputs.get("concorrentes", {})
    if not concorrentes or not isinstance(concorrentes, dict):
        return {"concorrentes_conteudo": {}}

    conteudo: dict[str, str] = {}
    # Limit to 3 entries to control cost
    for nome, url in list(concorrentes.items())[:3]:
        if not url:
            continue
        try:
            raw = await _call_mcp_tool(
                "web_crawl", {"url": url, "max_depth": 2, "max_pages": 5}
            )
            conteudo[nome] = raw[:5000] if raw else ""
            logger.info("[routine_fn] crawl_competitor: crawled %s (%d chars)", url, len(conteudo[nome]))
        except Exception as exc:
            logger.warning("[routine_fn] crawl_competitor: failed for %s: %s", url, exc)
            conteudo[nome] = f"Erro ao acessar {url}: {exc}"

    return {"concorrentes_conteudo": conteudo}


# ---------------------------------------------------------------------------
# analytics.get_sales_performance — EST-01
# ---------------------------------------------------------------------------


@register(
    "analytics.get_sales_performance",
    description="Busca série temporal de 90 dias, tendência, top produtos/regiões e comparativo do período anterior.",
    inputs=[],
    outputs=[
        {"key": "serie_temporal", "type": "list", "description": "Vendas diárias dos últimos 90 dias"},
        {"key": "tendencia", "type": "dict", "description": "Slope e R² da regressão linear"},
        {"key": "top_produtos", "type": "list", "description": "Top 5 produtos por receita"},
        {"key": "top_regioes", "type": "list", "description": "Top 3 regiões por receita"},
        {"key": "kpi_resumo", "type": "dict", "description": "Resumo de KPIs com variação vs período anterior"},
        {"key": "performance_summary", "type": "str", "description": "Resumo markdown para o card"},
    ],
)
async def _get_sales_performance(inputs: dict, client_id: str) -> dict:
    """
    EST-01: Read v_series_temporal, v_resumo_dashboard, v_distribuicao_regional
    and compute simple linear trend.
    """
    from blu_supabase_client import get_supabase_client
    from datetime import datetime, timedelta, timezone

    db = get_supabase_client(use_service_role=True)
    since_90 = (datetime.now(timezone.utc) - timedelta(days=90)).date().isoformat()

    serie_resp, resumo_resp, regional_resp = await asyncio.gather(
        asyncio.to_thread(
            lambda: db.schema("analytics_v2")
            .table("v_series_temporal")
            .select("data, receita_liquida, pedidos, ticket_medio")
            .eq("client_id", client_id)
            .gte("data", since_90)
            .order("data")
            .execute()
        ),
        asyncio.to_thread(
            lambda: db.schema("analytics_v2")
            .table("v_resumo_dashboard")
            .select("*")
            .eq("client_id", client_id)
            .limit(1)
            .execute()
        ),
        asyncio.to_thread(
            lambda: db.schema("analytics_v2")
            .table("v_distribuicao_regional")
            .select("uf, receita_total, pedidos_total")
            .eq("client_id", client_id)
            .order("receita_total", desc=True)
            .limit(3)
            .execute()
        ),
    )

    serie: list[dict] = serie_resp.data or []
    resumo: dict = (resumo_resp.data or [{}])[0]
    regioes: list[dict] = regional_resp.data or []

    # Simple linear regression on receita_liquida over index
    tendencia: dict = {}
    if len(serie) >= 5:
        ys = [float(r.get("receita_liquida") or 0) for r in serie]
        n = len(ys)
        xs = list(range(n))
        mean_x = sum(xs) / n
        mean_y = sum(ys) / n
        num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
        den = sum((x - mean_x) ** 2 for x in xs)
        slope = num / den if den else 0.0
        ss_res = sum((y - (mean_y + slope * (x - mean_x))) ** 2 for x, y in zip(xs, ys))
        ss_tot = sum((y - mean_y) ** 2 for y in ys)
        r2 = 1 - ss_res / ss_tot if ss_tot else 0.0
        tendencia = {"slope": round(slope, 2), "r2": round(r2, 3)}

    # Top 5 products — v_top_produtos may not exist on all tenants
    try:
        top_produtos_resp = await asyncio.to_thread(
            lambda: db.schema("analytics_v2")
            .table("v_top_produtos")
            .select("nome_produto, receita_total, pedidos_total")
            .eq("client_id", client_id)
            .order("receita_total", desc=True)
            .limit(5)
            .execute()
        )
        top_produtos: list[dict] = top_produtos_resp.data or []
    except Exception:
        top_produtos = []

    receita_atual = float(resumo.get("receita_liquida_mtd") or 0)
    receita_ant = float(resumo.get("receita_liquida_mes_anterior") or 0)
    variacao = ((receita_atual - receita_ant) / receita_ant * 100) if receita_ant else 0.0

    kpi_resumo = {
        "receita_atual": receita_atual,
        "receita_anterior": receita_ant,
        "variacao_pct": round(variacao, 1),
        "pedidos_mes": resumo.get("total_pedidos_mtd"),
    }

    arrow = "▲" if variacao > 0 else "▼" if variacao < 0 else "→"
    summary_lines = [
        f"**📊 Desempenho de Vendas (90 dias):**",
        f"Receita MTD: R$ {receita_atual:,.0f} {arrow}{abs(variacao):.1f}% vs mês ant.",
    ]
    if tendencia:
        trend_dir = "crescente" if tendencia["slope"] > 0 else "decrescente"
        summary_lines.append(f"Tendência {trend_dir} (slope={tendencia['slope']:+.1f}/dia, R²={tendencia['r2']:.2f})")
    if top_produtos:
        summary_lines.append(f"Top produto: {top_produtos[0].get('nome_produto', 'N/A')}")
    if regioes:
        summary_lines.append(f"Região líder: {regioes[0].get('uf', 'N/A')}")

    logger.info(
        "[routine_fn] get_sales_performance: client=%s serie=%d slope=%.2f",
        client_id, len(serie), tendencia.get("slope", 0),
    )
    return {
        "serie_temporal": serie,
        "tendencia": tendencia,
        "top_produtos": top_produtos,
        "top_regioes": regioes,
        "kpi_resumo": kpi_resumo,
        "performance_summary": "\n".join(summary_lines),
    }


# ---------------------------------------------------------------------------
# analytics.get_nps_data — SAT-01
# ---------------------------------------------------------------------------


@register(
    "analytics.get_nps_data",
    description="Lê dados de NPS dos clientes (nps_score, nps_data_coletada, nps_detalhes) de dim_clientes.",
    inputs=[],
    outputs=[
        {"key": "nps_data", "type": "list", "description": "Clientes com NPS preenchido"},
        {"key": "nps_avg", "type": "float", "description": "NPS médio"},
        {"key": "promotores", "type": "int", "description": "Clientes com NPS >= 9"},
        {"key": "detratores", "type": "int", "description": "Clientes com NPS <= 6"},
        {"key": "nps_summary", "type": "str", "description": "Resumo markdown do NPS"},
    ],
)
async def _get_nps_data(inputs: dict, client_id: str) -> dict:
    """SAT-01: Read NPS fields from dim_clientes (added in INF-06 migration)."""
    from blu_supabase_client import get_supabase_client

    db = get_supabase_client(use_service_role=True)

    resp = await asyncio.to_thread(
        lambda: db.schema("analytics_v2")
        .table("dim_clientes")
        .select("nome, nps_score, nps_data_coletada, nps_detalhes")
        .eq("client_id", client_id)
        .not_.is_("nps_score", "null")
        .execute()
    )
    rows: list[dict] = resp.data or []

    if not rows:
        return {
            "nps_data": [],
            "nps_avg": 0.0,
            "promotores": 0,
            "detratores": 0,
            "nps_summary": "ℹ️ Nenhum dado de NPS coletado ainda.",
        }

    scores = [float(r.get("nps_score") or 0) for r in rows]
    nps_avg = sum(scores) / len(scores)
    promotores = sum(1 for s in scores if s >= 9)
    detratores = sum(1 for s in scores if s <= 6)
    neutros = len(scores) - promotores - detratores

    nps_net = int(((promotores - detratores) / len(scores)) * 100)
    summary = (
        f"**🌟 NPS — {len(rows)} resposta(s):**\n"
        f"Score médio: {nps_avg:.1f} · NPS Net: {nps_net:+d}\n"
        f"😊 {promotores} promotores · 😐 {neutros} neutros · 😞 {detratores} detratores"
    )

    logger.info(
        "[routine_fn] get_nps_data: client=%s n=%d avg=%.1f net=%d",
        client_id, len(rows), nps_avg, nps_net,
    )
    return {
        "nps_data": rows,
        "nps_avg": nps_avg,
        "promotores": promotores,
        "detratores": detratores,
        "nps_summary": summary,
    }


# ---------------------------------------------------------------------------
# memory.* — Room Monitor shared memory writes
# ---------------------------------------------------------------------------


@register(
    "memory.write_dimension_state",
    description="Upsert do estado de uma dimensão na tabela dimension_state. Chamado por Room Monitors ao final de cada execução para alimentar o snapshot de contexto do agente.",
    inputs=[
        {"key": "dimension", "type": "str", "description": "Slug da dimensão: 'financeiro'|'compras'|'clientes'|'agenda'|'estrategia'|'documentos'", "required": True},
        {"key": "summary", "type": "str", "description": "Resumo em prosa (~250 tokens) legível por LLM descrevendo o estado atual da dimensão", "required": True},
        {"key": "structured", "type": "dict", "description": "Dados numéricos/estruturados em JSON para leitura programática (opcional)", "required": False},
        {"key": "ttl_hours", "type": "int", "description": "TTL em horas para este bloco de estado (default: 24)", "default": 24, "required": False},
    ],
    outputs=[
        {"key": "memory_written", "type": "bool", "description": "True se o upsert foi bem-sucedido"},
        {"key": "dimension_written", "type": "str", "description": "Slug da dimensão atualizada"},
    ],
)
async def _write_dimension_state(inputs: dict, client_id: str) -> dict:
    """
    Upsert the current state of a business dimension into `dimension_state`.

    Called at the end of every Room Monitor routine execution. The unique
    constraint (client_id, dimension) ensures one canonical row per dimension
    per tenant — repeated executions overwrite rather than append.

    inputs:
        dimension  — one of: financeiro, compras, clientes, agenda, estrategia, documentos
        summary    — prose description readable by an LLM (~250 tokens max)
        structured — optional JSON dict with numeric/structured data
        ttl_hours  — how long until this state expires (default 24h)

    outputs:
        memory_written    — True if upsert succeeded
        dimension_written — the dimension slug that was updated
    """
    import datetime

    from blu_supabase_client import get_supabase_client

    dimension: str = inputs.get("dimension", "").strip()
    summary: str = inputs.get("summary", "").strip()
    structured: dict | None = inputs.get("structured") or None
    ttl_hours: int = int(inputs.get("ttl_hours", 24))

    if not dimension:
        raise ValueError("memory.write_dimension_state: 'dimension' is required")
    if not summary:
        raise ValueError("memory.write_dimension_state: 'summary' is required")

    valid_until = (
        datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(hours=ttl_hours)
    ).isoformat()

    db = get_supabase_client(use_service_role=True)

    row: dict = {
        "client_id": client_id,
        "dimension": dimension,
        "summary": summary,
        "structured": structured,
        "valid_until": valid_until,
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    await asyncio.to_thread(
        lambda: db.table("dimension_state")
        .upsert(row, on_conflict="client_id,dimension")
        .execute()
    )

    logger.info(
        "[routine_fn] write_dimension_state: client=%s dimension=%s ttl=%dh",
        client_id, dimension, ttl_hours,
    )
    return {"memory_written": True, "dimension_written": dimension}


# ─────────────────────────────────────────────────────────────────────────────
# BIBLIOTECA MONITOR — funções de suporte
# ─────────────────────────────────────────────────────────────────────────────


@register(
    "biblioteca.get_document_status",
    description="Retorna contagem de documentos da base por status de indexação (indexed/pending/failed/rejected).",
    inputs=[],
    outputs=[
        {"key": "doc_status",    "type": "dict", "description": "Contagem por status"},
        {"key": "total_docs",    "type": "int",  "description": "Total de documentos"},
        {"key": "pending_count", "type": "int",  "description": "Documentos aguardando indexação"},
    ],
)
async def _biblioteca_get_document_status(inputs: dict, client_id: str) -> dict:
    """
    Consulta vector_db.documents e retorna contagem por status.
    Soft-fails: retorna zeros se tabela inexistente ou erro de conexão.
    """
    from blu_supabase_client import get_supabase_client

    db = get_supabase_client(use_service_role=True)

    try:
        resp = await asyncio.to_thread(
            lambda: db.rpc(
                "get_document_status",
                {"p_client_id": client_id},
            ).execute()
        )
        data = (resp.data or {})
        if isinstance(data, list):
            data = data[0] if data else {}
    except Exception as exc:
        logger.warning("[routine_fn] biblioteca.get_document_status failed for %s: %s", client_id, exc)
        data = {}

    indexed  = int(data.get("indexed",  0))
    pending  = int(data.get("pending",  0))
    failed   = int(data.get("failed",   0))
    rejected = int(data.get("rejected", 0))
    total    = int(data.get("total",    0))

    status_label = f"✅ {indexed} indexados | ⏳ {pending} pendentes | ❌ {failed} falhos | 🚫 {rejected} rejeitados"
    logger.info("[routine_fn] biblioteca.get_document_status: client=%s total=%d", client_id, total)

    return {
        "doc_status":    status_label,
        "total_docs":    total,
        "pending_count": pending,
    }


@register(
    "biblioteca.get_recent_uploads",
    description="Retorna documentos enviados pelo cliente nas últimas N horas.",
    inputs=[
        {"key": "hours_lookback", "type": "int", "description": "Janela em horas", "default": 24, "required": False},
    ],
    outputs=[
        {"key": "recent_count",       "type": "int",  "description": "Número de uploads recentes"},
        {"key": "recent_docs_summary","type": "str",  "description": "Lista resumida de uploads"},
        {"key": "pending_document_ids","type": "list", "description": "IDs de docs ainda pendentes"},
    ],
)
async def _biblioteca_get_recent_uploads(inputs: dict, client_id: str) -> dict:
    """
    Busca documentos enviados nas últimas hours_lookback horas.
    Retorna lista de nomes, contagem e IDs de docs pendentes para HITL.
    """
    from blu_supabase_client import get_supabase_client

    hours_lookback = int(inputs.get("hours_lookback", 24))
    db = get_supabase_client(use_service_role=True)

    try:
        resp = await asyncio.to_thread(
            lambda: db.rpc(
                "get_recent_uploads",
                {"p_client_id": client_id, "p_hours_lookback": hours_lookback},
            ).execute()
        )
        data = resp.data or {}
        if isinstance(data, list):
            data = data[0] if data else {}
    except Exception as exc:
        logger.warning("[routine_fn] biblioteca.get_recent_uploads failed for %s: %s", client_id, exc)
        data = {}

    count = int(data.get("count", 0))
    docs  = data.get("documents") or []

    pending_ids = [
        str(d["id"]) for d in docs
        if d.get("status") in (None, "pending")
    ]

    if not docs:
        summary = f"📄 Nenhum upload nas últimas {hours_lookback}h."
    else:
        lines = [f"📄 {count} upload(s) nas últimas {hours_lookback}h:"]
        for d in docs[:5]:
            status_icon = {"indexed": "✅", "pending": "⏳", "failed": "❌"}.get(
                d.get("status", "pending"), "⏳"
            )
            lines.append(f"  {status_icon} {d.get('file_name', '?')} ({d.get('file_type', '?')})")
        if count > 5:
            lines.append(f"  … e mais {count - 5} documento(s)")
        summary = "\n".join(lines)

    logger.info(
        "[routine_fn] biblioteca.get_recent_uploads: client=%s count=%d pending=%d",
        client_id, count, len(pending_ids),
    )
    return {
        "recent_count":        count,
        "recent_docs_summary": summary,
        "pending_document_ids": pending_ids,
    }


@register(
    "biblioteca.get_unanswered_queries",
    description="Retorna queries RAG recentes com baixo score de similaridade (gaps de conhecimento).",
    inputs=[
        {"key": "min_count", "type": "int", "description": "Mínimo de queries para alertar", "default": 3, "required": False},
    ],
    outputs=[
        {"key": "unanswered_count",   "type": "int", "description": "Número de queries sem boa resposta"},
        {"key": "unanswered_summary", "type": "str", "description": "Descrição dos gaps identificados"},
    ],
)
async def _biblioteca_get_unanswered_queries(inputs: dict, client_id: str) -> dict:
    """
    Consulta rag_query_log para queries com score < 0.6 nos últimos 7 dias.
    Soft-fail se a tabela não existir ainda.
    """
    from blu_supabase_client import get_supabase_client

    min_count = int(inputs.get("min_count", 3))
    db = get_supabase_client(use_service_role=True)

    try:
        resp = await asyncio.to_thread(
            lambda: db.rpc(
                "get_unanswered_queries",
                {"p_client_id": client_id, "p_min_count": min_count},
            ).execute()
        )
        data = resp.data or {}
        if isinstance(data, list):
            data = data[0] if data else {}
    except Exception as exc:
        logger.debug("[routine_fn] biblioteca.get_unanswered_queries: soft-fail for %s: %s", client_id, exc)
        data = {}

    count   = int(data.get("count", 0))
    queries = data.get("queries") or []

    if count == 0:
        summary = "🟢 Sem gaps de conhecimento identificados nos últimos 7 dias."
    else:
        lines = [f"⚠️ {count} perguntas sem boa cobertura documental (últimos 7 dias):"]
        for q in (queries or [])[:3]:
            lines.append(f"  • \"{q}\"")
        if count > 3:
            lines.append(f"  … e mais {count - 3} query(ies)")
        summary = "\n".join(lines)

    logger.info("[routine_fn] biblioteca.get_unanswered_queries: client=%s count=%d", client_id, count)
    return {
        "unanswered_count":   count,
        "unanswered_summary": summary,
    }


@register(
    "biblioteca.submit_pending_for_hitl",
    description="Submete documentos pendentes de indexação para aprovação HITL.",
    inputs=[
        {"key": "auto_submit",    "type": "bool", "description": "Submeter automaticamente",      "default": True,  "required": False},
        {"key": "document_ids",   "type": "list", "description": "IDs explícitos (opcional)",     "default": None,  "required": False},
    ],
    outputs=[
        {"key": "pending_hitl_count", "type": "int",  "description": "Documentos submetidos para HITL"},
        {"key": "hitl_summary",       "type": "str",  "description": "Descrição do resultado"},
    ],
)
async def _biblioteca_submit_pending_for_hitl(inputs: dict, client_id: str) -> dict:
    """
    Cria registros em approvals (type=document_indexing) para cada doc pendente.
    Idempotente: ON CONFLICT DO NOTHING evita duplicatas.
    """
    from blu_supabase_client import get_supabase_client

    auto_submit  = inputs.get("auto_submit", True)
    document_ids = inputs.get("document_ids") or None

    if not auto_submit:
        return {"pending_hitl_count": 0, "hitl_summary": "⏭️ HITL automático desabilitado."}

    db = get_supabase_client(use_service_role=True)

    # Normaliza document_ids para lista de strings
    if document_ids and isinstance(document_ids, list):
        doc_ids_pg = [str(d) for d in document_ids if d]
    else:
        doc_ids_pg = None

    try:
        resp = await asyncio.to_thread(
            lambda: db.rpc(
                "submit_pending_for_hitl",
                {
                    "p_client_id":    client_id,
                    "p_auto_submit":  True,
                    "p_document_ids": doc_ids_pg,
                },
            ).execute()
        )
        data = resp.data or {}
        if isinstance(data, list):
            data = data[0] if data else {}
    except Exception as exc:
        logger.warning("[routine_fn] biblioteca.submit_pending_for_hitl failed for %s: %s", client_id, exc)
        return {"pending_hitl_count": 0, "hitl_summary": f"⚠️ Erro ao submeter para HITL: {exc}"}

    submitted = int(data.get("submitted", 0))

    if submitted == 0:
        summary = "✅ Nenhum documento novo para submeter ao HITL."
    else:
        summary = f"📋 {submitted} documento(s) submetido(s) para aprovação (HITL). Aguardando revisão."

    logger.info("[routine_fn] biblioteca.submit_pending_for_hitl: client=%s submitted=%d", client_id, submitted)
    return {
        "pending_hitl_count": submitted,
        "hitl_summary":       summary,
    }


# ---------------------------------------------------------------------------
# compras.* — Procurement and inventory snapshots
# ---------------------------------------------------------------------------


@register(
    "compras.get_stock_levels",
    description="Retorna snapshot de niveis de estoque: SKUs abaixo do minimo, cobertura media em dias, e valor total em estoque.",
    inputs=[],
    outputs=[
        {"key": "stock_summary", "type": "str", "description": "Resumo markdown dos niveis de estoque"},
        {"key": "low_stock_count", "type": "int", "description": "SKUs abaixo do minimo"},
        {"key": "avg_coverage_days", "type": "float", "description": "Cobertura media em dias"},
    ],
)
async def _compras_get_stock_levels(inputs: dict, client_id: str) -> dict:
    from blu_supabase_client import get_supabase_client

    db = get_supabase_client(use_service_role=True)

    try:
        resp = await asyncio.to_thread(
            lambda: db.rpc(
                "get_stock_levels",
                {"p_client_id": client_id},
            ).execute()
        )
        data = resp.data or {}
        if isinstance(data, list):
            data = data[0] if data else {}
    except Exception as exc:
        logger.warning("[routine_fn] compras.get_stock_levels failed for %s: %s", client_id, exc)
        return {
            "stock_summary": "",
            "low_stock_count": 0,
            "avg_coverage_days": 0.0,
        }

    low_stock_count = int(data.get("low_stock_count", 0))
    avg_coverage_days = float(data.get("avg_coverage_days", 0.0) or 0.0)
    total_stock_value = float(
        data.get("total_stock_value", data.get("stock_total_value", 0.0)) or 0.0
    )

    stock_summary = (
        f"📦 {low_stock_count} SKUs abaixo do minimo | cobertura media: {avg_coverage_days:.1f}d "
        f"| estoque total: R${total_stock_value:,.2f}"
    )

    logger.info(
        "[routine_fn] compras.get_stock_levels: client=%s low_stock=%d coverage=%.1f total=%.2f",
        client_id,
        low_stock_count,
        avg_coverage_days,
        total_stock_value,
    )
    return {
        "stock_summary": stock_summary,
        "low_stock_count": low_stock_count,
        "avg_coverage_days": avg_coverage_days,
    }


@register(
    "compras.get_supplier_performance",
    description="Retorna performance de fornecedores: lead time medio, taxa de atraso, e fornecedores com alertas ativos.",
    inputs=[
        {"key": "lookback_days", "type": "int", "description": "Janela em dias (padrão 30)", "default": 30, "required": False},
    ],
    outputs=[
        {"key": "supplier_summary", "type": "str", "description": "Resumo markdown de fornecedores"},
        {"key": "delayed_supplier_count", "type": "int", "description": "Fornecedores com atraso ativo"},
        {"key": "avg_lead_time_days", "type": "float", "description": "Lead time medio em dias"},
    ],
)
async def _compras_get_supplier_performance(inputs: dict, client_id: str) -> dict:
    from blu_supabase_client import get_supabase_client

    lookback_days = int(inputs.get("lookback_days", 30))
    db = get_supabase_client(use_service_role=True)

    try:
        resp = await asyncio.to_thread(
            lambda: db.rpc(
                "get_supplier_performance",
                {"p_client_id": client_id, "p_lookback_days": lookback_days},
            ).execute()
        )
        data = resp.data or {}
        if isinstance(data, list):
            data = data[0] if data else {}
    except Exception as exc:
        logger.warning("[routine_fn] compras.get_supplier_performance failed for %s: %s", client_id, exc)
        return {
            "supplier_summary": "",
            "delayed_supplier_count": 0,
            "avg_lead_time_days": 0.0,
        }

    delayed_supplier_count = int(data.get("delayed_supplier_count", data.get("delayed_count", 0)))
    avg_lead_time_days = float(data.get("avg_lead_time_days", data.get("avg_lead_time", 0.0)) or 0.0)

    supplier_summary = f"🚚 {delayed_supplier_count} fornecedor(es) com atraso | lead time medio: {avg_lead_time_days:.1f}d"

    logger.info(
        "[routine_fn] compras.get_supplier_performance: client=%s delayed=%d lead_time=%.1f lookback_days=%d",
        client_id,
        delayed_supplier_count,
        avg_lead_time_days,
        lookback_days,
    )
    return {
        "supplier_summary": supplier_summary,
        "delayed_supplier_count": delayed_supplier_count,
        "avg_lead_time_days": avg_lead_time_days,
    }


@register(
    "compras.get_purchase_trends",
    description="Retorna tendencias de compras: volume, ticket medio, e variacao em relacao ao periodo anterior.",
    inputs=[
        {"key": "period_days", "type": "int", "description": "Período em dias (padrão 30)", "default": 30, "required": False},
    ],
    outputs=[
        {"key": "purchase_summary", "type": "str", "description": "Resumo markdown das tendencias"},
        {"key": "total_purchase_value", "type": "float", "description": "Valor total de compras no periodo"},
        {"key": "purchase_count", "type": "int", "description": "Numero de pedidos de compra"},
        {"key": "period_change_pct", "type": "float", "description": "Variacao percentual vs periodo anterior"},
    ],
)
async def _compras_get_purchase_trends(inputs: dict, client_id: str) -> dict:
    from blu_supabase_client import get_supabase_client

    period_days = int(inputs.get("period_days", 30))
    db = get_supabase_client(use_service_role=True)

    try:
        resp = await asyncio.to_thread(
            lambda: db.rpc(
                "get_purchase_trends",
                {"p_client_id": client_id, "p_period_days": period_days},
            ).execute()
        )
        data = resp.data or {}
        if isinstance(data, list):
            data = data[0] if data else {}
    except Exception as exc:
        logger.warning("[routine_fn] compras.get_purchase_trends failed for %s: %s", client_id, exc)
        return {
            "purchase_summary": "",
            "total_purchase_value": 0.0,
            "purchase_count": 0,
            "period_change_pct": 0.0,
        }

    total_purchase_value = float(data.get("total_purchase_value", data.get("total_value", 0.0)) or 0.0)
    purchase_count = int(data.get("purchase_count", data.get("count", 0)))
    period_change_pct = float(data.get("period_change_pct", data.get("change_pct", 0.0)) or 0.0)

    purchase_summary = (
        f"🛒 {purchase_count} compras | R${total_purchase_value:,.2f} "
        f"| variacao: {period_change_pct:+.1f}% vs periodo anterior"
    )

    logger.info(
        "[routine_fn] compras.get_purchase_trends: client=%s purchases=%d total=%.2f change=%.1f period_days=%d",
        client_id,
        purchase_count,
        total_purchase_value,
        period_change_pct,
        period_days,
    )
    return {
        "purchase_summary": purchase_summary,
        "total_purchase_value": total_purchase_value,
        "purchase_count": purchase_count,
        "period_change_pct": period_change_pct,
    }
