"""
Langfuse integration for LLM observability.

This module centralizes all Langfuse-related functionality:
- Callback handler for LangChain/LangGraph tracing
- Prompt management client with automatic version tagging
- Async flush/shutdown utilities

Usage:
    from vizu_observability_bootstrap.langfuse import (
        get_langfuse_callback,
        LangfusePromptClient,
        flush_langfuse_async,
    )
"""

from __future__ import annotations

import asyncio
import logging
import os
from functools import lru_cache
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from langchain_core.callbacks.base import BaseCallbackHandler
    from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

# Thread-local storage for prompt metadata (auto-injected into traces)
_prompt_metadata: dict[str, Any] = {}


def _get_prompt_metadata() -> dict[str, Any]:
    """Get current prompt metadata for trace injection."""
    return _prompt_metadata.copy()


def _set_prompt_metadata(name: str, version: int | str | None, label: str | None = None) -> None:
    """Set prompt metadata for automatic trace injection."""
    global _prompt_metadata
    _prompt_metadata = {
        "prompt_name": name,
        "prompt_version": version,
        "prompt_label": label,
    }


def _clear_prompt_metadata() -> None:
    """Clear prompt metadata after trace creation."""
    global _prompt_metadata
    _prompt_metadata = {}


# =============================================================================
# LANGFUSE SETTINGS
# =============================================================================


@lru_cache
def get_langfuse_settings() -> dict[str, Any]:
    """
    Get Langfuse configuration from environment.

    Environment variables:
    - LANGFUSE_HOST: Langfuse server URL (default: https://cloud.langfuse.com)
    - LANGFUSE_PUBLIC_KEY: Public API key (pk-lf-...)
    - LANGFUSE_SECRET_KEY: Secret API key (sk-lf-...)
    """
    return {
        "host": os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        "public_key": os.environ.get("LANGFUSE_PUBLIC_KEY"),
        "secret_key": os.environ.get("LANGFUSE_SECRET_KEY"),
    }


def is_langfuse_enabled() -> bool:
    """Check if Langfuse is properly configured."""
    settings = get_langfuse_settings()
    return bool(settings["public_key"] and settings["secret_key"])


# =============================================================================
# SANITIZATION HELPERS
# =============================================================================


def sanitize_observation(obj: dict, max_messages: int = 6) -> dict:
    """
    Return a sanitized shallow copy of an observation-like mapping.

    - Removes `_internal_context`.
    - Truncates `messages` to the last `max_messages` entries.
    - Trims `response_metadata` inside messages to small subset.
    """
    from collections.abc import Mapping

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


# =============================================================================
# CALLBACK HANDLER
# =============================================================================


