"""
blu_agent_framework.skill_factory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

SkillFactory — executes SkillDefinitions as isolated, ephemeral sub-graphs.

Each skill runs in its own compiled LangGraph (use_skill_graph: respond → end),
bound to only the skill's required_tool_names.  No checkpointer is attached so
no Redis keys are written for skill execution.

The factory is instantiated once per process (inside StandaloneAgentFactory)
and caches compiled skill graphs across requests.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from blu_agent_framework.mcp_executor import MCPToolExecutor
    from blu_agent_framework.state import AgentState

logger = logging.getLogger(__name__)


# =============================================================================
# SkillResult
# =============================================================================


@dataclass
class SkillResult:
    """
    Structured output from a single skill execution.

    Attributes:
        skill_name: Which skill ran.
        success: False if the skill graph errored or hit turn limit with on_max_turns='raise'.
        output: The full final state dict returned by the skill graph.
        turns_used: How many LLM ↔ tool cycles the skill consumed.
        error: Error message when success=False.
        tool_calls: All tool calls made during the skill's execution.
    """

    skill_name: str
    success: bool
    output: dict[str, Any]
    turns_used: int = 0
    error: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "success": self.success,
            "turns_used": self.turns_used,
            "error": self.error,
        }

    def last_text(self) -> str:
        """Extract the last AI-generated text from the skill's message history."""
        from langchain_core.messages import AIMessage

        messages = self.output.get("messages", [])
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                return str(msg.content)
        return ""


# =============================================================================
# SkillFactory
# =============================================================================


