"""
Routines router.

POST /v1/internal/routines/run-dispatched
  Called by pg_cron/pg_net every minute.  Returns 202 immediately and
  processes claimed executions in a FastAPI BackgroundTask.

GET /v1/routines/catalog
  Returns all registered functions, artifacts and skill slugs — the live
  source of truth for what steps can be used in cross_agent_routines.
"""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException

from agent_api.api.auth import AuthResult, get_auth_result
from agent_api.config import get_settings
from agent_api.core.factory import get_context_service
from agent_api.core.routines import (
    check_and_enqueue_triggers,
    claim_dispatched_batch,
    enqueue_manual_run,
    run_dispatched_executions,
)

logger = logging.getLogger(__name__)

# Two sub-routers: internal dispatch + public catalog
router = APIRouter(tags=["routines"])
_internal = APIRouter(prefix="/internal/routines")
_public = APIRouter(prefix="/routines")


def _verify_token(authorization: str | None) -> None:
    settings = get_settings()
    expected = settings.ROUTINE_DISPATCH_TOKEN
    if not expected:
        raise HTTPException(status_code=503, detail="ROUTINE_DISPATCH_TOKEN not configured")
    if authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Unauthorized")


@_internal.post("/run-dispatched", status_code=202)
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

    # Phase 7: check cron/numeric triggers first — enqueues any due executions so
    # the claim loop below picks them up in the same tick
    await check_and_enqueue_triggers()

    claimed = await claim_dispatched_batch(batch_size=settings.ROUTINE_BATCH_SIZE)

    if claimed:
        background_tasks.add_task(run_dispatched_executions, claimed, context_service)
        logger.info("[RoutineDispatch] Claimed %d executions for background processing", len(claimed))
    else:
        logger.debug("[RoutineDispatch] No dispatched executions found")

    return {"status": "claimed", "count": len(claimed)}


# ---------------------------------------------------------------------------
# Manual dispatch — "Rodar agora" button in the routines panel
# ---------------------------------------------------------------------------


@_public.post("/{routine_id}/run", status_code=202)
async def run_routine_now(
    routine_id: str,
    background_tasks: BackgroundTasks,
    auth_result: AuthResult = Depends(get_auth_result),
) -> dict:
    """
    Dispatch a routine execution immediately for the authenticated client,
    bypassing the cron schedule. The execution is claimed and processed in a
    background task, so the endpoint returns 202 with the execution id.
    """
    client_id = str(auth_result.client_id)

    try:
        exec_id = await enqueue_manual_run(routine_id, client_id)
    except LookupError:
        raise HTTPException(
            status_code=404,
            detail=f"Rotina '{routine_id}' não está ativa para este cliente",
        )

    if not exec_id:
        raise HTTPException(
            status_code=409,
            detail="Já existe uma execução em andamento para esta rotina",
        )

    settings = get_settings()
    claimed = await claim_dispatched_batch(batch_size=settings.ROUTINE_BATCH_SIZE)
    if claimed:
        background_tasks.add_task(run_dispatched_executions, claimed, get_context_service())
        logger.info(
            "[RoutineManual] routine=%s client=%s exec=%s — claimed %d execution(s)",
            routine_id, client_id, exec_id, len(claimed),
        )

    return {"status": "dispatched", "execution_id": exec_id}


# ---------------------------------------------------------------------------
# Public catalog — live registries
# ---------------------------------------------------------------------------


@_public.get("/catalog")
async def get_routine_catalog() -> dict:
    """
    Return every step primitive available for building routines.

    - functions  : registered in routine_functions._REGISTRY (with metadata)
    - artifacts  : registered in routine_artifacts._REGISTRY (with metadata)
    - skills     : all agent slugs from AgentTypeRegistry (with descriptions)
    - triggers   : available trigger types with config schemas
    """
    from blu_agent_framework.registry import AgentTypeRegistry
    from blu_agent_framework.skills import SKILL_REGISTRY

    from agent_api.core.routine_artifacts import list_artifacts_with_meta
    from agent_api.core.routine_functions import list_functions_with_meta
    from agent_api.core.routines import list_numeric_metrics

    # Agents available as skill executors in routine steps (new system only)
    _NEW_SYSTEM_AGENTS = {"orchestrator", "frontdesk", "context-gatherer"}

    skills = [
        {
            "id": slug,
            "label": slug.replace("-", " ").title(),
            "description": f"Agente {slug}",
        }
        for slug in sorted(AgentTypeRegistry.all().keys())
        if slug in _NEW_SYSTEM_AGENTS
    ]

    # Also expose L3 skill definitions from SKILL_REGISTRY so the builder
    # can reference individual skills directly (skill_slug = skill.name).
    # These are invoked by the orchestrator/context-gatherer, not by old agent slugs.
    l3_skills = [
        {
            "id": s.name,
            "label": s.name.replace("_", " ").title(),
            "description": s.description,
            "tags": s.tags,
            "kind": "l3_skill",  # UI can distinguish from agent-executor skills
        }
        for s in SKILL_REGISTRY.values()
        if "l3" in (s.tags or [])
    ]

    triggers = [
        {
            "id": "manual",
            "label": "Manual",
            "description": "Disparada sob demanda a partir do painel ou do chat.",
            "config_schema": [],
        },
        {
            "id": "schedule",
            "label": "Agendada",
            "description": "Executa automaticamente em horários definidos (cron).",
            "config_schema": [
                {"key": "expression", "type": "str", "description": "Expressão cron (ex: 0 9 * * 1 = segunda às 9h)", "required": True},
            ],
        },
        {
            "id": "event",
            "label": "Evento",
            "description": "Dispara quando um evento específico ocorre na plataforma.",
            "config_schema": [
                {
                    "key": "event_type",
                    "type": "select",
                    "description": "Tipo de evento que dispara a rotina",
                    "required": True,
                    "options": [
                        {"value": "ingestion_completed", "label": "Ingestão de dados concluída"},
                        {"value": "onboarding_completed", "label": "Onboarding do cliente concluído"},
                        {"value": "monthly_close", "label": "Fechamento mensal"},
                        {"value": "new_integration", "label": "Nova integração conectada"},
                        {"value": "document_created", "label": "Documento criado"},
                    ],
                },
                {"key": "cooldown_hours", "type": "int", "description": "Intervalo mínimo entre execuções (horas)", "default": 1, "required": False},
            ],
        },
        {
            "id": "numeric",
            "label": "Monitoramento",
            "description": "Dispara quando uma métrica cai abaixo de um limite definido.",
            "config_schema": [
                {
                    "key": "metric",
                    "type": "select",
                    "description": "Métrica a monitorar",
                    "required": True,
                    "options": list_numeric_metrics(),
                },
                {
                    "key": "threshold",
                    "type": "float",
                    "description": "Fração do histórico que dispara o alerta (ex: 0.85 = queda > 15%)",
                    "required": True,
                    "default": 0.85,
                },
                {"key": "window_months", "type": "int", "description": "Janela de comparação em meses", "default": 1, "required": False},
                {"key": "cooldown_hours", "type": "int", "description": "Intervalo mínimo entre execuções (horas)", "default": 24, "required": False},
            ],
        },
    ]

    return {
        "functions": list_functions_with_meta(),
        "artifacts": list_artifacts_with_meta(),
        "skills": skills,
        "l3_skills": l3_skills,
        "triggers": triggers,
        # legacy flat lists — kept for backward compat
        "skill_slugs": [s["id"] for s in skills],
    }


# Wire sub-routers into the exported router
router.include_router(_internal)
router.include_router(_public)
