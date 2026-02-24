# src/analytics_api/main.py
import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from analytics_api.api.router import api_router
from analytics_api.core.config import settings

# Configuração de observabilidade
from vizu_observability_bootstrap import setup_structured_logging, setup_telemetry

# Configuração de logging (INFO level - structured logging handles this)
setup_structured_logging()
logger = logging.getLogger(__name__)


# --- Database Connection Timeout Middleware ---
class DatabaseTimeoutMiddleware(BaseHTTPMiddleware):
    """
    Sets PostgreSQL session timeouts on every request to prevent connection leaks.

    Protects against:
    - Long-running queries blocking connection pool
    - Idle transactions holding locks
    - Frontend disconnections leaving transactions open
    """
    async def dispatch(self, request: Request, call_next):
        # Set timeouts at session level for this request
        # These are more aggressive than database defaults since API requests should be fast
        from sqlalchemy import text

        from vizu_db_connector.database import SessionLocal
        session = SessionLocal()
        try:
            # 30s statement timeout - any single query taking longer is killed
            session.execute(text("SET statement_timeout = '30s'"))
            # 5min idle_in_transaction timeout - transaction idle > 5min is auto-rolled back
            session.execute(text("SET idle_in_transaction_session_timeout = '5min'"))
            session.close()
        except Exception as e:
            logger.warning(f"Could not set session timeouts: {e}")
            session.close()

        return await call_next(request)


# --- Cache-Control Header Middleware ---
class CacheControlMiddleware(BaseHTTPMiddleware):
    """
    Adds Cache-Control headers to dashboard GET endpoints.

    Enables browser caching for dashboard data:
    - private: Only browser cache, not CDN (user-specific data)
    - max-age=300: Cache for 5 minutes
    """
    CACHEABLE_PATHS = ["/api/dashboard/", "/api/indicators"]

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Only cache GET requests to dashboard endpoints
        if request.method == "GET" and any(
            request.url.path.startswith(path) for path in self.CACHEABLE_PATHS
        ):
            response.headers["Cache-Control"] = "private, max-age=300"

        return response


# --- Criação da Instância FastAPI ---
# Esta é a variável 'app' que o Uvicorn procura
app = FastAPI(
    title="Vizu Analytics API",
    version="0.1.0",
    description="Serviço responsável pelos cálculos Silver -> Gold e RAG."
    # TODO: Adicionar configuração de OpenAPI (docs_url, redoc_url)
)

# Setup telemetry after app creation
setup_telemetry(app=app, service_name="analytics-api")

# --- CORS Configuration (MUST be added BEFORE routes) ---
# Get allowed origins from environment variable or use defaults
allowed_origins_env = os.getenv("CORS_ORIGINS", "")
if allowed_origins_env:
    # Production: Use environment variable (comma-separated list)
    origins = [origin.strip() for origin in allowed_origins_env.split(",")]
else:
    # Development/Default: Allow common local ports + Cloud Run patterns
    origins = [
        "http://localhost:3000",
        "http://localhost:3001",  # vizu_dashboard port
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
        # Cloud Run dashboard URLs (production)
        "https://vizu-dashboard-858493958314.southamerica-east1.run.app",
        "https://vizu-dashboard-858493958314.us-central1.run.app",
        # Supabase Edge Functions (if needed)
        "https://haruewffnubdgyofftut.supabase.co",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)
logger.debug(f"CORS origins configured: {origins}")

# Add database timeout middleware
app.add_middleware(DatabaseTimeoutMiddleware)
logger.debug("Database timeout middleware configured (30s query, 5min idle)")

# Add cache-control headers for dashboard routes
app.add_middleware(CacheControlMiddleware)
logger.debug("Cache-Control middleware configured (5min private cache)")

# Rota de Health Check
@app.get("/health", tags=["Infra"])
def health_check():
    """Verifica se a API está operacional."""
    return {"status": "ok", "service": "analytics-api", "auth": "jwt/header/query_param"}


# --- Lifecycle Events ---
@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    logger.info("Analytics API starting up...")
    # Connection pool is lazily initialized on first use
    logger.info("Database connection pool will be initialized on first request")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Cleanup resources on shutdown.

    Properly disposes database engine to close all pooled connections.
    This prevents connection leaks when the service restarts.
    """
    logger.info("Analytics API shutting down...")
    try:
        from vizu_db_connector.database import get_engine
        engine = get_engine()
        if engine:
            engine.dispose()
            logger.info("Database connection pool disposed successfully")
    except Exception as e:
        logger.warning(f"Error disposing database pool: {e}")


# Inclui todas as rotas com prefixo /api
app.include_router(api_router, prefix="/api")

# Bloco para permitir execução direta com 'python src/analytics_api/main.py' (embora usemos Uvicorn)
if __name__ == "__main__":
    import uvicorn
    logger.info("Iniciando servidor Uvicorn para desenvolvimento local...")
    # Usamos host="0.0.0.0" para permitir acesso de fora do container (se rodado em Docker)
    # ou de outras máquinas na rede local. A porta padrão do container é 8000.
    uvicorn.run(app, host="0.0.0.0", port=8000)
