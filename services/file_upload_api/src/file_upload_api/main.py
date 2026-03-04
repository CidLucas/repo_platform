import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

# Importações de componentes da nossa aplicação
# (O router ainda não existe, mas já deixamos o import)
from file_upload_api.api.router import api_router
from file_upload_api.core.config import get_settings

# Logger inicial
logger = logging.getLogger(__name__)

# --- Padrão Vizu: Application Factory ---


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager para eventos de startup e shutdown da aplicação.
    Ideal para inicializar/fechar pools de conexão, clientes, etc.
    """
    logger.info("Serviço de Upload iniciando...")
    # No futuro, clientes globais (ex: Google Storage Client)
    # poderiam ser inicializados aqui e atrelados ao 'app.state'.
    yield
    # Lógica de shutdown (se necessário)
    logger.info("Serviço de Upload encerrando.")


def create_app() -> FastAPI:
    """
    Cria e configura uma nova instância da aplicação FastAPI.
    Este é o padrão "Application Factory" usado em todos os serviços Vizu.
    """
    settings = get_settings()

    # Cria a instância principal da aplicação
    app = FastAPI(
        title=settings.SERVICE_NAME,
        description="API síncrona para upload e enfileiramento de arquivos na Vizu.",
        version="0.1.0",
        lifespan=lifespan,  # Adiciona o gerenciador de ciclo de vida
    )

    # --- Padrão Vizu: Observabilidade Mandatória ---
    # 1. Configura a telemetria (OpenTelemetry) se o endpoint estiver definido.
    # Isso é um pilar da nossa arquitetura[cite: 13, 133].
    if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        logger.info(f"Configurando telemetria para o serviço '{settings.SERVICE_NAME}'...")
        try:
            # Importa a 'lib' compartilhada de observabilidade
            from vizu_observability_bootstrap import setup_telemetry

            setup_telemetry(app, service_name=settings.SERVICE_NAME)
        except ImportError:
            logger.warning(
                "Falha ao importar 'vizu_observability_bootstrap'. Telemetria não configurada."
            )
    else:
        logger.info("Telemetria não configurada (OTEL_EXPORTER_OTLP_ENDPOINT não definido).")

    # 2. Inclui os roteadores da API
    # (Este arquivo será o próximo passo)
    app.include_router(api_router, prefix="/v1/upload")

    # 3. Define endpoints de saúde (Padrão de Microserviço)
    @app.get("/health", tags=["Health Check"])
    def health_check():
        """Verifica se o serviço está operacional."""
        return {"status": "ok"}

    logger.info(f"Serviço '{settings.SERVICE_NAME}' configurado e pronto.")
    return app


# --- Instância Global ---
# Cria a instância da aplicação para ser usada pelo Uvicorn em produção.
app = create_app()
