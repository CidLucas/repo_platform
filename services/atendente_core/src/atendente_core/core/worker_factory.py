"""
Worker Factory — Builds and invokes worker agents in-process.

Workers reuse atendente_core's existing mcp_manager and Redis checkpointer.
Each worker is a lightweight LLM invocation loop: compose prompt from fragments,
bind the worker's tool subset, invoke, execute tools, return result.

Workers are cached per (session_id, worker_slug) to avoid recomposing prompts
on repeated delegations within the same conversation.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import UUID

from anyio import BrokenResourceError, ClosedResourceError
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

# Maximum retries for transient LLM errors (e.g. Ollama Cloud 500s)
_LLM_MAX_RETRIES = 2
_LLM_RETRY_DELAY_SECS = 1.0

from atendente_core.core.config import get_settings
from atendente_core.core.worker_registry import WorkerConfig, WorkerRegistry

# Reuse atendente_core's shared MCP connection
from atendente_core.services.mcp_client import mcp_manager
from vizu_llm_service import get_model
from vizu_prompt_management import compose_prompt

if TYPE_CHECKING:
    from vizu_context_service import ContextService

logger = logging.getLogger(__name__)

# Maximum tool→LLM cycles per worker invocation
_WORKER_MAX_TURNS = 3

# Maximum chars from tool output sent to worker LLM
_WORKER_MAX_TOOL_OUTPUT = 4000


def _is_transient_llm_error(exc: Exception) -> bool:
    """Check if an LLM error is transient and worth retrying."""
    try:
        from ollama._types import ResponseError
        if isinstance(exc, ResponseError):
            return True
    except ImportError:
        pass
    err_str = str(exc).lower()
    return "internal server error" in err_str or "status code: -1" in err_str


@dataclass
class WorkerResult:
    """Result returned by a worker invocation."""

    summary: str  # Text summary for the supervisor/user
    worker_slug: str = ""  # Worker identifier for traceability
    structured_data: dict[str, Any] | None = None  # Tabular data for frontend
    tool_calls_made: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class _CachedWorkerPrompt:
    """Cached prompt + tools for a worker within a session."""

    system_prompt: str
    tool_names: set[str]


# Module-level prompt cache: (session_id, worker_slug) → prompt
_prompt_cache: dict[tuple[str, str], _CachedWorkerPrompt] = {}


def clear_worker_cache(session_id: str | None = None) -> None:
    """Clear cached worker prompts. If session_id given, clear only that session."""
    global _prompt_cache
    if session_id is None:
        _prompt_cache = {}
    else:
        _prompt_cache = {k: v for k, v in _prompt_cache.items() if k[0] != session_id}


def _create_llm_data_summary(structured_data: dict, full_output: dict) -> str:
    """Create concise LLM-friendly summary of tool results (reused from nodes.py pattern)."""
    rows = structured_data.get("rows", [])
    columns = structured_data.get("columns", [])
    total_rows = full_output.get("row_count", len(rows))

    parts = [f"{total_rows} registros encontrados."]
    if columns:
        parts.append(f"Colunas: {', '.join(columns)}")
    if rows:
        sample = rows[:3]
        parts.append("\n".join(f"  Exemplo {i+1}: {r}" for i, r in enumerate(sample)))
    if total_rows > 3:
        parts.append(f"(Mostrando 3 de {total_rows}. Dados completos na tabela.)")
    return "\n".join(parts)


async def _build_worker_prompt(
    worker: WorkerConfig,
    nome_empresa: str,
    context_sections: str,
    context_service: "ContextService | None",
) -> str:
    """Compose the worker's system prompt from its fragment list."""
    variables = {
        "nome_empresa": nome_empresa,
        "context_sections": context_sections,
        # Workers don't get tools_description in prompt — tools are bound via LLM
        "tools_description": "",
        # Standalone fragment variables (some fragments reference these)
        "agent_name": worker.name,
        "agent_description": worker.description,
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

    try:
        prompt = await compose_prompt(
            fragments=worker.fragments,
            variables=variables,
            context_service=context_service,
        )
        if prompt and prompt.strip():
            return prompt
    except Exception as e:
        logger.warning(f"[WorkerFactory] Fragment composition failed for {worker.slug}: {e}")

    # Minimal fallback
    return (
        f"You are {worker.name}, a specialist assistant for {nome_empresa}.\n"
        f"{worker.description}\n\n"
        f"Answer in the user's language. Use available tools."
    )


async def _execute_worker_tools(
    tool_calls: list[dict],
    tool_map: dict,
) -> tuple[list[ToolMessage], list[dict]]:
    """
    Execute tool calls for a worker (parallel, same as execute_tools_node).

    Returns (tool_messages, list_of_structured_data).
    Each execute returns a tuple so structured_data is collected after gather
    (no race condition with nonlocal under asyncio.gather).
    """

    async def _run_one(tc: dict) -> tuple[ToolMessage, dict | None]:
        name = tc["name"]
        call_id = tc["id"]
        tool = tool_map.get(name)
        if not tool:
            return ToolMessage(
                content=f"Tool '{name}' not found.", tool_call_id=call_id, name=name
            ), None

        args = dict(tc.get("args") or {})
        # Strip internal params
        for p in ("cliente_id", "user_jwt"):
            args.pop(p, None)

        try:
            output = await mcp_manager.call_tool(name, args)

            # Unwrap MCP CallToolResult
            if hasattr(output, "content") and output.content:
                output = "\n".join(
                    item.text if hasattr(item, "text") else str(item) for item in output.content
                )

            # Extract structured_data before truncation
            tool_structured_data: dict | None = None
            try:
                parsed = json.loads(output) if isinstance(output, str) else output
                if isinstance(parsed, dict) and parsed.get("structured_data"):
                    full_data = parsed["structured_data"]
                    frontend_data = full_data.copy()
                    if frontend_data.get("rows") and len(frontend_data["rows"]) > 20:
                        frontend_data["rows"] = frontend_data["rows"][:20]
                        frontend_data["truncated"] = True
                        frontend_data["total_rows"] = len(full_data["rows"])
                    frontend_data["source_tool"] = name
                    tool_structured_data = frontend_data

                    llm_summary = _create_llm_data_summary(full_data, parsed)
                    parsed["output"] = llm_summary
                    del parsed["structured_data"]
                    output = json.dumps(parsed, ensure_ascii=False)
            except (json.JSONDecodeError, TypeError):
                pass

            output_str = str(output)
            if len(output_str) > _WORKER_MAX_TOOL_OUTPUT:
                output_str = output_str[:_WORKER_MAX_TOOL_OUTPUT] + "\n[truncated]"

            return ToolMessage(content=output_str, tool_call_id=call_id, name=name), tool_structured_data

        except (BrokenResourceError, ClosedResourceError) as e:
            logger.warning(f"[Worker] MCP stream error on '{name}': {e}, reconnecting")
            try:
                await mcp_manager.disconnect()
                await mcp_manager.connect()
                # Retry once
                output = await mcp_manager.call_tool(name, args)
                if hasattr(output, "content") and output.content:
                    output = "\n".join(
                        item.text if hasattr(item, "text") else str(item)
                        for item in output.content
                    )
                output_str = str(output)[:_WORKER_MAX_TOOL_OUTPUT]
                return ToolMessage(content=output_str, tool_call_id=call_id, name=name), None
            except Exception as retry_err:
                logger.exception(f"[Worker] Retry failed for '{name}': {retry_err}")
                return ToolMessage(
                    content=f"Connection error: {e}", tool_call_id=call_id, name=name
                ), None
        except Exception as e:
            logger.exception(f"[Worker] Error executing '{name}': {e}")
            return ToolMessage(
                content=f"Error: {e}", tool_call_id=call_id, name=name
            ), None

    raw_results = await asyncio.gather(*[_run_one(tc) for tc in tool_calls])
    messages = [msg for msg, _ in raw_results]
    all_structured_data = [sd for _, sd in raw_results if sd is not None]
    return messages, all_structured_data


async def invoke_worker(
    worker_slug: str,
    task: str,
    *,
    session_id: str,
    cliente_id: UUID | None = None,
    nome_empresa: str = "Vizu",
    context_sections: str = "",
    context_service: "ContextService | None" = None,
) -> WorkerResult:
    """
    Build (or fetch cached) a worker and run it to completion on *task*.

    The worker shares mcp_manager with the supervisor. It runs a simple
    LLM loop: prompt → bind tools → invoke → execute tools → loop or return.

    Args:
        worker_slug: Worker identifier (e.g., "data-analyst")
        task: The user/supervisor task to execute
        session_id: Current conversation session
        cliente_id: Client UUID (for tool auth — already set on mcp_manager)
        nome_empresa: Company name for prompt variables
        context_sections: Compiled context sections text
        context_service: For Redis-cached prompt loading

    Returns:
        WorkerResult with summary text and optional structured_data
    """
    worker = WorkerRegistry.get_worker(worker_slug)
    if not worker:
        return WorkerResult(summary="", worker_slug=worker_slug, error=f"Unknown worker: {worker_slug}")

    # 1. Build or retrieve cached prompt
    cache_key = (session_id, worker_slug)
    cached = _prompt_cache.get(cache_key)
    if cached:
        system_prompt = cached.system_prompt
        allowed_tool_names = cached.tool_names
    else:
        system_prompt = await _build_worker_prompt(
            worker, nome_empresa, context_sections, context_service
        )
        allowed_tool_names = set(worker.enabled_tools)
        _prompt_cache[cache_key] = _CachedWorkerPrompt(
            system_prompt=system_prompt, tool_names=allowed_tool_names
        )

    logger.info(
        f"[Worker:{worker_slug}] Invoking with task ({len(task)} chars), "
        f"prompt ({len(system_prompt)} chars), tools={sorted(allowed_tool_names)}"
    )

    # 2. Filter MCP tools to the worker's subset
    all_tools = mcp_manager.tools or []
    worker_tools = [t for t in all_tools if t.name in allowed_tool_names]
    tool_map = {t.name: t for t in worker_tools}

    if not worker_tools:
        logger.warning(f"[Worker:{worker_slug}] No matching MCP tools found")

    # 3. LLM invocation loop
    llm = get_model()
    if worker_tools:
        bound_llm = llm.bind_tools(worker_tools)
    else:
        bound_llm = llm

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=task),
    ]

    structured_data: dict | None = None
    calls_made: list[str] = []

    for turn in range(_WORKER_MAX_TURNS):
        last_llm_error: Exception | None = None
        response: AIMessage | None = None

        for retry in range(_LLM_MAX_RETRIES + 1):
            try:
                response = await bound_llm.ainvoke(messages)
                break
            except Exception as e:
                last_llm_error = e
                if retry < _LLM_MAX_RETRIES and _is_transient_llm_error(e):
                    logger.warning(
                        f"[Worker:{worker_slug}] Transient LLM error on turn {turn} "
                        f"(retry {retry+1}/{_LLM_MAX_RETRIES}): {e}"
                    )
                    await asyncio.sleep(_LLM_RETRY_DELAY_SECS * (retry + 1))
                else:
                    logger.exception(f"[Worker:{worker_slug}] LLM error on turn {turn}: {e}")
                    return WorkerResult(
                        summary=f"Worker error: {e}",
                        worker_slug=worker_slug,
                        structured_data=structured_data,
                        tool_calls_made=calls_made,
                        error=str(e),
                    )

        if response is None:
            logger.error(f"[Worker:{worker_slug}] All retries exhausted on turn {turn}")
            return WorkerResult(
                summary=f"Worker error: {last_llm_error}",
                worker_slug=worker_slug,
                structured_data=structured_data,
                tool_calls_made=calls_made,
                error=str(last_llm_error),
            )

        messages.append(response)

        # If no tool calls, we have the final answer
        if not response.tool_calls:
            logger.info(f"[Worker:{worker_slug}] Final response on turn {turn}")
            return WorkerResult(
                summary=response.content or "",
                worker_slug=worker_slug,
                structured_data=structured_data,
                tool_calls_made=calls_made,
            )

        # Execute tool calls
        calls_made.extend(tc["name"] for tc in response.tool_calls)
        tool_msgs, extracted_list = await _execute_worker_tools(response.tool_calls, tool_map)
        messages.extend(tool_msgs)

        # Use first structured_data from this turn if we don't have one yet
        if extracted_list and structured_data is None:
            structured_data = extracted_list[0]

    # Max turns exceeded — use last response content if available
    last_ai = next(
        (m for m in reversed(messages) if isinstance(m, AIMessage) and m.content), None
    )
    summary = last_ai.content if last_ai else "Worker reached maximum turns without a final answer."

    logger.warning(f"[Worker:{worker_slug}] Hit max turns ({_WORKER_MAX_TURNS})")
    return WorkerResult(
        summary=summary,
        worker_slug=worker_slug,
        structured_data=structured_data,
        tool_calls_made=calls_made,
    )
