# tool_pool_api/server/tool_modules/routines_module.py
"""
Módulo Rotinas - Ferramentas para criação e gestão de rotinas via chat

Permite que agentes conversacionais criem, listem e gerenciem rotinas
personalizadas e de catálogo em nome dos clientes.
"""

import logging
from uuid import uuid4

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from blu_auth.mcp.auth_middleware import mcp_inject_client_id
from blu_supabase_client import get_supabase_client
from tool_pool_api.server.dependencies import get_context_service

from tool_pool_api.server.tool_modules import register_module

logger = logging.getLogger(__name__)


# =============================================================================
# LÓGICA DE NEGÓCIO
# =============================================================================


async def _listar_rotinas_catalogo_logic(
    ctx: Context,
    client_id: str | None = None,
) -> dict:
    """
    List all catalog routines available for the client's domain, along with
    their current activation status for this client.

    Returns a list of catalog routines with fields:
      - id: routine identifier
      - name: routine name
      - active: whether this client has it active (null = not configured)
      - status: client's status for this routine (null = not configured)
      - config: client's custom config for this routine
    """
    if not client_id:
        raise ToolError("client_id não encontrado. Certifique-se de estar autenticado.")

    try:
        db = get_supabase_client()

        catalog_result = await db.table("cross_agent_routines").select(
            "id, name, trigger_domain, config_schema"
        ).execute()

        catalog_routines = catalog_result.data or []

        client_result = await db.table("client_routines").select(
            "routine_id, active, status, config"
        ).eq("client_id", client_id).eq("source", "catalog").execute()

        client_map = {r["routine_id"]: r for r in (client_result.data or [])}

        enriched = []
        for routine in catalog_routines:
            cr = client_map.get(routine["id"])
            enriched.append({
                "id": routine["id"],
                "name": routine["name"],
                "trigger_domain": routine.get("trigger_domain"),
                "active": cr["active"] if cr else False,
                "status": cr["status"] if cr else "inactive",
                "config": cr["config"] if cr else {},
                "config_schema": routine.get("config_schema", []),
            })

        logger.info(f"[Rotinas] Listou {len(enriched)} rotinas de catálogo para {client_id}")
        return {"rotinas": enriched, "total": len(enriched)}

    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Rotinas] Erro ao listar rotinas de catálogo: {e}")
        raise ToolError(f"Erro ao listar rotinas de catálogo: {e}")


async def _listar_rotinas_personalizadas_logic(
    ctx: Context,
    client_id: str | None = None,
) -> dict:
    """
    List the client's custom (non-catalog) routines with their current status.

    Returns routines created by the client (via chat or QuickBuilder), including
    draft, pending_approval, and active routines.
    """
    if not client_id:
        raise ToolError("client_id não encontrado. Certifique-se de estar autenticado.")

    try:
        db = get_supabase_client()

        result = await db.table("client_routines").select(
            "id, name, description, status, active, steps, trigger_type, trigger_config, created_by_ai, created_at"
        ).eq("client_id", client_id).eq("source", "custom").order("created_at", desc=True).execute()

        rotinas = result.data or []
        logger.info(f"[Rotinas] Listou {len(rotinas)} rotinas personalizadas para {client_id}")
        return {"rotinas": rotinas, "total": len(rotinas)}

    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Rotinas] Erro ao listar rotinas personalizadas: {e}")
        raise ToolError(f"Erro ao listar rotinas personalizadas: {e}")


async def _criar_rotina_personalizada_logic(
    name: str,
    steps: list,
    ctx: Context,
    description: str | None = None,
    trigger_type: str = "manual",
    client_id: str | None = None,
) -> dict:
    """
    Create a new custom routine as a draft.

    Args:
        name: Human-readable name for the routine (e.g., "Relatório semanal de vendas")
        steps: List of step objects. Each step: {"step": <int>, "agent": "<slug>", "action": "<action_id>", "input": {...}}
        description: Optional description of what this routine does
        trigger_type: One of "manual", "schedule", "document", "event" (default: "manual")

    The routine is created with status="draft". Call enviar_rotina_para_aprovacao
    to submit it for activation.
    """
    if not client_id:
        raise ToolError("client_id não encontrado. Certifique-se de estar autenticado.")

    if not name or not name.strip():
        raise ToolError("O nome da rotina é obrigatório.")

    if not steps or not isinstance(steps, list):
        raise ToolError("A rotina deve ter pelo menos um passo (steps).")

    valid_triggers = ("manual", "schedule", "document", "event")
    if trigger_type not in valid_triggers:
        raise ToolError(f"trigger_type inválido. Use um de: {', '.join(valid_triggers)}")

    try:
        db = get_supabase_client()

        routine_id = str(uuid4())
        row = {
            "id": routine_id,
            "client_id": client_id,
            "routine_id": routine_id,
            "source": "custom",
            "status": "draft",
            "active": False,
            "name": name.strip(),
            "description": description,
            "steps": steps,
            "trigger_type": trigger_type,
            "created_by_ai": True,
        }

        result = await db.table("client_routines").insert(row).execute()

        created = result.data[0] if result.data else row
        logger.info(f"[Rotinas] Rotina personalizada criada: {routine_id} para {client_id}")
        return {
            "id": created.get("id", routine_id),
            "name": name,
            "status": "draft",
            "message": (
                f"Rotina '{name}' criada em rascunho. "
                "Chame enviar_rotina_para_aprovacao para ativá-la."
            ),
        }

    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Rotinas] Erro ao criar rotina personalizada: {e}")
        raise ToolError(f"Erro ao criar rotina personalizada: {e}")


