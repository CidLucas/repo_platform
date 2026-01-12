import io
import json
import logging
import uuid  # 👈 ADICIONADO

from google.cloud import storage
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

# --- INÍCIO DAS ADIÇÕES ---
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client.models import PointStruct

from file_processing_worker.core.config import Settings
from file_processing_worker.services.routing_service import RoutingService
from vizu_qdrant_client.client import VizuQdrantClient

logger = logging.getLogger(__name__)


class ProcessingService:
    """
    Orquestra o processo completo de processamento de um ficheiro:
    1. Descodifica a mensagem Pub/Sub.
    2. Faz o download do ficheiro do GCS.
    3. Roteia para o parser correto (via RoutingService).
    4. Executa o parsing.
    5. Divide em chunks, gera embeddings e salva no Qdrant. (FASE 3)
    """

    def __init__(
        self,
        storage_client: storage.Client,
        routing_service: RoutingService,
        settings: Settings,
        # --- INÍCIO DAS ADIÇÕES ---
        embedding_model: Embeddings,
        qdrant_client: VizuQdrantClient,
        # --- FIM DAS ADIÇÕES ---
    ):
        """
        Inicializa o serviço com as suas dependências (injeção de dependência).
        """
        self.storage_client = storage_client
        self.routing_service = routing_service
        self.settings = settings
        # --- INÍCIO DAS ADIÇÕES ---
        self.embedding_model = embedding_model
        self.qdrant_client = qdrant_client
        # --- FIM DAS ADIÇÕES ---

        try:
            # Pega a referência do bucket (existente)
            self.bucket = self.storage_client.get_bucket(settings.GCS_BUCKET_NAME)
        except Exception as e:
            logger.critical(
                f"Falha ao aceder ao GCS Bucket '{settings.GCS_BUCKET_NAME}'. Erro: {e}"
            )
            raise

        # --- INÍCIO DAS ADIÇÕES ---
        # Inicializa o TextSplitter que usaremos na Fase 3
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        logger.info("ProcessingService inicializado com TextSplitter.")
        # --- FIM DAS ADIÇÕES ---

    def process_message(self, message_data: bytes):
        """
        Ponto de entrada principal para processar uma nova mensagem Pub/Sub.
        (Lógica das Fases 1 e 2 mantida)
        """

        # --- FASE 1: Descodificar e Fazer Download (Sem alterações) ---
        try:
            message_dict = json.loads(message_data.decode("utf-8"))
            job_id = message_dict.get("job_id", str(uuid.uuid4()))
            logger.info(f"Job [{job_id}]: Mensagem recebida. Iniciando processamento.")

            # Validação e extração de metadados
            gcs_path = message_dict["gcs_path"]
            client_id = message_dict["client_id"]
            original_filename = message_dict.get("original_filename", "N/A")
            file_mime_type = message_dict["file_mime_type"]

            # Download
            blob = self.bucket.blob(gcs_path)
            if not blob.exists():
                logger.error(
                    f"Job [{job_id}]: Ficheiro não encontrado no GCS: {gcs_path}"
                )
                return
            file_bytes = blob.download_as_bytes()
            file_stream = io.BytesIO(file_bytes)
            logger.info(
                f"Job [{job_id}]: FASE 1 Concluída. Download do ficheiro {gcs_path}."
            )

        except Exception as e:
            logger.error(
                f"Job [{job_id}]: Falha na FASE 1 (Download/Parsing Msg). Erro: {e}"
            )
            return  # Acknowledge a mensagem para não re-processar

        # --- FASE 2: Parsing (Sem alterações) ---
        try:
            parser = self.routing_service.get_parser(file_mime_type)
            extracted_text = parser.parse(file_stream)
            if not extracted_text:
                logger.warning(f"Job [{job_id}]: Parser não extraiu texto do ficheiro.")
                return

            logger.info(
                f"Job [{job_id}]: FASE 2 Concluída. {len(extracted_text)} caracteres extraídos."
            )

        except Exception as e:
            logger.error(f"Job [{job_id}]: Falha na FASE 2 (Parsing). Erro: {e}")
            return

        # --- INÍCIO DA FASE 3 (Implementação do Placeholder) ---
        try:
            logger.info(
                f"Job [{job_id}]: FASE 3: Iniciando Chunking, Embedding e Upsert."
            )

            # 1. Preparar metadados base para os chunks
            base_metadata = {
                "job_id": job_id,
                "gcs_path": gcs_path,
                "client_id": client_id,
                "original_filename": original_filename,
                "file_mime_type": file_mime_type,
            }

            # 2. Dividir o texto em Chunks (Documentos LangChain)
            chunks: list[Document] = self.text_splitter.create_documents(
                [extracted_text], metadatas=[base_metadata]
            )
            logger.info(f"Job [{job_id}]: Texto dividido em {len(chunks)} chunks.")

            if not chunks:
                logger.warning(f"Job [{job_id}]: Text splitter não gerou chunks.")
                return

            # 3. Gerar Embeddings para os chunks (chamada de rede ao embedding_service)
            texts_to_embed = [chunk.page_content for chunk in chunks]
            # self.embedding_model é o VizuEmbeddingAPIClient (Passo 2)
            vectors = self.embedding_model.embed_documents(texts_to_embed)

            logger.info(
                f"Job [{job_id}]: {len(vectors)} vetores gerados pelo embedding_service."
            )

            # 4. Preparar os 'Pontos' (objetos) para o Qdrant
            points = []
            for i, chunk in enumerate(chunks):
                point_id = str(uuid.uuid4())  # ID único para cada chunk
                vector = vectors[i]

                # Payload combina os metadados base + o texto do chunk
                payload = chunk.metadata.copy()
                payload["text"] = chunk.page_content

                points.append(PointStruct(id=point_id, vector=vector, payload=payload))

            # 5. Fazer 'upsert' no Qdrant (em lote)
            # self.qdrant_client é o VizuQdrantClient
            self.qdrant_client.upsert(
                collection_name=self.settings.QDRANT_COLLECTION_NAME, points=points
            )

            logger.info(
                f"Job [{job_id}]: FASE 3 Concluída. {len(points)} pontos salvos no Qdrant (Collection: {self.settings.QDRANT_COLLECTION_NAME})."
            )

        except Exception as e:
            logger.error(
                f"Job [{job_id}]: Falha na FASE 3 (Embedding/Qdrant). Erro: {e}"
            )
            # Dependendo da regra de negócio, pode querer tentar novamente (raise)
            return
        # --- FIM DA FASE 3 ---
