"""
vizu_tool_registry.exceptions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Custom exceptions for tool registry operations.
"""


class ToolRegistryError(Exception):
    """Base exception for tool registry errors."""

    pass


class ToolNotFoundError(ToolRegistryError):
    """Raised when a requested tool is not found in the registry."""

    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        super().__init__(f"Tool not found: {tool_name}")


class TierAccessDeniedError(ToolRegistryError):
    """Raised when a client tier doesn't have access to a tool."""

    def __init__(self, tool_name: str, required_tier: str, client_tier: str):
        self.tool_name = tool_name
        self.required_tier = required_tier
        self.client_tier = client_tier
        super().__init__(
            f"Access denied: '{tool_name}' requires tier {required_tier}, "
            f"but client has tier {client_tier}"
        )


class DockerMCPConnectionError(ToolRegistryError):
    """Raised when connection to Docker MCP fails."""

    def __init__(self, integration: str, reason: str):
        self.integration = integration
        self.reason = reason
        super().__init__(f"Docker MCP connection failed for '{integration}': {reason}")


class ToolValidationError(ToolRegistryError):
    """Raised when tool configuration validation fails."""

    def __init__(self, tool_name: str, reason: str):
        self.tool_name = tool_name
        self.reason = reason
        super().__init__(f"Tool validation failed for '{tool_name}': {reason}")
