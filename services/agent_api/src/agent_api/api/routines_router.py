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

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException

from agent_api.config import get_settings
from agent_api.core.factory import get_context_service
from agent_api.core.routines import (
    check_and_enqueue_triggers,
    claim_dispatched_batch,
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

    from agent_api.core.routine_artifacts import list_artifacts_with_meta
    from agent_api.core.routine_functions import list_functions_with_meta

    _SKILL_DESCRIPTIONS: dict[str, str] = {
        "financeiro": "Analisa dados financeiros, fluxo de caixa e rentabilidade. Gera insights e recomendações.",
        "compras": "Avalia estoque, giro de produtos e sugere pedidos de reposição.",
        "estrategia": "Cria planos estratégicos, metas e análises de mercado.",
        "clientes": "Analisa base de clientes, churn, segmentação e oportunidades de reengajamento.",
        "agenda": "Planeja e organiza calendário, lembretes e tarefas.",
        "documentos": "Gera, resume e processa documentos e relatórios.",
        "context-gatherer": "Consolida contexto do cliente a partir de múltiplas fontes de dados.",
    }

    skills = [
        {
            "id": slug,
            "label": slug.replace("-", " ").title(),
            "description": _SKILL_DESCRIPTIONS.get(slug, f"Agente {slug}"),
        }
        for slug in sorted(AgentTypeRegistry.all().keys())
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
            "description": "Dispara quando uma métrica ultrapassa um limite definido.",
            "config_schema": [
                {"key": "metric", "type": "str", "description": "Nome da métrica monitorada (ex: new_clients_monthly_rate)", "required": True},
                {"key": "threshold", "type": "float", "description": "Valor limite que dispara a rotina", "required": True},
                {"key": "window_months", "type": "int", "description": "Janela de avaliação em meses", "default": 1, "required": False},
                {"key": "cooldown_hours", "type": "int", "description": "Intervalo mínimo entre execuções (horas)", "default": 24, "required": False},
            ],
        },
    ]

    return {
        "functions": list_functions_with_meta(),
        "artifacts": list_artifacts_with_meta(),
        "skills": skills,
        "triggers": triggers,
        # legacy flat lists — kept for backward compat
        "skill_slugs": [s["id"] for s in skills],
    }


# Wire sub-routers into the exported router
router.include_router(_internal)
router.include_router(_public)
