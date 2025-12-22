# tool_pool_api/server/tool_modules/rag_module.py
"""
Módulo RAG - Ferramentas de Retrieval-Augmented Generation

Este módulo contém tools para busca em bases de conhecimento dos clientes.

Phase 3: Updated to use vizu_tool_registry for tool validation.
"""

import logging
from importlib import import_module
from types import ModuleType
from uuid import UUID

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import AccessToken

from vizu_llm_service import ModelTier, get_model
from vizu_models.vizu_client_context import VizuClientContext

# Phase 3: Use ToolRegistry for validation
from vizu_tool_registry import ToolRegistry

from . import register_module

logger = logging.getLogger(__name__)


# =============================================================================
# HELPERS
# =============================================================================


def _is_tool_enabled_for_client(
    tool_name: str, context: VizuClientContext
) -> bool:
    """
    Check if a tool is enabled for a client.

    Supports both:
    - New `enabled_tools` list field
    - Legacy boolean flags

    Args:
        tool_name: Name of the tool (e.g., "executar_rag_cliente")
        context: VizuClientContext

    Returns:
        True if tool is enabled
    """
    # Only consult the authoritative `enabled_tools` list and enforce tier.
    enabled = getattr(context, "enabled_tools", None)
    if enabled is not None and not isinstance(enabled, list | tuple | set):
        enabled = None
    legacy_tools = ToolRegistry.get_tool_names_for_legacy_flags(
        rag_enabled=getattr(context, "ferramenta_rag_habilitada", False),
        sql_enabled=getattr(context, "ferramenta_sql_habilitada", False),
        scheduling_enabled=getattr(context, "ferramenta_agendamento_habilitada", False),
    )

    if enabled is not None and tool_name not in enabled:
        return False

    if enabled is None and tool_name not in legacy_tools:
        return False

    raw_tier = getattr(context, "tier", None)
    if isinstance(raw_tier, str) and raw_tier:
        tier = raw_tier
    elif hasattr(raw_tier, "value") and isinstance(raw_tier.value, str) and raw_tier.value:
        tier = raw_tier.value
    else:
        tier = "BASIC"
    tool_meta = ToolRegistry.get_tool(tool_name)
    if tool_meta and not tool_meta.is_accessible_by_tier(tier):
        return False

    return True


# =============================================================================
# LÓGICA DE NEGÓCIO (Testável)
# =============================================================================


async def _executar_rag_cliente_logic(
    query: str,
    ctx: Context,
    cliente_id: str | None = None,
) -> str:
    """
    Executa consulta RAG na base de conhecimento do cliente.

    Args:
        query: Pergunta do usuário
        ctx: Contexto MCP
        cliente_id: ID do cliente (injetado pelo middleware ou explícito)

    Returns:
        Resposta gerada pelo RAG

    Raises:
        ToolError: Se cliente não autorizado ou RAG desabilitado
    """
    # 1. Obter dependências

    def _resolve_server_tools_module() -> ModuleType:
        """Resolve o módulo de compatibilidade de tools, considerando aliases de importação."""

        for module_name in ("src.tool_pool_api.server.tools", "tool_pool_api.server.tools"):
            try:
                return import_module(module_name)
            except ModuleNotFoundError:
                continue

        raise ImportError("Não foi possível importar tool_pool_api.server.tools")

    server_tools = _resolve_server_tools_module()

    try:
        ctx_service = server_tools.get_context_service()
    except Exception as e:
        logger.exception(f"Erro ao obter serviço de contexto: {e}")
        raise ToolError("Erro interno no serviço de ferramentas.")

    # 2. Resolver o Contexto Vizu
    vizu_context: VizuClientContext | None = None

    try:
        if cliente_id:
            # Caminho A: Injeção via MCP Client (Túnel Persistente)
            logger.info(f"[RAG] Usando cliente_id injetado: {cliente_id}")
            try:
                uuid_obj = UUID(cliente_id)
            except ValueError:
                raise ToolError(f"ID de cliente inválido: {cliente_id}")

            vizu_context = await ctx_service.get_client_context_by_id(uuid_obj)

            if not vizu_context:
                raise ToolError(f"Contexto não encontrado para o ID: {cliente_id}")

        else:
            # Caminho B: Autenticação via Token
            access_token: AccessToken | None = server_tools.get_access_token()
            vizu_context = await server_tools.load_context_from_token(
                ctx_service, access_token
            )

    except ToolError as e:
        logger.warning(f"[RAG] Falha na autorização: {e}")
        raise e
    except Exception as e:
        logger.exception(f"[RAG] Erro inesperado ao carregar contexto: {e}")
        raise ToolError("Erro interno ao carregar contexto do cliente.")

    # 3. Validations - Using ToolRegistry (Phase 3)
    real_client_id = vizu_context.id
    logger.info(f"[RAG] Executando para cliente {real_client_id}...")

    if not _is_tool_enabled_for_client("executar_rag_cliente", vizu_context):
        logger.warning(f"[RAG] Ferramenta desabilitada para {real_client_id}.")
        raise ToolError("Ferramenta RAG não está habilitada para este cliente.")

    # 4. Execução da Ferramenta
    try:
        llm = get_model(
            tier=ModelTier.DEFAULT,
            task="rag",
            user_id=str(real_client_id),
            tags=["tool_pool", "rag_module"],
        )

        rag_runnable = server_tools.create_rag_runnable(vizu_context, llm=llm)

        if not rag_runnable:
            logger.error(f"[RAG] Fábrica retornou None para {real_client_id}.")
            raise ToolError("Não foi possível inicializar o sistema RAG.")

        result = await rag_runnable.ainvoke({"question": query})
        logger.info(f"[RAG] Executado com sucesso para {real_client_id}.")

        return str(result)

    except Exception as e:
        logger.exception(f"[RAG] Erro ao executar para {real_client_id}: {e}")
        raise ToolError(f"Erro durante a execução do RAG: {e}")


# =============================================================================
# REGISTRO DO MÓDULO
# =============================================================================


@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    """Registra as tools do módulo RAG."""

    # Wrapper que aceita cliente_id injetado pelo atendente_core
    # mas não expõe ao schema público da LLM
    async def _rag_tool_wrapper(
        query: str,
        ctx: Context,
        cliente_id: str | None = None,  # Injetado pelo atendente_core
    ) -> str:
        """
        Busca informações na base de conhecimento do cliente.

        Args:
            query: Pergunta do usuário sobre o negócio
            cliente_id: ID do cliente (injetado internamente, não pela LLM)
        """
        return await _executar_rag_cliente_logic(
            query=query, ctx=ctx, cliente_id=cliente_id
        )

    # Registra com description que menciona apenas 'query'
    # O cliente_id é hidden (não aparece no schema da LLM)
    mcp.tool(
        name="executar_rag_cliente",
        description=(
            "Busca informações na base de conhecimento do cliente "
            "(produtos, serviços, preços, FAQ, políticas). "
            "USE ESTA FERRAMENTA para responder perguntas sobre o negócio. "
            "Parâmetro: query (string com a pergunta do usuário)."
        ),
    )(_rag_tool_wrapper)

    logger.info("[RAG Module] Ferramentas registradas.")
    return ["executar_rag_cliente"]
