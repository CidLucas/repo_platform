"""
Redis-backed storage for pending elicitations.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from vizu_elicitation_service.exceptions import ElicitationNotFoundError
from vizu_elicitation_service.models import PendingElicitation

logger = logging.getLogger(__name__)


class PendingElicitationStore:
    """
    Store and retrieve pending elicitations in Redis.

    Uses Redis hash for efficient storage with automatic TTL.
    """

    def __init__(
        self,
        redis_client: Any,
        ttl_seconds: int = 3600,
        key_prefix: str = "vizu:elicitation:",
    ):
        """
        Initialize store.

        Args:
            redis_client: Redis client instance
            ttl_seconds: Time-to-live for pending elicitations (default 1 hour)
            key_prefix: Prefix for Redis keys
        """
        self.redis = redis_client
        self.ttl_seconds = ttl_seconds
        self.key_prefix = key_prefix

    def _make_key(self, session_id: str) -> str:
        """Generate Redis key for session."""
        return f"{self.key_prefix}{session_id}"

    async def save(
        self,
        session_id: str,
        elicitation: PendingElicitation,
        ttl_seconds: int | None = None,
    ) -> None:
        """
        Save a pending elicitation.

        Args:
            session_id: Session identifier
            elicitation: PendingElicitation to store
            ttl_seconds: Optional TTL override
        """
        key = self._make_key(session_id)
        ttl = ttl_seconds or self.ttl_seconds

        # Add expiration timestamp
        expires_at = (datetime.utcnow() + timedelta(seconds=ttl)).isoformat()
        elicitation_data = dict(elicitation)
        elicitation_data["expires_at"] = expires_at

        data = json.dumps(elicitation_data)

        # Use async if available, fallback to sync
        if hasattr(self.redis, "set") and callable(self.redis.set):
            try:
                await self.redis.set(key, data, ex=ttl)
            except TypeError:
                # Sync redis client
                self.redis.set(key, data, ex=ttl)

        logger.debug(f"Saved elicitation {elicitation.get('elicitation_id')} for session {session_id}")

    async def get(self, session_id: str) -> PendingElicitation | None:
        """
        Get pending elicitation for session.

        Args:
            session_id: Session identifier

        Returns:
            PendingElicitation if found, None otherwise
        """
        key = self._make_key(session_id)

        try:
            data = await self.redis.get(key)
        except TypeError:
            # Sync redis client
            data = self.redis.get(key)

        if not data:
            return None

        if isinstance(data, bytes):
            data = data.decode("utf-8")

        try:
            return json.loads(data)
        except json.JSONDecodeError:
            logger.error(f"Failed to decode elicitation data for session {session_id}")
            return None

    async def get_or_raise(self, session_id: str) -> PendingElicitation:
        """
        Get pending elicitation or raise exception.

        Args:
            session_id: Session identifier

        Returns:
            PendingElicitation

        Raises:
            ElicitationNotFoundError: If no pending elicitation found
        """
        elicitation = await self.get(session_id)
        if elicitation is None:
            raise ElicitationNotFoundError(session_id)
        return elicitation

    async def delete(self, session_id: str) -> bool:
        """
        Delete pending elicitation.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False if not found
        """
        key = self._make_key(session_id)

        try:
            result = await self.redis.delete(key)
        except TypeError:
            # Sync redis client
            result = self.redis.delete(key)

        deleted = result > 0
        if deleted:
            logger.debug(f"Deleted elicitation for session {session_id}")
        return deleted

    async def exists(self, session_id: str) -> bool:
        """
        Check if pending elicitation exists.

        Args:
            session_id: Session identifier

        Returns:
            True if exists
        """
        key = self._make_key(session_id)

        try:
            result = await self.redis.exists(key)
        except TypeError:
            # Sync redis client
            result = self.redis.exists(key)

        return result > 0

    async def extend_ttl(
        self,
        session_id: str,
        additional_seconds: int,
    ) -> bool:
        """
        Extend TTL for pending elicitation.

        Args:
            session_id: Session identifier
            additional_seconds: Seconds to add to current TTL

        Returns:
            True if extended, False if not found
        """
        key = self._make_key(session_id)

        try:
            current_ttl = await self.redis.ttl(key)
        except TypeError:
            current_ttl = self.redis.ttl(key)

        if current_ttl < 0:
            return False

        new_ttl = current_ttl + additional_seconds

        try:
            await self.redis.expire(key, new_ttl)
        except TypeError:
            self.redis.expire(key, new_ttl)

        return True

    async def get_ttl(self, session_id: str) -> int | None:
        """
        Get remaining TTL for pending elicitation.

        Args:
            session_id: Session identifier

        Returns:
            Remaining seconds, or None if not found
        """
        key = self._make_key(session_id)

        try:
            ttl = await self.redis.ttl(key)
        except TypeError:
            ttl = self.redis.ttl(key)

        return ttl if ttl >= 0 else None
