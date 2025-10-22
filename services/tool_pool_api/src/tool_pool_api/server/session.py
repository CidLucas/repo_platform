import logging
from uuid import UUID
from fastapi import Depends

from mcp.server.fastmcp import ClientSession

# 1. Importa a instância 'mcp' principal
from tool_pool_api.server.mcp_server import mcp

# 2. Importa o getter do ContextService
from tool_pool_api.server.dependencies import get_context_service
from vizu_context_service.context_service import ContextService

# 3. Importa as fábricas de ferramentas das nossas libs (Fase 1)
from vizu_rag_factory.factory import create_rag_runnable
from vizu_sql_factory.factory import create_sql_agent

# (TODO: Importar o create_tavily_search_tool quando a lib vizu_generic_tools for criada)
# from vizu_generic_tools.tavily import create_tavily_search_tool


logger = logging.getLogger(__name__)


@mcp.session_manager
async def vizu_client_session(
    session: ClientSession,
    context: dict,
    context_service: ContextService = Depends(get_context_service)
):
    """
    Gerenciador de sessão MCP para clientes Vizu.

    Este hook é executado no início de cada nova sessão. Ele é responsável por:
    1. Autenticar o cliente (via cliente_id).
    2. Carregar o VizuClientContext (do cache Redis-first).
    3. Instanciar (Bootstrap) as ferramentas (Agente SQL, RAG) UMA VEZ.
    4. Armazenar as ferramentas instanciadas no 'session.state'.
    """
    logger.info(f"Iniciando nova sessão MCP para o serviço: {session.service_name}")

    # 1. Autenticação e Carga de Contexto
    cliente_id_str = context.get("cliente_id")
    if not cliente_id_str:
        logger.error("Falha ao iniciar sessão: 'cliente_id' ausente no contexto.")
        raise ValueError("Contexto 'cliente_id' (UUID) é obrigatório.")

    try:
        cliente_id_uuid = UUID(cliente_id_str)
        logger.info(f"Buscando contexto para cliente_id: {cliente_id_uuid}...")

        # Usa o singleton para buscar o contexto (lógica Redis-First)
        vizu_context = await context_service.get_client_context_by_id(
            cliente_id=cliente_id_uuid
        )

        if not vizu_context:
            logger.warning(f"Contexto não encontrado para cliente_id: {cliente_id_uuid}")
            raise ValueError(f"Contexto não encontrado para o cliente_id fornecido.")

    except ValueError as e:
        logger.error(f"Erro de validação ou busca de contexto para '{cliente_id_str}': {e}")
        # Re-levanta a exceção para falhar a criação da sessão
        raise
    except Exception as e:
        logger.error(f"Erro inesperado ao buscar contexto: {e}")
        raise ValueError("Erro interno ao processar contexto do cliente.")

    logger.info(f"Contexto carregado com sucesso para: {vizu_context.cliente_vizu.nome_identificador}")

    # 2. Bootstrap das Ferramentas (Pago UMA VEZ por sessão)
    # As fábricas extraem o que precisam do vizu_context

    logger.debug("Iniciando bootstrap das ferramentas...")

    # Cria o agente SQL (se habilitado)
    sql_tool = create_sql_agent(vizu_context)
    if sql_tool:
        logger.info(f"Ferramenta 'sql_tool' criada para {vizu_context.cliente_vizu.nome_identificador}")

    # Cria o runnable RAG (se habilitado)
    rag_tool = create_rag_runnable(vizu_context)
    if rag_tool:
        logger.info(f"Ferramenta 'rag_tool' criada para {vizu_context.cliente_vizu.nome_identificador}")

    # TODO: Criar ferramenta Tavily
    # tavily_tool = create_tavily_search_tool(vizu_context)
    # if tavily_tool:
    #    logger.info("Ferramenta 'tavily_tool' criada.")

    # 3. Armazena os objetos prontos na memória da sessão
    # O 'yield' passa o controle de volta ao MCP e define o 'session.state'
    yield {
        "rag_tool": rag_tool,
        "sql_tool": sql_tool,
        # "tavily_tool": tavily_tool,
    }

    # (Código após o yield é executado no 'teardown' da sessão, se necessário)
    logger.info(f"Encerrando sessão para cliente: {vizu_context.cliente_vizu.nome_identificador}")