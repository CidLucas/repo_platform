# Repo Index — Issue #24: Hook pós-ETL Onboarding Snapshot Inicial

> Branch: `phase-2/issue-24-post-etl-onboarding-snapshot`
> Fase 2, T2.4
> Gerado: 2026-06-19

## Arquivos Afetados (6 subtarefas)

### T2.4.1 — Aplicar migrações de templates de snapshot (prereq #22)

| Arquivo | Status | Descrição |
|---------|--------|-----------|
| `supabase/migrations/proposed/20260619000000_shared_business_memory.sql` | ✅ Existe | Cria tabela `public.shared_business_memory` com RLS. entity_type CHECK atual: skill, client, contact, supplier, user. |
| `supabase/migrations/proposed/20260619000002_shared_memory_integrity.sql` | ✅ Existe | Trigger `validate_memory_insert()` + view `valid_shared_memory`. Valida key, category, value, confidence. |
| `supabase/migrations/proposed/20260619000003_snapshot_templates.sql` | ⚠️ CONFLITO | Issue #22: adiciona coluna `version` + `'snapshot'` ao CHECK. **Conflito com routine_checkpoint_rpc.sql (mesmo timestamp).** |
| `supabase/migrations/proposed/20260619000003_routine_checkpoint_rpc.sql` | ⚠️ CONFLITO | Issue #21: adiciona `'agent_result', 'agent_metadata', 'routine'` ao MESMO CHECK. **Destruição mútua.** |
| `libs/blu_context_service/src/blu_context_service/context_schemas.py` | ✅ Pronto | `_SNAPSHOT_DIMENSION_FIELDS` completo (4 dimensões, 21 indicadores, 15 queries referência). TypedDicts e helpers. |
| `services/tool_pool_api/src/tool_pool_api/server/tool_modules/memory_module.py` | ✅ Pronto | `_SNAPSHOT_BASE_FIELDS`, `_SNAPSHOT_FRONTMATTER_REQUIRED`, `_VALID_DIMENSIONS`, `_VALID_PERIODS`. Funções `_validate_snapshot_frontmatter()` + `_validate_snapshot_body()`. |

### T2.4.2 — Criar função SQL `generate_onboarding_snapshots`

| Arquivo | Status | Descrição |
|---------|--------|-----------|
| `supabase/migrations/TBD_generate_onboarding_snapshots.sql` | ❌ Não existe | A criar. Função `analytics_v2.generate_onboarding_snapshots(p_client_id uuid)`. |
| `supabase/migrations/archive/20260430000000_baseline.sql` | ℹ️ Baseline | Define schema `analytics_v2` (L24) e tabela `reg_jobs` (L555). |

### T2.4.3 — Criar trigger pós-ETL em `reg_jobs`

| Arquivo | Status | Descrição |
|---------|--------|-----------|
| `supabase/migrations/TBD_onboarding_etl_hook.sql` | ❌ Não existe | A criar. Trigger `trg_onboarding_etl_complete` AFTER UPDATE em `analytics_v2.reg_jobs`. |
| `supabase/migrations/proposed/20260526100000_reg_jobs_running_watchdog.sql` | ℹ️ Existe | `reset_stuck_running_jobs()` — não conflita, mas trigger deve coexistir. |

### T2.4.4 — Adicionar RPCs faltantes para queries de referência

| Arquivo | Status | Descrição |
|---------|--------|-----------|
| `supabase/migrations/TBD_snapshot_reference_queries.sql` | ❌ Não existe | A criar. 15 RPCs listadas em `_SNAPSHOT_DIMENSION_FIELDS`. |
| **RPCs existentes** (verificação): | | |
| `get_cash_position` | ❌ Não encontrada | |
| `get_recent_transactions` | ❌ Não encontrada | |
| `get_aging_accounts` | ❌ Não encontrada | |
| `get_active_clients` | ❌ Não encontrada | |
| `get_churn_metrics` | ❌ Não encontrada | |
| `get_nps_scores` | ❌ Não encontrada | |
| `get_client_ltv` | ❌ Não encontrada | |
| `get_today_meetings` | ❌ Não encontrada | |
| `get_weekly_meetings` | ❌ Não encontrada | |
| `get_pending_followups` | ❌ Não encontrada | |
| `get_collection_contacts` | ❌ Não encontrada | |
| `get_open_purchase_orders` | ❌ Não encontrada | |
| `get_critical_stock` | ❌ Não encontrada | |
| `get_pending_suppliers` | ❌ Não encontrada | |
| `get_pending_approval_orders` | ❌ Não encontrada | |

### T2.4.5 — Teste de integração end-to-end

| Arquivo | Status | Descrição |
|---------|--------|-----------|
| `scripts/test_onboarding_snapshots.py` | ❌ Não existe | A criar. Teste: onboarding → CSV ETL → trigger → 4 snapshots. |

### T2.4.6 — Documentação e seed de snapshots

| Arquivo | Status | Descrição |
|---------|--------|-----------|
| `docs/llm_wiki/SHARED_MEMORY_DESIGN.md` | ✅ Existe (223L) | Documenta templates de snapshot (T2.2). **Sem seção sobre hook pós-ETL.** |
| `scripts/seed_onboarding_snapshots.py` | ❌ Não existe | A criar. Seed standalone para ambiente dev. |

## Documentação de Referência

| Arquivo | Relevância |
|---------|-----------|
| `docs/llm_wiki/SHARED_MEMORY_DESIGN.md` | Design completo dos snapshots: dimensões, indicadores, frontmatter, validação. |
| `docs/llm_wiki/ROUTINES_SYSTEM.md` | Catálogo de rotinas. `onboarding_complete` existe mas não gera snapshots. |
| `docs/llm_wiki/entities/context-gatherer.md` | Agente que processa onboarding. Acionado por webhook `onboarding_complete`. |
| `docs/llm_wiki/concepts/shared-memory.md` | Arquitetura da shared memory: tabelas, tipos de entidade, fluxo. |
| `supabase/migrations/proposed/20260526060000_unified_ingest_staging_and_apply.sql` | Pipeline ETL: `apply_staging_to_facts()` → enfileira `refresh_dashboards`. Ponto de inserção do hook. |

## Estrutura de Migrações — Propostas Relacionadas

```
supabase/migrations/proposed/
├── 20260526060000_unified_ingest_staging_and_apply.sql   # ETL apply → fato_transacoes
├── 20260526070000_etl_dispatcher_via_pg_net.sql          # Dispatcher original via pg_net
├── 20260526080000_etl_dispatcher_v2_vault.sql             # Dispatcher Rev3 via vault
├── 20260526100000_reg_jobs_running_watchdog.sql           # Reset stuck jobs
├── 20260527010000_csv_etl_tipo_transacao_inference.sql    # CSV ETL pipeline
├── 20260619000000_shared_business_memory.sql              # Tabela base de snapshots
├── 20260619000002_shared_memory_integrity.sql             # Validação de integridade
├── 20260619000003_snapshot_templates.sql                  # ⚠️ #22: +version, +snapshot
└── 20260619000003_routine_checkpoint_rpc.sql              # ⚠️ #21: +routine types (CONFLITO)
```
