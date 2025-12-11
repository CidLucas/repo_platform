"""
Tests for VendasAgent.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from vendas_agent.core.agent import VendasAgent


class MockClientContext:
    """Mock client context for testing."""

    def __init__(self):
        self.id = uuid4()
        self.nome_empresa = "Test Company"
        self.tier = "SME"
        self._enabled_tools = ["executar_rag_cliente", "buscar_produtos"]

    def get_enabled_tools_list(self):
        return self._enabled_tools


class TestVendasAgent:
    """Tests for VendasAgent class."""

    def test_agent_initialization(self):
        """Test that agent initializes correctly."""
        context = MockClientContext()

        with patch('vendas_agent.core.agent.ToolRegistry') as mock_registry:
            mock_registry.get_available_tools.return_value = []

            agent = VendasAgent(cliente_context=context)

            assert agent.config.name == "vendas_agent"
            assert agent.config.role == "Sales Representative"
            assert agent.config.elicitation_strategy == "sales_pipeline"
            assert agent.config.max_turns == 15

    def test_agent_uses_correct_elicitation_strategy(self):
        """Test that agent uses sales_pipeline strategy."""
        context = MockClientContext()

        with patch('vendas_agent.core.agent.ToolRegistry') as mock_registry:
            mock_registry.get_available_tools.return_value = []

            agent = VendasAgent(cliente_context=context)

            # Sales pipeline vs support_triage
            assert agent.config.elicitation_strategy == "sales_pipeline"

    def test_agent_respects_tier_tools(self):
        """Test that agent gets tools based on tier."""
        context = MockClientContext()

        with patch('vendas_agent.core.agent.ToolRegistry') as mock_registry:
            mock_tool = MagicMock()
            mock_tool.name = "buscar_produtos"
            mock_registry.get_available_tools.return_value = [mock_tool]

            agent = VendasAgent(cliente_context=context)

            mock_registry.get_available_tools.assert_called_once_with(
                enabled_tools=["executar_rag_cliente", "buscar_produtos"],
                tier="SME",
            )

            assert "buscar_produtos" in agent.config.enabled_tools

    def test_agent_includes_metadata(self):
        """Test that agent includes client metadata for tracing."""
        context = MockClientContext()

        with patch('vendas_agent.core.agent.ToolRegistry') as mock_registry:
            mock_registry.get_available_tools.return_value = []

            agent = VendasAgent(cliente_context=context)

            assert agent.config.metadata["nome_empresa"] == "Test Company"
            assert agent.config.metadata["tier"] == "SME"


class TestVendasAgentProcessMessage:
    """Tests for VendasAgent.process_message."""

    @pytest.mark.asyncio
    async def test_process_message_invokes_agent(self):
        """Test that process_message invokes the underlying agent."""
        context = MockClientContext()

        with patch('vendas_agent.core.agent.ToolRegistry') as mock_registry:
            mock_registry.get_available_tools.return_value = []

            agent = VendasAgent(cliente_context=context)

            # Mock the compiled agent
            agent.agent = AsyncMock()
            agent.agent.ainvoke.return_value = {
                "messages": [MagicMock(content="Olá! Como posso ajudar?")],
            }

            result = await agent.process_message(
                message="Quero comprar um produto",
                session_id="test-session",
            )

            assert result["response"] == "Olá! Como posso ajudar?"
            agent.agent.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_passes_elicitation_response(self):
        """Test that elicitation response is passed to agent."""
        context = MockClientContext()

        with patch('vendas_agent.core.agent.ToolRegistry') as mock_registry:
            mock_registry.get_available_tools.return_value = []

            agent = VendasAgent(cliente_context=context)
            agent.agent = AsyncMock()
            agent.agent.ainvoke.return_value = {"messages": [MagicMock(content="Ok")]}

            await agent.process_message(
                message="smartphones",
                session_id="test-session",
                elicitation_response={
                    "elicitation_id": "abc-123",
                    "response": "smartphones",
                },
            )

            call_args = agent.agent.ainvoke.call_args[0][0]
            assert call_args["elicitation_response"]["elicitation_id"] == "abc-123"
