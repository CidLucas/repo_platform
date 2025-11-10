import io
import json
import logging
import uuid
from google.cloud import storage

from file_processing_worker.core.config import Settings
from file_processing_worker.services.routing_service import RoutingService

logger = logging.getLogger(__name__)

class ProcessingService:
    """
    Orquestra o processo completo de processamento de um ficheiro:
    1. Descodifica a mensagem Pub/Sub.
    2. Faz o download do ficheiro do GCS.
    3. Roteia para o parser correto (via RoutingService).
    4. Executa o parsing.
    5. (Futuro) Envia para a Fase 3 (Embedding/Vsearch).
    """

    def __init__(
        self,
        storage_client: storage.Client,
        routing_service: RoutingService,
        settings: Settings,
    ):
        """
        Inicializa o serviço com as suas dependências (injeção de dependência).
        """
        self.storage_client = storage_client
        self.routing_service = routing_service
        self.settings = settings

        try:
            # Pega a referência do bucket uma vez na inicialização
            self.bucket = self.storage_client.get_bucket(settings.GCS_BUCKET_NAME)
        except Exception as e:
            logger.critical(f"Falha ao aceder ao GCS Bucket '{settings.GCS_BUCKET_NAME}'. Erro: {e}")
            raise

    def process_message(self, message_data: bytes):
        """
        Ponto de entrada principal para processar uma nova mensagem Pub/Sub.
        """

        # --- 1. Descodificar a Mensagem ---
        try:
            data = json.loads(message_data.decode("utf-8"))

            # Validação básica da mensagem
            job_id = data.get("job_id", str(uuid.uuid4())) # Usa um ID de fallback
            gcs_path = data.get("gcs_path")
            content_type = data.get("content_type")
            cliente_vizu_id = data.get("cliente_vizu_id")
            trace_id = data.get("trace_id") # Padrão Vizu: Observabilidade

            if not all([gcs_path, content_type, cliente_vizu_id]):
                logger.error(f"Job [{job_id}]: Mensagem inválida. Faltam campos obrigatórios (gcs_path, content_type, cliente_vizu_id).")
                return

        except json.JSONDecodeError as e:
            logger.error(f"Falha ao descodificar a mensagem Pub/Sub. Conteúdo: {message_data!r}. Erro: {e}")
            return

        logger.info(f"Job [{job_id}]: Iniciando processamento para {gcs_path} (Tipo: {content_type}).")
        # TODO: Propagar o 'trace_id' para o contexto de logging/telemetria.

        # --- 2. Download do GCS ---
        try:
            blob = self.bucket.blob(gcs_path)
            if not blob.exists():
                logger.error(f"Job [{job_id}]: Ficheiro não encontrado no GCS: {gcs_path}")
                return

            logger.debug(f"Job [{job_id}]: Fazendo download do ficheiro...")
            file_stream = io.BytesIO()
            blob.download_to_file(file_stream)
            file_stream.seek(0) # Rebobina o stream para o início
            logger.debug(f"Job [{job_id}]: Download concluído.")

        except Exception as e:
            logger.error(f"Job [{job_id}]: Falha no download do GCS {gcs_path}. Erro: {e}", exc_info=True)
            return

        # --- 3. Roteamento (Obter Parser) ---
        parser = self.routing_service.get_parser(content_type)

        if parser is None:
            logger.error(f"Job [{job_id}]: Tipo de ficheiro '{content_type}' não é suportado. Processamento abortado.")
            file_stream.close()
            return

        # --- 4. Parsing (Extração de Texto) ---
        try:
            logger.debug(f"Job [{job_id}]: Executando {parser.__class__.__name__}...")
            extracted_text = parser.parse(file_stream)

            if not extracted_text:
                logger.warning(f"Job [{job_id}]: {parser.__class__.__name__} executado, mas nenhum texto foi extraído do ficheiro.")
                return

        except Exception as e:
            logger.error(f"Job [{job_id}]: Falha durante a execução do parser {parser.__class__.__name__}. Erro: {e}", exc_info=True)
            return
        finally:
            file_stream.close() # Garante que o stream em memória é fechado

        # --- 5. Sucesso (Próxima Etapa: Fase 3) ---
        logger.info(f"Job [{job_id}]: Parsing BEM-SUCEDIDO. {len(extracted_text)} caracteres extraídos.")

        # (Apenas para depuração, remover em produção)
        # logger.debug(f"Job [{job_id}]: Texto extraído (primeiros 200 caracteres): {extracted_text[:200]}...")

        # --- INÍCIO DA FASE 3 (Placeholder - Corrigido para Qdrant) ---
        #
        # 1. Chamar a API de Embedding:
        #    # (Assumindo que temos um self.embedding_client injetado)
        #    vectors = self.embedding_client.generate(extracted_text)
        #
        # 2. Preparar os 'pontos' para o Qdrant (Padrão Vizu):
        #    from qdrant_client.http.models import Point, Distance, VectorParams
        #
        #    point = Point(
        #       id=str(job_id), # ID do job como ID do ponto
        #       vector=vectors,  # O embedding
        #       payload={      # Os metadados para filtro
        #           "cliente_vizu_id": cliente_vizu_id,
        #           "gcs_path": gcs_path,
        #           "original_text_snippet": extracted_text[:200] # Amostra
        #       }
        #    )
        #
        # 3. Fazer 'upsert' no Qdrant:
        #    # (Assumindo que temos um self.qdrant_client injetado)
        #    self.qdrant_client.upsert(
        #        collection_name=self.settings.QDRANT_COLLECTION_NAME,
        #        points=[point],
        #        wait=True # Espera pela confirmação
        #    )
        #
        # logger.info(f"Job [{job_id}]: Embedding e 'upsert' no Qdrant concluídos.")
        #
        # --- FIM DA FASE 3 ---