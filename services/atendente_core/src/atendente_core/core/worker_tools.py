"""
Worker Meta-Tools — StructuredTools that the supervisor uses to delegate to workers.

Each tool wraps `invoke_worker()` from worker_factory. The supervisor LLM
picks these via tool_calls just like it picks MCP tools today, but instead
of executing MCP directly, they spin up a worker agent loop in-process.

The tools are built dynamically from WorkerRegistry so adding a new worker
type only requires a registry entry — no code changes here.
"""

import json
import logging
from typing import Any
from uuid import UUID

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from atendente_core.core.worker_factory import WorkerResult, invoke_worker
from atendente_core.core.worker_registry import WorkerConfig, WorkerRegistry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared input schema for all delegation tools
# ---------------------------------------------------------------------------


class DelegationInput(BaseModel):
    """Input for a worker delegation tool."""

    task: str = Field(
        description=(
            "Clear, specific task description for the specialist worker. "
            "Include all relevant details from the user's question."
        )
    )


# ---------------------------------------------------------------------------
# Tool builder
# ---------------------------------------------------------------------------


def _make_delegation_tool(
    worker: WorkerConfig,
    *,
    session_id: str,
    cliente_id: UUID | None,
    nome_empresa: str,
    context_sections: str,
    context_service: Any | None,
) -> StructuredTool:
    """
    Create a StructuredTool that delegates to a specific worker.

    The returned tool is async-compatible and captures the session context
    via closure so the supervisor LLM only needs to provide `task`.
    """
    tool_name = f"delegate_to_{worker.slug.replace('-', '_')}"

    async def _invoke(task: str) -> str:
        logger.info(f"[DelegationTool] {tool_name} invoked with task: {task[:120]}...")
        result: WorkerResult = await invoke_worker(
            worker_slug=worker.slug,
            task=task,
            session_id=session_id,
            cliente_id=cliente_id,
            nome_empresa=nome_empresa,
            context_sections=context_sections,
            context_service=context_service,
        )

        if result.error:
            logger.warning(f"[DelegationTool] {tool_name} error: {result.error}")
            return f"Worker error: {result.error}\n{result.summary}"

        # Return JSON with summary + structured_data marker + worker identity
        response: dict[str, Any] = {
            "summary": result.summary,
            "worker_slug": result.worker_slug,
        }
        if result.structured_data:
            response["structured_data"] = result.structured_data
        if result.tool_calls_made:
            response["tools_used"] = result.tool_calls_made

        return json.dumps(response, ensure_ascii=False)

    return StructuredTool(
        name=tool_name,
        description=worker.description,
        func=lambda task: None,  # sync stub (not used)
        coroutine=_invoke,
        args_schema=DelegationInput,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_worker_tools(
    tier: str,
    *,
    session_id: str,
    cliente_id: UUID | None = None,
    nome_empresa: str = "Blu",
    context_sections: str = "",
    context_service: Any | None = None,
) -> list[StructuredTool]:
    """
    Build delegation StructuredTools for all workers available at *tier*.

    These tools are bound to the supervisor LLM alongside any simple
    public tools that the supervisor handles directly (e.g., greetings).

    Args:
        tier: Client tier (e.g., "BASIC", "SME", "PREMIUM")
        session_id: Current session ID
        cliente_id: Client UUID
        nome_empresa: Company name for worker prompts
        context_sections: Compiled context for worker prompts
        context_service: For Redis-cached prompt loading

    Returns:
        List of StructuredTool instances (one per available worker)
    """
    workers = WorkerRegistry.get_available_workers(tier)
    tools: list[StructuredTool] = []

    for worker in workers:
        tool = _make_delegation_tool(
            worker,
            session_id=session_id,
            cliente_id=cliente_id,
            nome_empresa=nome_empresa,
            context_sections=context_sections,
            context_service=context_service,
        )
        tools.append(tool)
        logger.debug(f"[WorkerTools] Built delegation tool: {tool.name}")

    logger.info(
        f"[WorkerTools] Built {len(tools)} delegation tools for tier {tier}: "
        f"{[t.name for t in tools]}"
    )
    return tools


def is_delegation_tool_call(tool_name: str) -> bool:
    """Check whether a tool_call name corresponds to a worker delegation."""
    return tool_name.startswith("delegate_to_")
