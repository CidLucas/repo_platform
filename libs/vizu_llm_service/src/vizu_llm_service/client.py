# libs/vizu_llm_service/src/vizu_llm_service/client.py
"""
Vizu LLM Service: Cliente centralizado para LLMs locais e comerciais.

Suporta:
- Ollama (local)
- OpenAI (API)
- Anthropic (API)
- Google Gemini (API)

Com integração Langfuse para observabilidade.
"""

import logging
from enum import Enum
from typing import Any

from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

from .config import LLMSettings, get_llm_settings

logger = logging.getLogger(__name__)


def sanitize_observation(obj: dict, max_messages: int = 6) -> dict:
    """
    Return a sanitized shallow copy of an observation-like mapping.

    - Removes `_internal_context`.
    - Truncates `messages` to the last `max_messages` entries.
    - Trims `response_metadata` inside messages to small subset.
    """
    try:
        from collections.abc import Mapping
    except Exception:
        Mapping = dict

    if not isinstance(obj, Mapping):
        return obj

    o = dict(obj)
    o.pop("_internal_context", None)

    msgs = o.get("messages")
    if isinstance(msgs, list) and len(msgs) > max_messages:
        o["messages"] = msgs[-max_messages:]

    if isinstance(o.get("messages"), list):
        for m in o["messages"]:
            if isinstance(m, dict) and "response_metadata" in m:
                rm = m.get("response_metadata")
                if isinstance(rm, dict):
                    m["response_metadata"] = {
                        k: rm.get(k) for k in ("model", "done", "done_reason") if k in rm
                    }

    return o


# ============================================================================
# ENUMS
# ============================================================================


class ModelTier(str, Enum):
    """Tier de modelo - controla qualidade vs custo/velocidade."""

    DEFAULT = "default"  # Modelo padrão balanceado
    FAST = "fast"  # Modelo rápido/barato
    POWERFUL = "powerful"  # Modelo mais capaz/caro


class ModelTask(str, Enum):
    """Tipo de tarefa - pode influenciar na escolha do modelo."""

    GENERAL_AGENT = "general_agent"
    CLASSIFICATION = "classification"
    EMBEDDING = "embedding"
    RAG = "rag"


class LLMProvider(str, Enum):
    """Provedor de LLM."""

    OLLAMA = "ollama"  # Local (container)
    OLLAMA_CLOUD = "ollama_cloud"  # Ollama Cloud API (api.ollama.com)
    OPENAI = "openai"  # OpenAI API
    ANTHROPIC = "anthropic"  # Anthropic API
    GOOGLE = "google"  # Google Gemini API


# ============================================================================
# LANGFUSE CALLBACK (SDK v3)
# ============================================================================


def get_langfuse_callback(
    settings: LLMSettings | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> BaseCallbackHandler | None:
    """
    Cria o CallbackHandler do Langfuse para tracing.

    SDK v3: Usa variáveis de ambiente ou inicialização explícita.

    Variáveis necessárias:
    - LANGFUSE_SECRET_KEY
    - LANGFUSE_PUBLIC_KEY
    - LANGFUSE_HOST (opcional, default: https://cloud.langfuse.com)

    Args:
        settings: LLMSettings (opcional)
        user_id: ID do usuário para agrupar traces
        session_id: ID da sessão para agrupar traces
        tags: Tags para categorização
        metadata: Metadados adicionais

    Returns:
        CallbackHandler ou None se Langfuse não estiver configurado
    """
    if settings is None:
        settings = get_llm_settings()

    if not settings.langfuse_enabled:
        logger.debug("Langfuse não está habilitado (faltam credenciais)")
        return None

    try:
        # Langfuse SDK v3 - import correto
        from langfuse import Langfuse
        from langfuse.langchain import CallbackHandler

        # Inicializa o cliente Langfuse (singleton)
        Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
        )

        # Cria o handler - SDK v3 não aceita args no construtor
        handler = CallbackHandler()

        # Wrap handler with a sanitizer to avoid leaking internal state
        class SanitizingCallback(BaseCallbackHandler):
            """
            Wrapper around an existing callback handler that sanitizes
            any dict-like observation/outputs passed to callback methods.

            Behaviors:
            - Truncates `messages` lists to `max_messages` (default 6)
            - Removes `_internal_context` key entirely
            - Truncates large `response_metadata` objects to a small subset
            """

            def __init__(self, inner, max_messages: int = 6):
                self._inner = inner
                self._max_messages = max_messages

            def _sanitize_obj(self, obj):
                try:
                    return sanitize_observation(obj, max_messages=self._max_messages)
                except Exception:
                    return obj

            def _wrap_call(self, func, *args, **kwargs):
                # Sanitize all mapping-like positional args and kwargs
                new_args = []
                for a in args:
                    try:
                        from collections.abc import Mapping
                    except Exception:
                        Mapping = dict
                    if isinstance(a, Mapping):
                        new_args.append(self._sanitize_obj(a))
                    else:
                        new_args.append(a)

                new_kwargs = {}
                for k, v in kwargs.items():
                    try:
                        from collections.abc import Mapping
                    except Exception:
                        Mapping = dict
                    if isinstance(v, Mapping):
                        new_kwargs[k] = self._sanitize_obj(v)
                    else:
                        new_kwargs[k] = v

                return func(*new_args, **new_kwargs)

            # Generic delegation for known callback entrypoints
            def on_chain_start(self, serialized, inputs, **kwargs):
                try:
                    return self._wrap_call(self._inner.on_chain_start, serialized, inputs, **kwargs)
                except Exception:
                    return None

            def on_chain_end(self, outputs, **kwargs):
                try:
                    return self._wrap_call(self._inner.on_chain_end, outputs, **kwargs)
                except Exception:
                    return None

            def on_llm_end(self, response, **kwargs):
                try:
                    return self._wrap_call(self._inner.on_llm_end, response, **kwargs)
                except Exception:
                    return None

            def on_tool_end(self, output, **kwargs):
                try:
                    return self._wrap_call(self._inner.on_tool_end, output, **kwargs)
                except Exception:
                    return None

            def __getattr__(self, name):
                # Fallback: delegate any other attribute to inner handler
                return getattr(self._inner, name)

        wrapped = SanitizingCallback(handler, max_messages=getattr(settings, "LANGFUSE_MAX_OBSERVATION_MESSAGES", 6))

        logger.debug(f"Langfuse callback created - host: {settings.LANGFUSE_HOST}")
        return wrapped

    except ImportError:
        logger.warning("langfuse não instalado, tracing desabilitado")
        return None
    except Exception as e:
        logger.error(f"Erro ao criar Langfuse callback: {e}")
        return None


