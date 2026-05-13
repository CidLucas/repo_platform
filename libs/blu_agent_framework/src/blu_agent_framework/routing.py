"""
Routing functions for agent graph edges.
"""

import logging
import re
from typing import Literal

from blu_agent_framework.state import AgentState

logger = logging.getLogger(__name__)

# Matches pure-greeting messages (word boundaries prevent "obrigado pelo contexto"
# from matching and bypassing elicitation).  Only applied to short messages so a
# greeting that also contains a question still goes through the normal path.
_GREETING_RE = re.compile(r"\b(?:oi|ol[aá]|tchau|obrigad[ao])\b", re.IGNORECASE)
_GREETING_MAX_LEN = 60  # chars; longer = likely contains a real question


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
        logger.debug("route_from_init: ended=True -> 'end'")
        return "end"

    # If there are messages, we might need to respond directly
    messages = state.get("messages", [])
    if messages:
        last_message = messages[-1]
        content = getattr(last_message, "content", "")
        if len(content) <= _GREETING_MAX_LEN and _GREETING_RE.search(content):
            logger.debug("route_from_init: greeting detected -> 'respond'")
            return "respond"

    logger.debug(f"route_from_init: -> 'elicit' (messages={len(messages)})")
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


def route_after_enrichment(
    state: AgentState,
) -> Literal["elicit", "respond", "select_skill", "end"]:
    """
    Route after context_enrichment_node — the main fork between simple and complex paths.

    Simple path  (complexity == "simple" or None) → elicit → respond (Phase-4 binding)
    Complex path (complexity == "moderate"/"complex") → select_skill → run_skill → respond
    Greetings bypass elicitation entirely → respond directly.
    """
    if state.get("ended"):
        return "end"

    # Short-circuit for simple greetings — no tool use needed.
    messages = state.get("messages", [])
    if messages:
        content = getattr(messages[-1], "content", "")
        if len(content) <= _GREETING_MAX_LEN and _GREETING_RE.search(content):
            return "respond"

    complexity = state.get("complexity")
    if complexity in ("moderate", "complex"):
        return "select_skill"

    return "elicit"


def route_after_select_skill(state: AgentState) -> Literal["run_skill", "elicit"]:
    """
    Route after select_skill_node.

    A skill was selected → run_skill.
    No match (select_skill cleared current_skill and reset complexity to 'simple') → elicit.
    """
    if state.get("current_skill"):
        return "run_skill"
    return "elicit"


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
