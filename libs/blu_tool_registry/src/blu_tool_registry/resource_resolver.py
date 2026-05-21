"""
blu_tool_registry.resource_resolver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

ResourceResolver — single entry point for tier-aware resource resolution.

Replaces the scattered tier enforcement copies across:
  - factory.py (get_frontdesk_graph, get_standalone_agent)
  - routines.py line 1175 (worker tool filter)
  - agents_router.py (/catalog/agents filter)
  - tool_pool_api/resources.py

Usage:
    from blu_tool_registry.resource_resolver import ResourceResolver

    tools = ResourceResolver.resolve_tools("financeiro", "SME")
    agents = ResourceResolver.resolve_agents("PREMIUM")
    ok = ResourceResolver.can_access_agent("fiscal-agent", "SME")  # False
    ok = ResourceResolver.can_access_agent("fiscal-agent", "ENTERPRISE")  # True
"""

from __future__ import annotations

import logging

from .features import FeatureRegistry
from .tool_metadata import TierLevel

logger = logging.getLogger(__name__)


class ResourceResolver:
    """
    Tier-aware resource resolver.

    Wraps FeatureRegistry with:
    - Graceful handling of unknown tier strings (falls back to FREE, warns)
    - Optional intersection with an explicit enabled_tools override list
      (preserves the per-client tool customisation already in the DB)

    All methods are class-methods — no instantiation needed.
    """

    # ── private ────────────────────────────────────────────────────────────

    @staticmethod
    def _safe_tier(tier: str | TierLevel) -> str | TierLevel:
        """
        Normalise and validate a tier value.

        Returns the original value if valid; returns TierLevel.FREE and
        emits a warning if the tier is unrecognised.
        """
        try:
            FeatureRegistry._normalize_tier(tier)
            return tier
        except ValueError:
            logger.warning(
                "ResourceResolver: unknown tier %r — falling back to FREE", tier
            )
            return TierLevel.FREE

    # ── public API ─────────────────────────────────────────────────────────

    @classmethod
    def resolve_tools(
        cls,
        agent_slug: str,
        tier: str | TierLevel,
        *,
        enabled_tools_override: list[str] | None = None,
    ) -> list[str]:
        """
        Return the tool slugs available to *agent_slug* under *tier*.

        Args:
            agent_slug: Agent identifier (e.g. "financeiro", "frontdesk").
            tier:       Client tier string or TierLevel enum.
            enabled_tools_override: If provided and non-empty, filter the
                feature-derived tools to only those present in this list.
                This preserves per-client customisation stored in clientes_blu.

        Returns:
            Ordered list of tool slugs. Empty list if the agent is not
            accessible under the given tier.
        """
        safe = cls._safe_tier(tier)

        if not FeatureRegistry.is_agent_accessible(agent_slug, safe):
            logger.debug(
                "ResourceResolver.resolve_tools: agent %r not accessible at tier %r",
                agent_slug,
                tier,
            )
            return []

        tools = FeatureRegistry.get_tools_for_agent_and_tier(agent_slug, safe)

        if enabled_tools_override:
            override_set = set(enabled_tools_override)
            tools = [t for t in tools if t in override_set]

        return tools

    @classmethod
    def resolve_agents(cls, tier: str | TierLevel) -> list[str]:
        """
        Return agent slugs visible to a client with *tier*.

        The list is ordered by first appearance across features (feature
        priority order from TIER_FEATURES).
        """
        safe = cls._safe_tier(tier)
        return FeatureRegistry.get_agents_for_tier(safe)

    @classmethod
    def can_access_agent(cls, agent_slug: str, tier: str | TierLevel) -> bool:
        """
        Return True if *agent_slug* is reachable under *tier*.

        Safe: never raises; unknown tier is treated as FREE.
        """
        safe = cls._safe_tier(tier)
        return FeatureRegistry.is_agent_accessible(agent_slug, safe)

    @classmethod
    def can_access_tool(cls, tool_slug: str, tier: str | TierLevel) -> bool:
        """
        Return True if *tool_slug* is reachable under *tier* (any agent).

        Safe: never raises; unknown tier is treated as FREE.
        """
        safe = cls._safe_tier(tier)
        return FeatureRegistry.is_tool_accessible(tool_slug, safe)

    @classmethod
    def resolve_all_tools_for_tier(cls, tier: str | TierLevel) -> list[str]:
        """
        Return every tool reachable under *tier* regardless of agent.

        Useful for pool-level filtering (tool_pool_api/resources.py).
        """
        safe = cls._safe_tier(tier)
        return FeatureRegistry.get_tools_for_tier(safe)

    @classmethod
    def filter_tools(
        cls,
        raw_tools: list[str],
        agent_slug: str,
        tier: str | TierLevel,
    ) -> list[str]:
        """
        Filter *raw_tools* to those allowed for *agent_slug* at *tier*.

        Primary gate: FeatureRegistry (feature map).
        Fallback for tools absent from the feature map: ToolRegistry per-tool
        tier check (forward-compat while migration is incomplete).

        Replaces the three identical inline filter blocks that previously lived
        in factory.py (×2) and routines.py (×1).
        """
        # Import locally to avoid circular imports at module level.
        from .registry import ToolRegistry  # noqa: PLC0415

        tier_str: str = tier.value if isinstance(tier, TierLevel) else tier
        feature_tools = set(cls.resolve_tools(agent_slug, tier))
        return [
            t for t in raw_tools
            if t in feature_tools
            or (meta := ToolRegistry.get_tool(t)) is None
            or meta.is_accessible_by_tier(tier_str)
        ]
