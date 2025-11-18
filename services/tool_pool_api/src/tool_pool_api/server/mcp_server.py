import logging
from dotenv import load_dotenv
from fastapi import FastAPI
from fastmcp import FastMCP
from .tools import register_tools

load_dotenv()

logger = logging.getLogger(__name__)


def create_mcp_server():
    """
    Factory para criar e configurar a instância principal do FastMCP.
    """
    logger.info("Criando instância do FastMCP...")

    # 1. Crie o objeto FastMCP isolado
    mcp = FastMCP("Vizu Tool Pool")

    # 2. Registre as ferramentas nele
    register_tools(mcp)

    # 3. Crie o app FastAPI principal
    app = FastAPI(title="Tool Pool API")

    # 4. Monte o servidor MCP no FastAPI
    # O mcp.mount() é para composição de MCPs. Para FastAPI, usamos app.mount().
    # Precisamos extrair a aplicação ASGI do MCP.
    try:
        # Cria a aplicação ASGI específica para SSE
        mcp_asgi = mcp.sse_app()

        # Monta no FastAPI na rota /mcp
        # Isso fará com que o endpoint de conexão seja: /mcp/sse
        app.mount("/mcp", mcp_asgi)

        logger.info("MCP (SSE) montado com sucesso em /mcp/sse")

    except Exception as e:
        logger.error(f"Erro fatal ao montar MCP no FastAPI: {e}")
        raise e

    logger.info("App criado, montado no MCP e ferramentas registradas.")

    # Retorna ambos (para o uvicorn rodar o 'app')
    return mcp, app