"""Phase 4 (R4.3) — Reports REST endpoints for the dashboard.

These endpoints all run under the dashboard user JWT (same pattern as
the inbox endpoints): the JWT is decoded to derive ``client_id`` and
PostgREST is bound to the user JWT so the ``security_invoker`` RPCs
filter correctly.

Routes (prefix ``/integrations/reports``):
    GET  /templates
    GET  /runs
    GET  /runs/{run_id}/payload
    POST /generate
    GET  /schedules
    POST /schedules                    create or update
    POST /schedules/{schedule_id}/disable
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field

from tool_pool_api.api.integrations_router import _get_auth_result
from vizu_auth.core.models import AuthResult
from vizu_supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations/reports", tags=["Reports"])

bearer_scheme = HTTPBearer(auto_error=False)


# ────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────


def _supabase_with_user_jwt(jwt_token: str):
    """Bind a fresh Supabase client to the dashboard user's JWT so RLS /
    security-invoker RPCs see ``get_my_client_id()`` correctly."""
    db = get_supabase_client()
    try:
        db.postgrest.auth(jwt_token)
    except Exception:
        logger.debug("reports: could not attach user JWT to postgrest client", exc_info=True)
    return db


def _next_run_for(cadence: str) -> str:
    """Compute next_run_at given a cadence label."""
    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)
    delta = {
        "daily":   timedelta(days=1),
        "weekly":  timedelta(days=7),
        "monthly": timedelta(days=30),
    }.get(cadence, timedelta(days=30))
    return (now + delta).isoformat()


# ────────────────────────────────────────────────────────────────────────
# Schemas
# ────────────────────────────────────────────────────────────────────────


class GenerateReportRequest(BaseModel):
    template_id: str
    period: str | None = None
    format: str | None = None


class ScheduleRequest(BaseModel):
    template_id: str
    period: str = "30d"
    format: str = "pdf"
    cadence: str = Field(default="monthly", pattern="^(daily|weekly|monthly)$")
    notify_channel: str = Field(default="app", pattern="^(app|email|whatsapp)$")
    enabled: bool = True
    config: dict[str, Any] | None = None


# ────────────────────────────────────────────────────────────────────────
# Endpoints
# ────────────────────────────────────────────────────────────────────────


@router.get("/templates")
async def get_templates(
    auth: AuthResult = Depends(_get_auth_result),
):
    """Return the static template catalog (no DB hit)."""
    from tool_pool_api.server.tool_modules.report_templates import list_templates

    return {"templates": list_templates()}


@router.get("/runs")
async def list_runs(
    limit: int = Query(default=50, ge=1, le=200),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth: AuthResult = Depends(_get_auth_result),
):
    """List the tenant's recent report runs."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    db = _supabase_with_user_jwt(credentials.credentials)
    try:
        resp = db.rpc("list_report_runs", {"p_limit": limit}).execute()
    except Exception as exc:
        logger.exception("reports.list_runs failed for client=%s", auth.client_id)
        raise HTTPException(status_code=500, detail=str(exc))
    return {"runs": getattr(resp, "data", None) or []}


@router.get("/runs/{run_id}/payload")
async def fetch_run_payload(
    run_id: str,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth: AuthResult = Depends(_get_auth_result),
):
    """Return the inline payload (markdown / PDF / XLSX) of a finished run.

    For ``gdoc`` / ``gsheet`` runs the dashboard should redirect the user
    to ``output_url`` directly — this endpoint returns ``404`` for those.
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    db = _supabase_with_user_jwt(credentials.credentials)
    try:
        resp = (
            db.table("report_runs")
            .select("id,format,output_metadata,status")
            .eq("id", run_id)
            .single()
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    row = getattr(resp, "data", None)
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")
    if row.get("status") != "success":
        raise HTTPException(status_code=409, detail=f"Run status: {row.get('status')}")

    md = row.get("output_metadata") or {}
    payload_b64 = md.get("payload_b64")
    if not payload_b64:
        raise HTTPException(
            status_code=404,
            detail="Run has no inline payload (likely a Google Doc/Sheet — use output_url).",
        )
    return {
        "run_id":     row["id"],
        "format":     row["format"],
        "mime_type":  md.get("mime_type"),
        "filename":   md.get("filename"),
        "size_bytes": md.get("size_bytes"),
        "payload_b64": payload_b64,
    }


@router.post("/generate")
async def generate_report(
    payload: GenerateReportRequest,
    auth: AuthResult = Depends(_get_auth_result),
):
    """Generate a report synchronously. Returns the run summary."""
    from tool_pool_api.server.tool_modules.report_module import generate_report_core

    try:
        return await generate_report_core(
            cliente_id=str(auth.client_id),
            template_id=payload.template_id,
            period=payload.period,
            format=payload.format,
            requested_by=str(auth.client_id),
        )
    except ToolError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/schedules")
async def list_schedules(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth: AuthResult = Depends(_get_auth_result),
):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    db = _supabase_with_user_jwt(credentials.credentials)
    try:
        resp = db.rpc("list_report_schedules", {}).execute()
    except Exception as exc:
        logger.exception("reports.list_schedules failed")
        raise HTTPException(status_code=500, detail=str(exc))
    return {"schedules": getattr(resp, "data", None) or []}


@router.post("/schedules")
async def upsert_schedule(
    payload: ScheduleRequest = Body(...),
    auth: AuthResult = Depends(_get_auth_result),
):
    """Create or update a schedule for the calling tenant.

    Uses the service-role client so the constraint
    ``UNIQUE(client_id, template_id, cadence)`` triggers an upsert with a
    deterministic ``next_run_at``.
    """
    from tool_pool_api.server.tool_modules.report_templates import (
        get_template,
        validate_format,
    )

    try:
        get_template(payload.template_id)
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Unknown template '{payload.template_id}'")
    try:
        fmt = validate_format(payload.format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    db = get_supabase_client()
    record = {
        "client_id":      str(auth.client_id),
        "template_id":    payload.template_id,
        "period":         payload.period,
        "format":         fmt,
        "cadence":        payload.cadence,
        "notify_channel": payload.notify_channel,
        "enabled":        payload.enabled,
        "next_run_at":    _next_run_for(payload.cadence),
        "config":         payload.config or {},
    }
    try:
        resp = (
            db.table("report_schedules")
            .upsert(record, on_conflict="client_id,template_id,cadence")
            .execute()
        )
    except Exception as exc:
        logger.exception("reports.upsert_schedule failed")
        raise HTTPException(status_code=400, detail=str(exc))
    rows = getattr(resp, "data", None) or []
    if not rows:
        raise HTTPException(status_code=500, detail="upsert returned no rows")
    return rows[0]


@router.post("/schedules/{schedule_id}/disable")
async def disable_schedule(
    schedule_id: str,
    auth: AuthResult = Depends(_get_auth_result),
):
    db = get_supabase_client()
    try:
        UUID(schedule_id)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid schedule_id")
    try:
        resp = (
            db.table("report_schedules")
            .update({"enabled": False})
            .eq("id", schedule_id)
            .eq("client_id", str(auth.client_id))
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    rows = getattr(resp, "data", None) or []
    if not rows:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return rows[0]
