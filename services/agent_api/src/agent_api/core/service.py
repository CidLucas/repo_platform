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

from langchain_core.messages import AIMessage, HumanMessage

from blu_context_service import ContextService
from blu_llm_service import MODEL_MAPPINGS, LLMProvider, ModelTier, get_llm_settings

from agent_api.config import get_settings
from agent_api.core.factory import (
    BuiltAgent,
    get_context_service,
    get_factory,
    get_mcp_manager,
)

logger = logging.getLogger(__name__)

# Fire-and-forget task registry (prevents GC of background tasks)
_background_tasks: set = set()


def _fire_and_forget(coro) -> None:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


# ---------------------------------------------------------------------------
# ChatResult
# ---------------------------------------------------------------------------


class ChatResult:
    def __init__(
        self,
        response: str,
        model_used: str | None = None,
        pending_elicitation: dict | None = None,
        structured_data: dict[str, Any] | None = None,
        structured_data_list: list[dict[str, Any]] | None = None,
    ) -> None:
        self.response = response
        self.model_used = model_used
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
    Per-session conversation state lives in the Redis checkpointer (thread_id=session_id).
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

    async def _connect_mcp(self, cliente_id: str, session_id: str, user_jwt: str | None = None) -> None:
        """Ensure MCP is connected with correct client headers."""
        mcp_mgr = get_mcp_manager()
        mcp_mgr.set_cliente_id(cliente_id)
        mcp_mgr.set_session_id(session_id)
        if user_jwt:
            mcp_mgr.set_auth_token(user_jwt)

        if not getattr(mcp_mgr, "is_connected", False):
            try:
                await asyncio.wait_for(mcp_mgr.connect(), timeout=30)
                logger.info("[ChatService] MCP connected")
            except Exception as exc:
                logger.warning("[ChatService] MCP connect failed (will retry on tool call): %s", exc)

    def _build_langfuse_config(self, session_id: str, cliente_id: str, tags: list[str]) -> dict:
        try:
            from agent_api.core.observability import get_langfuse_config
            return get_langfuse_config(session_id=session_id, cliente_id=cliente_id, tags=tags)
        except Exception:
            return {"configurable": {"thread_id": session_id}}

    async def process_message(
        self,
        session_id: str,
        message: str,
        client_id: UUID,
        context_service: ContextService,
        model_override: str | None = None,
        elicitation_response: dict[str, Any] | None = None,
        user_jwt: str | None = None,
    ) -> ChatResult:
        """Run supervisor graph and return a sync ChatResult."""
        client_ctx = await self._get_client_context(str(client_id), context_service)
        tier: str = getattr(client_ctx, "tier", "BASIC") or "BASIC"
        nome_empresa: str = getattr(client_ctx, "nome_empresa", "") or ""
        cliente_id = str(client_ctx.id)

        logger.info("[ChatService] %s | session=%s", nome_empresa, session_id)

        await self._connect_mcp(cliente_id=cliente_id, session_id=session_id, user_jwt=user_jwt)

        # Build initial state
        from blu_agent_framework.state import AgentState
        initial_state = AgentState(
            messages=[HumanMessage(content=message)],
            session_id=session_id,
            cliente_id=cliente_id,
            nome_empresa=nome_empresa,
            tier=tier,
            model_override=model_override,
            user_jwt=user_jwt,
            pending_elicitation=None,
            elicitation_response=elicitation_response,
            ended=False,
            turn_count=0,
            structured_data=None,
            structured_data_list=[],
            _cached_system_prompt=None,
            _cached_tools=None,
        )

        graph = get_factory().get_supervisor_graph(tier=tier, context_service=context_service)
        config = self._build_langfuse_config(
            session_id=session_id,
            cliente_id=cliente_id,
            tags=["supervisor", nome_empresa],
        )
        config.setdefault("configurable", {})["thread_id"] = session_id

        start = time.time()
        final_state = await graph.ainvoke(initial_state, config)
        elapsed = time.time() - start
        logger.info("[ChatService] Graph completed in %.2fs", elapsed)

        # Trim message history in state to bounded window
        window = self.settings.SESSION_HISTORY_WINDOW
        if final_state and isinstance(final_state.get("messages"), list):
            final_state["messages"] = final_state["messages"][-window:]

        last_msg = (final_state.get("messages") or [])[-1] if final_state.get("messages") else None
        response_text = str(last_msg.content) if isinstance(last_msg, AIMessage) else ""

        return ChatResult(
            response=response_text,
            model_used=self._resolve_model_used(model_override),
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
        """Stream supervisor graph response as SSE events."""
        client_ctx = await self._get_client_context(str(client_id), context_service)
        tier: str = getattr(client_ctx, "tier", "BASIC") or "BASIC"
        nome_empresa: str = getattr(client_ctx, "nome_empresa", "") or ""
        cliente_id = str(client_ctx.id)

        logger.info("[ChatService/stream] %s | session=%s", nome_empresa, session_id)

        await self._connect_mcp(cliente_id=cliente_id, session_id=session_id, user_jwt=user_jwt)

        from blu_agent_framework.state import AgentState
        initial_state = AgentState(
            messages=[HumanMessage(content=message)],
            session_id=session_id,
            cliente_id=cliente_id,
            nome_empresa=nome_empresa,
            tier=tier,
            model_override=model_override,
            user_jwt=user_jwt,
            pending_elicitation=None,
            elicitation_response=None,
            ended=False,
            turn_count=0,
            structured_data=None,
            structured_data_list=[],
            _cached_system_prompt=None,
            _cached_tools=None,
        )

        graph = get_factory().get_supervisor_graph(tier=tier, context_service=context_service)
        config = self._build_langfuse_config(
            session_id=session_id,
            cliente_id=cliente_id,
            tags=["supervisor", "stream", nome_empresa],
        )
        config.setdefault("configurable", {})["thread_id"] = session_id

        full_response_parts: list[str] = []
        model_used = self._resolve_model_used(model_override)
        structured_data = None

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
                    yield f"data: {json.dumps({'event': 'tool_start', 'data': {'name': tool_name, 'args': data.get('input', {})}})}\n\n"

                elif event_type == "on_tool_end":
                    tool_name = event.get("name", "")
                    output = data.get("output", "")
                    preview = str(output)[:200] if output else ""
                    yield f"data: {json.dumps({'event': 'tool_end', 'data': {'name': tool_name, 'output': preview}})}\n\n"

                elif event_type == "on_chain_end" and event.get("name") == "LangGraph":
                    output = data.get("output") or {}
                    structured_data = output.get("structured_data")

        except Exception as exc:
            logger.exception("[ChatService/stream] Error streaming")
            yield f"data: {json.dumps({'event': 'error', 'data': {'message': str(exc)}})}\n\n"
            return

        full_response = "".join(full_response_parts)
        done_data: dict[str, Any] = {"response": full_response, "model": model_used}
        if structured_data:
            done_data["structured_data"] = structured_data
        yield f"data: {json.dumps({'event': 'done', 'data': done_data}, ensure_ascii=False, default=str)}\n\n"


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
        cliente_id = str(client_ctx.id) if client_ctx else ""

        # Set MCP headers for this session
        mcp_mgr = get_mcp_manager()
        if cliente_id:
            mcp_mgr.set_cliente_id(cliente_id)
            mcp_mgr.set_session_id(session_id)

        initial_state = create_initial_state(
            session_id=session_id,
            cliente_id=cliente_id,
            messages=[HumanMessage(content=user_message)],
            system_prompt=built.system_prompt,
            agent_name=built.agent_name,
            agent_role=built.agent_role,
            client_context=built.client_context,
            metadata=built.metadata,
        )

        from agent_api.core.observability import get_langfuse_config
        config = get_langfuse_config(
            session_id=session_id,
            cliente_id=cliente_id,
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

        yield {"event": "done", "data": "".join(full_response_parts)}


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
