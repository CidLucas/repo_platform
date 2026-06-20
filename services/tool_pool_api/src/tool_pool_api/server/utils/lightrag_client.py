"""
lightrag_client.py — Factory LightRAG client por client_id (singleton com cache) (T4.1b)

Provides:
  - get_client_rag(client_id: UUID | str) -> LightRAG
  - clear_client_rag_cache(client_id: str | None = None)
  - RAGClientError

Design decisions:
  DD-T41b-01: Singleton cache dict with TTL=3600s (1 hour)
  DD-T41b-02: PG storage backends pointing to Supabase Postgres via DATABASE_URL
  DD-T41b-03: working_dir isolated per client_id: ./rag_storage/client_{client_id}
  DD-T41b-04: Database connection params derived from DATABASE_URL (same as project)
  DD-T41b-05: LightRAG instance created lazily on first access per client_id
"""

from __future__ import annotations

import logging
import os
import time
from typing import TYPE_CHECKING
from urllib.parse import urlparse
from uuid import UUID

if TYPE_CHECKING:
    from lightrag import LightRAG

logger = logging.getLogger(__name__)

# =============================================================================
# RAGClientError
# =============================================================================


class RAGClientError(Exception):
    """Raised when LightRAG client initialization or connection fails."""

    pass


# =============================================================================
# Cache singleton
# =============================================================================

_RAG_CLIENTS: dict[str, tuple["LightRAG", float]] = {}
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
# Factory
# =============================================================================


async def get_client_rag(client_id: UUID | str) -> "LightRAG":
    """Get or create a cached LightRAG instance for the given client_id.

    The LightRAG instance is configured with Postgres storage backends
    (PGKVStorage, PGVectorStorage, PGGraphStorage, PGDocStatusStorage)
    pointing to the project's Supabase Postgres via DATABASE_URL.

    Each client has an isolated working_dir at:
        ./rag_storage/client_{client_id}

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


async def _create_lightrag_instance(client_id_str: str) -> "LightRAG":
    """Internal factory: instantiate LightRAG with PG storage backends.

    Uses lazy import to avoid errors when lightrag-hku is not installed
    (allows the module to be imported for type checking).
    """
    try:
        from lightrag import LightRAG
    except ImportError as exc:
        raise RAGClientError(
            f"lightrag-hku package is not installed: {exc}. "
            f"Install with: pip install lightrag-hku"
        ) from exc

    working_dir = f"./rag_storage/client_{client_id_str}"

    # Ensure working_dir exists
    os.makedirs(working_dir, exist_ok=True)

    logger.info(
        "Creating LightRAG instance for client_id=%s: "
        "kv=PGKVStorage vector=PGVectorStorage "
        "graph=PGGraphStorage doc_status=PGDocStatusStorage "
        "working_dir=%s",
        client_id_str,
        working_dir,
    )

    rag = LightRAG(
        working_dir=working_dir,
        kv_storage="PGKVStorage",
        vector_storage="PGVectorStorage",
        graph_storage="PGGraphStorage",
        doc_status_storage="PGDocStatusStorage",
    )

    # Ensure initialization completes
    await rag.initialize_storages()

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
