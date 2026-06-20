"""routine_engine — Routine Engine cron jobs and handlers (T2.1).

The Routine Engine dispatches scheduled routines defined in
``cross_agent_routines`` (trigger_type='cron') and executes their
associated Python handlers via skill dispatch.

Routines in this package:
- ``prune_shared_memory`` — daily two-phase prune of shared_business_memory
"""
