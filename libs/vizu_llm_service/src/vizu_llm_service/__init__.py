"""
Vizu LLM Service: Biblioteca centralizada para roteamento e instanciação de LLMs.

Suporta múltiplos providers:
- Ollama Local (container)
- Ollama Cloud (api.ollama.com)
- OpenAI (API)
- Anthropic (API)
- Google Gemini (API)

Com integração Langfuse para observabilidade.

Uso rápido:
    # Usar Ollama local (padrão)
    from vizu_llm_service import get_model
    model = get_model()

    # Usar Ollama Cloud (precisa OLLAMA_CLOUD_API_KEY)
    from vizu_llm_service import get_model, LLMProvider
    model = get_model(provider=LLMProvider.OLLAMA_CLOUD)

    # Ou configure via .env:
    # LLM_PROVIDER=ollama_cloud
    # OLLAMA_CLOUD_API_KEY=sua-key-aqui
"""

from .client import (
    MODEL_MAPPINGS,
    LLMProvider,
    ModelTask,
    ModelTier,
    VizuEmbeddingAPIClient,
    flush_langfuse,
    get_base_callbacks,
    get_embedding_model,
    get_langfuse_callback,
    get_model,
    shutdown_langfuse,
)
from .config import LLMSettings, clear_settings_cache, get_llm_settings
from .prompt_service import (
    FetchedPrompt,
    LangfusePromptClient,
    PromptConfig,
    PromptService,
    get_prompt,
    get_prompt_service,
)
from .text_to_sql import (
    TextToSqlPrompt,
    get_text_to_sql_prompt,
)
from .text_to_sql_config import (
    LLMModel,
    TextToSqlLLMCall,
    TextToSqlLLMConfig,
    TextToSqlLLMResponse,
    get_llm_call,
)
from .text_to_sql_config import (
    LLMProvider as ConfigLLMProvider,
)

__all__ = [
    # Main API
    "get_model",
    "get_embedding_model",
    # Prompt Management (Langfuse-First)
    "PromptService",
    "FetchedPrompt",
    "PromptConfig",
    "LangfusePromptClient",
    "get_prompt_service",
    "get_prompt",
    # Text-to-SQL (Phase 1 Refactoring)
    "TextToSqlPrompt",
    "get_text_to_sql_prompt",
    "TextToSqlLLMConfig",
    "TextToSqlLLMCall",
    "TextToSqlLLMResponse",
    "get_llm_call",
    "LLMModel",
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
    # Mappings
    "MODEL_MAPPINGS",
]
