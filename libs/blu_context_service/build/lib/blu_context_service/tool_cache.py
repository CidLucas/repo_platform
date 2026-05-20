"""
Tool result caching for LangGraph agents.

Stores tool outputs in Redis for:
- Preventing context bloat (store reference, not full data)
- Session-scoped caching (auto-expires with session)
- Deduplication of expensive tool calls
- Debugging and observability

Key structure: tool:{session_id}:{tool_name}:{args_hash}
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    import redis

logger = logging.getLogger(__name__)

# Default TTL: 1 hour (session max lifetime)
DEFAULT_TTL_SECONDS = 3600
MAX_SUMMARY_LENGTH = 500  # Characters for the summary stored in message


class ToolResultCache:
    """
    Cache tool results in Redis with session-scoped TTL.

    Key structure: tool:{session_id}:{tool_name}:{args_hash}

    Usage:
        cache = ToolResultCache(redis_client)

        # Store tool result
        ref_id = cache.store(
            session_id="sess-123",
            tool_name="executar_sql_agent",
            args={"query": "top customers"},
            result={"output": "...", "all_rows": [...]},
            ttl=3600,
        )

        # Get reference for message (small)
        summary = cache.get_summary(ref_id)
        # Returns: "Query returned 592 rows. Top result: NOVELIS..."

        # Retrieve full result when needed
        full_result = cache.get(ref_id)
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        key_prefix: str = "tool",
        default_ttl: int = DEFAULT_TTL_SECONDS,
    ):
        self.client = redis_client
        self.key_prefix = key_prefix
        self.default_ttl = default_ttl

    def _make_key(
        self,
        session_id: str,
        tool_name: str,
        args: dict[str, Any],
    ) -> str:
        """Generate cache key from tool call parameters."""
        # Sort args for consistent hashing
        args_str = json.dumps(args, sort_keys=True, default=str)
        args_hash = hashlib.md5(args_str.encode()).hexdigest()[:12]
        return f"{self.key_prefix}:{session_id}:{tool_name}:{args_hash}"

    def _make_ref_id(self, key: str) -> str:
        """Generate a short reference ID from the full key."""
        # Use last part of key (hash) as ref_id
        return key.split(":")[-1]

    def store(
        self,
        session_id: str,
        tool_name: str,
        args: dict[str, Any],
        result: Any,
        ttl: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Cache tool result and return reference ID.

        Args:
            session_id: Session/conversation ID
            tool_name: Name of the tool
            args: Tool input arguments
            result: Tool output to cache (full data)
            ttl: TTL in seconds (uses default if None)
            metadata: Optional metadata (timing, trace_id, etc.)

        Returns:
            Reference ID to retrieve the result later
        """
        key = self._make_key(session_id, tool_name, args)
        ref_id = self._make_ref_id(key)

        # Generate summary for message content
        summary = self._generate_summary(tool_name, result)

        cache_entry = {
            "ref_id": ref_id,
            "result": result,
            "summary": summary,
            "tool_name": tool_name,
            "args": args,
            "session_id": session_id,
            "cached_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }

        try:
            self.client.setex(
                name=key,
                time=ttl or self.default_ttl,
                value=json.dumps(cache_entry, default=str),
            )
            logger.info(f"Tool cache STORE: {tool_name} -> ref:{ref_id}")
            return ref_id
        except Exception as e:
            logger.warning(f"Tool cache store error: {e}")
            # Return a fallback ref_id even on error
            return ref_id

    def get(self, ref_id: str, session_id: str | None = None) -> dict[str, Any] | None:
        """
        Retrieve full cached result by reference ID.

        Args:
            ref_id: Reference ID from store()
            session_id: Optional session_id to narrow search

        Returns:
            Full cached result dict or None if not found/expired
        """
        # If session_id provided, we can construct exact key pattern
        if session_id:
            pattern = f"{self.key_prefix}:{session_id}:*:{ref_id}"
        else:
            pattern = f"{self.key_prefix}:*:*:{ref_id}"

        try:
            for key in self.client.scan_iter(match=pattern, count=100):
                data = self.client.get(key)
                if data:
                    entry = json.loads(data)
                    if entry.get("ref_id") == ref_id:
                        logger.debug(f"Tool cache GET: ref:{ref_id}")
                        return entry.get("result")

            logger.debug(f"Tool cache MISS: ref:{ref_id}")
            return None
        except Exception as e:
            logger.warning(f"Tool cache get error: {e}")
            return None

    def get_summary(self, ref_id: str, session_id: str | None = None) -> str | None:
        """
        Get just the summary for a cached result.

        Useful for constructing ToolMessage content without full data.
        """
        if session_id:
            pattern = f"{self.key_prefix}:{session_id}:*:{ref_id}"
        else:
            pattern = f"{self.key_prefix}:*:*:{ref_id}"

        try:
            for key in self.client.scan_iter(match=pattern, count=100):
                data = self.client.get(key)
                if data:
                    entry = json.loads(data)
                    if entry.get("ref_id") == ref_id:
                        return entry.get("summary")
            return None
        except Exception as e:
            logger.warning(f"Tool cache get_summary error: {e}")
            return None

    def get_by_args(
        self,
        session_id: str,
        tool_name: str,
        args: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Check if we have a cached result for these exact args.

        Useful for deduplication before executing expensive tools.
        """
        key = self._make_key(session_id, tool_name, args)
        try:
            data = self.client.get(key)
            if data:
                entry = json.loads(data)
                logger.debug(f"Tool cache HIT by args: {tool_name}")
                return entry.get("result")
            logger.debug(f"Tool cache MISS by args: {tool_name}")
            return None
        except Exception as e:
            logger.warning(f"Tool cache get_by_args error: {e}")
            return None

    def invalidate_session(self, session_id: str) -> int:
        """
        Invalidate all cached results for a session.

        Call this when a session ends to free memory.

        Returns:
            Number of keys deleted
        """
        pattern = f"{self.key_prefix}:{session_id}:*"
        try:
            keys = list(self.client.scan_iter(match=pattern))
            if keys:
                count = self.client.delete(*keys)
                logger.info(f"Tool cache invalidated {count} keys for session {session_id}")
                return count
            return 0
        except Exception as e:
            logger.warning(f"Tool cache invalidate error: {e}")
            return 0

    def list_session_tools(self, session_id: str) -> list[dict[str, Any]]:
        """
        List all cached tool results for a session (for debugging).
        """
        pattern = f"{self.key_prefix}:{session_id}:*"
        results = []

        try:
            for key in self.client.scan_iter(match=pattern):
                data = self.client.get(key)
                if data:
                    entry = json.loads(data)
                    # Return summary info, not full result
                    results.append(
                        {
                            "ref_id": entry.get("ref_id"),
                            "tool_name": entry.get("tool_name"),
                            "summary": entry.get("summary"),
                            "cached_at": entry.get("cached_at"),
                        }
                    )
            return results
        except Exception as e:
            logger.warning(f"Tool cache list error: {e}")
            return []

    def _generate_summary(self, tool_name: str, result: Any) -> str:
        """
        Generate a short summary of the tool result for message content.

        This summary is what goes into ToolMessage.content instead of full data.
        """
        try:
            if isinstance(result, dict):
                # SQL tool specific summary
                if tool_name == "executar_sql_agent":
                    return self._summarize_sql_result(result)

                # RAG tool specific summary
                if tool_name == "executar_rag_cliente":
                    return self._summarize_rag_result(result)

                # Generic dict summary
                output = result.get("output", result.get("result", str(result)))
                if isinstance(output, str):
                    return output[:MAX_SUMMARY_LENGTH] + (
                        "..." if len(output) > MAX_SUMMARY_LENGTH else ""
                    )
                return str(output)[:MAX_SUMMARY_LENGTH]

            # String result
            if isinstance(result, str):
                return result[:MAX_SUMMARY_LENGTH] + (
                    "..." if len(result) > MAX_SUMMARY_LENGTH else ""
                )

            # List result
            if isinstance(result, list):
                return (
                    f"List with {len(result)} items. First: {str(result[0])[:100]}..."
                    if result
                    else "Empty list"
                )

            return str(result)[:MAX_SUMMARY_LENGTH]

        except Exception as e:
            logger.warning(f"Error generating summary: {e}")
            return f"Tool {tool_name} executed successfully"

    def _summarize_sql_result(self, result: dict) -> str:
        """Generate summary for SQL tool results."""
        output = result.get("output", "")
        all_rows = result.get("all_rows", [])
        sql = result.get("sql", "")

        row_count = len(all_rows) if all_rows else "unknown"

        # Extract preview from output
        preview = str(output)[:300] if output else ""

        return f"SQL query returned {row_count} rows.\n\nPreview:\n{preview}"

    def _summarize_rag_result(self, result: dict) -> str:
        """Generate summary for RAG tool results."""
        if isinstance(result, str):
            return result[:MAX_SUMMARY_LENGTH]

        output = result.get("output", result.get("result", str(result)))
        return str(output)[:MAX_SUMMARY_LENGTH]


# =============================================================================
# FACTORY FUNCTION
# =============================================================================


_tool_cache_instance: ToolResultCache | None = None


def get_tool_cache(redis_url: str | None = None) -> ToolResultCache:
    """
    Get singleton ToolResultCache instance.

    Args:
        redis_url: Redis URL (defaults to REDIS_URL env var)

    Returns:
        ToolResultCache instance
    """
    global _tool_cache_instance

    if _tool_cache_instance is None:
        import redis

        url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        client = redis.from_url(url)
        _tool_cache_instance = ToolResultCache(client)
        logger.info(f"ToolResultCache initialized with Redis: {url}")

    return _tool_cache_instance
