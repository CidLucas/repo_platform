"""Phase 4 (R4.1, R4.2, R4.4) — Report module.

The MVP report pipeline:

    1. Resolve the static template metadata from
       :mod:`report_templates`.
    2. Insert a ``report_runs`` row with ``status='running'``.
    3. Fetch the indicator block via the service-role dispatcher
       ``analytics_v2.get_indicator_block_for(p_client_id, p_template_id,
       p_period)``.
    4. (R4.4) Optionally pull the most recent KB summaries for the
       tenant (rows with ``category in ('agent_summary','analysis')``)
       so the LLM has agent-derived context to lean on.
    5. Compose a Markdown body via the LLM (DEFAULT tier).
    6. Convert the body to the requested format with the adapters in
       :mod:`report_format_adapters`. Google Docs / Sheets exports go
       through the existing ``blu_google_suite_client``.
    7. Persist the output URL / inline payload, flip ``status='success'``
       and stamp ``audit_log``.

The module exposes a single ctx-free core (:func:`generate_report_core`)
and an MCP-tool wrapper (:func:`_generate_report_logic`).
"""

from __future__ import annotations

import base64
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from blu_agent_framework import record_audit as _record_audit
from blu_auth.mcp.auth_middleware import mcp_inject_client_id
from blu_supabase_client import get_supabase_client

from . import register_module
from .report_format_adapters import to_markdown, to_pdf, to_xlsx
from .report_templates import (
    REPORT_TEMPLATES,
    ReportTemplate,
    get_template,
    list_templates,
    validate_format,
)

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────
# Indicator + KB context loaders
# ────────────────────────────────────────────────────────────────────────


def _fetch_indicator_block(
    db: Any, *, client_id: str, template_id: str, period: str
) -> dict[str, Any]:
    """Call the service-role dispatcher RPC."""
    try:
        resp = db.rpc(
            "get_indicator_block_for",
            {
                "p_client_id":   client_id,
                "p_template_id": template_id,
                "p_period":      period,
            },
        ).execute()
    except Exception as exc:
        logger.warning(
            "report_module: indicator dispatcher failed (template=%s, period=%s): %s",
            template_id, period, exc,
        )
        return {}
    data = getattr(resp, "data", None)
    if isinstance(data, dict):
        return data
    if isinstance(data, str):
        try:
            return json.loads(data)
        except Exception:
            return {}
    return {}


def _fetch_kb_context(
    db: Any, *, client_id: str, period: str, limit: int = 5
) -> list[dict[str, Any]]:
    """(R4.4) Pull recent KB summaries to enrich the report.

    Looks for rows in ``kb_documents`` (or ``client_knowledge`` as a
    fallback) flagged as agent summaries / analyses. Soft failure: if
    the table doesn't exist, return ``[]`` and continue.
    """
    cutoff = _resolve_period_cutoff(period)
    for table in ("kb_documents", "client_knowledge"):
        try:
            q = (
                db.table(table)
                .select("title,content,category,created_at,metadata")
                .eq("client_id", client_id)
                .in_("category", ["agent_summary", "analysis", "report"])
                .order("created_at", desc=True)
                .limit(limit)
            )
            if cutoff:
                q = q.gte("created_at", cutoff.isoformat())
            resp = q.execute()
            rows = getattr(resp, "data", None) or []
            if rows:
                return rows
        except Exception:
            continue
    return []


def _resolve_period_cutoff(period: str) -> datetime | None:
    p = (period or "").strip().lower()
    now = datetime.now(UTC)
    table = {
        "7d":  timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
        "mtd": timedelta(days=now.day),
        "ytd": timedelta(days=now.timetuple().tm_yday),
    }
    delta = table.get(p)
    if delta is None:
        return None
    return now - delta


# ────────────────────────────────────────────────────────────────────────
# LLM composition
# ────────────────────────────────────────────────────────────────────────


