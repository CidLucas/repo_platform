"""
MCP exceptions for Vizu services.

Provides structured error handling with error codes for MCP operations.
These exceptions can be caught by FastMCP and converted to proper MCP error responses.
"""



class MCPError(Exception):
    """Base exception for all MCP errors."""

    code: str = "MCP_ERROR"
    status_code: int = 500

    def __init__(self, message: str, code: str | None = None, details: dict | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.details = details or {}

    def to_dict(self) -> dict:
        """Convert exception to dictionary for JSON serialization."""
        return {
            "error": True,
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


class MCPAuthError(MCPError):
    """Authentication error - invalid or missing credentials."""

    code = "AUTH_ERROR"
    status_code = 401

    def __init__(self, message: str = "Autenticação necessária", **kwargs):
        super().__init__(message, **kwargs)


class MCPAuthorizationError(MCPError):
    """Authorization error - user authenticated but not authorized."""

    code = "AUTHORIZATION_ERROR"
    status_code = 403

    def __init__(self, message: str = "Acesso não autorizado", **kwargs):
        super().__init__(message, **kwargs)


class MCPToolError(MCPError):
    """Tool execution error."""

    code = "TOOL_ERROR"
    status_code = 500

    def __init__(self, message: str, tool_name: str | None = None, **kwargs):
        super().__init__(message, **kwargs)
        self.tool_name = tool_name
        if tool_name:
            self.details["tool_name"] = tool_name


class MCPContextError(MCPError):
    """Context resolution error - client context not found or invalid."""

    code = "CONTEXT_ERROR"
    status_code = 404

    def __init__(self, message: str = "Contexto do cliente não encontrado", **kwargs):
        super().__init__(message, **kwargs)


class MCPValidationError(MCPError):
    """Validation error - invalid input or parameters."""

    code = "VALIDATION_ERROR"
    status_code = 400

    def __init__(self, message: str = "Dados inválidos", field: str | None = None, **kwargs):
        super().__init__(message, **kwargs)
        if field:
            self.details["field"] = field


class MCPTimeoutError(MCPError):
    """Timeout error - operation took too long."""

    code = "TIMEOUT_ERROR"
    status_code = 504

    def __init__(self, message: str = "Operação expirou", timeout_seconds: float | None = None, **kwargs):
        super().__init__(message, **kwargs)
        if timeout_seconds:
            self.details["timeout_seconds"] = timeout_seconds


class MCPTierAccessError(MCPAuthorizationError):
    """Tier-based access error - tool requires higher tier."""

    code = "TIER_ACCESS_ERROR"

    def __init__(
        self,
        message: str = "Tier insuficiente para esta ferramenta",
        required_tier: str | None = None,
        current_tier: str | None = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        if required_tier:
            self.details["required_tier"] = required_tier
        if current_tier:
            self.details["current_tier"] = current_tier


class MCPToolNotFoundError(MCPError):
    """Tool not found error."""

    code = "TOOL_NOT_FOUND"
    status_code = 404

    def __init__(self, message: str = "Ferramenta não encontrada", tool_name: str | None = None, **kwargs):
        super().__init__(message, **kwargs)
        if tool_name:
            self.details["tool_name"] = tool_name


class MCPToolDisabledError(MCPAuthorizationError):
    """Tool is disabled for this client."""

    code = "TOOL_DISABLED"

    def __init__(self, message: str = "Ferramenta desabilitada para este cliente", tool_name: str | None = None, **kwargs):
        super().__init__(message, **kwargs)
        if tool_name:
            self.details["tool_name"] = tool_name