class SkillFactory:
    """
    Builds and runs skill sub-agents.

    One instance lives per StandaloneAgentFactory (i.e. per service process).
    Compiled skill graphs are cached in _compiled so the graph is only built
    once per skill name per process.

    Args:
        llm: The same LLM client used by the parent agent.
        mcp_executor: Shared MCP executor (same tool pool, no extra connections).
        agent_enabled_tools: The parent agent's enabled_tools whitelist.
            SkillFactory intersects this with skill.required_tool_names so a
            data-analyst agent cannot accidentally run RFQ tools.
    """

    def __init__(
        self,
        llm: Any,
        mcp_executor: MCPToolExecutor,
        agent_enabled_tools: list[str],
    ) -> None:
        self._llm = llm
        self._mcp_executor = mcp_executor
        self._agent_enabled_tools: set[str] = set(agent_enabled_tools)
        self._compiled: dict[str, Any] = {}  # skill_name → CompiledGraph

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(
        self,
        skill_name: str,
        parent_state: AgentState,
    ) -> SkillResult:
        """
        Execute a skill as an isolated sub-graph.

        Steps:
        1. Fetch the skill's system prompt from Langfuse.
        2. Build isolated state (deep-copied, fresh message list, clean counters).
        3. Run the cached compiled graph — no checkpointer, no Redis writes.
        4. Return SkillResult; raise SkillTurnLimitError if on_max_turns='raise'.
        """
        from blu_agent_framework.skills import SKILL_REGISTRY, SkillTurnLimitError
        from blu_prompt_management import get_prompt_loader

        if skill_name not in SKILL_REGISTRY:
            return SkillResult(
                skill_name=skill_name,
                success=False,
                output={},
                error=f"Unknown skill '{skill_name}'",
            )

        skill = SKILL_REGISTRY[skill_name]

        # --- 1. Load system prompt from Langfuse ---
        system_prompt = ""
        try:
            loaded = await get_prompt_loader().load(
                skill.prompt_name,
                variables={"max_turns": skill.max_turns},
                allow_fallback=False,
            )
            system_prompt = loaded.content
        except Exception as exc:
            logger.warning(
                f"[SkillFactory] Could not load prompt '{skill.prompt_name}': {exc}. "
                "Proceeding with empty system prompt."
            )

        # --- 2. Build isolated state ---
        from langchain_core.messages import SystemMessage

        # Selective copy instead of deepcopy of the full parent state.
        # Scalars are immutable so they need no copying; mutable containers
        # (dicts, lists) get a shallow copy — skills don't mutate nested values.
        parent_messages = list(parent_state.get("messages", []))
        skill_state: dict = {
            # Immutable scalars — pass through directly
            "session_id": parent_state.get("session_id", ""),
            "cliente_id": parent_state.get("cliente_id", ""),
            "thread_id": parent_state.get("thread_id", ""),
            "channel": parent_state.get("channel", "api"),
            "agent_name": parent_state.get("agent_name", ""),
            "agent_role": parent_state.get("agent_role", ""),
            "tier": parent_state.get("tier", "BASIC"),
            "nome_empresa": parent_state.get("nome_empresa", ""),
            "current_domain": parent_state.get("current_domain"),
            # Shallow copies of mutable containers the skill may read
            "client_context": dict(parent_state.get("client_context") or {}),
            "metadata": dict(parent_state.get("metadata") or {}),
            "intent_tags": list(parent_state.get("intent_tags") or []),
            "loaded_context_keys": list(parent_state.get("loaded_context_keys") or []),
            # Fresh message list: system prompt + last 3 parent turns for context
            "messages": (
                [SystemMessage(content=system_prompt)] if system_prompt else []
            ) + parent_messages[-3:],
            # Reset all transient / turn-scoped fields
            "system_prompt": system_prompt,
            "turn_count": 0,
            "max_turns": skill.max_turns,
            "tool_results": [],
            "pending_tool_calls": [],
            "tool_to_execute": None,
            "tool_args": None,
            "last_tool_result": None,
            "ended": False,
            "error": None,
            "errors": [],
            "skill_results": [],
            "current_skill": None,
            "complexity": None,
            "available_tools_metadata": [],
            "elicitation_history": [],
            "pending_elicitation": None,
            "elicitation_response": None,
        }

        # --- 3. Compile graph (cached per-process) ---
        if skill_name not in self._compiled:
            self._compiled[skill_name] = self._build_skill_graph(skill)
        graph = self._compiled[skill_name]

        # --- 4. Run — no thread_id / no checkpointer ---
        try:
            result_state = await graph.ainvoke(skill_state)
        except Exception as exc:
            logger.exception(f"[SkillFactory] Skill '{skill_name}' raised during ainvoke")
            return SkillResult(
                skill_name=skill_name,
                success=False,
                output={},
                error=str(exc),
            )

        turns_used = result_state.get("turn_count", 0)

        # Handle turn-limit contract.
        if turns_used >= skill.max_turns and skill.on_max_turns == "raise":
            raise SkillTurnLimitError(skill_name, skill.max_turns)

        error = result_state.get("error")
        return SkillResult(
            skill_name=skill_name,
            success=not error,
            output=result_state,
            turns_used=turns_used,
            error=error,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_skill_graph(self, skill: Any) -> Any:
        """
        Compile a minimal 2-node graph for this skill.

        Graph: respond → end
        No init, no elicitation, no classify_intent boilerplate.
        The respond node is bound to skill.required_tool_names ∩ agent_enabled_tools.
        """
        from blu_agent_framework.builder import AgentBuilder
        from blu_agent_framework.config import AgentConfig

        # Intersect skill tools with the parent agent's whitelist.
        active_tools = [
            t for t in skill.required_tool_names
            if not self._agent_enabled_tools or t in self._agent_enabled_tools
        ]

        cfg = AgentConfig(
            name=skill.name,
            role=skill.description,
            enabled_tools=active_tools,
        )

        builder = AgentBuilder(cfg, mcp_executor=self._mcp_executor, checkpointer=None)
        builder.with_llm(self._llm)
        builder.with_tool_filter(active_tools)  # Skip get_for_task(); use exact list
        builder.use_skill_graph()

        compiled = builder.build()
        logger.info(
            f"[SkillFactory] Compiled graph for skill '{skill.name}' "
            f"with tools={active_tools}"
        )
        return compiled
