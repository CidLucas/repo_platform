"""Phase 4 (R4.3) — scheduled report dispatcher.

Polled by pg_cron (or a sidecar) at whatever cadence Ops decides; this
endpoint scans ``public.report_schedules`` for due rows via the
service-role helper :sql:`public.list_due_report_schedules` and runs
each one through :func:`report_module.generate_report_core`. Successful
runs flip ``last_run_at`` and recompute ``next_run_at``; failures are
already persisted to ``report_runs`` by the core itself.

Auth: shared bearer secret in ``REPORTS_DISPATCH_TOKEN`` (or the same
``DAILY_INSIGHTS_RUNNER_TOKEN`` fallback used elsewhere so Ops can wire
a single Vault entry).
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Header, HTTPException, status
from fastmcp.exceptions import ToolError

from vizu_supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/reports", tags=["Reports Internal"])


def _verify_token(authorization: str | None) -> None:
    expected = (
        os.getenv("REPORTS_DISPATCH_TOKEN")
        or os.getenv("DAILY_INSIGHTS_RUNNER_TOKEN")
        or os.getenv("RFQ_FOLLOW_UPS_TOKEN")
    )
    if not expected:
        return
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    token = authorization.split(" ", 1)[1].strip()
    if token != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


def _next_run_for(cadence: str) -> str:
    now = datetime.now(UTC)
    delta = {
        "daily":   timedelta(days=1),
        "weekly":  timedelta(days=7),
        "monthly": timedelta(days=30),
    }.get(cadence, timedelta(days=30))
    return (now + delta).isoformat()


@router.post("/run-scheduled")
async def run_scheduled_reports(
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    """Generate reports for every due schedule (up to 50 per call)."""
    _verify_token(authorization)

    from tool_pool_api.server.tool_modules.report_module import generate_report_core

    db = get_supabase_client()
    try:
        resp = db.rpc("list_due_report_schedules", {"p_limit": 50}).execute()
    except Exception:
        logger.exception("reports.dispatch: scan failed")
        raise HTTPException(status_code=500, detail="scan failed")

    rows = getattr(resp, "data", None) or []
    summary = {"scanned": len(rows), "generated": 0, "failed": 0}
    if not rows:
        return summary

    for sched in rows:
        sched_id    = sched["id"]
        client_id   = sched["client_id"]
        template_id = sched["template_id"]
        period      = sched.get("period") or "30d"
        fmt         = sched.get("format") or "pdf"
        cadence     = sched.get("cadence") or "monthly"

        try:
            await generate_report_core(
                cliente_id=client_id,
                template_id=template_id,
                period=period,
                format=fmt,
                schedule_id=sched_id,
            )
            summary["generated"] += 1
        except ToolError as exc:
            logger.warning(
                "reports.dispatch: tool error for schedule=%s: %s", sched_id, exc,
            )
            summary["failed"] += 1
        except Exception:
            logger.exception("reports.dispatch: unexpected failure for schedule=%s", sched_id)
            summary["failed"] += 1

        # Always advance the schedule cursor so a single broken template
        # doesn't pin the worker on the same row forever.
        try:
            db.table("report_schedules").update({
                "last_run_at": datetime.now(UTC).isoformat(),
                "next_run_at": _next_run_for(cadence),
            }).eq("id", sched_id).execute()
        except Exception:
            logger.exception("reports.dispatch: failed to advance schedule=%s", sched_id)

    return summary
