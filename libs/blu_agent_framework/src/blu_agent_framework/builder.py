"""
Agent builder factory for creating LangGraph agents.
"""

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.graph import CompiledGraph
from langgraph.types import Send

from blu_agent_framework.checkpointer import RedisCheckpointer
from blu_agent_framework.config import AgentConfig
from blu_agent_framework.mcp_executor import MCPToolExecutor
from blu_agent_framework.nodes import (
    NodeRegistry,
    fan_out_tool_calls,
)
from blu_agent_framework.routing import (
    route_from_elicit,
    route_from_init,
    route_from_respond,
    route_from_tool,
)
from blu_agent_framework.state import AgentState

logger = logging.getLogger(__name__)


@dataclass
class EdgeDefinition:
    """Definition of a graph edge."""

    from_node: str
    to_node: str
    is_conditional: bool = False
    router: Callable | None = None
    # dict[str, str] for string→node routing; list[str] for Send-based fan-out targets
    routes: dict[str, str] | list[str] = field(default_factory=dict)


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
        self._use_fanout: bool = False

        # LLM client (set via with_llm)
        self._llm_client = None

        # Skill support (set via with_skill_factory / with_tool_filter)
        self._skill_factory = None          # SkillFactory instance for run_skill_node
        self._tool_filter: list[str] | None = None  # When set, skips get_for_task()

        # Supervisor graph support (set via use_supervisor_graph)
        self._supervisor_tier: str = "BASIC"
        self._supervisor_prompt_name: str = ""
        self._supervisor_fragments: list[str] = []
        self._context_service: Any = None

        # Orchestrator graph support (set via use_orchestrator_graph)
        self._orchestrator_tier: str = ""   # non-empty ↔ orchestrator mode

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

    def with_skill_factory(self, skill_factory: Any) -> "AgentBuilder":
        """Attach a SkillFactory so run_skill_node can invoke skills."""
        self._skill_factory = skill_factory
        return self

    def with_tool_filter(self, tool_names: list[str]) -> "AgentBuilder":
        """
        Pin the respond node to exactly these tools instead of running get_for_task().

        Used by SkillFactory._build_skill_graph() so skill sub-graphs bind the
        skill's curated required_tool_names, not a tag-scored subset.
        """
        self._tool_filter = list(tool_names)
        return self

    def with_context_service(self, context_service: Any) -> "AgentBuilder":
        """
        Attach a ContextService for supervisor prompt caching and context fetching.

        Used by use_supervisor_graph() to inject per-request context without
        threading non-serializable objects through LangGraph state.
        """
        self._context_service = context_service
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
        self._edges.append(
            EdgeDefinition(
                from_node=from_node,
                to_node=to_node,
            )
        )
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
        self._edges.append(
            EdgeDefinition(
                from_node=from_node,
                to_node="",  # Not used for conditional
                is_conditional=True,
                router=router,
                routes=routes,
            )
        )
        return self

    def use_default_graph(self) -> "AgentBuilder":
        """
        Use the default agent graph structure.

        Default structure (simple path):
            START → init → classify_intent → context_enrichment
                  → [route_after_enrichment] → elicit | respond | select_skill | end
            elicit → [route_from_elicit] → execute_tool | elicit | respond | end
            execute_tool → [route_from_tool] → respond | elicit | end
            respond → [route_from_respond] → init | END

        Complex path (when complexity >= "moderate" and enable_skills=True):
            context_enrichment → select_skill → [route_after_select_skill]
                               → run_skill → respond → END
                               → elicit (fallback when no skill matched)

        classify_intent is a no-op on tool-result turns (HumanMessage guard).
        context_enrichment always runs to keep loaded_context_keys current.

        Returns:
            Self for chaining
        """
        from blu_agent_framework.routing import (
            route_after_enrichment,
            route_after_select_skill,
        )

        # Add nodes
        self.add_node("init", "init")
        self.add_node("classify_intent", "classify_intent")
        self.add_node("context_enrichment", "context_enrichment")
        self.add_node("elicit", "elicit")
        self.add_node("execute_tool", "execute_tool")
        self.add_node("respond", "respond")
        self.add_node("end", "end")

        # Skill nodes — always present; run_skill is a no-op when _skill_factory is None
        self.add_node("select_skill", "select_skill")
        self.add_node("run_skill", "run_skill")

        # Add edges
        self.add_edge(START, "init")
        self.add_edge("init", "classify_intent")
        self.add_edge("classify_intent", "context_enrichment")
        self.add_conditional_edge(
            "context_enrichment",
            route_after_enrichment,
            {
                "elicit": "elicit",
                "respond": "respond",
                "select_skill": "select_skill",
                "end": "end",
            },
        )
        self.add_conditional_edge(
            "select_skill",
            route_after_select_skill,
            {
                "run_skill": "run_skill",
                "elicit": "elicit",
            },
        )
        self.add_edge("run_skill", "respond")
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

    def use_fanout_graph(self) -> "AgentBuilder":
        """
        Use a graph structure with Send-based fan-out for parallel tool execution.

        Structure:
            START -> init -> classify_intent -> context_enrichment
                  -> [route_from_init] -> elicit | respond | end
            elicit -> [route_from_elicit] -> execute_single_tool | elicit | respond | end
            execute_single_tool (parallel via Send) -> collect_tool_results (fan-in)
            collect_tool_results -> [route_from_tool] -> respond | elicit | end
            respond -> [route_from_respond] -> init | END

        Returns:
            Self for chaining
        """
        # Add nodes
        self.add_node("init", "init")
        self.add_node("classify_intent", "classify_intent")
        self.add_node("context_enrichment", "context_enrichment")
        self.add_node("elicit", "elicit")
        self.add_node("execute_single_tool", "execute_single_tool")
        self.add_node("collect_tool_results", "collect_tool_results")
        self.add_node("respond", "respond")
        self.add_node("end", "end")

        # Mark this builder as using fan-out
        self._use_fanout = True

        # Add edges
        self.add_edge(START, "init")
        self.add_edge("init", "classify_intent")
        self.add_edge("classify_intent", "context_enrichment")
        self.add_conditional_edge(
            "context_enrichment",
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
                "needs_tool": "execute_single_tool",
                "needs_elicitation": "elicit",
                "ready_to_respond": "respond",
                "end": "end",
            },
        )

        # Fan-in: after all parallel tool executions complete, collect results
        self.add_edge("execute_single_tool", "collect_tool_results")

        self.add_conditional_edge(
            "collect_tool_results",
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

    def use_skill_graph(self) -> "AgentBuilder":
        """
        Minimal graph for skill sub-agents: respond ↔ execute_tool → end.

        Skips init, classify_intent, context_enrichment, and elicitation —
        all the boilerplate that's irrelevant inside a focused skill execution.
        The respond node uses self._tool_filter (set via with_tool_filter) so
        it binds the skill's curated tools directly instead of tag-scoring.

        When the LLM emits tool calls, route_from_respond returns "init" which
        maps to execute_tool here (not back to respond) so tool calls are
        actually executed before the next LLM turn.
        """
        self.add_node("respond", "respond")
        self.add_node("execute_tool", "execute_tool")
        self.add_node("end", "end")
        self.add_edge(START, "respond")
        self.add_conditional_edge(
            "respond",
            route_from_respond,
            {
                "init": "execute_tool",  # tool call → execute → respond
                "end": "end",
            },
        )
        self.add_conditional_edge(
            "execute_tool",
            route_from_tool,
            {
                "success": "respond",
                "error": "respond",
                "needs_elicitation": "end",
                "end": "end",
            },
        )
        self.add_edge("end", END)
        return self

    def use_supervisor_graph(
        self,
        tier: str = "BASIC",
        prompt_name: str = "",
        fragments: list[str] | None = None,
    ) -> "AgentBuilder":
        """
        Use the supervisor+worker graph structure.

        The supervisor LLM routes user requests to specialist workers via
        ``delegate_to_*`` tool calls.  Workers run as parallel in-process
        LLM+tool loops (fan-out via Send) and their results are aggregated
        before the supervisor generates a final response.

        Structure::

            START → supervisor → [route_after_supervisor]
                ↓ (Send ×N)
            execute_worker → collect_worker_results
                ↓ [route_after_workers]
            supervisor (loop) | elicit | end → END

        Args:
            tier: Default client tier for worker filtering when not in state.
            prompt_name: Named Langfuse prompt for the supervisor system prompt.
                         When set, overrides ``fragments``.
            fragments: Fragment list for compose_prompt.  Defaults to the four
                       standard supervisor fragments when omitted.

        Returns:
            Self for chaining.
        """
        from blu_agent_framework.nodes import elicit_node, end_node
        from blu_agent_framework.supervisor import (
            collect_worker_results_node,
            route_after_supervisor,
            route_after_workers,
        )

        self._supervisor_tier = tier
        self._supervisor_prompt_name = prompt_name
        self._supervisor_fragments = fragments or [
            "fragment/supervisor-role",
            "fragment/supervisor-workers",
            "fragment/supervisor-rules",
            "fragment/response-format",
        ]

        # Sentinel callables replaced by actual implementations in _wrap_nodes()
        async def _supervisor_sentinel(state: Any) -> dict:
            return {}

        async def _execute_worker_sentinel(state: Any) -> dict:
            return {}

        self._nodes["supervisor"] = _supervisor_sentinel
        self._nodes["execute_worker"] = _execute_worker_sentinel
        self._nodes["collect_worker_results"] = collect_worker_results_node
        self._nodes["elicit"] = elicit_node
        self._nodes["end"] = end_node

        # Entry point
        self.add_edge(START, "supervisor")

        # Fan-out: route_after_supervisor returns list[Send] | str.
        # Pass a list of possible target names (LangGraph Send fan-out API).
        self._edges.append(EdgeDefinition(
            from_node="supervisor",
            to_node="",
            is_conditional=True,
            router=route_after_supervisor,
            routes=["execute_worker", "elicit", "end"],
        ))

        # Fan-in: all parallel execute_worker completions → collect_worker_results
        self.add_edge("execute_worker", "collect_worker_results")

        # After collection: loop back to supervisor or terminate
        self._edges.append(EdgeDefinition(
            from_node="collect_worker_results",
            to_node="",
            is_conditional=True,
            router=route_after_workers,
            routes={"supervisor": "supervisor", "elicit": "elicit", "end": "end"},
        ))

        self.add_edge("elicit", "end")
        self.add_edge("end", END)

        return self

    def use_orchestrator_graph(self, tier: str = "BASIC") -> "AgentBuilder":
        """
        Build the Layer-4 orchestrator graph.

        The orchestrator is the meta-skill that plans multi-step work, delegates each
        step to a Layer-3 domain skill (AgentTypeRegistry), and synthesizes results.

        Structure::

            START → parse_intent → gather_context → [route_after_context]
                ↓ simple                             ↓ complex          ↓ uncertain
            execute_step ←──────────────── decompose → plan → [confirm?]
                ↓ (loop via route_after_step)
            synthesize → end → END

            confirm → end → END  (waits; parse_intent handles response on next invocation)
            escalate → end → END

        Args:
            tier: Default client tier used when not present in state.

        Returns:
            Self for chaining.
        """
        from blu_agent_framework.nodes import end_node
        from blu_agent_framework.orchestrator import (
            confirm_node,
            escalate_node,
            route_after_context,
            route_after_plan,
            route_after_step,
        )

        self._orchestrator_tier = tier

        # Sentinel callables — replaced with real closures in _wrap_nodes()
        async def _sentinel(state: Any) -> dict:
            return {}

        self._nodes["parse_intent"]   = _sentinel
        self._nodes["gather_context"] = _sentinel
        self._nodes["decompose"]      = _sentinel
        self._nodes["plan"]           = _sentinel
        self._nodes["execute_step"]   = _sentinel
        self._nodes["synthesize"]     = _sentinel
        self._nodes["confirm"]        = confirm_node
        self._nodes["escalate"]       = escalate_node
        self._nodes["end"]            = end_node

        # Edges
        self.add_edge(START, "parse_intent")
        self.add_edge("parse_intent", "gather_context")
        self.add_conditional_edge(
            "gather_context",
            route_after_context,
            {
                "execute_step": "execute_step",
                "decompose":    "decompose",
                "confirm":      "confirm",
                "end":          "end",
            },
        )
        self.add_edge("decompose", "plan")
        self.add_conditional_edge(
            "plan",
            route_after_plan,
            {
                "execute_step": "execute_step",
                "confirm":      "confirm",
                "escalate":     "escalate",
            },
        )
        self.add_conditional_edge(
            "execute_step",
            route_after_step,
            {
                "execute_step": "execute_step",
                "synthesize":   "synthesize",
                "escalate":     "escalate",
            },
        )
        self.add_edge("synthesize", "end")
        self.add_edge("confirm",    "end")
        self.add_edge("escalate",   "end")
        self.add_edge("end", END)

        return self

    def use_custom_graph(self, graph_def: dict[str, Any]) -> "AgentBuilder":
        """
        Build the graph from a custom workflow_graph definition.

        The graph_def must have:
            - nodes: list of {id, type, ...}
            - edges: list of {source, target, label?, condition?}

        Nodes use their 'type' field to look up registered handlers.
        Edges with a 'condition' field are treated as conditional edges
        using the default routing functions for the source node type.

        Returns:
            Self for chaining
        """
        nodes_def = graph_def.get("nodes", [])
        edges_def = graph_def.get("edges", [])

        # Map of known conditional routers by source node name
        routers: dict[str, Callable] = {
            "init": route_from_init,
            "elicit": route_from_elicit,
            "execute_tool": route_from_tool,
            "respond": route_from_respond,
        }

        # Add nodes (skip __start__ and __end__ which are graph sentinels)
        for ndef in nodes_def:
            nid = ndef.get("id", "")
            ntype = ndef.get("type", nid)
            if nid in ("__start__", "__end__"):
                continue
            handler = NodeRegistry.get(ntype)
            if handler:
                self._nodes[nid] = handler
            else:
                logger.warning(f"Custom graph: node type '{ntype}' not in registry, skipping")

        # Group edges by source to detect conditional routing
        edges_by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for edef in edges_def:
            edges_by_source[edef["source"]].append(edef)

        # Process edges grouped by source
        processed_sources: set[str] = set()
        for source, src_edges in edges_by_source.items():
            src_key = source if source != "__start__" else START

            # If there's only one edge from this source and no condition, add simple edge
            if len(src_edges) == 1 and not src_edges[0].get("condition"):
                target = src_edges[0]["target"]
                tgt_key = target if target != "__end__" else END
                self._edges.append(EdgeDefinition(from_node=src_key, to_node=tgt_key))
                continue

            # Multiple edges or conditional edges → build conditional routing
            router = routers.get(source)
            if router:
                routes: dict[str, str] = {}
                for edef in src_edges:
                    label = edef.get("label") or edef.get("condition") or edef["target"]
                    target = edef["target"]
                    tgt_key = target if target != "__end__" else END
                    routes[label] = tgt_key
                self.add_conditional_edge(src_key, router, routes)
            else:
                # No router for this source — add individual simple edges
                for edef in src_edges:
                    target = edef["target"]
                    tgt_key = target if target != "__end__" else END
                    self._edges.append(EdgeDefinition(from_node=src_key, to_node=tgt_key))

        # Validate that all edge targets reference known nodes
        valid_node_ids = set(self._nodes.keys()) | {START, END}
        for edge in self._edges:
            if edge.is_conditional:
                for target in edge.routes.values():
                    if target not in valid_node_ids and target != END:
                        raise ValueError(
                            f"Custom graph edge from '{edge.from_node}' routes to unknown node '{target}'. "
                            f"Known nodes: {sorted(self._nodes.keys())}"
                        )
            else:
                if edge.to_node not in valid_node_ids and edge.to_node != END:
                    raise ValueError(
                        f"Custom graph edge references unknown target node '{edge.to_node}'. "
                        f"Known nodes: {sorted(self._nodes.keys())}"
                    )

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
                # list[str] routes → Send-based fan-out (LangGraph accepts both dict and list)
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
        # Resolve a single MCPToolExecutor before building closures so all
        # tool-execution nodes share the same instance and MCP connection.
        if self.mcp_executor is None:
            self.mcp_executor = MCPToolExecutor(
                mcp_url=self.config.mcp_url,
                timeout=self.config.timeout_seconds,
            )

        # Orchestrator graph: create all LLM-bound nodes in one shot.
        if self._orchestrator_tier:
            return self._create_orchestrator_nodes()

        wrapped = {}

        for name, handler in self._nodes.items():
            if name == "execute_tool":
                wrapped[name] = self._create_tool_executor_node(handler)
            elif name == "execute_single_tool":
                wrapped[name] = self._create_single_tool_executor_node(handler)
            elif name == "respond":
                wrapped[name] = self._create_respond_node(handler)
            elif name == "run_skill":
                wrapped[name] = self._create_run_skill_node(handler)
            elif name == "supervisor":
                wrapped[name] = self._create_supervisor_node()
            elif name == "execute_worker":
                wrapped[name] = self._create_worker_executor_node()
            else:
                wrapped[name] = handler

        return wrapped

    def _create_orchestrator_nodes(self) -> dict[str, Callable]:
        """
        Create all orchestrator node implementations and return a wrapped-nodes dict.

        Static nodes (confirm, escalate, end) are passed through as-is.
        LLM-dependent nodes get closures via the make_* factories in orchestrator.py.
        """
        from blu_agent_framework.orchestrator import (
            make_decompose_node,
            make_execute_step_node,
            make_gather_context_node,
            make_parse_intent_node,
            make_plan_node,
            make_synthesize_node,
        )
        from blu_agent_framework.supervisor import _WorkerInvoker

        tier    = self._orchestrator_tier
        llm     = self._llm_client
        ctx_svc = self._context_service

        invoker = _WorkerInvoker(llm=llm, mcp_executor=self.mcp_executor)

        llm_nodes: dict[str, Callable] = {
            "parse_intent":   make_parse_intent_node(llm, tier),
            "gather_context": make_gather_context_node(ctx_svc),
            "decompose":      make_decompose_node(llm, tier),
            "plan":           make_plan_node(llm, tier),
            "execute_step":   make_execute_step_node(invoker, ctx_svc),
            "synthesize":     make_synthesize_node(llm),
        }

        wrapped: dict[str, Callable] = {}
        for name, handler in self._nodes.items():
            wrapped[name] = llm_nodes.get(name, handler)
        return wrapped

    def _create_supervisor_node(self) -> Callable:
        """
        Create the supervisor node closure for use_supervisor_graph().

        Builds delegation StructuredTools from AgentTypeRegistry, composes the
        system prompt (fragments or named prompt), binds tools to the LLM, and
        stores tool_calls in pending_tool_calls for route_after_supervisor.
        """
        from blu_agent_framework.supervisor import (
            _is_transient_error,
            build_delegation_tools,
        )

        llm_client = self._llm_client
        supervisor_tier = self._supervisor_tier
        supervisor_fragments = self._supervisor_fragments
        supervisor_prompt_name = self._supervisor_prompt_name
        context_service = self._context_service

        async def supervisor_node_impl(state: AgentState) -> dict[str, Any]:
            nome_empresa = state.get("nome_empresa", "")
            tier = state.get("tier") or supervisor_tier
            model_override = state.get("model_override")

            messages = state.get("messages", [])
            last_msg = messages[-1] if messages else None
            is_tool_result_turn = isinstance(last_msg, ToolMessage)

            # Inject elicitation response context into conversation
            pending_elicit = state.get("pending_elicitation")
            elicit_resp = state.get("elicitation_response")
            if pending_elicit and elicit_resp:
                ctx_msg = (
                    f"The user replied '{elicit_resp.get('response')}' "
                    f"to: {pending_elicit.get('message')}"
                )
                messages = list(messages) + [HumanMessage(content=ctx_msg)]

            # Build / cache delegation tools
            cached_tools = state.get("_cached_tools")
            delegation_tools = cached_tools if cached_tools else build_delegation_tools(tier)

            # Build / cache system prompt
            cached_prompt = state.get("_cached_system_prompt")
            if cached_prompt:
                system_prompt = cached_prompt
            else:
                from blu_agent_framework.registry import AgentTypeRegistry

                workers_description = AgentTypeRegistry.build_supervisor_description(tier)
                variables: dict[str, Any] = {
                    "nome_empresa": nome_empresa,
                    "workers_description": workers_description,
                    "context_sections": "",
                    "tools_description": "",
                }
                system_prompt = ""

                if supervisor_prompt_name:
                    try:
                        from blu_prompt_management import build_prompt  # type: ignore[import]
                        system_prompt = await build_prompt(
                            name=supervisor_prompt_name,
                            variables=variables,
                            context_service=context_service,
                        )
                    except Exception as exc:
                        logger.warning("[Supervisor] build_prompt failed: %s", exc)

                if not system_prompt and supervisor_fragments:
                    try:
                        from blu_prompt_management import compose_prompt  # type: ignore[import]
                        system_prompt = await compose_prompt(
                            fragments=supervisor_fragments,
                            variables=variables,
                            context_service=context_service,
                        )
                    except Exception as exc:
                        logger.warning("[Supervisor] compose_prompt failed: %s", exc)

                if not system_prompt:
                    workers_list = "\n".join(
                        f"- delegate_to_{cfg.slug.replace('-', '_')}: {cfg.description}"
                        for cfg in AgentTypeRegistry.for_tier(tier)
                    )
                    system_prompt = (
                        f"You are a supervisor assistant"
                        f"{f' for {nome_empresa}' if nome_empresa else ''}.\n"
                        f"Delegate tasks to specialist workers:\n{workers_list}\n"
                        "Answer simple questions directly. Respond in the user's language."
                    )

            # Apply history window and build LLM input
            history_window = 10
            recent = messages[-history_window:]
            llm_messages = [SystemMessage(content=system_prompt)] + recent

            # Resolve LLM (with optional model override)
            llm = llm_client
            if model_override and llm is not None:
                try:
                    from blu_llm_service import get_model  # type: ignore[import]
                    llm = get_model(model_name=model_override)
                except Exception:
                    pass

            if llm is None:
                return {
                    "messages": [AIMessage(content="No LLM configured for supervisor.")],
                    "ended": True,
                }

            bound_llm = llm.bind_tools(delegation_tools) if delegation_tools else llm

            # Invoke with transient-error retry
            response: AIMessage | None = None
            for attempt in range(3):
                try:
                    response = await bound_llm.ainvoke(llm_messages)
                    break
                except Exception as exc:
                    if attempt < 2 and _is_transient_error(exc):
                        logger.warning(
                            "[Supervisor] Transient error attempt %d: %s", attempt + 1, exc
                        )
                        await asyncio.sleep(1.0 * (attempt + 1))
                    else:
                        logger.error("[Supervisor] LLM error: %s", exc)
                        return {
                            "messages": [AIMessage(content="Internal supervisor error.")],
                            "ended": True,
                        }

            if response is None:
                return {
                    "messages": [AIMessage(content="Internal supervisor error.")],
                    "ended": True,
                }

            updates: dict[str, Any] = {
                "messages": [response],
                "_cached_system_prompt": system_prompt,
                "_cached_tools": delegation_tools,
            }

            # On new user turns, clear structured data from previous interactions
            if not is_tool_result_turn:
                updates["structured_data"] = None
                updates["structured_data_list"] = None  # _list_reducer: None → clear

            # Parse delegation tool_calls → pending_tool_calls for route_after_supervisor
            tool_calls = getattr(response, "tool_calls", None) or []
            if tool_calls:
                pending = [
                    {"name": tc["name"], "id": tc["id"], "args": tc.get("args", {})}
                    for tc in tool_calls
                ]
                updates["pending_tool_calls"] = pending
                logger.info(
                    "[Supervisor] Delegating to %d worker(s): %s",
                    len(pending),
                    [p["name"] for p in pending],
                )
            else:
                updates["pending_tool_calls"] = []
                logger.info("[Supervisor] Final response (no tool calls)")

            return updates

        return supervisor_node_impl

    def _create_worker_executor_node(self) -> Callable:
        """
        Create the execute_worker node closure for use_supervisor_graph().

        Receives a ToolCallSendState-like dict dispatched via Send, extracts
        the worker slug from the delegation tool name, and runs the worker
        loop via _WorkerInvoker.  Returns a ToolMessage plus optional
        structured_data_list update for fan-in aggregation.
        """
        _MAX_CONTENT = 4_000

        from blu_agent_framework.supervisor import _WorkerInvoker

        llm_client = self._llm_client
        mcp_executor = self.mcp_executor  # already resolved in _wrap_nodes
        context_service = self._context_service

        invoker = _WorkerInvoker(llm=llm_client, mcp_executor=mcp_executor)

        async def execute_worker_node_impl(state: dict[str, Any]) -> dict[str, Any]:
            from blu_agent_framework.registry import AgentTypeRegistry

            tool_call = state.get("tool_call", {})
            tool_name = tool_call.get("name", "")
            tool_call_id = tool_call.get("id", "")
            args = tool_call.get("args", {})
            task = args.get("task", "")
            nome_empresa = state.get("nome_empresa", "")

            if not tool_name.startswith("delegate_to_"):
                return {
                    "messages": [
                        ToolMessage(
                            content=f"Invalid delegation tool: {tool_name}",
                            tool_call_id=tool_call_id,
                            name=tool_name,
                        )
                    ]
                }

            slug = tool_name[len("delegate_to_"):].replace("_", "-")
            cfg = AgentTypeRegistry.get(slug)

            if cfg is None:
                return {
                    "messages": [
                        ToolMessage(
                            content=f"Unknown worker slug: {slug}",
                            tool_call_id=tool_call_id,
                            name=tool_name,
                        )
                    ]
                }

            logger.info("[execute_worker] Invoking '%s', task: %.100s...", slug, task)

            result = await invoker.invoke(
                cfg=cfg,
                task=task,
                nome_empresa=nome_empresa,
                context_service=context_service,
            )

            content = result.summary
            if result.error:
                content = f"Worker error: {result.error}\n{result.summary}"
            if len(content) > _MAX_CONTENT:
                content = content[:_MAX_CONTENT] + "\n[truncated]"

            updates: dict[str, Any] = {
                "messages": [
                    ToolMessage(
                        content=content,
                        tool_call_id=tool_call_id,
                        name=tool_name,
                    )
                ]
            }

            if result.structured_data:
                sd = dict(result.structured_data)
                sd["source_worker"] = slug
                updates["structured_data_list"] = [sd]

            return updates

        return execute_worker_node_impl

    def _create_run_skill_node(self, original_handler: Callable) -> Callable:
        """
        Create run_skill node that delegates to SkillFactory.

        The closure captures skill_factory and agent_config at graph-build time.
        When skill_factory is None the node logs a warning and clears current_skill
        so the graph can continue without crashing.
        """
        skill_factory = self._skill_factory

        async def run_skill_node_impl(state: AgentState) -> dict[str, Any]:
            skill_name = state.get("current_skill")
            if not skill_name:
                logger.warning("[run_skill] No current_skill in state — skipping")
                return {"current_skill": None}

            if skill_factory is None:
                logger.warning(
                    f"[run_skill] SkillFactory not wired — skill '{skill_name}' cannot run. "
                    "Wire with_skill_factory() or set AgentConfig.enable_skills=True."
                )
                return {"current_skill": None}

            from blu_agent_framework.skills import SkillTurnLimitError

            try:
                result = await skill_factory.run(skill_name, state)
            except SkillTurnLimitError as exc:
                logger.error(f"[run_skill] Skill '{skill_name}' hit turn limit: {exc}")
                error_msg = AIMessage(
                    content=(
                        f"[Skill: {skill_name}]\nErro: limite de execução atingido. "
                        "Por favor, tente novamente ou simplifique sua solicitação."
                    )
                )
                return {
                    "messages": [error_msg],
                    "skill_results": [
                        {"skill_name": skill_name, "success": False, "error": str(exc)}
                    ],
                    "current_skill": None,
                }
            except Exception as exc:
                logger.exception(f"[run_skill] Unexpected error running skill '{skill_name}'")
                return {
                    "current_skill": None,
                    "skill_results": [
                        {"skill_name": skill_name, "success": False, "error": str(exc)}
                    ],
                }

            # Inject the skill's final AI message into parent message history.
            content = result.last_text()
            messages_update = (
                [AIMessage(content=f"[Skill: {skill_name}]\n{content}")]
                if content
                else []
            )

            return {
                "messages": messages_update,
                "skill_results": [result.to_dict()],
                "current_skill": None,
            }

        return run_skill_node_impl

    def _create_tool_executor_node(self, original_handler: Callable) -> Callable:
        """
        Create tool executor node with MCP integration.
        """
        mcp_executor = self.mcp_executor  # resolved once in _wrap_nodes

        async def tool_executor_node(state: AgentState) -> dict[str, Any]:
            tool_name = state.get("tool_to_execute")
            tool_args = state.get("tool_args", {})

            if not tool_name:
                return {"error": "No tool specified"}

            # Validate tool is enabled (per-agent config)
            enabled_tools = self.config.enabled_tools or []
            if enabled_tools and tool_name not in enabled_tools:
                return {
                    "error": f"Tool '{tool_name}' not enabled",
                    "tool_to_execute": None,
                }

            # Build context
            context = {
                "cliente_id": state.get("cliente_id", ""),
                "session_id": state.get("session_id", ""),
                "channel": state.get("channel", "api"),
                **(state.get("metadata") or {}),
            }

            # Execute tool
            result = await mcp_executor.execute(tool_name, tool_args, context)
            result_dict = result.to_dict()
            content = str(result_dict.get("result", ""))
            if result.error:
                content = f"Error: {result.error}"

            # Resolve tool_call_id from pending_tool_calls so the subsequent
            # LLM turn sees a properly-threaded ToolMessage (required by the
            # OpenAI / Anthropic function-calling format).
            pending = state.get("pending_tool_calls") or []
            tool_call_id = next(
                (tc.get("id", "") for tc in pending if tc.get("name") == tool_name),
                "",
            )

            updates: dict[str, Any] = {
                "tool_to_execute": None,
                "tool_args": None,
                "pending_tool_calls": [],
                "last_tool_result": result_dict,
                "tool_results": [result_dict],
                "error": result.error if not result.success else None,
            }
            if tool_call_id:
                updates["messages"] = [
                    ToolMessage(
                        content=content,
                        tool_call_id=tool_call_id,
                        name=tool_name,
                    )
                ]
            return updates

        return tool_executor_node

    def _create_single_tool_executor_node(self, original_handler: Callable) -> Callable:
        """
        Create single tool executor node for Send-based fan-out.

        Each invocation handles one tool call dispatched via Send.
        Receives ToolCallSendState and returns results to be aggregated.
        """
        mcp_executor = self.mcp_executor  # resolved once in _wrap_nodes

        async def single_tool_executor_node(state: dict[str, Any]) -> dict[str, Any]:
            tool_call = state.get("tool_call", {})
            tool_name = tool_call.get("name", "")
            tool_args = tool_call.get("args", {})
            tool_call_id = tool_call.get("id", "")

            if not tool_name:
                return {"error": "No tool specified in Send state"}

            # Validate tool is enabled (per-agent config)
            enabled_tools = self.config.enabled_tools or []
            if enabled_tools and tool_name not in enabled_tools:
                return {
                    "messages": [
                        ToolMessage(
                            content=f"Tool '{tool_name}' not enabled",
                            tool_call_id=tool_call_id,
                            name=tool_name,
                        )
                    ],
                    "tool_results": [{"tool_name": tool_name, "error": f"Tool '{tool_name}' not enabled", "success": False}],
                }

            # Build context from Send state
            context = {
                "cliente_id": state.get("cliente_id", ""),
                "session_id": state.get("session_id", ""),
                "channel": state.get("channel", "api"),
                **(state.get("metadata") or {}),
            }

            logger.info(f"[fan-out] Executing tool '{tool_name}' (call_id={tool_call_id})")

            # Execute tool via MCP
            result = await mcp_executor.execute(tool_name, tool_args, context)

            result_dict = result.to_dict()
            content = str(result_dict.get("result", ""))
            if result.error:
                content = f"Error: {result.error}"

            return {
                "messages": [
                    ToolMessage(
                        content=content,
                        tool_call_id=tool_call_id,
                        name=tool_name,
                    )
                ],
                "tool_results": [result_dict],
                "error": result.error if not result.success else None,
            }

        return single_tool_executor_node

    def _create_respond_node(self, original_handler: Callable) -> Callable:
        """
        Create respond node with LLM integration and dynamic tool binding.

        On every call the node:
        1. Selects up to max_tools tool names via ToolRegistry.get_for_task() using
           the intent_tags and loaded_context_keys already stored in state.
        2. Resolves those names to LangChain BaseTool objects from the live MCP session.
        3. Calls llm.bind_tools(lc_tools) — a zero-network RunnableBinding — so the
           LLM can emit tool_calls in its response.
        4. If the LLM response contains tool_calls, stores them in pending_tool_calls
           and tool_to_execute so route_from_respond loops back through the executor.
        """
        llm_client = self._llm_client
        mcp_executor = self.mcp_executor
        agent_config = self.config
        # Captured at build time: not None → skip get_for_task() and bind these directly.
        tool_filter = self._tool_filter
        # Per-graph tool selection cache: (intent_tags, tier, loaded_ctx) → active_names.
        # Avoids re-running ToolRegistry.get_for_task() on every respond invocation when
        # the intent hasn't changed between turns.
        _tool_selection_cache: dict[tuple, list[str]] = {}
        logger.debug(f"Creating respond node with llm_client={llm_client is not None}")

        async def respond_node(state: AgentState) -> dict[str, Any]:
            logger.debug(f"respond_node: llm_client={llm_client is not None}")

            messages = state.get("messages", [])
            system_prompt = state.get("system_prompt", "")
            last_tool_result = state.get("last_tool_result")

            if not llm_client:
                # Fallback: generate a simple response without LLM
                logger.warning("No LLM client configured - using fallback response")

                if last_tool_result:
                    import json

                    result_text = last_tool_result.get("result", "")
                    if isinstance(result_text, dict):
                        result_text = json.dumps(result_text, ensure_ascii=False, indent=2)
                    fallback_response = f"Resultado: {result_text}"
                else:
                    fallback_response = "Desculpe, não consegui processar sua solicitação. Por favor, tente novamente."

                return {
                    "messages": [AIMessage(content=fallback_response)],
                    "last_tool_result": None,
                    "ended": True,
                }

            # Build messages for LLM
            llm_messages = []
            if system_prompt:
                llm_messages.append(SystemMessage(content=system_prompt))
            llm_messages.extend(messages)

            # last_tool_result is only present on legacy single-tool turns that did
            # not produce a ToolMessage (e.g., when no tool_call_id was available).
            # Proper function-calling turns already appended a ToolMessage to messages.
            if last_tool_result:
                tool_context = (
                    f"\n\nTool Result ({last_tool_result.get('tool_name')}):\n"
                    + str(last_tool_result.get("result", ""))
                )
                llm_messages.append(SystemMessage(content=tool_context))

            # --- Dynamic tool binding ---
            bound_llm = llm_client
            enabled_tools: list[str] = agent_config.enabled_tools or []
            if enabled_tools and mcp_executor:
                try:
                    if tool_filter is not None:
                        # Skill sub-graph: use the exact curated list, skip tag-scoring.
                        active_names = tool_filter
                        intent_tags_log: list[str] = ["(skill-filter)"]
                        tier_log = ""
                    else:
                        from blu_tool_registry import ToolRegistry

                        intent_tags: list[str] = state.get("intent_tags") or []
                        loaded_ctx: list[str] = state.get("loaded_context_keys") or []
                        tier: str = state.get("metadata", {}).get("tier", "BASIC")
                        max_tools = 4 if len(loaded_ctx) < 3 else 8

                        # Cache tool selection by (tags, tier, ctx) so we skip
                        # ToolRegistry scoring on subsequent turns with the same intent.
                        cache_key = (tuple(sorted(intent_tags)), tier, tuple(sorted(loaded_ctx)))
                        if cache_key in _tool_selection_cache:
                            active_names = _tool_selection_cache[cache_key]
                        else:
                            active_names = ToolRegistry.get_for_task(
                                enabled_tools=enabled_tools,
                                tier=tier,
                                intent_tags=intent_tags,
                                available_context=loaded_ctx,
                                max_tools=max_tools,
                            )
                            if not active_names:
                                active_names = enabled_tools[:max_tools]
                            _tool_selection_cache[cache_key] = active_names

                        intent_tags_log = intent_tags
                        tier_log = tier

                    lc_tools = await mcp_executor.get_lc_tools(active_names)
                    if lc_tools:
                        bound_llm = llm_client.bind_tools(lc_tools)
                        logger.info(
                            f"[respond] Bound {len(lc_tools)} tools "
                            f"(intent={intent_tags_log}, tier={tier_log}): "
                            f"{[t.name for t in lc_tools]}"
                        )
                except Exception as exc:
                    logger.warning(
                        f"[respond] Dynamic tool binding failed, using unbound LLM: {exc}"
                    )

            # Generate response
            try:
                response = await bound_llm.ainvoke(llm_messages)

                # Store the full AIMessage so tool_call IDs are preserved for the
                # subsequent ToolMessage created by _create_tool_executor_node.
                updates: dict[str, Any] = {
                    "messages": [response],
                    "last_tool_result": None,
                }

                # Parse LLM-native tool calls and wire routing state.
                tool_calls = getattr(response, "tool_calls", None) or []
                if tool_calls:
                    pending = [
                        {"name": tc["name"], "args": tc.get("args", {}), "id": tc["id"]}
                        for tc in tool_calls
                    ]
                    updates["pending_tool_calls"] = pending
                    # route_from_respond checks tool_to_execute to loop back through
                    # init → elicit → execute_tool (single-tool compat path).
                    updates["tool_to_execute"] = pending[0]["name"]
                    updates["tool_args"] = pending[0].get("args", {})
                    logger.info(
                        f"[respond] LLM requested {len(pending)} tool(s): "
                        f"{[p['name'] for p in pending]}"
                    )

                return updates

            except Exception as e:
                logger.exception("LLM invocation failed")
                return {
                    "messages": [
                        AIMessage(
                            content="Desculpe, ocorreu um erro ao processar sua solicitação."
                        )
                    ],
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
