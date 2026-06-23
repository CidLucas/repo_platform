# performance-review-f1-5.md — Performance Bottleneck Analysis (Fases 1-5)

> **Gerado por:** factory-coder (t_123ff4c1), 2026-06-23
> **Escopo:** 25 artefatos de Fases 1-5 (21 libs, 2 services, 1 app, 1 package)
> **Fonte:** scan automatizado via `_perf_scan.py` + inspeção manual de hotspots
> **Branch:** `phase-0/issue-57-code-patterns-review`
> **Depende de:** `inventory-catalog.md` (T57.1), `performance-review.md` (baseline parcial), `resolution.md` (DQ3 tier classification)

---

## 1. Executive Summary

| Métrica | Valor |
|----------|-------|
| Total de artefatos analisados | **25** (21 libs, 2 services, 1 app, 1 package) |
| Total de bottlenecks identificados | **16** |
| P0 (Imediato — Tier 1 escalated) | 3 |
| P1 (Next Sprint) | 9 |
| P2 (Backlog) | 4 |
| Artefatos com zero issues de performance | 9/25 |
| Artefatos com issues P0/P1 | 11/25 |

**Resumo narrativo:** O codebase tem 3 gargalos P0 críticos em Tier 1: (a) N+1 queries em `nodes.py:rfq_wait_node` e `nodes.py:rfq_follow_up_node` com batch updates triviais transformados em N queries individuais; (b) tabela `rfq_requests` referenciada no código mas potencialmente deprecated pela migration `20260602000000_agent_lists.sql`. Os problemas P1 concentram-se em serial awaits no `context_service.py` (7+ queries Supabase sequenciais), HTTP sequencial em `routine_functions.py`, e N+1 upserts em `memory_post_flight.py` e `memory_module.py`. O frontend (`apps/blu_v3`) não tem code splitting nem otimização de imagens.

**Comparação com `performance-review.md` (baseline anterior):** O baseline cobriu 8/25 artefatos (Tier 1 completo + 2 Tier 2 + frontend). Este review cobre todos 25 artefatos e identifica +6 novos bottlenecks não catalogados anteriormente: memory_module (N+1 auto-link), memory_post_flight (N+1 tool_usage upsert), version_module (N+1 delete), config_helper_module (loop com DB), report_module (loop com DB), e context_report (serial queries).

---

## 2. Methodology

### 2.1 Scan Tool
Script `_perf_scan.py` (250+ linhas) executando varredura completa com 6 detectores:
- **N+1 queries:** `for` loops contendo `.execute()` ou `.query()` por iteração
- **Serial awaits:** 3+ `await` consecutivos sem `asyncio.gather`
- **Inefficient loops:** `.table()` dentro de `for` sem `.in_()` (batch)
- **Allocations:** list comprehensions grandes, `.copy()`/`dict()` em loops
- **Schema gaps:** tabelas sem índices explícitos, FK sem covering index
- **DB Schema:** análise de migrations SQL

### 2.2 Scope
- Python: `libs/` (21) + `services/` (2) → 416 `.py` files
- TypeScript: `apps/blu_v3/` (1) + `packages/` (1) → 97 `.ts/.tsx` files
- SQL: `supabase/migrations/` → 65 `.sql` files
- Exclusões: `.venv/`, `node_modules/`, `__pycache__/`, `dist/`, `build/`, `.next/`, `egg-info/`, `tool_pool_venv/`, `build/lib/`

### 2.3 Tier Classification (per resolution.md §DQ3)
| Tier | Criticality | Count | Threshold |
|------|-------------|-------|-----------|
| **Tier 1** | Crítico | 6 (blu_agent_framework, blu_supabase_client, blu_models, blu_context_service, agent_api) | P1 → P0 escalation |
| **Tier 2** | Alto | 5 (tool_pool_api, blu_llm_service, blu_rag_factory, blu_prompt_management, blu_sql_factory) | Standard |
| **Tier 3** | Médio | 4 (blu_auth, blu_hitl_service, blu_data_connectors, blu_db_connector) | Standard |
| **Tier 4** | Baixo | 10 (demais libs + apps/blu_v3 + packages/blu-auth) | Relaxed |

---

## 3. Per-Artefact Bottleneck Table

