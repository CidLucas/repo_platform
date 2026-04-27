"""Routine workers that run on a schedule (Phase 2 onward).

Each module exports a `run_for_client(client_id, ...)` coroutine and a
`run_all_enabled(...)` coroutine for fan-out. The CLI lives in each module
under `python -m vizu_agent_framework.routines.<name>`.
"""

from vizu_agent_framework.routines import daily_insights

__all__ = ["daily_insights"]
