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

    # --- Supabase Configuration ---
    # These are loaded from environment by vizu_supabase_client
    SUPABASE_URL: str | None = None
    SUPABASE_SERVICE_KEY: str | None = None
    SUPABASE_BUCKET: str = "file-uploads"

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
