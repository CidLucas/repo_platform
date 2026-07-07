# Routines System

Routines are the actual product of Blu: **multi-step background automations** that run on behalf of a client (cron, numeric trigger, event, or manual). Each routine delivers direct value *and* writes context back for agents (`dimension_state`, `client_insights`) so the LLM already knows business state when the user or system acts.

Source: `docs/system_reference/ROUTINES_SYSTEM.md`, `docs/llm_wiki/05_rotinas.md`, `docs/system_reference/TASK_PLAYBOOKS.md`, `services/agent_api/src/agent_api/core/routines.py`.

---

## Pipeline

```text
Trigger (cron | numeric | event | manual)
  → dispatch_execution  (INSERT client_routine_executions status=dispatched)
  → pg_cron @ 1/min → dispatch_routine_executions() [SQL]
      → POST /v1/internal/routines/run-dispatched  [pg_net]
          → check_and_enqueue_triggers()      [Python]
          → claim_dispatched_batch()           [SQL: SELECT … FOR UPDATE SKIP LOCKED]
          → run_dispatched_executions()        [asyncio.gather per execution]
              → _run_single_execution()        [semaphore + heartbeat + 120s timeout]
                  → _execute_one()             [step engine]
                      step loop: function | skill | llm | artifact | approval
                  → _notify_client()           [app / whatsapp / email]
```

Webhook entry: `routines_router.py` exposes `/v1/internal/routines/run-dispatched` to receive the pg_cron → pg_net dispatch.

---

## Data tables

| Table | Role |
|---|---|
| `cross_agent_routines` | **Catalog** of routines (shared by all clients). PK = `id` (slug, e.g. `financeiro_monitor`). Columns: `name`, `steps` (jsonb), `trigger_type`, `trigger_config`, `config_schema` (jsonb), `room`, `visibility` (user/internal). |
| `client_routines` | **Per-client subscription**. `client_id` FK, `routine_id` FK (or UUID for custom), `active`, `status` (active/suspended), `trigger_type`/`trigger_config` overrides, `config` (jsonb overrides), `notify_channel`, `last_run_at`, `consecutive_failures`, `steps` (custom), `source` (catalog/ai), `created_by_ai`. |
| `client_routine_executions` | **Execution log**. `status` (pending→dispatched→executing→completed/failed/awaiting_approval), `triggered_by` (NOT NULL), `trigger_data`, `dispatched_at`, `heartbeat_at`, `result_text`, `result_metadata` (checkpoint jsonb), `completed_at`, `worker_slug`, `failure_count`. |
| `dimension_state` | Structured analysis outputs per dimension (`financeiro`, `clientes`, …). `summary` (text), `structured` (jsonb), `valid_until`, `updated_at`. One row per dimension per client. |
| `artifact_delivery_claims` | Dedup of notification delivery. |

---

## Triggers

- **cron**: croniter expression; evaluated against `last_run_at`. First activation stamps `now()` and skips to avoid immediate fire.
- **numeric**: `_NUMERIC_METRIC_REGISTRY`. Fires when `current < threshold * baseline`. Valid metrics: `revenue`, `new_clients_monthly_rate`, `ticket_medio`, `churn_rate`, `pedidos_count`.
- **event**: `enqueue_routine_event()` or RPC `dispatch_routine_event()`.
- **manual**: direct INSERT into `client_routine_executions` with `status=dispatched`.

---

## Steps

Each step: `{ id, step (ordinal), type, inputs, outputs, on_failure (continue|halt), parallel_group?, on_complete? }`.

Step types:
- **function** — `routine_functions.py` fetch/analytics/storage functions.
- **skill** — a L2 `SkillDefinition` (narrative routines are pure-LLM, `required_tool_names=[]`).
- **llm** — direct Langfuse prompt.
- **artifact** — side-effect + dedupe (save insight/report/message).
- **approval** — HITL gate; re-dispatches via `trg_redispatch_after_approval`.

Step outputs are referenced by later steps via `{{variable}}` templates (must have defaults in the step, not in client config).

---

## Resilience

- **Atomic claim** via `SELECT … FOR UPDATE SKIP LOCKED`.
- **In-flight guard** to avoid double execution.
- **Semaphore**: max 4 parallel executions per client.
- **Heartbeat**: every 20s (`threading.Thread`) so the reaper doesn't kill live executions.
- **Timeout**: 120s → `failed` + circuit breaker.
- **Circuit breaker**: 3 consecutive failures → `client_routines.status = suspended`.

Notification: in-app, WhatsApp (`TwilioClient.send_whatsapp`), email (`_deliver_email`). Message = routine name + first line of `result_text` + link to app.

---

## Catalog (25 routines)

`agenda_monitor`, `cash_flow_alert`, `client_reactivation`, `clientes_monitor`, `collection_overdue`, `competitor_analysis`, `compras_monitor`, `context_report_monthly`, `context_report_post_ingestion`, `daily_briefing`, `daily_insights`, `deadline_radar`, `end_of_day_digest`, `financeiro_monitor`, `hidden_patterns`, `inventory_alert`, `meeting_prep`, `monthly_reconciliation`, `morning_sync`, `onboarding_complete`, `pending_decisions_review`, `sales_followup`, `satisfaction_survey`, `supplier_management`, `weekly_summary`.

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Routine doesn't fire | `active=true`, `status=active`, `consecutive_failures < 3`, valid `trigger_config`. (`active=false` blocks silently — check before testing.) |
| `summary=""` | empty Langfuse prompt, invalid `model_tier`, skill not in registry, tag mismatch. |
| `{{var}}` not resolved | prior step `outputs` key doesn't match next step template key. |
| `column does not exist` | `cross_agent_routines` PK is `id`, not `name`; JSONB accessed with `->>`, not `.` |
| Manual dispatch 401 | wrong token in `app_config.agent_api_routine_dispatch_token`. |

**Pitfalls when adding a routine:**
- `triggered_by` is NOT NULL on `client_routine_executions` — always pass `'cron'` on manual INSERT.
- `client_routines.source` accepts only `catalog | custom | system`.
- Never use `is_active` (doesn't exist) — use `active`.

---

## Adding a routine (summary)

1. Seed `cross_agent_routines` (slug `id`, `room`, `trigger_type`, `trigger_config`, `steps` jsonb, `agent_slug`, `active=true`).
2. Add fetch function in `routine_functions.py` + register in dispatch dict.
3. For `type=skill` steps: add skill file under `libs/blu_agent_framework/.../routines/`, add prompt to `templates.py` (`skill:{name}:system`, `type=skill`) **and** Langfuse (production).
4. Persist output via `routine_artifacts.py` (`save_insights()` / `save_report()`).
5. Activate for a client via `client_routines` INSERT.

Full recipe → [Dev Playbooks: add routine](workflows/dev-playbooks.md#1-add-a-new-routine).

---

## Next

- Execution engine source → `services/agent_api/src/agent_api/core/routines.py`
- Agent that creates routines → `platform` in [agents/catalog](agents/catalog.md)
- Step skill definitions → [agents/skills](agents/skills.md)
