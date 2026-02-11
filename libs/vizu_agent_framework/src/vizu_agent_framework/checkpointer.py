"""
Redis checkpointer for LangGraph state persistence.
"""

import json
import logging
from collections.abc import Iterator
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)

logger = logging.getLogger(__name__)


class RedisCheckpointer(BaseCheckpointSaver):
    """
    Redis-backed checkpoint saver for LangGraph.

    Stores agent state in Redis with configurable TTL.
    Supports both sync and async Redis clients.
    """

    def __init__(
        self,
        redis_client: Any,
        key_prefix: str = "vizu:checkpoint:",
        ttl_seconds: int = 86400,  # 24 hours
    ):
        """
        Initialize checkpointer.

        Args:
            redis_client: Redis client instance (sync or async)
            key_prefix: Prefix for Redis keys
            ttl_seconds: Time-to-live for checkpoints
        """
        super().__init__()
        self.redis = redis_client
        self.key_prefix = key_prefix
        self.ttl_seconds = ttl_seconds

    def _make_key(self, thread_id: str, checkpoint_ns: str = "") -> str:
        """Generate Redis key for checkpoint."""
        if checkpoint_ns:
            return f"{self.key_prefix}{thread_id}:{checkpoint_ns}"
        return f"{self.key_prefix}{thread_id}"

    def _serialize(self, checkpoint: Checkpoint) -> str:
        """Serialize checkpoint to JSON."""
        return json.dumps(
            {
                "v": checkpoint["v"],
                "ts": checkpoint["ts"],
                "id": checkpoint["id"],
                "channel_values": self._serialize_channel_values(checkpoint["channel_values"]),
                "channel_versions": checkpoint["channel_versions"],
                "versions_seen": checkpoint["versions_seen"],
                "pending_sends": checkpoint.get("pending_sends", []),
            }
        )

    def _serialize_channel_values(self, values: dict[str, Any]) -> dict[str, Any]:
        """Serialize channel values (handle messages and other non-JSON types)."""
        from langchain_core.messages import BaseMessage

        serialized = {}
        for key, value in values.items():
            if key == "messages" and isinstance(value, list):
                # Serialize LangChain messages
                serialized[key] = [
                    {
                        "type": type(msg).__name__,
                        "content": msg.content if hasattr(msg, "content") else str(msg),
                        "additional_kwargs": getattr(msg, "additional_kwargs", {}),
                    }
                    for msg in value
                ]
            elif isinstance(value, BaseMessage):
                # Single message
                serialized[key] = {
                    "type": type(value).__name__,
                    "content": value.content if hasattr(value, "content") else str(value),
                    "additional_kwargs": getattr(value, "additional_kwargs", {}),
                }
            elif isinstance(value, list):
                # Handle lists that might contain messages
                serialized[key] = [self._serialize_value(item) for item in value]
            elif isinstance(value, dict):
                # Recursively serialize dicts
                serialized[key] = {k: self._serialize_value(v) for k, v in value.items()}
            else:
                serialized[key] = self._serialize_value(value)
        return serialized

    def _serialize_value(self, value: Any) -> Any:
        """Serialize a single value."""
        from uuid import UUID

        from langchain_core.messages import BaseMessage

        if isinstance(value, BaseMessage):
            return {
                "__type__": "message",
                "type": type(value).__name__,
                "content": value.content if hasattr(value, "content") else str(value),
                "additional_kwargs": getattr(value, "additional_kwargs", {}),
            }
        elif isinstance(value, UUID):
            return {"__type__": "uuid", "value": str(value)}
        elif isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._serialize_value(v) for v in value]
        elif hasattr(value, "__dict__"):
            # Try to serialize objects with __dict__
            try:
                return {"__type__": "object", "class": type(value).__name__, "data": str(value)}
            except Exception:
                return str(value)
        else:
            return value

    def _deserialize(self, data: str) -> Checkpoint:
        """Deserialize checkpoint from JSON."""
        parsed = json.loads(data)
        return Checkpoint(
            v=parsed["v"],
            ts=parsed["ts"],
            id=parsed["id"],
            channel_values=self._deserialize_channel_values(parsed["channel_values"]),
            channel_versions=parsed["channel_versions"],
            versions_seen=parsed["versions_seen"],
            pending_sends=parsed.get("pending_sends", []),
        )

    def _deserialize_channel_values(self, values: dict[str, Any]) -> dict[str, Any]:
        """Deserialize channel values (restore messages)."""
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        MESSAGE_TYPES = {
            "HumanMessage": HumanMessage,
            "AIMessage": AIMessage,
            "SystemMessage": SystemMessage,
        }

        deserialized = {}
        for key, value in values.items():
            if key == "messages" and isinstance(value, list):
                messages = []
                for msg_data in value:
                    msg_type = MESSAGE_TYPES.get(msg_data["type"], HumanMessage)
                    messages.append(
                        msg_type(
                            content=msg_data["content"],
                            additional_kwargs=msg_data.get("additional_kwargs", {}),
                        )
                    )
                deserialized[key] = messages
            else:
                deserialized[key] = value
        return deserialized

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        """Get checkpoint tuple for config (sync)."""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")

        key = self._make_key(thread_id, checkpoint_ns)

        try:
            data = self.redis.get(key)
            if not data:
                return None

            if isinstance(data, bytes):
                data = data.decode("utf-8")

            checkpoint = self._deserialize(data)

            return CheckpointTuple(
                config=config,
                checkpoint=checkpoint,
                metadata=CheckpointMetadata(
                    source="redis",
                    step=-1,
                    writes={},
                    parents={},
                ),
                parent_config=None,
            )
        except Exception as e:
            logger.error(f"Failed to get checkpoint: {e}")
            return None

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        """Get checkpoint tuple for config (async)."""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")

        key = self._make_key(thread_id, checkpoint_ns)

        try:
            data = await self.redis.get(key)
            if not data:
                return None

            if isinstance(data, bytes):
                data = data.decode("utf-8")

            checkpoint = self._deserialize(data)

            return CheckpointTuple(
                config=config,
                checkpoint=checkpoint,
                metadata=CheckpointMetadata(
                    source="redis",
                    step=-1,
                    writes={},
                    parents={},
                ),
                parent_config=None,
            )
        except Exception as e:
            logger.error(f"Failed to get checkpoint: {e}")
            return None

    def list(
        self,
        config: RunnableConfig | None = None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        """List checkpoints (sync)."""
        # Basic implementation - list all keys matching prefix
        if config:
            thread_id = config["configurable"]["thread_id"]
            pattern = f"{self.key_prefix}{thread_id}*"
        else:
            pattern = f"{self.key_prefix}*"

        count = 0
        for key in self.redis.scan_iter(match=pattern):
            if limit and count >= limit:
                break

            try:
                data = self.redis.get(key)
                if data:
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")

                    checkpoint = self._deserialize(data)

                    # Extract thread_id from key
                    key_str = key if isinstance(key, str) else key.decode("utf-8")
                    thread_id = key_str.replace(self.key_prefix, "").split(":")[0]

                    yield CheckpointTuple(
                        config=RunnableConfig(configurable={"thread_id": thread_id}),
                        checkpoint=checkpoint,
                        metadata=CheckpointMetadata(
                            source="redis",
                            step=-1,
                            writes={},
                            parents={},
                        ),
                        parent_config=None,
                    )
                    count += 1
            except Exception as e:
                logger.warning(f"Failed to deserialize checkpoint: {e}")

    async def alist(
        self,
        config: RunnableConfig | None = None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ):
        """List checkpoints (async)."""
        # Async implementation would use async scan
        # For simplicity, yield from sync version
        for item in self.list(config, filter=filter, before=before, limit=limit):
            yield item

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: dict[str, Any] | None = None,
    ) -> RunnableConfig:
        """Put checkpoint (sync)."""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")

        key = self._make_key(thread_id, checkpoint_ns)
        data = self._serialize(checkpoint)

        try:
            self.redis.set(key, data, ex=self.ttl_seconds)
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

        return config

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: dict[str, Any] | None = None,
    ) -> RunnableConfig:
        """Put checkpoint (async)."""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")

        key = self._make_key(thread_id, checkpoint_ns)
        data = self._serialize(checkpoint)

        try:
            await self.redis.set(key, data, ex=self.ttl_seconds)
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

        return config

    def put_writes(
        self,
        config: RunnableConfig,
        writes: list,
        task_id: str,
    ) -> None:
        """Put writes (sync) - not implemented for basic checkpointer."""
        pass

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: list,
        task_id: str,
    ) -> None:
        """Put writes (async) - not implemented for basic checkpointer."""
        pass

    async def delete_checkpoint(self, thread_id: str, checkpoint_ns: str = "") -> bool:
        """Delete a specific checkpoint."""
        key = self._make_key(thread_id, checkpoint_ns)
        try:
            result = await self.redis.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Failed to delete checkpoint: {e}")
            return False

    async def delete_thread(self, thread_id: str) -> int:
        """Delete all checkpoints for a thread."""
        pattern = f"{self.key_prefix}{thread_id}*"
        deleted = 0

        try:
            async for key in self.redis.scan_iter(match=pattern):
                await self.redis.delete(key)
                deleted += 1
        except Exception as e:
            logger.error(f"Failed to delete thread checkpoints: {e}")

        return deleted
