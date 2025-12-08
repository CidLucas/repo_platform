"""
Routing functions for agent graph edges.
"""

import logging
from typing import Literal

from vizu_agent_framework.state import AgentState

logger = logging.getLogger(__name__)


# Type aliases for routing
ElicitRoutes = Literal["needs_tool", "needs_elicitation", "ready_to_respond", "end"]
ToolRoutes = Literal["success", "error", "needs_elicitation", "end"]
ContinueRoutes = Literal["continue", "end"]


def route_from_elicit(state: AgentState) -> ElicitRoutes:
    """
    Route after elicitation node.

    Returns:
        - "needs_tool": Tool execution is required
        - "needs_elicitation": Waiting for user input
        - "ready_to_respond": Generate response
        - "end": End conversation
    """
    # Check if conversation should end
    if state.get("ended"):
        return "end"

    # Check for pending elicitation
    if state.get("pending_elicitation"):
        return "needs_elicitation"

    # Check if a tool needs to be executed
    if state.get("tool_to_execute"):
        return "needs_tool"

    # Default: generate response
    return "ready_to_respond"


def route_from_tool(state: AgentState) -> ToolRoutes:
    """
    Route after tool execution node.

    Returns:
        - "success": Tool executed successfully
        - "error": Tool execution failed
        - "needs_elicitation": Tool requires user confirmation
        - "end": End conversation
    """
    # Check if conversation should end
    if state.get("ended"):
        return "end"

    # Check for errors
    if state.get("error"):
        return "error"

    # Check for pending elicitation (tool may have triggered one)
    if state.get("pending_elicitation"):
        return "needs_elicitation"

    # Tool executed successfully
    return "success"


def should_continue(state: AgentState) -> ContinueRoutes:
    """
    Determine if conversation should continue.

    Returns:
        - "continue": Continue processing
        - "end": End conversation
    """
    # Explicit end flag
    if state.get("ended"):
        logger.debug(f"Ending: {state.get('end_reason', 'unknown')}")
        return "end"

    # Max turns exceeded
    turn_count = state.get("turn_count", 0)
    max_turns = state.get("max_turns", 20)
    if turn_count >= max_turns:
        logger.debug(f"Ending: max turns ({max_turns}) exceeded")
        return "end"

    # Too many errors
    errors = state.get("errors", [])
    if len(errors) >= 3:
        logger.debug(f"Ending: too many errors ({len(errors)})")
        return "end"

    return "continue"


def route_from_init(state: AgentState) -> Literal["elicit", "respond", "end"]:
    """
    Route after init node.

    Returns:
        - "elicit": Start elicitation flow
        - "respond": Skip to response (for simple queries)
        - "end": End conversation
    """
    if state.get("ended"):
        return "end"

    # If there are messages, we might need to respond directly
    messages = state.get("messages", [])
    if len(messages) > 0:
        # Check if this is a simple query that doesn't need elicitation
        last_message = messages[-1]
        content = getattr(last_message, "content", "").lower()

        # Simple greetings or farewells can skip elicitation
        simple_patterns = ["oi", "olá", "tchau", "obrigado", "thanks"]
        if any(pattern in content for pattern in simple_patterns):
            return "respond"

    return "elicit"


def route_from_respond(state: AgentState) -> Literal["init", "end"]:
    """
    Route after respond node.

    Returns:
        - "init": Continue conversation (loop back) - only for multi-turn within same request
        - "end": End conversation (default for HTTP request/response pattern)
    """
    if state.get("ended"):
        return "end"

    # Check if there are pending tool calls that need to be executed
    if state.get("tool_to_execute"):
        return "init"

    # Check for pending elicitation that needs user input
    if state.get("pending_elicitation"):
        return "end"  # Return to client with pending elicitation

    # Check if max turns reached
    turn_count = state.get("turn_count", 0)
    max_turns = state.get("max_turns", 20)
    if turn_count >= max_turns:
        return "end"

    # Default: end after generating response
    # The next user message will start a new invocation
    return "end"


def route_on_error(state: AgentState) -> Literal["recover", "respond", "end"]:
    """
    Route when an error occurs.

    Returns:
        - "recover": Attempt error recovery
        - "respond": Generate error response
        - "end": End conversation
    """
    error = state.get("error", "")
    errors = state.get("errors", [])

    # Critical errors should end immediately
    critical_patterns = ["authentication", "unauthorized", "forbidden"]
    if any(pattern in error.lower() for pattern in critical_patterns):
        return "end"

    # Too many errors
    if len(errors) >= 3:
        return "end"

    # Recoverable errors
    recoverable_patterns = ["timeout", "rate limit", "temporarily"]
    if any(pattern in error.lower() for pattern in recoverable_patterns):
        return "recover"

    # Default: generate error response
    return "respond"


def route_on_elicitation(state: AgentState) -> Literal["wait", "process", "timeout"]:
    """
    Route during elicitation wait.

    Returns:
        - "wait": Continue waiting for response
        - "process": Response received, process it
        - "timeout": Elicitation timed out
    """
    pending = state.get("pending_elicitation")
    response = state.get("elicitation_response")

    if not pending:
        return "process"  # No pending elicitation

    if response is not None:
        return "process"  # Response received

    # Check for timeout (would need timestamp in pending)
    # For now, just wait
    return "wait"
