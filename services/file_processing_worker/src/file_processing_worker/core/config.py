from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Gerencia as configurações do worker, carregadas de variáveis de ambiente.
    """

    # --- Configuração do Serviço ---
    SERVICE_NAME: str = "file-processing-worker"

    # --- Configuração de Observabilidade (Padrão Vizu) ---
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = None

    # --- Configuração de Infraestrutura (GCP) ---
    GCP_PROJECT_ID: str

    # O nome do GCS Bucket de onde os arquivos serão lidos.
    # (Deve ser o mesmo bucket para onde a 'file_upload_api' envia)
    GCS_BUCKET_NAME: str

    # O ID da "Subscription" Pub/Sub que o worker deve escutar.
    # Esta subscription deve estar atrelada ao tópico 'PUBSUB_TOPIC_ID' da API.
    PUBSUB_SUBSCRIPTION_ID: str

    # --- Configuração da Fase 3: IA e Qdrant (Placeholders) ---
    # (Deixamos preparado para as próximas fases)

    # Endpoint da nossa API de embedding (se for um serviço separado)
    # EMBEDDING_API_ENDPOINT: str = "http://embedding-api-service..."

    # URL do cluster Qdrant (Padrão Vizu)
    # QDRANT_URL: str = "http://qdrant-db:6333"

    # Nome da coleção principal no Qdrant
    # QDRANT_COLLECTION_NAME: str = "vizu-documentos"


    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

@lru_cache
def get_settings() -> Settings:
    """
    Retorna uma instância singleton cacheada das configurações.
    """
    return Settings()