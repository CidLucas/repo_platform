"""
Langfuse Observability Integration for LangGraph.

This module provides a thin wrapper around vizu_llm_service's Langfuse functions,
adding LangGraph-specific configuration (thread_id for memory).

All Langfuse initialization and callback handling is delegated to vizu_llm_service
to avoid code duplication.
"""

import logging
from typing import Any

from vizu_llm_service import (
    flush_langfuse,
    get_llm_settings,
    shutdown_langfuse,
)
from vizu_llm_service import (
    get_langfuse_callback as _get_langfuse_callback,
)

logger = logging.getLogger(__name__)


def is_langfuse_enabled() -> bool:
    """Check if Langfuse is available and configured."""
    settings = get_llm_settings()
    return settings.langfuse_enabled


def get_langfuse_callback() -> Any | None:
    """
    Get a Langfuse CallbackHandler for LangChain/LangGraph.

    Delegates to vizu_llm_service.get_langfuse_callback().
    """
    return _get_langfuse_callback()


def get_langfuse_config(
    session_id: str | None = None,
    user_id: str | None = None,
    cliente_id: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """
    Get a LangChain/LangGraph config dict with Langfuse callback.

    This function builds the config dict with:
    - thread_id for LangGraph memory (checkpointing)
    - Langfuse callback for tracing
    - Metadata with Langfuse-specific keys

    Args:
        session_id: Session ID for trace grouping and thread memory
        user_id: User ID for attribution
        cliente_id: Vizu client ID for multi-tenant filtering
        tags: Optional tags for filtering

    Returns:
        Config dict ready to pass to graph.invoke() or graph.ainvoke()
    """
    config: dict[str, Any] = {
        "configurable": {
            "thread_id": session_id or "default",
        }
    }

    # Use cliente_id as user_id if not provided
    effective_user_id = user_id or cliente_id

    # Build metadata with Langfuse special keys (SDK v3)
    trace_metadata = {
        "langfuse_session_id": session_id,
        "langfuse_user_id": effective_user_id,
        "langfuse_tags": tags or ["atendente"],
        "cliente_id": cliente_id,
    }

    callback = get_langfuse_callback()

    if callback:
        config["callbacks"] = [callback]
        config["metadata"] = trace_metadata
        logger.debug(
            f"Langfuse config created for session={session_id}, cliente={cliente_id}"
        )

    return config


# Re-export for convenience
__all__ = [
    "is_langfuse_enabled",
    "get_langfuse_callback",
    "get_langfuse_config",
    "flush_langfuse",
    "shutdown_langfuse",
]
