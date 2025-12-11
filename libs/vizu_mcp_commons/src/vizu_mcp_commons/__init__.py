"""
vizu_mcp_commons - Common MCP utilities for Vizu services.

This library provides shared infrastructure for MCP-based services including
authentication, dependency injection, middleware, and tool execution.
"""

__version__ = "0.1.0"

# Core exports
from vizu_mcp_commons.auth import (
    TokenClaims,
    TokenValidator,
)
from vizu_mcp_commons.dependencies import (
    DependencyContainer,
    get_context_service,
    get_db_session,
    get_redis_client,
)
from vizu_mcp_commons.exceptions import (
    MCPAuthError,
    MCPAuthorizationError,
    MCPContextError,
    MCPError,
    MCPTimeoutError,
    MCPToolError,
    MCPValidationError,
)
from vizu_mcp_commons.tool_executor import (
    ToolCall,
    ToolExecutor,
    ToolResult,
)

__all__ = [
    "__version__",
    # Exceptions
    "MCPError",
    "MCPAuthError",
    "MCPAuthorizationError",
    "MCPToolError",
    "MCPContextError",
    "MCPValidationError",
    "MCPTimeoutError",
    # Auth
    "TokenValidator",
    "TokenClaims",
    # Dependencies
    "get_context_service",
    "get_redis_client",
    "get_db_session",
    "DependencyContainer",
    # Tool Execution
    "ToolExecutor",
    "ToolCall",
    "ToolResult",
]
