"""Context report HTTP router — replaces supabase/functions/generate-context-report/.

Mounted at /v1/internal/context-report in services/agent_api/src/agent_api/main.py.

Phase 4.1 (M7) of the edge-functions rationalization plan: the Deno EF
was a 610 LOC TypeScript port of the Python
``blu_agent_framework.routines.context_report.run_for_client`` routine.
Python can do the same thing in-process, so the EF is dead code.

This endpoint is the in-process Python replacement. It mirrors the EF
behaviour:

  - Fire-and-forget: returns 202 immediately, runs the heavy
    ``run_for_client`` (30-60s) in a FastAPI BackgroundTask. The caller
    (``onboarding-bootstrap``) uses ``EdgeRuntime.waitUntil`` on its
    side to avoid blocking the user response.
  - Returns ``{"skipped": true, ...}`` if the routine reports no data
    yet (the EF's contract).
  - Auth: static shared token via ``CONTEXT_REPORT_TOKEN`` env var
    (same pattern as ``routines_router._verify_token`` for the
    run-dispatched endpoint). The onboarding-bootstrap EF is the only
    caller and sets the same token on its end.

Callers:
  - supabase/functions/onboarding-bootstrap/index.ts:162 (was the Deno EF)

Replaces:
  - supabase/functions/generate-context-report/index.ts (DELETED in
    this phase, along with its config block).
  - public.schedule_monthly_context_reports() — orphan SQL function
    with no cron job calling it, dropped via migration in this phase.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from pydantic import BaseModel, Field

from agent_api.config import get_settings
from agent_api.core.routine_functions import _generate_context_report

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/context-report", tags=["context-report"])


# ── Request / Response schemas ────────────────────────────────────────


class ContextReportRequest(BaseModel):
    client_id: str = Field(..., description="Client UUID to generate the report for")


class ContextReportAccepted(BaseModel):
    status: str = "accepted"
    client_id: str
    message: str = "Context report scheduled in background"


# ── Auth ──────────────────────────────────────────────────────────────


def _verify_token(authorization: str | None) -> None:
    """Static shared-token auth, same pattern as routines_router._verify_token.

    The token is shared with ``onboarding-bootstrap`` (set on both sides
    via the ``CONTEXT_REPORT_TOKEN`` env var).  No service-role key is
    needed because the routine runs under the agent_api service identity
    and reads via its own DB connection.
    """
    settings = get_settings()
    expected = settings.CONTEXT_REPORT_TOKEN
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="CONTEXT_REPORT_TOKEN not configured on agent_api",
        )
    if authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Unauthorized")


# ── Endpoint ──────────────────────────────────────────────────────────


@router.post("", status_code=202, response_model=ContextReportAccepted)
async def trigger_context_report(
    body: ContextReportRequest,
    background_tasks: BackgroundTasks,
    request: Request,
) -> ContextReportAccepted:
    """Trigger the context report for ``client_id`` in a background task.

    Returns 202 immediately. The report run takes 30-60s, well beyond
    any reasonable HTTP timeout, so we offload it to FastAPI's
    BackgroundTask (analogous to Deno's ``EdgeRuntime.waitUntil``).
    """
    _verify_token(request.headers.get("authorization"))

    client_id = body.client_id
    logger.info("[ContextReport] Triggering report for client %s", client_id)

    background_tasks.add_task(
        _run_context_report_safe, client_id=client_id
    )

    return ContextReportAccepted(
        client_id=client_id,
        message="Context report scheduled in background",
    )


# ── Background task wrapper ──────────────────────────────────────────


async def _run_context_report_safe(client_id: str) -> None:
    """Run ``_generate_context_report`` and log the outcome.

    Wraps the routine so that any unhandled exception is caught and
    logged — a failed background task must not crash the FastAPI worker
    or surface as a 500 (we already returned 202 to the caller).
    """
    try:
        result = await _generate_context_report({}, client_id)
        logger.info(
            "[ContextReport] Done for client %s: %s",
            client_id,
            result.get("context_report_summary", "<no summary>"),
        )
    except Exception as exc:
        logger.error(
            "[ContextReport] Background run failed for client %s: %s",
            client_id,
            exc,
            exc_info=True,
        )