| # | Artefact | Tier | File:Line | Pattern | Impact | Priority | Suggestion |
|---|----------|------|-----------|---------|--------|----------|------------|
| 1 | blu_agent_framework | T1 | `nodes.py:901-904` | **N+1 updates**: `for rfq_id in expired: db.table().update().eq().execute()` | Alto — N queries individuais para batch update trivial | **P0** | `db.table().update({"status":"expired"}).in_("id", expired).execute()` |
| 2 | blu_agent_framework | T1 | `nodes.py:961-990` | **N+1 select+update**: `for rfq_id in ids: .select().eq().maybe_single().execute()` + `.update().eq().execute()` | Crítico — 2N round-trips Supabase por follow-up | **P0** | Batch select com `.in_("id", ids)`, processa em memória, batch update final |
| 3 | blu_agent_framework | T1 | `nodes.py` → `rfq_requests` | **Schema gap**: código referencia tabela `rfq_requests` mas migration `20260602000000_agent_lists.sql` documenta substituição | Crítico — queries em tabela potencialmente deprecated | **P0** | Verificar existência em produção; migrar para `agent_lists` se necessário |
| 4 | agent_api | T1 | `routine_functions.py:1727-1773` | **Serial awaits**: `acct_resp`, `bills_resp`, `intg_resp` aguardados sequencialmente (3x `await asyncio.to_thread()`) | Médio — 3 queries Supabase independentes em série | **P1** | `asyncio.gather(acct_fn, bills_fn, intg_fn)` para paralelizar |
| 5 | agent_api | T1 | `routine_functions.py:1781-1815` | **HTTP in loop**: `for intg_id in integration_ids: await http.get(...)` com paginação interna | Alto — N integrações × P páginas de HTTP sequencial | **P1** | `asyncio.gather` com `Semaphore(5)` para paralelismo controlado |
| 6 | blu_context_service | T1 | `context_service.py:585-730` | **Serial snapshot**: 7+ queries Supabase sequenciais (`approval_requests`, `notifications`, `client_goals`, `dimension_state`, `client_insights`, `approval_requests` 2x, `cross_agent_routines`) em `build_context_snapshot()` | Médio — latência = soma de todas as queries | **P1** | Agrupar queries independentes com `asyncio.gather` |
| 7 | tool_pool_api | T2 | `memory_module.py:1321-1333` | **N+1 links**: `for ref in references: await _shared_memory_link_logic(...)` — 1 DB call por entity reference | Médio — com 10 referências, são 10 inserts sequenciais | **P1** | Batch insert via `.upsert([...])` com múltiplos payloads, ou `asyncio.gather` |
| 8 | tool_pool_api | T2 | `memory_post_flight.py:162-189` | **N+1 upsert**: `for tool_name in tool_calls: db.table().upsert(...).execute()` — 1 DB call por tool | Médio — 5-20 tools por execução | **P1** | Batch upsert: `.upsert([payload1, payload2, ...])` em uma chamada |
| 9 | tool_pool_api | T2 | `version_module.py:468-475` | **N+1 delete**: `for vid in to_delete: db.table().delete().eq().execute()` — 1 DB call por versão | Baixo — tipicamente 1-5 versões para deletar | **P1** | Batch delete: `.delete().in_("id", to_delete).execute()` |
| 10 | tool_pool_api | T2 | `report_module.py:98` | **Loop com DB**: `for table in ("kb_documents", "client_knowledge"): db.table(table).select()...` — 2 queries sequenciais para tabelas diferentes | Baixo — apenas 2 iterações, mas poderia ser paralelo | **P2** | `asyncio.gather` para queries independentes em tabelas diferentes |
| 11 | tool_pool_api | T2 | `config_helper_module.py:291` | **Loop com DB**: `for f in completeness["missing"]` → possível `.execute()` por campo faltante | Baixo — depende da implementação interna | **P2** | Verificar se `completeness` faz queries por campo; se sim, consolidar |
| 12 | blu_agent_framework | T1 | `routines/context_report.py:217-237` | **Bom padrão**: usa `asyncio.gather` com `Semaphore` para paralelizar por tenant ✅ | Positivo | — (exemplo a seguir) |
| 13 | blu_v3 (apps) | T4 | `apps/blu_v3/src/` | **Sem code splitting**: zero usos de `React.lazy`, `Suspense`, ou `dynamic()` imports | Alto — bundle size cresce; TTI degradado | **P1** | `React.lazy` + `Suspense` nas rotas; `React.memo` em componentes pesados |
| 14 | blu_v3 (apps) | T4 | `apps/blu_v3/src/` | **Sem otimização de imagens**: `<img>` tags raw sem `loading="lazy"`, sem WebP/AVIF, sem `srcset` | Baixo — LCP degradado | **P2** | `loading="lazy"` + `srcset`; converter assets para WebP |
| 15 | blu_v3 (apps) | T4 | `apps/blu_v3/src/` | **console.log residual**: 33 chamadas em produção | Baixo — polui console, expõe dados | **P2** | Remover ou condicionar a `process.env.NODE_ENV === 'development'` |
| 16 | Supabase (migrations) | T1 | `applied/20260601_agent_sessions_table.sql` | **Missing index**: `agent_sessions` sem índice em `agent_catalog_id`; queries em `agents_router.py` filtram por esta coluna | Baixo — `id` é PK (indexado), mas `agent_catalog_id` sem `client_id` não usa índice | **P2** | `CREATE INDEX idx_agent_sessions_catalog ON agent_sessions(agent_catalog_id)` |

