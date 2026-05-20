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
            .select("website_url")
            .eq("client_id", client_id)
            .maybe_single()
            .execute()
        )
        if row.data:
            url = row.data.get("website_url") or ""

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

