"""
blu_agent_framework - Reusable LangGraph agent framework for Blu.

This library provides:
- AgentBuilder factory for creating agents
- AgentState base class with common fields
- Reusable graph nodes (init, elicit, execute_tool, respond, end)
- MCP tool integration (StreamableHTTP client)
- Redis checkpointing
- Langfuse observability hooks
"""

__version__ = "0.1.0"

from blu_agent_framework.builder import AgentBuilder
from blu_agent_framework.checkpointer import RedisCheckpointer
from blu_agent_framework.config import (
    APPOINTMENT_CONFIG,
    ATENDENTE_CONFIG,
    SUPPORT_CONFIG,
    VENDAS_CONFIG,
    AgentConfig,
)
from blu_agent_framework.approval import (
    ApprovalEngine,
    ApprovalError,
    ApprovalRequest,
)
from blu_agent_framework.audit import record_audit
from blu_agent_framework.mcp_client import (
    MCPConnectionManager,
    get_mcp_manager,
    initialize_mcp,
)
from blu_agent_framework.nodes import (
    NodeMetadata,
    NodeRegistry,
    collect_tool_results_node,
    elicit_node,
    end_node,
    execute_single_tool_node,
    execute_tool_node,
    fan_out_tool_calls,
    init_node,
    respond_node,
)
from blu_agent_framework.routing import (
    route_from_elicit,
    route_from_tool,
    should_continue,
)
from blu_agent_framework.state import AgentState, ToolCallSendState, create_initial_state

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
    "ToolCallSendState",
    "create_initial_state",
    # Builder
    "AgentBuilder",
    # Nodes
    "NodeRegistry",
    "init_node",
    "elicit_node",
    "execute_tool_node",
    "execute_single_tool_node",
    "collect_tool_results_node",
    "fan_out_tool_calls",
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
    # Approval Engine v1
    "ApprovalEngine",
    "ApprovalError",
    "ApprovalRequest",
    # Audit
    "record_audit",
]
