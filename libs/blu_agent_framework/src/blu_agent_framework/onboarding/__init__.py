
from __future__ import annotations
# GOAL: Hook pós-ETL onboarding — Issue #24, Fase 2
# BEHAVIOR: Hook que escreve snapshot inicial na shared memory após ETL onboarding

from blu_agent_framework.onboarding.onboarding_shared_memory_hook import (
    write_onboarding_snapshot_to_shared_memory,
)

__all__ = ["write_onboarding_snapshot_to_shared_memory"]
