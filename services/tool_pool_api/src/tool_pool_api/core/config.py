import logging
from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()
# Configura um logger básico para mensagens de inicialização
log = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Carrega e valida as variáveis de ambiente da aplicação.
    """

    # --- Configuração do Ambiente ---
    VIZU_ENV: str = "production"

    # --- Conexões de Infraestrutura ---
    # Necessárias para o ContextService (via dependencies.py)
    DATABASE_URL: str | None = None
    REDIS_URL: str | None = None

    # --- Observabilidade ---
    SENTRY_DSN: str = ""
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""
    MCP_AUTH_GOOGLE_CLIENT_ID: str = ""
    MCP_AUTH_GOOGLE_CLIENT_SECRET_ID: str = ""  # ID do segredo no Secret Manager
    MCP_AUTH_BASE_URL: str = "http://localhost:8000"
    MCP_AUTH_REQUIRED_SCOPES: str = "email,profile"

    # --- Internal tools service ---
    TOOLS_SERVICE_BASE_URL: str = "http://tools:8000"


@lru_cache
def get_settings() -> Settings:
    """
    Retorna uma instância singleton cacheada das configurações.

    Esta função lê o .env e valida os campos apenas na primeira chamada.
    As chamadas subsequentes retornarão instantaneamente o objeto Settings.
    """
    log.info("Carregando configurações da aplicação...")
    try:
        settings = Settings()
        log.info(f"Configurações carregadas para o ambiente: {settings.VIZU_ENV}")
        return settings
    except Exception as e:
        log.error(f"Erro fatal ao carregar configurações: {e}")
        # Falha em carregar a configuração é um erro crítico.
        raise SystemExit(f"Erro ao carregar configurações: {e}")


if __name__ == "__main__":
    # Um pequeno utilitário para verificar se o .env está sendo lido
    print("Verificando carregamento de configurações...")
    settings = get_settings()
    print(settings.model_dump_json(indent=2))
