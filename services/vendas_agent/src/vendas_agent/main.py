"""
Vendas Agent - Main FastAPI application.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from vendas_agent.api.router import router as api_router
from vendas_agent.core.config import get_settings
from vendas_agent.core.service import get_mcp_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle (Startup/Shutdown)."""

    # --- STARTUP ---
    logger.info("🚀 Starting Vizu Vendas Agent...")

    # Initialize MCP connection
    try:
        mcp_manager = await get_mcp_manager()
        logger.info(f"✅ MCP connected with {len(mcp_manager.tools)} tools")
    except Exception as e:
        logger.error(f"⚠️ Failed to connect to MCP: {e}")

    yield

    # --- SHUTDOWN ---
    logger.info("🛑 Shutting down Vendas Agent...")


# Initialize App
settings = get_settings()
app = FastAPI(
    title="Vizu Vendas Agent",
    description="Sales agent for B2C order processing (AgentBuilder Framework)",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure Telemetry (if available)
if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
    try:
        from vizu_observability_bootstrap import setup_telemetry
        setup_telemetry(app, service_name=settings.SERVICE_NAME)
        logger.info("🔭 OpenTelemetry configured.")
    except ImportError:
        logger.warning("⚠️ Observability lib not found. Skipping setup.")

# Register Routes
# 1. /api/v1 prefix (best practice)
app.include_router(api_router, prefix="/api/v1")
# 2. Root (for convenience)
app.include_router(api_router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "vendas_agent", "version": "1.0.0"}
