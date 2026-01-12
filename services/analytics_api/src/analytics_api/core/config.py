# src/analytics_api/core/config.py
import logging

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """
    Configurações da aplicação lidas do ambiente ou ficheiro .env.
    Usa Pydantic V2 para validação.
    """
    # URL do Banco de Dados PostgreSQL (lida do ambiente/Docker Compose)
    DATABASE_URL: str = "postgresql+psycopg2://user:password@localhost:5433/vizu_db"

    # URL do Redis para cache (use 'redis' service name in Docker)
    REDIS_URL: str = "redis://redis:6379/0"

    # TTL padrão do cache em segundos (5 minutos)
    CACHE_TTL_SECONDS: int = 300

    # Google OAuth config (adicione essas variáveis ao .env)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = ""

    # Supabase JWT Secret (required for JWT validation)
    SUPABASE_JWT_SECRET: str = ""

    # Configuração do Pydantic V2 para ler do .env
    model_config = SettingsConfigDict(
        env_file=".env",              # Nome do ficheiro .env
        env_file_encoding='utf-8',    # Encoding do ficheiro
        extra='ignore'                # Ignora variáveis extras no .env
    )

# --- Instância Global das Configurações ---
# É esta instância 'settings' que será importada pelos outros módulos.
try:
    settings = Settings()
    logger.info("Configurações carregadas com sucesso.")
    # Log para depuração (opcional, pode remover depois)
    logger.debug(f"DATABASE_URL: {settings.DATABASE_URL}")
except Exception as e:
    logger.error(f"Erro ao carregar as configurações: {e}", exc_info=True)
    # Lança a exceção para impedir a API de iniciar com config inválida
    raise
