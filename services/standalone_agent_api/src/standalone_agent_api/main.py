"""Main FastAPI application for standalone agent service."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from standalone_agent_api.api.agents_router import router as agents_router
from standalone_agent_api.api.documents_router import router as documents_router
from standalone_agent_api.config import get_settings

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=get_settings().LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


# --- Database Connection Timeout Middleware ---
class DatabaseTimeoutMiddleware(BaseHTTPMiddleware):
    """
    Sets PostgreSQL session timeouts on every request to prevent connection leaks.
    Matches the pattern from atendente_core.
    """

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        if request.url.path == "/health":
            return await call_next(request)

        try:
            from sqlalchemy import text
            from vizu_db_connector.database import SessionLocal

            session = SessionLocal()
            try:
                session.execute(text("SET statement_timeout = '30s'"))
                session.execute(text("SET idle_in_transaction_session_timeout = '5min'"))
            finally:
                session.close()
        except Exception as e:
            logger.warning(f"Could not set session timeouts (non-fatal): {e}")

        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app startup and shutdown."""
    # Startup
    logger.info("Starting standalone agent API service...")
    settings = get_settings()

    # Initialize Langfuse if configured
    if settings.LANGFUSE_PUBLIC_KEY:
        from langfuse import Langfuse

        _ = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            base_url=settings.LANGFUSE_BASE_URL,
        )
        logger.info("Langfuse observability initialized")

    logger.info("Service ready")

    yield

    # Shutdown
    logger.info("Shutting down standalone agent API service...")


# Create FastAPI app
app = FastAPI(
    title="Standalone Agent API",
    description="Runtime service for standalone agents with config helper & data analysis",
    version="0.1.0",
    lifespan=lifespan,
)

# --- CORS Configuration ---
# Use same env var as atendente_core for consistency
allowed_origins_env = os.getenv("CORS_ORIGINS", "") or os.getenv("CORS_ALLOWED_ORIGINS", "")
if allowed_origins_env:
    origins = [origin.strip() for origin in allowed_origins_env.split(",")]
else:
    origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://localhost:5177",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5176",
        "http://localhost:8080",  # Dashboard Docker port
        "http://127.0.0.1:8080",
    ]

# --- Middleware Stack ---
# IMPORTANT: Middleware is processed in REVERSE order of addition.
# Add CORS LAST so it's the OUTERMOST layer (wraps all responses including errors)
app.add_middleware(DatabaseTimeoutMiddleware)
logger.debug("Database timeout middleware configured (30s query, 5min idle)")

# CORS MUST be added LAST to be outermost (process first on request, last on response)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)
logger.info(f"CORS configured (outermost middleware): {origins}")


# Health check
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "standalone_agent_api"}


# Include routers
app.include_router(agents_router, prefix="/v1", tags=["agents"])
app.include_router(documents_router, prefix="/v1", tags=["documents"])


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "standalone_agent_api.main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
