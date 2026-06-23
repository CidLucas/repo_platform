# GOAL: Hook de handoff entre agentes na shared memory
# BEHAVIOR: B4 — Criar handoff/__init__.py com exports
# DECISÃO: create_new
# Implementação mínima para teste RED passar (GREEN)

from blu_agent_framework.handoff.handoff_hook import run_handoff_hook
from blu_agent_framework.handoff.shared_memory_context import load_shared_memory_context

__all__ = ['run_handoff_hook', 'load_shared_memory_context']
