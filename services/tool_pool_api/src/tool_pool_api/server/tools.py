import logging
from typing import Callable, Awaitable, Any

# --- Imports FastMCP ---
# Removido 'from fastapi import Depends'
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
# Importa a dependência de runtime correta do FastMCP
from fastmcp.server.dependencies import AccessToken, get_access_token

# --- Imports do Ecossistema Vizu ---

# 1. Importa as dependências de serviço (cacheadas) e o novo helper
from tool_pool_api.server.dependencies import (
    get_context_service,
    load_context_from_token # Assumindo que você criou este helper em dependencies.py
)
# 2. Importa o modelo de contexto compartilhado
from vizu_shared_models.cliente_vizu import VizuClientContext

# 3. Importa as fábricas de ferramentas
from vizu_rag_factory.factory import create_rag_runnable
from vizu_sql_factory.factory import create_sql_agent
# (TODO: Importar o create_tavily_search_tool)

logger = logging.getLogger(__name__)

# =============================================================================
# == LÓGICA DAS TOOLS (TESTÁVEIS UNITARIAMENTE)
# =============================================================================
#
# Definimos a lógica de negócio em funções "puras" e globais.
# Isso nos permite importá-las em 'test_tools.py' e testá-las
# isoladamente (Princípio da Testabilidade).
#
# =============================================================================

async def _executar_rag_cliente_logic(
    query: str,
    ctx: Context, # O Contexto padrão do FastMCP
) -> str:
    """
    Lógica de negócio pura e testável para executar a consulta RAG.
    """

    # --- Injeção de Dependência (O Padrão Agnostico Vizu/FastMCP) ---
    try:
        # 1. Obtém as dependências de serviço (cacheadas)
        ctx_service = get_context_service()
        # 2. Obtém o token do contexto runtime do FastMCP
        access_token: AccessToken | None = get_access_token()

        # 3. Carrega o contexto do cliente (lazy loading)
        # (Usando o helper que definimos em 'dependencies.py')
        vizu_context = await load_context_from_token(ctx_service, access_token)

    except ToolError as e:
        logger.warning(f"Falha na autorização da tool 'executar_rag_cliente': {e}")
        raise e # Re-levanta o ToolError para o cliente
    except Exception as e:
        logger.exception(f"Erro inesperado ao carregar contexto Vizu: {e}")
        raise ToolError("Erro interno ao carregar contexto do cliente.")
    # --- Fim da Injeção ---

    cliente_id = vizu_context.id
    logger.info(f"Executando 'executar_rag_cliente' para cliente {cliente_id}...")

    # 4. Verificar permissões (caminho baseado no seu 'cliente_vizu.py')
    if not vizu_context.ferramenta_rag_habilitada:
        logger.warning(f"Tentativa negada: Ferramenta RAG desabilitada para {cliente_id}.")
        raise ToolError("Ferramenta RAG não está habilitada para este cliente.")

    # 5. Criar e Executar a ferramenta (lógica do seu 'factory.py')
    try:
        # Passamos 'llm=None' (o factory usará o default)
        rag_runnable = create_rag_runnable(vizu_context, llm=None)
        if not rag_runnable:
            logger.error(f"Fábrica retornou 'None' para rag_runnable do cliente {cliente_id}.")
            raise ToolError("Não foi possível inicializar o runnable RAG.")

        logger.debug(f"Runnable RAG criado para {cliente_id}.")

        # O 'factory.py' do RAG espera um dicionário com a chave "question"
        result = await rag_runnable.ainvoke({"question": query})
        logger.info(f"Runnable RAG executado com sucesso para {cliente_id}.")

        # O 'result' do seu factory já deve ser a string de resposta
        return str(result)

    except Exception as e:
        logger.exception(f"Erro ao executar runnable RAG para {cliente_id}: {e}")
        raise ToolError(f"Erro durante a execução do RAG: {e}")


async def _executar_sql_agent_logic(
    query: str,
    ctx: Context,
) -> dict:
    """
    Lógica de negócio pura e testável para executar o agente SQL.
    """
    # --- Injeção de Dependência (Padrão Agnostico Vizu/FastMCP) ---
    try:
        ctx_service = get_context_service()
        access_token: AccessToken | None = get_access_token()
        vizu_context = await load_context_from_token(ctx_service, access_token)
    except ToolError as e:
        logger.warning(f"Falha na autorização da tool 'executar_sql_agent': {e}")
        raise e
    except Exception as e:
        logger.exception(f"Erro inesperado ao carregar contexto Vizu: {e}")
        raise ToolError("Erro interno ao carregar contexto do cliente.")
    # --- Fim da Injeção ---

    cliente_id = vizu_context.id
    logger.info(f"Executando 'executar_sql_agent' para {cliente_id}...")

    # 2. Verificar permissões (caminho baseado no 'cliente_vizu.py')
    if not vizu_context.ferramenta_sql_habilitada:
        logger.warning(f"Tentativa negada: Ferramenta SQL desabilitada para {cliente_id}.")
        raise ToolError("Ferramenta SQL não está habilitada para este cliente.")

    # 3. Criar e Executar a ferramenta
    try:
        sql_agent_runnable = create_sql_agent(vizu_context, llm=None) # Passando llm=None
        if not sql_agent_runnable:
            logger.error(f"Fábrica retornou 'None' para sql_agent do cliente {cliente_id}.")
            raise ToolError("Não foi possível inicializar o agente SQL.")

        logger.debug(f"Agente SQL criado para {cliente_id}.")

        # Baseado no seu 'tools.py' original, o SQL agent espera a chave "input"
        result = await sql_agent_runnable.ainvoke({"input": query})
        logger.info(f"Agente SQL executado com sucesso para {cliente_id}.")

        if isinstance(result, dict):
            return result
        # Garante que a saída seja sempre um dicionário
        return {"output": str(result)}

    except Exception as e:
        logger.exception(f"Falha ao criar ou executar sql_agent para {cliente_id}: {e}")
        raise ToolError(f"Erro ao processar a consulta SQL: {e}")


def _ferramenta_publica_de_teste_logic(nome: str) -> str:
    """
    Lógica de negócio pura para a ferramenta de teste.
    Testável unitariamente.
    """
    logger.info(f"Executando 'ferramenta_publica_de_teste' com nome: {nome}")
    return f"Olá, {nome}! Esta é uma ferramenta pública."


# =============================================================================
# == REGISTRO DAS TOOLS (MODULARIZAÇÃO)
# =============================================================================
#
# Esta função tem a responsabilidade única de "conectar" as funções
# de lógica pura ao servidor FastMCP.
#
# =============================================================================

def register_tools(mcp: FastMCP) -> None:
    """
    Registra as funções de lógica de negócio como tools no servidor FastMCP.
    """

    # Usamos a forma funcional de 'mcp.tool' para registrar as funções
    # de lógica que definimos globalmente.

    mcp.tool(
        name="executar_rag_cliente",
        description="Executa uma consulta RAG usando o contexto do cliente autenticado."
    )(_executar_rag_cliente_logic)

    mcp.tool(
        name="executar_sql_agent",
        description="Executa uma consulta no agente SQL usando o contexto do cliente autenticado."
    )(_executar_sql_agent_logic)

    mcp.tool(
        name="ferramenta_publica_de_teste",
        description="Uma ferramenta simples que NÃO requer o contexto Vizu."
    )(_ferramenta_publica_de_teste_logic)

    logger.info(
        "Ferramentas Vizu (executar_rag_cliente, "
        "executar_sql_agent, ferramenta_publica_de_teste) "
        "registradas no servidor MCP."
    )