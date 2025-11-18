import logging
from uuid import UUID
from typing import Callable, Awaitable, Any

# --- Imports FastMCP ---
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
# Importa a dependência de runtime correta do FastMCP
from fastmcp.server.dependencies import AccessToken, get_access_token

# --- Imports do Ecossistema Vizu ---

# 1. Importa as dependências de serviço e o helper de token
from tool_pool_api.server.dependencies import (
    get_context_service,
    load_context_from_token
)
# 2. Importa o modelo de contexto compartilhado
from vizu_shared_models.cliente_vizu import VizuClientContext

# 3. Importa as fábricas de ferramentas
from vizu_rag_factory.factory import create_rag_runnable
from vizu_sql_factory.factory import create_sql_agent

logger = logging.getLogger(__name__)

# =============================================================================
# == LÓGICA DAS TOOLS (TESTÁVEIS UNITARIAMENTE)
# =============================================================================

async def _executar_rag_cliente_logic(
    query: str,
    ctx: Context,
    cliente_id: str | None = None,  # Injeção opcional de contexto (para MCP Client)
) -> str:
    """
    Lógica de negócio pura e testável para executar a consulta RAG.
    Aceita um cliente_id explícito (túnel persistente) ou usa o token de acesso (sessão direta).
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
            # Caminho A: Injeção via MCP Client (Túnel Persistente)
            logger.info(f"Usando cliente_id injetado manualmente: {cliente_id}")
            try:
                uuid_obj = UUID(cliente_id)
            except ValueError:
                raise ToolError(f"ID de cliente inválido: {cliente_id}")

            # Busca direta no serviço de contexto (bypassing token decode)
            vizu_context = await ctx_service.get_client_context_by_id(uuid_obj)

            if not vizu_context:
                raise ToolError(f"Contexto não encontrado para o ID: {cliente_id}")

        else:
            # Caminho B: Autenticação via Token (Chamada Direta/Legada)
            access_token: AccessToken | None = get_access_token()
            # O helper load_context_from_token já trata as exceções de token ausente
            vizu_context = await load_context_from_token(ctx_service, access_token)

    except ToolError as e:
        logger.warning(f"Falha na autorização da tool 'executar_rag_cliente': {e}")
        raise e
    except Exception as e:
        logger.exception(f"Erro inesperado ao carregar contexto Vizu: {e}")
        raise ToolError("Erro interno ao carregar contexto do cliente.")

    # 3. Validações de Negócio
    real_client_id = vizu_context.id
    logger.info(f"Executando 'executar_rag_cliente' para cliente {real_client_id}...")

    if not vizu_context.ferramenta_rag_habilitada:
        logger.warning(f"Tentativa negada: Ferramenta RAG desabilitada para {real_client_id}.")
        raise ToolError("Ferramenta RAG não está habilitada para este cliente.")

    # 4. Execução da Ferramenta
    try:
        # Cria o runnable RAG com o contexto carregado
        rag_runnable = create_rag_runnable(vizu_context, llm=None)

        if not rag_runnable:
            logger.error(f"Fábrica retornou 'None' para rag_runnable do cliente {real_client_id}.")
            raise ToolError("Não foi possível inicializar o sistema RAG.")

        logger.debug(f"Runnable RAG criado para {real_client_id}.")

        # Executa a chain
        result = await rag_runnable.ainvoke({"question": query})
        logger.info(f"Runnable RAG executado com sucesso para {real_client_id}.")

        return str(result)

    except Exception as e:
        logger.exception(f"Erro ao executar runnable RAG para {real_client_id}: {e}")
        raise ToolError(f"Erro durante a execução do RAG: {e}")


async def _executar_sql_agent_logic(
    query: str,
    ctx: Context,
    cliente_id: str | None = None, # Injeção opcional
) -> dict:
    """
    Lógica de negócio pura e testável para executar o agente SQL.
    Aceita um cliente_id explícito (túnel persistente) ou usa o token de acesso (sessão direta).
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
            logger.info(f"Usando cliente_id injetado manualmente (SQL): {cliente_id}")
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
        logger.warning(f"Falha na autorização da tool 'executar_sql_agent': {e}")
        raise e
    except Exception as e:
        logger.exception(f"Erro inesperado ao carregar contexto Vizu: {e}")
        raise ToolError("Erro interno ao carregar contexto do cliente.")

    # 3. Validações de Negócio
    real_client_id = vizu_context.id
    logger.info(f"Executando 'executar_sql_agent' para {real_client_id}...")

    if not vizu_context.ferramenta_sql_habilitada:
        logger.warning(f"Tentativa negada: Ferramenta SQL desabilitada para {real_client_id}.")
        raise ToolError("Ferramenta SQL não está habilitada para este cliente.")

    # 4. Execução da Ferramenta
    try:
        sql_agent_runnable = create_sql_agent(vizu_context, llm=None)

        if not sql_agent_runnable:
            logger.error(f"Fábrica retornou 'None' para sql_agent do cliente {real_client_id}.")
            raise ToolError("Não foi possível inicializar o agente SQL.")

        logger.debug(f"Agente SQL criado para {real_client_id}.")

        result = await sql_agent_runnable.ainvoke({"input": query})
        logger.info(f"Agente SQL executado com sucesso para {real_client_id}.")

        if isinstance(result, dict):
            return result

        return {"output": str(result)}

    except Exception as e:
        logger.exception(f"Falha ao criar ou executar sql_agent para {real_client_id}: {e}")
        raise ToolError(f"Erro ao processar a consulta SQL: {e}")


def _ferramenta_publica_de_teste_logic(nome: str) -> str:
    """
    Lógica de negócio pura para a ferramenta de teste.
    Testável unitariamente e não requer autenticação/contexto.
    """
    logger.info(f"Executando 'ferramenta_publica_de_teste' com nome: {nome}")
    return f"Olá, {nome}! Esta é uma ferramenta pública do Tool Pool."


# =============================================================================
# == REGISTRO DAS TOOLS
# =============================================================================

def register_tools(mcp: FastMCP) -> None:
    """
    Registra as funções de lógica de negócio como tools no servidor FastMCP.
    O FastMCP inspeciona automaticamente a assinatura das funções para gerar o schema.
    """

    mcp.tool(
        name="executar_rag_cliente",
        description="Executa uma consulta RAG usando o contexto do cliente. Opcionalmente recebe 'cliente_id' se chamado via proxy."
    )(_executar_rag_cliente_logic)

    mcp.tool(
        name="executar_sql_agent",
        description="Executa uma consulta no agente SQL usando o contexto do cliente. Opcionalmente recebe 'cliente_id' se chamado via proxy."
    )(_executar_sql_agent_logic)

    mcp.tool(
        name="ferramenta_publica_de_teste",
        description="Uma ferramenta simples que NÃO requer o contexto Vizu."
    )(_ferramenta_publica_de_teste_logic)

    logger.info(
        "Ferramentas Vizu (executar_rag_cliente, executar_sql_agent, ferramenta_publica_de_teste) "
        "registradas com sucesso no servidor MCP."
    )