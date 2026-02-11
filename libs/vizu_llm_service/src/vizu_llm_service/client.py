# libs/vizu_llm_service/src/vizu_llm_service/client.py
"""
Vizu LLM Service: Centralized client for local and commercial LLMs.

Supports:
- Ollama (local)
- OpenAI (API)
- Anthropic (API)
- Google Gemini (API)

Langfuse integration is handled by vizu_observability_bootstrap.
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


# ============================================================================
# LANGFUSE CALLBACKS (delegated to vizu_observability_bootstrap)
# ============================================================================


def get_langfuse_callback(
    settings: LLMSettings | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    trace_name: str | None = None,
) -> BaseCallbackHandler | None:
    """
    Create Langfuse CallbackHandler for LLM tracing.

    Delegates to vizu_observability_bootstrap.langfuse module.

    Args:
        settings: LLMSettings (optional, for backwards compatibility)
        user_id: User ID for trace grouping
        session_id: Session ID for trace grouping
        tags: Tags for categorization
        metadata: Additional metadata
        trace_name: Name for the trace (e.g., 'atendente_chat')

    Returns:
        CallbackHandler or None if Langfuse not configured
    """
    try:
        from vizu_observability_bootstrap.langfuse import (
            get_langfuse_callback as _get_callback,
        )

        return _get_callback(
            user_id=user_id,
            session_id=session_id,
            tags=tags,
            metadata=metadata,
            trace_name=trace_name,
        )
    except ImportError:
        logger.debug("vizu_observability_bootstrap not available, Langfuse disabled")
        return None


def get_base_callbacks(
    settings: LLMSettings | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    tags: list[str] | None = None,
) -> list[BaseCallbackHandler]:
    """Return list of default callbacks (Langfuse, etc)."""
    callbacks = []

    lf = get_langfuse_callback(
        settings=settings,
        user_id=user_id,
        session_id=session_id,
        tags=tags,
    )
    if lf:
        callbacks.append(lf)

    return callbacks


# ============================================================================
# EMBEDDING CLIENT (API)
# ============================================================================


class VizuEmbeddingAPIClient(Embeddings):
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
        ModelTier.DEFAULT: "gpt-oss:20b",  # Balanced
        ModelTier.FAST: "gpt-oss:20b",  # Fast/efficient
        ModelTier.POWERFUL: "deepseek-v3.1:671b",  # Most capable
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

    Args:
        tier: Tier do modelo (default, fast, powerful)
        task: Tipo de tarefa
        provider: Provedor (ollama, openai, anthropic, google).
                  Se None, usa LLM_PROVIDER do settings.
        model_name: Nome específico do modelo (sobrescreve o mapeamento por tier)
        user_id: ID do usuário para Langfuse
        session_id: ID da sessão para Langfuse
        tags: Tags para Langfuse
        **kwargs: Parâmetros adicionais passados ao modelo

    Returns:
        BaseChatModel configurado

    Example:
        # Usar Ollama local (padrão)
        model = get_model()

        # Usar OpenAI GPT-4
        model = get_model(provider=LLMProvider.OPENAI, tier=ModelTier.POWERFUL)

        # Modelo específico
        model = get_model(provider=LLMProvider.OPENAI, model_name="gpt-4-turbo")
    """
    settings = get_llm_settings()

    # Determina o provider
    if provider is None:
        provider = LLMProvider(settings.LLM_PROVIDER)

    # Determina o modelo
    if model_name is None:
        model_name = MODEL_MAPPINGS.get(provider, {}).get(tier, "gpt-oss:20b")

    # Cria callbacks
    callbacks = get_base_callbacks(
        settings=settings,
        user_id=user_id,
        session_id=session_id,
        tags=tags,
    )

    # Cria o modelo
    factory_map = {
        LLMProvider.OLLAMA_CLOUD: _get_ollama_cloud_model,
        LLMProvider.OPENAI: _get_openai_model,
        LLMProvider.ANTHROPIC: _get_anthropic_model,
        LLMProvider.GOOGLE: _get_google_model,
    }

    factory = factory_map.get(provider)
    if factory is None:
        raise ValueError(f"Provider não suportado: {provider}")

    return factory(model_name, settings, callbacks, **kwargs)


def get_embedding_model() -> Embeddings:
    """Return embedding client (via API)."""
    settings = get_llm_settings()
    logger.debug(f"VizuEmbeddingAPIClient: {settings.EMBEDDING_SERVICE_URL}")
    return VizuEmbeddingAPIClient(base_url=settings.EMBEDDING_SERVICE_URL)


# ============================================================================
# LANGFUSE UTILITIES (delegated to vizu_observability_bootstrap)
# ============================================================================


def flush_langfuse():
    """Force flush Langfuse events."""
    try:
        from vizu_observability_bootstrap.langfuse import flush_langfuse as _flush

        _flush()
    except ImportError:
        logger.debug("vizu_observability_bootstrap not available")


def shutdown_langfuse():
    """Shutdown Langfuse client."""
    try:
        from vizu_observability_bootstrap.langfuse import shutdown_langfuse as _shutdown

        _shutdown()
    except ImportError:
        logger.debug("vizu_observability_bootstrap not available")
