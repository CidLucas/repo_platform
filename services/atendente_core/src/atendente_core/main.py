import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from atendente_core.api.router import router as api_router
from atendente_core.core.config import get_settings
from atendente_core.services.mcp_client import mcp_manager

logger = logging.getLogger(__name__)


# Health check functions for dependencies
async def check_mcp_connection() -> bool:
    """Check if MCP tools are available."""
    try:
        return mcp_manager.tools is not None and len(mcp_manager.tools) > 0
    except Exception:
        return False


async def check_database() -> bool:
    """Check database connectivity via Supabase REST API."""
    try:
        from vizu_supabase_client import get_supabase_client
        client = get_supabase_client()
        # Simple health check: query clientes_vizu with limit 1
        response = client.table("clientes_vizu").select("client_id").limit(1).execute()
        return response is not None
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação (Startup/Shutdown)"""

    # --- STARTUP ---
    logger.info("Starting Vizu Atendente Core...")
    logger.debug("MCP connection deferred (lazy initialization)")

    yield

    # --- SHUTDOWN ---
    logger.info("Shutting down Atendente Core...")

    # Flush observability data
    try:
        from vizu_observability_bootstrap import shutdown_observability
        await shutdown_observability(timeout=5.0)
    except Exception as e:
        logger.warning(f"Observability shutdown error: {e}")

    # Disconnect MCP
    try:
        await mcp_manager.disconnect()
    except Exception as e:
        logger.error(f"MCP disconnect error: {e}")


# Inicializa a App
settings = get_settings()
app = FastAPI(
    title="Vizu Atendente Core",
    description="Cérebro do Agente de IA (LangGraph + MCP)",
    version="2.0.0",
    lifespan=lifespan,
)

# --- CORS Configuration ---
allowed_origins_env = os.getenv("CORS_ORIGINS", "")
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info(f"CORS configurado para: {origins}")

# Configure observability (OTLP + Langfuse)
try:
    from vizu_observability_bootstrap import create_health_router, setup_observability

    setup_observability(app, service_name=settings.SERVICE_NAME)

    # Add health router with dependency checks
    health_router = create_health_router(
        service_name=settings.SERVICE_NAME,
        version="2.0.0",
        checks={
            "database": check_database,
            "mcp_tools": check_mcp_connection,
        }
    )
    app.include_router(health_router)
    logger.debug("Health router configured with database and MCP checks")
except ImportError as e:
    logger.warning(f"Observability bootstrap not available: {e}")

# Registra as Rotas
# 1. Prefixo /api/v1 (Boas práticas)
app.include_router(api_router, prefix="/api/v1")
# 2. Raiz (Opcional, mas ajuda nos seus testes de curl atuais)
app.include_router(api_router)


# Fallback health check if observability bootstrap not available
@app.get("/health", include_in_schema=False)
def health_check_fallback():
    return {"status": "ok", "service": "atendente_core", "version": "2.0.0"}
