# tool_pool_api/server/tool_modules/knowledge_graph_module.py
"""
Módulo Knowledge Graph — consulta ao grafo de conhecimento LightRAG (T4.3)

O grafo é alimentado semanalmente por sbm_to_lightrag_synthesis a partir da
shared_business_memory curada. Esta tool fecha o ciclo: até aqui o grafo era
write-only (nenhum caminho de leitura existia).

Retrieval-only (only_need_context=True), seguindo o padrão do
executar_rag_cliente: o LLM do agente sintetiza a resposta final.
"""

import logging
from uuid import UUID

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from blu_auth.mcp.auth_middleware import mcp_inject_client_id
from tool_pool_api.server.dependencies import get_context_service
from tool_pool_api.server.tool_helpers import is_tool_accessible_by_tier
from tool_pool_api.server.tool_modules import register_module
from tool_pool_api.server.utils.lightrag_client import RAGClientError, get_client_rag

logger = logging.getLogger(__name__)

_VALID_MODES = ("mix", "local", "global", "hybrid", "naive")


async def _consultar_grafo_conhecimento_logic(
    query: str,
    ctx: Context,
    client_id: str | None = None,
    modo: str = "mix",
) -> str:
    """Consulta o grafo de conhecimento do cliente (entidades e fatos curados).

    Fontes: sínteses da shared_business_memory (clientes, contatos,
    fornecedores, snapshots, rotinas) inseridas no LightRAG. Complementa o
    executar_rag_cliente (documentos): use este quando a pergunta é sobre
    ENTIDADES do negócio e suas relações, não sobre conteúdo de documentos.
    """
    if not query or not query.strip():
        raise ToolError("query é obrigatória.")

    if modo not in _VALID_MODES:
        raise ToolError(f"modo inválido: {modo}. Use um de {', '.join(_VALID_MODES)}.")

    if not client_id:
        raise ToolError("client_id não encontrado no contexto da requisição.")

    try:
        uuid_obj = UUID(client_id)
    except ValueError:
        raise ToolError(f"ID de cliente inválido: {client_id}")

    # Tier gating — mesma fonte de dados da shared memory (SME)
    ctx_service = get_context_service()
    blu_context = await ctx_service.get_client_context_by_id(uuid_obj)
    if not blu_context:
        raise ToolError(f"Contexto não encontrado para o ID: {client_id}")
    if not is_tool_accessible_by_tier("consultar_grafo_conhecimento", blu_context):
        raise ToolError(
            "Consulta ao grafo de conhecimento não está habilitada para este cliente."
        )

    try:
        rag = await get_client_rag(uuid_obj)
    except RAGClientError as exc:
        logger.error(
            "[KG] LightRAG indisponível para client_id=%s: %s", client_id, exc
        )
        raise ToolError(
            "Grafo de conhecimento indisponível no momento. "
            "Use executar_rag_cliente para buscar nos documentos."
        )

    try:
        from lightrag import QueryParam

        # enable_rerank=False: sem modelo de rerank configurado no LightRAG
        # (o rerank do pipeline pgvector é externo); com True e sem modelo,
        # a lib descarta os chunks recuperados.
        result = await rag.aquery(
            query.strip(),
            param=QueryParam(mode=modo, only_need_context=True, enable_rerank=False),
        )
    except Exception as exc:
        logger.exception(
            "[KG] Erro na consulta ao grafo para client_id=%s: %s", client_id, exc
        )
        raise ToolError(f"Erro ao consultar o grafo de conhecimento: {exc}")

    text = str(result or "").strip()
    if not text or text in ("None", "[no-context]"):
        return (
            "Nenhum contexto encontrado no grafo de conhecimento para esta "
            "consulta. O grafo é alimentado pela memória de negócio curada — "
            "pode ainda não haver sínteses para este tema."
        )

    logger.info(
        "[KG] Consulta executada para client_id=%s (modo=%s, %d chars)",
        client_id,
        modo,
        len(text),
    )
    return text


@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    """Registra as tools do módulo Knowledge Graph."""
    mcp.tool(
        name="consultar_grafo_conhecimento",
        description=(
            "Query the client's business knowledge graph (curated entities: "
            "clients, contacts, suppliers, snapshots, routines — synthesized "
            "weekly from shared business memory). Returns raw graph context "
            "(entities, relations, passages) — YOU must synthesise the answer. "
            "Use for questions about business ENTITIES and their facts; for "
            "document content use executar_rag_cliente. Parameters: query "
            "(search-optimized question), modo (mix|local|global|hybrid|naive, "
            "default mix)."
        ),
    )(mcp_inject_client_id(get_context_service)(_consultar_grafo_conhecimento_logic))

    logger.info("[KG Module] Tool registered: consultar_grafo_conhecimento")
    return ["consultar_grafo_conhecimento"]
