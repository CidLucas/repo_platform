"""
blu_agent_framework.orchestrator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Layer 4 meta-skill: the orchestrator plans, delegates to Layer 3 domain skills,
and synthesizes their outputs into a coherent response.

Skill hierarchy
---------------
Layer 4  ORCHESTRATOR          this module — plans and coordinates
Layer 3  DOMAIN SKILLS         AgentTypeRegistry entries, run via specialist subgraphs
                               (data-analyst, knowledge-assistant, customer-communication, …)
Layer 2  TOOL SKILLS           deterministic single-purpose wrappers (future)
Layer 1  PRIMITIVE TOOLS       MCP-exposed functions (supabase.query, bigquery.run_query, …)

The orchestrator ONLY calls Layer 3 skills.  It never calls Layer 2 or Layer 1
directly.  If a plan needs a BigQuery query, it delegates to data-analyst, which
internally resolves the right tool calls.

Graph nodes
-----------
parse_intent   classify request: simple | complex | uncertain; detect confirmations
gather_context load tier, company, available Layer-3 skills
decompose      (complex only) identify sub-tasks and their domains
plan           (complex only) map sub-tasks to Layer-3 skills, order, flag mutations
execute_step   run one Layer-3 skill via specialist subgraph; loops until plan is complete
synthesize     combine step results into final user-facing response
confirm        gate mutations / show plan; waits for user approval
escalate       handle failures gracefully

Routing
-------
simple    → parse_intent → gather_context → execute_step → synthesize → end
complex   → parse_intent → gather_context → decompose → plan → [confirm?]
                        → execute_step (×N loop) → synthesize → end
uncertain → parse_intent → gather_context → confirm → end  (re-enters on next message)
resumed   → parse_intent (detects confirmation) → gather_context → execute_step → …
"""

from __future__ import annotations

import json
import logging
from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from blu_agent_framework.registry import AgentTypeRegistry
from blu_agent_framework.state import AgentState
from blu_agent_framework.utils.llm_parse import parse_first_json
from blu_agent_framework.utils.observability import (
    LLMCallTimer,
    generate_correlation_id,
    log_llm_call,
    log_llm_response,
    log_parse_failure,
)

logger = logging.getLogger(__name__)


async def _load_prompt(name: str, variables: dict[str, Any] | None = None) -> str:
    """Load an orchestrator prompt via PromptLoader (Langfuse-first, builtin fallback)."""
    try:
        from blu_prompt_management import build_prompt
        return await build_prompt(
            f"orchestrator/{name}",
            variables=variables or {},
            allow_fallback=True,
        )
    except Exception as exc:
        logger.warning("[orchestrator] Could not load prompt '%s': %s", name, exc)
        return ""


# ---------------------------------------------------------------------------
# Pydantic models for structured LLM output
# ---------------------------------------------------------------------------

class PlanStep(BaseModel):
    id: str = Field(description="Unique step id, e.g. 'step_1'")
    skill_slug: str = Field(description="Layer-3 skill slug from the available-skills list")
    task: str = Field(description="Specific task description sent to the skill")
    depends_on: list[str] = Field(default_factory=list)
    is_mutation: bool = Field(default=False, description="True if this step modifies data or emits messages")
    requires_confirmation: bool = Field(default=False)


class ParseIntentResult(BaseModel):
    complexity: Literal["simple", "complex", "uncertain"]
    involved_domains: list[str]
    plan: list[PlanStep] = Field(default_factory=list)   # populated for 'simple'
    clarification: str = Field(default="")               # populated for 'uncertain'


class DecomposeResult(BaseModel):
    sub_tasks: list[dict] = Field(
        description="[{id, domain, description, depends_on}]"
    )


class PlanResult(BaseModel):
    plan: list[PlanStep]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_YES = {"yes", "sim", "ok", "sure", "confirm", "confirmar", "proceed", "go",
        "pode", "afirmativo", "claro", "yep", "yup"}
_NO  = {"no", "nao", "não", "cancel", "cancelar", "stop", "abort",
        "rejeitar", "reject", "n", "nope"}


def _parse_yes_no(text: str) -> bool | None:
    """Return True (yes), False (no), or None (unclear) from a short user reply."""
    words = set(text.lower().split())
    if words & _YES:
        return True
    if words & _NO:
        return False
    return None


def _get_next_step(plan: list[dict]) -> dict[str, Any] | None:
    """Return the first pending step whose dependencies are all done."""
    done_ids = {s["id"] for s in plan if s["status"] == "done"}
    for step in plan:
        if step["status"] != "pending":
            continue
        if set(step.get("depends_on") or []).issubset(done_ids):
            return step
    return None


