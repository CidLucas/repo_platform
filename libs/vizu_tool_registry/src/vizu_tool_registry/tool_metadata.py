"""
vizu_tool_registry.tool_metadata
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tool definition and metadata models.

This module defines the ToolMetadata dataclass which holds all information
about a tool including its tier requirements, category, and Docker MCP integration.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any


class ToolCategory(str, Enum):
    """Categories of tools available in the system."""

    RAG = "rag"
    SQL = "sql"
    SCHEDULING = "scheduling"
    DOCKER_MCP = "docker_mcp"
    PUBLIC = "public"
    GOOGLE = "google"
    CUSTOM = "custom"


class TierLevel(str, Enum):
    """
    Service tiers that control tool access.

    Order: FREE < BASIC < SME < PREMIUM < ENTERPRISE
    """

    FREE = "FREE"
    BASIC = "BASIC"
    SME = "SME"
    PREMIUM = "PREMIUM"
    ENTERPRISE = "ENTERPRISE"

    @classmethod
    def get_order(cls, tier: str) -> int:
        """Get numeric order for tier comparison."""
        order = {"FREE": 0, "BASIC": 1, "SME": 2, "PREMIUM": 3, "ENTERPRISE": 4}
        return order.get(tier, 0)

    def __lt__(self, other: "TierLevel") -> bool:
        return self.get_order(self.value) < self.get_order(other.value)

    def __le__(self, other: "TierLevel") -> bool:
        return self.get_order(self.value) <= self.get_order(other.value)

    def __gt__(self, other: "TierLevel") -> bool:
        return self.get_order(self.value) > self.get_order(other.value)

    def __ge__(self, other: "TierLevel") -> bool:
        return self.get_order(self.value) >= self.get_order(other.value)


@dataclass
class ToolMetadata:
    """
    Metadata for a tool in the registry.

    Attributes:
        name: Technical name of the tool (e.g., 'executar_rag_cliente')
        category: Category of the tool (rag, sql, scheduling, docker_mcp)
        description: Human-readable description
        tier_required: Minimum tier required to access this tool
        requires_confirmation: Whether tool needs user confirmation before execution
        docker_mcp_integration: Docker MCP server name if applicable (e.g., 'github')
        enabled: Whether the tool is globally enabled
        parameters: JSON schema for tool parameters
        tags: Additional tags for filtering/grouping
    """

    name: str
    category: ToolCategory
    description: str
    tier_required: TierLevel = TierLevel.BASIC
    requires_confirmation: bool = False
    docker_mcp_integration: Optional[str] = None
    enabled: bool = True
    parameters: Optional[Dict[str, Any]] = None
    tags: list = field(default_factory=list)

    def is_accessible_by_tier(self, client_tier: str) -> bool:
        """
        Check if a client tier can access this tool.

        Args:
            client_tier: The client's tier as a string

        Returns:
            True if the client can access this tool
        """
        client_order = TierLevel.get_order(client_tier)
        required_order = TierLevel.get_order(self.tier_required.value)
        return client_order >= required_order

    def is_docker_mcp_tool(self) -> bool:
        """Check if this is a Docker MCP integration tool."""
        return self.docker_mcp_integration is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "tier_required": self.tier_required.value,
            "requires_confirmation": self.requires_confirmation,
            "docker_mcp_integration": self.docker_mcp_integration,
            "enabled": self.enabled,
            "parameters": self.parameters,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolMetadata":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            category=ToolCategory(data.get("category", "custom")),
            description=data.get("description", ""),
            tier_required=TierLevel(data.get("tier_required", "BASIC")),
            requires_confirmation=data.get("requires_confirmation", False),
            docker_mcp_integration=data.get("docker_mcp_integration"),
            enabled=data.get("enabled", True),
            parameters=data.get("parameters"),
            tags=data.get("tags", []),
        )
