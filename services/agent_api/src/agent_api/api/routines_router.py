"""
Internal router for pg_cron routine dispatch.

POST /v1/internal/routines/run-dispatched
  Called by pg_cron/pg_net every minute.  Returns 202 immediately and
  processes claimed executions in a FastAPI BackgroundTask.
"""

import logging

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException

from agent_api.config import get_settings
from agent_api.core.factory import get_context_service
from agent_api.core.routines import claim_dispatched_batch, run_dispatched_executions

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/internal/routines", tags=["routines-internal"])


def _verify_token(authorization: str | None) -> None:
    settings = get_settings()
    expected = settings.ROUTINE_DISPATCH_TOKEN
    if not expected:
        raise HTTPException(status_code=503, detail="ROUTINE_DISPATCH_TOKEN not configured")
    if authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.post("/run-dispatched", status_code=202)
async def run_dispatched(
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(default=None),
) -> dict:
    """
    Claim dispatched routine executions and process them in a background task.

    Returns 202 immediately so pg_net's 30 s timeout is never hit.
    """
    _verify_token(authorization)

    settings = get_settings()
    context_service = get_context_service()

    claimed = await claim_dispatched_batch(batch_size=settings.ROUTINE_BATCH_SIZE)

    if claimed:
        background_tasks.add_task(run_dispatched_executions, claimed, context_service)
        logger.info("[RoutineDispatch] Claimed %d executions for background processing", len(claimed))
    else:
        logger.debug("[RoutineDispatch] No dispatched executions found")

    return {"status": "claimed", "count": len(claimed)}
