"""
Agent state definition using TypedDict for LangGraph compatibility.
"""

from typing import Annotated, Any

from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict

_MAX_MESSAGES = 60  # Rolling window stored in Redis per session


def add_messages(left: list[BaseMessage], right: list[BaseMessage]) -> list[BaseMessage]:
    """Reducer for messages: appends new messages and caps at _MAX_MESSAGES.

    Keeps the most recent messages so the Redis checkpoint never grows unbounded.
    The TokenBudget in respond_node provides a second layer of protection before
    the LLM call itself.
    """
    combined = left + right
    return combined[-_MAX_MESSAGES:] if len(combined) > _MAX_MESSAGES else combined


def merge_dict(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Reducer for dicts: merges right into left."""
    return {**left, **right}


def _cap_errors(left: list[str], right: list[str]) -> list[str]:
    """Reducer for errors: appends new entries, caps at 20 to prevent unbounded growth."""
    combined = left + right
    return combined[-20:] if len(combined) > 20 else combined


def _cap_tool_results(left: list[dict], right: list[dict]) -> list[dict]:
    """Reducer for tool_results: appends and caps at 30 to prevent unbounded growth."""
    combined = left + right
    return combined[-30:] if len(combined) > 30 else combined


def _cap_skill_results(left: list[dict], right: list[dict]) -> list[dict]:
    """Reducer for skill_results: appends and caps at 20 per session."""
    combined = left + right
    return combined[-20:] if len(combined) > 20 else combined


def _list_reducer(left: list | None, right: list | None) -> list:
    """
    Reducer for lists that supports fan-out accumulation and clearing.

    - right is a list → appends to left (accumulates parallel worker results)
    - right is None → returns [] (clears, used on new user turns)
    """
    if right is None:
        return []
    return (left or []) + right


class PendingElicitation(TypedDict, total=False):
    """Elicitation waiting for a user response.

    Stores the information needed to resume tool execution after the user
    replies.  Compatible with both atendente_core (typed) and the framework
    (previously untyped dict).
    """

    elicitation_id: str        # unique correlation ID
    type: str                  # confirmation | selection | text_input | date_time
    message: str               # prompt shown to the user
    options: list[dict[str, Any]] | None   # choices for selection type
    tool_name: str             # tool that raised the elicitation
    tool_args: dict[str, Any]  # original tool arguments
    metadata: dict[str, Any] | None


class ToolCallSendState(TypedDict, total=False):
    """
    State passed to each fan-out tool execution node via LangGraph Send.

    Each Send dispatches one tool call to execute_single_tool_node
    with this minimal state. Results are aggregated back via reducers.
    """

    tool_call: dict[str, Any]  # Single tool call: {name, id, args}
    client_id: str
    session_id: str
    channel: str
    metadata: dict[str, Any]
    available_tools_metadata: list[dict[str, Any]]


class AgentState(TypedDict, total=False):
    """
    Base state for all Blu agents.

    This TypedDict defines the common state fields that all agents share.
    Agent-specific extensions can add additional fields.

    Annotated fields use reducers for proper state updates in LangGraph.
    """

    # =========================================================================
    # Core Identifiers
    # =========================================================================

    session_id: str  # Unique session identifier
    client_id: str  # Client UUID (from context)
    thread_id: str  # LangGraph thread ID for checkpointing
    channel: str  # Channel: "whatsapp", "web", "api"

    # =========================================================================
    # Messages (with reducer for accumulation)
    # =========================================================================

    messages: Annotated[list[BaseMessage], add_messages]

    # =========================================================================
    # Tool Configuration
    # =========================================================================

    available_tools_metadata: list[dict[str, Any]]  # Full tool metadata

    # =========================================================================
    # Elicitation State
    # =========================================================================

    pending_elicitation: PendingElicitation | None  # Current pending elicitation
    elicitation_response: Any | None  # User's response to elicitation
    elicitation_history: list[dict[str, Any]]  # Past elicitations

    # =========================================================================
    # Tool Execution State
    # =========================================================================

    tool_to_execute: str | None  # Next tool to execute (legacy single-tool)
    tool_args: dict[str, Any] | None  # Arguments for next tool (legacy)
    tool_results: Annotated[list[dict[str, Any]], _cap_tool_results]  # Accumulated tool results, capped at 30
    last_tool_result: dict[str, Any] | None  # Most recent result

    # Fan-out tool execution (Send-based parallel dispatch)
    pending_tool_calls: list[dict[str, Any]]  # Tool calls to fan-out via Send

    # =========================================================================
    # Conversation Control
    # =========================================================================

    turn_count: int  # Current turn number
    max_turns: int  # Maximum allowed turns
    sql_attempts: int  # execute_sql calls in current turn (loop guard)
    ended: bool  # Whether conversation has ended
    end_reason: str | None  # Reason for ending

    # =========================================================================
    # Agent Context
    # =========================================================================

    system_prompt: str  # System prompt for LLM
    agent_name: str  # Agent identifier
    agent_role: str  # Agent role description

    # =========================================================================
    # Client Context (from blu_context_service)
    # =========================================================================

    client_context: dict[str, Any]  # Full client context
    nome_empresa: str  # Company name
    tier: str  # Client tier

    # =========================================================================
    # Skill Routing (Agent-as-Skill pattern)
    # =========================================================================

    complexity: str | None         # "simple" | "moderate" | "complex" — set by classify_intent
    current_skill: str | None      # SKILL_REGISTRY key selected by select_skill_node; cleared after run
    skill_results: Annotated[list[dict], _cap_skill_results]  # Accumulated SkillResult dicts, capped at 20

    # =========================================================================
    # Orchestrator Planning (Layer 4 meta-skill)
    # =========================================================================

    # Sequential execution plan — list of steps, each a dict:
    #   {id, skill_slug, task, depends_on, status, result, is_mutation, requires_confirmation}
    # None when agent is not an orchestrator.
    plan: list[dict] | None

    # Results from completed steps: {step_id: result_text}
    # Injected as context into dependent steps by execute_step_node.
    step_results: dict[str, str]

    # Domains identified by parse_intent (e.g. ["analytics", "communication"])
    involved_domains: list[str]

    # Pending user confirmation — set by confirm_node, cleared by parse_intent on response.
    # {type: "plan" | "clarification" | "mutation", message: str}
    pending_confirmation: dict | None

    # User approval state — True=approved, False=rejected, None=not yet asked.
    # Set by parse_intent when it detects a confirmation response.
    confirmed: bool | None

    # Internal: sub-tasks from decompose_node, consumed by plan_node.
    # Not user-visible; cleared after plan is built.
    _sub_tasks: list[dict] | None

    # =========================================================================
    # Error Handling
    # =========================================================================

    error: str | None  # Current error message
    errors: Annotated[list[str], _cap_errors]  # Accumulated errors, capped at 20

    # =========================================================================
    # Agent Memory Context (Shared Business Memory — Pre-flight + Post-flight)
    # =========================================================================

    # Pre-flight context injected before agent execution (DD-PF-08).
    # Structure: {agent_metadata: [...], agent_results: [...], execution_count: int, agent_slug: str}
    # Read by graphs that want historical execution context.
    # Optional — graphs that don't use it ignore the field.
    agent_preflight_context: dict | None

    # Reserved for T1.2 (post-flight): pending post-flight data to write after execution.
    agent_postflight_pending: dict | None

    # =========================================================================
    # Metadata
    # =========================================================================

    metadata: Annotated[dict[str, Any], merge_dict]  # Additional metadata

    # =========================================================================
    # Supervisor-tier fields (atendente_core convergence)
    # =========================================================================

    # Per-request model override (e.g. "gpt-4o" for a specific turn).
    model_override: str | None

    # JWT forwarded to tool calls that require caller authentication.
    user_jwt: str | None

    # Tabular results from SQL queries / worker delegations, kept separate
    # from the LLM context so the frontend can render them interactively.
    structured_data: dict[str, Any] | None
    # Accumulates across parallel fan-out workers; None return clears the list.
    structured_data_list: Annotated[list[dict[str, Any]], _list_reducer]


def create_initial_state(
    session_id: str,
    client_id: str,
    messages: list[BaseMessage] | None = None,
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
        client_id: Client UUID
        messages: Initial messages (optional)
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
        client_id=client_id,
        thread_id=f"{session_id}:{client_id}",
        channel=channel,
        # Messages
        messages=messages or [],
        # Tools
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
        pending_tool_calls=[],
        # Conversation control
        turn_count=0,
        max_turns=max_turns,
        sql_attempts=0,
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
        # Skill routing
        complexity=None,
        current_skill=None,
        skill_results=[],
        # Orchestrator planning
        plan=None,
        step_results={},
        involved_domains=[],
        pending_confirmation=None,
        confirmed=None,
        _sub_tasks=None,
        # Error handling
        error=None,
        errors=[],
        # Agent memory context (pre-flight / post-flight)
        agent_preflight_context=None,
        agent_postflight_pending=None,
        # Metadata
        metadata=metadata or {},
        # Supervisor-tier fields
        model_override=None,
        user_jwt=None,
        structured_data=None,
        structured_data_list=[],
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
    client_id: str
    last_tool_result: dict[str, Any] | None


class ElicitationState(TypedDict, total=False):
    """
    State subset for elicitation handling.
    """

    pending_elicitation: dict[str, Any] | None
    elicitation_response: Any | None
    elicitation_history: list[dict[str, Any]]
