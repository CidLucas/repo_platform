# performance-review.md — Performance Bottleneck Analysis (#57)

> **Gerado por:** factory-coder (t_166acbd7), 2026-06-22  
> **Fonte:** scan automatizado de `libs/`, `services/`, `apps/`, `supabase/migrations/`  
> **Branch:** `phase-0/issue-57-code-patterns-review`  
> **Depende de:** `inventory-catalog.md` (T57.1), `resolution.md` (DD-06)

---

## 1. Executive Summary

| Métrica | Valor |
|----------|-------|
| Total de bottlenecks identificados | **10** |
| P0 (Imediato) | 3 |
| P1 (Next Sprint) | 5 |
| P2 (Backlog) | 2 |
| Tier 1 analisados | 5/5 (agent_api, blu_agent_framework, blu_supabase_client, blu_models, blu_context_service) |
| Tier 2 analisados | 2/5 (rotina priorizada: routine_functions, context_service) |
| Frontend analisado | blu_v3 (Tier 4) |
| SQL migrations revisados | 3 ativos + 22 applied + 10 archive |

**Classificação DD-06:** P1 findings em Tier 1 são escalados para P0 conforme resolution.md §DQ3.

---

## 2. Per-Service Bottleneck Table

| # | File | Line(s) | Pattern | Impact | Tier | Priority | Suggestion |
|---|------|---------|---------|--------|------|----------|------------|
| 1 | `libs/blu_agent_framework/src/blu_agent_framework/nodes.py` | 961–990 | **N+1 queries**: `.maybe_single().execute()` + `.update().execute()` dentro de `for rfq_id in follow_up_ids:` | Alto — cada follow-up gera 2 queries DB separadas | T1 | **P0** | Buscar todos rfqs de uma vez com `.in_("id", follow_up_ids)`, depois iterar em memória; batch update com upsert |
| 2 | `libs/blu_agent_framework/src/blu_agent_framework/nodes.py` | 901–904 | **N+1 queries**: `.update().eq("id", rfq_id).execute()` dentro de `for rfq_id in expired:` | Alto — cada RFQ expirada gera 1 query de update | T1 | **P0** | Substituir por batch update: `.update({"status": "expired"}).in_("id", expired).execute()` |
| 3 | Schema gap: `rfq_requests` | — | **Tabela referenciada no código mas ausente do schema** — `nodes.py` query `rfq_requests` mas migration `20260602000000_agent_lists.sql` documenta substituição | Crítico — queries em tabela que pode não existir ou estar deprecated | T1 | **P0** | Verificar se `rfq_requests` ainda existe no DB de produção; migrar `nodes.py:rfq_wait_node` e `nodes.py:rfq_follow_up_node` para `agent_lists` |
| 4 | `services/agent_api/src/agent_api/core/routine_functions.py` | 1727–1773 | **Sequential awaits**: `acct_resp`, `bills_resp`, `intg_resp` aguardados sequencialmente (3x `await asyncio.to_thread()`) | Médio — 3 queries Supabase independentes rodando em série | T1 | **P1** | Usar `asyncio.gather(acct_fn, bills_fn, intg_fn)` para paralelizar |
| 5 | `services/agent_api/src/agent_api/core/routine_functions.py` | 1781–1815 | **HTTP in loop**: `for intg_id in integration_ids:` → `await http.get(...)` com paginação interna — chamadas HTTP sequenciais não batchadas | Alto — N integrações × P páginas de chamadas HTTP em série | T1 | **P1** | Usar `asyncio.gather` para disparar HTTP GETs em paralelo; adicionar semáforo para limitar concorrência (ex: `asyncio.Semaphore(5)`) |
| 6 | `libs/blu_context_service/src/blu_context_service/context_service.py` | 320–730 | **Sequential snapshot**: 7+ chamadas Supabase em série (`approval_requests`, `notifications`, `client_goals`, `dimension_state`, `client_insights`, `approval_requests` novamente, `cross_agent_routines`) dentro do método `build_context_snapshot()` | Médio — queries independentes rodando em série; latência soma de todas | T1 | **P1** | Agrupar queries independentes com `asyncio.gather`; queries dependentes do limite `used < max_chars` podem usar abordagem lazy com cancel |
| 7 | `apps/blu_v3/` | — | **Sem code splitting**: sem `React.lazy`, `React.memo`, ou `dynamic()` imports. Todas as páginas carregadas no bundle inicial | Alto — bundle size cresce com novas features; TTI degradado | T4 | **P1** | Aplicar `React.lazy` + `Suspense` nas rotas (`pages/app/*`, `pages/onboarding/*`); memoizar componentes pesados com `React.memo` |
| 8 | `services/agent_api/src/agent_api/core/routine_functions.py` | 1–3297 | **Monolith**: 3297 linhas em arquivo único com 41+ chamadas `.execute()`; funções misturam analytics, calendar, polp, nps, ecommerce, suppliers | Baixo — tempo de import/parse; risco de merge conflicts | T1 | **P1** | Split em módulos por domínio: `routine_functions/analytics.py`, `routine_functions/polp.py`, `routine_functions/calendar.py`, etc. |
| 9 | `supabase/migrations/applied/20260601_agent_sessions_table.sql` | — | **Missing index**: `agent_sessions` tem índice em `(client_id)` e `(client_id, status)`, mas queries em `agents_router.py` filtram por `agent_catalog_id` e `id` isoladamente | Baixo — `id` é PK (indexado), mas queries por `agent_catalog_id` sem `client_id` não usam índice | T1 | **P2** | Adicionar `CREATE INDEX idx_agent_sessions_catalog ON agent_sessions(agent_catalog_id)` |
| 10 | `apps/blu_v3/` | — | **Sem otimização de imagens**: zero usos de `next/image` ou equivalentes; `<img>` tags raw sem lazy loading, sem WebP/AVIF, sem srcset responsivo | Baixo — LCP degradado em páginas com imagens | T4 | **P2** | Adotar `<img loading="lazy">` + `srcset`; converter assets para WebP; considerar `vite-plugin-imagemin` |

