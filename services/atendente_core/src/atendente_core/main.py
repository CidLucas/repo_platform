import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

# Imports corrigidos para a nova estrutura
from atendente_core.api.router import router as api_router
from atendente_core.core.config import get_settings
from atendente_core.services.mcp_client import mcp_manager

# Configuração de Logs
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Health check functions for dependencies
async def check_mcp_connection() -> bool:
    """Check if MCP tools are available."""
    try:
        return mcp_manager.tools is not None and len(mcp_manager.tools) > 0
    except Exception:
        return False


async def check_database() -> bool:
    """Check database connectivity."""
    try:
        from vizu_observability_bootstrap import check_database_url
        return await check_database_url()
    except Exception:
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação (Startup/Shutdown)"""

    # --- STARTUP ---
    logger.info("🚀 Iniciando Vizu Atendente Core...")

    # Skip MCP connection during startup to allow fast container startup
    # MCP will be connected lazily on first API request if needed
    logger.info("Iniciando em modo sem-ferramentas (lazy MCP connection)")

    yield

    # --- SHUTDOWN ---
    logger.info("🛑 Desligando Atendente Core...")
    try:
        await mcp_manager.disconnect()
    except Exception as e:
        logger.error(f"Erro ao desconectar: {e}")


# Inicializa a App
settings = get_settings()
app = FastAPI(
    title="Vizu Atendente Core",
    description="Cérebro do Agente de IA (LangGraph + MCP)",
    version="2.0.0",
    lifespan=lifespan,
)

# Configura Telemetria (se disponível)
if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
    try:
        from vizu_observability_bootstrap import create_health_router, setup_telemetry

        setup_telemetry(app, service_name=settings.SERVICE_NAME)
        logger.info("🔭 Telemetria OpenTelemetry configurada.")

        # Add comprehensive health router
        health_router = create_health_router(
            service_name=settings.SERVICE_NAME,
            version="2.0.0",
            checks={
                "database": check_database,
                "mcp_tools": check_mcp_connection,
            }
        )
        app.include_router(health_router)
        logger.info("✅ Health router configurado com checks de database e MCP.")
    except ImportError as e:
        logger.warning(f"⚠️ Lib de observabilidade não encontrada: {e}. Pulando setup.")

# Registra as Rotas
# 1. Prefixo /api/v1 (Boas práticas)
app.include_router(api_router, prefix="/api/v1")
# 2. Raiz (Opcional, mas ajuda nos seus testes de curl atuais)
app.include_router(api_router)


# Fallback health check if observability bootstrap not available
@app.get("/health", include_in_schema=False)
def health_check_fallback():
    return {"status": "ok", "service": "atendente_core", "version": "2.0.0"}
