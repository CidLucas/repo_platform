"""
Reusable graph nodes for agent workflows.
"""

import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

from langgraph.types import Send

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


# =============================================================================
# Fan-out Tool Execution (Send-based parallel dispatch)
# =============================================================================


def fan_out_tool_calls(state: AgentState) -> list[Send]:
    """
    Fan-out dispatcher: returns a list of Send objects for parallel tool execution.

    Use as a conditional edge function. Each pending tool call is dispatched
    to the 'execute_single_tool' node with its own state slice.

    If no pending tool calls exist, returns an empty list (no fan-out).

    Usage in graph:
        graph.add_conditional_edges("supervisor", fan_out_tool_calls, ["execute_single_tool"])
    """
    pending = state.get("pending_tool_calls", [])
    if not pending:
        logger.debug("fan_out_tool_calls: no pending tool calls")
        return []

    sends = []
    for tool_call in pending:
        sends.append(
            Send(
                "execute_single_tool",
                {
                    "tool_call": tool_call,
                    "cliente_id": state.get("cliente_id", ""),
                    "session_id": state.get("session_id", ""),
                    "channel": state.get("channel", "api"),
                    "metadata": state.get("metadata", {}),
                    "available_tools_metadata": state.get("available_tools_metadata", []),
                },
            )
        )

    logger.info(
        f"fan_out_tool_calls: dispatching {len(sends)} parallel tool calls: "
        f"{[tc.get('name', 'unknown') for tc in pending]}"
    )
    return sends