def _enrich_task(task: str, step: dict[str, Any], step_results: dict[str, str]) -> str:
    """Prepend outputs of dependency steps as context for the current task."""
    deps = step.get("depends_on") or []
    ctx_lines = [
        f"[Context from {dep}]:\n{step_results[dep][:800]}"
        for dep in deps
        if dep in step_results
    ]
    if not ctx_lines:
        return task
    return task + "\n\nContext from prior steps:\n" + "\n\n".join(ctx_lines)


def _parse_json_with_model(text: str, model_cls: type) -> Any | None:
    """Extract the first JSON object from an LLM response and validate with a pydantic model.

    Uses parse_first_json for tolerant extraction (fenced blocks, balanced braces,
    trailing-comma cleanup) then delegates to model_cls.model_validate for schema
    validation. Logs the raw response on failure.
    """
    raw = parse_first_json(text)
    if raw is None:
        logger.warning("[orchestrator] Could not extract JSON from LLM response: %.200s", text)
        return None
    try:
        return model_cls.model_validate(raw)
    except Exception as exc:
        logger.warning("[orchestrator] JSON schema validation failed (%s): %.200s", exc, text)
        return None


# Keep the old name as an alias so any external callers are not broken.
_parse_json = _parse_json_with_model


def _step_to_dict(step: PlanStep) -> dict[str, Any]:
    return step.model_dump() | {"status": "pending", "result": None}


def _format_plan(plan: list[dict]) -> str:
    return "\n".join(
        f"  {i + 1}. [{s['skill_slug']}] {s['task']}"
        + (" ⚠️ requires confirmation" if s.get("requires_confirmation") else "")
        + (" 🔁 mutation" if s.get("is_mutation") else "")
        for i, s in enumerate(plan)
    )


# ---------------------------------------------------------------------------
# Node factory functions
# (called by AgentBuilder to bind LLM / MCP dependencies at graph-build time)
# ---------------------------------------------------------------------------

def make_parse_intent_node(llm: Any, tier: str) -> None:
    """
    Layer 4 entry — classifies the user request and detects confirmation responses.

    On every invocation:
    1. If pending_confirmation exists and the user's message is a yes/no → resolve it.
    2. Otherwise → call LLM to classify: simple | complex | uncertain.
       - simple  : also build a single-step plan
       - uncertain: set pending_confirmation with a clarifying question
    """

    async def parse_intent_node(state: AgentState) -> dict[str, Any]:
        messages     = state.get("messages", [])
        last_msg     = messages[-1] if messages else None
        pending_conf = state.get("pending_confirmation")

        # --- Confirmation-response path ---
        if pending_conf and isinstance(last_msg, HumanMessage):
            verdict = _parse_yes_no(last_msg.content)
            if verdict is True:
                return {"confirmed": True,  "pending_confirmation": None}
            if verdict is False:
                return {"confirmed": False, "pending_confirmation": None}
            # Unclear reply → treat as a new uncertain request (fall through)

        # --- Fresh-intent classification ---
        if not isinstance(last_msg, HumanMessage):
            return {"complexity": "uncertain", "involved_domains": [], "confirmed": None}

        cur_tier     = state.get("tier") or tier
        skills_desc  = AgentTypeRegistry.build_supervisor_description(cur_tier)
        system_prompt = await _load_prompt("parse-intent", {"workers_description": skills_desc})

        cid = generate_correlation_id()
        log_llm_call(logger, cid, node="parse_intent", prompt_preview=system_prompt[:300])
        try:
            async with LLMCallTimer() as timer:
                response: AIMessage = await llm.ainvoke([
                    SystemMessage(content=system_prompt),
                    last_msg,
                ])
            log_llm_response(
                logger, cid, node="parse_intent",
                latency_ms=timer.elapsed_ms,
                response_preview=str(response.content)[:300],
            )
        except Exception as exc:
            logger.error("[parse_intent] LLM call failed: %s", exc)
            return {"complexity": "uncertain", "involved_domains": [], "confirmed": None}

        raw_content = str(response.content)
        parsed = _parse_json(raw_content, ParseIntentResult)
        if not parsed:
            log_parse_failure(logger, cid, node="parse_intent", raw_response=raw_content,
                              reason="Could not parse intent JSON; defaulting to uncertain")
            return {"complexity": "uncertain", "involved_domains": [], "confirmed": None}

        updates: dict[str, Any] = {
            "complexity":        parsed.complexity,
            "involved_domains":  parsed.involved_domains,
            "confirmed":         None,
            # Reset plan state from any previous turn
            "plan":              None,
            "step_results":      {},
            "_sub_tasks":        None,
        }

        if parsed.complexity == "simple" and parsed.plan:
            updates["plan"] = [_step_to_dict(s) for s in parsed.plan]

        if parsed.complexity == "uncertain" and parsed.clarification:
            updates["pending_confirmation"] = {
                "type":    "clarification",
                "message": parsed.clarification,
            }

        return updates

    return parse_intent_node


