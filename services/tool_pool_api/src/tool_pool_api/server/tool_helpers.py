"""
Shared helpers for tool modules.

This module provides common functionality used across multiple tool modules
to avoid duplication and ensure consistency.
"""

import logging

from blu_models.blu_client_context import BluClientContext
from blu_tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


def is_tool_accessible_by_tier(tool_name: str, context: BluClientContext) -> bool:
    """
    Check if a tool is accessible by the client's tier.

    Args:
        tool_name: Name of the tool (e.g., "executar_sql_agent")
        context: BluClientContext

    Returns:
        True if tool is accessible by client's tier
    """
    tier = get_tier_for_context(context)
    tool_meta = ToolRegistry.get_tool(tool_name)
    if tool_meta and not tool_meta.is_accessible_by_tier(tier):
        return False

    return True


def get_tier_for_context(context: BluClientContext) -> str:
    """
    Get tier string from client context.

    Handles both string tier values and enum types.

    Args:
        context: BluClientContext

    Returns:
        Tier string ("BASIC", "SME", "ENTERPRISE")
    """
    raw_tier = getattr(context, "tier", None)
    if isinstance(raw_tier, str) and raw_tier:
        return raw_tier
    elif hasattr(raw_tier, "value") and isinstance(raw_tier.value, str) and raw_tier.value:
        return raw_tier.value
    return "BASIC"
