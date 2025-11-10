import base64
import logging
from fastapi import FastAPI, Request, HTTPException, status, Depends
from pydantic import BaseModel, Field

# Importações do nosso worker
from file_processing_worker.core.config import get_settings, Settings
from file_processing_worker.core.worker import get_processing_service
from file_processing_worker.services.processing_service import ProcessingService

# Configuração de logging inicial
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Schemas de Validação para o Pub/Sub Push ---
# Define a estrutura da mensagem que o Pub/Sub envia via HTTP POST

class PubSubMessage(BaseModel):
    """O 'envelope' interno da mensagem Pub/Sub."""
    data: str = Field(..., description="A mensagem real, codificada em Base64.")
    message_id: str = Field(..., description="ID único da mensagem.")
    attributes: dict[str, str] | None = None

class PubSubPushRequest(BaseModel):
    """O corpo (body) completo do POST enviado pelo Pub/Sub."""
    message: PubSubMessage
    subscription: str

# --- Padrão Vizu: Application Factory (consistente com a API) ---

def create_app() -> FastAPI:
    """
    Cria e configura a instância do FastAPI para o worker.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.SERVICE_NAME,
        description="Worker assíncrono para processamento de ficheiros (via Pub/Sub Push).",
        version="0.1.0"
    )

    # --- Padrão Vizu: Observabilidade Mandatória ---
    if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        logger.info(f"Configurando telemetria para o serviço '{settings.SERVICE_NAME}'...")
        try:
            from vizu_observability_bootstrap import setup_telemetry
            setup_telemetry(app, service_name=settings.SERVICE_NAME)
        except ImportError:
            logger.warning("Falha ao importar 'vizu_observability_bootstrap'. Telemetria não configurada.")
    else:
        logger.info("Telemetria não configurada (OTEL_EXPORTER_OTLP_ENDPOINT não definido).")

    # --- Endpoint Principal do Worker ---
    @app.post(
        "/",
        status_code=status.HTTP_204_NO_CONTENT,
        summary="Ponto de entrada para eventos Push do Pub/Sub."
    )
    def handle_pubsub_push(
        request: PubSubPushRequest, # FastAPI valida o body do POST
        service: ProcessingService = Depends(get_processing_service)
    ):
        """
        Recebe, descodifica e processa a mensagem do Pub/Sub.
        """
        logger.info(f"Recebida mensagem Pub/Sub (ID: {request.message.message_id}) da subscrição: {request.subscription}")

        try:
            # 1. Descodificar a mensagem (vem em Base64)
            message_data_bytes = base64.b64decode(request.message.data)
        except Exception as e:
            logger.error(f"Falha ao descodificar dados Base64 da mensagem. Erro: {e}")
            # Retorna um erro 400. Pub/Sub não deve reenviar (mensagem corrompida).
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mensagem Base64 inválida.")

        try:
            # 2. Chamar o serviço de processamento (o coração da lógica)
            service.process_message(message_data_bytes)

            # 3. Sucesso: Retorna 204 No Content
            # Isto serve como "ACK" (confirmação) para o Pub/Sub.
            logger.info(f"Mensagem {request.message.message_id} processada com sucesso.")
            return

        except Exception as e:
            # 4. Erro no Processamento
            logger.error(f"Falha ao processar a mensagem {request.message.message_id}. Erro: {e}", exc_info=True)
            # Lança um erro 500. Isto sinaliza ao Pub/Sub para
            # *TENTAR NOVAMENTE* (NACK), garantindo a Fidedignidade.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno no processamento do worker."
            )

    return app

# --- Instância Global ---
# Cria a instância da aplicação para ser usada pelo Uvicorn em produção.
app = create_app()