def make_gather_context_node(context_service: Any | None) -> None:
    """
    Loads client context and enriches metadata with available Layer-3 skills.
    Deterministic — no LLM call.
    """

    async def gather_context_node(state: AgentState) -> dict[str, Any]:
        cur_tier    = state.get("tier", "BASIC")
        nome_empresa = state.get("nome_empresa", "")

        available_skills = [
            {"slug": cfg.slug, "name": cfg.name, "description": cfg.description}
            for cfg in AgentTypeRegistry.for_tier(cur_tier)
        ]

        return {
            "metadata": {
                "tier":             cur_tier,
                "nome_empresa":     nome_empresa,
                "available_skills": [s["slug"] for s in available_skills],
            }
        }

    return gather_context_node


def make_decompose_node(llm: Any, tier: str) -> None:
    """
    (Complex path) Decomposes the user request into domain-level sub-tasks
    without yet deciding which Layer-3 skill handles each one.
    Output is stored in _sub_tasks for the plan node.
    """

    async def decompose_node(state: AgentState) -> dict[str, Any]:
        messages = state.get("messages", [])
        last_msg = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
        if not last_msg:
            return {"_sub_tasks": []}

        system_prompt = await _load_prompt("decompose")

        cid = generate_correlation_id()
        log_llm_call(logger, cid, node="decompose", prompt_preview=system_prompt[:300])
        try:
            async with LLMCallTimer() as timer:
                response: AIMessage = await llm.ainvoke([
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=last_msg.content),
                ])
            log_llm_response(logger, cid, node="decompose", latency_ms=timer.elapsed_ms,
                             response_preview=str(response.content)[:300])
        except Exception as exc:
            logger.error("[decompose] LLM call failed: %s", exc)
            return {"_sub_tasks": []}

        raw_content = str(response.content)
        parsed = _parse_json(raw_content, DecomposeResult)
        if not parsed:
            log_parse_failure(logger, cid, node="decompose", raw_response=raw_content,
                              reason="Could not parse DecomposeResult")
        sub_tasks = parsed.sub_tasks if parsed else []
        logger.info("[decompose] %d sub-tasks identified", len(sub_tasks))
        return {"_sub_tasks": sub_tasks}

    return decompose_node


def make_plan_node(llm: Any, tier: str) -> None:
    """
    (Complex path) Maps decomposed sub-tasks to Layer-3 skills, determines execution
    order, and flags mutations.  Produces the plan list consumed by execute_step.
    """

    async def plan_node(state: AgentState) -> dict[str, Any]:
        sub_tasks = state.get("_sub_tasks") or []
        cur_tier  = state.get("tier") or tier

        if not sub_tasks:
            logger.warning("[plan] No sub-tasks from decompose; plan will be empty")
            return {"plan": [], "_sub_tasks": None}

        skills_desc = AgentTypeRegistry.build_supervisor_description(cur_tier)
        system_prompt = await _load_prompt("plan", {"workers_description": skills_desc})

        cid = generate_correlation_id()
        log_llm_call(logger, cid, node="plan", prompt_preview=system_prompt[:300])
        try:
            async with LLMCallTimer() as timer:
                response: AIMessage = await llm.ainvoke([
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=json.dumps(sub_tasks, ensure_ascii=False)),
                ])
            log_llm_response(logger, cid, node="plan", latency_ms=timer.elapsed_ms,
                             response_preview=str(response.content)[:300])
        except Exception as exc:
            logger.error("[plan] LLM call failed: %s", exc)
            return {"plan": [], "_sub_tasks": None}

        raw_content = str(response.content)
        parsed = _parse_json(raw_content, PlanResult)
        if not parsed or not parsed.plan:
            log_parse_failure(logger, cid, node="plan", raw_response=raw_content,
                              reason="Could not parse PlanResult")
            return {"plan": [], "_sub_tasks": None}

        plan = [_step_to_dict(s) for s in parsed.plan]
        logger.info("[plan] Built plan with %d step(s): %s", len(plan), [s["id"] for s in plan])
        return {"plan": plan, "_sub_tasks": None}

    return plan_node


