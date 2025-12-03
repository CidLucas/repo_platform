import logging
from fastapi import FastAPI

# Importações de componentes da nossa aplicação
from clientes_finais_api.api.router import api_router
from clientes_finais_api.core.config import get_settings

# Logger inicial
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Cria e configura uma nova instância da aplicação FastAPI.
    Este é o padrão "Application Factory".
    """
    settings = get_settings()

    # Cria a instância principal da aplicação
    app = FastAPI(
        title=settings.SERVICE_NAME,
        description="API para o gerenciamento de Clientes Finais dos clientes da Vizu.",
        version="0.1.0",
    )

    # 1. Configura a telemetria (se habilitada)
    # Esta é a etapa que adiciona middleware, por isso deve vir antes do fim da configuração.
    if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        logger.info(
            f"Configurando telemetria para o serviço '{settings.SERVICE_NAME}'..."
        )
        from vizu_observability_bootstrap import setup_telemetry

        setup_telemetry(app, service_name=settings.SERVICE_NAME)
    else:
        logger.info(
            "Telemetria não configurada (OTEL_EXPORTER_OTLP_ENDPOINT não definido)."
        )

    # 2. Inclui os roteadores da API
    app.include_router(api_router, prefix="/clientes-finais")

    # 3. Define endpoints de saúde e outros endpoints globais
    @app.get("/health", tags=["Health Check"])
    def health_check():
        return {"status": "ok"}

    logger.info(f"Serviço '{settings.SERVICE_NAME}' configurado e pronto.")
    return app


# Cria a instância da aplicação para ser usada pelo Uvicorn em produção
app = create_app()
