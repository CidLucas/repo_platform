# tool_pool_api/server/tool_modules/platform_module.py
"""
Módulo Platform - Ferramentas de rotinas e metas para o cliente

Tools para gerenciar rotinas do catálogo e metas do cliente via linguagem natural.

**Tools disponíveis**:
- criar_rotina: Ativa uma rotina do catálogo para o cliente
- listar_rotinas_catalogo: Lista rotinas disponíveis no catálogo
- definir_meta: Cria ou atualiza uma meta do cliente
- listar_metas: Lista metas ativas do cliente
"""

import asyncio
import logging
from datetime import datetime

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from blu_auth.mcp.auth_middleware import mcp_inject_client_id
from blu_supabase_client import get_supabase_client

from tool_pool_api.server.tool_modules import register_module

logger = logging.getLogger(__name__)


async def _criar_rotina_logic(
    routine_id: str,
    ctx: Context,
    notify_channel: str = "app",
    cron_expression: str | None = None,
    config_overrides: dict | None = None,
    client_id: str | None = None,
) -> dict:
    """
    Cria ou ativa uma rotina para o cliente a partir do catálogo.

    O agente usa esta tool quando o usuário diz algo como
    'cria uma rotina que me manda o digest financeiro toda segunda'.

    Args:
        routine_id: Slug da rotina no catálogo (ex: 'financeiro_monitor')
        notify_channel: Canal de notificação ('app' | 'whatsapp' | 'email')
        cron_expression: Expressão cron customizada (ex: '0 8 * * 1' para segunda às 8h).
                         Se None, usa o default do catálogo.
        config_overrides: Configurações adicionais (ex: {"threshold": 1000})

    Returns:
        dict com status, routine_id, name e mensagem de confirmação
    """
    client_id = client_id or ctx.request_context.lifespan_context.get("client_id")

    if not client_id:
        raise ToolError("client_id não encontrado no contexto")

    try:
        db = get_supabase_client()

        # 1. Fetch catalog entry
        catalog_result = await asyncio.to_thread(
            lambda: db.table("cross_agent_routines")
            .select("id,name,description,steps,trigger_type,trigger_config")
            .eq("id", routine_id)
            .maybe_single()
            .execute()
        )

        catalog = catalog_result.data
        if not catalog:
            raise ToolError(
                f"Rotina '{routine_id}' não encontrada no catálogo. "
                "Use listar_rotinas_catalogo para ver as disponíveis."
            )

        # 2. Build trigger_config merging catalog defaults with optional cron override
        base_trigger_config = catalog.get("trigger_config") or {}
        if cron_expression:
            trigger_config = {**base_trigger_config, "expression": cron_expression}
        else:
            trigger_config = base_trigger_config

        # 3. Upsert into client_routines
        upsert_data = {
            "client_id": client_id,
            "routine_id": routine_id,
            "notify_channel": notify_channel,
            "active": True,
            "source": "user_nl",
            "created_by_ai": True,
            "name": catalog.get("name"),
            "description": catalog.get("description"),
            "steps": catalog.get("steps"),
            "trigger_type": catalog.get("trigger_type"),
            "trigger_config": trigger_config,
            "config": config_overrides or {},
        }

        await asyncio.to_thread(
            lambda: db.table("client_routines")
            .upsert(
                upsert_data,
                on_conflict="routine_id,client_id",
            )
            .execute()
        )

        name = catalog.get("name", routine_id)
        logger.info(f"[Platform] Rotina '{routine_id}' ativada para client_id={client_id}")

        return {
            "status": "ok",
            "routine_id": routine_id,
            "name": name,
            "message": f"Rotina '{name}' ativada com sucesso.",
        }

    except ToolError:
        raise
    except Exception as e:
        logger.error(f"[Platform] Erro ao criar rotina '{routine_id}': {e}")
        raise ToolError(f"Erro ao criar rotina: {str(e)}")


