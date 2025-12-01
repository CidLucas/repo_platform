"""
Vizu LLM Service: Biblioteca centralizada para roteamento e instanciação de LLMs.

Suporta múltiplos providers:
- Ollama (local)
- OpenAI (API)
- Anthropic (API)
- Google Gemini (API)

Com integração Langfuse para observabilidade.
"""

from .client import (
    get_model,
    get_embedding_model,
    get_langfuse_callback,
    get_base_callbacks,
    flush_langfuse,
    shutdown_langfuse,
    ModelTier,
    ModelTask,
    LLMProvider,
    VizuEmbeddingAPIClient,
)
from .config import get_llm_settings, LLMSettings, clear_settings_cache

__all__ = [
    # Main API
    "get_model",
    "get_embedding_model",
    # Langfuse
    "get_langfuse_callback",
    "get_base_callbacks",
    "flush_langfuse",
    "shutdown_langfuse",
    # Enums
    "ModelTier",
    "ModelTask",
    "LLMProvider",
    # Classes
    "VizuEmbeddingAPIClient",
    # Config
    "get_llm_settings",
    "LLMSettings",
    "clear_settings_cache",
]