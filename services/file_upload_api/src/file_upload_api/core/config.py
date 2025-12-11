from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Gerencia as configurações da aplicação, carregadas de variáveis de ambiente.
    Valida que as configurações necessárias estão presentes no início.
    """

    # --- Configuração do Serviço ---
    # Nome do serviço para logging e telemetria
    SERVICE_NAME: str = "file-upload-api"

    # --- Configuração de Observabilidade (Padrão Vizu) ---
    # Endpoint do coletor OpenTelemetry (ex: "http://otel-collector:4317")
    # É opcional para permitir a execução em testes sem um coletor.
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = None

    # --- Configuração de Infraestrutura (Lógica de Negócio) ---
    # O 'Project ID' do GCP onde os recursos (Bucket, Topic) estão.
    GCP_PROJECT_ID: str

    # O nome do GCS Bucket para onde os arquivos serão enviados.
    GCS_BUCKET_NAME: str

    # O ID do Tópico Pub/Sub para onde as mensagens de job serão publicadas.
    PUBSUB_TOPIC_ID: str

    class Config:
        # Permite carregar variáveis de um arquivo .env (ótimo para dev local)
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignora variáveis de ambiente extras


@lru_cache
def get_settings() -> Settings:
    """
    Retorna uma instância singleton cacheada das configurações.

    Esta é a dependência que será injetada na aplicação para
    acessar as configurações de forma padronizada.
    """
    return Settings()
