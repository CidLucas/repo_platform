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
from typing import Any

from langchain_core.callbacks.base import BaseCallbackHandler

logger = logging.getLogger(__name__)


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


def sanitize_observation(obj: dict, max_messages: int = 6, max_str_len: int = 2000) -> dict:
    """
    Return a sanitized shallow copy of an observation-like mapping.

    - Removes `_internal_context`, `all_rows`, `vizu_context`.
    - Truncates `messages` to the last `max_messages` entries.
    - Trims `response_metadata` inside messages to small subset.
    - Truncates large string values to prevent trace bloat.
    """
    from collections.abc import Mapping

    if not isinstance(obj, Mapping):
        return obj

    o = dict(obj)

    # Remove keys that cause trace bloat
    for key in ("_internal_context", "all_rows", "vizu_context", "safe_context"):
        o.pop(key, None)

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

    # Truncate any large string values
    for key, value in list(o.items()):
        if isinstance(value, str) and len(value) > max_str_len:
            o[key] = value[:max_str_len] + f"... [truncated {len(value) - max_str_len} chars]"

    return o


# =============================================================================
# CALLBACK HANDLER
# =============================================================================


class SanitizingLangfuseCallback(BaseCallbackHandler):
    """
    Wrapper around Langfuse CallbackHandler that sanitizes observations.

    Behaviors:
    - Truncates `messages` lists to `max_messages` (default 6)
    - Removes `_internal_context` key entirely
    - Truncates large `response_metadata` objects to a small subset

    Inherits from BaseCallbackHandler to pass isinstance() checks
    in LangChain/Pydantic validation (required by ChatOllama and others).
    """

    def __init__(self, inner: Any, max_messages: int = 6):
        super().__init__()
        self._inner = inner
        self._max_messages = max_messages
        # Expose required properties from inner handler
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
        """Handle tool output - truncate large outputs and remove all_rows."""
        try:
            sanitized_output = self._sanitize_tool_output(output)
            return self._wrap_call(self._inner.on_tool_end, sanitized_output, **kwargs)
        except Exception:
            return None

    def _sanitize_tool_output(self, output: Any, max_len: int = 4000) -> Any:
        """Sanitize tool output to prevent trace bloat."""
        import json

        if output is None:
            return output

        # If it's a string, check if it's JSON and sanitize
        if isinstance(output, str):
            # Try to parse as JSON and remove all_rows
            try:
                data = json.loads(output)
                if isinstance(data, dict):
                    # Remove keys that cause bloat
                    for key in ("all_rows", "rows", "data", "raw_data"):
                        if key in data and isinstance(data[key], list) and len(data[key]) > 10:
                            data[key] = f"[{len(data[key])} rows omitted from trace]"
                    output = json.dumps(data)
            except (json.JSONDecodeError, TypeError):
                pass

            # Truncate if still too long
            if len(output) > max_len:
                return output[:max_len] + f"... [truncated {len(output) - max_len} chars]"
            return output

        # If it's a dict, sanitize directly
        if isinstance(output, dict):
            output = dict(output)
            for key in ("all_rows", "rows", "data", "raw_data"):
                if key in output and isinstance(output[key], list) and len(output[key]) > 10:
                    output[key] = f"[{len(output[key])} rows omitted from trace]"
            return output

        return output

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def get_langfuse_callback(
    user_id: str | None = None,
    session_id: str | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    max_messages: int = 6,
    trace_name: str | None = None,
) -> BaseCallbackHandler | None:
    """
    Create a Langfuse CallbackHandler for LangChain/LangGraph tracing.

    Args:
        user_id: User ID for trace grouping
        session_id: Session ID for trace grouping
        tags: Tags for categorization
        metadata: Additional metadata (including prompt_name, prompt_version for trace linking)
        max_messages: Max messages to keep in observation (truncates older)
        trace_name: Name for the trace (e.g., 'atendente_chat'). If None, trace will be unnamed.

    Returns:
        Callback handler wrapped with SanitizingLangfuseCallback, or None if Langfuse not configured
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

        # Create handler with trace_name if provided
        handler = CallbackHandler(trace_name=trace_name) if trace_name else CallbackHandler()

        # Set metadata if provided (prompt metadata for trace linking should be passed here)
        if metadata:
            handler.metadata = metadata

        if user_id:
            handler.user_id = user_id
        if session_id:
            handler.session_id = session_id
        if tags:
            handler.tags = tags

        # Wrap with SanitizingLangfuseCallback to strip internal contexts from traces
        sanitized_handler = SanitizingLangfuseCallback(handler, max_messages=max_messages)

        logger.debug(
            f"Langfuse callback created - host: {settings['host']}, trace_name: {trace_name}"
        )
        return sanitized_handler

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
    Thin wrapper around Langfuse SDK for prompt fetching + compiling.

    Simplified from the previous implementation:
    - Uses langfuse.get_prompt(name, label, cache_ttl_seconds) natively
    - Uses prompt.compile(**variables) for {{variable}} substitution
    - Returns both compiled text AND the prompt object (for trace linking)
    - Keeps circuit breaker logic (cooldown on connection failure)

    Usage:
        client = LangfusePromptClient()
        text, prompt_obj = client.get_and_compile(
            "atendente/default",
            {"nome_empresa": "Acme"},
            label="production"
        )
        # prompt_obj can be used for trace linking
    """

    # Circuit breaker: skip Langfuse for this many seconds after a failure
    _cooldown_until: float = 0.0
    _COOLDOWN_SECONDS: float = 300.0  # 5 minutes

    def __init__(self):
        self._client: Any = None

    def _ensure_client(self) -> Any:
        """Lazily initialize Langfuse client. Returns None if in cooldown."""
        import time

        if time.time() < self._cooldown_until:
            logger.debug("Langfuse client in cooldown period")
            return None

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

    def _trigger_cooldown(self) -> None:
        """Trigger circuit breaker cooldown after connection failure."""
        import time

        self._cooldown_until = time.time() + self._COOLDOWN_SECONDS
        logger.warning(f"Langfuse unreachable, disabling for {self._COOLDOWN_SECONDS}s")

    def get_and_compile(
        self,
        name: str,
        variables: dict[str, Any],
        label: str = "production",
        cache_ttl_seconds: int = 300,
    ) -> tuple[str, Any] | None:
        """
        Fetch prompt and compile with variables using Langfuse SDK natively.

        Args:
            name: Prompt name in Langfuse
            variables: Dict of variables for {{variable}} substitution
            label: Label like "production" or "staging"
            cache_ttl_seconds: TTL for Langfuse SDK's internal cache

        Returns:
            Tuple of (compiled_text, prompt_object) or None if failed
            The prompt_object can be used for trace linking via prompt.link()
        """
        try:
            client = self._ensure_client()
            if client is None:
                return None

            # Use Langfuse SDK natively - it handles caching internally
            prompt = client.get_prompt(
                name,
                label=label,
                cache_ttl_seconds=cache_ttl_seconds,
                type="text",
            )

            # Use prompt.compile() for {{variable}} substitution
            compiled = prompt.compile(**variables)

            actual_version = getattr(prompt, "version", None)
            logger.debug(f"Fetched and compiled prompt '{name}' v{actual_version} (label={label})")

            return compiled, prompt

        except Exception as e:
            error_str = str(e).lower()
            if (
                "connection refused" in error_str
                or "connection" in error_str
                or "timeout" in error_str
            ):
                self._trigger_cooldown()
            logger.warning(f"Langfuse prompt '{name}' fetch failed (label={label}): {e}")
            return None

    def get_prompt_template(
        self,
        name: str,
        label: str = "production",
        cache_ttl_seconds: int = 300,
    ) -> tuple[str, Any] | None:
        """
        Fetch raw prompt template (without variable substitution).

        Useful when you need to cache the raw template separately
        and apply variables later.

        Args:
            name: Prompt name in Langfuse
            label: Label like "production" or "staging"
            cache_ttl_seconds: TTL for Langfuse SDK's internal cache

        Returns:
            Tuple of (raw_template_text, prompt_object) or None if failed
        """
        try:
            client = self._ensure_client()
            if client is None:
                return None

            prompt = client.get_prompt(
                name,
                label=label,
                cache_ttl_seconds=cache_ttl_seconds,
                type="text",
            )

            # Return raw template without compilation
            raw_text = prompt.prompt

            actual_version = getattr(prompt, "version", None)
            logger.debug(f"Fetched raw template '{name}' v{actual_version} (label={label})")

            return raw_text, prompt

        except Exception as e:
            error_str = str(e).lower()
            if (
                "connection refused" in error_str
                or "connection" in error_str
                or "timeout" in error_str
            ):
                self._trigger_cooldown()
            logger.warning(f"Langfuse template '{name}' fetch failed (label={label}): {e}")
            return None

    def is_available(self) -> bool:
        """Check if Langfuse is enabled and not in cooldown."""
        import time

        if time.time() < self._cooldown_until:
            return False
        return is_langfuse_enabled()


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
