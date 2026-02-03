"""
Agent builder factory for creating LangGraph agents.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.graph import CompiledGraph

from vizu_agent_framework.checkpointer import RedisCheckpointer
from vizu_agent_framework.config import AgentConfig
from vizu_agent_framework.mcp_executor import MCPToolExecutor
from vizu_agent_framework.nodes import (
    NodeRegistry,
)
from vizu_agent_framework.routing import (
    route_from_elicit,
    route_from_init,
    route_from_respond,
    route_from_tool,
)
from vizu_agent_framework.state import AgentState

logger = logging.getLogger(__name__)


@dataclass
class EdgeDefinition:
    """Definition of a graph edge."""

    from_node: str
    to_node: str
    is_conditional: bool = False
    router: Callable | None = None
    routes: dict[str, str] = field(default_factory=dict)


class AgentBuilder:
    """
    Factory for creating LangGraph agents with shared patterns.

    Usage:
        config = AgentConfig(
            name="my_agent",
            role="My Role",
            enabled_tools=["tool1", "tool2"],
        )

        builder = AgentBuilder(config)
        agent = builder.build()

        result = await agent.ainvoke({
            "messages": [...],
            "session_id": "...",
        })
    """

    def __init__(
        self,
        config: AgentConfig,
        mcp_executor: MCPToolExecutor | None = None,
        checkpointer: RedisCheckpointer | None = None,
    ):
        """
        Initialize builder.

        Args:
            config: Agent configuration
            mcp_executor: Optional MCP executor (created if None)
            checkpointer: Optional Redis checkpointer (created if None)
        """
        self.config = config
        self.mcp_executor = mcp_executor
        self.checkpointer = checkpointer

        # Graph construction state
        self._graph = StateGraph(AgentState)
        self._nodes: dict[str, Callable] = {}
        self._edges: list[EdgeDefinition] = []
        self._custom_nodes: dict[str, Callable] = {}

        # LLM client (set via with_llm)
        self._llm_client = None

        # Langfuse configuration
        self._langfuse_enabled = config.use_langfuse
        self._langfuse_session_id: str | None = None
        self._langfuse_user_id: str | None = None
        self._langfuse_metadata: dict[str, Any] = {}

    # =========================================================================
    # Configuration Methods (Fluent API)
    # =========================================================================

    def with_llm(self, llm_client: Any) -> "AgentBuilder":
        """
        Set LLM client for response generation.

        Args:
            llm_client: LangChain-compatible LLM client

        Returns:
            Self for chaining
        """
        self._llm_client = llm_client
        return self

    def with_mcp(self, mcp_executor: MCPToolExecutor) -> "AgentBuilder":
        """
        Set MCP executor for tool execution.

        Args:
            mcp_executor: MCPToolExecutor instance

        Returns:
            Self for chaining
        """
        self.mcp_executor = mcp_executor
        return self

    def with_checkpointer(self, checkpointer: RedisCheckpointer) -> "AgentBuilder":
        """
        Set Redis checkpointer for state persistence.

        Args:
            checkpointer: RedisCheckpointer instance

        Returns:
            Self for chaining
        """
        self.checkpointer = checkpointer
        return self

    def with_langfuse(
        self,
        session_id: str | None = None,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "AgentBuilder":
        """
        Configure Langfuse observability.

        Args:
            session_id: Session identifier for tracing
            user_id: User identifier for tracing
            metadata: Additional metadata for traces

        Returns:
            Self for chaining
        """
        self._langfuse_enabled = True
        self._langfuse_session_id = session_id
        self._langfuse_user_id = user_id
        self._langfuse_metadata = metadata or {}
        return self

    # =========================================================================
    # Graph Construction Methods
    # =========================================================================

    def add_node(
        self,
        name: str,
        handler: str | Callable,
    ) -> "AgentBuilder":
        """
        Add a node to the graph.

        Args:
            name: Node name
            handler: Either a registered node name (str) or a callable

        Returns:
            Self for chaining
        """
        if isinstance(handler, str):
            # Look up in registry
            registered = NodeRegistry.get(handler)
            if not registered:
                raise ValueError(f"Node '{handler}' not found in registry")
            self._nodes[name] = registered
        else:
            self._nodes[name] = handler

        return self

    def add_edge(self, from_node: str, to_node: str) -> "AgentBuilder":
        """
        Add a simple edge between nodes.

        Args:
            from_node: Source node name
            to_node: Target node name

        Returns:
            Self for chaining
        """
        self._edges.append(EdgeDefinition(
            from_node=from_node,
            to_node=to_node,
        ))
        return self

    def add_conditional_edge(
        self,
        from_node: str,
        router: Callable,
        routes: dict[str, str],
    ) -> "AgentBuilder":
        """
        Add a conditional edge with routing logic.

        Args:
            from_node: Source node name
            router: Function that returns route key
            routes: Dict mapping route keys to target nodes

        Returns:
            Self for chaining
        """
        self._edges.append(EdgeDefinition(
            from_node=from_node,
            to_node="",  # Not used for conditional
            is_conditional=True,
            router=router,
            routes=routes,
        ))
        return self

    def use_default_graph(self) -> "AgentBuilder":
        """
        Use the default agent graph structure.

        Default structure:
            START -> init -> elicit -> [route] -> execute_tool | respond
            execute_tool -> respond
            respond -> [should_continue] -> init | END

        Returns:
            Self for chaining
        """
        # Add default nodes
        self.add_node("init", "init")
        self.add_node("elicit", "elicit")
        self.add_node("execute_tool", "execute_tool")
        self.add_node("respond", "respond")
        self.add_node("end", "end")

        # Add edges
        self.add_edge(START, "init")
        self.add_conditional_edge(
            "init",
            route_from_init,
            {
                "elicit": "elicit",
                "respond": "respond",
                "end": "end",
            },
        )
        self.add_conditional_edge(
            "elicit",
            route_from_elicit,
            {
                "needs_tool": "execute_tool",
                "needs_elicitation": "elicit",  # Wait loop
                "ready_to_respond": "respond",
                "end": "end",
            },
        )
        self.add_conditional_edge(
            "execute_tool",
            route_from_tool,
            {
                "success": "respond",
                "error": "respond",
                "needs_elicitation": "elicit",
                "end": "end",
            },
        )
        self.add_conditional_edge(
            "respond",
            route_from_respond,
            {
                "init": "init",
                "end": "end",
            },
        )
        self.add_edge("end", END)

        return self

    # =========================================================================
    # Build Method
    # =========================================================================

    def build(self) -> CompiledGraph:
        """
        Build and compile the agent graph.

        Returns:
            CompiledGraph ready for invocation
        """
        # If no nodes added, use default graph
        if not self._nodes:
            self.use_default_graph()

        # Wrap nodes with MCP and LLM integration
        wrapped_nodes = self._wrap_nodes()

        # Add nodes to graph
        for name, handler in wrapped_nodes.items():
            self._graph.add_node(name, handler)

        # Add edges
        for edge in self._edges:
            if edge.is_conditional:
                self._graph.add_conditional_edges(
                    edge.from_node,
                    edge.router,
                    edge.routes,
                )
            elif edge.from_node == START:
                self._graph.add_edge(START, edge.to_node)
            elif edge.to_node == END:
                self._graph.add_edge(edge.from_node, END)
            else:
                self._graph.add_edge(edge.from_node, edge.to_node)

        # Compile with checkpointer if available
        compile_kwargs = {}
        if self.checkpointer:
            compile_kwargs["checkpointer"] = self.checkpointer

        compiled = self._graph.compile(**compile_kwargs)

        logger.debug(
            f"Built agent '{self.config.name}' with "
            f"{len(wrapped_nodes)} nodes and {len(self._edges)} edges"
        )

        return compiled

    def _wrap_nodes(self) -> dict[str, Callable]:
        """
        Wrap nodes with MCP executor and LLM client injection.
        """
        wrapped = {}

        for name, handler in self._nodes.items():
            if name == "execute_tool":
                wrapped[name] = self._create_tool_executor_node(handler)
            elif name == "respond":
                wrapped[name] = self._create_respond_node(handler)
            else:
                wrapped[name] = handler

        return wrapped

    def _create_tool_executor_node(self, original_handler: Callable) -> Callable:
        """
        Create tool executor node with MCP integration.
        """
        mcp_executor = self.mcp_executor or MCPToolExecutor(
            mcp_url=self.config.mcp_url,
            timeout=self.config.timeout_seconds,
        )

        async def tool_executor_node(state: AgentState) -> dict[str, Any]:
            tool_name = state.get("tool_to_execute")
            tool_args = state.get("tool_args", {})

            if not tool_name:
                return {"error": "No tool specified"}

            # Validate tool is enabled
            enabled_tools = state.get("enabled_tools", [])
            if tool_name not in enabled_tools:
                return {
                    "error": f"Tool '{tool_name}' not enabled",
                    "tool_to_execute": None,
                }

            # Build context
            context = {
                "cliente_id": state.get("cliente_id", ""),
                "session_id": state.get("session_id", ""),
                "channel": state.get("channel", "api"),
            }

            # Execute tool
            result = await mcp_executor.execute(tool_name, tool_args, context)

            return {
                "tool_to_execute": None,
                "tool_args": None,
                "last_tool_result": result.to_dict(),
                "tool_results": [result.to_dict()],
                "error": result.error if not result.success else None,
            }

        return tool_executor_node

    def _create_respond_node(self, original_handler: Callable) -> Callable:
        """
        Create respond node with LLM integration.
        """
        llm_client = self._llm_client
        logger.debug(f"Creating respond node with llm_client={llm_client is not None}")

        async def respond_node(state: AgentState) -> dict[str, Any]:
            from langchain_core.messages import AIMessage

            logger.debug(f"respond_node: llm_client={llm_client is not None}")

            messages = state.get("messages", [])
            system_prompt = state.get("system_prompt", "")
            last_tool_result = state.get("last_tool_result")

            if not llm_client:
                # Fallback: generate a simple response without LLM
                logger.warning("No LLM client configured - using fallback response")

                # If we have a tool result, format it as the response
                if last_tool_result:
                    result_text = last_tool_result.get("result", "")
                    if isinstance(result_text, dict):
                        import json
                        result_text = json.dumps(result_text, ensure_ascii=False, indent=2)
                    fallback_response = f"Resultado: {result_text}"
                else:
                    fallback_response = "Desculpe, não consegui processar sua solicitação. Por favor, tente novamente."

                return {
                    "messages": [AIMessage(content=fallback_response)],
                    "last_tool_result": None,
                    "ended": True,  # End conversation after fallback
                }

            # Build messages for LLM
            from langchain_core.messages import SystemMessage

            llm_messages = []

            if system_prompt:
                llm_messages.append(SystemMessage(content=system_prompt))

            llm_messages.extend(messages)

            # Add tool result as context
            if last_tool_result:
                tool_context = f"\n\nTool Result ({last_tool_result.get('tool_name')}):\n"
                tool_context += str(last_tool_result.get("result", ""))
                llm_messages.append(SystemMessage(content=tool_context))

            # Generate response
            try:
                response = await llm_client.ainvoke(llm_messages)
                return {
                    "messages": [AIMessage(content=response.content)],
                    "last_tool_result": None,
                }
            except Exception as e:
                logger.exception("LLM invocation failed")
                return {
                    "messages": [AIMessage(content="Desculpe, ocorreu um erro ao processar sua solicitação.")],
                    "error": str(e),
                    "last_tool_result": None,
                    "ended": True,
                }

        return respond_node


# =============================================================================
# Convenience Functions
# =============================================================================


def create_agent(
    config: AgentConfig,
    redis_client: Any | None = None,
    llm_client: Any | None = None,
) -> CompiledGraph:
    """
    Convenience function to create an agent with default settings.

    Args:
        config: Agent configuration
        redis_client: Optional Redis client for checkpointing
        llm_client: Optional LLM client for response generation

    Returns:
        Compiled agent graph
    """
    builder = AgentBuilder(config)

    if redis_client:
        checkpointer = RedisCheckpointer(redis_client)
        builder.with_checkpointer(checkpointer)

    if llm_client:
        builder.with_llm(llm_client)

    builder.use_default_graph()

    return builder.build()