async def _ativar_rotina_catalogo_logic(
    routine_id: str,
    active: bool,
    ctx: Context,
    config: dict | None = None,
    client_id: str | None = None,
) -> dict:
    """
    Toggle a catalog routine on or off for this client.

    Args:
        routine_id: The cross_agent_routines.id to activate/deactivate
        active: True to activate, False to deactivate
        config: Optional configuration overrides for this routine

    Creates or updates the client's subscription to a catalog routine.
    """
    if not client_id:
        raise ToolError("client_id não encontrado. Certifique-se de estar autenticado.")

    if not routine_id or not routine_id.strip():
        raise ToolError("routine_id é obrigatório.")

    try:
        db = get_supabase_client()

        catalog_result = await db.table("cross_agent_routines").select("id, name").eq("id", routine_id).maybe_single().execute()
        if not catalog_result.data:
            raise ToolError(f"Rotina de catálogo não encontrada: {routine_id}")

        routine_name = catalog_result.data["name"]
        new_status = "active" if active else "inactive"

        upsert_row = {
            "client_id": client_id,
            "routine_id": routine_id,
            "source": "catalog",
            "active": active,
            "status": new_status,
            "config": config or {},
        }

        await db.table("client_routines").upsert(
            upsert_row,
            on_conflict="client_id,routine_id",
        ).execute()

        action = "ativada" if active else "desativada"
        logger.info(f"[Rotinas] Rotina catálogo '{routine_id}' {action} para {client_id}")
        return {
            "routine_id": routine_id,
            "name": routine_name,
            "active": active,
            "status": new_status,
            "message": f"Rotina '{routine_name}' {action} com sucesso.",
        }

    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Rotinas] Erro ao ativar/desativar rotina catálogo: {e}")
        raise ToolError(f"Erro ao ativar/desativar rotina de catálogo: {e}")


async def _enviar_rotina_para_aprovacao_logic(
    routine_id: str,
    ctx: Context,
    client_id: str | None = None,
) -> dict:
    """
    Submit a draft custom routine to the approval queue.

    Args:
        routine_id: The UUID of the client_routines row to submit (must be source='custom', status='draft')

    Updates status to 'pending_approval' and creates an approval_requests entry
    so the client or admin can review and activate it.
    """
    if not client_id:
        raise ToolError("client_id não encontrado. Certifique-se de estar autenticado.")

    if not routine_id or not routine_id.strip():
        raise ToolError("routine_id é obrigatório.")

    try:
        db = get_supabase_client()

        routine_result = await db.table("client_routines").select(
            "id, name, description, steps, status, source, client_id"
        ).eq("id", routine_id).eq("client_id", client_id).maybe_single().execute()

        if not routine_result.data:
            raise ToolError(f"Rotina não encontrada ou sem permissão: {routine_id}")

        routine = routine_result.data

        if routine.get("source") != "custom":
            raise ToolError("Apenas rotinas personalizadas (source='custom') podem ser enviadas para aprovação.")

        if routine.get("status") not in ("draft", "pending_approval"):
            raise ToolError(
                f"Rotina já está com status '{routine['status']}' e não pode ser "
                "enviada para aprovação. Apenas rotinas em rascunho (draft) ou "
                "pendentes (pending_approval) são aceitas."
            )

        await db.table("client_routines").update(
            {"status": "pending_approval"}
        ).eq("id", routine_id).execute()

        routine_name = routine.get("name") or "Rotina Personalizada"
        await db.table("approval_requests").insert({
            "client_id": client_id,
            "action_type": "routine_activation",
            "agent_slug": "customer-support",
            "title": f"Ativar rotina: {routine_name}",
            "body": routine.get("description"),
            "payload": {
                "client_routine_id": routine_id,
                "routine_name": routine_name,
                "steps": routine.get("steps", []),
                "source": "custom",
                "created_by_ai": True,
            },
        }).execute()

        logger.info(f"[Rotinas] Rotina {routine_id} enviada para aprovação por {client_id}")
        return {
            "routine_id": routine_id,
            "name": routine_name,
            "status": "pending_approval",
            "message": (
                f"Rotina '{routine_name}' enviada para aprovação. "
                "Você receberá uma notificação quando for revisada."
            ),
        }

    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Rotinas] Erro ao enviar rotina para aprovação: {e}")
        raise ToolError(f"Erro ao enviar rotina para aprovação: {e}")


