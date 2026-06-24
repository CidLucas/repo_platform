# tool_pool_api/server/tool_modules/rag_module.py
"""
Módulo RAG - Ferramentas de Retrieval-Augmented Generation

Este módulo contém tools para busca em bases de conhecimento dos clientes.

Phase 3: Updated to use blu_tool_registry for tool validation.
"""

import logging
from uuid import UUID

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from blu_auth.mcp.auth_middleware import mcp_inject_client_id
from blu_models.blu_client_context import BluClientContext
from blu_rag_factory.factory import create_rag_retriever
from tool_pool_api.server.dependencies import get_context_service
from tool_pool_api.server.tool_helpers import is_tool_accessible_by_tier
from tool_pool_api.server.utils.mcp_context import (
    extract_client_id,
    extract_document_ids,
)

from tool_pool_api.server.tool_modules import register_module

logger = logging.getLogger(__name__)


# =============================================================================
# LÓGICA DE NEGÓCIO (Testável)
# =============================================================================


async def _executar_rag_cliente_logic(
    query: str,
    ctx: Context,
    client_id: str | None = None,
) -> str:
    """
       **Tool: executar_rag_cliente**

    **Purpose:** Search a company's knowledge base and return relevant document
    passages with source metadata. The calling agent synthesises the final answer.

    **When to use this tool:**
    - User asks questions about a company's offerings, prices, or services
    - User needs information from company documentation, manuals, or help articles
    - User asks about company policies, terms of service, or procedures

    **Returns:** Raw document passages with [Source | Relevance | Scope] headers.
    You must synthesise these into a coherent answer and cite sources.

    **Input format:**
    - query: (string) A search-optimized version of the user's question.
      Before calling this tool, **rewrite the user's question** to maximize retrieval quality:
      1. Decompose multi-topic questions into key concepts
      2. Expand with synonyms and related terms (same language)
      3. Remove conversational filler (greetings, "gostaria de saber")
      4. Keep 15-40 words of domain-relevant terms

    **Examples:**
    - User: "What are your shipping costs to Europe?" → query: "shipping costs rates Europe international delivery pricing freight"
    - User: "Qual a política de devolução?" → query: "política devolução reembolso troca prazo condições retorno garantia"

    **IMPORTANT:** This tool accesses the specific company's knowledge base. The company context is automatically injected - do NOT ask the user for company ID.
    """
    # 1. Obter dependências
    ctx_service = get_context_service()

    # 2. Resolver o Contexto Blu
    # Priority: 1) client_id param, 2) request meta, 3) access token
    blu_context: BluClientContext | None = None

    # Resolve client_id and document_ids from request meta (passed by
    # atendente_core via _meta) using the shared MCP context helpers.
    if not client_id:
        client_id = extract_client_id(ctx)
        if client_id:
            logger.info(f"[RAG] Using client_id from request meta: {client_id}")
    document_ids = extract_document_ids(ctx)
    if document_ids:
        logger.info(f"[RAG] Scoping search to {len(document_ids)} attached documents")

    try:
        if client_id:
            logger.info(f"[RAG] Usando client_id: {client_id}")
            try:
                uuid_obj = UUID(client_id)
            except ValueError:
                raise ToolError(f"ID de cliente inválido: {client_id}")

            blu_context = await ctx_service.get_client_context_by_id(uuid_obj)

            if not blu_context:
                raise ToolError(f"Contexto não encontrado para o ID: {client_id}")

        else:
            # Fallback to JWT auth (direct API calls)
            # mcp_inject_client_id injects client_id from the Authorization header;
            # this branch only triggers in edge cases where the header is absent.
            raise ToolError("client_id não encontrado no contexto da requisição.")

    except ToolError as e:
        logger.warning(f"[RAG] Falha na autorização: {e}")
        raise e
    except Exception as e:
        logger.exception(f"[RAG] Erro inesperado ao carregar contexto: {e}")
        raise ToolError("Erro interno ao carregar contexto do cliente.")

    # 3. Validations - Using ToolRegistry (Phase 3)
    real_client_id = blu_context.id
    logger.info(f"[RAG] Executando para cliente {real_client_id}...")

    if not is_tool_accessible_by_tier("executar_rag_cliente", blu_context):
        logger.warning(f"[RAG] Ferramenta desabilitada para {real_client_id}.")
        raise ToolError("Ferramenta RAG não está habilitada para este cliente.")

    # 4. Execução da Ferramenta — retrieval-only (no LLM answer generation)
    # The calling agent LLM will synthesise the answer from the retrieved context,
    # eliminating one redundant DEFAULT-tier LLM call per RAG query.
    try:
        rag_retriever = await create_rag_retriever(
            blu_context, document_ids=document_ids
        )

        if not rag_retriever:
            logger.error(f"[RAG] Fábrica retornou None para {real_client_id}.")
            raise ToolError("Não foi possível inicializar o sistema RAG.")

        result = await rag_retriever.ainvoke({"question": query})
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
    # Register using mcp_inject_client_id decorator to inject client_id from auth
    mcp.tool(
        name="executar_rag_cliente",
        description=(
            "Search the company's knowledge base and return relevant document "
            "passages with source metadata. Returns raw context — YOU must "
            "synthesise, cite sources, and answer based on the retrieved passages. "
            "Parameter: query (a search-optimized rewrite of the user's question — "
            "decompose multi-topic queries into key concepts, add synonyms and "
            "related terms, remove conversational filler)."
        ),
    )(mcp_inject_client_id(get_context_service)(_executar_rag_cliente_logic))

    logger.info("[RAG Module] Tool registered: executar_rag_cliente")
    return ["executar_rag_cliente"]
