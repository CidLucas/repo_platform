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
from .token_budget import (
    DEFAULT_CHARS_PER_TOKEN,
    DEFAULT_MAX_PROMPT_TOKENS,
    TokenBudget,
    TokenBudgetResult,
    estimate_tokens,
    get_message_content,
    truncate_messages,
)

# text_to_sql imports are lazy to avoid pulling in vizu_sql_factory/vizu_prompt_management
# for services that don't need them (e.g., file_processing_worker)
def __getattr__(name):
    """Lazy import for text_to_sql and prompt-related symbols."""
    _text_to_sql_symbols = {
        "TextToSqlPrompt",
        "get_text_to_sql_prompt",
    }
    _text_to_sql_config_symbols = {
        "LLMModel",
        "TextToSqlLLMCall",
        "TextToSqlLLMConfig",
        "TextToSqlLLMResponse",
        "get_llm_call",
        "ConfigLLMProvider",
    }

    # LangfusePromptClient is lazy to avoid requiring vizu_observability_bootstrap
    # in services that don't need prompt management
    if name == "LangfusePromptClient":
        from vizu_observability_bootstrap.langfuse import LangfusePromptClient
        return LangfusePromptClient

    if name in _text_to_sql_symbols:
        from .text_to_sql import TextToSqlPrompt, get_text_to_sql_prompt
        return locals()[name]

    if name in _text_to_sql_config_symbols:
        from .text_to_sql_config import (
            LLMModel,
            TextToSqlLLMCall,
            TextToSqlLLMConfig,
            TextToSqlLLMResponse,
            get_llm_call,
            LLMProvider as ConfigLLMProvider,
        )
        return locals()[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    # Main API
    "get_model",
    "get_embedding_model",
    # Token Budgeting
    "TokenBudget",
    "TokenBudgetResult",
    "estimate_tokens",
    "get_message_content",
    "truncate_messages",
    "DEFAULT_MAX_PROMPT_TOKENS",
    "DEFAULT_CHARS_PER_TOKEN",
    # Prompt Management (from vizu_observability_bootstrap)
    "LangfusePromptClient",
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
