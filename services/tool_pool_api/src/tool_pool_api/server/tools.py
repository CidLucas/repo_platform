import logging
from typing import Any, Dict

from mcp.server.fastmcp import ClientSession, Depends

# 1. Importa a instância 'mcp' principal
from tool_pool_api.server.mcp_server import mcp

logger = logging.getLogger(__name__)


@mcp.tool(name="executar_sql_cliente")
def executar_sql_cliente(
    query: str, session: ClientSession = Depends(mcp.session)
) -> Dict[str, Any]:
    """
    Executa uma consulta SQL no banco de dados isolado do cliente.

    Use esta ferramenta para responder perguntas sobre dados do cliente
    que exigem acesso direto ao banco de dados (ex: métricas de vendas,
    listagem de pedidos, contagem de usuários).

    Args:
        query: A consulta SQL (dialeto do cliente) a ser executada.
        session: A sessão MCP injetada.

    Returns:
        Um dicionário contendo o resultado da consulta ou um erro.
    """
    logger.info(f"Ferramenta 'executar_sql_cliente' invocada com query: {query[:50]}...")

    # 1. Pega o agente SQL do estado da sessão (criado no session.py)
    tool = session.state.get("sql_tool")

    # 2. Verifica se a ferramenta está habilitada (não é None)
    if tool is None:
        logger.warning("Invocação falhou: 'sql_tool' não está habilitada para este cliente.")
        # Retorna um erro amigável para o LLM
        return {
            "error": "Ferramenta SQL não habilitada para este cliente."
        }

    # 3. Invoca a ferramenta (o Agente SQL)
    try:
        # O 'tool' aqui é um Agente LangChain, .invoke() espera um dict
        result = tool.invoke({"input": query})
        logger.info("Agente SQL executado com sucesso.")
        return result
    except Exception as e:
        logger.error(f"Erro ao invocar 'sql_tool': {e}")
        return {"error": f"Erro ao executar consulta SQL: {e}"}


@mcp.tool(name="executar_rag_cliente")
def executar_rag_cliente(
    query: str, session: ClientSession = Depends(mcp.session)
) -> Dict[str, Any]:
    """
    Busca informações na base de conhecimento vetorial (RAG) do cliente.

    Use esta ferramenta para responder perguntas sobre documentos,
    procedimentos, manuais ou qualquer informação não estruturada
    previamente indexada pelo cliente.

    Args:
        query: A pergunta ou termo de busca.
        session: A sessão MCP injetada.

    Returns:
        Um dicionário contendo a resposta e as fontes.
    """
    logger.info(f"Ferramenta 'executar_rag_cliente' invocada com query: {query[:50]}...")

    # 1. Pega o runnable RAG do estado da sessão
    tool = session.state.get("rag_tool")

    # 2. Verifica se a ferramenta está habilitada
    if tool is None:
        logger.warning("Invocação falhou: 'rag_tool' não está habilitada para este cliente.")
        return {
            "error": "Ferramenta RAG não habilitada para este cliente."
        }

    # 3. Invoca a ferramenta (o Runnable RAG)
    try:
        # O 'tool' aqui é um Runnable LangChain, .invoke() espera um dict
        result = tool.invoke({"input": query})
        logger.info("Runnable RAG executado com sucesso.")
        return result
    except Exception as e:
        logger.error(f"Erro ao invocar 'rag_tool': {e}")
        return {"error": f"Erro ao executar busca RAG: {e}"}


# TODO: Implementar quando a lib vizu_generic_tools for criada
# @mcp.tool(name="tavily_search")
# def tavily_search(
#     query: str, session: ClientSession = Depends(mcp.session)
# ) -> Dict[str, Any]:
#     """Busca na web usando Tavily."""
#     logger.info(f"Ferramenta 'tavily_search' invocada com query: {query[:50]}...")
#     tool = session.state.get("tavily_tool")
#     if tool is None:
#         logger.warning("Invocação falhou: 'tavily_tool' não está habilitada.")
#         return {
#             "error": "Ferramenta de busca na web não habilitada para este cliente."
#         }
#     try:
#         result = tool.invoke({"query": query})
#         logger.info("Tavily search executado com sucesso.")
#         return result
#     except Exception as e:
#         logger.error(f"Erro ao invocar 'tavily_tool': {e}")
#         return {"error": f"Erro ao executar busca na web: {e}"}