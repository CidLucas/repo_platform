# libs/blu_llm_service/src/blu_llm_service/client.py
"""
Blu LLM Service: Centralized client for local and commercial LLMs.

Supports:
- Ollama (local)
- OpenAI (API)
- Anthropic (API)
- Google Gemini (API)

Langfuse integration is handled by blu_observability_bootstrap.
"""

import logging
from enum import Enum
from typing import Any

from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

from .config import LLMSettings, get_llm_settings

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS
# ============================================================================


class ModelTier(Enum):
    """Model tier - controls quality vs cost/speed."""

    DEFAULT = "default"  # Balanced default model
    FAST = "fast"  # Fast/cheap model
    POWERFUL = "powerful"  # Most capable/expensive model


class ModelTask(Enum):
    """Task type - may influence model selection."""

    GENERAL_AGENT = "general_agent"
    CLASSIFICATION = "classification"
    EMBEDDING = "embedding"
    RAG = "rag"


class LLMProvider(Enum):
    """LLM provider."""

    OLLAMA_CLOUD = "ollama_cloud"  # Ollama Cloud API (ollama.com)
    OPENAI = "openai"  # OpenAI API
    ANTHROPIC = "anthropic"  # Anthropic API
    GOOGLE = "google"  # Google Gemini API


class OllamaCloudModel(str, Enum):
    """Available models on Ollama Cloud (https://ollama.com/search?c=cloud).

    Values are the model IDs used when calling the Ollama API.
    Pass these to get_model(provider=LLMProvider.OLLAMA_CLOUD, model_name=OllamaCloudModel.X).
    """

    # --- Frontier / Powerful ---
    DEEPSEEK_V4_PRO = "deepseek-v4-pro"          # DeepSeek; frontier MoE, 1M context
    DEEPSEEK_V4_FLASH = "deepseek-v4-flash"       # DeepSeek; 284B (13B active), 1M context, fast MoE
    DEEPSEEK_V3_1 = "deepseek-v3.1:671b"         # DeepSeek; previous flagship (671B)
    GLM_5 = "glm-5"                               # Z.ai; 744B (40B active), reasoning focus
    GLM_5_1 = "glm-5.1"                           # Z.ai; improved reasoning
    COGITO_2_1 = "cogito-2.1"                     # MIT licensed; 671B
    DEVSTRAL_2 = "devstral-2"                     # Mistral; 123B, software engineering
    QWEN3_NEXT = "qwen3-next"                     # Alibaba; 80B
    MINIMAX_M2_7 = "minimax-m2.7"                 # MiniMax; agentic workflows, coding
    KIMI_K2_6 = "kimi-k2.6"                       # Moonshot; multimodal agentic
    NEMOTRON_3_SUPER = "nemotron-3-super"         # NVIDIA; 120B (12B active), open MoE

    # --- Balanced / Default ---
    KIMI_K2_5 = "kimi-k2.5"                       # Moonshot; multimodal agentic
    DEVSTRAL_SMALL_2 = "devstral-small-2"         # Mistral; 24B, software engineering agents
    MINIMAX_M2_5 = "minimax-m2.5"                 # MiniMax; productivity and coding
    GEMMA4 = "gemma4"                             # Google; 26–31B, frontier-level
    QWEN3_5 = "qwen3.5"                           # Alibaba; multimodal family (0.8B–122B)
    QWEN3_CODER_NEXT = "qwen3-coder-next"         # Alibaba; coding-focused

    # --- Fast / Lightweight ---
    GPT_OSS_20B = "gpt-oss:20b"                   # OpenAI OSS; 20B balanced
    DEEPSEEK_R1_14B = "deepseek-r1:14b"           # DeepSeek R1; 14B reasoning
    MINISTRAL_3 = "ministral-3"                   # Mistral; 3–14B, edge deployment
    NEMOTRON_3_NANO = "nemotron-3-nano"           # NVIDIA; 4–30B lightweight
    RNJ_1 = "rnj-1"                               # Essential AI; 8B
    GEMINI_3_FLASH_PREVIEW = "gemini-3-flash-preview"  # Google; fast frontier intelligence


