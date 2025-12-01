# services/embedding_service/src/config.py
"""
Configurações do Embedding Service.

IMPORTANTE: Todas as variáveis de ambiente devem vir do .env da RAIZ do monorepo.
Este é o único arquivo de configuração de credenciais do projeto.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmbeddingSettings(BaseSettings):
    """Configurações para o Serviço de Embedding."""

    # Carrega variáveis de ambiente (em Docker, vêm do docker-compose.yml que lê o .env da raiz)
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # O nome do modelo HuggingFace que será carregado.
    # Modelos recomendados:
    #   - sentence-transformers/all-MiniLM-L6-v2 (384 dims, rápido, básico)
    #   - intfloat/multilingual-e5-large (1024 dims, excelente para PT-BR)
    #   - BAAI/bge-m3 (1024 dims, estado da arte multilingual)
    EMBEDDING_MODEL_NAME: str = "intfloat/multilingual-e5-large"

    # Dimensão do vetor de embedding (deve corresponder ao modelo escolhido)
    # all-MiniLM-L6-v2 = 384, multilingual-e5-large = 1024, bge-m3 = 1024
    EMBEDDING_VECTOR_SIZE: int = 1024

    # O dispositivo para rodar o modelo ('cuda' se tiver GPU, 'cpu' caso contrário)
    EMBEDDING_MODEL_DEVICE: str = "cpu"


@lru_cache
def get_embedding_settings() -> EmbeddingSettings:
    """
    Retorna uma instância singleton das configurações do Embedding Service.
    O @lru_cache garante que as variáveis de ambiente sejam lidas apenas uma vez.
    """
    settings = EmbeddingSettings()
    print(f"INFO: Embedding Service Config:")
    print(f"  - Modelo: {settings.EMBEDDING_MODEL_NAME}")
    print(f"  - Dimensão: {settings.EMBEDDING_VECTOR_SIZE}")
    print(f"  - Device: {settings.EMBEDDING_MODEL_DEVICE}")
    return settings