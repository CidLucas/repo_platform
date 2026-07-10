# libs/blu_llm_service/src/blu_llm_service/client.py
"""
Blu LLM Service: Centralized client for local and commercial LLMs.

Supports:
- Ollama Cloud (ollama.com)
- OpenAI (API)
- Anthropic (API)
- Google Gemini (API)
- HuggingFace Inference API
- DeepSeek (API direta, OpenAI-compatible)

Langfuse integration is handled by blu_observability_bootstrap.
"""

from __future__ import annotations

import logging
import os
from enum import Enum
from typing import Any

from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

from blu_llm_service.config import LLMSettings, get_llm_settings

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
    """Task type — controls which specialized model is selected."""

    GENERAL_AGENT = "general_agent"   # General chat/agent (default)
    CLASSIFICATION = "classification" # Intent routing, label classification
    EMBEDDING = "embedding"           # Vector embeddings
    RAG = "rag"                       # Retrieval-augmented generation
    CODE = "code"                     # Code generation / completion
    MATH = "math"                     # Mathematical reasoning, Text-to-SQL
    SUMMARIZATION = "summarization"   # Document/report summarization
    ASR = "asr"                       # Automatic Speech Recognition
    TTS = "tts"                       # Text-to-Speech
    IMAGE_TO_TEXT = "image_to_text"   # OCR / image captioning / vision


class LLMProvider(Enum):
    """LLM provider."""

    OLLAMA_CLOUD = "ollama_cloud"   # Ollama Cloud API (ollama.com)
    OPENAI = "openai"               # OpenAI API
    ANTHROPIC = "anthropic"         # Anthropic API
    GOOGLE = "google"               # Google Gemini API
    HUGGINGFACE = "huggingface"     # HuggingFace Inference API
    DEEPSEEK = "deepseek"           # DeepSeek API direta (OpenAI-compatible)


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
    QWEN3_5 = "qwen3.5:397b"                        # Alibaba; multimodal family (0.8B–122B)
    QWEN3_CODER_NEXT = "qwen3-coder-next"         # Alibaba; coding-focused

    # --- Fast / Lightweight ---
    GPT_OSS_20B = "gpt-oss:20b"                   # OpenAI OSS; 20B balanced
    DEEPSEEK_R1_14B = "deepseek-r1:14b"           # DeepSeek R1; 14B reasoning
    MINISTRAL_3 = "ministral-3:8b"                   # Mistral; 3–14B, edge deployment
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

    Historically this returned a Langfuse singleton handler that was
    baked into LLM constructors. That created a SECOND, flat trace in
    Langfuse (no trace_id, no session_id) which appeared as a single
    non-expandable trace in the UI and hid the proper hierarchical
    trace created per-invocation by agent_api/core/observability.py.

    Now returns an empty list so the per-invocation handler passed via
    LangGraph config is the SOLE source of LLM tracing — yielding one
    hierarchical trace per request. LangChain's automatic callback
    propagation routes the config callbacks to every nested Runnable
    (graph nodes, LLM calls, tool calls).

    Re-enable this only if you need to trace LLM calls made OUTSIDE a
    LangGraph context (e.g., standalone scripts, ad-hoc classifiers).
    """
    return []


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
# COHERE EMBEDDING CLIENT (Direct API)
# ============================================================================


class CohereEmbeddingClient(Embeddings):
    """Cliente Cohere embed-multilingual-light-v3.0 (384 dims).

    Espelha o comportamento das Edge Functions process-document
    e search-documents. Usa API v2/embed com batching de ateh 96 textos.

    Modelo: embed-multilingual-light-v3.0
    Dimensoes: 384 (halfvec)
    API: POST https://api.cohere.com/v2/embed
    """

    MODEL = "embed-multilingual-light-v3.0"
    DIMENSIONS = 384
    BATCH_SIZE = 96

    def __init__(self, api_key: str):
        self.api_key = api_key

    def _call_api(self, texts: list[str], input_type: str) -> list[list[float]]:
        """Chama Cohere v2/embed com batching.

        Args:
            texts: Lista de textos para embedding.
            input_type: 'search_document' (storage) ou 'search_query' (busca).

        Returns:
            Lista de embeddings (cada um com 384 floats).

        Raises:
            requests.HTTPError: Se a API retornar erro.
        """
        import requests

        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), self.BATCH_SIZE):
            batch = texts[i : i + self.BATCH_SIZE]
            resp = requests.post(
                "https://api.cohere.com/v2/embed",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.MODEL,
                    "texts": batch,
                    "input_type": input_type,
                    "embedding_types": ["float"],
                },
                timeout=60,
            )
            resp.raise_for_status()
            all_embeddings.extend(resp.json()["embeddings"]["float"])
        return all_embeddings

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Gera embeddings para documentos (input_type='search_document')."""
        return self._call_api(texts, input_type="search_document")

    def embed_query(self, text: str) -> list[float]:
        """Gera embedding para query (input_type='search_query')."""
        return self._call_api([text], input_type="search_query")[0]


