# Blu MVP — Observability (EPIC-H)

This folder ships the artefacts for tickets BLU-MVP-070..072:

| File                             | Ticket      | Purpose                                                                          |
| -------------------------------- | ----------- | -------------------------------------------------------------------------------- |
| `grafana/blu-mvp-tool-pool.json` | BLU-MVP-071 | Grafana dashboard: tool latency p50/p95, error rate, approvals queued.           |
| `grafana/alerts-blu-mvp.yaml`    | BLU-MVP-072 | Provisioning alerts: MV staleness, RFQ webhook, Langfuse outage, approval queue. |

The OTel spans wired in [services/tool_pool_api/src/tool_pool_api/server/otel_instrumentation.py](../../services/tool_pool_api/src/tool_pool_api/server/otel_instrumentation.py) emit the metrics those panels consume:

- `vizu.tool.duration_ms` (histogram) — labels: `tool_name`, `outcome`, `client_id`, `tier`.
- `vizu.tool.calls_total` (counter)
- `vizu.tool.errors_total` (counter)

Span name: `mcp.tool.<tool_name>`, with attributes `tool.name`, `tool_name`, `client_id`, `tier`, `session_id`.

## Importing

### Dashboard

1. Open Grafana → **Dashboards → New → Import**.
2. Upload `grafana/blu-mvp-tool-pool.json`.
3. Pick the Mimir/Prometheus datasource for `${DS_PROM}` and the Supabase Postgres datasource for `${DS_PG}`.

### Alerts

```bash
# Grafana Cloud / OSS provisioning
cp docs/observability/grafana/alerts-blu-mvp.yaml \
   $GRAFANA_HOME/conf/provisioning/alerting/alerts-blu-mvp.yaml
systemctl reload grafana-server   # or restart the container
```

## Runbooks

### MV staleness

The Postgres query in alert #1 reads `analytics_v2.mv_refresh_log` (created by the MV refresh worker). When the alert fires:

```sql
REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_resumo_dashboard;
```

If `mv_refresh_log` itself is missing rows for > 25h, the pg_cron job `refresh_analytics_mvs` is stuck — inspect:

```sql
SELECT * FROM cron.job_run_details
 WHERE jobname = 'refresh_analytics_mvs'
 ORDER BY start_time DESC LIMIT 5;
```

### RFQ webhook failure

Inbound Twilio webhook lives in `services/tool_pool_api`. Common failure modes:

- Twilio signature mismatch → check `TWILIO_AUTH_TOKEN` envvar.
- `parse_supplier_reply` LLM call timing out → drop to FAST tier in `vizu_llm_service`.
- Postgres busy → look at `vizu.tool.duration_ms` for `parse_supplier_reply` in the dashboard.

### Langfuse outage

Prompts auto-fall back to the in-repo files under `libs/vizu_prompt_management/prompts/<domain>/<slug>.md`, so the agent keeps responding. Restore steps:

1. Confirm Langfuse status — https://status.langfuse.com.
2. Inspect `langfuse/worker` container logs.
3. Force-flush Langfuse buffers via `flush_langfuse()` on each service.

### Approval queue

The dashboard's _Approvals pending — by tenant_ panel breaks down the queue. If a single tenant has > 50 pending, the owner is overwhelmed or routing is wrong:

- Check `client_enabled_agents.approval_policy` for the agent in question.
- If routing role is set but no user has it, fall back to the owner.

## Coverage matrix

| Failure mode (roadmap §10)         | Alert                         |
| ---------------------------------- | ----------------------------- |
| MV stale > 25h                     | `blu-mvp-mv-staleness`        |
| Twilio outbound/inbound failures   | `blu-mvp-rfq-webhook-failure` |
| Langfuse unreachable               | `blu-mvp-langfuse-outage`     |
| Approval queue > 50 pending/tenant | `blu-mvp-approval-queue`      |

## RLS regression suite (BLU-MVP-073)

See [tests/test_rls_regression.py](../../tests/test_rls_regression.py).
