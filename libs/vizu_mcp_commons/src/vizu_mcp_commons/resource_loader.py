"""
Dynamic resource loading for MCP services.

Provides utilities for loading and filtering resources (prompts, knowledge bases, etc.)
based on client context.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


@dataclass
class ResourceMetadata:
    """Metadata for a loadable resource."""

    name: str
    uri: str
    description: str = ""
    mime_type: str = "text/plain"
    tier_required: str | None = None
    client_specific: bool = False
    version: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass
class LoadedResource:
    """A loaded resource with content and metadata."""

    metadata: ResourceMetadata
    content: Any
    loaded_at: float | None = None


class ResourceLoader:
    """
    Load and manage MCP resources dynamically.

    Supports:
    - Loading resources from database
    - Client-specific resource filtering
    - Tier-based access control
    - Caching
    """

    def __init__(
        self,
        context_service_factory: Callable | None = None,
        cache_ttl_seconds: int = 300,
    ):
        """
        Initialize ResourceLoader.

        Args:
            context_service_factory: Factory function for ContextService
            cache_ttl_seconds: TTL for cached resources
        """
        self.context_service_factory = context_service_factory
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[str, LoadedResource] = {}
        self._resource_registry: dict[str, ResourceMetadata] = {}

    def register_resource(self, metadata: ResourceMetadata) -> None:
        """Register a resource for discovery."""
        self._resource_registry[metadata.uri] = metadata

    def list_resources(
        self,
        cliente_id: UUID | None = None,
        tier: str | None = None,
        tags: list[str] | None = None,
    ) -> list[ResourceMetadata]:
        """
        List available resources with optional filtering.

        Args:
            cliente_id: Filter to client-specific resources
            tier: Filter by minimum tier
            tags: Filter by tags (any match)

        Returns:
            List of ResourceMetadata
        """
        result = []

        for metadata in self._resource_registry.values():
            # Skip client-specific if no cliente_id
            if metadata.client_specific and not cliente_id:
                continue

            # Check tier if specified
            if tier and metadata.tier_required:
                from vizu_models.enums import TierCliente

                try:
                    required = TierCliente(metadata.tier_required)
                    current = TierCliente(tier)
                    if current < required:
                        continue
                except ValueError:
                    pass

            # Check tags if specified
            if tags and metadata.tags:
                if not any(tag in metadata.tags for tag in tags):
                    continue

            result.append(metadata)

        return result

    async def load_resource(
        self,
        uri: str,
        cliente_id: UUID | None = None,
        use_cache: bool = True,
    ) -> LoadedResource | None:
        """
        Load a resource by URI.

        Args:
            uri: Resource URI
            cliente_id: Client ID for context
            use_cache: Whether to use cached version

        Returns:
            LoadedResource or None if not found
        """
        import time

        cache_key = f"{uri}:{cliente_id or 'global'}"

        # Check cache
        if use_cache and cache_key in self._cache:
            cached = self._cache[cache_key]
            if cached.loaded_at and (time.time() - cached.loaded_at) < self.cache_ttl_seconds:
                return cached

        # Load from registry
        metadata = self._resource_registry.get(uri)
        if not metadata:
            logger.warning(f"Resource not found: {uri}")
            return None

        # Load content based on URI scheme
        content = await self._load_content(uri, cliente_id)
        if content is None:
            return None

        loaded = LoadedResource(
            metadata=metadata,
            content=content,
            loaded_at=time.time(),
        )

        # Cache
        self._cache[cache_key] = loaded
        return loaded

    async def _load_content(
        self,
        uri: str,
        cliente_id: UUID | None,
    ) -> Any | None:
        """Load resource content based on URI scheme."""
        if uri.startswith("db://prompts/"):
            return await self._load_prompt_from_db(uri, cliente_id)
        elif uri.startswith("file://"):
            return await self._load_from_file(uri)
        elif uri.startswith("config://"):
            return await self._load_config(uri, cliente_id)
        else:
            logger.warning(f"Unknown URI scheme: {uri}")
            return None

    async def _load_prompt_from_db(
        self,
        uri: str,
        cliente_id: UUID | None,
    ) -> str | None:
        """Load prompt template from database."""
        # Extract prompt name from URI: db://prompts/system_prompt
        prompt_name = uri.replace("db://prompts/", "")

        if not self.context_service_factory:
            logger.warning("No context service factory for DB resource loading")
            return None

        try:
            ctx_service = self.context_service_factory()
            # TODO: Implement prompt loading from context service
            # For now, return placeholder
            return f"[Prompt: {prompt_name}]"
        except Exception as e:
            logger.error(f"Error loading prompt from DB: {e}")
            return None

    async def _load_from_file(self, uri: str) -> str | None:
        """Load resource from file system."""
        import os

        import aiofiles

        path = uri.replace("file://", "")

        if not os.path.exists(path):
            logger.warning(f"File not found: {path}")
            return None

        try:
            async with aiofiles.open(path) as f:
                return await f.read()
        except Exception as e:
            logger.error(f"Error reading file {path}: {e}")
            return None

    async def _load_config(
        self,
        uri: str,
        cliente_id: UUID | None,
    ) -> dict | None:
        """Load configuration resource."""
        config_name = uri.replace("config://", "")

        if not self.context_service_factory:
            return None

        try:
            ctx_service = self.context_service_factory()
            if cliente_id:
                context = await ctx_service.get_client_context_by_id(cliente_id)
                if context:
                    # Return client-specific config
                    return {
                        "cliente_id": str(context.id),
                        "nome_cliente": context.nome_cliente,
                        "tier": context.tier.value if hasattr(context.tier, "value") else context.tier,
                        "enabled_tools": context.get_enabled_tools_list(),
                    }
            return None
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return None

    def clear_cache(self, uri: str | None = None) -> None:
        """Clear resource cache."""
        if uri:
            keys_to_remove = [k for k in self._cache if k.startswith(uri)]
            for key in keys_to_remove:
                del self._cache[key]
        else:
            self._cache.clear()


class MCPResourceBuilder:
    """
    Build MCP resource definitions from loaded resources.

    Converts LoadedResource objects to FastMCP resource format.
    """

    @staticmethod
    def to_mcp_resource(loaded: LoadedResource) -> dict[str, Any]:
        """
        Convert LoadedResource to MCP resource dict.

        Args:
            loaded: LoadedResource to convert

        Returns:
            Dict in MCP resource format
        """
        return {
            "uri": loaded.metadata.uri,
            "name": loaded.metadata.name,
            "description": loaded.metadata.description,
            "mimeType": loaded.metadata.mime_type,
        }

    @staticmethod
    def register_with_mcp(
        mcp: Any,
        loader: ResourceLoader,
        resources: list[ResourceMetadata],
    ) -> None:
        """
        Register resources with FastMCP server.

        Args:
            mcp: FastMCP instance
            loader: ResourceLoader to use
            resources: List of resources to register
        """
        for metadata in resources:
            async def resource_fn(uri: str = metadata.uri):
                loaded = await loader.load_resource(uri)
                if loaded:
                    return loaded.content
                return f"Resource not found: {uri}"

            mcp.resource(
                uri=metadata.uri,
                name=metadata.name,
                description=metadata.description,
                mime_type=metadata.mime_type,
            )(resource_fn)
