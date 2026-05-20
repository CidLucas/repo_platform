"""
blu_agent_framework.supervisor
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Shared result types for specialist worker invocations.

WorkerResult is returned by _invoke_worker in the routines engine and by
execute_step_node in the orchestrator when running specialist subgraphs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# =============================================================================
# Public result types
# =============================================================================


class WorkerTurnLimitError(Exception):
    """Raised when a worker with on_max_turns='raise' exceeds its turn budget."""

    def __init__(self, worker_slug: str, max_turns: int) -> None:
        self.worker_slug = worker_slug
        self.max_turns = max_turns
        super().__init__(
            f"Worker '{worker_slug}' exceeded max_turns={max_turns}."
        )


@dataclass
class WorkerResult:
    """Result returned from a single worker invocation."""

    summary: str
    worker_slug: str = ""
    structured_data: dict[str, Any] | None = None
    tool_calls_made: list[str] = field(default_factory=list)
    error: str | None = None