async def _compose_markdown(
    *,
    template: ReportTemplate,
    indicators: dict[str, Any],
    kb_summaries: list[dict[str, Any]],
    period: str,
) -> str:
    """Use the FAST-tier LLM to render a Markdown report."""
    from langchain_core.messages import HumanMessage, SystemMessage

    from blu_llm_service import get_model
    from blu_llm_service.client import ModelTier

    indicators_block = _format_indicators_for_prompt(indicators)
    kb_block = _format_kb_for_prompt(kb_summaries)

    user_payload = (
        f"Template: {template.title}\n"
        f"Período: {period}\n\n"
        f"Indicadores:\n{indicators_block}\n\n"
        f"Resumos recentes da base de conhecimento:\n{kb_block}\n\n"
        "Componha o relatório em Markdown seguindo as instruções do sistema."
    )

    model = get_model(
        tier=ModelTier.FAST,
        tags=["reports", template.domain, template.id],
    )
    response = await model.ainvoke([
        SystemMessage(content=template.system_prompt),
        HumanMessage(content=user_payload),
    ])
    text = (getattr(response, "content", None) or "").strip()
    if not text:
        # Defensive fallback so we never store an empty report.
        text = _builtin_fallback_markdown(
            template=template, indicators=indicators, period=period,
        )
    return text


def _format_indicators_for_prompt(indicators: dict[str, Any]) -> str:
    if not indicators:
        return "(sem indicadores disponíveis para o período)"
    lines = [f"- {k}: {v}" for k, v in indicators.items()]
    return "\n".join(lines)