async def _listar_rotinas_catalogo_logic(
    ctx: Context,
    client_id: str | None = None,
) -> list[dict]:
    """
    Lista as rotinas disponíveis no catálogo que o usuário pode ativar.

    Chame antes de criar uma rotina para verificar os slugs disponíveis.

    Returns:
        Lista de dicts com routine_id, name, description, trigger_type,
        already_active e notify_channel
    """
    client_id = client_id or ctx.request_context.lifespan_context.get("client_id")

    if not client_id:
        raise ToolError("client_id não encontrado no contexto")

    try:
        db = get_supabase_client()

        # 1. Fetch catalog routines
        catalog_result = await asyncio.to_thread(
            lambda: db.table("cross_agent_routines")
            .select("id,name,description,trigger_type,trigger_config")
            .in_("visibility", ["builtin", "optional"])
            .order("name")
            .execute()
        )
        catalog_rows = catalog_result.data or []

        # 2. Fetch client's active routines
        client_result = await asyncio.to_thread(
            lambda: db.table("client_routines")
            .select("routine_id,active,notify_channel")
            .eq("client_id", client_id)
            .execute()
        )
        client_rows = client_result.data or []

        # Build lookup: routine_id -> client subscription
        client_map = {row["routine_id"]: row for row in client_rows}

        result = []
        for row in catalog_rows:
            rid = row["id"]
            subscription = client_map.get(rid)
            result.append(
                {
                    "routine_id": rid,
                    "name": row.get("name"),
                    "description": row.get("description"),
                    "trigger_type": row.get("trigger_type"),
                    "already_active": bool(subscription and subscription.get("active")),
                    "notify_channel": subscription.get("notify_channel") if subscription else None,
                }
            )

        logger.info(
            f"[Platform] Catálogo listado para client_id={client_id}: "
            f"{len(result)} rotinas"
        )
        return result

    except ToolError:
        raise
    except Exception as e:
        logger.error(f"[Platform] Erro ao listar catálogo de rotinas: {e}")
        raise ToolError(f"Erro ao listar catálogo de rotinas: {str(e)}")


async def _definir_meta_logic(
    dimension: str,
    title: str,
    target_value: float,
    unit: str,
    ctx: Context,
    description: str | None = None,
    deadline: str | None = None,
    client_id: str | None = None,
) -> dict:
    """
    Cria ou atualiza uma meta do cliente.

    Use quando o usuário diz 'define uma meta de atingir R$50k de faturamento
    esse mês' ou 'quero atingir 200 clientes ativos até julho'.

    Args:
        dimension: Dimensão da meta ('financeiro' | 'clientes' | 'compras' | 'agenda' | 'biblioteca')
        title: Título curto da meta (ex: 'Faturamento de R$50k em junho')
        target_value: Valor numérico alvo (ex: 50000)
        unit: Unidade (ex: 'BRL', 'clientes', 'pedidos', '%')
        description: Contexto adicional (opcional)
        deadline: Data limite ISO 8601 (ex: '2026-06-30') (opcional)

    Returns:
        dict com status, goal_id e mensagem de confirmação
    """
    client_id = client_id or ctx.request_context.lifespan_context.get("client_id")

    if not client_id:
        raise ToolError("client_id não encontrado no contexto")

    try:
        db = get_supabase_client()

        # 1. Check for existing active goal with same dimension + title
        existing_result = await asyncio.to_thread(
            lambda: db.table("client_goals")
            .select("id")
            .eq("client_id", client_id)
            .eq("dimension", dimension)
            .eq("title", title)
            .eq("status", "active")
            .maybe_single()
            .execute()
        )

        existing = existing_result.data

        if existing:
            # Update existing goal
            update_data: dict = {
                "target_value": target_value,
                "updated_at": datetime.utcnow().isoformat(),
            }
            if description is not None:
                update_data["description"] = description
            if deadline is not None:
                update_data["deadline"] = deadline

            await asyncio.to_thread(
                lambda: db.table("client_goals")
                .update(update_data)
                .eq("id", existing["id"])
                .execute()
            )
            goal_id = existing["id"]
            logger.info(f"[Platform] Meta '{title}' atualizada (id={goal_id}) para client_id={client_id}")
        else:
            # Insert new goal
            insert_data = {
                "client_id": client_id,
                "dimension": dimension,
                "title": title,
                "target_value": target_value,
                "unit": unit,
                "status": "active",
                "source_agent": "platform",
            }
            if description is not None:
                insert_data["description"] = description
            if deadline is not None:
                insert_data["deadline"] = deadline

            insert_result = await asyncio.to_thread(
                lambda: db.table("client_goals")
                .insert(insert_data)
                .execute()
            )
            goal_id = (insert_result.data or [{}])[0].get("id")
            logger.info(f"[Platform] Meta '{title}' criada (id={goal_id}) para client_id={client_id}")

        deadline_str = deadline or "sem prazo"
        return {
            "status": "ok",
            "goal_id": goal_id,
            "message": f"Meta '{title}' definida: {target_value} {unit} até {deadline_str}.",
        }

    except ToolError:
        raise
    except Exception as e:
        logger.error(f"[Platform] Erro ao definir meta '{title}': {e}")
        raise ToolError(f"Erro ao definir meta: {str(e)}")


