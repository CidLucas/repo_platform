import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

logger = logging.getLogger(__name__)

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
        allow_methods=["*"],  # Permite todos os métodos (GET, POST, PUT, DELETE, OPTIONS, etc.)
        allow_headers=["*"],  # Permite todos os headers (Authorization, Content-Type, etc.)
    )

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

    # Endpoint de saúde
    @app.get("/health", tags=["Health Check"])
    def health_check():
        return {"status": "ok"}

    logger.info(f"Serviço '{SERVICE_NAME}' configurado e pronto.")
    return app

# Instância global para Uvicorn
app = create_app()