# ============================================================================
# LLM FACTORIES
# ============================================================================


def _get_ollama_cloud_model(
    model_name: str,
    settings: LLMSettings,
    callbacks: list[BaseCallbackHandler],
    **kwargs: Any,
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
    **kwargs: Any,
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
    **kwargs: Any,
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
    **kwargs: Any,
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


def _get_huggingface_model(
    model_name: str,
    settings: LLMSettings,
    callbacks: list[BaseCallbackHandler],
    **kwargs: Any,
) -> BaseChatModel:
    """
    Cria cliente HuggingFace via Inference API (OpenAI-compatible endpoint).

    Usa ChatOpenAI apontando para a Inference API do HuggingFace, que expõe
    um endpoint OpenAI-compatible em:
      https://api-inference.huggingface.co/models/{model}/v1

    Não requer langchain-huggingface — usa langchain-openai que já é dependência.

    Args:
        model_name: HuggingFace model ID (ex: "Qwen/Qwen2.5-Coder-7B-Instruct")
        settings: LLMSettings com HF_TOKEN
        callbacks: Langfuse callbacks
        **kwargs: Params extras para ChatOpenAI

    Raises:
        ValueError: Se HF_TOKEN não configurado
        ImportError: Se langchain-openai não instalado
    """
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        raise ImportError("langchain-openai não instalado. Rode: pip install langchain-openai")

    token = settings.HF_TOKEN
    if not token:
        raise ValueError(
            "HF_TOKEN não configurado. "
            "Obtenha em: https://huggingface.co/settings/tokens"
        )

    base_url = f"https://api-inference.huggingface.co/models/{model_name}/v1"
    logger.debug(f"HuggingFace Inference API: model={model_name}")

    return ChatOpenAI(
        model=model_name,
        api_key=token,
        base_url=base_url,
        callbacks=callbacks,
        **kwargs,
    )


def _get_deepseek_model(
    model_name: str,
    settings: LLMSettings,
    callbacks: list[BaseCallbackHandler],
    **kwargs: Any,
) -> BaseChatModel:
    """
    Cria cliente DeepSeek via API direta (endpoint OpenAI-compatible).

    Usa ChatOpenAI apontando para https://api.deepseek.com.
    Modelos: "deepseek-v4-flash" (rápido) e "deepseek-v4-pro" (frontier).

    Ref: https://api-docs.deepseek.com

    Requer DEEPSEEK_API_KEY configurada.
    """
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        raise ImportError("langchain-openai não instalado. Rode: pip install langchain-openai")

    api_key = settings.DEEPSEEK_API_KEY
    if not api_key:
        raise ValueError(
            "DEEPSEEK_API_KEY não configurada. "
            "Obtenha em: https://platform.deepseek.com/api_keys"
        )

    logger.debug(f"DeepSeek: {settings.DEEPSEEK_BASE_URL} model={model_name}")

    return ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=settings.DEEPSEEK_BASE_URL,
        callbacks=callbacks,
        **kwargs,
    )


# ============================================================================
# MODEL MAPPINGS
# ============================================================================

