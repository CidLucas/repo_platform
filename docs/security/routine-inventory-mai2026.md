# Routine Inventory — Mai/2026

**Sprint 4 / E1** — Inventário de fetch_functions vs rotinas seedadas.
**Data:** 2026-05-25. **Auditoria contra prod** (Supabase `cross_agent_routines`).

## TL;DR

- 25 rotinas seedadas em prod (visibility: 8 builtin, 7 optional, 3 system, 7 user).
- 35 functions registradas no `routine_functions.py` registry.
- 25/25 functions chamadas pelas rotinas estão **registradas** → cobertura 100%.
- 16/16 skill slugs referenciados existem em `blu_agent_framework/skills.py` e `blu_prompt_management/templates.py`.
- 0 LLM steps usando `prompt_name` (Langfuse) — todas usam `type=skill` (padrão atual).
- **Gap declarado no backlog `daily_insights.py — arquivo não existe` está RESOLVIDO**: a rotina `daily_insights` usa `analytics.get_kpi_snapshots` (registrado) + skill `insights_synthesis` (existe) + `channels.create_alert` (registrado).

## Resultado

> Sem GAPs bloqueantes para onboarding. E2 (implementar fetch_functions críticas) **não é mais necessário** como escopo amplo — só E3 (validação end-to-end com cliente teste) faz sentido.

## Rotinas builtin (autoativadas)

| Rotina | Steps | Functions | Artifacts | Status |
|---|---|---|---|---|
| agenda_monitor | 5 | 4 | – | ✅ |
| cash_flow_alert | 4 | 3 | 1 (alert) | ✅ |
| clientes_monitor | 6 | 5 | – | ✅ |
| collection_overdue | 4 | 1 | 1 (whatsapp draft) | ✅ |
| compras_monitor | 4 | 3 | – | ✅ |
| financeiro_monitor | 6 | 5 | – | ✅ |
| inventory_alert | 2 | 1 | 1 (alert) | ✅ |
| supplier_management | 2 | 1 | 1 (alert) | ✅ |

## Rotinas system (lifecycle)

| Rotina | Trigger | Status |
|---|---|---|
| context_report_monthly | cron mensal | ✅ |
| context_report_post_ingestion | event | ✅ |
| daily_insights | cron diário | ✅ |

## Functions registradas mas não usadas por nenhuma rotina (10)

São helpers/exploratórios — não removidos para manter API estável:

```
analytics.gather_client_context
analytics.get_weekly_activity
biblioteca.get_document_status
biblioteca.get_recent_uploads
biblioteca.get_unanswered_queries
biblioteca.submit_pending_for_hitl
compras.get_purchase_trends
compras.get_stock_levels
compras.get_supplier_performance
insights.generate_from_kpis
```

Recomendação: manter; aparecerão quando rotinas de Biblioteca/Compras forem ativadas.

## Functions usadas (25, 100% registradas)

```
agenda.get_calendar_events
agenda.get_upcoming_deadlines
agenda.get_upcoming_meetings
analytics.generate_context_report
analytics.get_client_pipeline
analytics.get_daily_activity
analytics.get_daily_schedule
analytics.get_inventory_alerts
analytics.get_kpi_snapshots
analytics.get_nps_data
analytics.get_overdue_approvals
analytics.get_overdue_customers
analytics.get_pending_approvals
analytics.get_sales_performance
analytics.get_supplier_orders
analytics.query_inactive_clients
financeiro.evaluate_cash_alert
financeiro.get_cash_position
financeiro.get_recent_transactions
integrations.check_health
knowledge.get_masterprompt
memory.write_dimension_state
web.crawl_competitor_pages
web.extract_company_context
web.get_meeting_participant_context
```

## Skills (16, 100% existem)

```
agenda_monitor_report     clients_monitor_report     collection_messages
competitor_analysis       end_of_day_digest          finance_monitor_report
followup_draft            hidden_patterns            insights_synthesis
inventory_digest          meeting_brief              morning_plan
reactivation_proposal     reconciliation_report      satisfaction_survey
weekly_summary
```

Todas presentes em:
- `libs/blu_prompt_management/src/blu_prompt_management/templates.py` (system prompts keyed `skill:<name>:system`)
- `libs/blu_agent_framework/src/blu_agent_framework/skills.py` (skill class/runner)

## Artifact channels (registrados em `routine_artifacts.py`)

```
channels.send_email_batch       channels.send_email
channels.send_whatsapp          channels.create_alert
channels.request_approval       channels.request_document_review
storage.save_context_document   storage.save_insights
```

Todos têm dedupe via `artifact_log` (UNIQUE execution_id, step_id) implementado em
Sprint 4/D2 para tipos side-effectful: `email`, `whatsapp`, `document`.

## Próximos passos

E2 fica **descartado como sprint dedicada** — não há gaps. Apenas:
- E3: rodar cliente de teste interno por 72h e validar que todas as 25 rotinas
  disparam pelo menos uma vez sem erro. Documentar em
  `docs/security/test-onboarding-log-mai2026.md`.
- Considerar ativar as 10 functions hoje "unused" via rotinas optional (biblioteca/compras)
  quando demanda real aparecer — não bloqueia onboarding.

## Como reproduzir esta auditoria

```bash
# Functions registradas
grep -A1 '^@register(' services/agent_api/src/agent_api/core/routine_functions.py \
  | grep -oE '"[a-z_]+\.[a-z_]+"' | sort -u

# Functions chamadas em prod
psql "$SUPABASE_DB_URL" -tAc "
  SELECT DISTINCT s->>'function'
  FROM cross_agent_routines, jsonb_array_elements(steps) s
  WHERE s->>'type'='function' ORDER BY 1;"
```
