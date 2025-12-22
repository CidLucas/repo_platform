"""
Configuração do Data Ingestion API.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Configurações do serviço de ingestão de dados.
    """

    # --- Configuração do Serviço ---
    SERVICE_NAME: str = "Vizu Data Ingestion API"

    # --- Observabilidade ---
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = None

    # --- CORS Configuration ---
    # Lista de origens permitidas separadas por vírgula
    # Exemplo: "http://localhost:5173,https://app.vizu.com.br"
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173"

    # Em desenvolvimento, pode permitir todas as origens
    CORS_ALLOW_ALL: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def get_cors_origins(self) -> list[str]:
        """
        Retorna a lista de origens CORS permitidas.

        Se CORS_ALLOW_ALL for True, retorna ["*"].
        Caso contrário, retorna a lista de CORS_ORIGINS.
        """
        if self.CORS_ALLOW_ALL:
            return ["*"]

        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """
    Retorna uma instância singleton das configurações.
    """
    return Settings()
