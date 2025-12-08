"""
DEPRECATED: Legacy MCP Tool Executor - use MCPConnectionManager instead.

This module is kept for backward compatibility with AgentBuilder.
New code should use mcp_client.MCPConnectionManager directly.
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Result from MCP tool execution."""

    tool_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "metadata": self.metadata,
        }


class MCPToolExecutor:
    """
    DEPRECATED: Use MCPConnectionManager from mcp_client instead.

    This class is kept for backward compatibility with AgentBuilder.
    """

    def __init__(
        self,
        mcp_url: str = "http://localhost:8000/mcp/",
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """Initialize executor (deprecated)."""
        import warnings
        warnings.warn(
            "MCPToolExecutor is deprecated. Use MCPConnectionManager instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.mcp_url = mcp_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._mcp_manager = None

    async def _get_mcp_manager(self):
        """Get or create MCP manager (lazy)."""
        if self._mcp_manager is None:
            from vizu_agent_framework.mcp_client import MCPConnectionManager
            self._mcp_manager = MCPConnectionManager(url=self.mcp_url)
            try:
                await self._mcp_manager.connect()
            except Exception as e:
                logger.warning(f"Failed to connect to MCP: {e}")
        return self._mcp_manager

    async def execute(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        context: Dict[str, Any],
    ) -> ToolResult:
        """Execute a tool via MCP."""
        import time
        start_time = time.time()

        try:
            mcp_manager = await self._get_mcp_manager()
            if mcp_manager is None or not mcp_manager.is_connected:
                return ToolResult(
                    tool_name=tool_name,
                    success=False,
                    error="MCP not connected",
                    execution_time_ms=(time.time() - start_time) * 1000,
                )

            # Find tool in manager
            tool = mcp_manager.get_tool_by_name(tool_name)
            if not tool:
                return ToolResult(
                    tool_name=tool_name,
                    success=False,
                    error=f"Tool '{tool_name}' not found",
                    execution_time_ms=(time.time() - start_time) * 1000,
                )

            # Inject context into args
            args = dict(tool_args)
            if "cliente_id" not in args and context.get("cliente_id"):
                args["cliente_id"] = context["cliente_id"]

            # Execute
            if hasattr(tool, "ainvoke"):
                result = await tool.ainvoke(args)
            elif hasattr(tool, "invoke"):
                result = await asyncio.to_thread(tool.invoke, args)
            else:
                result = str(tool.run(args))

            return ToolResult(
                tool_name=tool_name,
                success=True,
                result=result,
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            logger.exception(f"Tool execution failed: {tool_name}")
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000,
            )

    async def close(self):
        """Close MCP connection."""
        if self._mcp_manager:
            await self._mcp_manager.disconnect()
            self._mcp_manager = None
