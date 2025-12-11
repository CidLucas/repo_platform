"""
Agent state definition using TypedDict for LangGraph compatibility.
"""

from operator import add
from typing import Annotated, Any

from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict


def add_messages(left: list[BaseMessage], right: list[BaseMessage]) -> list[BaseMessage]:
    """Reducer for messages: appends new messages to existing list."""
    return left + right


def merge_dict(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Reducer for dicts: merges right into left."""
    return {**left, **right}


class AgentState(TypedDict, total=False):
    """
    Base state for all Vizu agents.

    This TypedDict defines the common state fields that all agents share.
    Agent-specific extensions can add additional fields.

    Annotated fields use reducers for proper state updates in LangGraph.
    """

    # =========================================================================
    # Core Identifiers
    # =========================================================================

    session_id: str  # Unique session identifier
    cliente_id: str  # Client UUID (from context)
    thread_id: str  # LangGraph thread ID for checkpointing
    channel: str  # Channel: "whatsapp", "web", "api"

    # =========================================================================
    # Messages (with reducer for accumulation)
    # =========================================================================

    messages: Annotated[list[BaseMessage], add_messages]

    # =========================================================================
    # Tool Configuration
    # =========================================================================

    enabled_tools: list[str]  # List of enabled tool names
    available_tools_metadata: list[dict[str, Any]]  # Full tool metadata

    # =========================================================================
    # Elicitation State
    # =========================================================================

    pending_elicitation: dict[str, Any] | None  # Current pending elicitation
    elicitation_response: Any | None  # User's response to elicitation
    elicitation_history: list[dict[str, Any]]  # Past elicitations

    # =========================================================================
    # Tool Execution State
    # =========================================================================

    tool_to_execute: str | None  # Next tool to execute
    tool_args: dict[str, Any] | None  # Arguments for next tool
    tool_results: Annotated[list[dict[str, Any]], add]  # Accumulated tool results
    last_tool_result: dict[str, Any] | None  # Most recent result

    # =========================================================================
    # Conversation Control
    # =========================================================================

    turn_count: int  # Current turn number
    max_turns: int  # Maximum allowed turns
    ended: bool  # Whether conversation has ended
    end_reason: str | None  # Reason for ending

    # =========================================================================
    # Agent Context
    # =========================================================================

    system_prompt: str  # System prompt for LLM
    agent_name: str  # Agent identifier
    agent_role: str  # Agent role description

    # =========================================================================
    # Client Context (from vizu_context_service)
    # =========================================================================

    client_context: dict[str, Any]  # Full client context
    nome_empresa: str  # Company name
    tier: str  # Client tier

    # =========================================================================
    # Error Handling
    # =========================================================================

    error: str | None  # Current error message
    errors: Annotated[list[str], add]  # Accumulated errors

    # =========================================================================
    # Metadata
    # =========================================================================

    metadata: Annotated[dict[str, Any], merge_dict]  # Additional metadata


def create_initial_state(
    session_id: str,
    cliente_id: str,
    messages: list[BaseMessage] | None = None,
    enabled_tools: list[str] | None = None,
    system_prompt: str = "",
    agent_name: str = "agent",
    agent_role: str = "Assistant",
    max_turns: int = 20,
    channel: str = "api",
    client_context: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> AgentState:
    """
    Create initial agent state with required fields populated.

    Args:
        session_id: Unique session identifier
        cliente_id: Client UUID
        messages: Initial messages (optional)
        enabled_tools: List of enabled tool names
        system_prompt: System prompt for LLM
        agent_name: Agent identifier
        agent_role: Agent role description
        max_turns: Maximum conversation turns
        channel: Communication channel
        client_context: Full client context dict
        metadata: Additional metadata

    Returns:
        AgentState with initial values
    """
    return AgentState(
        # Core identifiers
        session_id=session_id,
        cliente_id=cliente_id,
        thread_id=f"{session_id}:{cliente_id}",
        channel=channel,
        # Messages
        messages=messages or [],
        # Tools
        enabled_tools=enabled_tools or [],
        available_tools_metadata=[],
        # Elicitation
        pending_elicitation=None,
        elicitation_response=None,
        elicitation_history=[],
        # Tool execution
        tool_to_execute=None,
        tool_args=None,
        tool_results=[],
        last_tool_result=None,
        # Conversation control
        turn_count=0,
        max_turns=max_turns,
        ended=False,
        end_reason=None,
        # Agent context
        system_prompt=system_prompt,
        agent_name=agent_name,
        agent_role=agent_role,
        # Client context
        client_context=client_context or {},
        nome_empresa=client_context.get("nome_empresa", "") if client_context else "",
        tier=client_context.get("tier", "BASIC") if client_context else "BASIC",
        # Error handling
        error=None,
        errors=[],
        # Metadata
        metadata=metadata or {},
    )


class MinimalState(TypedDict, total=False):
    """
    Minimal state for simple agents that don't need full state.
    """

    messages: Annotated[list[BaseMessage], add_messages]
    session_id: str
    ended: bool


class ToolExecutionState(TypedDict, total=False):
    """
    State subset for tool execution context.
    """

    tool_to_execute: str
    tool_args: dict[str, Any]
    cliente_id: str
    enabled_tools: list[str]
    last_tool_result: dict[str, Any] | None


class ElicitationState(TypedDict, total=False):
    """
    State subset for elicitation handling.
    """

    pending_elicitation: dict[str, Any] | None
    elicitation_response: Any | None
    elicitation_history: list[dict[str, Any]]
