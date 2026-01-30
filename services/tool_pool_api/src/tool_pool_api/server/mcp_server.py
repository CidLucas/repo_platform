import asyncio
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastmcp import FastMCP

from .resources import register_resources
from .tools import get_available_modules, register_tools

load_dotenv()

logger = logging.getLogger(__name__)

# Docker MCP integration - lazy import to avoid startup errors
_docker_mcp_adapter = None
_docker_mcp_init_lock = asyncio.Lock()
_docker_mcp_initialized = False


async def _initialize_docker_mcp(mcp: FastMCP):
    """
    Initialize Docker MCP integration if enabled.

    Thread-safe via asyncio.Lock - prevents concurrent initialization.
    """
    global _docker_mcp_adapter, _docker_mcp_initialized

    # Fast path: already initialized
    if _docker_mcp_initialized:
        return

    async with _docker_mcp_init_lock:
        # Double-check after acquiring lock
        if _docker_mcp_initialized:
            return

        try:
            from .docker_mcp_adapter import get_docker_mcp_adapter

            adapter = get_docker_mcp_adapter()
            await adapter.initialize()

            # Discover and register Docker MCP tools
            registered = await adapter.discover_and_register(mcp)
            _docker_mcp_adapter = adapter
            _docker_mcp_initialized = True

            if registered:
                logger.info(f"Docker MCP: Registered {len(registered)} tools")
            else:
                logger.debug("Docker MCP: No tools registered (disabled or no containers)")

        except ImportError as e:
            logger.debug(f"Docker MCP adapter not available: {e}")
            _docker_mcp_initialized = True  # Mark as done to avoid retries
        except Exception as e:
            logger.warning(f"Docker MCP initialization failed: {e}")
            _docker_mcp_initialized = True  # Mark as done to avoid retries


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
    # Tools include prompt_module which registers native MCP prompts
    register_tools(mcp)
    register_resources(mcp)

    # 3. Crie a aplicação MCP ASGI
    # path='/' significa que o endpoint MCP será /mcp (sem duplicação)
    mcp_asgi = mcp.http_app(path="/")

    # 4. Crie o app FastAPI com lifespan do MCP (OBRIGATÓRIO para HTTP transport)
    @asynccontextmanager
    async def combined_lifespan(app: FastAPI):
        """Combina o lifespan do MCP com o do FastAPI."""
        async with mcp_asgi.lifespan(app):
            logger.info("MCP SessionManager inicializado.")

            # Initialize Docker MCP integration (non-blocking)
            asyncio.create_task(_initialize_docker_mcp(mcp))

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

        # Include Docker MCP status if available
        docker_mcp_status = None
        if _docker_mcp_adapter:
            docker_mcp_status = _docker_mcp_adapter.get_status()

        return {
            "name": "Vizu Tool Pool API",
            "version": "1.0.0",
            "transport": "http",
            "modules": list(modules.keys()),
            "tools_count": sum(len(m["tools"]) for m in modules.values()),
            "docker_mcp": docker_mcp_status,
        }

    #  6. Create a FastAPI app that includes MCP and integration routes
    # Register integration REST routes (OAuth flows, etc.)
    try:
        from tool_pool_api.api.integrations_router import router as integrations_router

        app.include_router(integrations_router)
        logger.info("Integrations router montado em /integrations")
    except Exception as e:
        logger.warning(f"Não foi possível montar router de integrações: {e}")

    logger.info("MCP server created successfully (not mounted yet - will be mounted by main.py)")

    # Return both mcp instance and the mcp_asgi app (NOT the FastAPI app)
    # main.py will mount mcp_asgi at /mcp on its own app
    return mcp, mcp_asgi