def get_base_callbacks(
    settings: LLMSettings | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    tags: list[str] | None = None,
) -> list[BaseCallbackHandler]:
    """Retorna lista de callbacks padrão (Langfuse, etc)."""
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


def _get_ollama_model(
    model_name: str,
    settings: LLMSettings,
    callbacks: list[BaseCallbackHandler],
    **kwargs,
) -> BaseChatModel:
    """Cria cliente Ollama (local)."""
    from langchain_ollama import ChatOllama

    logger.debug(f"Ollama Local: {settings.OLLAMA_BASE_URL} model={model_name}")

    return ChatOllama(
        base_url=settings.OLLAMA_BASE_URL,
        model=model_name,
        callbacks=callbacks,
        **kwargs,
    )


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
        raise ImportError(
            "langchain-openai não instalado. Rode: pip install langchain-openai"
        )

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

    return ChatAnthropic(
        model=model_name, api_key=api_key, callbacks=callbacks, **kwargs
    )


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
    LLMProvider.OLLAMA: {
        ModelTier.DEFAULT: "llama3.2:latest",
        ModelTier.FAST: "phi3:mini",
        ModelTier.POWERFUL: "llama3.1:70b",
    },
    LLMProvider.OLLAMA_CLOUD: {
        ModelTier.DEFAULT: "gpt-oss:20b",  # Rápido e eficiente
        ModelTier.FAST: "gpt-oss:20b",  # Mais rápido
        ModelTier.POWERFUL: "deepseek-v3.1:671b",  # Mais capaz
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
        model_name = MODEL_MAPPINGS.get(provider, {}).get(tier, "llama3.2:latest")

    # Cria callbacks
    callbacks = get_base_callbacks(
        settings=settings,
        user_id=user_id,
        session_id=session_id,
        tags=tags,
    )

    # Cria o modelo
    factory_map = {
        LLMProvider.OLLAMA: _get_ollama_model,
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
    """Retorna o cliente de embeddings (via API)."""
    settings = get_llm_settings()
    logger.info(
        f"Inicializando VizuEmbeddingAPIClient: {settings.EMBEDDING_SERVICE_URL}"
    )
    return VizuEmbeddingAPIClient(base_url=settings.EMBEDDING_SERVICE_URL)


# ============================================================================
# LANGFUSE UTILITIES
# ============================================================================


def flush_langfuse():
    """Força o flush dos eventos do Langfuse."""
    try:
        from langfuse import get_client

        get_client().flush()
        logger.debug("Langfuse flush completed")
    except Exception as e:
        logger.warning(f"Erro ao flush Langfuse: {e}")


def shutdown_langfuse():
    """Encerra o cliente Langfuse."""
    try:
        from langfuse import get_client

        get_client().shutdown()
        logger.debug("Langfuse shutdown completed")
    except Exception as e:
        logger.warning(f"Erro ao shutdown Langfuse: {e}")
