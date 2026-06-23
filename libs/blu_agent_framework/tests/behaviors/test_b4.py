"""BL-B4 — Behavior B4: Criar handoff/__init__.py com exports.

GOAL: Hook de handoff entre agentes na shared memory
BEHAVIOR: B4 — Criar handoff/__init__.py com exports
ACCEPTANCE CRITERION: AC1/AC2 — Ambos run_handoff_hook e load_shared_memory_context
    exportados publicamente via handoff package; handoff acessível via blu_agent_framework
DECISÃO DO PLANNER: create_new — libs/blu_agent_framework/src/blu_agent_framework/handoff/__init__.py
    + blu_agent_framework/__init__.py

Testa que:
  1. run_handoff_hook é exportado pelo handoff package (via __all__)
  2. load_shared_memory_context é exportado pelo handoff package (via __all__)
  3. O package handoff é acessível via blu_agent_framework.handoff
"""

import pytest

from blu_agent_framework.handoff import run_handoff_hook, load_shared_memory_context


class TestHandoffPackageExports:
    """B4 — handoff/__init__.py deve exportar ambas as funções publicamente."""

    def test_exports_run_handoff_hook(self):
        """run_handoff_hook deve ser importável do handoff package."""
        assert callable(run_handoff_hook), (
            "run_handoff_hook deve ser callable"
        )

    def test_exports_load_shared_memory_context(self):
        """load_shared_memory_context deve ser importável do handoff package."""
        assert callable(load_shared_memory_context), (
            "load_shared_memory_context deve ser callable"
        )

    def test_handoff_all_contains_both(self):
        """__all__ no handoff/{__init__}.py deve listar ambas as funções."""
        import blu_agent_framework.handoff as handoff_pkg
        assert "run_handoff_hook" in handoff_pkg.__all__
        assert "load_shared_memory_context" in handoff_pkg.__all__

    def test_handoff_accessible_via_blu_agent_framework(self):
        """blu_agent_framework deve exportar o handoff subpackage."""
        import blu_agent_framework
        assert hasattr(blu_agent_framework, "handoff"), (
            "blu_agent_framework deve ter atributo 'handoff'"
        )
        assert "handoff" in blu_agent_framework.__all__, (
            "handoff deve estar em blu_agent_framework.__all__"
        )