MODEL_MAPPINGS: dict[LLMProvider, dict[ModelTier, str]] = {
    LLMProvider.OLLAMA_CLOUD: {
        ModelTier.FAST:     OllamaCloudModel.MINISTRAL_3,        # confirmed working
        ModelTier.DEFAULT:  OllamaCloudModel.DEEPSEEK_V4_FLASH,   # 284B MoE, 1M ctx, SQL tasks
        ModelTier.POWERFUL: OllamaCloudModel.DEEPSEEK_V4_PRO,     # frontier MoE, 1M ctx
    },
    LLMProvider.OPENAI: {
        ModelTier.FAST:     "gpt-4o-mini",
        ModelTier.DEFAULT:  "gpt-4o-mini",
        ModelTier.POWERFUL: "gpt-4o",
    },
    LLMProvider.ANTHROPIC: {
        ModelTier.FAST:     "claude-haiku-4-5-20251001",
        ModelTier.DEFAULT:  "claude-sonnet-4-6",
        ModelTier.POWERFUL: "claude-opus-4-7",
    },
    LLMProvider.GOOGLE: {
        ModelTier.FAST:     "gemini-1.5-flash",
        ModelTier.DEFAULT:  "gemini-2.0-flash",
        ModelTier.POWERFUL: "gemini-1.5-pro",
    },
    LLMProvider.DEEPSEEK: {
        # IDs confirmados via GET https://api.deepseek.com/models (2026-07)
        ModelTier.FAST:     "deepseek-v4-flash",  # MoE 284B (13B ativos), 1M ctx
        ModelTier.DEFAULT:  "deepseek-v4-flash",
        ModelTier.POWERFUL: "deepseek-v4-pro",    # frontier MoE, 1M ctx
    },
}

# Fallback models used when the primary model is unavailable (Ollama Cloud only).
# Wired automatically via LangChain's .with_fallbacks() in get_model().
FALLBACK_MODEL_MAPPINGS: dict[LLMProvider, dict[ModelTier, str]] = {
    LLMProvider.OLLAMA_CLOUD: {
        ModelTier.FAST:     OllamaCloudModel.MINISTRAL_3,  # fallback = same (only confirmed working model)
        ModelTier.DEFAULT:  OllamaCloudModel.MINISTRAL_3,  # fallback = same
        ModelTier.POWERFUL: OllamaCloudModel.MINISTRAL_3,  # fallback = same
    },
}


# Task-specific model overrides.
# When get_model() receives a specialized task, these mappings take priority
# over MODEL_MAPPINGS[provider][tier]. Provider in the tuple is always the
# one that will be used regardless of LLM_PROVIDER env setting.
#
# Tasks NOT in this table (GENERAL_AGENT) fall through to MODEL_MAPPINGS.
# EMBEDDING, ASR, TTS, IMAGE_TO_TEXT are handled by dedicated get_*() helpers.
TASK_MODEL_MAPPINGS: dict[tuple[ModelTask, ModelTier], tuple[LLMProvider, str]] = {
    # ── CODE ────────────────────────────────────────────────────────────────
    # Qwen2.5-Coder: especializado, supera modelos gerais do mesmo tamanho
    # Qwen3-Coder-30B-A3B: MoE — 30B total, 3B ativos → custo de 3B, qualidade de 30B
    (ModelTask.CODE, ModelTier.FAST):     (LLMProvider.HUGGINGFACE, "Qwen/Qwen2.5-Coder-1.5B-Instruct"),
    (ModelTask.CODE, ModelTier.DEFAULT):  (LLMProvider.HUGGINGFACE, "Qwen/Qwen2.5-Coder-7B-Instruct"),
    (ModelTask.CODE, ModelTier.POWERFUL): (LLMProvider.HUGGINGFACE, "Qwen/Qwen3-Coder-30B-A3B-Instruct"),

    # ── MATH ────────────────────────────────────────────────────────────────
    # Qwen2.5-Math: treinado com verificação formal, CoT matemático nativo
    # Usado para: text_to_sql com cálculos, projeções financeiras, percentuais
    (ModelTask.MATH, ModelTier.FAST):     (LLMProvider.HUGGINGFACE, "Qwen/Qwen2.5-Math-1.5B-Instruct"),
    (ModelTask.MATH, ModelTier.DEFAULT):  (LLMProvider.HUGGINGFACE, "Qwen/Qwen2.5-Math-7B-Instruct"),
    (ModelTask.MATH, ModelTier.POWERFUL): (LLMProvider.HUGGINGFACE, "Qwen/Qwen2.5-Math-7B-Instruct"),

    # ── CLASSIFICATION ──────────────────────────────────────────────────────
    # Modelos pequenos: intent routing não precisa de raciocínio profundo
    # latência <150ms via HF Inference API serverless
    (ModelTask.CLASSIFICATION, ModelTier.FAST):     (LLMProvider.HUGGINGFACE, "Qwen/Qwen2.5-1.5B-Instruct"),
    (ModelTask.CLASSIFICATION, ModelTier.DEFAULT):  (LLMProvider.HUGGINGFACE, "Qwen/Qwen2.5-3B-Instruct"),
    (ModelTask.CLASSIFICATION, ModelTier.POWERFUL): (LLMProvider.HUGGINGFACE, "Qwen/Qwen2.5-7B-Instruct"),

    # ── RAG ─────────────────────────────────────────────────────────────────
    # Compressão de contexto e reranking de chunks
    # Modelos instruct pequenos: entendem bem, geram pouco (tarefa de compreensão)
    (ModelTask.RAG, ModelTier.FAST):     (LLMProvider.HUGGINGFACE, "Qwen/Qwen2.5-3B-Instruct"),
    (ModelTask.RAG, ModelTier.DEFAULT):  (LLMProvider.HUGGINGFACE, "Qwen/Qwen2.5-7B-Instruct"),
    (ModelTask.RAG, ModelTier.POWERFUL): (LLMProvider.HUGGINGFACE, "Qwen/Qwen3-8B"),

    # ── SUMMARIZATION ───────────────────────────────────────────────────────
    # FAST: BART é seq2seq dedicado a sumarização — mais eficiente que chat model
    # DEFAULT/POWERFUL: Qwen3 para resumos longos com contexto de negócio
    (ModelTask.SUMMARIZATION, ModelTier.FAST):     (LLMProvider.HUGGINGFACE, "facebook/bart-large-cnn"),
    (ModelTask.SUMMARIZATION, ModelTier.DEFAULT):  (LLMProvider.HUGGINGFACE, "Qwen/Qwen3-8B"),
    (ModelTask.SUMMARIZATION, ModelTier.POWERFUL): (LLMProvider.HUGGINGFACE, "Qwen/Qwen3-32B"),
}