def make_execute_step_node(llm: Any, mcp_executor: Any, context_service: Any | None) -> None:
    """
    Executes the next pending Layer-3 skill in the plan via a specialist subgraph.

    Finds the first step whose dependencies are all done, enriches its task
    description with prior-step outputs, compiles a cached specialist subgraph
    (``use_specialist_graph``), invokes it with an isolated initial state, and
    updates the plan step status.

    Loops: route_after_step sends control back here until the plan is complete.

    Args:
        llm: LLM client shared with the orchestrator graph.
        mcp_executor: MCPToolExecutor shared with the orchestrator graph.
        context_service: Optional ContextService for client context loading.
    """
    # Per-orchestrator-instance cache: slug → compiled specialist CompiledGraph
    _compiled_specialists: dict[str, Any] = {}

    async def execute_step_node(state: AgentState) -> dict[str, Any]:
        from langchain_core.messages import AIMessage as _AIMessage
        from langchain_core.messages import HumanMessage as _HumanMessage

        plan: list[dict]   = list(state.get("plan") or [])
        step_results: dict[str, Any] = dict(state.get("step_results") or {})

        step = _get_next_step(plan)
        if not step:
            logger.warning("[execute_step] No executable pending step in plan")
            return {}

        raw  = step.get("skill_slug", "")
        slug = raw.removeprefix("delegate_to_").replace("_", "-")
        cfg  = AgentTypeRegistry.get(slug)
        if cfg is None:
            logger.error("[execute_step] Unknown Layer-3 skill slug: '%s'", slug)
            for s in plan:
                if s["id"] == step["id"]:
                    s["status"] = "failed"
                    s["result"] = f"Unknown skill: '{slug}'"
            return {"plan": plan}

        task = _enrich_task(step["task"], step, step_results)
        logger.info("[execute_step] Step '%s' → specialist '%s'", step["id"], slug)

        # Build and cache the specialist subgraph (no checkpointer — ephemeral)
        if slug not in _compiled_specialists:
            from blu_agent_framework.builder import AgentBuilder
            from blu_agent_framework.config import AgentConfig
            from blu_agent_framework.skill_factory import SkillFactory

            agent_cfg = AgentConfig(
                name=cfg.name,
                role=cfg.slug,
                enabled_tools=cfg.enabled_tools,
                max_turns=cfg.max_turns,
            )
            skill_factory = SkillFactory(
                llm=llm,
                mcp_executor=mcp_executor,
                agent_enabled_tools=cfg.enabled_tools,
            )
            compiled = (
                AgentBuilder(agent_cfg, mcp_executor=mcp_executor, checkpointer=None)
                .with_llm(llm)
                .with_skill_factory(skill_factory)
                .use_specialist_graph(cfg)
                .build()
            )
            _compiled_specialists[slug] = compiled
            logger.info("[execute_step] Compiled specialist graph for '%s'", slug)

        graph = _compiled_specialists[slug]

        # Build isolated initial state for the specialist invocation
        from blu_agent_framework.state import create_initial_state

        client_context = state.get("client_context")
        initial_state = create_initial_state(
            session_id=f"orchestrator-step-{step['id']}",
            client_id=str(state.get("client_id") or ""),
            messages=[_HumanMessage(content=task)],
            agent_name=cfg.name,
            agent_role=cfg.slug,
            max_turns=cfg.max_turns,
            client_context=client_context if isinstance(client_context, dict) else {},
        )

        error_summary: str | None = None
        try:
            result_state = await graph.ainvoke(initial_state)
        except Exception as exc:
            logger.exception(
                "[execute_step] Specialist '%s' raised during ainvoke: %s", slug, exc
            )
            error_summary = str(exc)
            result_state = {}

        # Extract final AI message as the step summary
        final_messages = result_state.get("messages", [])
        last_ai = next(
            (m for m in reversed(final_messages) if isinstance(m, _AIMessage) and m.content),
            None,
        )
        summary = (
            str(last_ai.content)
            if last_ai
            else (error_summary or "Specialist completed without a final response.")
        )

        for s in plan:
            if s["id"] == step["id"]:
                s["status"] = "done" if not error_summary else "failed"
                s["result"] = summary

        step_results[step["id"]] = summary

        updates: dict[str, Any] = {"plan": plan, "step_results": step_results}
        structured_data = result_state.get("structured_data")
        if structured_data:
            updates["structured_data"] = structured_data

        return updates

    return execute_step_node