async def _renomear_rotina_personalizada_logic(
    routine_id: str,
    new_name: str,
    ctx: Context,
    client_id: str | None = None,
) -> dict:
    """
    Rename a custom routine owned by the client.

    Args:
        routine_id: The UUID of the client_routines row to rename (must be source='custom')
        new_name: The new name to apply (will be stripped)

    Updates the `name` column of the matching client_routines row. Catalog
    routines (source='catalog') cannot be renamed via this tool.
    """
    if not client_id:
        raise ToolError("client_id não encontrado. Certifique-se de estar autenticado.")

    if not routine_id or not routine_id.strip():
        raise ToolError("routine_id é obrigatório.")

    if not new_name or not new_name.strip():
        raise ToolError("O novo nome da rotina é obrigatório.")

    try:
        db = get_supabase_client()

        routine_result = await db.table("client_routines").select(
            "id, source"
        ).eq("id", routine_id).eq("client_id", client_id).maybe_single().execute()

        if not routine_result.data:
            raise ToolError(f"Rotina não encontrada ou sem permissão: {routine_id}")

        if routine_result.data.get("source") != "custom":
            raise ToolError("Apenas rotinas personalizadas (source='custom') podem ser renomeadas.")

        await db.table("client_routines").update(
            {"name": new_name.strip()}
        ).eq("id", routine_id).eq("client_id", client_id).execute()

        logger.info(f"[Rotinas] Rotina {routine_id} renomeada para '{new_name.strip()}' por {client_id}")
        return {
            "routine_id": routine_id,
            "new_name": new_name.strip(),
            "message": f"Rotina renomeada para '{new_name.strip()}' com sucesso.",
        }

    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Rotinas] Erro ao renomear rotina personalizada: {e}")
        raise ToolError(f"Erro ao renomear rotina personalizada: {e}")


# =============================================================================
# REGISTRO DO MÓDULO
# =============================================================================


@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    """Registra as tools do módulo Rotinas."""

    mcp.tool(
        name="listar_rotinas_catalogo",
        description=(
            "List all catalog routines available for the client, with their current "
            "activation status. Returns routine id, name, active flag, and config schema. "
            "Use this to show clients what automations are available before activating them."
        ),
    )(mcp_inject_client_id(get_context_service)(_listar_rotinas_catalogo_logic))

    mcp.tool(
        name="listar_rotinas_personalizadas",
        description=(
            "List the client's custom routines (created via chat or QuickBuilder) with status. "
            "Includes draft, pending_approval, and active routines. "
            "Use to show what custom automations the client has built."
        ),
    )(mcp_inject_client_id(get_context_service)(_listar_rotinas_personalizadas_logic))

    mcp.tool(
        name="criar_rotina_personalizada",
        description=(
            "Create a new custom routine as a draft. "
            "Parameters: name (string, required), steps (array of step objects, required), "
            "description (string, optional), trigger_type (manual|schedule|document|event, default: manual). "
            "Each step: {step: <int>, agent: <slug>, action: <action_id>, input: {...}}. "
            "After creation, call enviar_rotina_para_aprovacao to submit it for activation."
        ),
    )(mcp_inject_client_id(get_context_service)(_criar_rotina_personalizada_logic))

    mcp.tool(
        name="ativar_rotina_catalogo",
        description=(
            "Toggle a catalog routine on or off for the client. "
            "Parameters: routine_id (string, required), active (boolean, required), "
            "config (object, optional — custom config overrides for the routine). "
            "Use listar_rotinas_catalogo first to get valid routine_id values."
        ),
    )(mcp_inject_client_id(get_context_service)(_ativar_rotina_catalogo_logic))

    mcp.tool(
        name="enviar_rotina_para_aprovacao",
        description=(
            "Submit a draft custom routine to the approval queue for review and activation. "
            "Parameter: routine_id (string, required — UUID from criar_rotina_personalizada). "
            "The routine must have status='draft'. Updates status to 'pending_approval' and "
            "notifies the client for review."
        ),
    )(mcp_inject_client_id(get_context_service)(_enviar_rotina_para_aprovacao_logic))

    mcp.tool(
        name="renomear_rotina_personalizada",
        description=(
            "Rename a custom routine owned by the client. "
            "Parameters: routine_id (string, required — UUID from criar_rotina_personalizada), "
            "new_name (string, required — the new name for the routine). "
            "Only custom routines (source='custom') can be renamed; catalog routines are immutable."
        ),
    )(mcp_inject_client_id(get_context_service)(_renomear_rotina_personalizada_logic))

    registered = [
        "listar_rotinas_catalogo",
        "listar_rotinas_personalizadas",
        "criar_rotina_personalizada",
        "ativar_rotina_catalogo",
        "enviar_rotina_para_aprovacao",
        "renomear_rotina_personalizada",
    ]
    logger.info(f"[Routines Module] Tools registered: {registered}")
    return registered
