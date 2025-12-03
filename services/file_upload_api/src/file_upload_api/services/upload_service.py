import uuid
import json
import logging
from fastapi import UploadFile
from google.cloud import storage
from google.cloud.pubsub_v1 import PublisherClient
from opentelemetry import trace

# Importações locais da nossa aplicação
from file_upload_api.core.config import Settings
from file_upload_api.schemas.upload_schemas import FileUploadResponse

logger = logging.getLogger(__name__)


class UploadService:
    """
    Encapsula a lógica de negócio para o processo de upload.

    Esta classe é desenhada para ser injetada (dependency-injected)
    nos roteadores, recebendo os clientes e configurações necessárias.
    """

    def __init__(
        self,
        storage_client: storage.Client,
        publisher_client: PublisherClient,
        settings: Settings,
    ):
        """
        Inicializa o serviço com os clientes e configurações.
        """
        self.storage_client = storage_client
        self.publisher_client = publisher_client
        self.settings = settings

        # Pré-configura os caminhos do GCP para eficiência
        try:
            self.bucket = self.storage_client.get_bucket(settings.GCS_BUCKET_NAME)
            self.topic_path = self.publisher_client.topic_path(
                settings.GCP_PROJECT_ID, settings.PUBSUB_TOPIC_ID
            )
        except Exception as e:
            logger.critical(f"Falha ao inicializar clientes GCP: {e}")
            raise

    def _get_current_trace_id(self) -> str | None:
        """
        Captura o Trace ID do span atual do OpenTelemetry.
        (Padrão Vizu: Observabilidade Mandatória).
        """
        current_span = trace.get_current_span()
        if not current_span.is_recording():
            return None

        trace_id = current_span.get_span_context().trace_id
        return trace.format_trace_id(trace_id)

    def process_upload(
        self, file: UploadFile, cliente_vizu_id: uuid.UUID
    ) -> FileUploadResponse:
        """
        Orquestra o pipeline de upload:
        1. Gera IDs únicos.
        2. Captura o Trace ID.
        3. Faz o upload do arquivo para o GCS.
        4. Publica a mensagem de evento no Pub/Sub.
        5. Retorna o schema de resposta.
        """
        logger.info(
            f"Iniciando processamento de upload para cliente_vizu_id: {cliente_vizu_id}"
        )

        # 1. Gerar IDs
        job_id = uuid.uuid4()
        unique_filename = f"{job_id}-{file.filename}"

        # Padrão de GCS: {cliente_id}/{uuid_job}-{filename}
        gcs_path = f"{cliente_vizu_id}/{unique_filename}"

        # 2. Capturar Trace ID (Pilar: Observabilidade)
        trace_id = self._get_current_trace_id()

        # 3. Upload para GCS
        try:
            blob = self.bucket.blob(gcs_path)

            logger.info(f"Job [{job_id}]: Fazendo upload para GCS em {gcs_path}...")
            # file.file é o objeto 'file-like' do UploadFile
            blob.upload_from_file(file.file)
            logger.info(f"Job [{job_id}]: Upload para GCS concluído.")

        except Exception as e:
            logger.error(f"Job [{job_id}]: Falha no upload para GCS. Erro: {e}")
            # (Em produção, teríamos um tratamento de erro mais robusto)
            raise

        # 4. Publicar no Pub/Sub (Padrão Vizu: Tarefas Assíncronas)
        message_payload = {
            "job_id": str(job_id),
            "cliente_vizu_id": str(cliente_vizu_id),
            "gcs_path": gcs_path,
            "original_filename": file.filename,
            "content_type": file.content_type,
            "trace_id": trace_id,  # Propagação do trace!
        }

        try:
            # Serializa a mensagem para bytes
            data = json.dumps(message_payload).encode("utf-8")

            logger.info(f"Job [{job_id}]: Publicando evento no Pub/Sub...")
            # Publica a mensagem
            future = self.publisher_client.publish(self.topic_path, data)
            # Espera a confirmação (bloqueante, mas garante a publicação)
            message_id = future.result()
            logger.info(f"Job [{job_id}]: Evento publicado com ID: {message_id}")

        except Exception as e:
            logger.error(f"Job [{job_id}]: Falha ao publicar no Pub/Sub. Erro: {e}")
            # (Aqui precisaríamos de uma lógica de 'rollback' ou 'retry')
            raise

        # 5. Retornar o Schema de Resposta
        return FileUploadResponse(
            job_id=job_id,
            file_name=file.filename,
            content_type=file.content_type,
            gcs_path=gcs_path,
        )