class SanitizingLangfuseCallback:
    """
    Wrapper around Langfuse CallbackHandler that sanitizes observations.

    Behaviors:
    - Truncates `messages` lists to `max_messages` (default 6)
    - Removes `_internal_context` key entirely
    - Truncates large `response_metadata` objects to a small subset

    Note: This is a pure wrapper (not inheriting from BaseCallbackHandler)
    because we delegate all callback methods to the inner handler.
    LangChain accepts callback handlers via duck typing.
    """

    def __init__(self, inner: Any, max_messages: int = 6):
        self._inner = inner
        self._max_messages = max_messages
        # Expose required properties for LangChain duck typing
        self.ignore_agent = getattr(inner, "ignore_agent", False)
        self.ignore_chain = getattr(inner, "ignore_chain", False)
        self.ignore_llm = getattr(inner, "ignore_llm", False)
        self.ignore_retriever = getattr(inner, "ignore_retriever", False)
        self.ignore_retry = getattr(inner, "ignore_retry", False)
        self.raise_error = getattr(inner, "raise_error", False)

    def _sanitize_obj(self, obj: Any) -> Any:
        try:
            return sanitize_observation(obj, max_messages=self._max_messages)
        except Exception:
            return obj

    def _wrap_call(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        from collections.abc import Mapping

        new_args = []
        for a in args:
            if isinstance(a, Mapping):
                new_args.append(self._sanitize_obj(a))
            else:
                new_args.append(a)

        new_kwargs = {}
        for k, v in kwargs.items():
            if isinstance(v, Mapping):
                new_kwargs[k] = self._sanitize_obj(v)
            else:
                new_kwargs[k] = v

        return func(*new_args, **new_kwargs)

    def on_chain_start(self, serialized: Any, inputs: Any, **kwargs: Any) -> Any:
        try:
            return self._wrap_call(self._inner.on_chain_start, serialized, inputs, **kwargs)
        except Exception:
            return None

    def on_chain_end(self, outputs: Any, **kwargs: Any) -> Any:
        try:
            return self._wrap_call(self._inner.on_chain_end, outputs, **kwargs)
        except Exception:
            return None

    def on_llm_end(self, response: Any, **kwargs: Any) -> Any:
        try:
            return self._wrap_call(self._inner.on_llm_end, response, **kwargs)
        except Exception:
            return None

    def on_tool_end(self, output: Any, **kwargs: Any) -> Any:
        try:
            return self._wrap_call(self._inner.on_tool_end, output, **kwargs)
        except Exception:
            return None

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def get_langfuse_callback(
    user_id: str | None = None,
    session_id: str | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    max_messages: int = 6,
) -> BaseCallbackHandler | None:
    """
    Create a Langfuse CallbackHandler for LangChain/LangGraph tracing.

    Automatically injects prompt metadata (name, version) if a prompt was
    recently fetched via LangfusePromptClient.

    Args:
        user_id: User ID for trace grouping
        session_id: Session ID for trace grouping
        tags: Tags for categorization
        metadata: Additional metadata
        max_messages: Max messages to keep in observation (truncates older)

    Returns:
        Sanitizing callback handler or None if Langfuse not configured
    """
    if not is_langfuse_enabled():
        logger.debug("Langfuse not enabled (missing credentials)")
        return None

    try:
        # Import CallbackHandler - path differs between v2 and v3
        try:
            # v3: langfuse.langchain.CallbackHandler
            from langfuse.langchain import CallbackHandler
        except ImportError:
            # v2: langfuse.callback.CallbackHandler
            from langfuse.callback import CallbackHandler

        from langfuse import Langfuse

        settings = get_langfuse_settings()

        # Initialize Langfuse client (singleton)
        Langfuse(
            public_key=settings["public_key"],
            secret_key=settings["secret_key"],
            host=settings["host"],
        )

        # Create handler
        handler = CallbackHandler()

        # Merge prompt metadata with user metadata
        final_metadata = {**_get_prompt_metadata(), **(metadata or {})}
        if final_metadata:
            # SDK v3 doesn't accept metadata in constructor, set via trace
            handler.metadata = final_metadata

        if user_id:
            handler.user_id = user_id
        if session_id:
            handler.session_id = session_id
        if tags:
            handler.tags = tags

        # Clear prompt metadata after use
        _clear_prompt_metadata()

        # Return handler directly - Pydantic v2 validation requires proper BaseCallbackHandler inheritance
        # TODO: Implement sanitization via custom subclass that inherits from CallbackHandler
        logger.debug(f"Langfuse callback created - host: {settings['host']}")
        return handler

    except ImportError:
        logger.warning("langfuse not installed, tracing disabled")
        return None
    except Exception as e:
        logger.warning(f"Failed to create Langfuse callback: {e}")
        return None


# =============================================================================
# PROMPT CLIENT
# =============================================================================


class LangfusePromptClient:
    """
    Client for fetching prompts from Langfuse Prompt Management.

    Automatically tracks prompt name and version for trace metadata injection.

    Usage:
        client = LangfusePromptClient()
        prompt = client.get_prompt("system-prompt", label="production")
        # Now get_langfuse_callback() will auto-include prompt_name/version
    """

    def __init__(self):
        self._client: Any = None
        self._last_prompt_meta: dict[str, Any] = {}

    def _ensure_client(self) -> Any:
        """Lazily initialize Langfuse client."""
        if self._client is None:
            if not is_langfuse_enabled():
                raise RuntimeError("Langfuse not configured - missing credentials")

            from langfuse import Langfuse
            settings = get_langfuse_settings()
            self._client = Langfuse(
                public_key=settings["public_key"],
                secret_key=settings["secret_key"],
                host=settings["host"],
            )
        return self._client

    def get_prompt(
        self,
        name: str,
        version: int | None = None,
        label: str | None = None,
    ) -> ChatPromptTemplate:
        """
        Fetch a prompt from Langfuse and convert to LangChain format.

        Automatically sets prompt metadata for trace injection.

        Args:
            name: Prompt name in Langfuse
            version: Specific version number (optional)
            label: Label like "production" or "staging" (optional)

        Returns:
            ChatPromptTemplate ready for use with LangChain
        """
        client = self._ensure_client()

        # Fetch from Langfuse
        prompt = client.get_prompt(name, version=version, label=label)

        # Store metadata for auto-injection
        actual_version = getattr(prompt, "version", version)
        _set_prompt_metadata(name, actual_version, label)
        self._last_prompt_meta = {
            "prompt_name": name,
            "prompt_version": actual_version,
            "prompt_label": label,
        }

        logger.debug(f"Fetched prompt '{name}' v{actual_version} (label={label})")

        # Convert to LangChain format
        return prompt.get_langchain_prompt()

    def get_prompt_text(
        self,
        name: str,
        version: int | None = None,
        label: str | None = None,
    ) -> str:
        """
        Fetch a text prompt from Langfuse.

        Args:
            name: Prompt name in Langfuse
            version: Specific version number (optional)
            label: Label like "production" or "staging" (optional)

        Returns:
            Raw prompt text
        """
        client = self._ensure_client()
        prompt = client.get_prompt(name, version=version, label=label, type="text")

        actual_version = getattr(prompt, "version", version)
        _set_prompt_metadata(name, actual_version, label)
        self._last_prompt_meta = {
            "prompt_name": name,
            "prompt_version": actual_version,
            "prompt_label": label,
        }

        logger.debug(f"Fetched text prompt '{name}' v{actual_version}")
        return prompt.prompt

    def get_last_prompt_meta(self) -> dict[str, Any]:
        """Get metadata from the last fetched prompt."""
        return self._last_prompt_meta.copy()


# =============================================================================
# FLUSH & SHUTDOWN
# =============================================================================


def flush_langfuse() -> None:
    """Force flush Langfuse events (synchronous)."""
    if not is_langfuse_enabled():
        return

    try:
        from langfuse import get_client
        get_client().flush()
        logger.debug("Langfuse flush completed")
    except Exception as e:
        logger.warning(f"Langfuse flush failed: {e}")


async def flush_langfuse_async(timeout: float = 5.0) -> None:
    """
    Async flush of Langfuse events with timeout.

    Args:
        timeout: Maximum seconds to wait for flush
    """
    if not is_langfuse_enabled():
        return

    try:
        await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, flush_langfuse),
            timeout=timeout,
        )
    except TimeoutError:
        logger.warning(f"Langfuse flush timed out after {timeout}s")
    except Exception as e:
        logger.warning(f"Langfuse async flush failed: {e}")


def shutdown_langfuse() -> None:
    """Shutdown Langfuse client (synchronous)."""
    if not is_langfuse_enabled():
        return

    try:
        from langfuse import get_client
        get_client().shutdown()
        logger.debug("Langfuse shutdown completed")
    except Exception as e:
        logger.warning(f"Langfuse shutdown failed: {e}")


async def shutdown_langfuse_async(timeout: float = 5.0) -> None:
    """
    Async shutdown of Langfuse client with timeout.

    Args:
        timeout: Maximum seconds to wait for shutdown
    """
    if not is_langfuse_enabled():
        return

    try:
        await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, shutdown_langfuse),
            timeout=timeout,
        )
    except TimeoutError:
        logger.warning(f"Langfuse shutdown timed out after {timeout}s")
    except Exception as e:
        logger.warning(f"Langfuse async shutdown failed: {e}")


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "get_langfuse_callback",
    "is_langfuse_enabled",
    "get_langfuse_settings",
    "LangfusePromptClient",
    "flush_langfuse",
    "flush_langfuse_async",
    "shutdown_langfuse",
    "shutdown_langfuse_async",
    "sanitize_observation",
]
