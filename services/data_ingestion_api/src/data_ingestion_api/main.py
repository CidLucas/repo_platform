import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware

from data_ingestion_api.api.connector_status_routes import router as connector_status_router
from data_ingestion_api.api.etl_routes import router as etl_router

# Importação dos routers da aplicação
from data_ingestion_api.api.routes import router as credential_router
from data_ingestion_api.api.schema_routes import router as schema_router

# Tenta importar configuração de settings (padrão Vizu)
try:
    from data_ingestion_api.core.config import get_settings
    settings = get_settings()
    SERVICE_NAME = getattr(settings, "SERVICE_NAME", "Vizu Data Ingestion API")
    OTEL_EXPORTER_OTLP_ENDPOINT = getattr(settings, "OTEL_EXPORTER_OTLP_ENDPOINT", None)
except ImportError:
    SERVICE_NAME = "Vizu Data Ingestion API"
    OTEL_EXPORTER_OTLP_ENDPOINT = None

# Import database connector at module level (avoid lazy imports in middleware)
try:
    from vizu_db_connector.database import SessionLocal
    DB_CONNECTOR_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"vizu_db_connector not available: {e}")
    DB_CONNECTOR_AVAILABLE = False

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
        if DB_CONNECTOR_AVAILABLE:
            try:
                session = SessionLocal()
                try:
                    # 30s statement timeout - any single query taking longer is killed
                    session.execute(text("SET statement_timeout = '30s'"))
                    # 5min idle_in_transaction timeout - transaction idle > 5min is auto-rolled back
                    session.execute(text("SET idle_in_transaction_session_timeout = '5min'"))
                finally:
                    session.close()
            except Exception as e:
                logger.warning(f"Could not set session timeouts: {e}")

        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Serviço de Ingestão iniciando...")
    yield
    logger.info("Serviço de Ingestão encerrando.")

def create_app() -> FastAPI:
    app = FastAPI(
        title=SERVICE_NAME,
        description="API para ingestão e mapeamento de dados na Vizu.",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Configuração de CORS
    # Usa configurações do settings para permitir origens específicas
    cors_origins = settings.get_cors_origins()

    logger.info(f"Configurando CORS para as origens: {cors_origins}")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        max_age=3600,
    )

    # Add database timeout middleware
    app.add_middleware(DatabaseTimeoutMiddleware)
    logger.debug("Database timeout middleware configured (30s query, 5min idle)")

    # Observabilidade (OpenTelemetry)
    if OTEL_EXPORTER_OTLP_ENDPOINT:
        logger.info(f"Configurando telemetria para o serviço '{SERVICE_NAME}'...")
        try:
            from vizu_observability_bootstrap import setup_telemetry
            setup_telemetry(app, service_name=SERVICE_NAME)
        except ImportError:
            logger.warning("Falha ao importar 'vizu_observability_bootstrap'. Telemetria não configurada.")
    else:
        logger.info("Telemetria não configurada (OTEL_EXPORTER_OTLP_ENDPOINT não definido).")

    # Inclui os routers principais
    app.include_router(credential_router)
    app.include_router(schema_router, prefix="/schema", tags=["Schema Mapping"])
    app.include_router(etl_router)  # ETL routes already have /etl prefix
    app.include_router(connector_status_router)  # Connector status routes with /connectors prefix

    # Endpoint de saúde
    @app.get("/health", tags=["Health Check"])
    def health_check():
        return {"status": "ok"}

    logger.info(f"Serviço '{SERVICE_NAME}' configurado e pronto.")
    return app

# Instância global para Uvicorn
app = create_app()
