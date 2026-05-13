"""
blu_agent_framework.supervisor
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Worker invocation engine and graph primitives for use_supervisor_graph().

_WorkerInvoker runs AgentTypeConfig entries as isolated LLM+tool loops
with retry logic, structured-data extraction, and MCP reconnect handling.

Graph pieces exposed for AgentBuilder:
  - route_after_supervisor  — fan-out routing (pending_tool_calls → Send objects)
  - route_after_workers     — fan-in routing (loop back to supervisor)
  - collect_worker_results_node — clears pending_tool_calls after fan-in
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.types import Send

from pydantic import BaseModel, Field

from blu_agent_framework.registry import AgentTypeConfig, AgentTypeRegistry
from blu_agent_framework.state import AgentState

if TYPE_CHECKING:
    from blu_agent_framework.mcp_executor import MCPToolExecutor

logger = logging.getLogger(__name__)

_MAX_TOOL_OUTPUT_CHARS = 4_000


# ---------------------------------------------------------------------------
# Delegation tool schema — stable Pydantic model reused across calls.
# ---------------------------------------------------------------------------

class _DelegationInput(BaseModel):
    task: str = Field(
        description=(
            "Clear, specific task description for the specialist worker. "
            "Include all relevant details from the user's question."
        )
    )


# =============================================================================
# Public result types
# =============================================================================


class WorkerTurnLimitError(Exception):
    """Raised when a worker with on_max_turns='raise' exceeds its turn budget."""

    def __init__(self, worker_slug: str, max_turns: int) -> None:
        self.worker_slug = worker_slug
        self.max_turns = max_turns
        super().__init__(
            f"Worker '{worker_slug}' exceeded max_turns={max_turns}."
        )


@dataclass
class WorkerResult:
    """Result returned from a single worker invocation."""

    summary: str
    worker_slug: str = ""
    structured_data: dict[str, Any] | None = None
    tool_calls_made: list[str] = field(default_factory=list)
    error: str | None = None


# =============================================================================
# Internal helpers
# =============================================================================


def _is_transient_error(exc: Exception) -> bool:
    """Detect LLM errors worth retrying (Ollama 500s, network blips)."""
    try:
        from ollama._types import ResponseError  # type: ignore[import]
        if isinstance(exc, ResponseError):
            return True
    except ImportError:
        pass
    msg = str(exc).lower()
    return "internal server error" in msg or "status code: -1" in msg


def _extract_structured_data(
    raw_output: str, tool_name: str
) -> tuple[str, dict[str, Any] | None]:
    """
    Split structured_data out of a JSON tool result.

    Returns (llm_summary, frontend_structured_data).
    The summary is compact enough for LLM context; the full data goes to the
    frontend via state.structured_data.
    """
    try:
        parsed = json.loads(raw_output) if isinstance(raw_output, str) else raw_output
        if not isinstance(parsed, dict) or not parsed.get("structured_data"):
            return raw_output, None

        full_data: dict = parsed["structured_data"]
        frontend = dict(full_data)
        rows: list = frontend.get("rows", [])
        if len(rows) > 20:
            frontend["rows"] = rows[:20]
            frontend["truncated"] = True
            frontend["total_rows"] = len(rows)
        frontend["source_tool"] = tool_name

        # Compact summary for LLM
        total = parsed.get("row_count", len(rows))
        cols: list = full_data.get("columns", [])
        parts = [f"{total} registros encontrados."]
        if cols:
            parts.append(f"Colunas: {', '.join(cols)}")
        for i, row in enumerate(rows[:3]):
            parts.append(f"  Exemplo {i + 1}: {row}")
        if total > 3:
            parts.append(f"(Mostrando 3 de {total}. Dados completos na tabela.)")

        parsed.pop("structured_data")
        parsed["output"] = "\n".join(parts)
        return json.dumps(parsed, ensure_ascii=False), frontend

    except (json.JSONDecodeError, TypeError):
        return raw_output, None


# =============================================================================
# _WorkerInvoker
# =============================================================================


class _WorkerInvoker:
    """
    Runs AgentTypeConfig workers as in-process LLM+tool loops.

    One instance is shared between the supervisor node and the worker
    executor node for a single compiled graph.  Prompt cache is keyed by
    (slug, nome_empresa) so multiple sessions can share cached prompts.
    """

    def __init__(self, llm: Any, mcp_executor: MCPToolExecutor) -> None:
        self._llm = llm
        self._mcp_executor = mcp_executor
        self._prompt_cache: dict[str, str] = {}

    async def invoke(
        self,
        cfg: AgentTypeConfig,
        task: str,
        nome_empresa: str = "",
        context_service: Any = None,
    ) -> WorkerResult:
        system_prompt = await self._get_prompt(cfg, nome_empresa, context_service)

        lc_tools = await self._mcp_executor.get_lc_tools(cfg.enabled_tools)
        tool_map = {t.name: t for t in lc_tools}

        bound_llm = self._llm.bind_tools(lc_tools) if lc_tools else self._llm
        messages: list = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=task),
        ]

        structured_data: dict[str, Any] | None = None
        calls_made: list[str] = []

        for turn in range(cfg.max_turns):
            response: AIMessage | None = None
            last_error: Exception | None = None

            for attempt in range(cfg.max_retries + 1):
                try:
                    response = await bound_llm.ainvoke(messages)
                    break
                except Exception as exc:
                    last_error = exc
                    if attempt < cfg.max_retries and _is_transient_error(exc):
                        logger.warning(
                            "[Worker:%s] Transient error (attempt %d/%d): %s",
                            cfg.slug, attempt + 1, cfg.max_retries, exc,
                        )
                        await asyncio.sleep(1.0 * (attempt + 1))
                    else:
                        logger.exception("[Worker:%s] LLM error on turn %d", cfg.slug, turn)
                        return WorkerResult(
                            summary=f"Worker error: {last_error}",
                            worker_slug=cfg.slug,
                            structured_data=structured_data,
                            error=str(last_error),
                        )

            if response is None:
                return WorkerResult(
                    summary=f"Worker error: {last_error}",
                    worker_slug=cfg.slug,
                    error=str(last_error),
                )

            messages.append(response)

            if not response.tool_calls:
                logger.info("[Worker:%s] Final response on turn %d", cfg.slug, turn)
                return WorkerResult(
                    summary=str(response.content or ""),
                    worker_slug=cfg.slug,
                    structured_data=structured_data,
                    tool_calls_made=calls_made,
                )

            calls_made.extend(tc["name"] for tc in response.tool_calls)
            tool_msgs, sd_list = await self._run_tools(response.tool_calls, tool_map)
            messages.extend(tool_msgs)
            if sd_list and structured_data is None:
                structured_data = sd_list[0]

        # max_turns hit
        last_ai = next(
            (m for m in reversed(messages) if isinstance(m, AIMessage) and m.content),
            None,
        )
        summary = (
            str(last_ai.content)
            if last_ai
            else "Worker reached maximum turns without a final answer."
        )

        if cfg.on_max_turns == "raise":
            raise WorkerTurnLimitError(cfg.slug, cfg.max_turns)

        logger.warning("[Worker:%s] Hit max_turns (%d)", cfg.slug, cfg.max_turns)
        return WorkerResult(
            summary=summary,
            worker_slug=cfg.slug,
            structured_data=structured_data,
            tool_calls_made=calls_made,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _get_prompt(
        self,
        cfg: AgentTypeConfig,
        nome_empresa: str,
        context_service: Any,
    ) -> str:
        cache_key = f"{cfg.slug}:{nome_empresa}"
        if cache_key in self._prompt_cache:
            return self._prompt_cache[cache_key]

        variables: dict[str, Any] = {
            "nome_empresa": nome_empresa,
            "agent_name": cfg.name,
            "agent_description": cfg.description,
            "context_sections": "",
            "tools_description": "",
            "csv_datasets": [],
            "document_names": [],
            "csv_datasets_details": "",
            "collected_context": {},
            "filled_fields": 0,
            "total_fields": 0,
            "uploaded_file_count": 0,
            "google_connected": False,
            "knowledge_updated_at": "",
            "document_count": 0,
        }

        prompt = ""

        if cfg.prompt_name:
            try:
                from blu_prompt_management import build_prompt  # type: ignore[import]
                prompt = await build_prompt(
                    name=cfg.prompt_name,
                    variables=variables,
                    context_service=context_service,
                )
            except Exception as exc:
                logger.warning("[Worker:%s] build_prompt failed: %s", cfg.slug, exc)

        if not prompt and cfg.fragments:
            try:
                from blu_prompt_management import compose_prompt  # type: ignore[import]
                prompt = await compose_prompt(
                    fragments=cfg.fragments,
                    variables=variables,
                    context_service=context_service,
                )
            except Exception as exc:
                logger.warning("[Worker:%s] compose_prompt failed: %s", cfg.slug, exc)

        if not prompt:
            prompt = (
                f"You are {cfg.name}, a specialist assistant"
                f"{f' for {nome_empresa}' if nome_empresa else ''}.\n"
                f"{cfg.description}\n\n"
                "Answer in the user's language. Use available tools."
            )

        self._prompt_cache[cache_key] = prompt
        return prompt

    async def _run_tools(
        self,
        tool_calls: list[dict],
        tool_map: dict,
    ) -> tuple[list[ToolMessage], list[dict[str, Any]]]:
        """Execute tool calls in parallel with MCP reconnect on stream errors."""

        async def _one(tc: dict) -> tuple[ToolMessage, dict[str, Any] | None]:
            name = tc["name"]
            call_id = tc["id"]
            args = {
                k: v for k, v in (tc.get("args") or {}).items()
                if k not in ("cliente_id", "user_jwt")
            }

            if name not in tool_map:
                return (
                    ToolMessage(content=f"Tool '{name}' not found.", tool_call_id=call_id, name=name),
                    None,
                )

            try:
                mcp_mgr = await self._mcp_executor._get_mcp_manager()  # noqa: SLF001
                raw = await mcp_mgr.call_tool(name, args)
            except Exception as exc:
                # MCP stream error — attempt one reconnect
                from anyio import BrokenResourceError, ClosedResourceError
                if isinstance(exc, (BrokenResourceError, ClosedResourceError)):
                    logger.warning(
                        "[Worker] MCP stream error on '%s': %s — reconnecting", name, exc
                    )
                    try:
                        mcp_mgr = await self._mcp_executor._get_mcp_manager()  # noqa: SLF001
                        await mcp_mgr.disconnect()
                        await mcp_mgr.connect()
                        raw = await mcp_mgr.call_tool(name, args)
                    except Exception as retry_exc:
                        logger.exception("[Worker] Retry failed for '%s': %s", name, retry_exc)
                        return (
                            ToolMessage(content=f"Connection error: {exc}", tool_call_id=call_id, name=name),
                            None,
                        )
                else:
                    logger.exception("[Worker] Error executing '%s'", name)
                    return (
                        ToolMessage(content=f"Error: {exc}", tool_call_id=call_id, name=name),
                        None,
                    )

            output: str
            if hasattr(raw, "content") and raw.content:
                output = "\n".join(
                    item.text if hasattr(item, "text") else str(item)
                    for item in raw.content
                )
            else:
                output = str(raw)

            llm_text, sd = _extract_structured_data(output, name)
            if len(llm_text) > _MAX_TOOL_OUTPUT_CHARS:
                llm_text = llm_text[:_MAX_TOOL_OUTPUT_CHARS] + "\n[truncated]"

            return ToolMessage(content=llm_text, tool_call_id=call_id, name=name), sd

        results = await asyncio.gather(*[_one(tc) for tc in tool_calls])
        msgs = [r[0] for r in results]
        sds = [r[1] for r in results if r[1] is not None]
        return msgs, sds


# =============================================================================
# Delegation tool factory
# =============================================================================


def build_delegation_tools(tier: str) -> list:
    """
    Build StructuredTool instances for supervisor LLM tool-binding.

    Each tool's coroutine is a no-op — the LLM's tool_calls are routed to
    execute_worker nodes via Send; these tools exist only as routing schemas.

    Args:
        tier: Client tier string (e.g., "BASIC", "SME", "PREMIUM")

    Returns:
        List of StructuredTool instances, one per available agent type.
    """
    from langchain_core.tools import StructuredTool

    async def _noop(task: str) -> str:
        return ""

    configs = AgentTypeRegistry.for_tier(tier)
    tools = []
    for cfg in configs:
        tool_name = f"delegate_to_{cfg.slug.replace('-', '_')}"
        tool = StructuredTool(
            name=tool_name,
            description=cfg.description,
            func=lambda task: "",
            coroutine=_noop,
            args_schema=_DelegationInput,
        )
        tools.append(tool)

    logger.debug("[build_delegation_tools] %d tools for tier %s", len(tools), tier)
    return tools


# =============================================================================
# Graph primitives used by AgentBuilder
# =============================================================================


def route_after_supervisor(
    state: AgentState,
) -> list[Send] | str:
    """
    Fan-out routing from the supervisor node.

    Returns a list of Send objects (one per pending delegate call) when the
    supervisor LLM has requested worker delegations, or a plain string route
    for the elicitation and end cases.
    """
    if state.get("ended"):
        return "end"

    pending = state.get("pending_tool_calls") or []
    if pending:
        return [
            Send(
                "execute_worker",
                {
                    "tool_call": tc,
                    "cliente_id": str(state.get("cliente_id") or ""),
                    "session_id": state.get("session_id", ""),
                    "metadata": dict(state.get("metadata") or {}),
                    "nome_empresa": state.get("nome_empresa", ""),
                },
            )
            for tc in pending
        ]

    if state.get("pending_elicitation"):
        return "elicit"

    return "end"


def route_after_workers(state: AgentState) -> str:
    """Fan-in routing after all worker results are collected."""
    if state.get("ended"):
        return "end"
    if state.get("pending_elicitation"):
        return "elicit"
    return "supervisor"


async def collect_worker_results_node(state: AgentState) -> dict[str, Any]:
    """
    Fan-in aggregator: runs once after all parallel execute_worker nodes complete.

    Worker results are already merged into state via reducers on `messages` and
    `structured_data_list`.  This node just clears pending_tool_calls so the
    supervisor loop starts clean.
    """
    structured_list = state.get("structured_data_list") or []
    updates: dict[str, Any] = {"pending_tool_calls": []}

    # Promote the first structured result to the top-level field for
    # backward-compat readers that only check structured_data.
    if structured_list and not state.get("structured_data"):
        updates["structured_data"] = structured_list[0]

    return updates
