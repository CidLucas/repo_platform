"""
MCP Tool Executor — thin wrapper over MCPConnectionManager.

TODO(phase4): Inline MCPConnectionManager calls directly into AgentBuilder
and remove this module entirely.  All new code should use MCPConnectionManager.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Result from MCP tool execution."""

    tool_name: str
    success: bool
    result: Any = None
    error: str | None = None
    execution_time_ms: float = 0.0
    metadata: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> dict[str, Any]:
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
    """Wrapper over MCPConnectionManager used by AgentBuilder's tool execution path."""

    def __init__(
        self,
        mcp_url: str = "http://localhost:8000/mcp/",
        timeout: float = 30.0,
        max_retries: int = 3,
        mcp_manager=None,
    ):
        self.mcp_url = mcp_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        # Accept a pre-built MCPConnectionManager so that auth headers set on the
        # shared singleton (X-Cliente-Id, X-Session-Id) are visible to tool calls.
        # When None, a private manager is created lazily (legacy / test behaviour).
        self._mcp_manager = mcp_manager

    async def _get_mcp_manager(self) -> None:
        """Get or create MCP manager (lazy)."""
        if self._mcp_manager is None:
            from blu_agent_framework.mcp_client import MCPConnectionManager

            self._mcp_manager = MCPConnectionManager(url=self.mcp_url)
            try:
                await self._mcp_manager.connect()
            except Exception as e:
                logger.warning(f"Failed to connect to MCP: {e}")
        return self._mcp_manager

    async def execute(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        context: dict[str, Any],
    ) -> ToolResult:
        """Execute a tool via MCP."""
        import time

        start_time = time.time()

        try:
            mcp_manager = await self._get_mcp_manager()
            if mcp_manager is None:
                return ToolResult(
                    tool_name=tool_name,
                    success=False,
                    error="MCP not connected",
                    execution_time_ms=(time.time() - start_time) * 1000,
                )
            await mcp_manager.ensure_connected()
            if not mcp_manager.is_connected:
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

            # Build call arguments — do NOT inject client_id here.
            # client_id is set as X-Cliente-Id on the MCPConnectionManager's HTTP
            # headers (via set_client_id) and is injected server-side by
            # mcp_inject_client_id. Passing it in args would conflict with the
            # pydantic schema that hides it from the LLM.
            args = dict(tool_args)

            # Execute via call_tool with full context as meta
            raw_result = await mcp_manager.call_tool(tool_name, args, meta=context)

            # Extract text content from MCP CallToolResult
            if hasattr(raw_result, "content"):
                text_parts = [
                    c.text for c in raw_result.content
                    if hasattr(c, "text")
                ]
                result = "\n".join(text_parts) if text_parts else str(raw_result)
                is_error = getattr(raw_result, "isError", False)
            else:
                result = str(raw_result)
                is_error = False

            return ToolResult(
                tool_name=tool_name,
                success=not is_error,
                result=result,
                error=result if is_error else None,
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

    async def get_lc_tools(self, names: list[str]) -> list[Any]:
        """Return LangChain BaseTool objects for the requested tool names.

        Replaces direct access to the internal _mcp_manager so callers stay
        decoupled from the private connection lifecycle.
        """
        mcp_mgr = await self._get_mcp_manager()
        if not mcp_mgr:
            return []
        await mcp_mgr.ensure_connected()
        if not mcp_mgr.is_connected:
            return []
        return [t for name in names if (t := mcp_mgr.get_tool_by_name(name)) is not None]

    async def close(self) -> None:
        """Close MCP connection."""
        if self._mcp_manager:
            await self._mcp_manager.disconnect()
            self._mcp_manager = None
