"""
Integration tests for ChatService.process_message() with pre-flight hooks (T1.1f).

Tests the pre-flight shared memory integration in ChatService using mocked MCP
client and LangGraph.  Validates DD-PF-05 (hook points), DD-PF-07 (fail-open),
and agent_preflight_context injection into AgentState.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_preflight_mcp_result(data: dict) -> MagicMock:
    """Return a mock CallToolResult with .content[0].text containing JSON-encoded data."""
    text_item = MagicMock()
    text_item.text = json.dumps(data)

    result = MagicMock()
    result.content = [text_item]
    return result


def _preflight_data(
    agent_slug: str = "frontdesk",
    execution_count: int = 3,
) -> dict:
    """Return a synthetic pre-flight result dict."""
    return {
        "agent_metadata": [
            {"id": f"meta-{i:03d}", "entity_name": agent_slug, "key": f"execution:{i}"}
            for i in range(1, execution_count + 1)
        ],
        "agent_results": [
            {"id": f"result-{i:03d}", "entity_name": agent_slug, "key": f"decision:item-{i}"}
            for i in range(1, execution_count + 1)
        ],
        "execution_count": execution_count,
        "agent_slug": agent_slug,
    }


def _make_mock_client_ctx(
    client_id: str = "aaaaaaaa-bbbb-cccc-dddd-000000000001",
    nome_empresa: str = "Test Corp",
    tier: str = "BASIC",
) -> MagicMock:
    """Return a mock client context with required attributes."""
    ctx = MagicMock()
    ctx.id = client_id
    ctx.nome_empresa = nome_empresa
    ctx.tier = tier
    return ctx


def _make_mock_graph() -> MagicMock:
    """Return a mock compiled LangGraph with ainvoke that returns minimal state."""
    graph = MagicMock()

    async def _fake_ainvoke(state, config):
        return {
            "messages": [AIMessage(content="Resposta de teste.")],
        }

    graph.ainvoke = AsyncMock(side_effect=_fake_ainvoke)
    return graph


# ---------------------------------------------------------------------------
# Test: Frontdesk pre-flight loads context
# ---------------------------------------------------------------------------


class TestPreFlightFrontdesk:
    """ChatService.process_message() — frontdesk pre-flight scenarios."""

    @pytest.mark.asyncio
    async def test_frontdesk_preflight_injects_context(self):
        """Frontdesk pre-flight loads and agent_preflight_context is set in initial_state."""
        from agent_api.core.service import ChatService, ChatResult

        client_ctx = _make_mock_client_ctx()
        preflight = _preflight_data("frontdesk", execution_count=3)
        mock_call_tool = AsyncMock(return_value=_make_preflight_mcp_result(preflight))
        mock_graph = _make_mock_graph()
        mock_factory = MagicMock()
        mock_factory.get_frontdesk_graph.return_value = mock_graph

        # Capture the state passed to graph.ainvoke()
        captured_state: dict = {}

        async def _capture_ainvoke(state, config):
            nonlocal captured_state
            captured_state = dict(state)
            return {"messages": [AIMessage(content="OK")]}

        mock_graph.ainvoke = AsyncMock(side_effect=_capture_ainvoke)

        service = ChatService()

        with (
            patch(
                "agent_api.core.service.get_settings",
                return_value=MagicMock(SESSION_HISTORY_WINDOW=50),
            ),
            patch(
                "agent_api.core.service.get_factory",
                return_value=mock_factory,
            ),
            patch(
                "agent_api.core.service.get_mcp_manager",
                return_value=MagicMock(call_tool=mock_call_tool),
            ),
            patch.object(
                service,
                "_get_client_context",
                AsyncMock(return_value=client_ctx),
            ),
            patch.object(
                service,
                "_connect_mcp",
                AsyncMock(),
            ),
            patch.object(
                service,
                "_build_langfuse_config",
                return_value={"configurable": {}},
            ),
        ):
            result = await service.process_message(
                session_id="test-session",
                message="Olá",
                client_id=client_ctx.id,
                context_service=MagicMock(),
            )

        # Verify MCP call
        mock_call_tool.assert_called_once_with(
            "shared_memory_pre_flight",
            {"client_id": str(client_ctx.id), "agent_slug": "frontdesk"},
        )

        # Verify context injected
        assert "agent_preflight_context" in captured_state
        assert captured_state["agent_preflight_context"] == preflight
        assert isinstance(result, ChatResult)
        assert result.response == "OK"

    @pytest.mark.asyncio
    async def test_frontdesk_preflight_fails_continues_gracefully(self):
        """Pre-flight failure → continues without agent_preflight_context (DD-PF-07)."""
        from agent_api.core.service import ChatService, ChatResult

        client_ctx = _make_mock_client_ctx()
        mock_call_tool = AsyncMock(side_effect=Exception("MCP connection error"))
        mock_graph = _make_mock_graph()

        captured_state: dict = {}

        async def _capture_ainvoke(state, config):
            nonlocal captured_state
            captured_state = dict(state)
            return {"messages": [AIMessage(content="OK despite pre-flight failure")]}

        mock_graph.ainvoke = AsyncMock(side_effect=_capture_ainvoke)

        mock_factory = MagicMock()
        mock_factory.get_frontdesk_graph.return_value = mock_graph

        service = ChatService()

        with (
            patch(
                "agent_api.core.service.get_settings",
                return_value=MagicMock(SESSION_HISTORY_WINDOW=50),
            ),
            patch(
                "agent_api.core.service.get_factory",
                return_value=mock_factory,
            ),
            patch(
                "agent_api.core.service.get_mcp_manager",
                return_value=MagicMock(call_tool=mock_call_tool),
            ),
            patch.object(service, "_get_client_context", AsyncMock(return_value=client_ctx)),
            patch.object(service, "_connect_mcp", AsyncMock()),
            patch.object(service, "_build_langfuse_config", return_value={"configurable": {}}),
        ):
            result = await service.process_message(
                session_id="test-session",
                message="Olá",
                client_id=client_ctx.id,
                context_service=MagicMock(),
            )

        # State should NOT have agent_preflight_context (fail-open)
        assert captured_state.get("agent_preflight_context") is None
        assert isinstance(result, ChatResult)
        assert "OK" in result.response

    @pytest.mark.asyncio
    async def test_frontdesk_preflight_empty_result_does_not_break(self):
        """Pre-flight returns empty data → state has empty context but doesn't break."""
        from agent_api.core.service import ChatService, ChatResult

        client_ctx = _make_mock_client_ctx()
        preflight = _preflight_data("frontdesk", execution_count=0)
        # Make all lists empty
        preflight["agent_metadata"] = []
        preflight["agent_results"] = []

        mock_call_tool = AsyncMock(return_value=_make_preflight_mcp_result(preflight))

        captured_state: dict = {}

        async def _capture_ainvoke(state, config):
            nonlocal captured_state
            captured_state = dict(state)
            return {"messages": [AIMessage(content="OK with empty pre-flight")]}

        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(side_effect=_capture_ainvoke)

        mock_factory = MagicMock()
        mock_factory.get_frontdesk_graph.return_value = mock_graph

        service = ChatService()

        with (
            patch(
                "agent_api.core.service.get_settings",
                return_value=MagicMock(SESSION_HISTORY_WINDOW=50),
            ),
            patch(
                "agent_api.core.service.get_factory",
                return_value=mock_factory,
            ),
            patch(
                "agent_api.core.service.get_mcp_manager",
                return_value=MagicMock(call_tool=mock_call_tool),
            ),
            patch.object(service, "_get_client_context", AsyncMock(return_value=client_ctx)),
            patch.object(service, "_connect_mcp", AsyncMock()),
            patch.object(service, "_build_langfuse_config", return_value={"configurable": {}}),
        ):
            result = await service.process_message(
                session_id="test-session",
                message="Olá",
                client_id=client_ctx.id,
                context_service=MagicMock(),
            )

        # Context should be set even if empty
        assert "agent_preflight_context" in captured_state
        assert captured_state["agent_preflight_context"] == preflight
        assert isinstance(result, ChatResult)


