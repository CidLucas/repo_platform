# vizu_tool_registry
"""
Centralized tool discovery and dynamic allocation for Vizu multi-agent architecture.

This package provides:
- ToolRegistry: Central registry of all available tools
- TierValidator: Tier-based access control
- DockerMCPBridge: Docker MCP integration for composable tools
- ToolMetadata: Tool definition and metadata

Usage:
    from vizu_tool_registry import ToolRegistry, TierValidator, ToolMetadata

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

from .docker_mcp_bridge import DockerMCPBridge
from .exceptions import (
    DockerMCPConnectionError,
    TierAccessDeniedError,
    ToolNotFoundError,
    ToolRegistryError,
)
from .registry import ToolRegistry
from .tier_validator import TierValidator
from .tool_metadata import ToolCategory, ToolMetadata

__all__ = [
    # Core classes
    "ToolRegistry",
    "ToolMetadata",
    "ToolCategory",
    "TierValidator",
    "DockerMCPBridge",
    # Exceptions
    "ToolRegistryError",
    "ToolNotFoundError",
    "TierAccessDeniedError",
    "DockerMCPConnectionError",
]

__version__ = "0.1.0"
