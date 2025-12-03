# tool_pool_api/server/tool_modules/sql_module.py
"""
Módulo SQL - Ferramentas de SQL Agent

Este módulo contém tools para consultas a dados estruturados do cliente.
"""

import logging
from typing import List
from uuid import UUID

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import AccessToken, get_access_token

from tool_pool_api.server.dependencies import (
    get_context_service,
    load_context_from_token,
)
from vizu_models.vizu_client_context import VizuClientContext
from vizu_sql_factory.factory import create_sql_agent_runnable
from vizu_auth.mcp.auth_middleware import mcp_inject_cliente_id
from vizu_llm_service import get_model, ModelTier

from . import register_module

logger = logging.getLogger(__name__)


# =============================================================================
# LÓGICA DE NEGÓCIO (Testável)
# =============================================================================


async def _executar_sql_agent_logic(
    query: str,
    ctx: Context,
    cliente_id: str | None = None,
) -> dict:
    """
    Executa consulta SQL via agente para dados estruturados do cliente.

    Args:
        query: Consulta em linguagem natural
        ctx: Contexto MCP
        cliente_id: ID do cliente (injetado pelo middleware ou explícito)

    Returns:
        Dict com resultado da consulta

    Raises:
        ToolError: Se cliente não autorizado ou SQL desabilitado
    """
    # 1. Obter dependências
    try:
        ctx_service = get_context_service()
    except Exception as e:
        logger.exception(f"Erro ao obter serviço de contexto: {e}")
        raise ToolError("Erro interno no serviço de ferramentas.")

    # 2. Resolver o Contexto Vizu
    vizu_context: VizuClientContext | None = None

    try:
        if cliente_id:
            logger.info(f"[SQL] Usando cliente_id injetado: {cliente_id}")
            try:
                uuid_obj = UUID(cliente_id)
            except ValueError:
                raise ToolError(f"ID de cliente inválido: {cliente_id}")

            vizu_context = await ctx_service.get_client_context_by_id(uuid_obj)

            if not vizu_context:
                raise ToolError(f"Contexto não encontrado para o ID: {cliente_id}")
        else:
            access_token: AccessToken | None = get_access_token()
            vizu_context = await load_context_from_token(ctx_service, access_token)

    except ToolError as e:
        logger.warning(f"[SQL] Falha na autorização: {e}")
        raise e
    except Exception as e:
        logger.exception(f"[SQL] Erro inesperado ao carregar contexto: {e}")
        raise ToolError("Erro interno ao carregar contexto do cliente.")

    # 3. Validações de Negócio
    real_client_id = vizu_context.id
    logger.info(f"[SQL] Executando para {real_client_id}...")

    if not vizu_context.ferramenta_sql_habilitada:
        logger.warning(f"[SQL] Ferramenta desabilitada para {real_client_id}.")
        raise ToolError("Ferramenta SQL não está habilitada para este cliente.")

    # 4. Execução da Ferramenta
    try:
        llm = get_model(
            tier=ModelTier.DEFAULT,
            task="sql_agent",
            user_id=str(real_client_id),
            tags=["tool_pool", "sql_module"],
        )

        sql_agent_runnable = create_sql_agent_runnable(vizu_context, llm=llm)

        if not sql_agent_runnable:
            logger.error(f"[SQL] Fábrica retornou None para {real_client_id}.")
            raise ToolError("Não foi possível inicializar o agente SQL.")

        result = await sql_agent_runnable.ainvoke({"input": query})
        logger.info(f"[SQL] Executado com sucesso para {real_client_id}.")

        if isinstance(result, dict):
            return result

        return {"output": str(result)}

    except Exception as e:
        logger.exception(f"[SQL] Erro ao executar para {real_client_id}: {e}")
        raise ToolError(f"Erro ao processar a consulta SQL: {e}")


# =============================================================================
# REGISTRO DO MÓDULO
# =============================================================================


@register_module
def register_tools(mcp: FastMCP) -> List[str]:
    """Registra as tools do módulo SQL."""

    mcp.tool(
        name="executar_sql_agent",
        description=(
            "Consulta dados estruturados do banco de dados "
            "(pedidos, estoque, histórico). "
            "Use para dados transacionais. "
            "Parâmetro: query (string com a consulta)."
        ),
    )(mcp_inject_cliente_id(get_context_service)(_executar_sql_agent_logic))

    logger.info("[SQL Module] Ferramentas registradas.")
    return ["executar_sql_agent"]
