import logging
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .api.admin_router import router as admin_router
from .api.integrations_router import router as integrations_router

logger = logging.getLogger(__name__)

# Global state for MCP
_mcp = None
_mcp_asgi = None
_mcp_initialized = False


def _create_mcp():
    """Create MCP server and ASGI app."""
    global _mcp, _mcp_asgi, _mcp_initialized

    logger.info("🚀 Creating MCP server...")
    from .server.mcp_server import create_mcp_server
    _mcp, _mcp_asgi = create_mcp_server()
    _mcp_initialized = True
    logger.info("✅ MCP server created successfully")
    return _mcp, _mcp_asgi


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan - initializes MCP with proper lifespan management.

    IMPORTANT: The MCP ASGI app has its own lifespan that must be run
    to initialize the StreamableHTTPSessionManager task group.
    """
    logger.info("Starting Tool Pool API...")

    try:
        mcp, mcp_asgi = _create_mcp()

        app.mount("/mcp", mcp_asgi)
        logger.debug("MCP mounted at /mcp")

        async with mcp_asgi.lifespan(mcp_asgi):
            logger.debug("MCP lifespan started")
            yield
            logger.debug("MCP lifespan ending...")

    except Exception as e:
        logger.error(f"MCP initialization failed: {e}")
        logger.warning("Server starting without MCP")
        yield

    # Shutdown observability
    try:
        from vizu_observability_bootstrap import shutdown_observability
        await shutdown_observability(timeout=5.0)
    except Exception as e:
        logger.warning(f"Observability shutdown error: {e}")

    logger.info("Tool Pool API shutdown complete")


# Create FastAPI app with combined lifespan
app = FastAPI(
    title="Tool Pool API",
    description="MCP Server for Vizu Tools",
    lifespan=lifespan,
)

# Configure observability
try:
    from vizu_observability_bootstrap import setup_observability
    setup_observability(app, service_name="tool_pool_api")
except ImportError as e:
    logger.warning(f"Observability bootstrap not available: {e}")

# Mount API routers
app.include_router(admin_router)
app.include_router(integrations_router)


# Health check endpoint that doesn't require MCP
@app.get("/health")
async def health_check():
    """Health check for load balancers - fast endpoint."""
    return {"status": "healthy", "service": "tool_pool_api"}


@app.get("/info")
async def server_info():
    """Server info endpoint."""
    try:
        if not _mcp_initialized:
            return JSONResponse(
                {"error": "MCP not initialized", "status": "mcp_not_ready"},
                status_code=503,
            )

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
            {"error": str(e), "status": "error"},
            status_code=503,
        )


@app.on_event("startup")
async def startup_event():
    """App startup logging."""
    logger.debug("Tool Pool API started - endpoints: /health, /info, /mcp, /integrations, /admin/clients")
