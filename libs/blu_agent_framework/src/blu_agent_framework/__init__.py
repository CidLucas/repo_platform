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

from __future__ import annotations

__version__ = "0.1.0"

from blu_agent_framework.builder import AgentBuilder
from blu_agent_framework.checkpointer import RedisCheckpointer, create_checkpointer
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
from blu_agent_framework.registry import AgentTypeConfig, AgentTypeRegistry
from blu_agent_framework.state import AgentState, PendingElicitation, ToolCallSendState, create_initial_state
from blu_agent_framework.skills import (
    SKILL_REGISTRY,
    SkillDefinition,
    SkillTurnLimitError,
)
from blu_agent_framework.skill_factory import (
    SkillFactory,
    SkillResult,
)
from blu_agent_framework.supervisor import (
    WorkerResult,
    WorkerTurnLimitError,
)

# GOAL: Hook de handoff entre agentes na shared memory
# BEHAVIOR: B4 — Criar handoff/__init__.py com exports
# DECISÃO: create_new
# Implementação mínima para teste RED passar (GREEN)
from blu_agent_framework import handoff

__all__ = [
    "handoff",
    "__version__",
    # Config
    "AgentConfig",
    "ATENDENTE_CONFIG",
    "VENDAS_CONFIG",
    "SUPPORT_CONFIG",
    "APPOINTMENT_CONFIG",
    # Registry
    "AgentTypeConfig",
    "AgentTypeRegistry",
    # State
    "AgentState",
    "PendingElicitation",
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
    "create_checkpointer",
    # Approval Engine v1
    "ApprovalEngine",
    "ApprovalError",
    "ApprovalRequest",
    # Audit
    "record_audit",
    # Skills (Agent-as-Skill pattern)
    "SkillDefinition",
    "SkillTurnLimitError",
    "SKILL_REGISTRY",
    "SkillFactory",
    "SkillResult",
    # Supervisor / worker result types
    "WorkerResult",
    "WorkerTurnLimitError",
]
