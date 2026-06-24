# blu_tool_registry
"""
Centralized tool discovery and dynamic allocation for Blu multi-agent architecture.

This package provides:
- ToolRegistry: Central registry of all available tools
- TierValidator: Tier-based access control
- DockerMCPBridge: Docker MCP integration for composable tools
- ToolMetadata: Tool definition and metadata

Usage:
    from blu_tool_registry import ToolRegistry, TierValidator, ToolMetadata

    # Get available tools for a client
    tools = ToolRegistry.get_available_tools(
        enabled_tools=["executar_rag_cliente"],
        tier="BASIC"
    )

    # Validate client configuration
    is_valid, errors = ToolRegistry.validate_client_tools(
        enabled_tools=["executar_sql_agent"],
        tier="BASIC"
    )
"""

from blu_tool_registry.docker_mcp_bridge import DockerMCPBridge
from blu_tool_registry.exceptions import (
    DockerMCPConnectionError,
    TierAccessDeniedError,
    ToolNotFoundError,
    ToolRegistryError,
)
from blu_tool_registry.features import FEATURES, TIER_FEATURES, FeatureConfig, FeatureRegistry
from blu_tool_registry.registry import ToolRegistry
from blu_tool_registry.resource_resolver import ResourceResolver
from blu_tool_registry.tier_validator import TierValidator
from blu_tool_registry.tool_metadata import ToolCategory, ToolMetadata

__all__ = [
    # Core classes
    "ToolRegistry",
    "ToolMetadata",
    "ToolCategory",
    "TierValidator",
    "DockerMCPBridge",
    # Feature layer (Fase 1 — Tier Enforcement Redesign)
    "FeatureConfig",
    "FeatureRegistry",
    "ResourceResolver",
    "FEATURES",
    "TIER_FEATURES",
    # Exceptions
    "ToolRegistryError",
    "ToolNotFoundError",
    "TierAccessDeniedError",
    "DockerMCPConnectionError",
]

__version__ = "0.1.0"