async def _listar_metas_logic(
    ctx: Context,
    dimension: str | None = None,
    client_id: str | None = None,
) -> list[dict]:
    """
    Lista as metas ativas do cliente.

    Use para responder 'quais são minhas metas?' ou antes de atualizar uma meta.

    Args:
        dimension: Filtra por dimensão (opcional)

    Returns:
        Lista de dicts com todos os campos da meta (deadline formatado como DD/MM/YYYY)
    """
    client_id = client_id or ctx.request_context.lifespan_context.get("client_id")

    if not client_id:
        raise ToolError("client_id não encontrado no contexto")

    try:
        db = get_supabase_client()

        def _query() -> Any:
            q = (
                db.table("client_goals")
                .select("*")
                .eq("client_id", client_id)
                .eq("status", "active")
                .order("created_at", desc=True)
                .limit(20)
            )
            if dimension:
                q = q.eq("dimension", dimension)
            return q.execute()

        result = await asyncio.to_thread(_query)
        rows = result.data or []

        # Format deadline as DD/MM/YYYY
        formatted = []
        for row in rows:
            row = dict(row)
            if row.get("deadline"):
                try:
                    dl = datetime.fromisoformat(row["deadline"].split("T")[0])
                    row["deadline"] = dl.strftime("%d/%m/%Y")
                except Exception:
                    pass  # Keep original if parsing fails
            formatted.append(row)

        logger.info(
            f"[Platform] Metas listadas para client_id={client_id}: "
            f"{len(formatted)} metas"
            + (f" (dimension={dimension})" if dimension else "")
        )
        return formatted

    except ToolError:
        raise
    except Exception as e:
        logger.error(f"[Platform] Erro ao listar metas: {e}")
        raise ToolError(f"Erro ao listar metas: {str(e)}")


@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    """Registra as tools do módulo Platform (rotinas e metas)."""

    mcp.tool(
        name="criar_rotina",
        description=(
            "Cria ou ativa uma rotina para o cliente a partir do catálogo."
            "\n\n"
            "O agente usa esta tool quando o usuário diz algo como "
            "'cria uma rotina que me manda o digest financeiro toda segunda'."
            "\n\n"
            "Use listar_rotinas_catalogo antes para obter o routine_id correto."
        ),
    )(mcp_inject_client_id(_criar_rotina_logic))

    mcp.tool(
        name="listar_rotinas_catalogo",
        description=(
            "Lista as rotinas disponíveis no catálogo que o usuário pode ativar."
            "\n\n"
            "Chame antes de criar uma rotina para verificar os slugs disponíveis "
            "e quais já estão ativas para o cliente."
        ),
    )(mcp_inject_client_id(_listar_rotinas_catalogo_logic))

    mcp.tool(
        name="definir_meta",
        description=(
            "Cria ou atualiza uma meta do cliente."
            "\n\n"
            "Use quando o usuário diz 'define uma meta de atingir R$50k de faturamento "
            "esse mês' ou 'quero atingir 200 clientes ativos até julho'."
            "\n\n"
            "Se já existir uma meta ativa com o mesmo dimension+title, atualiza o valor e prazo."
        ),
    )(mcp_inject_client_id(_definir_meta_logic))

    mcp.tool(
        name="listar_metas",
        description=(
            "Lista as metas ativas do cliente."
            "\n\n"
            "Use para responder 'quais são minhas metas?' ou antes de atualizar uma meta. "
            "Pode filtrar por dimensão (financeiro, clientes, compras, agenda, biblioteca)."
        ),
    )(mcp_inject_client_id(_listar_metas_logic))

    logger.info(
        "[Platform Module] Tools registradas: "
        "criar_rotina, listar_rotinas_catalogo, definir_meta, listar_metas"
    )

    return [
        "criar_rotina",
        "listar_rotinas_catalogo",
        "definir_meta",
        "listar_metas",
    ]