# Fallbacks para task-specific HuggingFace models
TASK_FALLBACK_MAPPINGS: dict[tuple[ModelTask, ModelTier], tuple[LLMProvider, str]] = {
    (ModelTask.CODE, ModelTier.FAST):              (LLMProvider.HUGGINGFACE, "Qwen/Qwen2.5-1.5B-Instruct"),
    (ModelTask.CODE, ModelTier.DEFAULT):           (LLMProvider.HUGGINGFACE, "Qwen/Qwen2.5-Coder-3B"),
    (ModelTask.CODE, ModelTier.POWERFUL):          (LLMProvider.HUGGINGFACE, "Qwen/Qwen2.5-Coder-7B-Instruct"),
    (ModelTask.MATH, ModelTier.FAST):              (LLMProvider.HUGGINGFACE, "Qwen/Qwen3-4B"),
    (ModelTask.MATH, ModelTier.DEFAULT):           (LLMProvider.HUGGINGFACE, "Qwen/Qwen2.5-Math-1.5B-Instruct"),
    (ModelTask.MATH, ModelTier.POWERFUL):          (LLMProvider.HUGGINGFACE, "Qwen/Qwen2.5-Math-1.5B-Instruct"),
    (ModelTask.CLASSIFICATION, ModelTier.FAST):    (LLMProvider.HUGGINGFACE, "Qwen/Qwen3-0.6B"),
    (ModelTask.CLASSIFICATION, ModelTier.DEFAULT): (LLMProvider.HUGGINGFACE, "Qwen/Qwen2.5-1.5B-Instruct"),
    (ModelTask.CLASSIFICATION, ModelTier.POWERFUL):(LLMProvider.HUGGINGFACE, "Qwen/Qwen2.5-3B-Instruct"),
    (ModelTask.RAG, ModelTier.FAST):               (LLMProvider.HUGGINGFACE, "Qwen/Qwen3-0.6B"),
    (ModelTask.RAG, ModelTier.DEFAULT):            (LLMProvider.HUGGINGFACE, "Qwen/Qwen2.5-3B-Instruct"),
    (ModelTask.RAG, ModelTier.POWERFUL):           (LLMProvider.HUGGINGFACE, "Qwen/Qwen2.5-7B-Instruct"),
    (ModelTask.SUMMARIZATION, ModelTier.FAST):     (LLMProvider.HUGGINGFACE, "sshleifer/distilbart-cnn-12-6"),
    (ModelTask.SUMMARIZATION, ModelTier.DEFAULT):  (LLMProvider.HUGGINGFACE, "Qwen/Qwen3-4B"),
    (ModelTask.SUMMARIZATION, ModelTier.POWERFUL): (LLMProvider.HUGGINGFACE, "Qwen/Qwen3-8B"),
}

