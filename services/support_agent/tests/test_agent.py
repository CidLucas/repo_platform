"""
Tests for SupportAgent.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from support_agent.core.agent import SupportAgent


class MockClientContext:
    """Mock client context for testing."""

    def __init__(self):
        self.id = uuid4()
        self.nome_empresa = "Test Company"
        self.tier = "ENTERPRISE"
        self._enabled_tools = ["executar_rag_cliente", "escalar_ticket"]

    def get_enabled_tools_list(self):
        return self._enabled_tools


class TestSupportAgent:
    """Tests for SupportAgent class."""

    def test_agent_initialization(self):
        """Test that agent initializes correctly."""
        context = MockClientContext()

        with patch('support_agent.core.agent.ToolRegistry') as mock_registry:
            mock_registry.get_available_tools.return_value = []

            agent = SupportAgent(cliente_context=context)

            assert agent.config.name == "support_agent"
            assert agent.config.role == "Technical Support Specialist"
            assert agent.config.elicitation_strategy == "issue_classification"
            assert agent.config.max_turns == 25

    def test_agent_uses_correct_elicitation_strategy(self):
        """Test that agent uses issue_classification strategy."""
        context = MockClientContext()

        with patch('support_agent.core.agent.ToolRegistry') as mock_registry:
            mock_registry.get_available_tools.return_value = []

            agent = SupportAgent(cliente_context=context)

            # Issue classification vs support_triage or sales_pipeline
            assert agent.config.elicitation_strategy == "issue_classification"

    def test_agent_has_longer_max_turns(self):
        """Test that support agent allows more turns for complex issues."""
        context = MockClientContext()

        with patch('support_agent.core.agent.ToolRegistry') as mock_registry:
            mock_registry.get_available_tools.return_value = []

            agent = SupportAgent(cliente_context=context)

            # 25 turns vs 20 (atendente) or 15 (vendas)
            assert agent.config.max_turns == 25

    def test_agent_respects_tier_tools(self):
        """Test that agent gets tools based on tier."""
        context = MockClientContext()

        with patch('support_agent.core.agent.ToolRegistry') as mock_registry:
            mock_tool = MagicMock()
            mock_tool.name = "escalar_ticket"
            mock_registry.get_available_tools.return_value = [mock_tool]

            agent = SupportAgent(cliente_context=context)

            mock_registry.get_available_tools.assert_called_once_with(
                enabled_tools=["executar_rag_cliente", "escalar_ticket"],
                tier="ENTERPRISE",
            )

            assert "escalar_ticket" in agent.config.enabled_tools

    def test_agent_includes_metadata(self):
        """Test that agent includes client metadata for tracing."""
        context = MockClientContext()

        with patch('support_agent.core.agent.ToolRegistry') as mock_registry:
            mock_registry.get_available_tools.return_value = []

            agent = SupportAgent(cliente_context=context)

            assert agent.config.metadata["nome_empresa"] == "Test Company"
            assert agent.config.metadata["tier"] == "ENTERPRISE"


class TestSupportAgentProcessMessage:
    """Tests for SupportAgent.process_message."""

    @pytest.mark.asyncio
    async def test_process_message_invokes_agent(self):
        """Test that process_message invokes the underlying agent."""
        context = MockClientContext()

        with patch('support_agent.core.agent.ToolRegistry') as mock_registry:
            mock_registry.get_available_tools.return_value = []

            agent = SupportAgent(cliente_context=context)

            # Mock the compiled agent
            agent.agent = AsyncMock()
            agent.agent.ainvoke.return_value = {
                "messages": [MagicMock(content="Entendi o problema. Vou verificar.")],
                "issue_category": "technical",
                "severity": "high",
            }

            result = await agent.process_message(
                message="Meu sistema está dando erro",
                session_id="test-session",
            )

            assert result["response"] == "Entendi o problema. Vou verificar."
            assert result["issue_category"] == "technical"
            assert result["severity"] == "high"
            agent.agent.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_passes_ticket_context(self):
        """Test that ticket context is passed to agent."""
        context = MockClientContext()

        with patch('support_agent.core.agent.ToolRegistry') as mock_registry:
            mock_registry.get_available_tools.return_value = []

            agent = SupportAgent(cliente_context=context)
            agent.agent = AsyncMock()
            agent.agent.ainvoke.return_value = {"messages": [MagicMock(content="Ok")]}

            await agent.process_message(
                message="Continuo com o mesmo problema",
                session_id="test-session",
                ticket_context={"ticket_id": "TKT-123"},
            )

            call_args = agent.agent.ainvoke.call_args[0][0]
            assert call_args["ticket_context"]["ticket_id"] == "TKT-123"
