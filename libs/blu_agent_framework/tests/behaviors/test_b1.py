"""
BL-006 — Behavior B1: Adicionar campos de handoff ao AgentState.

GOAL: Hook de handoff entre agentes na shared memory
BEHAVIOR: Adicionar campos de handoff ao AgentState
ACCEPTANCE CRITERION: AC1 — Agente A escreve learning notes na shared memory durante handoff
DECISÃO DO PLANNER: create_new — libs/blu_agent_framework/src/blu_agent_framework/state.py

Testa que create_initial_state inclui os 3 novos campos de handoff
com seus valores padrão corretos:
  - has_learning: bool (default False)
  - learning_notes: list[dict] (default [])
  - skip_handoff_hook: bool (default False)
"""

import pytest

from blu_agent_framework.state import create_initial_state


class TestHandoffFieldsInInitialState:
    """B1 — create_initial_state must include the 3 handoff fields with correct defaults."""

    def test_has_learning_defaults_to_false(self):
        """has_learning must be False in the initial state."""
        state = create_initial_state("test-sid", "test-cid")
        assert state["has_learning"] is False, (
            "has_learning should default to False"
        )

    def test_learning_notes_defaults_to_empty_list(self):
        """learning_notes must be [] in the initial state."""
        state = create_initial_state("test-sid", "test-cid")
        assert state["learning_notes"] == [], (
            "learning_notes should default to []"
        )

    def test_skip_handoff_hook_defaults_to_false(self):
        """skip_handoff_hook must be False in the initial state."""
        state = create_initial_state("test-sid", "test-cid")
        assert state["skip_handoff_hook"] is False, (
            "skip_handoff_hook should default to False"
        )
