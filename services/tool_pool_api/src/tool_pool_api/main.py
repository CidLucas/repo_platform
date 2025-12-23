import logging
import sys
from contextlib import asynccontextmanager

import uvicorn  # Importe o uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .core.config import get_settings

# Configurar logging para todos os módulos do tool_pool_api e vizu_*
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# Aumentar o nível de log para módulos específicos
logging.getLogger("tool_pool_api").setLevel(logging.DEBUG)
logging.getLogger("vizu_rag_factory").setLevel(logging.DEBUG)
logging.getLogger("vizu_qdrant_client").setLevel(logging.DEBUG)
logging.getLogger("vizu_llm_service").setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)

# Global state for lazy MCP initialization
_mcp = None
_mcp_asgi = None
_mcp_initialized = False
_initialization_in_progress = False


async def _ensure_mcp_initialized():
    """Lazy initialization of MCP server - synchronizes multiple concurrent requests."""
    global _mcp, _mcp_asgi, _mcp_initialized, _initialization_in_progress

    if _mcp_initialized:
        return _mcp, _mcp_asgi

    # If another request is already initializing, wait for it
    if _initialization_in_progress:
        # Simple polling - in production would use asyncio.Event
        import asyncio
        max_retries = 300  # 30 seconds with 100ms waits
        for _ in range(max_retries):
            if _mcp_initialized:
                return _mcp, _mcp_asgi
            await asyncio.sleep(0.1)
        raise TimeoutError("MCP initialization timeout")

    _initialization_in_progress = True
    try:
        logger.info("🚀 Initializing MCP server (lazy)...")
        from .server.mcp_server import create_mcp_server
        _mcp, mcp_app = create_mcp_server()
        _mcp_asgi = mcp_app
        _mcp_initialized = True
        logger.info("✅ MCP server initialized successfully")
        return _mcp, _mcp_asgi
    except Exception as e:
        logger.exception(f"❌ Failed to initialize MCP server: {e}")
        raise
    finally:
        _initialization_in_progress = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - MCP is initialized at startup."""
    logger.info("🚀 Tool Pool API starting - initializing MCP...")

    # Initialize MCP at startup
    global _mcp, _mcp_asgi, _mcp_initialized
    try:
        from .server.mcp_server import create_mcp_server
        _mcp, _mcp_asgi = create_mcp_server()

        # Mount MCP at /mcp
        app.mount("/mcp", _mcp_asgi)
        logger.info("✅ MCP mounted at /mcp")

        # Run the MCP app's lifespan
        async with _mcp_asgi.lifespan(app):
            _mcp_initialized = True
            logger.info("✅ MCP SessionManager initialized")
            yield
    except Exception as e:
        logger.error(f"❌ Failed to initialize MCP: {e}")
        raise
    finally:
        logger.info("🛑 Tool Pool API shutting down...")


# Create minimal FastAPI app that will initialize MCP lazily
app = FastAPI(
    title="Tool Pool API",
    description="MCP Server for Vizu Tools (lazy-loaded)",
    lifespan=lifespan,
)


# Health check endpoint that doesn't require MCP
@app.get("/health")
async def health_check():
    """Health check for load balancers - fast endpoint, doesn't initialize MCP."""
    return {"status": "healthy", "service": "tool_pool_api"}


@app.get("/info")
async def server_info():
    """Server info endpoint - initializes MCP on first call."""
    try:
        _mcp, _ = await _ensure_mcp_initialized()

        from .server.tools import get_available_modules
        modules = get_available_modules()

        return {
            "name": "Vizu Tool Pool API",
            "version": "1.0.0",
            "transport": "http",
            "modules": list(modules.keys()),
            "tools_count": sum(len(m["tools"]) for m in modules.values()),
        }
    except Exception as e:
        logger.error(f"Failed to get server info: {e}")
        return JSONResponse(
            {"error": str(e), "status": "mcp_initialization_failed"},
            status_code=503,
        )


# MCP is now initialized at startup (see lifespan function above)
# No lazy loading middleware needed


@app.on_event("startup")
async def startup_event():
    """App startup - MCP is initialized in lifespan."""
    logger.info("✅ App started successfully")
    logger.info("📊 Health check available at /health")
    logger.info("ℹ️  Server info available at /info")
    logger.info("🔌 MCP endpoint available at /mcp")

