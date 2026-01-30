"""
Shared helpers for tool modules.

This module provides common functionality used across multiple tool modules
to avoid duplication and ensure consistency.
"""

import logging

from vizu_models.vizu_client_context import VizuClientContext
from vizu_tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


def is_tool_enabled_for_client(tool_name: str, context: VizuClientContext) -> bool:
    """
    Check if a tool is enabled for a client.

    Uses the authoritative `enabled_tools` list and validates against tier.

    Args:
        tool_name: Name of the tool (e.g., "executar_sql_agent")
        context: VizuClientContext

    Returns:
        True if tool is enabled and accessible by client's tier
    """
    enabled = getattr(context, "enabled_tools", None) or []

    if tool_name not in enabled:
        return False

    tier = get_tier_for_context(context)
    tool_meta = ToolRegistry.get_tool(tool_name)
    if tool_meta and not tool_meta.is_accessible_by_tier(tier):
        return False

    return True


def get_enabled_tools_for_context(context: VizuClientContext) -> list[str]:
    """
    Get list of enabled tool names from client context.

    Args:
        context: VizuClientContext

    Returns:
        List of enabled tool names
    """
    return getattr(context, "enabled_tools", []) or []


def get_tier_for_context(context: VizuClientContext) -> str:
    """
    Get tier string from client context.

    Handles both string tier values and enum types.

    Args:
        context: VizuClientContext

    Returns:
        Tier string ("BASIC", "SME", "ENTERPRISE")
    """
    raw_tier = getattr(context, "tier", None)
    if isinstance(raw_tier, str) and raw_tier:
        return raw_tier
    elif hasattr(raw_tier, "value") and isinstance(raw_tier.value, str) and raw_tier.value:
        return raw_tier.value
    return "BASIC"
