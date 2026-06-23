"""BL-xxx — shared_memory_context tests (B3).

Tests for load_shared_memory_context(), which loads context from shared
memory for handoff target entities.

GOAL: Hook de handoff entre agentes na shared memory
BEHAVIOR: B3 — Criar shared_memory_context.py com load_shared_memory_context()
ACCEPTANCE CRITERION: AC2 — Agente B lê contexto da shared memory após handoff
DECISÃO DO PLANNER: create_new — novo pacote handoff/ com extensão de AgentState
"""

import pytest

from blu_agent_framework.handoff.shared_memory_context import (
    load_shared_memory_context,
)


class TestLoadSharedMemoryContext:
    """load_shared_memory_context(agent_type, entity_names, tool_pool_client) → dict

    Para cada entity_name em entity_names, chama shared_memory_read (MCP tool
    via tool_pool_client.call_tool) e retorna
    {entity_name: {key: value, ...}}.
    """

    @pytest.mark.asyncio
    async def test_returns_context_dict_for_given_entity_names(self):
        """Carrega contexto de múltiplas entidades chamando shared_memory_read
        para cada entity_name e retorna dict estruturado."""
        # ------------------------------------------------------------------ #
        # Arrange
        # ------------------------------------------------------------------ #
        calls_log: list[dict] = []

        async def mock_call_tool(tool_name: str, arguments: dict, meta: dict | None = None) -> dict:
            calls_log.append({"tool": tool_name, "args": arguments})
            entity_name = arguments.get("entity_name", "unknown")
            return {
                "content": [
                    {
                        "text": f'{{"entity_name": "{entity_name}", "key": "preferencia_horario", "value": {{"horario": "manha"}}}}'
                    }
                ]
            }

        mock_client = type("FakeMCPClient", (), {"call_tool": mock_call_tool})()

        # ------------------------------------------------------------------ #
        # Act
        # ------------------------------------------------------------------ #
        result = await load_shared_memory_context(
            agent_type="specialist",
            entity_names=["joao", "maria"],
            tool_pool_client=mock_client,
        )

        # ------------------------------------------------------------------ #
        # Assert
        # ------------------------------------------------------------------ #
        assert isinstance(result, dict), "Deve retornar um dicionário"
        assert "joao" in result, "joao deve estar no resultado"
        assert "maria" in result, "maria deve estar no resultado"
        assert result["joao"]["preferencia_horario"]["horario"] == "manha"

        # Verifica que chamou shared_memory_read para cada entity_name
        assert len(calls_log) == 2
        assert calls_log[0]["tool"] == "shared_memory_read"
        assert calls_log[0]["args"]["entity_name"] == "joao"
        assert calls_log[1]["args"]["entity_name"] == "maria"
