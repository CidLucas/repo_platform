import logging
from dotenv import load_dotenv
from fastapi import FastAPI
from fastmcp import FastMCP
from .tools import register_tools

load_dotenv()

# Importa o "router" que contém todas as tools

logger = logging.getLogger(__name__)


def create_mcp_server() -> FastMCP:
    """
    Factory para criar e configurar a instância principal do FastMCP.

    Esta função é chamada pelo main.py para montar o servidor, garantindo
    que a autenticação e os middlewares estejam corretamente aplicados.
    """
    logger.info("Criando instância do FastMCP...")

    # 1. Obter o provedor de autenticação
    # A função get_auth_provider (que definiremos em dependencies.py)
    # é responsável por carregar a chave pública e instanciar o BearerAuthProvider.
    app = FastAPI()
    mcp = FastMCP.from_fastapi(app=app)
    register_tools(mcp)

    logger.info("App criado, montado no MCP e ferramentas registradas.")




    return mcp