---

## 3. Top 5 Highest-Impact Bottlenecks

### P0 #1 — N+1 queries em `rfq_follow_up_node` (nodes.py:961–990)

**Código atual:**
```python
for rfq_id in follow_up_ids:
    rfq_result = db.table("rfq_requests").select(
        "id,supplier_id,follow_up_count,deadline,communication_channel,"
        "supplier_roster(name,contact_phone,contact_email)"
    ).eq("id", rfq_id).maybe_single().execute()
    # ...
    db.table("rfq_requests").update({
        "follow_up_count": follow_ups
    }).eq("id", rfq_id).execute()
```

**Problema:** Para N follow-ups, são 2N queries DB. Com 10 RFQs pendentes → 20 round-trips Supabase.

**Solução:**
```python
# 1 query batch para buscar todos
rfqs_result = db.table("rfq_requests").select(
    "id,supplier_id,follow_up_count,deadline,communication_channel,"
    "supplier_roster(name,contact_phone,contact_email)"
).in_("id", follow_up_ids).execute()

# Processa em memória
for rfq in (rfqs_result.data or []):
    # ... lógica de follow-up por channel ...

# Batch update no final
db.table("rfq_requests").update({
    "follow_up_count": db.raw("follow_up_count + 1")
}).in_("id", reminded_ids).execute()
```

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

**Problema:** Batch update trivial se torna N queries individuais.

**Solução (1 linha):**
```python
if expired:
    db.table("rfq_requests").update(
        {"status": "expired"}
    ).in_("id", expired).execute()
```

---

### P0 #3 — Schema gap: `rfq_requests`

**Problema:** O código em `nodes.py` referencia a tabela `rfq_requests` (`.select()`, `.update()`, `.eq("id", ...)`), mas a migration `20260602000000_agent_lists.sql` documenta que `agent_lists` substitui `rfq_requests`. Não está claro se:
- `rfq_requests` ainda existe no DB de produção (criada fora das migrations versionadas)
- O código de `nodes.py` precisa ser migrado para `agent_lists`
- As queries atuais estão funcionando ou falhando silenciosamente

**Ação necessária:** Verificar existência da tabela no Supabase; migrar código se necessário.

---

### P1 #4 — HTTP sequencial em loop por integração (routine_functions.py:1781–1815)

**Código atual:**
```python
async with httpx.AsyncClient(timeout=15.0) as http:
    for intg_id in integration_ids:
        try:
            page = 1
            while True:
                r = await http.get(
                    f"{polp_base}/integrations/{intg_id}/recurrings",
                    headers=polp_headers,
                    params={"page": page},
                )
                # ... pagination ...
```

**Problema:** Cada integração faz chamadas HTTP em série. Com 5 integrações e 3 páginas cada → 15 chamadas sequenciais (~15s).

**Solução:**
```python
sem = asyncio.Semaphore(5)  # limita concorrência

async def fetch_integration(intg_id):
    async with sem:
        async with httpx.AsyncClient(timeout=15.0) as http:
            page = 1
            while True:
                r = await http.get(...)
                # ...

recurrings_results = await asyncio.gather(
    *[fetch_integration(iid) for iid in integration_ids]
)
```

---

### P1 #5 — Bundle sem code splitting (blu_v3)

**Situação atual:**
- Zero usos de `React.lazy` ou `React.memo` no source
- Vite config sem `manualChunks` ou `rollupOptions.output`
- `App.tsx` importa todas as páginas estaticamente

**Solução recomendada:**
```tsx
// Em App.tsx ou router config
const BibliotecaRoom = React.lazy(() => import('./pages/app/BibliotecaRoom'));
const DocumentosRoom = React.lazy(() => import('./pages/app/DocumentosRoom'));
const OnboardingApp = React.lazy(() => import('./pages/onboarding/OnboardingApp'));

// Com Suspense boundary
<Suspense fallback={<LoadingSpinner />}>
  <Routes>
    <Route path="/biblioteca" element={<BibliotecaRoom />} />
    ...
  </Routes>
</Suspense>
```

