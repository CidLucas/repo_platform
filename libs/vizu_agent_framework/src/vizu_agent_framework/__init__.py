"""
vizu_agent_framework - Reusable LangGraph agent framework for Vizu.

This library provides:
- AgentBuilder factory for creating agents
- AgentState base class with common fields
- Reusable graph nodes (init, elicit, execute_tool, respond, end)
- MCP tool integration (StreamableHTTP client)
- Redis checkpointing
- Langfuse observability hooks
"""

__version__ = "0.1.0"

from vizu_agent_framework.builder import AgentBuilder
from vizu_agent_framework.checkpointer import RedisCheckpointer
from vizu_agent_framework.config import (
    APPOINTMENT_CONFIG,
    ATENDENTE_CONFIG,
    SUPPORT_CONFIG,
    VENDAS_CONFIG,
    AgentConfig,
)
from vizu_agent_framework.mcp_client import (
    MCPConnectionManager,
    get_mcp_manager,
    initialize_mcp,
)
from vizu_agent_framework.nodes import (
    NodeRegistry,
    elicit_node,
    end_node,
    execute_tool_node,
    init_node,
    respond_node,
)
from vizu_agent_framework.routing import (
    route_from_elicit,
    route_from_tool,
    should_continue,
)
from vizu_agent_framework.state import AgentState, create_initial_state

__all__ = [
    "__version__",
    # Config
    "AgentConfig",
    "ATENDENTE_CONFIG",
    "VENDAS_CONFIG",
    "SUPPORT_CONFIG",
    "APPOINTMENT_CONFIG",
    # State
    "AgentState",
    "create_initial_state",
    # Builder
    "AgentBuilder",
    # Nodes
    "NodeRegistry",
    "init_node",
    "elicit_node",
    "execute_tool_node",
    "respond_node",
    "end_node",
    # Routing
    "route_from_elicit",
    "route_from_tool",
    "should_continue",
    # MCP (StreamableHTTP client)
    "MCPConnectionManager",
    "get_mcp_manager",
    "initialize_mcp",
    # Checkpointing
    "RedisCheckpointer",
]
