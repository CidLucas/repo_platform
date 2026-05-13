"""Langfuse config helper for LangGraph invocation."""

from __future__ import annotations

import logging
import uuid

logger = logging.getLogger(__name__)


def get_langfuse_config(
    session_id: str,
    cliente_id: str,
    tags: list[str] | None = None,
) -> dict:
    """
    Return a LangGraph config dict wired up with the centralized Langfuse callback.

    Uses blu_llm_service.get_langfuse_callback() so the sanitizing wrapper from
    blu_observability_bootstrap is always applied. Falls back to a plain
    thread_id config if Langfuse is not configured.
    """
    try:
        from blu_llm_service import get_langfuse_callback

        handler = get_langfuse_callback()
        if handler is None:
            raise RuntimeError("Langfuse not configured")

        trace_id = str(uuid.uuid4())
        return {
            "configurable": {"thread_id": session_id},
            "callbacks": [handler],
            "metadata": {
                "trace_id": trace_id,
                "cliente_id": cliente_id,
                "session_id": session_id,
                "tags": tags or [],
            },
        }
    except Exception as exc:
        logger.debug("Langfuse not available: %s", exc)
        return {"configurable": {"thread_id": session_id}}
