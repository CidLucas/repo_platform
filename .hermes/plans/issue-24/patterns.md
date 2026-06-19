# Patterns — Issue #24: Hook pós-ETL Onboarding Snapshot

> Branch: `phase-2/issue-24-post-etl-onboarding-snapshot`
> Gerado: 2026-06-19

## P1: Padrão de Migração com CHECK Constraint Destrutivo

**Localização:** `supabase/migrations/proposed/20260619000003_*.sql` (2 arquivos com mesmo timestamp)

**Problema:** Duas migrações independentes (#22 e #21) modificam o mesmo CHECK constraint `shared_business_memory_entity_type_check` via DROP + recriação. Cada uma adiciona seus próprios tipos sem conhecimento da outra:

```sql
-- snapshot_templates.sql (#22):
CHECK (entity_type IN (
    'skill', 'client', 'contact', 'supplier', 'user', 'snapshot'
))

-- routine_checkpoint_rpc.sql (#21):
CHECK (entity_type IN (
    'skill', 'client', 'contact', 'supplier', 'user',
    'agent_result', 'agent_metadata', 'routine'
))
```

**Consequência:** A ordem de aplicação determina qual conjunto sobrevive. A segunda migração destrói os tipos da primeira.

**Resolução (resolution.md):** Merge manual em migração unificada ou aplicar snapshot primeiro, depois checkpoint com UNION dos tipos.

---

## P2: Padrão de Trigger AFTER UPDATE para Hook de Pipeline

**Localização:** `supabase/migrations/proposed/20260526100000_reg_jobs_running_watchdog.sql`

**Padrão existente:** Watchdog usa função SQL + pg_cron para monitorar `reg_jobs.status`:
```sql
CREATE OR REPLACE FUNCTION analytics_v2.reset_stuck_running_jobs()
RETURNS void AS $$
  UPDATE analytics_v2.reg_jobs
  SET status = 'pending', error_message = 'reset by watchdog: stuck in running > 3min'
  WHERE status = 'running' AND updated_at < NOW() - INTERVAL '3 minutes';
$$ LANGUAGE sql;
```

**Padrão para T2.4.3:** Trigger deve seguir convenção de nomenclatura `trg_*` e usar `AFTER UPDATE ... FOR EACH ROW WHEN (OLD.status <> 'completed' AND NEW.status = 'completed')`. Deve ser idempotente (verificar existência prévia de snapshots para o client_id).

---

## P3: Padrão de RPCs de Referência (Query Functions)

**Localização:** `_SNAPSHOT_DIMENSION_FIELDS` em `libs/blu_context_service/src/blu_context_service/context_schemas.py`

**Padrão:** Cada dimensão declara queries de referência como strings. Exemplo:
```python
financeiro_queries = [
    "get_cash_position",
    "get_recent_transactions",
    "get_aging_accounts",
]
```

**Gap:** Nenhuma das 15 queries referenciadas existe como RPC/Função SQL. O padrão implica que devem ser funções `analytics_v2.*` que aceitam `p_client_id uuid` e retornam JSONB ou SETOF registros.

**Convenção esperada:** `analytics_v2.get_*(p_client_id uuid, p_days integer DEFAULT 30) RETURNS jsonb`

---

## P4: Padrão de Snapshot em shared_business_memory

**Localização:** `docs/llm_wiki/SHARED_MEMORY_DESIGN.md`, `memory_module.py`

**Padrão estabelecido:**
- `entity_type = 'snapshot'`
- `entity_name = '{dimensao}:{periodo}'` (ex: `financeiro:semanal`)
- `key = ISO timestamp` (ex: `2026-06-19T00:00:00Z`)
- `value = {body: {...}, frontmatter: {...}}`

**Body:**
```json
{
  "snapshot_id": "uuid",
  "dimensao": "financeiro",
  "periodo": "semanal",
  "gerado_em": "2026-06-19T12:00:00Z",
  "vigencia_inicio": "2026-06-12T00:00:00Z",
  "vigencia_fim": "2026-06-19T00:00:00Z",
  "indicadores": {...},
  "alertas": [...],
  "resumo_executivo": "..."
}
```

**Frontmatter:**
```json
{
  "tipo": "snapshot",
  "dimensao": "financeiro",
  "periodo": "semanal",
  "gerado_em": "2026-06-19T12:00:00Z",
  "gerado_por": "onboarding_etl_hook",
  "versao": 1,
  "template_version": 1,
  "fontes": ["fato_transacoes", "dim_clientes"],
  "confianca": 0.85
}
```

---

## P5: Padrão de Pipeline ETL — Ponto de Inserção do Hook

**Localização:** `supabase/migrations/proposed/20260526060000_unified_ingest_staging_and_apply.sql`

**Fluxo atual:**
```
reg_jobs.status = 'pending'
  → ETL dispatcher (process_pending_jobs / sincronizar_csv_cliente)
  → reg_jobs.status = 'running'
  → ingest_staging (CSV/BigQuery → staging tables)
  → apply_staging_to_facts (staging → fato_transacoes + dim_*)
  → reg_jobs.status = 'completed'
  → enqueue refresh_dashboards
```

**Ponto de inserção do hook (T2.4.3):** Trigger AFTER UPDATE em `reg_jobs` detecta `status → 'completed'` pela primeira vez para o client_id. Alternativa: adicionar passo explícito em `apply_staging_to_facts()` antes do `refresh_dashboards`.

**Design decision DD1:** Trigger (mais desacoplado, não modifica pipeline ETL existente).

---

## P6: Padrão de Onboarding Routine (sem snapshots atualmente)

**Localização:** `supabase/migrations/applied/20260603_onboarding_complete_routine_and_context_gaps.sql`

**Passos atuais da rotina `onboarding_complete`:**
1. `build_context(p_client_id)` — constrói contexto do onboarding
2. `save_context_map(p_client_id)` — salva context_map.md
3. `upsert_clientes_blu_context(p_client_id)` — upsert no contexto
4. `upsert_client_goals(p_client_id)` — upsert de metas
5. `init_home_state(p_client_id)` — inicializa home state

**Gap:** Nenhum passo gera snapshots. O hook pós-ETL (T2.4) é independente desta rotina — opera após ingest de dados transacionais, não após onboarding de perfil.

---

## P7: Padrão de Validação de Snapshot

**Localização:** `services/tool_pool_api/src/tool_pool_api/server/tool_modules/memory_module.py`

**Funções existentes:**
- `_validate_snapshot_frontmatter(frontmatter: dict) → bool` — valida campos obrigatórios
- `_validate_snapshot_body(body: dict) → bool` — valida indicadores por dimensão

**Reuso em T2.4:** A função `generate_onboarding_snapshots` deve gerar body + frontmatter compatíveis com estas validações. Os testes (T2.4.5) devem verificar que `_validate_snapshot_frontmatter` e `_validate_snapshot_body` passam para os snapshots gerados.

---

## P8: Padrão de Idempotência

**Localização:** Design decision DD2, risco R2

**Mecanismo:** `INSERT ... ON CONFLICT (client_id, entity_type, entity_name, key) DO UPDATE` garante idempotência na escrita de snapshots.

**Trigger-level:** Verificar existência prévia antes de disparar:
```sql
IF EXISTS (
  SELECT 1 FROM public.shared_business_memory
  WHERE client_id = NEW.client_id AND entity_type = 'snapshot'
) THEN
  RETURN NEW; -- já processado, skip
END IF;
```
