"""
vizu_tool_registry.tier_validator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tier-based access control for tools.

This module provides the TierValidator class which handles:
- Tier definitions and included tools
- Tier upgrade logic (auto-enable new tools)
- Access validation
"""

import logging
from typing import Any

from .tool_metadata import TierLevel

logger = logging.getLogger(__name__)


class TierValidator:
    """
    Validates tool access based on client tier.

    Provides:
    - Tier definitions with included tools and limits
    - Upgrade logic for adding tools on tier change
    - Access validation helpers
    """

    # =========================================================================
    # TIER DEFINITIONS
    # =========================================================================
    TIER_DEFINITIONS: dict[str, dict[str, Any]] = {
        "FREE": {
            "included_tools": [],
            "max_queries_per_day": 10,
            "max_sessions": 1,
            "description": "Trial tier - basic testing only",
            "features": ["limited_chat"],
        },
        "BASIC": {
            "included_tools": ["executar_rag_cliente"],
            "max_queries_per_day": 100,
            "max_sessions": 5,
            "description": "Basic RAG search only",
            "features": ["rag", "chat"],
        },
        "SME": {
            "included_tools": [
                "executar_rag_cliente",
                "executar_sql_agent",
                "agendar_consulta",
            ],
            "max_queries_per_day": 1000,
            "max_sessions": 50,
            "description": "RAG, SQL, and scheduling for small/medium businesses",
            "features": ["rag", "sql", "scheduling", "chat", "analytics"],
        },
        "PREMIUM": {
            "included_tools": [
                "executar_rag_cliente",
                "executar_sql_agent",
                "agendar_consulta",
                "google_calendar_list_events",
                "google_calendar_create_event",
                "google_drive_list_files",
            ],
            "max_queries_per_day": 5000,
            "max_sessions": 200,
            "description": "All SME tools + Google integrations",
            "features": [
                "rag", "sql", "scheduling", "chat", "analytics",
                "google_integrations"
            ],
        },
        "ENTERPRISE": {
            "included_tools": [
                "executar_rag_cliente",
                "executar_sql_agent",
                "agendar_consulta",
                "google_calendar_list_events",
                "google_calendar_create_event",
                "google_drive_list_files",
            ],
            "max_queries_per_day": None,  # Unlimited
            "max_sessions": None,  # Unlimited
            "description": "All tools + Docker MCP integrations + custom tools",
            "features": [
                "rag", "sql", "scheduling", "chat", "analytics",
                "google_integrations", "docker_mcp", "custom_tools",
                "priority_support"
            ],
        },
    }

    # =========================================================================
    # CLASS METHODS
    # =========================================================================

    @classmethod
    def get_tier_definition(cls, tier: str) -> dict[str, Any] | None:
        """Get the definition for a tier."""
        return cls.TIER_DEFINITIONS.get(tier)

    @classmethod
    def get_default_tools_for_tier(cls, tier: str) -> list[str]:
        """
        Get the default tools included in a tier.

        Args:
            tier: Tier name (BASIC, SME, ENTERPRISE, etc.)

        Returns:
            List of tool names included in that tier
        """
        tier_def = cls.TIER_DEFINITIONS.get(tier, {})
        return tier_def.get("included_tools", [])

    @classmethod
    def can_access_tool(cls, tool_name: str, tier: str) -> bool:
        """
        Check if a tier has access to a specific tool.

        Note: This checks tier defaults, not client-specific configuration.
        For client-specific checks, use ToolRegistry.get_available_tools().

        Args:
            tool_name: Name of the tool
            tier: Client tier

        Returns:
            True if the tier includes this tool by default
        """
        tier_def = cls.TIER_DEFINITIONS.get(tier)
        if not tier_def:
            return False
        return tool_name in tier_def.get("included_tools", [])

    @classmethod
    def upgrade_tier_tools(
        cls, enabled_tools: list[str], new_tier: str
    ) -> list[str]:
        """
        Upgrade tool list when client tier is upgraded.

        Automatically enables new tools that come with the higher tier,
        while preserving any custom tools the client already had.

        Args:
            enabled_tools: Current list of enabled tools
            new_tier: The new tier being upgraded to

        Returns:
            Updated list of enabled tools
        """
        default_for_tier = cls.get_default_tools_for_tier(new_tier)

        # Merge: keep existing + add new defaults
        merged = list(set(enabled_tools) | set(default_for_tier))

        logger.info(
            f"Tier upgrade to {new_tier}: "
            f"added {set(default_for_tier) - set(enabled_tools)}"
        )
        return merged

    @classmethod
    def downgrade_tier_tools(
        cls,
        enabled_tools: list[str],
        new_tier: str,
        remove_inaccessible: bool = True,
    ) -> list[str]:
        """
        Handle tool list when client tier is downgraded.

        Optionally removes tools that are no longer accessible at the
        lower tier.

        Args:
            enabled_tools: Current list of enabled tools
            new_tier: The new (lower) tier
            remove_inaccessible: If True, removes tools not in new tier

        Returns:
            Updated list of enabled tools
        """
        if not remove_inaccessible:
            # Keep all tools (they'll fail validation but won't execute)
            return enabled_tools

        # Import here to avoid circular dependency
        from .registry import ToolRegistry

        accessible = []
        for tool_name in enabled_tools:
            tool = ToolRegistry.get_tool(tool_name)
            if tool and tool.is_accessible_by_tier(new_tier):
                accessible.append(tool_name)
            else:
                logger.info(
                    f"Tier downgrade to {new_tier}: removing {tool_name}"
                )

        return accessible

    @classmethod
    def get_tier_limits(cls, tier: str) -> dict[str, Any]:
        """
        Get rate limits for a tier.

        Args:
            tier: Tier name

        Returns:
            Dict with max_queries_per_day, max_sessions, etc.
        """
        tier_def = cls.TIER_DEFINITIONS.get(tier, {})
        return {
            "max_queries_per_day": tier_def.get("max_queries_per_day"),
            "max_sessions": tier_def.get("max_sessions"),
        }

    @classmethod
    def get_tier_features(cls, tier: str) -> list[str]:
        """
        Get features enabled for a tier.

        Args:
            tier: Tier name

        Returns:
            List of feature names
        """
        tier_def = cls.TIER_DEFINITIONS.get(tier, {})
        return tier_def.get("features", [])

    @classmethod
    def compare_tiers(cls, tier_a: str, tier_b: str) -> int:
        """
        Compare two tiers.

        Args:
            tier_a: First tier
            tier_b: Second tier

        Returns:
            -1 if tier_a < tier_b
             0 if tier_a == tier_b
             1 if tier_a > tier_b
        """
        order_a = TierLevel.get_order(tier_a)
        order_b = TierLevel.get_order(tier_b)

        if order_a < order_b:
            return -1
        elif order_a > order_b:
            return 1
        return 0

    @classmethod
    def is_tier_higher_or_equal(cls, tier: str, required_tier: str) -> bool:
        """
        Check if a tier is higher or equal to a required tier.

        Args:
            tier: The tier to check
            required_tier: The minimum required tier

        Returns:
            True if tier >= required_tier
        """
        return cls.compare_tiers(tier, required_tier) >= 0

    @classmethod
    def get_tier_diff(cls, from_tier: str, to_tier: str) -> dict[str, Any]:
        """
        Get the difference between two tiers (for upgrade/downgrade UI).

        Args:
            from_tier: Current tier
            to_tier: Target tier

        Returns:
            Dict with added/removed tools and features
        """
        from_def = cls.TIER_DEFINITIONS.get(from_tier, {})
        to_def = cls.TIER_DEFINITIONS.get(to_tier, {})

        from_tools = set(from_def.get("included_tools", []))
        to_tools = set(to_def.get("included_tools", []))

        from_features = set(from_def.get("features", []))
        to_features = set(to_def.get("features", []))

        return {
            "tools_added": list(to_tools - from_tools),
            "tools_removed": list(from_tools - to_tools),
            "features_added": list(to_features - from_features),
            "features_removed": list(from_features - to_features),
            "is_upgrade": cls.compare_tiers(to_tier, from_tier) > 0,
        }
