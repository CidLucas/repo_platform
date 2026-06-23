"""BL-xxx — Behavior B2: Criar handoff_hook.py com run_handoff_hook().

GOAL: Hook de handoff entre agentes na shared memory
BEHAVIOR: B2 — Criar handoff_hook.py com run_handoff_hook()
ACCEPTANCE CRITERION: AC1 — Agente A escreve learning notes na shared memory durante handoff
DECISÃO DO PLANNER: create_new — libs/blu_agent_framework/src/blu_agent_framework/handoff/handoff_hook.py

Testa que run_handoff_hook() retorna early (nada escrito) quando
agent_state['has_learning'] é False.
"""

import pytest

from blu_agent_framework.handoff.handoff_hook import (
    run_handoff_hook,
)


class TestRunHandoffHookEarlyReturn:
    """run_handoff_hook(agent_state, tool_pool_client) → None

    Se agent_state['has_learning'] é False, deve retornar imediatamente
    sem chamar shared_memory_write no tool_pool_client.
    """

    @pytest.mark.asyncio
    async def test_returns_early_when_has_learning_is_false(self):
        """Com has_learning=False, run_handoff_hook não deve chamar
        shared_memory_write e deve retornar None."""
        # ------------------------------------------------------------------ #
        # Arrange
        # ------------------------------------------------------------------ #
        call_count = 0

        async def mock_call_tool(tool_name: str, arguments: dict, meta: dict | None = None) -> dict:
            nonlocal call_count
            call_count += 1
            return {"content": [{"text": "{}"}]}

        mock_client = type("FakeMCPClient", (), {"call_tool": mock_call_tool})()

        agent_state = {
            "has_learning": False,
            "learning_notes": [
                {"note": "Cliente prefere contato por e-mail", "confidence": 0.8},
            ],
            "agent_slug": "test_agent",
            "session_id": "sess_abc123",
        }

        # ------------------------------------------------------------------ #
        # Act
        # ------------------------------------------------------------------ #
        result = await run_handoff_hook(
            agent_state=agent_state,
            tool_pool_client=mock_client,
        )

        # ------------------------------------------------------------------ #
        # Assert
        # ------------------------------------------------------------------ #
        assert result is None, "Deve retornar None quando não há learning"
        assert call_count == 0, "Não deve chamar shared_memory_write quando has_learning=False"