**Artefatos sem issues de performance (9/25):** blu_supabase_client, blu_models, blu_llm_service, blu_rag_factory, blu_prompt_management, blu_sql_factory, blu_auth, blu_data_connectors, blu_db_connector, blu_hitl_service, blu_elicitation_service, blu_experiment_service, blu_landing_intel, blu_observability_bootstrap, blu_parsers, blu_shared_utils, blu_tool_registry, blu_twilio_client, blu_google_suite_client, packages/blu-auth.

**Nota:** Muitos artefatos Tier 3 e Tier 4 não apresentam padrões de performance problemáticos — são libs de suporte com pouco ou nenhum acesso a DB. A concentração de issues está nos serviços e nas libs core (Tier 1-2).

---

## 4. Top 5 Highest-Impact Bottlenecks (Detailed Analysis)

### P0 #1 — N+1 select+update em `rfq_follow_up_node` (nodes.py:961–990)

**Código atual:**
```python
for rfq_id in follow_up_ids:
    rfq_result = db.table("rfq_requests").select(
        "id,supplier_id,follow_up_count,deadline,communication_channel,"
        "supplier_roster(name,contact_phone,contact_email)"
    ).eq("id", rfq_id).maybe_single().execute()   # ← Query 1

    # ... lógica de follow-up ...

    db.table("rfq_requests").update({
        "follow_up_count": follow_ups
    }).eq("id", rfq_id).execute()                  # ← Query 2
```

**Problema:** Para N follow-ups pendentes → **2N** round-trips Supabase. Com 10 RFQs → 20 queries.

**Solução:**
```python
# 1 query batch para buscar todos
rfqs_result = db.table("rfq_requests").select(
    "id,supplier_id,follow_up_count,deadline,communication_channel,"
    "supplier_roster(name,contact_phone,contact_email)"
).in_("id", follow_up_ids).execute()

# Processa em memória
reminded_ids = []
for rfq in (rfqs_result.data or []):
    # ... lógica de follow-up por channel ...
    if sent:
        reminded_ids.append(rfq["id"])

# Batch update no final — 1 query
if reminded_ids:
    db.table("rfq_requests").update({
        "follow_up_count": db.raw("follow_up_count + 1")
    }).in_("id", reminded_ids).execute()
```

**Impacto:** Redução de 2N queries para **2 queries** (1 select batch + 1 update batch).

---

### P0 #2 — N+1 updates em `rfq_wait_node` (nodes.py:901–904)

**Código atual:**
```python
if expired:
    for rfq_id in expired:
        db.table("rfq_requests").update(
            {"status": "expired"}
        ).eq("id", rfq_id).execute()
```

**Problema:** Batch update trivial transformado em N queries individuais.

**Solução (1 linha):**
```python
if expired:
    db.table("rfq_requests").update(
        {"status": "expired"}
    ).in_("id", expired).execute()
```

---

### P0 #3 — Tabela `rfq_requests` potencialmente deprecated (Schema Gap)