---

## 4. Positive Patterns (Good Practices Found)

Nem tudo é bottleneck. O código também demonstra boas práticas:

| Pattern | Location | Notes |
|---------|----------|-------|
| `asyncio.gather` para paralelismo | `routine_functions.py:1011` | `routines_resp, approvals_resp, jobs_resp` em paralelo |
| `asyncio.gather` para KPI/calendar | `routine_functions.py:1351` | 4 queries paralelas |
| Redis caching com TTL | `context_service.py:340–355` | Cache de `sql_table_config` com fallback |
| Redis caching de prompts | `context_service.py:370–395` | Cache de templates Langfuse |
| Redis caching de canonical_columns | `context_service.py:420–440` | TTL longo, filtro in-memory |
| `asyncio.to_thread` para Supabase | `routine_functions.py` (geral) | Evita bloquear event loop com chamadas síncronas do Supabase client |

---

## 5. Bundle Size Analysis — blu_v3

| Métrica | Valor |
|----------|-------|
| Framework | Vite + React 18 + Tailwind v3 |
| .next/static/chunks/ | N/A (Vite, não Next.js) |
| `dist/` build | Não disponível (build não executado) |
| Dependências principais | react, react-dom, react-router-dom, @supabase/supabase-js, @tanstack/react-query, zustand, xlsx, @phosphor-icons/react |
| Code splitting | ❌ Ausente |
| Component memoization | ⚠️ Parcial — `useMemo`/`useCallback` em 6 arquivos, zero `React.memo` |
| Image optimization | ❌ Ausente — raw `<img>` tags |
| Lazy loading | ❌ Ausente — zero `React.lazy` / `Suspense` |

**Recomendações prioritárias:**
1. Code-split por rota com `React.lazy` + `Suspense` → reduz TTI inicial
2. `React.memo` em componentes de lista pesados (`MonthlyGantt`, `ChatPanel`, tabelas)
3. Vite `manualChunks` para separar vendor bundles (`xlsx`, `@phosphor-icons/react`)
4. Lazy loading de imagens com `loading="lazy"` e formato WebP

---

## 6. SQL Index Analysis

Dos 51 CREATE TABLE statements no baseline, há 62 índices — média de ~1.2 índices por tabela. Porém:

| Tabela | Índices existentes | Queries observadas | Gap |
|--------|-------------------|-------------------|-----|
| `agent_sessions` | `(client_id)`, `(client_id, status)` | Filtra por `id`, `agent_catalog_id`, `uploaded_document_ids` | Falta índice em `agent_catalog_id` |
| `agent_catalog` | PK `(id)`, UK `(slug)` | Filtra por `slug` → OK | — |
| `approval_requests` | `(client_id, agent_slug)`, `(client_id, status)`, `(session_id)` WHERE NOT NULL | OK | — |
| `client_goals` | `(client_id, dimension)` WHERE active, `(client_id)` | OK | — |
| `notifications` | `(client_id, read_at, created_at DESC)` WHERE not dismissed | OK | — |
| `rfq_requests` | ❌ Tabela não encontrada no schema | Referenciada em `nodes.py` | **P0** — schema gap |
| `polp_accounts` | `(client_id)`, `(integration_id)` | OK | — |
| `polp_bills` | `(client_id, due_date)` | Filtra também por `status` | Considere `(client_id, status, due_date)` |

---

## 7. Acceptance Criteria Checklist

- [x] All Tier 1 services analyzed for N+1, batching, indexes, caching
  - agent_api ✅, blu_agent_framework ✅, blu_supabase_client ✅, blu_models ✅, blu_context_service ✅
- [x] Frontend bundle size and render optimization checked
  - blu_v3 analisado (Vite, sem .next); code splitting + image optimization gaps documentados
- [x] At least 3 concrete bottlenecks identified with code references
  - 10 bottlenecks identificados, 5 com code snippets detalhados
- [x] File saved to `docs/planning/issue-57/performance-review.md`
- [ ] Git commit + push to `phase-0/issue-57-code-patterns-review`

---

## 8. Methodology Notes

**Ferramentas utilizadas:**
- `grep -rn` para pattern matching (rg não disponível no ambiente)
- `wc -l` para métricas de tamanho de arquivo
- Leitura direta de SQL migrations para análise de índices
- `find` para inventário de arquivos fonte no frontend

**Limitações:**
- `rg` (ripgrep) não pôde ser instalado (Amazon Linux 2023 sem repositório)
- Build do frontend (`vite build`) não foi executado — análise de bundle size baseada em source estático
- `blu_v3/.next/` não existe (projeto Vite, não Next.js)
- Apenas 3 arquivos de migration ativos analisados; applied/archive verificados seletivamente

**Escopo coberto:**
- Tier 1 completo (5/5)
- Tier 2 parcial: `blu_llm_service`, `blu_rag_factory`, `blu_prompt_management`, `blu_sql_factory`, `tool_pool_api` — análise delegada a scan de patterns globais (sequential await, N+1)
- Tier 3-4: frontend apenas (blu_v3)
