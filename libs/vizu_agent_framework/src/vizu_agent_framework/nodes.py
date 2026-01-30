"""
Reusable graph nodes for agent workflows.
"""

import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

from vizu_agent_framework.state import AgentState

logger = logging.getLogger(__name__)


class NodeRegistry:
    """
    Registry for custom node handlers.

    Allows agents to register custom nodes that can be used in AgentBuilder.
    """

    _registry: dict[str, Callable] = {}

    @classmethod
    def register(cls, name: str):
        """
        Decorator to register a node handler.

        Usage:
            @NodeRegistry.register("custom_validation")
            async def validate_order(state: AgentState) -> dict:
                ...
        """
        def decorator(func: Callable):
            cls._registry[name] = func
            return func
        return decorator

    @classmethod
    def get(cls, name: str) -> Callable | None:
        """Get registered node handler by name."""
        return cls._registry.get(name)

    @classmethod
    def list_nodes(cls) -> list[str]:
        """List all registered node names."""
        return list(cls._registry.keys())


# =============================================================================
# Built-in Nodes
# =============================================================================


async def init_node(state: AgentState) -> dict[str, Any]:
    """
    Initialize agent state at the start of conversation.

    This node:
    - Increments turn count
    - Validates required fields
    - Sets up initial context
    """
    logger.info(f"init_node called: session={state.get('session_id')}, messages={len(state.get('messages', []))}")

    turn_count = state.get("turn_count", 0) + 1
    max_turns = state.get("max_turns", 20)

    # Check if we've exceeded max turns
    if turn_count > max_turns:
        return {
            "ended": True,
            "end_reason": f"Maximum turns ({max_turns}) exceeded",
            "turn_count": turn_count,
        }

    return {
        "turn_count": turn_count,
        "error": None,  # Clear any previous errors
    }


async def elicit_node(state: AgentState) -> dict[str, Any]:
    """
    Handle elicitation flows.

    This node:
    - Checks for pending elicitations
    - Processes elicitation responses
    - Triggers new elicitations based on strategy
    """
    logger.info(f"elicit_node called: session={state.get('session_id')}, pending={state.get('pending_elicitation')}")

    pending = state.get("pending_elicitation")
    response = state.get("elicitation_response")

    # If there's a pending elicitation and user responded
    if pending and response is not None:
        # Process the response
        elicitation_history = state.get("elicitation_history", [])
        elicitation_history.append({
            "elicitation": pending,
            "response": response,
        })

        return {
            "pending_elicitation": None,
            "elicitation_response": None,
            "elicitation_history": elicitation_history,
        }

    # If there's a pending elicitation without response, wait
    if pending:
        logger.debug(f"Waiting for elicitation response: {pending.get('type')}")
        return {}

    # No pending elicitation - continue to next node
    return {}


async def execute_tool_node(state: AgentState) -> dict[str, Any]:
    """
    Execute a tool call via MCP.

    This node:
    - Gets tool to execute from state
    - Validates tool is in enabled_tools
    - Executes via MCP executor
    - Stores result in tool_results
    """
    logger.debug(f"Execute tool node: session={state.get('session_id')}")

    tool_name = state.get("tool_to_execute")
    tool_args = state.get("tool_args", {})
    enabled_tools = state.get("enabled_tools", [])

    if not tool_name:
        return {"error": "No tool specified for execution"}

    # Validate tool is enabled
    if tool_name not in enabled_tools:
        return {
            "error": f"Tool '{tool_name}' is not enabled for this client",
            "tool_to_execute": None,
            "tool_args": None,
        }

    # Note: Actual execution happens via MCPToolExecutor
    # This is a placeholder that will be replaced by AgentBuilder
    logger.info(f"Executing tool: {tool_name} with args: {tool_args}")

    # Return placeholder - actual execution is wired in AgentBuilder
    return {
        "tool_to_execute": None,
        "tool_args": None,
    }