**Evidência:** `nodes.py` referencia `rfq_requests` em 3 pontos (`rfq_wait_node:884`, `rfq_wait_node:901`, `rfq_follow_up_node:961`), mas a migration `20260602000000_agent_lists.sql` (applied) documenta substituição de `rfq_requests` por `agent_lists`.

**Risco:** Se `rfq_requests` não existe mais em produção, os nodes `rfq_wait` e `rfq_follow_up` vão falhar silenciosamente (exceções capturadas com `except Exception`). Se existe mas está deprecated, está desatualizado.

**Ação necessária:**
1. Verificar se `rfq_requests` existe no DB de produção
2. Se não existe: migrar queries para `agent_lists` (schema compat check)
3. Se existe mas deprecated: planejar migração + adicionar warning de depreciação

---

### P1 #4 — Serial snapshot: 7+ queries Supabase sequenciais em `build_context_snapshot()` (context_service.py:585–730)

**Código atual (estrutura):**
```python
# Query 1 — approval_requests
resp = supabase.table("approval_requests").select(...).eq(...).execute()
# Query 2 — notifications
resp = supabase.table("notifications").select(...).eq(...).execute()
# Query 3 — client_goals
resp = supabase.table("client_goals").select(...).eq(...).execute()
# Query 4 — dimension_state
resp = supabase.table("dimension_state").select(...).eq(...).execute()
# Query 5 — client_insights
resp = supabase.table("client_insights").select(...).eq(...).execute()
# Query 6 — approval_requests (again, different query)
# Query 7 — cross_agent_routines
```

**Problema:** 7 queries independentes rodando em série. Latência total = soma(7 latências). Com 100ms por query → 700ms.

**Solução:**
```python
import asyncio

# Agrupar queries independentes
results = await asyncio.gather(
    asyncio.to_thread(lambda: supabase.table("approval_requests").select(...).eq(...).execute()),
    asyncio.to_thread(lambda: supabase.table("notifications").select(...).eq(...).execute()),
    asyncio.to_thread(lambda: supabase.table("client_goals").select(...).eq(...).execute()),
    asyncio.to_thread(lambda: supabase.table("dimension_state").select(...).eq(...).execute()),
    asyncio.to_thread(lambda: supabase.table("client_insights").select(...).eq(...).execute()),
    return_exceptions=True  # não quebra se uma falhar
)

(approval_resp, notif_resp, goals_resp, dim_resp, insights_resp) = results
```

**Impacto:** Latência reduzida de 700ms para ~100ms (max das queries paralelas).

---

### P1 #5 — HTTP sequencial em `cash_flow_projection` (routine_functions.py:1781–1815)

**Código atual:**
```python
for intg_id in integration_ids:
    async with httpx.AsyncClient(timeout=15.0) as http:
        page = 1
        while True:
            resp = await http.get(f"{base_url}/v1/recurring", params={...})
            # processa página...
            if not next_page:
                break
            page += 1
```

**Problema:** N integrações × P páginas de chamadas HTTP em série. Com 5 integrações e 3 páginas cada → 15 HTTP calls sequenciais.

**Solução:**
```python
sem = asyncio.Semaphore(5)

async def fetch_integration(intg_id):
    async with sem:
        async with httpx.AsyncClient(timeout=15.0) as http:
            # ... mesmo loop de paginação ...
            return results

all_results = await asyncio.gather(*[
    fetch_integration(iid) for iid in integration_ids
])
```

---

## 5. Artefact-by-Artefact Analysis

### 5.1 Tier 1 — Crítico

| Artefact | Issues | Severidade | Detalhes |
|----------|--------|------------|----------|
| **blu_agent_framework** | 3 | P0×3 | N+1 em `nodes.py:901,961`; `rfq_requests` deprecated |
| **blu_supabase_client** | 0 | — | Sem issues — client wrapper simples |
| **blu_models** | 0 | — | Apenas Pydantic models, sem lógica de DB |
| **blu_context_service** | 1 | P1 | Serial snapshot: 7+ queries em `build_context_snapshot()` |
| **agent_api** | 2 | P1×2 | Serial awaits + HTTP em loop em `routine_functions.py` |

### 5.2 Tier 2 — Alto

