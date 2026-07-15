"""
lightrag_client.py — Factory LightRAG client por client_id (singleton com cache)

Provides:
  - get_client_rag(client_id: UUID | str) -> LightRAG
  - clear_client_rag_cache(client_id: str | None = None)
  - RAGClientError

Design decisions:
  DD-T41b-01: Singleton cache dict with TTL=3600s (1 hour)
  DD-T41b-02: PG storage backends pointing to Supabase Postgres via DATABASE_URL
  DD-T41b-03: Tenant isolation via LightRAG ``workspace="client_{client_id}"`` —
              the PG storages (PGKVStorage/PGVectorStorage/PGGraphStorage/
              PGDocStatusStorage) discriminate every row by workspace. O
              working_dir é apenas cache local efêmero (ok no Cloud Run).
  DD-T41b-04: Database connection params derived from DATABASE_URL (same as project)
  DD-T41b-05: LightRAG instance created lazily on first access per client_id
  DD-T41b-06: embedding_func = Cohere embed-multilingual-light-v3.0 (384 dims),
              o MESMO modelo do pgvector RAG (search_documents) — dimensões devem
              bater com o schema das tabelas LIGHTRAG_* criadas na inicialização.
  DD-T41b-07: llm_model_func = blu_llm_service FAST tier (extração de keywords
              nas queries e sumarização; ainsert_custom_kg não usa LLM).
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse
from uuid import UUID

if TYPE_CHECKING:
    from lightrag import LightRAG

logger = logging.getLogger(__name__)

# Mesmo modelo/dimensão do pgvector RAG (services/search_documents).
EMBEDDING_DIMENSIONS = 384

# =============================================================================
# RAGClientError
# =============================================================================


class RAGClientError(Exception):
    """Raised when LightRAG client initialization or connection fails."""

    pass


# =============================================================================
# Cache singleton
# =============================================================================

_RAG_CLIENTS: dict[str, tuple[LightRAG, float]] = {}
"""Global cache: client_id_str -> (LightRAG instance, creation_timestamp)."""

_RAG_CLIENTS_TTL: float = 3600.0
"""TTL in seconds — 1 hour. After expiry the instance is recreated."""

# =============================================================================
# Postgres env vars from DATABASE_URL
# =============================================================================

_postgres_env_set: bool = False


def _ensure_postgres_env_from_database_url() -> None:
    """Set POSTGRES_* env vars from DATABASE_URL if not already present.

    LightRAG's PGKVStorage/PGVectorStorage/PGGraphStorage/PGDocStatusStorage
    read POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD,
    POSTGRES_DATABASE from the environment.

    We derive them from the project's DATABASE_URL (same Supabase Postgres).
    """
    global _postgres_env_set

    if _postgres_env_set:
        return

    # Check if POSTGRES_* already set explicitly
    if all(
        os.getenv(v) for v in ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DATABASE")
    ):
        _postgres_env_set = True
        logger.debug("POSTGRES_* env vars already set — using existing values")
        return

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RAGClientError(
            "DATABASE_URL environment variable is not set. "
            "Cannot configure LightRAG Postgres storage backends."
        )

    parsed = urlparse(database_url)

    if not os.getenv("POSTGRES_HOST"):
        os.environ["POSTGRES_HOST"] = parsed.hostname or "localhost"
    if not os.getenv("POSTGRES_PORT"):
        os.environ["POSTGRES_PORT"] = str(parsed.port or 5432)
    if not os.getenv("POSTGRES_USER"):
        os.environ["POSTGRES_USER"] = parsed.username or "postgres"
    if not os.getenv("POSTGRES_PASSWORD"):
        os.environ["POSTGRES_PASSWORD"] = parsed.password or ""
    if not os.getenv("POSTGRES_DATABASE"):
        db_name = parsed.path.lstrip("/") or "postgres"
        os.environ["POSTGRES_DATABASE"] = db_name

    _postgres_env_set = True
    logger.info(
        "Postgres env vars derived from DATABASE_URL: "
        "host=%s port=%s user=%s database=%s",
        os.environ["POSTGRES_HOST"],
        os.environ["POSTGRES_PORT"],
        os.environ["POSTGRES_USER"],
        os.environ["POSTGRES_DATABASE"],
    )


# =============================================================================
# Embedding + LLM plumbing (DD-T41b-06 / DD-T41b-07)
# =============================================================================


async def _embed_texts(texts: list[str]) -> Any:
    """Async embedding func no formato que o LightRAG espera.

    Usa o mesmo Cohere embed-multilingual-light-v3.0 (384 dims) do pgvector
    RAG, via blu_llm_service. O embedder LangChain é sync → to_thread.
    """
    import numpy as np

    from blu_llm_service import get_cohere_embedding_model

    embedder = get_cohere_embedding_model()
    vectors = await asyncio.to_thread(embedder.embed_documents, list(texts))
    return np.array(vectors, dtype=np.float32)


async def _llm_complete(
    prompt: str,
    system_prompt: str | None = None,
    history_messages: list | None = None,
    **kwargs: Any,
) -> str:
    """LLM completion func no contrato do LightRAG (usada em queries).

    Encaminha para o blu_llm_service (FAST tier, task GENERAL_AGENT — o task
    RAG mapeia para HuggingFace Inference, que não está disponível em todos os
    ambientes; extração de keywords é tarefa genérica). kwargs extras do
    LightRAG (keyword_extraction, hashing_kv, ...) são ignorados.
    """
    from blu_llm_service.client import ModelTask, ModelTier, get_model

    model = get_model(tier=ModelTier.FAST, task=ModelTask.GENERAL_AGENT)

    messages: list[tuple[str, str]] = []
    if system_prompt:
        messages.append(("system", system_prompt))
    for msg in history_messages or []:
        role = msg.get("role", "user") if isinstance(msg, dict) else "user"
        content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
        messages.append((role if role in ("system", "user", "assistant") else "user", content))
    messages.append(("user", prompt))

    response = await model.ainvoke(messages)
    return response.content if hasattr(response, "content") else str(response)


# =============================================================================
# Factory
# =============================================================================


async def get_client_rag(client_id: UUID | str) -> LightRAG:
    """Get or create a cached LightRAG instance for the given client_id.

    The LightRAG instance is configured with Postgres storage backends
    (PGKVStorage, PGVectorStorage, PGGraphStorage, PGDocStatusStorage)
    pointing to the project's Supabase Postgres via DATABASE_URL.

    Tenant isolation: ``workspace="client_{client_id}"`` — every PG row is
    discriminated by workspace (DD-T41b-03).

    Args:
        client_id: The client UUID or string identifier.

    Returns:
        Configured LightRAG instance.

    Raises:
        RAGClientError: If DATABASE_URL is not set or LightRAG init fails.
    """
    client_id_str = str(client_id)

    # 1. Check cache
    now = time.time()
    cached = _RAG_CLIENTS.get(client_id_str)
    if cached is not None:
        instance, created_at = cached
        if (now - created_at) < _RAG_CLIENTS_TTL:
            logger.debug(
                "LightRAG client cache HIT for client_id=%s "
                "(age=%.0fs, ttl=%.0fs)",
                client_id_str,
                now - created_at,
                _RAG_CLIENTS_TTL,
            )
            return instance

        # Expired — remove from cache
        logger.info(
            "LightRAG client cache EXPIRED for client_id=%s "
            "(age=%.0fs > ttl=%.0fs) — recreating",
            client_id_str,
            now - created_at,
            _RAG_CLIENTS_TTL,
        )
        del _RAG_CLIENTS[client_id_str]

    # 2. Ensure Postgres env vars
    try:
        _ensure_postgres_env_from_database_url()
    except RAGClientError:
        raise
    except Exception as exc:
        raise RAGClientError(
            f"Failed to configure Postgres env vars for LightRAG: {exc}"
        ) from exc

    # 3. Create LightRAG instance with PG backends
    try:
        instance = await _create_lightrag_instance(client_id_str)
    except Exception as exc:
        raise RAGClientError(
            f"Failed to initialize LightRAG for client_id={client_id_str}: {exc}"
        ) from exc

    # 4. Store in cache
    _RAG_CLIENTS[client_id_str] = (instance, now)
    logger.info(
        "LightRAG client created and cached for client_id=%s (ttl=%.0fs)",
        client_id_str,
        _RAG_CLIENTS_TTL,
    )

    return instance


async def _create_lightrag_instance(client_id_str: str) -> LightRAG:
    """Internal factory: instantiate LightRAG with PG storage backends.

    Uses lazy import to avoid errors when lightrag-hku is not installed
    (allows the module to be imported for type checking).
    """
    try:
        from lightrag import LightRAG
        from lightrag.utils import EmbeddingFunc
    except ImportError as exc:
        raise RAGClientError(
            f"lightrag-hku package is not installed: {exc}. "
            f"Install with: pip install lightrag-hku"
        ) from exc

    # Cache local efêmero — os dados persistentes vivem no Postgres.
    base_dir = os.getenv("LIGHTRAG_WORKING_DIR", "/tmp/lightrag")
    working_dir = os.path.join(base_dir, f"client_{client_id_str}")
    os.makedirs(working_dir, exist_ok=True)

    workspace = f"client_{client_id_str}"

    logger.info(
        "Creating LightRAG instance for client_id=%s: "
        "workspace=%s kv=PGKVStorage vector=PGVectorStorage "
        "graph=NetworkXStorage doc_status=PGDocStatusStorage "
        "working_dir=%s embedding=cohere-384",
        client_id_str,
        workspace,
        working_dir,
    )

    rag = LightRAG(
        working_dir=working_dir,
        workspace=workspace,
        kv_storage="PGKVStorage",
        vector_storage="PGVectorStorage",
        # PGGraphStorage exige Apache AGE (ag_catalog/cypher), que o Postgres
        # do Supabase NÃO suporta. Grafo fica em NetworkX (working_dir); sem
        # perda prática em T4.1 (relationships=[] — retrieval vem dos vetores
        # de entidades/chunks no PG). Revisitar quando houver relations.
        graph_storage="NetworkXStorage",
        doc_status_storage="PGDocStatusStorage",
        embedding_func=EmbeddingFunc(
            embedding_dim=EMBEDDING_DIMENSIONS,
            func=_embed_texts,
        ),
        llm_model_func=_llm_complete,
    )

    # Ensure initialization completes
    await rag.initialize_storages()

    # Pipeline status é usado pelos fluxos de ingest do LightRAG; idempotente.
    try:
        from lightrag.kg.shared_storage import initialize_pipeline_status

        await initialize_pipeline_status()
    except Exception:
        logger.debug("initialize_pipeline_status indisponível — seguindo sem ele")

    return rag


# =============================================================================
# Cache management
# =============================================================================


def clear_client_rag_cache(client_id: str | None = None) -> None:
    """Clear cached LightRAG instance(s).

    Args:
        client_id: If provided, remove only that client's cached instance.
                   If None (default), clear the entire cache.

    """
    if client_id is not None:
        removed = _RAG_CLIENTS.pop(str(client_id), None)
        if removed:
            logger.info(
                "LightRAG client cache cleared for client_id=%s", client_id
            )
        else:
            logger.debug(
                "LightRAG client cache — no entry for client_id=%s", client_id
            )
    else:
        count = len(_RAG_CLIENTS)
        _RAG_CLIENTS.clear()
        logger.info(
            "LightRAG client cache cleared (removed %d entries)", count
        )