def _format_kb_for_prompt(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "(nenhum resumo de agente recente)"
    chunks: list[str] = []
    for row in rows:
        title = (row.get("title") or "").strip() or "Resumo"
        content = (row.get("content") or "").strip()
        if len(content) > 800:
            content = content[:800].rstrip() + "…"
        chunks.append(f"### {title}\n{content}")
    return "\n\n".join(chunks)


def _builtin_fallback_markdown(
    *, template: ReportTemplate, indicators: dict[str, Any], period: str
) -> str:
    """Emergency fallback if the LLM call returns nothing."""
    lines = [
        f"# {template.title}",
        "",
        f"_Período: {period}_",
        "",
        "## Indicadores",
        "",
        "| Indicador | Valor |",
        "| --- | --- |",
    ]
    for key, value in (indicators or {}).items():
        lines.append(f"| {key} | {value} |")
    lines.extend([
        "",
        "## Observações",
        "",
        "Relatório gerado em modo de fallback (LLM indisponível).",
    ])
    return "\n".join(lines)


# ────────────────────────────────────────────────────────────────────────
# Format dispatch
# ────────────────────────────────────────────────────────────────────────


async def _emit_format(
    *,
    fmt: str,
    template: ReportTemplate,
    markdown_body: str,
    indicators: dict[str, Any],
    client_id: str,
) -> dict[str, Any]:
    """Convert the markdown body to the requested format. Returns a metadata
    dict that will be merged into the ``report_runs`` row."""

    if fmt == "markdown":
        body, mime, fname = to_markdown(markdown_body=markdown_body)
        return _inline_payload(body=body, mime=mime, filename=fname)

    if fmt == "pdf":
        body, mime, fname = to_pdf(markdown_body=markdown_body, title=template.title)
        return _inline_payload(body=body, mime=mime, filename=fname)

    if fmt == "xlsx":
        body, mime, fname = to_xlsx(
            markdown_body=markdown_body,
            title=template.title,
            indicators=indicators,
        )
        return _inline_payload(body=body, mime=mime, filename=fname)

    if fmt == "gdoc":
        return await _export_gdoc(
            client_id=client_id,
            template=template,
            markdown_body=markdown_body,
        )

    if fmt == "gsheet":
        return await _export_gsheet(
            client_id=client_id,
            template=template,
            indicators=indicators,
            markdown_body=markdown_body,
        )

    raise ToolError(f"Unsupported report format '{fmt}'")


def _inline_payload(*, body: bytes, mime: str, filename: str) -> dict[str, Any]:
    return {
        "output_url": None,
        "output_metadata": {
            "mime_type":   mime,
            "filename":    filename,
            "size_bytes":  len(body),
            "payload_b64": base64.b64encode(body).decode("ascii"),
        },
    }


async def _export_gdoc(
    *,
    client_id: str,
    template: ReportTemplate,
    markdown_body: str,
) -> dict[str, Any]:
    from blu_google_suite_client import GoogleDocsClient

    tokens = await _get_google_tokens(client_id)
    client = GoogleDocsClient(access_token=tokens["access_token"])

    title = f"{template.title} — {datetime.now(UTC).strftime('%Y-%m-%d')}"
    doc = await client.create_document(title)
    doc_id = doc["document_id"]
    await client.append_text(doc_id, markdown_body)

    return {
        "output_url": doc.get("document_url")
        or f"https://docs.google.com/document/d/{doc_id}",
        "output_metadata": {
            "mime_type":   "application/vnd.google-apps.document",
            "document_id": doc_id,
            "title":       title,
        },
    }


async def _export_gsheet(
    *,
    client_id: str,
    template: ReportTemplate,
    indicators: dict[str, Any],
    markdown_body: str,
) -> dict[str, Any]:
    from blu_google_suite_client import GoogleSheetsClient

    tokens = await _get_google_tokens(client_id)
    client = GoogleSheetsClient(access_token=tokens["access_token"])

    title = f"{template.title} — {datetime.now(UTC).strftime('%Y-%m-%d')}"
    sheet = await client.create_spreadsheet(title)
    spreadsheet_id = sheet["spreadsheet_id"]

    rows: list[list[Any]] = [["Indicador", "Valor"]]
    for k, v in (indicators or {}).items():
        rows.append([str(k), v if v is not None else ""])
    rows.append([])
    rows.append(["Relatório (Markdown)"])
    for line in markdown_body.splitlines():
        rows.append([line])

    await client.append_values(spreadsheet_id, "A1", rows)

    return {
        "output_url": sheet.get("spreadsheet_url")
        or f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
        "output_metadata": {
            "mime_type":      "application/vnd.google-apps.spreadsheet",
            "spreadsheet_id": spreadsheet_id,
            "title":          title,
        },
    }


async def _get_google_tokens(client_id: str) -> dict[str, Any]:
    """Re-uses the integration_tokens path the RFQ module already wired."""
    from uuid import UUID

    from tool_pool_api.server.dependencies import get_context_service

    ctx_service = get_context_service()
    wrapper = await ctx_service.get_integration_tokens(
        UUID(client_id), "google", auto_refresh=True,
    )
    if not wrapper or not wrapper.is_valid():
        raise ToolError(
            "Integração Google não configurada ou expirada. "
            "Reconecte sua conta Google nas configurações."
        )
    return wrapper.get_decrypted_tokens()


# ────────────────────────────────────────────────────────────────────────
# Public core
# ────────────────────────────────────────────────────────────────────────


async def generate_report_core(
    *,
    client_id: str,
    template_id: str,
    period: str | None = None,
    format: str | None = None,
    schedule_id: str | None = None,
    requested_by: str | None = None,
) -> dict[str, Any]:
    """Generate a report and persist the run.

    Returns a dict with at least ``run_id, status, format, template_id,
    output_url, output_metadata``.
    """
    if not client_id:
        raise ToolError("Missing client_id")

    template = get_template(template_id)
    fmt = validate_format(format or template.default_format)
    period = (period or template.default_period).strip().lower()

    db = get_supabase_client()

    # Insert pending run.
    insert_payload = {
        "client_id":    client_id,
        "template_id":  template_id,
        "period":       period,
        "format":       fmt,
        "status":       "running",
        "started_at":   datetime.now(UTC).isoformat(),
        "schedule_id":  schedule_id,
        "requested_by": requested_by,
    }
    insert_resp = db.table("report_runs").insert(insert_payload).execute()
    rows = getattr(insert_resp, "data", None) or []
    if not rows:
        raise ToolError("Failed to create report_runs row")
    run_id = rows[0]["id"]

    try:
        indicators = _fetch_indicator_block(
            db, client_id=client_id, template_id=template_id, period=period,
        )

        kb = []
        if template.include_kb_summaries:
            kb = _fetch_kb_context(db, client_id=client_id, period=period, limit=5)

        markdown_body = await _compose_markdown(
            template=template,
            indicators=indicators,
            kb_summaries=kb,
            period=period,
        )

        emit = await _emit_format(
            fmt=fmt,
            template=template,
            markdown_body=markdown_body,
            indicators=indicators,
            client_id=client_id,
        )

        # Always preserve the markdown body in metadata so the dashboard
        # can render an inline preview regardless of the export format.
        output_metadata = dict(emit.get("output_metadata") or {})
        output_metadata.setdefault("markdown_preview", markdown_body[:4000])
        output_metadata["template_id"] = template_id
        output_metadata["template_title"] = template.title
        output_metadata["period"] = period
        output_metadata["indicator_keys"] = list(indicators.keys())
        output_metadata["kb_summaries_used"] = len(kb)

        update_payload = {
            "status":          "success",
            "output_url":      emit.get("output_url"),
            "output_metadata": output_metadata,
            "finished_at":     datetime.now(UTC).isoformat(),
            "error_message":   None,
        }
        db.table("report_runs").update(update_payload).eq("id", run_id).execute()

        _record_audit(
            db,
            p_action="reports.generate",
            p_payload={
                "template_id": template_id,
                "period":      period,
                "format":      fmt,
                "run_id":      run_id,
                "schedule_id": schedule_id,
            },
            p_resource="report_runs",
            p_resource_id=run_id,
            p_actor_kind="agent" if not requested_by else "user",
            p_agent_slug="report-composer",
            p_outcome="success",
            p_client_id=client_id,
        )

        return {
            "run_id":          run_id,
            "status":          "success",
            "template_id":     template_id,
            "format":          fmt,
            "period":          period,
            "output_url":      emit.get("output_url"),
            "output_metadata": output_metadata,
        }

    except Exception as exc:
        message = str(exc) or exc.__class__.__name__
        try:
            db.table("report_runs").update({
                "status":        "failed",
                "finished_at":   datetime.now(UTC).isoformat(),
                "error_message": message[:1000],
            }).eq("id", run_id).execute()
        except Exception:
            logger.exception("report_module: failed to mark run failed")

        _record_audit(
            db,
            p_action="reports.generate",
            p_payload={
                "template_id": template_id, "period": period,
                "format": fmt, "run_id": run_id, "error": message[:500],
            },
            p_resource="report_runs",
            p_resource_id=run_id,
            p_actor_kind="agent",
            p_agent_slug="report-composer",
            p_outcome="failure",
            p_client_id=client_id,
        )

        if isinstance(exc, ToolError):
            raise
        logger.exception("report_module: generation failed for client=%s", client_id)
        raise ToolError(f"Falha ao gerar relatório: {message}") from exc


# ────────────────────────────────────────────────────────────────────────
# MCP tool registration
# ────────────────────────────────────────────────────────────────────────


async def _list_report_templates_logic() -> dict[str, Any]:
    """MCP tool: return the static template catalog."""
    return {"templates": list_templates()}


async def _generate_report_logic(
    template_id: str,
    period: str | None = None,
    format: str | None = None,
    client_id: str | None = None,
) -> dict[str, Any]:
    """MCP wrapper around :func:`generate_report_core`.

    The MCP layer injects ``client_id`` via the lifespan context middleware
    (same pattern as the rfq tools).
    """
    if not client_id:
        raise ToolError("Missing client_id in context")
    return await generate_report_core(
        client_id=client_id,
        template_id=template_id,
        period=period,
        format=format,
    )


@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    from tool_pool_api.server.dependencies import get_context_service

    mcp.tool(
        name="list_report_templates",
        description=(
            "Lista os templates de relatório disponíveis para o tenant. "
            "Retorna id, título, descrição, domínio, período e formato padrão."
        ),
    )(_list_report_templates_logic)

    mcp.tool(
        name="generate_report",
        description=(
            "Gera um relatório em Markdown / PDF / XLSX / Google Doc / "
            "Google Sheets para o tenant atual. Templates suportados: "
            + ", ".join(REPORT_TEMPLATES.keys())
        ),
    )(mcp_inject_client_id(get_context_service)(_generate_report_logic))

    return ["list_report_templates", "generate_report"]
