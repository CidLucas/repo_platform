import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastmcp import FastMCP
from .tools import register_tools, get_available_modules
from .resources import register_resources
from .prompts import register_prompts

load_dotenv()

logger = logging.getLogger(__name__)


def create_mcp_server():
    """
    Factory para criar e configurar a instância principal do FastMCP.

    Registra:
    - Tools: Ações executáveis (RAG, SQL, etc.)
    - Resources: Dados read-only (knowledge base, config)
    - Prompts: Templates de prompt versionados

    Transporte: HTTP (Streamable HTTP) - mais moderno que SSE
    """
    logger.info("Criando instância do FastMCP...")

    # 1. Crie o objeto FastMCP isolado
    mcp = FastMCP("Vizu Tool Pool")

    # 2. Registre os componentes MCP
    register_tools(mcp)
    register_resources(mcp)
    register_prompts(mcp)

    # 3. Crie a aplicação MCP ASGI
    # path='/' significa que o endpoint MCP será /mcp (sem duplicação)
    mcp_asgi = mcp.http_app(path='/')

    # 4. Crie o app FastAPI com lifespan do MCP (OBRIGATÓRIO para HTTP transport)
    @asynccontextmanager
    async def combined_lifespan(app: FastAPI):
        """Combina o lifespan do MCP com o do FastAPI."""
        async with mcp_asgi.lifespan(app):
            logger.info("MCP SessionManager inicializado.")
            yield
            logger.info("MCP SessionManager finalizado.")

    app = FastAPI(title="Tool Pool API", lifespan=combined_lifespan)

    # 5. Endpoints determinísticos (não passados para LLM)
    @app.get("/health")
    async def health_check():
        """Health check para load balancers e k8s probes."""
        return {"status": "healthy", "service": "tool_pool_api"}

    @app.get("/info")
    async def server_info():
        """Informações do servidor para debugging/admin."""
        modules = get_available_modules()
        return {
            "name": "Vizu Tool Pool API",
            "version": "1.0.0",
            "transport": "http",
            "modules": list(modules.keys()),
            "tools_count": sum(len(m["tools"]) for m in modules.values())
        }

    # 6. Monte o servidor MCP no FastAPI
    try:
        app.mount("/mcp", mcp_asgi)
        logger.info("MCP (HTTP) montado com sucesso em /mcp")

    except Exception as e:
        logger.error(f"Erro fatal ao montar MCP no FastAPI: {e}")
        raise e

    logger.info("App criado, montado no MCP e ferramentas registradas.")

    # Register integration REST routes (OAuth flows, etc.)
    try:
        from tool_pool_api.api.integrations_router import router as integrations_router
        app.include_router(integrations_router)
        logger.info("Integrations router montado em /integrations")
    except Exception as e:
        logger.warning(f"Não foi possível montar router de integrações: {e}")

    # Retorna ambos (para o uvicorn rodar o 'app')
    return mcp, app