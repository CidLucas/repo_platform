"""
Service layer for agent_api.

ChatService — supervisor-mode sync + streaming chat.
AgentService — standalone agent streaming chat.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from blu_context_service import ContextService
from blu_llm_service import MODEL_MAPPINGS, LLMProvider, ModelTier, get_llm_settings
from blu_prompt_management import build_prompt
from blu_prompt_management.variables import VariableExtractor
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent_api.config import get_settings
from agent_api.core.factory import (
    BuiltAgent,
    get_context_service,
    get_factory,
    get_mcp_manager,
)

import re

logger = logging.getLogger(__name__)

# Fire-and-forget task registry (prevents GC of background tasks)
_background_tasks: set = set()

# Post-processing: strip internal model tokens that leak through the chat template.
# Covers: <|token|>, <think>...</think>, commentary<...>, analysis<...>
_INTERNAL_TOKEN_RE = re.compile(
    r"<\|[^|]*\|>"           # <|im_end|>, <|channel|>, etc.
    r"|<think>.*?</think>"   # chain-of-thought blocks (DeepSeek, Qwen3)
    r"|commentary<.*?>"      # commentary injection artifacts
    r"|analysis<.*?>",       # analysis injection artifacts
    re.DOTALL,
)


def _clean_response(text: str) -> str:
    """Remove internal model tokens from a response string."""
    cleaned = _INTERNAL_TOKEN_RE.sub("", text)
    return cleaned.strip()


def _render_company_profile(company_profile: dict | None) -> str:
    """Render company_profile JSONB dict to a markdown string for prompt injection."""
    if not company_profile or not isinstance(company_profile, dict):
        return ""
    lines = []
    for key, value in company_profile.items():
        if value:
            label = key.replace("_", " ").title()
            lines.append(f"- **{label}**: {value}")
    return "\n".join(lines)


async def _build_frontdesk_prompt(
    client_ctx: Any,
    context_service: ContextService,
) -> str:
    """Assemble variables from client_ctx and call build_prompt for agents/frontdesk."""
    from blu_agent_framework.registry import AgentTypeRegistry

    cfg = AgentTypeRegistry.get("frontdesk")
    prompt_name = cfg.prompt_name if cfg else "agents/frontdesk"
    nome_empresa: str = getattr(client_ctx, "nome_empresa", "") or ""

    # SQL schema: use per-client table configs; fall back to static analytics_v2 schema.
    sql_schema_context = VariableExtractor.render_sql_schema(
        getattr(client_ctx, "data_schema", None)
    )
    if not sql_schema_context:
        try:
            sql_schema_context = await build_prompt(
                "fragment/sql-schema", {}, context_service=context_service
            )
        except Exception:
            sql_schema_context = ""

    company_profile = _render_company_profile(
        getattr(client_ctx, "company_profile", None)
    )

    # Dynamic catalog: only validated agents (frontdesk_visible=True)
    available_agents = AgentTypeRegistry.build_frontdesk_catalog()

    variables: dict = {
        "nome_empresa": nome_empresa,
        "sql_schema_context": sql_schema_context,
        "company_profile": company_profile,
        "available_agents": available_agents,
    }

    try:
        return await build_prompt(
            name=prompt_name,
            variables=variables,
            context_service=context_service,
        )
    except Exception as exc:
        logger.warning("[ChatService] build_prompt(%s) failed: %s", prompt_name, exc)
        return (
            f"You are the Frontdesk assistant for {nome_empresa}. "
            "Answer in the user's language. Use available tools when appropriate."
        )


async def _build_specialist_prompt(
    slug: str,
    client_ctx: Any,
    context_service: ContextService,
) -> str:
    """Build system prompt for any specialist agent.

    Specialists that need business_snapshot (crm, estrategia) get it injected.
    Others (supplier, scheduler, doc-writer, fiscal) get a lighter prompt.
    """
    from blu_agent_framework.registry import AgentTypeRegistry

    cfg = AgentTypeRegistry.get(slug)
    prompt_name = cfg.prompt_name if cfg else f"agents/{slug}"
    nome_empresa: str = getattr(client_ctx, "nome_empresa", "") or ""
    client_id_str: str = str(getattr(client_ctx, "id", ""))

    needs_snapshot = slug in ("crm", "estrategia", "data-analyst")
    snapshot = ""
    if needs_snapshot:
        try:
            snapshot = await context_service.get_business_memory_snapshot(
                client_id_str, max_chars=6000
            )
        except Exception as exc:
            logger.warning("[specialist:%s] snapshot failed: %s", slug, exc)

    variables: dict = {"nome_empresa": nome_empresa, "business_snapshot": snapshot}

    try:
        return await build_prompt(
            name=prompt_name,
            variables=variables,
            context_service=context_service,
        )
    except Exception as exc:
        logger.warning("[ChatService] build_prompt(%s) failed: %s", prompt_name, exc)
        return (
            f"Você é um especialista do {nome_empresa}. "
            "Responda em português com base nos dados disponíveis."
        )


def _fire_and_forget(coro) -> None:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def _post_flight_for_state(
    final_state: dict,
    client_id: str,
    agent_slug: str,
    session_id: str,
    elapsed: float,
    tool_calls_seen: list[str] | None = None,
) -> None:
    """Extract agent result/metadata from final state and persist via post-flight.

    Fire-and-forget — never blocks the user. Errors are logged as warnings.
    """
    try:
        from tool_pool_api.server.tool_modules.memory_post_flight import (
            _shared_memory_post_flight_logic,
        )

        msgs = final_state.get("messages") or []
        last_ai = None
        for m in reversed(msgs):
            if isinstance(m, AIMessage):
                last_ai = m
                break

        agent_result = None
        if last_ai and last_ai.content:
            tool_names = tool_calls_seen or [
                tc.get("name")
                for tc in getattr(last_ai, "tool_calls", []) or []
            ]
            agent_result = {
                "summary": str(last_ai.content)[:_MAX_SUMMARY_CHARS],
                "tool_calls": tool_names,
            }

        agent_metadata = {
            "session_id": session_id,
            "agent_slug": agent_slug,
            "elapsed_seconds": round(elapsed, 2),
        }

        await _shared_memory_post_flight_logic(
            client_id=client_id,
            agent_slug=agent_slug,
            session_id=session_id,
            agent_result=agent_result,
            agent_metadata=agent_metadata,
        )
    except Exception:
        logger.warning(
            "[ChatService] Post-flight failed for agent=%s session=%s",
            agent_slug,
            session_id,
            exc_info=True,
        )


# Post-flight summary max chars (mirrors memory_post_flight._MAX_SUMMARY_CHARS)
_MAX_SUMMARY_CHARS = 2000


# ---------------------------------------------------------------------------
# ChatResult
# ---------------------------------------------------------------------------


class ChatResult:
    def __init__(
        self,
        response: str,
        model_used: str | None = None,
        agent_slug: str = "frontdesk",
        pending_elicitation: dict | None = None,
        structured_data: dict[str, Any] | None = None,
        structured_data_list: list[dict[str, Any]] | None = None,
    ) -> None:
        self.response = response
        self.model_used = model_used
        self.agent_slug = agent_slug
        self.pending_elicitation = pending_elicitation
        self.structured_data = structured_data
        self.structured_data_list = structured_data_list


# ---------------------------------------------------------------------------
# ChatService — supervisor mode
# ---------------------------------------------------------------------------


class ChatService:
    """
    Handles supervisor-mode chat (sync + streaming).

    The supervisor graph is built once per tier and shared across all sessions.
    Per-session conversation state lives in the Redis checkpointer (thread_id="{client_id}:{session_id}").
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    def _resolve_model_used(self, override: str | None) -> str:
        if override:
            return override
        llm_settings = get_llm_settings()
        provider = LLMProvider(llm_settings.LLM_PROVIDER)
        return MODEL_MAPPINGS.get(provider, {}).get(ModelTier.DEFAULT, "default")

    async def _get_client_context(self, external_user_id: str, ctx_service: ContextService):
        """Resolve client context from external_user_id (Supabase auth UUID)."""
        client_context = await ctx_service.get_client_context_by_external_user_id(external_user_id)
        if not client_context:
            raise ValueError(f"Client not found for user_id={external_user_id}")
        return client_context

    async def _connect_mcp(self, client_id: str, session_id: str, user_jwt: str | None = None) -> None:
        """Ensure MCP is connected with correct client headers."""
        mcp_mgr = get_mcp_manager()
        mcp_mgr.set_client_id(client_id)
        mcp_mgr.set_session_id(session_id)
        if user_jwt:
            mcp_mgr.set_auth_token(user_jwt)

        if not getattr(mcp_mgr, "is_connected", False):
            try:
                await asyncio.wait_for(mcp_mgr.connect(), timeout=45)
                logger.info("[ChatService] MCP connected")
            except asyncio.CancelledError:
                # anyio cancel scope leaks CancelledError as BaseException — swallow it
                # so the worker survives; mcp_client will reconnect on next tool call.
                logger.warning("[ChatService] MCP connect cancelled (scope leak) — continuing without MCP")
            except Exception as exc:
                logger.warning("[ChatService] MCP connect failed (will retry on tool call): %s", exc)

    def _build_langfuse_config(self, session_id: str, client_id: str, tags: list[str], trace_name: str | None = None) -> dict:
        try:
            from agent_api.core.observability import get_langfuse_config
            return get_langfuse_config(session_id=session_id, client_id=client_id, tags=tags, trace_name=trace_name)
        except Exception:
            return {"configurable": {"thread_id": f"{client_id}:{session_id}"}}

    async def process_message(
        self,
        session_id: str,
        message: str,
        client_id: UUID,
        context_service: ContextService,
        model_override: str | None = None,
        elicitation_response: dict[str, Any] | None = None,
        user_jwt: str | None = None,
        extra_tags: list[str] | None = None,
    ) -> ChatResult:
        """Run frontdesk graph and return a sync ChatResult."""
        client_ctx = await self._get_client_context(str(client_id), context_service)
        tier: str = getattr(client_ctx, "tier", "BASIC") or "BASIC"
        nome_empresa: str = getattr(client_ctx, "nome_empresa", "") or ""
        client_id = str(client_ctx.id)

        logger.info("[ChatService] %s | session=%s", nome_empresa, session_id)

        await self._connect_mcp(client_id=client_id, session_id=session_id, user_jwt=user_jwt)

        factory = get_factory()
        system_prompt = await _build_frontdesk_prompt(
            client_ctx=client_ctx,
            context_service=context_service,
        )

        # Routing is now handled by the frontdesk LLM via route_to_specialist tool.
        # Keyword pre-routing removed — see service.py git history for legacy impl.
        _selected_agent = "frontdesk"

        # Build initial state
        from blu_agent_framework.state import AgentState
        initial_state = AgentState(
            messages=[HumanMessage(content=message)],
            session_id=session_id,
            client_id=client_id,
            nome_empresa=nome_empresa,
            tier=tier,
            model_override=model_override,
            user_jwt=user_jwt,
            system_prompt=system_prompt,
            pending_elicitation=None,
            elicitation_response=elicitation_response,
            ended=False,
            turn_count=0,
            structured_data=None,
            structured_data_list=[],
        )

        graph = factory.get_frontdesk_graph(tier=tier, context_service=context_service)
        config = self._build_langfuse_config(
            session_id=session_id,
            client_id=client_id,
            tags=["frontdesk", nome_empresa] + (extra_tags or []),
            trace_name=f"chat:{nome_empresa}:{session_id[:8]}",
        )
        config.setdefault("configurable", {})["thread_id"] = f"{client_id}:{session_id}"
        config["recursion_limit"] = 12  # default_graph has 5 nodes; 12 ≈ 2 full turn cycles

        start = time.time()
        final_state = await graph.ainvoke(initial_state, config)
        elapsed = time.time() - start
        logger.info("[ChatService] Graph completed in %.2fs", elapsed)

        # ------------------------------------------------------------------
        # Handoff: frontdesk called route_to_specialist → run specialist graph
        #
        # The sentinel "__ROUTE_TO_SPECIALIST__:<slug>:<reason>" is emitted
        # by the route_to_specialist MCP tool as a ToolMessage.  After the
        # tool executes, the frontdesk LLM gets one more turn and produces a
        # final AIMessage ("Transferindo...") — so messages[-1] is that
        # AIMessage, NOT the ToolMessage.  We must scan all messages for the
        # sentinel in any ToolMessage, not just the last message.
        # ------------------------------------------------------------------
        def _find_route_sentinel(msgs: list) -> str | None:
            """Return the sentinel string from the last ToolMessage that contains it, or None."""
            for msg in reversed(msgs or []):
                if isinstance(msg, ToolMessage):
                    content = str(msg.content)
                    if content.startswith("__ROUTE_TO_SPECIALIST__:"):
                        return content
            return None

        all_msgs = final_state.get("messages") or []
        sentinel = _find_route_sentinel(all_msgs)
        if sentinel:
            parts = sentinel.split(":", 2)
            specialist_slug = parts[1] if len(parts) > 1 else "frontdesk"
            reason = parts[2] if len(parts) > 2 else ""
            logger.info("[ChatService] Handoff → specialist=%s reason=%s", specialist_slug, reason)
            try:
                specialist_prompt = await _build_specialist_prompt(
                    slug=specialist_slug,
                    client_ctx=client_ctx,
                    context_service=context_service,
                )
                specialist_state = AgentState(
                    messages=[HumanMessage(content=message)],
                    session_id=session_id,
                    client_id=client_id,
                    nome_empresa=nome_empresa,
                    tier=tier,
                    model_override=model_override,
                    user_jwt=user_jwt,
                    system_prompt=specialist_prompt,
                    pending_elicitation=None,
                    elicitation_response=elicitation_response,
                    ended=False,
                    turn_count=0,
                    structured_data=None,
                    structured_data_list=[],
                )
                specialist_graph = factory.get_specialist_graph(slug=specialist_slug, tier=tier)
                specialist_config = self._build_langfuse_config(
                    session_id=session_id,
                    client_id=client_id,
                    tags=[specialist_slug, nome_empresa],
                    trace_name=f"chat:{specialist_slug}:{nome_empresa}:{session_id[:8]}",
                )
                specialist_config.setdefault("configurable", {})["thread_id"] = f"{client_id}:{session_id}:{specialist_slug}"
                # Recursion limit must account for graph topology:
                #   fanout:  5 nodes/turn (init→elicit→execute_single_tool→collect→respond)
                #   default: 4 nodes/turn (init→elicit→execute_tool→respond)
                # Use AgentTypeRegistry to get max_turns and topology for the slug.
                from blu_agent_framework.registry import AgentTypeRegistry as _ATR
                _cfg = _ATR.get(specialist_slug)
                _max_turns = (_cfg.max_turns if _cfg else 6) + 2  # +2 buffer
                _nodes_per_turn = 6 if (_cfg and getattr(_cfg, "graph_topology", "default") == "fanout") else 5
                specialist_config["recursion_limit"] = _max_turns * _nodes_per_turn
                logger.info(
                    "[ChatService] Specialist %s recursion_limit=%d (max_turns=%d, topology=%s)",
                    specialist_slug, specialist_config["recursion_limit"],
                    _max_turns, getattr(_cfg, "graph_topology", "default") if _cfg else "default",
                )
                final_state = await specialist_graph.ainvoke(specialist_state, specialist_config)
                _selected_agent = specialist_slug
            except Exception as exc:
                logger.warning("[ChatService] Specialist graph failed (%s): %s — returning neutral error message", specialist_slug, exc)
                # Do NOT fall back to frontdesk last message — it may be an
                # optimistic "success" hallucination emitted before the specialist crashed.
                # Override with a neutral message so the user knows to retry.
                neutral_msg = AIMessage(content="Desculpe, não consegui concluir essa ação agora. Tente novamente em alguns instantes.")
                if final_state and isinstance(final_state.get("messages"), list):
                    final_state["messages"] = [
                        m for m in final_state["messages"]
                        if not (hasattr(m, "content") and str(m.content).startswith("__ROUTE_TO_SPECIALIST__:"))
                    ] + [neutral_msg]
                elif final_state is not None:
                    final_state["messages"] = [neutral_msg]
                else:
                    final_state = {"messages": [neutral_msg]}
        # ------------------------------------------------------------------

        # Trim message history in state to bounded window
        window = self.settings.SESSION_HISTORY_WINDOW
        if final_state and isinstance(final_state.get("messages"), list):
            final_state["messages"] = final_state["messages"][-window:]

        last_msg = (final_state.get("messages") or [])[-1] if final_state.get("messages") else None
        response_text = _clean_response(str(last_msg.content)) if isinstance(last_msg, AIMessage) else ""
        if not response_text.strip():
            response_text = "Desculpe, ocorreu um erro. Tente novamente."

        # Post-flight hook (fire-and-forget, never blocks the user)
        _fire_and_forget(
            _post_flight_for_state(
                final_state=final_state,
                client_id=client_id,
                agent_slug=_selected_agent,
                session_id=session_id,
                elapsed=elapsed,
            )
        )

        return ChatResult(
            response=response_text,
            model_used=self._resolve_model_used(model_override),
            agent_slug=_selected_agent,
            pending_elicitation=final_state.get("pending_elicitation"),
            structured_data=final_state.get("structured_data"),
            structured_data_list=final_state.get("structured_data_list") or None,
        )

    async def process_message_stream(
        self,
        session_id: str,
        message: str,
        client_id: UUID,
        context_service: ContextService,
        model_override: str | None = None,
        user_jwt: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream frontdesk graph response as SSE events."""
        client_ctx = await self._get_client_context(str(client_id), context_service)
        tier: str = getattr(client_ctx, "tier", "BASIC") or "BASIC"
        nome_empresa: str = getattr(client_ctx, "nome_empresa", "") or ""
        client_id = str(client_ctx.id)

        logger.info("[ChatService/stream] %s | session=%s", nome_empresa, session_id)

        await self._connect_mcp(client_id=client_id, session_id=session_id, user_jwt=user_jwt)

        factory = get_factory()
        system_prompt = await _build_frontdesk_prompt(
            client_ctx=client_ctx,
            context_service=context_service,
        )

        # Routing is now handled by the frontdesk LLM via route_to_specialist tool.
        # Keyword pre-routing removed — see service.py git history for legacy impl.

        from blu_agent_framework.state import AgentState
        initial_state = AgentState(
            messages=[HumanMessage(content=message)],
            session_id=session_id,
            client_id=client_id,
            nome_empresa=nome_empresa,
            tier=tier,
            model_override=model_override,
            user_jwt=user_jwt,
            system_prompt=system_prompt,
            pending_elicitation=None,
            elicitation_response=None,
            ended=False,
            turn_count=0,
            structured_data=None,
            structured_data_list=[],
        )

        graph = factory.get_frontdesk_graph(tier=tier, context_service=context_service)
        config = self._build_langfuse_config(
            session_id=session_id,
            client_id=client_id,
            tags=["frontdesk", "stream", nome_empresa],
            trace_name=f"chat-stream:{nome_empresa}:{session_id[:8]}",
        )
        config.setdefault("configurable", {})["thread_id"] = f"{client_id}:{session_id}"
        config["recursion_limit"] = 12  # default_graph has 5 nodes; 12 ≈ 2 full turn cycles

        full_response_parts: list[str] = []
        model_used = self._resolve_model_used(model_override)
        structured_data = None
        tool_calls_seen: list[str] = []
        stream_agent = "frontdesk"
        stream_start = time.time()

        try:
            async for event in graph.astream_events(initial_state, config, version="v2"):
                event_type = event.get("event", "")
                data = event.get("data", {})

                if event_type == "on_chat_model_stream":
                    chunk = data.get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        token = chunk.content
                        full_response_parts.append(token)
                        yield f"data: {json.dumps({'event': 'token', 'data': token})}\n\n"

                elif event_type == "on_tool_start":
                    tool_name = event.get("name", "")
                    if tool_name:
                        tool_calls_seen.append(tool_name)
                    yield f"data: {json.dumps({'event': 'tool_start', 'data': {'name': tool_name, 'args': data.get('input', {})}})}\n\n"

                elif event_type == "on_tool_end":
                    tool_name = event.get("name", "")
                    output = data.get("output", "")
                    preview = str(output)[:200] if output else ""
                    yield f"data: {json.dumps({'event': 'tool_end', 'data': {'name': tool_name, 'output': preview}})}\n\n"

                elif event_type == "on_chain_end" and event.get("name") == "LangGraph":
                    output = data.get("output") or {}
                    structured_data = output.get("structured_data")
                    # Detect handoff signal from route_to_specialist tool.
                    # The sentinel lives in a ToolMessage, not in messages[-1]
                    # (the LLM always produces a final AIMessage after the tool
                    # call, so the last message is never the sentinel itself).
                    msgs = output.get("messages") or []
                    sentinel_content = None
                    for _m in reversed(msgs):
                        if isinstance(_m, ToolMessage):
                            _c = str(getattr(_m, "content", ""))
                            if _c.startswith("__ROUTE_TO_SPECIALIST__:"):
                                sentinel_content = _c
                                break
                    if sentinel_content:
                        parts = sentinel_content.split(":", 2)
                        specialist_slug = parts[1] if len(parts) > 1 else "frontdesk"
                        stream_agent = specialist_slug
                        reason = parts[2] if len(parts) > 2 else ""
                        logger.info("[ChatService/stream] Handoff → specialist=%s reason=%s", specialist_slug, reason)
                        yield f"data: {json.dumps({'event': 'handoff', 'data': {'agent': specialist_slug, 'reason': reason}})}\n\n"
                        try:
                            specialist_prompt = await _build_specialist_prompt(
                                slug=specialist_slug,
                                client_ctx=client_ctx,
                                context_service=context_service,
                            )
                            specialist_state = AgentState(
                                messages=[HumanMessage(content=message)],
                                session_id=session_id,
                                client_id=client_id,
                                nome_empresa=nome_empresa,
                                tier=tier,
                                model_override=model_override,
                                user_jwt=user_jwt,
                                system_prompt=specialist_prompt,
                                pending_elicitation=None,
                                elicitation_response=None,
                                ended=False,
                                turn_count=0,
                                structured_data=None,
                                structured_data_list=[],
                            )
                            specialist_graph = factory.get_specialist_graph(slug=specialist_slug, tier=tier)
                            specialist_config = self._build_langfuse_config(
                                session_id=session_id,
                                client_id=client_id,
                                tags=[specialist_slug, "stream", nome_empresa],
                                trace_name=f"chat-stream:{specialist_slug}:{nome_empresa}:{session_id[:8]}",
                            )
                            specialist_config.setdefault("configurable", {})["thread_id"] = f"{client_id}:{session_id}:{specialist_slug}"
                            full_response_parts = []  # reset — specialist will produce the real answer
                            async for sp_event in specialist_graph.astream_events(specialist_state, specialist_config, version="v2"):
                                sp_type = sp_event.get("event", "")
                                sp_data = sp_event.get("data", {})
                                if sp_type == "on_chat_model_stream":
                                    chunk = sp_data.get("chunk")
                                    if chunk and hasattr(chunk, "content") and chunk.content:
                                        token = chunk.content
                                        full_response_parts.append(token)
                                        yield f"data: {json.dumps({'event': 'token', 'data': token})}\n\n"
                                elif sp_type == "on_tool_start":
                                    tool_name_sp = sp_event.get('name', '')
                                    if tool_name_sp:
                                        tool_calls_seen.append(tool_name_sp)
                                    yield f"data: {json.dumps({'event': 'tool_start', 'data': {'name': sp_event.get('name', ''), 'args': sp_data.get('input', {})}})}\n\n"
                                elif sp_type == "on_tool_end":
                                    preview = str(sp_data.get("output", ""))[:200]
                                    yield f"data: {json.dumps({'event': 'tool_end', 'data': {'name': sp_event.get('name', ''), 'output': preview}})}\n\n"
                                elif sp_type == "on_chain_end" and sp_event.get("name") == "LangGraph":
                                    structured_data = (sp_data.get("output") or {}).get("structured_data")
                        except Exception as exc:
                            logger.warning("[ChatService/stream] Specialist graph failed (%s): %s", specialist_slug, exc)
                            yield f"data: {json.dumps({'event': 'error', 'data': {'message': f'Specialist {specialist_slug} failed: {exc}'}})}\n\n"

        except Exception as exc:
            logger.exception("[ChatService/stream] Error streaming")
            yield f"data: {json.dumps({'event': 'error', 'data': {'message': str(exc)}})}\n\n"
            return

        full_response = _clean_response("".join(full_response_parts))
        if not full_response.strip():
            full_response = "Desculpe, ocorreu um erro. Tente novamente."
        done_data: dict[str, Any] = {"response": full_response, "model": model_used}
        if structured_data:
            done_data["structured_data"] = structured_data
        yield f"data: {json.dumps({'event': 'done', 'data': done_data}, ensure_ascii=False, default=str)}\n\n"

        # Post-flight hook (fire-and-forget, never blocks the stream)
        if full_response_parts:
            stream_elapsed = time.time() - stream_start
            _fire_and_forget(
                _post_flight_for_state(
                    final_state={"messages": []},
                    client_id=client_id,
                    agent_slug=stream_agent,
                    session_id=session_id,
                    elapsed=stream_elapsed,
                    tool_calls_seen=tool_calls_seen,
                )
            )


# ---------------------------------------------------------------------------
# AgentService — standalone agents
# ---------------------------------------------------------------------------


class AgentService:
    """
    Handles standalone agent chat (streaming).

    Each session has its own compiled graph, built from the agent_catalog entry.
    """

    async def stream_agent_response(
        self,
        session_id: str,
        client_id: UUID,
        agent_catalog_id: UUID,
        user_message: str,
    ) -> AsyncIterator[str]:
        """Stream standalone agent response as SSE dicts (without data: prefix)."""
        try:
            built: BuiltAgent = await get_factory().get_standalone_agent(
                session_id=session_id,
                client_id=client_id,
                agent_catalog_id=agent_catalog_id,
            )
        except Exception as exc:
            logger.error("[AgentService] Failed to build agent: %s", exc)
            yield {"event": "error", "message": str(exc)}
            return

        ctx_service = get_context_service()
        client_ctx = await ctx_service.get_client_context_by_external_user_id(str(client_id))
        client_id = str(client_ctx.id) if client_ctx else ""

        # Set MCP headers for this session
        mcp_mgr = get_mcp_manager()
        if client_id:
            mcp_mgr.set_client_id(client_id)
            mcp_mgr.set_session_id(session_id)

        initial_state = create_initial_state(
            session_id=session_id,
            client_id=client_id,
            messages=[HumanMessage(content=user_message)],
            system_prompt=built.system_prompt,
            agent_name=built.agent_name,
            agent_role=built.agent_role,
            client_context=built.client_context,
            metadata=built.metadata,
        )
        # Issue 4: create_initial_state reads tier from client_context, which here
        # is the session's collected_context (not BluClientContext). Inject explicitly.
        initial_state["tier"] = built.tier

        from agent_api.core.observability import get_langfuse_config
        config = get_langfuse_config(
            session_id=session_id,
            client_id=client_id,
            tags=["standalone", built.agent_name or ""],
        )

        full_response_parts: list[str] = []

        try:
            async for event in built.graph.astream_events(initial_state, config, version="v2"):
                event_type = event.get("event", "")
                data = event.get("data", {})

                if event_type == "on_chat_model_stream":
                    chunk = data.get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        token = chunk.content
                        full_response_parts.append(token)
                        yield {"event": "token", "data": token}

                elif event_type == "on_tool_start":
                    yield {"event": "tool_start", "data": {"name": event.get("name", ""), "args": data.get("input", {})}}

                elif event_type == "on_tool_end":
                    yield {"event": "tool_end", "data": {"name": event.get("name", ""), "output": str(data.get("output", ""))[:200]}}

        except Exception as exc:
            logger.exception("[AgentService] Error during stream")
            yield {"event": "error", "message": str(exc)}
            return

        yield {"event": "done", "data": _clean_response("".join(full_response_parts))}


# ---------------------------------------------------------------------------
# Service singletons
# ---------------------------------------------------------------------------

_chat_service: ChatService | None = None
_agent_service: AgentService | None = None


def get_chat_service() -> ChatService:
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service


def get_agent_service() -> AgentService:
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    return _agent_service


# ---------------------------------------------------------------------------
# Import guard for create_initial_state
# ---------------------------------------------------------------------------

from blu_agent_framework.state import create_initial_state  # noqa: E402
