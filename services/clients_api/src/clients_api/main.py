import logging
from fastapi import FastAPI
from vizu_observability_bootstrap import setup_telemetry
from .api.router import router
from .core.config import settings

# 1. Cria a instância da aplicação
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="API para gerenciar Clientes Vizu e suas credenciais.",
)

# 2. Configura a observabilidade (Logs + Traces)
# Esta chamada única instrumenta toda a aplicação.
setup_telemetry(app, service_name=settings.SERVICE_NAME)

# Logger DEVE ser instanciado APÓS o setup_telemetry
logger = logging.getLogger(__name__)

@app.on_event("startup")
def startup_event():
    logger.info("Iniciando a Clients API...")

# 3. Inclui as rotas definidas no router
app.include_router(router, prefix="/api/v1")

@app.get("/health", tags=["Monitoring"])
def health_check():
    """Endpoint de verificação de saúde."""
    logger.info("Health check solicitado.")
    return {"status": "ok"}