async def respond_node(state: AgentState) -> dict[str, Any]:
    """
    Generate LLM response.

    This node:
    - Gathers context from state
    - Calls LLM to generate response
    - Appends response to messages
    """
    logger.debug(f"Respond node: session={state.get('session_id')}")

    messages = state.get("messages", [])
    last_tool_result = state.get("last_tool_result")

    # Note: Actual LLM call happens via LLM client
    # This is a placeholder that will be replaced by AgentBuilder
    logger.debug(f"Generating response with {len(messages)} messages, tool_result={last_tool_result is not None}")

    return {
        "last_tool_result": None,  # Clear after processing
    }


async def end_node(state: AgentState) -> dict[str, Any]:
    """
    End the conversation.

    This node:
    - Sets ended flag
    - Logs conversation end
    - Returns final state
    """
    logger.debug(f"End node: session={state.get('session_id')}")

    return {
        "ended": True,
        "end_reason": state.get("end_reason") or "Conversation completed",
    }


# =============================================================================
# Specialized Nodes
# =============================================================================


async def error_recovery_node(state: AgentState) -> dict[str, Any]:
    """
    Handle errors and attempt recovery.
    """
    error = state.get("error")
    errors = state.get("errors", [])

    if error:
        errors.append(error)
        logger.error(f"Agent error: {error}")

        # Attempt recovery based on error type
        if "rate limit" in error.lower():
            return {
                "error": None,
                "errors": errors,
                "metadata": {**state.get("metadata", {}), "retry_after": 5},
            }

    return {"error": None, "errors": errors}


async def context_enrichment_node(state: AgentState) -> dict[str, Any]:
    """
    Enrich state with additional context from client configuration.
    """
    client_context = state.get("client_context", {})

    # Extract useful fields from client context
    enriched_metadata = {
        "nome_empresa": client_context.get("nome_empresa", ""),
        "tier": client_context.get("tier", "BASIC"),
        "has_rag": "executar_rag_cliente" in state.get("enabled_tools", []),
        "has_sql": "executar_sql_agent" in state.get("enabled_tools", []),
    }

    return {
        "metadata": {**state.get("metadata", {}), **enriched_metadata},
    }


async def rate_limit_node(state: AgentState) -> dict[str, Any]:
    """
    Check and enforce rate limits.
    """
    turn_count = state.get("turn_count", 0)
    max_turns = state.get("max_turns", 20)

    if turn_count >= max_turns:
        return {
            "ended": True,
            "end_reason": f"Rate limit: {max_turns} turns reached",
        }

    return {}


# =============================================================================
# Node Decorators
# =============================================================================


def with_logging(node_name: str):
    """
    Decorator to add logging to a node function.
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(state: AgentState) -> dict[str, Any]:
            session_id = state.get("session_id", "unknown")
            logger.info(f"[{node_name}] Starting: session={session_id}")
            try:
                result = await func(state)
                logger.info(f"[{node_name}] Completed: session={session_id}")
                return result
            except Exception as e:
                logger.error(f"[{node_name}] Error: {e}")
                return {"error": str(e)}
        return wrapper
    return decorator


def with_tracing(trace_name: str):
    """
    Decorator to add Langfuse tracing to a node function.
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(state: AgentState) -> dict[str, Any]:
            # Import here to avoid circular dependency
            try:
                from langfuse import Langfuse
                langfuse = Langfuse()
                trace = langfuse.trace(
                    name=trace_name,
                    session_id=state.get("session_id"),
                    metadata={
                        "agent_name": state.get("agent_name"),
                        "turn_count": state.get("turn_count"),
                    },
                )
                result = await func(state)
                trace.update(output=result)
                return result
            except ImportError:
                return await func(state)
        return wrapper
    return decorator


# Register built-in nodes
NodeRegistry._registry.update({
    "init": init_node,
    "elicit": elicit_node,
    "execute_tool": execute_tool_node,
    "respond": respond_node,
    "end": end_node,
    "error_recovery": error_recovery_node,
    "context_enrichment": context_enrichment_node,
    "rate_limit": rate_limit_node,
})
