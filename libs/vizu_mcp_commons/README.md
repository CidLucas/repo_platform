# vizu_mcp_commons

> ⚠️ **DEPRECATED**: This library is not actively used. Services now use the MCP client from `vizu_agent_framework` instead. This library may be removed in a future version.

Common MCP utilities for Vizu services including authentication, dependencies, middleware, and tool execution.

## Purpose

This library centralizes shared MCP infrastructure that is used by multiple services:
- `tool_pool_api` - Main MCP server
- `atendente_core` - Primary agent service
- Future agents (vendas, support, etc.)

## Features

### Authentication (`auth.py`)
- `TokenValidator` - JWT validation and claims extraction
- `MCPTokenExtractor` - Extract tokens from MCP context

### Dependencies (`dependencies.py`)
- Shared dependency injection utilities
- Context service factory with connection pooling
- Redis pool management

### Exceptions (`exceptions.py`)
- Common MCP exceptions with error codes
- `MCPAuthError` - Authentication failures
- `MCPAuthorizationError` - Authorization failures
- `MCPToolError` - Tool execution failures

### Middleware (`middleware.py`)
- `MCPAuthMiddleware` - Request-level authentication
- `inject_cliente_context` - Decorator for context injection

### Tool Executor (`tool_executor.py`)
- `ToolExecutor` - Execute tools with context injection
- Tier validation integration
- Parallel execution support

### Resource Loader (`resource_loader.py`)
- Dynamic resource loading from database
- Prompt template resolution
- Client-specific resource filtering

## Installation

```bash
poetry add vizu_mcp_commons
```

## Usage

### Token Validation
```python
from vizu_mcp_commons import TokenValidator

validator = TokenValidator(jwt_secret="your-secret")
claims = validator.validate("your-jwt-token")
cliente_id = claims.cliente_id
```

### Context Injection Middleware
```python
from vizu_mcp_commons.middleware import inject_cliente_context
from vizu_mcp_commons.dependencies import get_context_service

@inject_cliente_context(get_context_service)
async def my_tool(query: str, *, cliente_context: VizuClientContext) -> str:
    # cliente_context is automatically injected
    return f"Processing for {cliente_context.nome_cliente}"
```

### Tool Executor
```python
from vizu_mcp_commons import ToolExecutor

executor = ToolExecutor(context_service, tool_registry)

# Execute single tool
result = await executor.execute_tool(
    tool_name="executar_rag_cliente",
    args={"query": "What are your products?"},
    cliente_context=context
)

# Execute multiple tools in parallel
results = await executor.execute_parallel([
    ToolCall(name="tool1", args={"arg": "value"}),
    ToolCall(name="tool2", args={"arg": "value"}),
])
```

## Dependencies

- `vizu_models` - Shared data types
- `vizu_db_connector` - Database connection
- `vizu_context_service` - Client context management
- `vizu_auth` - Core authentication utilities
- `vizu_tool_registry` - Tool metadata and validation