# ============================================================================
# LANGFUSE CALLBACKS (delegated to blu_observability_bootstrap)
# ============================================================================


def get_langfuse_callback(
    **_kwargs: Any,
) -> BaseCallbackHandler | None:
    """
    Create Langfuse CallbackHandler for LLM tracing.

    Delegates to blu_observability_bootstrap.langfuse module.
    Langfuse SDK v3 reads trace attributes from config["metadata"]
    at invoke time, not from constructor args.

    Returns:
        CallbackHandler or None if Langfuse not configured
    """
    try:
        from blu_observability_bootstrap.langfuse import (
            get_langfuse_callback as _get_callback,
        )

        return _get_callback()
    except ImportError:
        logger.debug("blu_observability_bootstrap not available, Langfuse disabled")
        return None


def get_base_callbacks() -> list[BaseCallbackHandler]:
    """Return list of default callbacks (Langfuse, etc).

    Langfuse SDK v3 reads trace attributes from config["metadata"]
    at invoke time, so no parameters needed here.
    """
    callbacks = []

    lf = get_langfuse_callback()
    if lf:
        callbacks.append(lf)

    return callbacks


# ============================================================================
# EMBEDDING CLIENT (API)
# ============================================================================


class BluEmbeddingAPIClient(Embeddings):
    """
    Cliente de embedding via API HTTP.
    Não carrega modelos localmente - chama o embedding_service.

    Suporta modelos E5 automaticamente através do parâmetro 'mode':
    - mode="document" para armazenar documentos (prefixo "passage:")
    - mode="query" para buscar documentos (prefixo "query:")
    """

    def __init__(self, base_url: str):
        self.api_url = f"{base_url.rstrip('/')}/embed"

    def _call_api(self, texts: list[str], mode: str = "document") -> list[list[float]]:
        import requests

        try:
            response = requests.post(
                self.api_url,
                json={"texts": texts, "mode": mode},
                timeout=60,  # Timeout maior para modelos grandes
            )
            response.raise_for_status()
            return response.json()["embeddings"]
        except Exception as e:
            logger.error(f"Erro ao conectar ao Embedding Service ({self.api_url}): {e}")
            raise

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Gera embeddings para documentos (usa prefixo 'passage:' para E5)."""
        return self._call_api(texts, mode="document")

    def embed_query(self, text: str) -> list[float]:
        """Gera embedding para query (usa prefixo 'query:' para E5)."""
        return self._call_api([text], mode="query")[0]


# ============================================================================
# LLM FACTORIES
# ============================================================================


def _get_ollama_cloud_model(
    model_name: str,
    settings: LLMSettings,
    callbacks: list[BaseCallbackHandler],
    **kwargs,
) -> BaseChatModel:
    """
    Cria cliente Ollama Cloud (ollama.com).

    Usa a biblioteca nativa do Ollama (langchain-ollama) com host
    apontando para https://ollama.com e autenticação via header.

    Ref: https://docs.ollama.com/cloud

    Requer OLLAMA_CLOUD_API_KEY configurada.
    """
    from langchain_ollama import ChatOllama

    api_key = settings.OLLAMA_CLOUD_API_KEY
    if not api_key:
        raise ValueError(
            "OLLAMA_CLOUD_API_KEY não configurada. "
            "Obtenha sua API key em: https://ollama.com/settings/keys"
        )

    base_url = settings.OLLAMA_CLOUD_BASE_URL  # https://ollama.com

    logger.debug(f"Ollama Cloud: {base_url} model={model_name}")

    # Ollama Cloud usa a mesma API do Ollama local, mas com autenticação
    # Passamos o header de autorização via client_kwargs
    return ChatOllama(
        base_url=base_url,
        model=model_name,
        callbacks=callbacks,
        client_kwargs={"headers": {"Authorization": f"Bearer {api_key}"}},
        **kwargs,
    )


def _get_openai_model(
    model_name: str,
    settings: LLMSettings,
    callbacks: list[BaseCallbackHandler],
    **kwargs,
) -> BaseChatModel:
    """Cria cliente OpenAI (API)."""
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        raise ImportError("langchain-openai não instalado. Rode: pip install langchain-openai")

    api_key = settings.OPENAI_API_KEY
    if not api_key:
        raise ValueError("OPENAI_API_KEY não configurada")

    logger.debug(f"OpenAI: model={model_name}")

    return ChatOpenAI(model=model_name, api_key=api_key, callbacks=callbacks, **kwargs)


def _get_anthropic_model(
    model_name: str,
    settings: LLMSettings,
    callbacks: list[BaseCallbackHandler],
    **kwargs,
) -> BaseChatModel:
    """Cria cliente Anthropic (API)."""
    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError:
        raise ImportError(
            "langchain-anthropic não instalado. Rode: pip install langchain-anthropic"
        )

    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY não configurada")

    logger.debug(f"Anthropic: model={model_name}")

    return ChatAnthropic(model=model_name, api_key=api_key, callbacks=callbacks, **kwargs)


def _get_google_model(
    model_name: str,
    settings: LLMSettings,
    callbacks: list[BaseCallbackHandler],
    **kwargs,
) -> BaseChatModel:
    """Cria cliente Google Gemini (API)."""
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError:
        raise ImportError(
            "langchain-google-genai não instalado. Rode: pip install langchain-google-genai"
        )

    api_key = settings.GOOGLE_API_KEY
    if not api_key:
        raise ValueError("GOOGLE_API_KEY não configurada")

    logger.debug(f"Google Gemini: model={model_name}")

    return ChatGoogleGenerativeAI(
        model=model_name, google_api_key=api_key, callbacks=callbacks, **kwargs
    )


# ============================================================================
# MODEL MAPPINGS
# ============================================================================

MODEL_MAPPINGS: dict[LLMProvider, dict[ModelTier, str]] = {
    LLMProvider.OLLAMA_CLOUD: {
        ModelTier.DEFAULT: OllamaCloudModel.QWEN3_5,           # Alibaba; multimodal family
        ModelTier.FAST: OllamaCloudModel.QWEN3_5,              # Same for fast tier
        ModelTier.POWERFUL: OllamaCloudModel.QWEN3_5,          # Same for powerful tier
    },
    LLMProvider.OPENAI: {
        ModelTier.DEFAULT: "gpt-4o-mini",
        ModelTier.FAST: "gpt-4o-mini",
        ModelTier.POWERFUL: "gpt-4o",
    },
    LLMProvider.ANTHROPIC: {
        ModelTier.DEFAULT: "claude-3-5-sonnet-20241022",
        ModelTier.FAST: "claude-3-5-haiku-20241022",
        ModelTier.POWERFUL: "claude-3-5-sonnet-20241022",
    },
    LLMProvider.GOOGLE: {
        ModelTier.DEFAULT: "gemini-1.5-flash",
        ModelTier.FAST: "gemini-1.5-flash",
        ModelTier.POWERFUL: "gemini-1.5-pro",
    },
}

# Fallback models used when the primary model is unavailable (Ollama Cloud only).
# Wired automatically via LangChain's .with_fallbacks() in get_model().
FALLBACK_MODEL_MAPPINGS: dict[LLMProvider, dict[ModelTier, str]] = {
    LLMProvider.OLLAMA_CLOUD: {
        ModelTier.DEFAULT: OllamaCloudModel.GPT_OSS_20B,  # Fallback: 20B balanced
        ModelTier.FAST: OllamaCloudModel.GPT_OSS_20B,     # Fallback: 20B balanced
        ModelTier.POWERFUL: OllamaCloudModel.GPT_OSS_20B, # Fallback: 20B balanced
    },
}


# ============================================================================
# MAIN API
# ============================================================================


def get_model(
    tier: ModelTier = ModelTier.DEFAULT,
    task: ModelTask = ModelTask.GENERAL_AGENT,
    provider: LLMProvider | None = None,
    model_name: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    tags: list[str] | None = None,
    **kwargs,
) -> BaseChatModel:
    """
    Retorna um cliente de LLM configurado.

    For Ollama Cloud, automatically wires a fallback model via LangChain's
    .with_fallbacks() so that if the primary model is unavailable the request
    is retried against the fallback transparently.

    Primary / fallback per tier (Ollama Cloud):
      DEFAULT:  qwen3.5  → gpt-oss:20b
      FAST:     qwen3.5  → gpt-oss:20b
      POWERFUL: qwen3.5  → gpt-oss:20b

    Args:
        tier: Tier do modelo (default, fast, powerful)
        task: Tipo de tarefa
        provider: Provedor (ollama, openai, anthropic, google).
                  Se None, usa LLM_PROVIDER do settings.
        model_name: Nome específico do modelo (sobrescreve o mapeamento por tier
                    e desabilita o fallback automático)
        user_id: ID do usuário para Langfuse
        session_id: ID da sessão para Langfuse
        tags: Tags para Langfuse
        **kwargs: Parâmetros adicionais passados ao modelo

    Returns:
        BaseChatModel configurado (com fallback quando aplicável)

    Example:
        # Default agent model (qwen3.5 → gpt-oss:20b fallback)
        model = get_model()

        # Usar OpenAI GPT-4
        model = get_model(provider=LLMProvider.OPENAI, tier=ModelTier.POWERFUL)

        # Modelo específico (sem fallback automático)
        model = get_model(provider=LLMProvider.OPENAI, model_name="gpt-4-turbo")
    """
    settings = get_llm_settings()

    # Determina o provider
    if provider is None:
        provider = LLMProvider(settings.LLM_PROVIDER)

    # Determina o modelo
    explicit_model = model_name is not None
    if model_name is None:
        model_name = MODEL_MAPPINGS.get(provider, {}).get(tier, OllamaCloudModel.GPT_OSS_20B)

    # Cria callbacks (Langfuse reads trace attrs from config["metadata"] at invoke time)
    callbacks = get_base_callbacks()

    factory_map = {
        LLMProvider.OLLAMA_CLOUD: _get_ollama_cloud_model,
        LLMProvider.OPENAI: _get_openai_model,
        LLMProvider.ANTHROPIC: _get_anthropic_model,
        LLMProvider.GOOGLE: _get_google_model,
    }

    factory = factory_map.get(provider)
    if factory is None:
        raise ValueError(f"Provider não suportado: {provider}")

    primary = factory(model_name, settings, callbacks, **kwargs)

    # Wire fallback automatically for Ollama Cloud unless caller passed an
    # explicit model_name (in that case they know what they want).
    if not explicit_model and provider == LLMProvider.OLLAMA_CLOUD:
        fallback_name = FALLBACK_MODEL_MAPPINGS.get(provider, {}).get(tier)
        if fallback_name and fallback_name != model_name:
            logger.debug(f"Ollama Cloud: primary={model_name}, fallback={fallback_name}")
            fallback = factory(fallback_name, settings, callbacks, **kwargs)
            return primary.with_fallbacks([fallback])

    return primary


def get_embedding_model() -> Embeddings:
    """Return embedding client (via API)."""
    settings = get_llm_settings()
    logger.debug(f"BluEmbeddingAPIClient: {settings.EMBEDDING_SERVICE_URL}")
    return BluEmbeddingAPIClient(base_url=settings.EMBEDDING_SERVICE_URL)


# ============================================================================
# LANGFUSE UTILITIES (delegated to blu_observability_bootstrap)
# ============================================================================


def flush_langfuse():
    """Force flush Langfuse events."""
    try:
        from blu_observability_bootstrap.langfuse import flush_langfuse as _flush

        _flush()
    except ImportError:
        logger.debug("blu_observability_bootstrap not available")


def shutdown_langfuse():
    """Shutdown Langfuse client."""
    try:
        from blu_observability_bootstrap.langfuse import shutdown_langfuse as _shutdown

        _shutdown()
    except ImportError:
        logger.debug("blu_observability_bootstrap not available")
