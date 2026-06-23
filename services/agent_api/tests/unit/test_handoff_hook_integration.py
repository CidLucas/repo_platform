# GOAL: Hook de handoff entre agentes na shared memory
# BEHAVIOR: B5 — Integrar handoff hook no route_to_specialist flow (service.py)
# ACCEPTANCE CRITERION: AC3 — Hook automático na transição route_to_specialist
# DECISÃO DO PLANNER: create_new — service.py

"""Unit tests for handoff hook integration in ChatService.route_to_specialist flow.

Tests that run_handoff_hook and load_shared_memory_context from
blu_agent_framework.handoff are called during the route_to_specialist
transition in ChatService.process_message_stream(), and that the
skip_handoff_hook flag prevents the hook from firing.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import ToolMessage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_client_context():
    """Build a mock client context object with required attributes."""
    ctx = MagicMock()
    ctx.id = "client-123"
    ctx.tier = "BASIC"
    ctx.nome_empresa = "TestCorp"
    return ctx


def _mock_context_service():
    """Build a mock context service with async methods."""
    svc = MagicMock()
    svc.get_client_context_by_external_user_id = AsyncMock(
        return_value=_mock_client_context(),
    )
    return svc


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_graph():
    """Return a mock frontdesk graph whose astream_events yields events
    with a __ROUTE_TO_SPECIALIST__ sentinel in its final tool message."""
    graph = MagicMock()

    tool_msg = ToolMessage(
        content="__ROUTE_TO_SPECIALIST__:analytics_financeiro:user asked about expenses",
        tool_call_id="t1",
    )

    ai_msg = MagicMock()
    ai_msg.content = ""

    chain_end_data = {
        "output": {
            "messages": [tool_msg, ai_msg],
            "structured_data": None,
        }
    }

    graph.astream_events.return_value.__aiter__.return_value = [
        {"event": "on_chain_end", "name": "LangGraph", "data": chain_end_data},
    ]
    return graph


@pytest.fixture
def mock_graph_with_skip_flag():
    """Same as mock_graph but the sentinel includes a skip_handoff_hook flag."""
    graph = MagicMock()

    tool_msg = ToolMessage(
        content="__ROUTE_TO_SPECIALIST__:analytics_financeiro:user asked:skip_handoff_hook=True",
        tool_call_id="t1",
    )

    ai_msg = MagicMock()
    ai_msg.content = ""

    chain_end_data = {
        "output": {
            "messages": [tool_msg, ai_msg],
            "structured_data": None,
        }
    }

    graph.astream_events.return_value.__aiter__.return_value = [
        {"event": "on_chain_end", "name": "LangGraph", "data": chain_end_data},
    ]
    return graph


@pytest.fixture
def chat_service():
    """Build a minimal ChatService with mocked settings."""
    with patch("agent_api.core.service.get_settings") as mock_get_settings:
        settings = MagicMock()
        settings.SESSION_HISTORY_WINDOW = 50
        settings.LANGFUSE_SECRET_KEY = "sk-test"
        settings.LANGFUSE_PUBLIC_KEY = "pk-test"
        settings.LANGFUSE_HOST = "http://localhost:3000"
        mock_get_settings.return_value = settings

        from agent_api.core.service import ChatService

        service = ChatService()
        service._build_langfuse_config = MagicMock(return_value={})
        yield service


# ---------------------------------------------------------------------------
# Test: handoff hook fires on route_to_specialist, skipped with flag
# ---------------------------------------------------------------------------

class TestHandoffHookCalledOnRouteToSpecialist:
    """B5 — run_handoff_hook and load_shared_memory_context are called
    when __ROUTE_TO_SPECIALIST__ is detected."""

    @pytest.mark.asyncio
    async def test_handoff_hook_called_on_sentinel(
        self, chat_service, mock_graph,
    ):
        """When __ROUTE_TO_SPECIALIST__ is detected, run_handoff_hook
        and load_shared_memory_context are called before specialist_state
        is created."""
        mock_run_handoff_hook = AsyncMock()
        mock_load_context = AsyncMock(return_value={"entidade_x": {"nome": "XPTO"}})

        mock_factory = MagicMock()
        mock_factory.get_frontdesk_graph.return_value = mock_graph
        mock_specialist_graph = MagicMock()
        mock_specialist_graph.astream_events.return_value.__aiter__.return_value = []
        mock_factory.get_specialist_graph.return_value = mock_specialist_graph

        ctx_service = _mock_context_service()

        with (
            patch(
                "agent_api.core.service.get_factory",
                return_value=mock_factory,
            ),
            patch(
                "agent_api.core.service.get_context_service",
                return_value=ctx_service,
            ),
            patch(
                "agent_api.core.service.get_mcp_manager",
                return_value=MagicMock(),
            ),
            patch(
                "agent_api.core.service.run_handoff_hook",
                mock_run_handoff_hook,
                create=True,
            ),
            patch(
                "agent_api.core.service.load_shared_memory_context",
                mock_load_context,
                create=True,
            ),
        ):
            collected = []
            async for event in chat_service.process_message_stream(
                session_id="session-abc",
                message="Show me financial data",
                client_id="client-123",
                context_service=ctx_service,
            ):
                collected.append(event)

        # The handoff hook should have been called
        mock_run_handoff_hook.assert_awaited_once()
        # The shared memory context should have been loaded
        mock_load_context.assert_awaited_once()

        # Verify handoff event was emitted
        handoff_events = [e for e in collected if '"event": "handoff"' in e]
        assert len(handoff_events) > 0, (
            "Expected at least one handoff event when __ROUTE_TO_SPECIALIST__ "
            "is detected"
        )

    @pytest.mark.asyncio
    async def test_handoff_hook_skipped_with_flag(
        self, chat_service, mock_graph_with_skip_flag,
    ):
        """When skip_handoff_hook=True flag is present, run_handoff_hook and
        load_shared_memory_context should NOT be called."""
        mock_run_handoff_hook = AsyncMock()
        mock_load_context = AsyncMock(return_value={})

        mock_factory = MagicMock()
        mock_factory.get_frontdesk_graph.return_value = mock_graph_with_skip_flag
        mock_specialist_graph = MagicMock()
        mock_specialist_graph.astream_events.return_value.__aiter__.return_value = []
        mock_factory.get_specialist_graph.return_value = mock_specialist_graph

        ctx_service = _mock_context_service()

        with (
            patch(
                "agent_api.core.service.get_factory",
                return_value=mock_factory,
            ),
            patch(
                "agent_api.core.service.get_context_service",
                return_value=ctx_service,
            ),
            patch(
                "agent_api.core.service.get_mcp_manager",
                return_value=MagicMock(),
            ),
            patch(
                "agent_api.core.service.run_handoff_hook",
                mock_run_handoff_hook,
                create=True,
            ),
            patch(
                "agent_api.core.service.load_shared_memory_context",
                mock_load_context,
                create=True,
            ),
        ):
            collected = []
            async for event in chat_service.process_message_stream(
                session_id="session-abc",
                message="Show me financial data",
                client_id="client-123",
                context_service=ctx_service,
            ):
                collected.append(event)

        # The handoff hook should NOT have been called
        mock_run_handoff_hook.assert_not_awaited()
        # The shared memory context should NOT have been loaded
        mock_load_context.assert_not_awaited()

        # But the handoff event should still be emitted (specialist runs)
        handoff_events = [e for e in collected if '"event": "handoff"' in e]
        assert len(handoff_events) > 0, (
            "Expected handoff event even when skip_handoff_hook=True "
            "(specialist should still run)"
        )

    @pytest.mark.asyncio
    async def test_handoff_context_injected_into_specialist_state(
        self, chat_service, mock_graph,
    ):
        """Context loaded via load_shared_memory_context is injected
        into the specialist_state's metadata or client_context."""
        shared_context = {
            "cliente_abc": {"ramo": "TI", "projetos": ["BI", "RPA"]},
        }
        mock_run_handoff_hook = AsyncMock()
        mock_load_context = AsyncMock(return_value=shared_context)

        mock_specialist_graph = MagicMock()
        mock_specialist_graph.astream_events.return_value.__aiter__.return_value = []

        ctx_service = _mock_context_service()

        with (
            patch(
                "agent_api.core.service.get_factory",
            ) as mock_get_factory,
            patch(
                "agent_api.core.service.get_context_service",
                return_value=ctx_service,
            ),
            patch(
                "agent_api.core.service.get_mcp_manager",
                return_value=MagicMock(),
            ),
            patch(
                "agent_api.core.service.run_handoff_hook",
                mock_run_handoff_hook,
                create=True,
            ),
            patch(
                "agent_api.core.service.load_shared_memory_context",
                mock_load_context,
                create=True,
            ),
            patch(
                "agent_api.core.service._build_specialist_prompt",
                new=AsyncMock(return_value="specialist prompt"),
            ),
        ):
            mock_factory = MagicMock()
            mock_factory.get_frontdesk_graph.return_value = mock_graph
            mock_factory.get_specialist_graph.return_value = mock_specialist_graph
            mock_get_factory.return_value = mock_factory

            # Patch the TypedDict with a callable mock to capture AgentState kwargs.
            # AgentState is a TypedDict (dict subclass), so __init__ interception
            # doesn't work — we patch the reference at the module level instead.
            with patch(
                "blu_agent_framework.state.AgentState",
                side_effect=lambda **kw: kw,
            ) as mock_agent_state:
                collected = []
                async for event in chat_service.process_message_stream(
                    session_id="session-abc",
                    message="Show me financial data",
                    client_id="client-123",
                    context_service=ctx_service,
                ):
                    collected.append(event)

        # Find the AgentState call that includes handoff_context in metadata
        all_calls = mock_agent_state.call_args_list
        metadata_injections = [
            kw.get("metadata", {})
            for args, kw in all_calls
            if "handoff_context" in kw.get("metadata", {})
        ]
        assert any(
            md.get("handoff_context") == shared_context
            for md in metadata_injections
        ), (
            "Expected shared_memory_context to be injected into specialist_state's "
            "metadata via AgentState(). Captured calls: %s" % all_calls
        )