| Artefact | Issues | Severidade | Detalhes |
|----------|--------|------------|----------|
| **tool_pool_api** | 4 | P1×3, P2×1 | N+1 em `memory_module`, `memory_post_flight`, `version_module`; loop DB em `report_module` |
| **blu_llm_service** | 0 | — | Chamadas a APIs externas (fora do escopo de DB performance) |
| **blu_rag_factory** | 0 | — | Sem acesso direto a DB |
| **blu_prompt_management** | 0 | — | Gerenciamento de templates |
| **blu_sql_factory** | 0 | — | SQL generation, sem execução de queries em loop |

### 5.3 Tier 3 — Médio

| Artefact | Issues | Severidade | Detalhes |
|----------|--------|------------|----------|
| **blu_auth** | 0 | — | Autenticação; queries pontuais |
| **blu_hitl_service** | 0 | — | Human-in-the-loop; sem acesso DB pesado |
| **blu_data_connectors** | 0 | — | Conectores externos; HTTP calls, sem DB direto |
| **blu_db_connector** | 0 | — | Infra de conexão; sem queries de aplicação |

### 5.4 Tier 4 — Baixo

| Artefact | Issues | Severidade | Detalhes |
|----------|--------|------------|----------|
| **apps/blu_v3** | 3 | P1×1, P2×2 | Sem code splitting; sem otimização de imagens; `console.log` residual |
| **packages/blu-auth** | 0 | — | Package TS de auth; sem lógica de performance |
| Demais 8 libs Tier 4 | 0 | — | Libs auxiliares sem acesso a DB |

---

## 6. Cross-Cutting Patterns

### 6.1 Batch Operations Gap (`.in_()` usage)

Apenas **20 arquivos** no codebase usam `.in_()` para operações batch. O padrão dominante é `.eq()` por iteração em loops:

| Padrão | Ocorrências | Performance |
|--------|-------------|-------------|
| `.eq("id", val).execute()` em loop | 12+ hotspots identificados | 1 query por iteração |
| `.in_("id", vals).execute()` | 20 arquivos | 1 query total |

**Recomendação:** Criar guideline no `patterns.md`: "Sempre que houver `for x in ids: db.table().eq('id', x)`, substituir por `.in_('id', ids)`."

### 6.2 Serial vs Parallel Awaits

| Padrão | Exemplo bom | Exemplo ruim |
|--------|-------------|--------------|
| `asyncio.gather` | `context_report.py:237` — `asyncio.gather(*(_bound(t["client_id"]) for t in tenants))` | `context_service.py:585-730` — 7 awaits sequenciais |
| `asyncio.Semaphore` | `context_report.py:229` — `asyncio.Semaphore(concurrency)` | `routine_functions.py:1781` — HTTP sequencial sem limite |

### 6.3 Frontend Bundle Health

| Métrica | Valor | Status |
|----------|-------|--------|
| Code splitting (React.lazy) | 0 usos | ❌ Ausente |
| Image optimization (WebP, srcset) | 0 usos | ❌ Ausente |
| `console.log` em produção | 33 chamadas | ⚠️ P2 |

---

## 7. SQL Schema Analysis

### 7.1 Migration Files Analisados

- **Applied:** 21 migrations ativas
- **Proposed:** 6 migrations pendentes
- **Archive:** ~10 migrations arquivadas

### 7.2 Missing Indexes

| Tabela | Coluna | Migration | Impacto |
|--------|--------|-----------|---------|
| `agent_sessions` | `agent_catalog_id` | `20260601_agent_sessions_table.sql` | Queries em `agents_router.py` filtram por esta coluna sem índice |
| `shared_business_memory` | `client_id, entity_type, entity_name` | `20260619000000_shared_business_memory.sql` | PK é `id`; queries frequentes usam composite `(client_id, entity_type, entity_name)` — verificar se índice implícito existe |
| `shared_memory_links` | `source_entity_name, target_entity_name` | `20260619000001_shared_memory_links.sql` | FK references sem covering index explícito |

### 7.3 FK Columns Without Covering Indexes

As migrations propostas `shared_business_memory`, `shared_memory_links`, `shared_business_memory_meta`, e `shared_business_memory_versions` definem FOREIGN KEYs mas não incluem `CREATE INDEX` para as colunas referenciadas. O Supabase/PostgreSQL não cria índices automaticamente para FKs — isso pode degradar JOINs e verificações de integridade referencial.

