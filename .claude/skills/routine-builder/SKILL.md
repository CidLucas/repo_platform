---
name: routine-builder
description: Create, modify, and troubleshoot scheduled routines in the Blu platform. Use when building a new routine, adding step functions or artifact handlers, debugging step failures, fixing insight display issues in rooms, or when the user mentions cross_agent_routines, client_routines, routine steps, or run_routine.py.
---

# Routine Builder

## Quick start

Routines are state machines in Supabase. Each step outputs a dict that merges into shared state — later steps read values via `{{key}}` placeholders.

```bash
# Test any routine end-to-end:
docker exec blu_agent_api python run_routine.py <routine_id> [client_uuid]
```

## Workflows

### Create a new routine

- [ ] Insert into `cross_agent_routines`: `id`, `name`, `room`, `trigger_type`, `steps` JSONB
- [ ] Add needed `@register("x.y")` handlers to `routine_functions.py` (function steps) or `routine_artifacts.py` (artifact steps)
- [ ] Insert into `client_routines`: `routine_id`, `client_id`, `active=true`, `status='active'`, `source='catalog'`
- [ ] Copy edited files to container, then run `run_routine.py` to verify

### Add a function step (deterministic, no LLM)

Register in `services/agent_api/src/agent_api/core/routine_functions.py`:

```python
@register("namespace.fn_name")
async def _my_fn(inputs: dict, client_id: str) -> dict:
    ...
    return {"output_key": value}
```

### Add an artifact step (side-effect)

Register in `services/agent_api/src/agent_api/core/routine_artifacts.py`:

```python
@register("namespace.action_name")
async def _my_artifact(inputs: dict, client_id: str) -> dict:
    ...
    return {"result_key": value}
```

### Add a skill step (LLM agent)

In the step definition, set `skill_slug` to an available agent and `outputs` with one key if the LLM returns a JSON array — it will be auto-wrapped under that key.
Available slugs: `financeiro`, `compras`, `estrategia`, `clientes`, `agenda`, `documentos`, `context-gatherer`

## Troubleshooting checklist

```
[ ] Step outputs missing?       → check result_metadata in client_routine_executions
[ ] Skill returns no structure? → outputs must have exactly one key for array auto-wrap
[ ] Artifact gets a string?     → use pure "{{key}}" not inline "text {{key}}" for lists/dicts
[ ] Insights not in room?       → dimension mismatch — see REFERENCE.md § Dimension map
[ ] Toggle ON but not in panel? → client_routines.source must not be 'system'
[ ] DB constraint violation?    → severity must be: info | warning | error (not alert)
[ ] Handler not found?          → docker cp the file to the container after editing
```

## Advanced reference

→ [REFERENCE.md](references/REFERENCE.md) — step schema, available functions & artifacts, dimension map, DB tables, executor internals
