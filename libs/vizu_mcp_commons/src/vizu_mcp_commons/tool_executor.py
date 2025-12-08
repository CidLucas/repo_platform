"""
Tool execution with context injection and parallel support.

Provides a unified interface for executing MCP tools with:
- Automatic context injection
- Tier validation
- Parallel execution
- Error handling
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, List, Optional, Dict, Callable
from uuid import UUID

from vizu_models.vizu_client_context import VizuClientContext

from vizu_mcp_commons.exceptions import (
    MCPToolError,
    MCPToolNotFoundError,
    MCPToolDisabledError,
    MCPTierAccessError,
)

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """Represents a tool call to be executed."""

    name: str
    args: Dict[str, Any] = field(default_factory=dict)
    call_id: Optional[str] = None


@dataclass
class ToolResult:
    """Result of a tool execution."""

    call_id: str
    name: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    duration_ms: Optional[float] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "call_id": self.call_id,
            "name": self.name,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "error_code": self.error_code,
            "duration_ms": self.duration_ms,
        }


class ToolExecutor:
    """
    Execute MCP tools with context injection and validation.

    Provides:
    - Single tool execution
    - Parallel execution of multiple tools
    - Automatic context injection
    - Tier-based access validation
    - Tool enablement validation
    """

    def __init__(
        self,
        context_service_factory: Callable,
        tool_registry: Optional[Any] = None,
        tool_callables: Optional[Dict[str, Callable]] = None,
    ):
        """
        Initialize ToolExecutor.

        Args:
            context_service_factory: Factory function returning ContextService
            tool_registry: Optional ToolRegistry for metadata and validation
            tool_callables: Dict mapping tool names to callable functions
        """
        self.context_service_factory = context_service_factory
        self.tool_registry = tool_registry
        self.tool_callables = tool_callables or {}

    def register_tool(self, name: str, callable: Callable) -> None:
        """Register a tool callable."""
        self.tool_callables[name] = callable

    async def execute_tool(
        self,
        tool_name: str,
        args: Dict[str, Any],
        cliente_context: VizuClientContext,
        call_id: Optional[str] = None,
        validate_access: bool = True,
    ) -> ToolResult:
        """
        Execute a single tool with context injection.

        Args:
            tool_name: Name of the tool to execute
            args: Tool arguments
            cliente_context: Client context for authorization
            call_id: Optional call ID for correlation
            validate_access: Whether to validate tool access

        Returns:
            ToolResult with execution outcome
        """
        import time

        call_id = call_id or f"{tool_name}_{int(time.time() * 1000)}"
        start_time = time.time()

        try:
            # Validate access if requested
            if validate_access:
                self._validate_access(tool_name, cliente_context)

            # Get tool callable
            tool_fn = self.tool_callables.get(tool_name)
            if tool_fn is None:
                raise MCPToolNotFoundError(
                    f"Ferramenta '{tool_name}' não encontrada.",
                    tool_name=tool_name,
                )

            # Inject cliente_id into args
            args_with_context = {
                **args,
                "cliente_id": str(cliente_context.id),
            }

            # Execute tool
            if asyncio.iscoroutinefunction(tool_fn):
                result = await tool_fn(**args_with_context)
            else:
                # Run sync function in thread pool
                result = await asyncio.to_thread(tool_fn, **args_with_context)

            duration_ms = (time.time() - start_time) * 1000

            return ToolResult(
                call_id=call_id,
                name=tool_name,
                success=True,
                result=result,
                duration_ms=duration_ms,
            )

        except MCPToolNotFoundError as e:
            return ToolResult(
                call_id=call_id,
                name=tool_name,
                success=False,
                error=e.message,
                error_code=e.code,
            )

        except MCPToolDisabledError as e:
            return ToolResult(
                call_id=call_id,
                name=tool_name,
                success=False,
                error=e.message,
                error_code=e.code,
            )

        except MCPTierAccessError as e:
            return ToolResult(
                call_id=call_id,
                name=tool_name,
                success=False,
                error=e.message,
                error_code=e.code,
            )

        except Exception as e:
            logger.exception(f"Error executing tool {tool_name}: {e}")
            duration_ms = (time.time() - start_time) * 1000
            return ToolResult(
                call_id=call_id,
                name=tool_name,
                success=False,
                error=str(e),
                error_code="EXECUTION_ERROR",
                duration_ms=duration_ms,
            )

    async def execute_parallel(
        self,
        tool_calls: List[ToolCall],
        cliente_context: VizuClientContext,
        max_concurrent: int = 5,
        validate_access: bool = True,
    ) -> List[ToolResult]:
        """
        Execute multiple tools in parallel.

        Args:
            tool_calls: List of ToolCall objects to execute
            cliente_context: Client context for authorization
            max_concurrent: Maximum concurrent executions
            validate_access: Whether to validate tool access

        Returns:
            List of ToolResult objects (same order as input)
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def execute_with_semaphore(tool_call: ToolCall) -> ToolResult:
            async with semaphore:
                return await self.execute_tool(
                    tool_name=tool_call.name,
                    args=tool_call.args,
                    cliente_context=cliente_context,
                    call_id=tool_call.call_id,
                    validate_access=validate_access,
                )

        tasks = [execute_with_semaphore(tc) for tc in tool_calls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to ToolResult
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(
                    ToolResult(
                        call_id=tool_calls[i].call_id or str(i),
                        name=tool_calls[i].name,
                        success=False,
                        error=str(result),
                        error_code="PARALLEL_EXECUTION_ERROR",
                    )
                )
            else:
                final_results.append(result)

        return final_results

    def _validate_access(
        self,
        tool_name: str,
        cliente_context: VizuClientContext,
    ) -> None:
        """Validate that client has access to the tool."""
        # Check if tool is in enabled list
        enabled_tools = cliente_context.get_enabled_tools_list()

        if enabled_tools and tool_name not in enabled_tools:
            raise MCPToolDisabledError(
                f"Ferramenta '{tool_name}' não está habilitada para este cliente.",
                tool_name=tool_name,
            )

        # Check tier if registry available
        if self.tool_registry:
            try:
                from vizu_tool_registry import TierValidator, ToolRegistry

                if isinstance(self.tool_registry, ToolRegistry):
                    tool_meta = self.tool_registry.get_tool(tool_name)
                    if tool_meta and tool_meta.tier_required:
                        from vizu_models.enums import TierCliente

                        client_tier = TierCliente(
                            cliente_context.tier.value
                            if hasattr(cliente_context.tier, "value")
                            else cliente_context.tier
                        )

                        validator = TierValidator()
                        if not validator.can_access_tier(client_tier, tool_meta.tier_required):
                            raise MCPTierAccessError(
                                f"Tier {tool_meta.tier_required.value} necessário para '{tool_name}'.",
                                required_tier=tool_meta.tier_required.value,
                                current_tier=client_tier.value,
                            )
            except ImportError:
                pass  # Tool registry not available


class ToolCallBuilder:
    """Builder for creating ToolCall lists from LLM responses."""

    @staticmethod
    def from_openai_tool_calls(tool_calls: list) -> List[ToolCall]:
        """
        Convert OpenAI-style tool calls to ToolCall objects.

        Args:
            tool_calls: List of OpenAI tool call dicts with 'name', 'arguments', 'id'

        Returns:
            List of ToolCall objects
        """
        import json

        result = []
        for tc in tool_calls:
            args = tc.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}

            result.append(
                ToolCall(
                    name=tc.get("name", tc.get("function", {}).get("name", "")),
                    args=args,
                    call_id=tc.get("id"),
                )
            )
        return result

    @staticmethod
    def from_langchain_tool_calls(tool_calls: list) -> List[ToolCall]:
        """
        Convert LangChain-style tool calls to ToolCall objects.

        Args:
            tool_calls: List of LangChain ToolCall objects or dicts

        Returns:
            List of ToolCall objects
        """
        result = []
        for tc in tool_calls:
            name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")
            args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})
            call_id = tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", None)

            result.append(
                ToolCall(
                    name=name,
                    args=args,
                    call_id=call_id,
                )
            )
        return result
