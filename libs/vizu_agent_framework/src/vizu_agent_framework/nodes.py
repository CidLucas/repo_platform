"""
Reusable graph nodes for agent workflows.
"""

import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

from vizu_agent_framework.state import AgentState

logger = logging.getLogger(__name__)


class NodeMetadata:
    """Metadata for a registered node."""

    def __init__(
        self,
        name: str,
        description: str = "",
        category: str = "core",
        inputs: list[str] | None = None,
        outputs: list[str] | None = None,
    ):
        self.name = name
        self.description = description
        self.category = category
        self.inputs = inputs or []
        self.outputs = outputs or []

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "inputs": self.inputs,
            "outputs": self.outputs,
        }


class NodeRegistry:
    """
    Registry for custom node handlers.

    Allows agents to register custom nodes that can be used in AgentBuilder.
    """

    _registry: dict[str, Callable] = {}
    _metadata: dict[str, NodeMetadata] = {}

    @classmethod
    def register(cls, name: str, description: str = "", category: str = "core",
                 inputs: list[str] | None = None, outputs: list[str] | None = None):
        """
        Decorator to register a node handler.

        Usage:
            @NodeRegistry.register("custom_validation", description="Validates order data")
            async def validate_order(state: AgentState) -> dict:
                ...
        """

        def decorator(func: Callable):
            cls._registry[name] = func
            cls._metadata[name] = NodeMetadata(
                name=name,
                description=description or (func.__doc__ or "").strip().split("\n")[0],
                category=category,
                inputs=inputs,
                outputs=outputs,
            )
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

    @classmethod
    def list_nodes_with_metadata(cls) -> list[dict]:
        """List all registered nodes with metadata."""
        result = []
        for name in cls._registry:
            if name in cls._metadata:
                result.append(cls._metadata[name].to_dict())
            else:
                result.append({"name": name, "description": "", "category": "core", "inputs": [], "outputs": []})
        return result


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
    logger.debug(
        f"init_node: session={state.get('session_id')}, messages={len(state.get('messages', []))}"
    )

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
    logger.debug(
        f"elicit_node: session={state.get('session_id')}, pending={state.get('pending_elicitation')}"
    )

    pending = state.get("pending_elicitation")
    response = state.get("elicitation_response")

    # If there's a pending elicitation and user responded
    if pending and response is not None:
        # Process the response
        elicitation_history = state.get("elicitation_history", [])
        elicitation_history.append(
            {
                "elicitation": pending,
                "response": response,
            }
        )

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
    - Executes via MCP executor
    - Stores result in tool_results
    """
    logger.debug(f"Execute tool node: session={state.get('session_id')}")

    tool_name = state.get("tool_to_execute")
    tool_args = state.get("tool_args", {})

    if not tool_name:
        return {"error": "No tool specified for execution"}

    # Note: Actual execution happens via MCPToolExecutor
    # This is a placeholder that will be replaced by AgentBuilder
    logger.debug(f"Executing tool: {tool_name} with args: {tool_args}")

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
    logger.debug(
        f"Generating response with {len(messages)} messages, tool_result={last_tool_result is not None}"
    )

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
    available_tools = client_context.get("available_tools", {})
    tool_names = available_tools.get("enabled_tool_names", []) if available_tools else []
    enriched_metadata = {
        "nome_empresa": client_context.get("nome_empresa", ""),
        "tier": client_context.get("tier", "BASIC"),
        "has_rag": "executar_rag_cliente" in tool_names,
        "has_sql": "executar_sql_agent" in tool_names,
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
            logger.debug(f"[{node_name}] Starting: session={session_id}")
            try:
                result = await func(state)
                logger.debug(f"[{node_name}] Completed: session={session_id}")
                return result
            except Exception as e:
                logger.error(f"[{node_name}] Error: {e}")
                return {"error": str(e)}

        return wrapper

    return decorator


def with_tracing(_trace_name: str):
    """
    Decorator to add Langfuse tracing to a node function.

    Note: In Langfuse SDK v3, tracing is handled via CallbackHandler
    configured in the LLM. This decorator is kept for backward compatibility
    but won't create traces if Langfuse SDK v3 is installed.

    Args:
        _trace_name: Unused in v3, kept for API compatibility
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(state: AgentState) -> dict[str, Any]:
            # Langfuse SDK v3 no longer supports direct trace creation via Langfuse().trace()
            # Tracing is now handled via CallbackHandler in the LLM configuration.
            # This decorator simply passes through to the wrapped function.
            return await func(state)

        return wrapper

    return decorator


# Register built-in nodes with metadata
_BUILTIN_NODES = {
    "init": {
        "handler": init_node,
        "description": "Initialize agent state and increment turn count",
        "category": "core",
        "inputs": ["messages"],
        "outputs": ["turn_count", "error"],
    },
    "elicit": {
        "handler": elicit_node,
        "description": "Handle elicitation flows for collecting user context",
        "category": "core",
        "inputs": ["pending_elicitation", "elicitation_response"],
        "outputs": ["pending_elicitation", "elicitation_history"],
    },
    "execute_tool": {
        "handler": execute_tool_node,
        "description": "Execute a tool call via MCP",
        "category": "core",
        "inputs": ["tool_to_execute", "tool_args"],
        "outputs": ["tool_to_execute", "tool_args"],
    },
    "respond": {
        "handler": respond_node,
        "description": "Generate LLM response from gathered context",
        "category": "core",
        "inputs": ["messages", "last_tool_result"],
        "outputs": ["last_tool_result"],
    },
    "end": {
        "handler": end_node,
        "description": "End the conversation and set the ended flag",
        "category": "core",
        "inputs": ["end_reason"],
        "outputs": ["ended", "end_reason"],
    },
    "error_recovery": {
        "handler": error_recovery_node,
        "description": "Handle errors and attempt recovery",
        "category": "specialized",
        "inputs": ["error"],
        "outputs": ["error", "errors", "metadata"],
    },
    "context_enrichment": {
        "handler": context_enrichment_node,
        "description": "Enrich state with additional client context",
        "category": "specialized",
        "inputs": ["client_context"],
        "outputs": ["metadata"],
    },
    "rate_limit": {
        "handler": rate_limit_node,
        "description": "Check and enforce rate limits",
        "category": "specialized",
        "inputs": ["turn_count", "max_turns"],
        "outputs": ["ended", "end_reason"],
    },
}

for _name, _info in _BUILTIN_NODES.items():
    NodeRegistry._registry[_name] = _info["handler"]
    NodeRegistry._metadata[_name] = NodeMetadata(
        name=_name,
        description=_info["description"],
        category=_info["category"],
        inputs=_info.get("inputs", []),
        outputs=_info.get("outputs", []),
    )