# ---------------------------------------------------------------------------
# Test: Specialist handoff pre-flight
# ---------------------------------------------------------------------------


class TestPreFlightSpecialistHandoff:
    """ChatService.process_message() — specialist handoff pre-flight scenarios."""

    @pytest.mark.asyncio
    async def test_specialist_handoff_preflight_injects_context(self):
        """Specialist handoff loads pre-flight and injects into specialist state."""
        from agent_api.core.service import ChatService, ChatResult
        from langchain_core.messages import ToolMessage

        client_ctx = _make_mock_client_ctx()

        # Frontdesk pre-flight (simpler)
        fd_preflight = _preflight_data("frontdesk", execution_count=2)
        # Specialist pre-flight
        sp_preflight = _preflight_data("financeiro", execution_count=5)

        # Track sequence of call_tool calls
        call_sequence: list[tuple] = []

        async def _call_tool(tool_name, arguments):
            call_sequence.append((tool_name, arguments))
            if tool_name == "shared_memory_pre_flight":
                slug = arguments.get("agent_slug", "")
                if slug == "frontdesk":
                    return _make_preflight_mcp_result(fd_preflight)
                elif slug == "financeiro":
                    return _make_preflight_mcp_result(sp_preflight)
            return MagicMock()

        mock_mcp = MagicMock()
        mock_mcp.call_tool = AsyncMock(side_effect=_call_tool)

        # Frontdesk graph returns a sentinel to route to specialist
        async def _fd_ainvoke(state, config):
            return {
                "messages": [
                    HumanMessage(content="Preciso de análise financeira"),
                    ToolMessage(
                        content="__ROUTE_TO_SPECIALIST__:financeiro:cliente pediu financeiro",
                        tool_call_id="tc-001",
                    ),
                    AIMessage(content="Transferindo para especialista..."),
                ],
            }

        fd_graph = MagicMock()
        fd_graph.ainvoke = AsyncMock(side_effect=_fd_ainvoke)

        # Specialist graph
        sp_captured_state: dict = {}

        async def _sp_ainvoke(state, config):
            nonlocal sp_captured_state
            sp_captured_state = dict(state)
            return {"messages": [AIMessage(content="Análise financeira completa.")]}

        sp_graph = MagicMock()
        sp_graph.ainvoke = AsyncMock(side_effect=_sp_ainvoke)

        mock_factory = MagicMock()
        mock_factory.get_frontdesk_graph.return_value = fd_graph
        mock_factory.get_specialist_graph.return_value = sp_graph

        service = ChatService()

        with (
            patch(
                "agent_api.core.service.get_settings",
                return_value=MagicMock(SESSION_HISTORY_WINDOW=50),
            ),
            patch(
                "agent_api.core.service.get_factory",
                return_value=mock_factory,
            ),
            patch(
                "agent_api.core.service.get_mcp_manager",
                return_value=mock_mcp,
            ),
            patch.object(service, "_get_client_context", AsyncMock(return_value=client_ctx)),
            patch.object(service, "_connect_mcp", AsyncMock()),
            patch.object(service, "_build_langfuse_config", return_value={"configurable": {}}),
        ):
            result = await service.process_message(
                session_id="test-session",
                message="Preciso de análise financeira",
                client_id=client_ctx.id,
                context_service=MagicMock(),
            )

        # Verify both pre-flight calls were made
        assert len(call_sequence) >= 2
        assert call_sequence[0] == (
            "shared_memory_pre_flight",
            {"client_id": str(client_ctx.id), "agent_slug": "frontdesk"},
        )
        assert call_sequence[1] == (
            "shared_memory_pre_flight",
            {"client_id": str(client_ctx.id), "agent_slug": "financeiro"},
        )

        # Verify specialist state has pre-flight context
        assert "agent_preflight_context" in sp_captured_state
        assert sp_captured_state["agent_preflight_context"] == sp_preflight
        assert isinstance(result, ChatResult)

    @pytest.mark.asyncio
    async def test_specialist_preflight_fails_continues(self):
        """Specialist pre-flight fails → specialist still runs without context (DD-PF-07)."""
        from agent_api.core.service import ChatService, ChatResult
        from langchain_core.messages import ToolMessage

        client_ctx = _make_mock_client_ctx()

        call_sequence: list[tuple] = []

        async def _call_tool(tool_name, arguments):
            call_sequence.append((tool_name, arguments))
            if tool_name == "shared_memory_pre_flight":
                slug = arguments.get("agent_slug", "")
                if slug == "frontdesk":
                    return _make_preflight_mcp_result(_preflight_data("frontdesk"))
                elif slug == "financeiro":
                    raise Exception("Specialist pre-flight connection timeout")
            return MagicMock()

        mock_mcp = MagicMock()
        mock_mcp.call_tool = AsyncMock(side_effect=_call_tool)

        async def _fd_ainvoke(state, config):
            return {
                "messages": [
                    HumanMessage(content="Análise financeira"),
                    ToolMessage(
                        content="__ROUTE_TO_SPECIALIST__:financeiro:análise",
                        tool_call_id="tc-002",
                    ),
                    AIMessage(content="Encaminhando..."),
                ],
            }

        fd_graph = MagicMock()
        fd_graph.ainvoke = AsyncMock(side_effect=_fd_ainvoke)

        sp_captured_state: dict = {}

        async def _sp_ainvoke(state, config):
            nonlocal sp_captured_state
            sp_captured_state = dict(state)
            return {"messages": [AIMessage(content="Análise concluída apesar da falha.")]}

        sp_graph = MagicMock()
        sp_graph.ainvoke = AsyncMock(side_effect=_sp_ainvoke)

        mock_factory = MagicMock()
        mock_factory.get_frontdesk_graph.return_value = fd_graph
        mock_factory.get_specialist_graph.return_value = sp_graph

        service = ChatService()

        with (
            patch(
                "agent_api.core.service.get_settings",
                return_value=MagicMock(SESSION_HISTORY_WINDOW=50),
            ),
            patch(
                "agent_api.core.service.get_factory",
                return_value=mock_factory,
            ),
            patch(
                "agent_api.core.service.get_mcp_manager",
                return_value=mock_mcp,
            ),
            patch.object(service, "_get_client_context", AsyncMock(return_value=client_ctx)),
            patch.object(service, "_connect_mcp", AsyncMock()),
            patch.object(service, "_build_langfuse_config", return_value={"configurable": {}}),
        ):
            result = await service.process_message(
                session_id="test-session",
                message="Análise financeira",
                client_id=client_ctx.id,
                context_service=MagicMock(),
            )

        # Specialist state should NOT have pre-flight (fail-open)
        assert sp_captured_state.get("agent_preflight_context") is None
        assert isinstance(result, ChatResult)