def make_synthesize_node(llm: Any) -> None:
    """
    Combines all step results into a single, coherent user-facing response.
    Last node before end.
    """

    async def synthesize_node(state: AgentState) -> dict[str, Any]:
        plan         = state.get("plan") or []
        step_results = state.get("step_results") or {}
        messages     = state.get("messages", [])

        original_request = next(
            (m.content for m in reversed(messages) if isinstance(m, HumanMessage)), ""
        )

        results_block = "\n\n".join(
            f"[{s['id']} — {s['skill_slug']}]:\n{step_results.get(s['id'], '(no result)')}"
            for s in plan
        )

        system_prompt = await _load_prompt("synthesize")

        try:
            response: AIMessage = await llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=(
                    f"User request: {original_request}\n\n"
                    f"Specialist results:\n{results_block}"
                )),
            ])
        except Exception as exc:
            logger.error("[synthesize] LLM call failed: %s", exc)
            response = AIMessage(content="I was unable to compile the results. Please try again.")

        return {"messages": [response]}

    return synthesize_node


# ---------------------------------------------------------------------------
# Static nodes (no LLM / MCP dependency)
# ---------------------------------------------------------------------------

async def confirm_node(state: AgentState) -> dict[str, Any]:
    """
    Presents the plan or a clarifying question to the user and waits.

    On the next user message, parse_intent_node detects pending_confirmation
    and resolves it to confirmed=True/False before proceeding.
    """
    pending_conf = state.get("pending_confirmation")
    plan         = state.get("plan") or []

    if pending_conf and pending_conf.get("type") == "clarification":
        question = pending_conf.get("message", "Could you clarify what you need?")
        return {
            "messages": [AIMessage(content=question)],
        }

    # Mutation / plan confirmation
    mutation_steps = [s for s in plan if s.get("is_mutation")]
    if mutation_steps:
        steps_text = _format_plan(mutation_steps)
        message = (
            "I'm about to perform the following actions:\n"
            f"{steps_text}\n\n"
            "Should I proceed? (yes / no)"
        )
    elif plan:
        message = (
            f"Here's my plan:\n{_format_plan(plan)}\n\n"
            "Should I proceed? (yes / no)"
        )
    else:
        message = "I'm ready to proceed — shall I continue? (yes / no)"

    return {
        "messages": [AIMessage(content=message)],
        "pending_confirmation": {
            "type":    "plan",
            "message": message,
        },
    }


async def escalate_node(state: AgentState) -> dict[str, Any]:
    """Handles failed steps — logs, generates user message, and ends the graph."""
    plan   = state.get("plan") or []
    failed = [s for s in plan if s["status"] == "failed"]

    if failed:
        desc = "; ".join(
            f"{s['id']} ({s['skill_slug']}): {s.get('result') or 'unknown error'}"
            for s in failed
        )
        message = (
            f"I encountered an issue completing your request. "
            f"The following step(s) failed: {desc}.\n"
            "Please try again or rephrase your request."
        )
    else:
        message = "I wasn't able to complete your request. Please try again."

    logger.error("[escalate] Failed: %s", [s["id"] for s in failed])
    return {
        "messages":  [AIMessage(content=message)],
        "ended":     True,
        "end_reason": "escalation",
    }


# ---------------------------------------------------------------------------
# Routing functions
# ---------------------------------------------------------------------------

def route_after_context(state: AgentState) -> str:
    """
    Routes after gather_context.

    Priority order:
    1. Resuming after confirmation  → execute_step
    2. User rejected                → end
    3. Pending clarification        → confirm
    4. complex                      → decompose
    5. uncertain                    → confirm
    6. simple (default)             → execute_step
    """
    confirmed = state.get("confirmed")
    if confirmed is True:
        return "execute_step"
    if confirmed is False:
        return "end"

    if state.get("pending_confirmation"):
        return "confirm"

    complexity = state.get("complexity", "simple")
    if complexity == "complex":
        return "decompose"
    if complexity == "uncertain":
        return "confirm"
    return "execute_step"


def route_after_plan(state: AgentState) -> str:
    """After plan_node: confirm if any mutation steps exist, else execute."""
    plan = state.get("plan") or []
    if not plan:
        return "escalate"
    if any(s.get("is_mutation") for s in plan):
        return "confirm"
    return "execute_step"


def route_after_step(state: AgentState) -> str:
    """
    Loop control for execute_step.

    - Any failed step  → escalate
    - More pending     → execute_step (continue loop)
    - All done         → synthesize
    """
    plan = state.get("plan") or []
    if any(s["status"] == "failed" for s in plan):
        return "escalate"
    if _get_next_step(plan):
        return "execute_step"
    return "synthesize"
