import logging
from functools import lru_cache
from google.cloud import storage
from fastapi import Depends # <-- Importar Depends

from file_processing_worker.core.config import Settings, get_settings
from file_processing_worker.services.processing_service import ProcessingService
from file_processing_worker.services.routing_service import RoutingService

logger = logging.getLogger(__name__)

# --- Funções de Fábrica (Injeção de Dependência) ---

@lru_cache
def get_gcp_storage_client() -> storage.Client:
    logger.info("Inicializando cliente GCS...")
    return storage.Client()

@lru_cache
def get_routing_service() -> RoutingService:
    logger.info("Inicializando RoutingService...")
    return RoutingService()

# NÂO usar @lru_cache aqui. Deixar o FastAPI gerir o gráfico.
def get_processing_service(
    storage_client: storage.Client = Depends(get_gcp_storage_client),
    routing_service: RoutingService = Depends(get_routing_service),
    settings: Settings = Depends(get_settings),
) -> ProcessingService:
    """
    Função de fábrica que o FastAPI usará para injetar o serviço.
    Recebe as suas dependências via Depends().
    """

    # O log "Construindo..." foi removido porque o FastAPI pode
    # chamar isto múltiplas vezes (por request).

    return ProcessingService(
        storage_client=storage_client,
        routing_service=routing_service,
        settings=settings,
    )