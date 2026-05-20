# Routine Builder — Reference

## DB tables

| Table                       | Purpose                                                                                                   |
| --------------------------- | --------------------------------------------------------------------------------------------------------- |
| `cross_agent_routines`      | Routine catalog: `id`, `name`, `room`, `trigger_type`, `trigger_config`, `steps` JSONB                    |
| `client_routines`           | Per-client enablement: `routine_id`, `client_id`, `active`, `status`, `source`, `config`, `last_run_at`   |
| `client_routine_executions` | Run log: `status`, `result_text`, `result_metadata` (full step I/O), `triggered_by`                       |
| `client_insights`           | Persisted insights: `dimension`, `kpi`, `title`, `observation`, `recommendation`, `severity`, `dismissed` |

`client_routines.source` values: `catalog` (standard), `custom` (user-created), `system` (internal — hidden from frontend active panel).

---

## Step schema (full)

```jsonc
{
  "step": 1, // execution order (int)
  "id": "fetch_kpis", // unique string key within the routine
  "type": "function", // function | skill | artifact
  "on_failure": "halt", // halt (stop execution) | continue (skip step)

  // function / artifact only:
  "function": "analytics.get_kpi_snapshots",
  "inputs": { "period": "30d", "data": "{{state_key}}" },

  // skill only:
  "skill_slug": "financeiro",
  "task_template": "Analise {{kpi_data}} para {{nome_empresa}}...",
  "outputs": { "insights": "list of insight dicts" },
}
```

State available in every step: `client_id`, `routine_name`, `exec_id`, `nome_empresa`, plus all keys from `client_routines.config` and outputs of all prior steps.

---

## Registered function handlers (`routine_functions.py`)

| Name                                | Inputs                                 | Outputs                                         |
| ----------------------------------- | -------------------------------------- | ----------------------------------------------- |
| `analytics.query_inactive_clients`  | `lookback_months`, `days_inactive`     | `client_list`                                   |
| `analytics.gather_client_context`   | `client_list`                          | `client_context` (enriched with cluster labels) |
| `analytics.generate_context_report` | _(none)_                               | `context_report_summary`, `report_upserted`     |
| `analytics.get_kpi_snapshots`       | `period` (e.g. `"30d"`), `window_days` | `kpi_data` (dict by dimension)                  |
| `web.extract_company_context`       | `url` (optional, falls back to DB)     | `website_content`                               |
| `knowledge.get_masterprompt`        | _(none)_                               | `masterprompt`, `masterprompt_exists`           |

---

## Registered artifact handlers (`routine_artifacts.py`)

| Name                            | Key inputs                                          | Key outputs                                    |
| ------------------------------- | --------------------------------------------------- | ---------------------------------------------- |
| `channels.send_email`           | `to`, `subject`, `body_html`                        | `email_sent`                                   |
| `channels.send_email_batch`     | `emails` (list of `{to_email, subject, body_html}`) | `emails_sent`, `emails_failed`, `delivery_log` |
| `channels.create_alert`         | `title`, `body`, `priority`, `agent_slug`           | `alert_id`, `alert_created`                    |
| `channels.send_whatsapp`        | `to` (E.164), `body`                                | `whatsapp_sent`                                |
| `storage.save_context_document` | `content` (md), `title`, `file_name`, `category`    | `document_saved`, `storage_path`               |
| `storage.save_insights`         | `insights` (list of insight dicts)                  | `insights_written`                             |

---

## Insight dict schema (for `storage.save_insights`)

```jsonc
{
  "dimension": "finance", // see Dimension map below
  "kpi": "receita_liquida",
  "title": "Short title ≤200 chars",
  "observation": "What the data shows",
  "recommendation": "Suggested action",
  "severity": "warning", // info | warning | error  (NOT alert)
  "metric_value": 195.59, // number or null
  "baseline_value": 100.0, // number or null
  "variance_pct": 95.59, // number or null
}
```

---

## Dimension map (routine → frontend room)

| Routine dimension value             | Room           | Room filter accepts |
| ----------------------------------- | -------------- | ------------------- |
| `finance` or `financeiro`           | FinanceiroRoom | both                |
| `supply`, `inventory`, or `compras` | ComprasRoom    | all three           |
| `commercial` or `clientes`          | ClientesRoom   | both                |
| `estrategia`                        | EstrategiaRoom | `estrategia` only   |
| `agenda`                            | AgendaRoom     | `agenda` only       |
| `documentos`                        | DocumentosRoom | `documentos` only   |

Insights with `dimension = null` appear in all rooms.

---

## Skill step executor internals

File: `services/agent_api/src/agent_api/core/routines.py` → `_execute_skill_step`

1. Resolves `task_template` against merged state + inputs
2. Calls `_invoke_worker(skill_slug, task, ...)` → `WorkerResult(summary, structured_data, error)`
3. If `structured_data` is present → merged directly into step outputs
4. Else if `summary` contains JSON → `_extract_json_from_text(summary, outputs_schema)` extracts it
   - JSON object → merged as-is
   - JSON array + `outputs` has one key → wrapped as `{key: array}`
5. Always adds `summary` (truncated to 500 chars) and `worker_slug` to outputs

---

## Template resolution rules

| Pattern            | Example              | Result                                     |
| ------------------ | -------------------- | ------------------------------------------ |
| Pure placeholder   | `"{{insights}}"`     | Preserves original type (list, dict, int…) |
| Inline placeholder | `"Total: {{count}}"` | Always stringified                         |
| Missing key        | `"{{unknown}}"`      | Left as-is (placeholder not replaced)      |

Implemented in both `routines.py` and `run_routine.py` via `_PURE_PLACEHOLDER_RE` / `_INLINE_PLACEHOLDER_RE`.

---

## Copying files to the container

```bash
docker cp services/agent_api/src/agent_api/core/routine_functions.py \
  blu_agent_api:/app/src/agent_api/core/routine_functions.py

docker cp services/agent_api/src/agent_api/core/routine_artifacts.py \
  blu_agent_api:/app/src/agent_api/core/routine_artifacts.py
```

The API does not auto-reload on file change; a container restart is needed for production, but `run_routine.py` re-imports on each run so a copy is sufficient for testing.
