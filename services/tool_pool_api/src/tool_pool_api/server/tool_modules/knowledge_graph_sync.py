"""knowledge_graph_sync.py — Internal tool for syncing Knowledge Graph summary.

Este módulo é chamado pelo job semanal de enriquecimento SBM→LightRAG
(T4.1) como step final após sincronizar o grafo.  Ele atualiza o campo
``knowledge_graph_summary`` dentro de ``clientes_blu.available_tools``
(JSONB) e invalida o cache de contexto para que a próxima chamada a
``get_client_context()`` retorne os dados atualizados.

It is **NOT** exposed as an MCP tool — it is used via direct function call.

.. note::

    T4.1 ainda não foi implementado.  Este módulo é preparatório — a
    interface está pronta para consumo quando o job de enriquecimento
    existir.  O exemplo abaixo mostra o contrato esperado.

Payload example — T4.1 enrichment job should call this module as follows::

    from datetime import datetime, UTC
    from uuid import UUID

    from tool_pool_api.server.tool_modules.knowledge_graph_sync import (
        update_knowledge_graph_summary,
    )

    # Inside the T4.1 enrichment job, after the SBM→LightRAG sync:
    summary = {
        "total_documents": rag.get_documents_count(),
        "total_entities": rag.get_entities_count(),
        "top_entities": rag.get_top_entities_by_degree(10),
        "last_sync": datetime.now(UTC).isoformat(),
        "version": 1,
    }

    ok = await update_knowledge_graph_summary(
        client_id=UUID("..."),    # ID do cliente Blu
        summary=summary,
    )

Schema (KnowledgeGraphSummary / DD-04 required keys)::

    {
        "total_documents":  int,           # >= 0
        "total_entities":   int,           # >= 0
        "top_entities":     list[dict],    # [{"name": str, "type": str, "degree": int}, ...]
        "last_sync":        str | None,    # ISO 8601 (UTC)
        "version":          int,           # >= 1, monotonic
    }
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from blu_supabase_client import get_supabase_client

from tool_pool_api.server.dependencies import get_context_service

logger = logging.getLogger(__name__)

# Required keys in the summary dict (DD-04).
_REQUIRED_KEYS: frozenset[str] = frozenset({
    "total_documents",
    "total_entities",
    "top_entities",
    "last_sync",
    "version",
})


def _validate_summary(summary: dict[str, Any]) -> None:
    """Validate the summary dict against the KnowledgeGraphSummary schema.

    Raises:
        ValueError: If required keys are missing or have invalid types.
    """
    if not isinstance(summary, dict):
        raise ValueError("summary must be a dict")

    missing = _REQUIRED_KEYS - set(summary.keys())
    if missing:
        raise ValueError(
            f"summary missing required keys: {sorted(missing)}"
        )

    # Validate types
    total_docs = summary.get("total_documents")
    if not isinstance(total_docs, int) or total_docs < 0:
        raise ValueError(
            f"total_documents must be a non-negative int, "
            f"got {type(total_docs).__name__}"
        )

    total_ent = summary.get("total_entities")
    if not isinstance(total_ent, int) or total_ent < 0:
        raise ValueError(
            f"total_entities must be a non-negative int, "
            f"got {type(total_ent).__name__}"
        )

    top_entities = summary.get("top_entities")
    if not isinstance(top_entities, list):
        raise ValueError(
            f"top_entities must be a list, got {type(top_entities).__name__}"
        )
    for i, entity in enumerate(top_entities):
        if not isinstance(entity, dict):
            raise ValueError(
                f"top_entities[{i}] must be a dict, "
                f"got {type(entity).__name__}"
            )
        if (
            "name" not in entity
            or "type" not in entity
            or "degree" not in entity
        ):
            raise ValueError(
                f"top_entities[{i}] missing required fields: "
                f"name={'name' in entity}, type={'type' in entity}, "
                f"degree={'degree' in entity}"
            )

    last_sync = summary.get("last_sync")
    if last_sync is not None and not isinstance(last_sync, str):
        raise ValueError(
            f"last_sync must be a str or None, "
            f"got {type(last_sync).__name__}"
        )

    version = summary.get("version")
    if not isinstance(version, int) or version < 1:
        raise ValueError(
            f"version must be a positive int, got {type(version).__name__}"
        )


async def update_knowledge_graph_summary(
    client_id: UUID,
    summary: dict[str, Any],
) -> bool:
    """Update the knowledge_graph_summary inside available_tools for a client.

    Reads the current ``available_tools`` JSONB from ``clientes_blu``,
    merges the new summary (preserving fields like ``tier``,
    ``enabled_tool_names``, etc.), upserts via Supabase, and invalidates
    the Redis context cache so the next read is fresh.

    Args:
        client_id: The Blu client UUID.
        summary: A dict with keys matching
            ``KnowledgeGraphSummary`` (see module docstring for example).

    Returns:
        ``True`` on success, ``False`` on failure (Supabase error, missing
        client, or validation error).

    Raises:
        ValueError: If ``summary`` fails validation.
    """
    # ── validate ────────────────────────────────────────────────────────
    _validate_summary(summary)

    db = get_supabase_client()

    # ── read current available_tools ────────────────────────────────────
    try:
        response = (
            await db.table("clientes_blu")
            .select("available_tools")
            .eq("client_id", str(client_id))
            .maybe_single()
            .execute()
        )
    except Exception as exc:
        logger.error(
            "[knowledge_graph_sync] Failed to read client %s: %s",
            client_id, exc,
        )
        return False

    if response.data is None:
        logger.warning(
            "[knowledge_graph_sync] Client not found: %s", client_id
        )
        return False

    # ── merge ───────────────────────────────────────────────────────────
    available_tools: dict[str, Any] = response.data.get("available_tools") or {}

    # Preserve all existing fields — only replace knowledge_graph_summary.
    available_tools["knowledge_graph_summary"] = summary

    # ── update Supabase ─────────────────────────────────────────────────
    try:
        update_response = (
            await db.table("clientes_blu")
            .update({"available_tools": available_tools})
            .eq("client_id", str(client_id))
            .execute()
        )
    except Exception as exc:
        logger.error(
            "[knowledge_graph_sync] Failed to update client %s: %s",
            client_id, exc,
        )
        return False

    if not update_response.data:
        logger.error(
            "[knowledge_graph_sync] update returned no data for %s",
            client_id,
        )
        return False

    # ── invalidate cache ────────────────────────────────────────────────
    try:
        ctx_service = get_context_service()
        await ctx_service.clear_context_cache(client_id)
    except Exception as exc:
        logger.warning(
            "[knowledge_graph_sync] Cache invalidation failed for %s: %s",
            client_id, exc,
        )
        # Non-fatal — cache will expire on its own (TTL 5 min).

    # ── structured log ──────────────────────────────────────────────────
    logger.info(
        "knowledge_graph_summary updated: client=%s, entities=%d, docs=%d, sync=%s",
        client_id,
        summary.get("total_entities", 0),
        summary.get("total_documents", 0),
        summary.get("last_sync"),
    )

    return True