# ── Specialized task model config (não-chat: ASR, TTS, Vision) ──────────────
# Usado pelas funções get_asr_client(), get_tts_client(), get_image_to_text_client()
SPECIALIZED_MODEL_MAPPINGS: dict[tuple[ModelTask, ModelTier], str] = {
    # ASR — Whisper family (OpenAI open-source, padrão da indústria)
    (ModelTask.ASR, ModelTier.FAST):     "openai/whisper-small",
    (ModelTask.ASR, ModelTier.DEFAULT):  "openai/whisper-large-v3-turbo",
    (ModelTask.ASR, ModelTier.POWERFUL): "Qwen/Qwen3-ASR-1.7B",
    # TTS — Kokoro (ultra-rápido), XTTS-v2 (voice cloning), Qwen3-TTS (custom voice)
    (ModelTask.TTS, ModelTier.FAST):     "hexgrad/Kokoro-82M",
    (ModelTask.TTS, ModelTier.DEFAULT):  "coqui/XTTS-v2",
    (ModelTask.TTS, ModelTier.POWERFUL): "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    # IMAGE_TO_TEXT — TrOCR (OCR), BLIP (captioning), Qwen2-VL (visão geral)
    (ModelTask.IMAGE_TO_TEXT, ModelTier.FAST):     "microsoft/trocr-base-printed",
    (ModelTask.IMAGE_TO_TEXT, ModelTier.DEFAULT):  "Salesforce/blip-image-captioning-large",
    (ModelTask.IMAGE_TO_TEXT, ModelTier.POWERFUL): "Qwen/Qwen2-VL-7B-Instruct",
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
    **kwargs: Any,
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

    # Determina o provider padrão do ambiente
    if provider is None:
        provider = LLMProvider(settings.LLM_PROVIDER)

    # ── Task-specific routing ────────────────────────────────────────────────
    # Tasks especializadas (CODE, MATH, CLASSIFICATION, RAG, SUMMARIZATION)
    # sobrescrevem o provider/model independente do LLM_PROVIDER do ambiente.
    task_key = (task, tier)
    if task_key in TASK_MODEL_MAPPINGS and model_name is None:
        task_provider, task_model = TASK_MODEL_MAPPINGS[task_key]
        logger.debug(f"Task routing: task={task.value} tier={tier.value} → {task_provider.value}/{task_model}")

        callbacks = get_base_callbacks()
        factory_map = {
            LLMProvider.OLLAMA_CLOUD: _get_ollama_cloud_model,
            LLMProvider.OPENAI: _get_openai_model,
            LLMProvider.ANTHROPIC: _get_anthropic_model,
            LLMProvider.GOOGLE: _get_google_model,
            LLMProvider.HUGGINGFACE: _get_huggingface_model,
            LLMProvider.DEEPSEEK: _get_deepseek_model,
        }
        factory = factory_map[task_provider]
        primary = factory(task_model, settings, callbacks, **kwargs)

        # Wire task fallback
        fallback_entry = TASK_FALLBACK_MAPPINGS.get(task_key)
        if fallback_entry:
            fb_provider, fb_model = fallback_entry
            if fb_model != task_model:
                fb_factory = factory_map.get(fb_provider, _get_huggingface_model)
                try:
                    fallback = fb_factory(fb_model, settings, callbacks, **kwargs)
                    return primary.with_fallbacks([fallback])
                except Exception as e:
                    logger.warning(f"Não foi possível criar fallback {fb_model}: {e}")

        return primary

    # ── Standard provider/tier routing (GENERAL_AGENT e tasks sem mapeamento) ─
    explicit_model = model_name is not None
    if model_name is None:
        model_name = MODEL_MAPPINGS.get(provider, {}).get(tier, OllamaCloudModel.GPT_OSS_20B)

    callbacks = get_base_callbacks()

    factory_map = {
        LLMProvider.OLLAMA_CLOUD: _get_ollama_cloud_model,
        LLMProvider.OPENAI: _get_openai_model,
        LLMProvider.ANTHROPIC: _get_anthropic_model,
        LLMProvider.GOOGLE: _get_google_model,
        LLMProvider.HUGGINGFACE: _get_huggingface_model,
        LLMProvider.DEEPSEEK: _get_deepseek_model,
    }

    factory = factory_map.get(provider)
    if factory is None:
        raise ValueError(f"Provider não suportado: {provider}")

    primary = factory(model_name, settings, callbacks, **kwargs)

    # Wire fallback automaticamente para Ollama Cloud
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


def get_cohere_embedding_model() -> CohereEmbeddingClient:
    """Retorna cliente Cohere de embedding.

    Requer CO_API_KEY no ambiente (mesma env var das Edge Functions).

    Returns:
        CohereEmbeddingClient configurado.

    Raises:
        ValueError: Se CO_API_KEY nao estiver configurada.
    """
    settings = get_llm_settings()
    api_key = getattr(settings, "CO_API_KEY", None) or os.environ.get("CO_API_KEY")
    if not api_key:
        raise ValueError(
            "CO_API_KEY nao configurada. "
            "Obtenha em: https://dashboard.cohere.com/api-keys"
        )
    logger.debug("CohereEmbeddingClient: model=%s dims=%d", CohereEmbeddingClient.MODEL, CohereEmbeddingClient.DIMENSIONS)
    return CohereEmbeddingClient(api_key=api_key)


# ============================================================================
# SPECIALIZED TASK CLIENTS (ASR, TTS, IMAGE_TO_TEXT)
# ============================================================================


def get_hf_inference_client(task: ModelTask = ModelTask.ASR, tier: ModelTier = ModelTier.DEFAULT) -> Any:
    """
    Retorna um InferenceClient do HuggingFace para tasks especializadas
    que não são BaseChatModel: ASR, TTS, IMAGE_TO_TEXT.

    Requires:
        pip install huggingface-hub>=0.30

    Args:
        task: ModelTask.ASR | ModelTask.TTS | ModelTask.IMAGE_TO_TEXT
        tier: FAST | DEFAULT | POWERFUL

    Returns:
        huggingface_hub.InferenceClient configurado com o modelo adequado

    Example:
        # Transcrever áudio
        client = get_hf_inference_client(ModelTask.ASR, ModelTier.DEFAULT)
        result = client.automatic_speech_recognition("audio.wav")

        # TTS
        client = get_hf_inference_client(ModelTask.TTS, ModelTier.FAST)
        audio = client.text_to_speech("Olá, tudo bem?")

        # OCR / Image captioning
        client = get_hf_inference_client(ModelTask.IMAGE_TO_TEXT, ModelTier.FAST)
        caption = client.image_to_text("document.jpg")
    """
    try:
        from huggingface_hub import InferenceClient
    except ImportError:
        raise ImportError(
            "huggingface-hub não instalado. Rode: pip install huggingface-hub>=0.30"
        )

    settings = get_llm_settings()
    if not settings.HF_TOKEN:
        raise ValueError(
            "HF_TOKEN não configurado. "
            "Obtenha em: https://huggingface.co/settings/tokens"
        )

    model_id = SPECIALIZED_MODEL_MAPPINGS.get(
        (task, tier),
        SPECIALIZED_MODEL_MAPPINGS.get((task, ModelTier.DEFAULT)),
    )
    if model_id is None:
        raise ValueError(f"Task {task.value} não tem mapeamento de modelo especializado")

    logger.debug(f"HF InferenceClient: task={task.value} tier={tier.value} model={model_id}")

    return InferenceClient(
        model=model_id,
        token=settings.HF_TOKEN,
        provider=settings.HF_INFERENCE_PROVIDER,
    )


# ============================================================================
# LANGFUSE UTILITIES (delegated to blu_observability_bootstrap)
# ============================================================================


def flush_langfuse() -> None:
    """Force flush Langfuse events."""
    try:
        from blu_observability_bootstrap.langfuse import flush_langfuse as _flush

        _flush()
    except ImportError:
        logger.debug("blu_observability_bootstrap not available")


def shutdown_langfuse() -> None:
    """Shutdown Langfuse client."""
    try:
        from blu_observability_bootstrap.langfuse import shutdown_langfuse as _shutdown

        _shutdown()
    except ImportError:
        logger.debug("blu_observability_bootstrap not available")