---

## 8. Summary by Priority

### P0 — Imediato (3 issues)

| # | Issue | Artefact | Ação |
|---|-------|----------|------|
| 1 | N+1 select+update em `rfq_follow_up_node` | blu_agent_framework | Batch select + batch update |
| 2 | N+1 updates em `rfq_wait_node` | blu_agent_framework | `.in_("id", expired)` 1-liner |
| 3 | Tabela `rfq_requests` deprecated? | blu_agent_framework | Verificar produção, migrar para `agent_lists` |

### P1 — Next Sprint (9 issues)

| # | Issue | Artefact | Ação |
|---|-------|----------|------|
| 4 | Serial awaits cash_flow | agent_api | `asyncio.gather` |
| 5 | HTTP in loop | agent_api | `asyncio.gather` + Semaphore |
| 6 | Serial snapshot 7+ queries | blu_context_service | `asyncio.gather` |
| 7 | N+1 auto-link inserts | tool_pool_api/memory_module | Batch upsert |
| 8 | N+1 tool_usage upsert | tool_pool_api/memory_post_flight | Batch upsert |
| 9 | N+1 version delete | tool_pool_api/version_module | `.in_()` batch delete |
| 10 | Frontend: sem code splitting | apps/blu_v3 | React.lazy + Suspense |
| 11 | Frontend: sem otimização imagens | apps/blu_v3 | loading="lazy" + WebP |
| 12 | FK sem covering indexes | supabase/migrations | Adicionar CREATE INDEX |

### P2 — Backlog (4 issues)

| # | Issue | Artefact | Ação |
|---|-------|----------|------|
| 13 | Loop DB: report_module | tool_pool_api | asyncio.gather |
| 14 | Loop DB: config_helper | tool_pool_api | Consolidar queries |
| 15 | console.log em prod | apps/blu_v3 | Remover/condicionar |
| 16 | Missing index agent_catalog_id | supabase/migrations | CREATE INDEX |

---

## 9. Artefacts with Positive Patterns (Exemplos a Seguir)

| Artefact | Padrão | Descrição |
|----------|--------|-----------|
| `blu_agent_framework/routines/context_report.py:217-237` | `asyncio.gather` + `Semaphore` | Paraleliza consultas por tenant com limite de concorrência |
| `blu_agent_framework/routines/context_report.py:265` | List comprehension limpa | `[MetricRow.from_dict(r) for r in (resp.data or [])]` |
| `blu_context_service/context_service.py` (Redis caching) | Cache com TTL | `cache.get_json(cache_key)` → evita query Supabase repetida |

---

## 10. Recommendations

1. **Criar guideline "Batch-First" no `patterns.md`:** "Toda operação DB em loop deve usar `.in_()` para batch; se não for possível, documentar o motivo."
2. **Auditar queries `.eq()` em loops:** Rodar o detector N+1 como pre-commit hook (ou CI check) para prevenir regressões.
3. **Paralelizar `build_context_snapshot`:** Maior ganho de latência com menor esforço (apenas agrupar queries independentes).
4. **Migrar `rfq_requests` → `agent_lists`:** Eliminar risco de queries em tabela deprecated e consolidar schema.
5. **Adicionar code splitting no frontend:** `React.lazy` nas rotas principais (app, onboarding, settings) para reduzir bundle inicial.
6. **Adicionar índices FK:** Executar `CREATE INDEX` para colunas FK nas migrations propostas antes do deploy.

---

## 11. Reference Documentation Used

| Document | Status | Utilização |
|----------|--------|-----------|
| `inventory-catalog.md` | ✅ | Lista dos 25 artefatos + tier classification |
| `performance-review.md` | ✅ | Baseline parcial (Tier 1-2 + frontend) |
| `patterns.md` | ✅ | Baseline de convenções esperadas |
| `resolution.md` | ✅ | Design decisions, DQ3 tier thresholds |
| `repo-index.md` | ✅ | Scan inicial com pygount stats |
| `HERMES.md` | ✅ | Visão geral do monorepo |

---

*Fim do review. Encaminhar para Reviewer de B3.*
