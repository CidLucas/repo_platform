"""
Support Agent - Main FastAPI application.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from support_agent.api.router import router as api_router
from support_agent.core.config import get_settings

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
    logger.info("🚀 Starting Vizu Support Agent...")

    yield

    # --- SHUTDOWN ---
    logger.info("🛑 Shutting down Support Agent...")


# Initialize App
settings = get_settings()
app = FastAPI(
    title="Vizu Support Agent",
    description="Technical support agent for issue classification (AgentBuilder Framework)",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure Observability (if available)
if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
    try:
        from vizu_observability_bootstrap import setup_observability
        setup_observability(app, service_name=settings.SERVICE_NAME, log_min_level=logging.INFO)
        logger.info("Observability configured (traces + logs + metrics).")
    except ImportError:
        logger.warning("Observability lib not found. Skipping setup.")

# Register Routes
# 1. /api/v1 prefix (best practice)
app.include_router(api_router, prefix="/api/v1")
# 2. Root (for convenience)
app.include_router(api_router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "support_agent", "version": "1.0.0"}
