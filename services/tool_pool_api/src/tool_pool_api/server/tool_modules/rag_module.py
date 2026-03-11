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

from tool_pool_api.server.dependencies import get_context_service
from tool_pool_api.server.tool_helpers import is_tool_enabled_for_client
from vizu_auth.mcp.auth_middleware import mcp_inject_cliente_id
from vizu_llm_service import ModelTier, get_model
from vizu_models.vizu_client_context import VizuClientContext

from . import register_module

logger = logging.getLogger(__name__)


# =============================================================================
# LÓGICA DE NEGÓCIO (Testável)
# =============================================================================


async def _executar_rag_cliente_logic(
    query: str,
    ctx: Context,
    cliente_id: str | None = None,
) -> str:
    """
       **Tool: executar_rag_cliente**

    **Purpose:** Search a company's knowledge base for information about their products, services, pricing, policies, FAQs, and business operations.

    **When to use this tool:**
    - User asks questions about a company's offerings, prices, or services
    - User needs information from company documentation, manuals, or help articles
    - User asks about company policies, terms of service, or procedures
    - User requests information that should be in the company's internal knowledge base

    **Input format:**
    - query: (string) A search-optimized version of the user's question.
      Before calling this tool, **rewrite the user's question** to maximize retrieval quality:
      1. Decompose multi-topic questions into key concepts
      2. Expand with synonyms and related terms (same language)
      3. Remove conversational filler (greetings, "gostaria de saber")
      4. Keep 15-40 words of domain-relevant terms

    **Examples:**
    - User: "What are your shipping costs to Europe?" → query: "shipping costs rates Europe international delivery pricing freight"
    - User: "Tell me about your premium subscription features" → query: "premium subscription plan features benefits pricing tier enterprise"
    - User: "Qual a política de devolução?" → query: "política devolução reembolso troca prazo condições retorno garantia"

    **IMPORTANT:** This tool accesses the specific company's knowledge base. The company context is automatically injected - do NOT ask the user for company ID.
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
        raise ToolError(f"Erro interno no serviço de ferramentas: {type(e).__name__}: {e}")

    # 2. Resolver o Contexto Vizu
    # Priority: 1) cliente_id param, 2) request meta, 3) access token
    vizu_context: VizuClientContext | None = None

    # Try to get cliente_id and document_ids from request meta (passed by atendente_core via _meta)
    document_ids: list[str] | None = None
    if ctx and hasattr(ctx, "request_context"):
        meta = getattr(ctx.request_context, "meta", None)
        if meta:
            meta_dict = meta.model_dump() if hasattr(meta, "model_dump") else dict(meta)
            if not cliente_id:
                cliente_id = meta_dict.get("cliente_id")
                if cliente_id:
                    logger.info(f"[RAG] Using cliente_id from request meta: {cliente_id}")
            # Extract attached_document_ids for scoped RAG search (Phase B3)
            raw_doc_ids = meta_dict.get("attached_document_ids")
            if raw_doc_ids and isinstance(raw_doc_ids, list):
                document_ids = [str(d) for d in raw_doc_ids]
                logger.info(f"[RAG] Scoping search to {len(document_ids)} attached documents")

    try:
        if cliente_id:
            logger.info(f"[RAG] Usando cliente_id: {cliente_id}")
            try:
                uuid_obj = UUID(cliente_id)
            except ValueError:
                raise ToolError(f"ID de cliente inválido: {cliente_id}")

            vizu_context = await ctx_service.get_client_context_by_id(uuid_obj)

            if not vizu_context:
                raise ToolError(f"Contexto não encontrado para o ID: {cliente_id}")

        else:
            # Fallback to JWT auth (direct API calls)
            # Uses vizu_auth for token validation from MCP request headers
            jwt_claims = server_tools.get_jwt_claims_from_mcp()
            vizu_context = await server_tools.load_context_from_jwt_claims(ctx_service, jwt_claims)

    except ToolError as e:
        logger.warning(f"[RAG] Falha na autorização: {e}")
        raise e
    except Exception as e:
        logger.exception(f"[RAG] Erro inesperado ao carregar contexto: {e}")
        raise ToolError("Erro interno ao carregar contexto do cliente.")

    # 3. Validations - Using ToolRegistry (Phase 3)
    real_client_id = vizu_context.id
    logger.info(f"[RAG] Executando para cliente {real_client_id}...")

    if not is_tool_enabled_for_client("executar_rag_cliente", vizu_context):
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

        rag_runnable = await server_tools.create_rag_runnable(
            vizu_context, llm=llm, document_ids=document_ids
        )

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
    # Register using mcp_inject_cliente_id decorator to inject cliente_id from auth
    mcp.tool(
        name="executar_rag_cliente",
        description=(
            "Search the company's knowledge base for information about products, "
            "services, pricing, policies, FAQs, and business operations. "
            "Parameter: query (a search-optimized rewrite of the user's question — "
            "decompose multi-topic queries into key concepts, add synonyms and "
            "related terms, remove conversational filler. Include keywords for "
            "ALL topics mentioned so results are diverse)."
        ),
    )(mcp_inject_cliente_id(get_context_service)(_executar_rag_cliente_logic))

    logger.info("[RAG Module] Tool registered: executar_rag_cliente")
    return ["executar_rag_cliente"]
