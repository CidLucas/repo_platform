# services/embedding_service/src/config.py

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class EmbeddingSettings(BaseSettings):
    """Configurações para o Serviço de Embedding."""

    # Carrega variáveis de ambiente de um arquivo .env, se existir
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # O nome do modelo HuggingFace que será carregado.
    # Este é o padrão, mas pode ser sobrescrito via variável de ambiente.
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"

    # O dispositivo para rodar o modelo ('cuda' se tiver GPU, 'cpu' caso contrário)
    # 'cpu' é um padrão seguro que funciona em qualquer máquina.
    EMBEDDING_MODEL_DEVICE: str = "cpu"

@lru_cache
def get_embedding_settings() -> EmbeddingSettings:
    """
    Retorna uma instância singleton das configurações do Embedding Service.
    O @lru_cache garante que as variáveis de ambiente sejam lidas apenas uma vez.
    """
    print("INFO: Carregando configurações do Embedding Service...")
    return EmbeddingSettings()