async def execute_single_tool_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Execute a single tool call dispatched via Send (fan-out).

    This node receives a ToolCallSendState with a single tool_call
    and returns results that are aggregated back via reducers.

    Note: Actual execution is wired in AgentBuilder._create_single_tool_executor_node().
    This is a placeholder.
    """
    tool_call = state.get("tool_call", {})
    tool_name = tool_call.get("name", "unknown")

    logger.debug(f"execute_single_tool_node: {tool_name}")

    # Placeholder - actual execution injected by AgentBuilder
    return {
        "tool_results": [{"tool_name": tool_name, "error": "Not wired to executor"}],
    }


async def collect_tool_results_node(state: AgentState) -> dict[str, Any]:
    """
    Fan-in node: collects results from parallel tool executions.

    This node runs after all Send-dispatched execute_single_tool nodes complete.
    Results are already aggregated by the reducer on tool_results and messages.
    This node clears pending_tool_calls and sets last_tool_result.
    """
    tool_results = state.get("tool_results", [])
    logger.debug(f"collect_tool_results_node: {len(tool_results)} results collected")

    # Set last_tool_result to the most recent result
    last_result = tool_results[-1] if tool_results else None

    return {
        "pending_tool_calls": [],  # Clear after fan-out complete
        "last_tool_result": last_result,
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
    "execute_single_tool": {
        "handler": execute_single_tool_node,
        "description": "Execute a single tool call dispatched via Send (fan-out)",
        "category": "core",
        "inputs": ["tool_call"],
        "outputs": ["tool_results", "messages"],
    },
    "collect_tool_results": {
        "handler": collect_tool_results_node,
        "description": "Fan-in: collect results from parallel tool executions",
        "category": "core",
        "inputs": ["tool_results"],
        "outputs": ["pending_tool_calls", "last_tool_result"],
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


# =============================================================================
# RFQ Workflow Nodes (Phase 2)
# =============================================================================


@NodeRegistry.register(
    "rfq_wait_responses",
    description="Poll rfq_requests status and route to follow-up or optimization",
    category="rfq",
    inputs=["session_id", "metadata"],
    outputs=["rfq_poll_result", "metadata"],
)
async def rfq_wait_responses_node(state: AgentState) -> dict[str, Any]:
    """
    Check how many RFQ responses are in. Routes to:
    - 'optimize' if all responded or deadline passed
    - 'follow_up' if responses pending and reminder thresholds hit
    - 'wait' if still within deadline window
    """
    from datetime import datetime

    metadata = state.get("metadata", {})
    session_id = state.get("session_id")

    if not session_id:
        return {"rfq_poll_result": "error", "error": "No session_id in state"}

    try:
        from vizu_supabase_client import get_supabase_client

        db = get_supabase_client()
        result = db.table("rfq_requests").select(
            "id,status,deadline,follow_up_count"
        ).eq("session_id", session_id).execute()

        rfqs = result.data or []
        if not rfqs:
            return {"rfq_poll_result": "no_rfqs"}

        now = datetime.now(datetime.UTC)
        total = len(rfqs)
        responded = sum(1 for r in rfqs if r["status"] == "responded")
        pending = [r for r in rfqs if r["status"] in ("sent", "pending")]

        # All responded → optimize
        if responded == total:
            logger.info(f"[rfq_wait] All {total} RFQs responded → optimize")
            return {"rfq_poll_result": "optimize", "metadata": {**metadata, "rfq_responded": responded, "rfq_total": total}}

        # Check deadlines
        expired = []
        needs_follow_up = []
        for rfq in pending:
            deadline_str = rfq.get("deadline")
            if not deadline_str:
                continue
            deadline = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
            hours_left = (deadline - now).total_seconds() / 3600
            follow_ups = rfq.get("follow_up_count", 0) or 0

            if hours_left <= 0:
                expired.append(rfq["id"])
            elif hours_left <= 2 and follow_ups < 2:
                needs_follow_up.append(rfq["id"])
            elif hours_left <= 12 and follow_ups < 1:
                needs_follow_up.append(rfq["id"])

        # Mark expired
        if expired:
            for rfq_id in expired:
                db.table("rfq_requests").update(
                    {"status": "expired"}
                ).eq("id", rfq_id).execute()
            logger.info(f"[rfq_wait] {len(expired)} RFQs expired")

        # If some responded + rest expired → optimize with partial
        active_pending = [r for r in pending if r["id"] not in expired]
        if not active_pending and responded > 0:
            logger.info(f"[rfq_wait] {responded}/{total} responded, rest expired → optimize")
            return {
                "rfq_poll_result": "optimize",
                "metadata": {**metadata, "rfq_responded": responded, "rfq_total": total, "partial": True},
            }

        # Follow-up needed
        if needs_follow_up:
            return {
                "rfq_poll_result": "follow_up",
                "metadata": {**metadata, "rfq_follow_up_ids": needs_follow_up},
            }

        # Still waiting
        return {
            "rfq_poll_result": "wait",
            "metadata": {**metadata, "rfq_responded": responded, "rfq_pending": len(active_pending)},
        }

    except Exception as e:
        logger.error(f"[rfq_wait] Error polling RFQ status: {e}")
        return {"rfq_poll_result": "error", "error": str(e)}


@NodeRegistry.register(
    "rfq_follow_up",
    description="Send follow-up reminders for pending RFQs at T-12h and T-2h",
    category="rfq",
    inputs=["metadata"],
    outputs=["metadata"],
)
async def rfq_follow_up_node(state: AgentState) -> dict[str, Any]:
    """
    Send reminder messages for RFQs approaching deadline.
    Increments follow_up_count to avoid duplicate reminders.
    """
    from datetime import datetime

    metadata = state.get("metadata", {})
    follow_up_ids = metadata.get("rfq_follow_up_ids", [])

    if not follow_up_ids:
        return {"metadata": metadata}

    try:
        from vizu_supabase_client import get_supabase_client

        db = get_supabase_client()
        now = datetime.now(datetime.UTC)
        reminded = []

        for rfq_id in follow_up_ids:
            rfq_result = db.table("rfq_requests").select(
                "id,supplier_id,follow_up_count,deadline,communication_channel,"
                "supplier_roster(name,contact_phone,contact_email)"
            ).eq("id", rfq_id).maybe_single().execute()

            rfq = rfq_result.data
            if not rfq:
                continue

            follow_ups = (rfq.get("follow_up_count") or 0) + 1
            supplier_info = rfq.get("supplier_roster") or {}
            supplier_name = supplier_info.get("name", "Fornecedor")
            channel = rfq.get("communication_channel", "mock")

            deadline_str = rfq.get("deadline", "")
            hours_left = 0
            if deadline_str:
                deadline = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
                hours_left = max(0, (deadline - now).total_seconds() / 3600)

            # Send follow-up via appropriate channel
            if channel == "whatsapp":
                phone = supplier_info.get("contact_phone")
                if phone:
                    try:
                        from vizu_twilio_client import TwilioClient
                        from vizu_twilio_client.config import get_twilio_settings

                        twilio = TwilioClient(get_twilio_settings())
                        msg = (
                            f"Olá {supplier_name}! Gentil lembrete: sua cotação vence em "
                            f"{hours_left:.0f}h. Por favor, envie sua resposta o mais breve possível."
                        )
                        twilio.send_whatsapp(to=phone, body=msg)
                    except Exception as e:
                        logger.warning(f"[rfq_follow_up] WhatsApp send failed for {supplier_name}: {e}")

            # Update follow-up count
            db.table("rfq_requests").update({
                "follow_up_count": follow_ups,
                "updated_at": now.isoformat(),
            }).eq("id", rfq_id).execute()

            reminded.append(supplier_name)
            logger.info(f"[rfq_follow_up] Reminder #{follow_ups} sent to {supplier_name} ({channel})")

        updated_meta = {**metadata}
        updated_meta.pop("rfq_follow_up_ids", None)
        updated_meta["rfq_last_follow_up"] = reminded

        return {"metadata": updated_meta}

    except Exception as e:
        logger.error(f"[rfq_follow_up] Error sending follow-ups: {e}")
        return {"metadata": metadata, "error": str(e)}
