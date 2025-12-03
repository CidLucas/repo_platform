import logging
from functools import lru_cache
from google.cloud import storage
from fastapi import Depends

from file_processing_worker.core.config import Settings, get_settings
from file_processing_worker.services.processing_service import ProcessingService
from file_processing_worker.services.routing_service import RoutingService
# (Os parsers podem ser movidos para o routing_service se não forem usados aqui)
# from file_processing_worker.parsers import PdfParser, CsvParser

# --- INÍCIO DAS ADIÇÕES ---
# (Estes imports já estavam no seu arquivo, o que é ótimo)
from vizu_llm_service.client import get_embedding_model
from vizu_qdrant_client.client import VizuQdrantClient
from langchain_core.embeddings import Embeddings
# --- FIM DAS ADIÇÕES ---

logger = logging.getLogger(__name__)

# --- Funções de Fábrica (Injeção de Dependência) ---


@lru_cache
def get_gcp_storage_client() -> storage.Client:
    logger.info("Inicializando cliente GCS...")
    return storage.Client()


@lru_cache
def get_routing_service() -> RoutingService:
    # (A lógica de inicialização dos parsers deve ficar aqui)
    logger.info("Inicializando RoutingService...")
    # parsers = { ... }
    # return RoutingService(parsers=parsers)
    return (
        RoutingService()
    )  # <-- Simplificado, assumindo que routing_service lida com isso


# --- INÍCIO DAS NOVAS FÁBRICAS ---


@lru_cache
def get_vizu_embedding_model() -> Embeddings:
    """
    Cria uma instância singleton do nosso cliente de API de embedding.
    Conecta-se ao embedding_service (porta 11435).
    """
    logger.info("Inicializando cliente de Embedding (VizuEmbeddingAPIClient)...")
    return get_embedding_model()


@lru_cache
def get_vizu_qdrant_client(
    settings: Settings = Depends(get_settings),
) -> VizuQdrantClient:
    """
    Cria uma instância singleton do nosso cliente Qdrant.
    Usa as settings do worker para saber onde se conectar.
    """
    logger.info(f"Inicializando cliente Qdrant (Host: {settings.QDRANT_HOST})...")
    return VizuQdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)


# --- FIM DAS NOVAS FÁBRICAS ---


# NÂO usar @lru_cache aqui. Deixar o FastAPI gerir o gráfico.
def get_processing_service(
    storage_client: storage.Client = Depends(get_gcp_storage_client),
    routing_service: RoutingService = Depends(get_routing_service),
    settings: Settings = Depends(get_settings),
    # --- INÍCIO DAS ADIÇÕES ---
    embedding_model: Embeddings = Depends(get_vizu_embedding_model),
    qdrant_client: VizuQdrantClient = Depends(get_vizu_qdrant_client),
    # --- FIM DAS ADIÇÕES ---
) -> ProcessingService:
    """
    Função de fábrica que o FastAPI usará para injetar o ProcessingService.
    Recebe as suas dependências via Depends().
    """

    return ProcessingService(
        storage_client=storage_client,
        routing_service=routing_service,
        settings=settings,
        # --- INÍCIO DAS ADIÇÕES ---
        embedding_model=embedding_model,
        qdrant_client=qdrant_client,
        # --- FIM DAS ADIÇÕES ---
    )
