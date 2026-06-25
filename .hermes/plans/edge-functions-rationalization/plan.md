# Plano: Racionalização de Edge Functions e Higiene de Auth

**Status:** Draft v2 (reescrito após merge da main em `53a9bbc1`)
**Owner:** TBD
**Branch base:** `main`
**Data baseline:** 2026-06-25

---

## 0. TL;DR

A racionalização original propôs ~3.580 LOC de redução em 5 ondas. **~30% já foi feita** (Fases 1.1, 1.2, 2.1, 2.4 minhas + 3.2 via BKL-197/199/210 + BKL-038/041 etc. suas). O que sobra são **2 categorias de trabalho**:

1. **Auth fix P0 (bloqueante de produção):** 7 testes RED em `tests/integration/test_sequential_signups.py` + `tests/behaviors/test_b1_*.py` esperam um fix que ainda não foi aplicado ao código. O plano de fix existe em `docs/observability/auth-second-signup-root-cause.md` mas o código em `packages/blu-auth/src/AuthContext.tsx:233-240` ainda chama `signUp` sem `signOut` prévio.
2. **Higiene + 5 pendências de runtime:** trigger DB órfão, M7 (kill `generate-context-report`), Polp webhook consolidation, e 3 movimentos para Python/SQL.

**Princípio orientador** (herdado de `.github/skills/supabase`):
- EFs são para tempo < 60s, validação JWT, ou URL pública como `redirect_uri`
- EFs são inadequados para: ETL longo, computação que deveria ser SQL, lógica de negócio Python já em framework
- Toda EF user-facing deve usar `requireAuth` de `_shared/blu_auth.ts` ou `verify_jwt=true` — **não pode ser aberta sem justificativa**

---

## 1. Estado atual (baseline: `main` @ 53a9bbc1)

### Inventário de EFs (25 deployed, 8.494 LOC)

| # | EF | LOC | `verify_jwt` | Trigger | Auth gate real |
|---|---|---|---|---|---|
| 1 | discover-bigquery-columns | 207 | false | frontend | `requireAuth` + ownership check |
| 2 | etl-bigquery-ingest | 491 | false | pg_net (service role) | `isSystemInvocation` + `requireAuth` fallback |
| 3 | etl-refresh-dashboards | 132 | false | pg_net (service role) | `isSystemInvocation` only |
| 4 | generate-context-report | 610 | false | waitUntil from onboarding-bootstrap | service role only |
| 5 | get-agenda-events | 1009 | true | frontend | edge-layer (HS256) |
| 6 | get-monday-subitems | 162 | true | frontend | edge-layer (HS256) |
| 7 | google-calendar-events | 348 | false | frontend | `requireAuth` |
| 8 | google-oauth-callback | 186 | false | external (Google redirect) | state-blob 10min TTL |
| 9 | google-oauth-start | 85 | true | frontend | edge-layer (HS256) |
| 10 | match-columns | 505 | false | EF-to-EF (service role) + frontend | `isSystemInvocation` + `requireAuth` |
| 11 | onboarding-bootstrap | 228 | false | frontend | `requireAuth` |
| 12 | onboarding-capture-drive-token | 139 | false | frontend | `requireAuth` |
| 13 | onboarding-website-intel | 221 | false | frontend | `requireAuth` |
| 14 | polp-connect | 136 | true | frontend | edge-layer (HS256) |
| 15 | polp-sync | 147 | false | frontend | `requireAuth` |
| 16 | polp-webhook | 375 | false | external (Polp HMAC) | HMAC-SHA256 |
| 17 | process-document | 751 | true | EF-to-EF (service role) + frontend | edge-layer (HS256) |
| 18 | routine-builder | 190 | false | frontend | `requireAuth` |
| 19 | run-csv-etl | 378 | false | frontend | `requireAuth` |
| 20 | run-sync-etl | 184 | false | frontend | `requireAuth` |
| 21 | save-api-token | 269 | false | frontend | `requireAuth` |
| 22 | search-documents | 212 | true | frontend + service role | edge-layer (HS256) |
| 23 | upload-csv-source | 252 | true | frontend | edge-layer (HS256) |
| 24 | upload-drive-source | 324 | true | frontend | edge-layer (HS256) |
| 25 | website-context-builder | 486 | false | waitUntil from onboarding-bootstrap | service role only |

### Helpers em `_shared/` (8 files, 1.728 LOC)

| Helper | LOC | Função | Usado por |
|---|---|---|---|
| `bigquery_auth.ts` | 434 | RS256 JWT → access token, BigQuery paginated query | discover-bq, etl-bq-ingest |
| `blu_auth.ts` | 258 | JWT validation, system-key detection, MFA, client resolution | 18 EFs |
| `cors.ts` | 37 | CORS + JSON helper | todos os EFs |
| `fernet.ts` | 194 | AES-128-CBC + HMAC-SHA256, Web Crypto, interop Python | 4 EFs (3 readers + store_google_token) |
| `fernet.test.ts` | 130 | 10 Deno test blocks (round-trip, cross-compat) | (test file) |
| `google_drive.ts` | 292 | Refresh token exchange, Drive metadata + export | upload-drive-source |
| `sheet_intake.ts` | 196 | Sheet scoring, type inference, CSV parser | run-csv-etl, upload-csv/drive |
| `store_google_token.ts` | 128 | Encrypt + upsert Google token pair | google-oauth-callback, capture-drive |

### Tests

- `tests/behaviors/`: 123 test files
- `tests/integration/`: 4 files (incl. `test_sequential_signups.py` com 4 RED tests)
- `tests/unit/`: 5 files
- `supabase/functions/*/index_test.ts`: 1 (apenas `onboarding-website-intel/index_test.ts`, 11 tests)
- `supabase/functions/_shared/fernet.test.ts`: 1 (10 Deno tests)
- `supabase/functions/onboarding-bootstrap/tests/mappers_test.ts`: 1 (pure module test, 84 LOC)

### Migrations

- Root: 4 files (5.398 LOC, inclui `baseline_v2.sql` com 5.196 LOC)
- Applied: 23 files (2.557 LOC)
- Total schema: 27 migrations, 7.955 LOC

---

## 2. Decisões tomadas

| ID | Decisão | Origem |
|---|---|---|
| D1 | Plano em `.hermes/plans/edge-functions-rationalization/plan.md` | D1 do plano original |
| D2 | **Reescrito do zero** após merge com main (519 commits à frente) | Feedback do usuário |
| D3 | **Auth fix é P0** — precede qualquer outra fase | 7 RED tests em `test_sequential_signups.py` + `b1_fluxo_signup.py` |
| D4 | Phases 2.2 e 2.3 do plano original **descartadas** (BKL-038/041 fazem polling e unificação de upload, respectivamente) | Conflito no merge |
| D5 | Phase 3.2 (website-intel → client-side) **parcialmente feita** (PRs #197/#199/#210) — manter como expansão do EF, não mover para client-side | O usuário expandiu o EF (CNPJ, phone, 17 verticals) em vez de mover |
| D6 | Phase 4.1 (M7) **bloqueada** — tentativa foi revertida em `cf33ffd1` | Commit `73c7080c` → `cf33ffd1` |
| D7 | Estratégia de execução: em ondas, cada fase mergeável independentemente | D2 do plano original |

---

## 3. Issues conhecidos (não estavam no plano original)

### Issue 3.1 — AuthContext contamination no signup (P0)

**Sintoma:** `carolina@test → lucia@test → joao@test` em sequência, 2º e 3º falham estruturalmente.

**Root cause confirmado** (em `docs/observability/auth-second-signup-root-cause.md`, mas **NÃO aplicado**):
- `packages/blu-auth/src/AuthContext.tsx:233-240` `signUp()` não chama `supabase.auth.signOut()` antes
- `OnboardingApp.tsx:316-336` `handleSubmit()` não verifica sessão existente
- `packages/blu-auth/src/index.ts` não expõe `onSignUp` lifecycle hook

**7 RED tests esperando:** `tests/integration/test_sequential_signups.py` (4 tests) + `tests/behaviors/test_b1_fluxo_signup.py` (3 tests).

**Evidência:** o `git log` mostra o doc criado mas o código não foi tocado depois. Plano de fix em section 5 do doc (B-1 + B-2 + B-3).

### Issue 3.2 — Trigger `on_auth_user_created` ausente (P0)

**Sintoma:** `public.handle_new_auth_user()` (baseline L2975) é código morto. Nunca é chamada.

**Root cause:** o trigger `CREATE TRIGGER on_auth_user_created ON auth.users AFTER INSERT EXECUTE FUNCTION public.handle_new_auth_user()` **não existe em nenhuma migration**. Existia no schema pré-baseline (provavelmente Supabase Auth webhook); foi perdido no corte do baseline.

**Impacto:**
- `clientes_blu` row só é criado via `ensure_tenant_row()` SECURITY DEFINER (chamado por `onboarding-bootstrap` L84)
- O trigger morto é uma "rede de segurança" que nunca dispara
- O comment de `onboarding-bootstrap` admite: "if the handle_new_auth_user trigger missed it (e.g. some OAuth flows)"

**Evidência:** `tests/behaviors/test_b1_trigger_on_auth_user_created.py` (326 lines, AC#1 explícita: "O comando `CREATE TRIGGER on_auth_user_created ON auth.users AFTER INSERT EXECUTE FUNCTION public.handle_new_auth_user()` existe em `supabase/migrations/20260523999999_baseline_v2.sql`.")

### Issue 3.3 — `run-csv-etl` faz ETL inline (não apenas orquestração)

**Sintoma:** o nome sugere "orquestrador" mas o body faz stages + `dim_clientes` upsert + `fato_transacoes` insert + cleanup + `reg_jobs` insert. O `reg_jobs` row é então um record do que já foi feito.

**Comentário no código (L1-12):** "this replaces the previous pg_cron + sincronizar_csv_cliente path so that the handler is the single source of truth for ETL."

**Impacto:** o nome é enganoso. Não bloqueia produção mas dificulta entendimento.

### Issue 3.4 — `etl-bigquery-ingest` daisy-chain complexo

**Sintoma:** 491 LOC, dos quais ~40 (L343-373) são lógica de self-daisy-chain via `BLU_SYSTEM_INVOKE_KEY` Bearer token, com `chain_attempts` capped em 50 e `input_params.bq_resume_cursor` shape complexa.

**Impacto:** workaround para o cap de 60s do edge runtime. Complexo de debugar e manter.

### Issue 3.5 — `generate-context-report` é supostamente monthly via pg_cron mas não há schedule SQL

**Sintoma:** comment no código (L11) diz "pg_cron mensal". Não encontrei `net.http_post` para essa EF em applied migrations.

**Impacto:** se o monthly report realmente roda, está por outro caminho (provavelmente Python routine `context_report` chamado via `agent_api/core/routine_functions.py:223` — `analytics.generate_context_report`).

### Issue 3.6 — `config.toml` `match-columns` comment enganoso

**Sintoma:** `match-columns` tem `verify_jwt = false` mas o comment do config diz "No sensitive data accessed, so no auth gate is needed". A função REALMENTE tem `isSystemInvocation` + `requireAuth` (L447-449).

**Impacto:** comentário enganoso dificulta auditoria de segurança.

### Issue 3.7 — `google-oauth-start` sob header errado

**Sintoma:** `google-oauth-start` está sob o section header "Internal workers" no `config.toml`, mas tem `verify_jwt = true` e é user-facing. O callback (`google-oauth-callback`) está num section diferente.

**Impacto:** auditoria visual confusa.

### Issue 3.8 — Polp webhook: 2 implementações

**Sintoma:** `supabase/functions/polp-webhook/` (TS, vocabulário Polp atual) + `services/tool_pool_api/.../polp_webhook_router.py` (Python, vocabulário Pluggy legado). Total: 642 LOC. Polp é integração live com Open Finance (não código morto — D3 do plano original).

**Status:** plano de consolidação depende de investigação de logs (Fase 3.0 original) para decidir qual é canônico.

---

## 4. Estado das fases do plano original

| Fase | Título | Status | Notas |
|---|---|---|---|
| 1.1 | Auth gap (match-columns, onboarding-website-intel) | ✅ **feito** (commit `02f2a4c5`) | Sobreviveu ao merge |
| 1.2 | Fernet helper compartilhado | ✅ **feito** (commit `eb77db58`) | Sobreviveu ao merge, 4 EFs o usam |
| 2.1 | BQ discover/preview merge | ✅ **feito** (commit `a06f8292`) | `preview-bigquery-columns` deletado |
| 2.2 | enqueue_sync_job helper | ❌ **dropado** | BKL-038 mudou o padrão de polling |
| 2.3 | intake_file helper | ❌ **dropado** | BKL-041 unificou upload via process-document |
| 2.4 | store_google_token helper | ✅ **feito** (commit `b443555c`) | 2 EFs o usam |
| 3.0 | Investigar logs Polp | ⏸️ **pendente** | Bloqueador da 3.1 |
| 3.1 | Consolidar Polp webhook | ⏸️ **pendente** | Depende de 3.0 |
| 3.2 | website-intel → client-side | ⚠️ **parcial** | PRs #197/#199/#210 expandiram o EF (CNPJ, phone, 17 verticals). EF ainda existe, mas com mais funcionalidade. Decisão: manter como EF ou re-avaliar |
| 3.3 | etl-refresh-dashboards → pg_cron | ⏸️ **pendente** | |
| 3.4 | match-columns → Python service | ⏸️ **pendente** | |
| 3.5 | search-documents → direct SQL + Cohere | ⏸️ **pendente** | |
| 3.6 | search-documents → Python service (Phase 3.3 da nova onda 5) | ✅ **feito** | 212 LOC → Python `services/search_documents/` + FastAPI `/v1/search-documents`. Bloqueado por **Issue 3.6.1** (função RPC sumiu do baseline ativo). |
| 4.1 | Matar generate-context-report EF (M7) | ⚠️ **bloqueada** | Tentativa `73c7080c` revertida em `cf33ffd1`. Re-avaliar contexto antes de retentar |
| 4.2 | etl-bigquery-ingest → Python | ⏸️ **pendente** (opcional) | |
| 4.3 | routine-builder → agent_api | ⏸️ **pendente** (opcional) | |
| 4.4 | polp-sync → Python | ⏸️ **pendente** (opcional) | |
| 5.1 | Unificar agenda endpoints (3→1) | ⏸️ **pendente** (opcional) | |

**LOC economizado até agora:** ~280 LOC (Phase 2.1 BQ merge).
**LOC em helpers compartilhados:** ~1.728 LOC (`_shared/`).
**LOC de EFs:** 8.494 (era 8.115 no plano original — cresceu por causa da expansão BKL-019/024/028/029/037/038/039/040/041).

---

## 5. Fases propostas (reorganizadas)

### Onda 0 — Auth P0 (CRÍTICO, bloqueia produção)

#### Fase 0.1 — Fix AuthContext contamination

**Justificativa:** 7 RED tests em `tests/integration/test_sequential_signups.py` + `tests/behaviors/test_b1_fluxo_signup.py`. Bloqueador de produção — qualquer novo usuário falha no signup após o primeiro em um mesmo browser.

**Origem do plano:** `docs/observability/auth-second-signup-root-cause.md` section 5 (B-1 + B-2 + B-3).

| # | Tarefa | Arquivos | LOC |
|---|---|---|---|
| 0.1.1 | B-1: Em `packages/blu-auth/src/AuthContext.tsx:233-240`, antes de `supabase.auth.signUp`, fazer `await supabase.auth.signOut()` + reset de state (`session=null, user=null, clientId=null, tier=null, loading=false`) | 1 | +5 |
| 0.1.2 | B-2: Em `apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx:316-336`, `handleSubmit`, adicionar check no topo: se já há sessão, chamar `signOut()` antes de `signUp` | 1 | +3 |
| 0.1.3 | B-3: Exportar `onSignUp` lifecycle hook em `packages/blu-auth/src/index.ts` para que consumers possam resetar cache pós-signup (analytics identify, etc.) | 1 | +10 |
| 0.1.4 | Validar que os 7 RED tests viraram GREEN | (test files) | 0 |

**Critérios de done:**
- Os 7 RED tests viraram GREEN
- `tests/integration/test_sequential_signups.py` passa com 3+ signups em sequência
- `tests/behaviors/test_b1_fluxo_signup.py` (3 tests) passam

**Risco:** Baixo. Mudança isolada em 3 arquivos.

---

#### Fase 0.2 — Recriar trigger `on_auth_user_created` (B-1 do test_b1_trigger_on_auth_user_created.py)

**Justificativa:** `handle_new_auth_user` está órfão desde o baseline. Sem o trigger, `clientes_blu` só é criado via `ensure_tenant_row()` (SECURITY DEFINER) que é chamado tarde demais pelo `onboarding-bootstrap`. Recriar o trigger garante que o tenant é criado no momento do INSERT em `auth.users`, não dependendo do frontend.

**Origem do plano:** `tests/behaviors/test_b1_trigger_on_auth_user_created.py` AC#1.

| # | Tarefa | Arquivos | LOC |
|---|---|---|---|
| 0.2.1 | Nova migration: `supabase/migrations/applied/20260625_p14_recreate_on_auth_user_created_trigger.sql` com `CREATE TRIGGER on_auth_user_created AFTER INSERT ON auth.users FOR EACH ROW EXECUTE FUNCTION public.handle_new_auth_user();` | 1 | +5 |
| 0.2.2 | Validar que `test_b1_trigger_on_auth_user_created.py` AC#1 (existence) e AC#2 (fires correctly) viraram GREEN | (test files) | 0 |

**Critérios de done:**
- O trigger existe no schema
- Novo INSERT em `auth.users` cria automaticamente a row em `clientes_blu` (com `external_user_id`, `api_key`, `nome_empresa`)
- `tests/behaviors/test_b1_trigger_on_auth_user_created.py` passa

**Risco:** Médio. O trigger pode duplicar o que `ensure_tenant_row` faz. Mitigação: o `handle_new_auth_user` já usa `ON CONFLICT (external_user_id) DO NOTHING`, então é idempotente.

---

### Onda 1 — Higiene de runtime (baixo risco, qualidade)

#### Fase 1.1 — Limpar `config.toml`

**Justificativa:** comentários enganosos dificultam auditoria de segurança.

| # | Tarefa | LOC |
|---|---|---|
| 1.1.1 | Corrigir comment de `match-columns`: remover "No sensitive data accessed, so no auth gate is needed" (errado — a função TEM auth gate interno) | -2 |
| 1.1.2 | Mover `[functions.google-oauth-start]` para o section "User-facing" (está sob "Internal workers" — errado) | 0 (reordenação) |
| 1.1.3 | Adicionar `[auth]` section mínima se houver config relevante (atualmente não há) | 0 ou +5 |

**Risco:** Mínimo. Mudança só em config.

---

#### Fase 1.2 — Renomear `run-csv-etl` ou documentar o ETL inline

**Justificativa:** o nome sugere "orquestrador" mas o body faz ETL completo. Decisão: ou renomear para `csv-etl-pipeline` (mais preciso) ou apenas documentar melhor no header.

| # | Tarefa | LOC |
|---|---|---|
| 1.2.1 | Adicionar nota clara no header do arquivo: "This function does the FULL ETL pipeline inline, not just orchestration. The `reg_jobs` row it creates is a record of the work, not a trigger for downstream processing." | +5 |
| 1.2.2 | Considerar renomear para `csv-etl-pipeline` (mudança breaking — atualizar todos os callers) | 0 ou -10 |

**Risco:** Mínimo (mudança só de doc) ou médio (rename).

---

#### Fase 1.3 — Decidir sobre `generate-context-report` monthly cron

**Justificativa:** comment diz "monthly pg_cron" mas não há schedule SQL. Provavelmente o monthly report roda via `agent_api/core/routine_functions.py:223` (`analytics.generate_context_report` routine function). O EF só é fire-and-forget de `onboarding-bootstrap`.

| # | Tarefa | LOC |
|---|---|---|
| 1.3.1 | Investigar: o monthly report roda pelo Python routine ou pelo EF? | 0 |
| 1.3.2 | Se for via Python: corrigir o comment enganoso no EF | 0 |
| 1.3.3 | Se for via EF: adicionar a migration pg_cron que está faltando | 0 a +20 |

**Risco:** Baixo (só doc) ou médio (adicionar SQL).

---

### Onda 2 — Investigação Polp e consolidação

#### Fase 2.0 — Investigar qual webhook Polp é canônico

**Justificativa:** Plano original pendente. Duas implementações paralelas (TS + Python) de webhook do Polp. Polp é live (D3 do plano original), então o canônico é o que o Polp dashboard está apontando.

| # | Tarefa | Quem |
|---|---|---|
| 2.0.1 | Logs do Supabase Edge runtime: `polp-webhook` (últimos 30 dias) | Eng |
| 2.0.2 | Logs do `tool_pool_api` FastAPI: `/webhooks/polp` (últimos 30 dias) | Eng |
| 2.0.3 | `SELECT event_type, COUNT(*) FROM polp_webhook_events GROUP BY event_type` — contar vocabulário Pluggy (`item/updated`) vs Polp (`integrations.updated`) | Eng |
| 2.0.4 | Checar config do Polp dashboard: qual URL está registrada? | Ops |
| 2.0.5 | Decidir canônico | Owner |

**Critério de parada:** se ambos receberem eventos, investigar por que (redirect, config pendente).

---

#### Fase 2.1 — Consolidar Polp webhook (depende de 2.0)

| Cenário | Ação | LOC economizado |
|---|---|---|
| TS vence (esperado) | Deletar `services/tool_pool_api/.../polp_webhook_router.py` + import + `PLUGGY_WEBHOOK_SECRET` env | -267 |
| Python vence | Deletar `supabase/functions/polp-webhook/` + config block + reconfigurar Polp dashboard | -375 |

---

### Onda 3 — Movimentos para runtime melhor

#### Fase 3.1 — `etl-refresh-dashboards` → pg_cron

**Justificativa:** 132 LOC de EF para chamar 1 RPC. Overhead puro. Pode ser um `pg_cron` job que chama `analytics_v2.refresh_client_dashboards(client_id)` direto, eliminando a EF.

| # | Tarefa | LOC |
|---|---|---|
| 3.1.1 | Estender `analytics_v2.process_pending_jobs` para também processar `job_type='refresh_dashboards'` (já está parcialmente no dispatcher) | 0 a +20 |
| 3.1.2 | Deletar `supabase/functions/etl-refresh-dashboards/` | -132 |
| 3.1.3 | Remover bloco `[functions.etl-refresh-dashboards]` do config | -6 |

**Risco:** Baixo. Mudança puramente SQL + delete.

---

#### Fase 3.2 — `match-columns` → Python service

**Justificativa:** Dice coefficient + alias table é CPU-bound trivial. Pode ser um módulo Python em `services/blu_schema_matcher/`. Hoje é chamado por 2 EFs + 1 serviço Python — 3 callers, todos podem chamar direto.

| # | Tarefa | LOC |
|---|---|---|
| 3.2.1 | Criar `services/blu_schema_matcher/` com `match_columns(source_columns, target_table)` | +500 |
| 3.2.2 | Reescrever callers para chamar o serviço Python | -10 |
| 3.2.3 | Deletar `supabase/functions/match-columns/` | -505 |

**Risco:** Médio. Precisa de cobertura de teste ampla para garantir equivalência de output.

---

#### Fase 3.3 — `search-documents` → direct SQL + Cohere

**Justificativa:** 212 LOC de wrapper sobre 2 RPCs SQL + 1 chamada Cohere. `blu_rag_factory` Python pode chamar Cohere direto + RPC direto.

| # | Tarefa | LOC |
|---|---|---|
| 3.3.1 | Em `services/blu_rag_factory/.../retriever.py`: substituir `supabase.functions.invoke('search-documents')` por `cohere.embed()` + `supabase.rpc('vector_db.hybrid_match_documents', {...})` | ±20 |
| 3.3.2 | Deletar `supabase/functions/search-documents/` | -212 |
| 3.3.3 | Remover bloco `[functions.search-documents]` do config | -5 |

**Risco:** Médio. SQL RPC precisa ter grants corretos para service-role do RAG factory.

---

#### Issue 3.6.1 — `vector_db.hybrid_match_documents` não existe no baseline ativo (BLOQUEADOR P0)

**Achado durante a execução da Fase 3.3:**

1. A EF `search-documents` chama `vector_db.hybrid_match_documents` com **12 parâmetros** (incluindo `scope`, `categories`, `themes`, `fusion_strategy`, `keyword_weight`, `vector_weight`).
2. A única definição no repo está em `archive/20260430000000_baseline.sql:2692` e tem apenas **5 parâmetros**: `(p_client_id, p_query_embed, p_query_text, p_match_count, p_theme_filter)`.
3. O baseline ativo `20260523999999_baseline_v2.sql` **NÃO DEFINE** nenhuma das duas funções (`hybrid_match_documents` nem `match_documents`).
4. Lucas confirmou (2026-06-25) que `vector_db.document_chunks` e `vector_db.documents` **EXISTEM no DB live** (schema confirmado via Studio). Só as funções estão faltando.

**Implicações:**
- A EF `search-documents` retornava 500 silenciosamente em produção (ou nunca foi deployada — Lucas disse que "não achei hybrid match documents" no DB).
- O port Python (commit `085af419`) replica a assinatura de 12 params, então também vai falhar até que a função seja reaplicada.

**Migration proposta criada:**

`supabase/migrations/proposed/20260625000000_hybrid_match_documents_12param.sql`

- Cria `vector_db.match_documents` (5 params, signature exata que o EF "semantic" mode chama).
- Cria `vector_db.hybrid_match_documents` (12 params, signature exata que o EF "hybrid" mode e o port Python chamam).
- Implementa RRF (`1/(60+rank_sem) + 1/(60+rank_kw)`) e weighted fusion (configurável por `p_fusion_strategy`).
- Threshold do hybrid é aplicado LOOSELY (similarity >= threshold/2 OR keyword_score > 0) pra preservar FTS-only hits.
- JOIN com `vector_db.documents` retorna `file_name` e `document_title` (o que `blu_rag_factory.retriever` espera).
- `SET search_path = ''` + `STABLE SECURITY DEFINER` (padrão).
- Grants para `service_role` e `authenticated`.

**Ação de Lucas (próximo passo):**
- [ ] Revisar a migration proposta (5 min de leitura).
- [ ] Aplicar no DB live via Supabase Studio SQL Editor OU `supabase db push` se a migration for promoted para `applied/`.
- [ ] Smoke test: rodar a query comentada no fim do arquivo (descomentar e ajustar o client_id).
- [ ] Verificar se `POST /v1/search-documents` retorna 200 com resultados reais (os 33 tests do port são todos unit-mocked — só cobrem a forma, não a função SQL).

**Follow-up (P1, não-bloqueador):**
- [ ] Capturar o schema de `vector_db.documents` + `vector_db.document_chunks` + 11 índices numa migration `proposed/20260625*_vector_db_schema_snapshot.sql` pra repo ficar reproduzível (Lucas colou o DDL via chat; precisa virar migration).
- [ ] Adicionar test E2E real (1-2 tests) que valide `POST /v1/search-documents` contra o DB live, com cleanup.

**LOC:** +200 LOC SQL (a migration proposta).

---

#### Fase 3.4 — `onboarding-website-intel` → client-side (REAVALIAR)

**Justificativa original:** 100ms de regex + fetch + JSON, sem DB / sem secrets. Era candidata natural para client-side.

**Estado atual:** PRs #197/#199/#210 expandiram o EF para incluir CNPJ extraction (mod-11 check digit), phone, 17 verticals (era 11), confidence dinâmico. O teste Deno (`index_test.ts`, 11 tests) cobre esses casos. Mover para client-side perde esses testes e o backend precisa ser reescrito.

**Recomendação:** MANTER COMO EF. A expansão justificou a permanência. Marcar Fase 3.2 do plano original como **não-aplicável** dado o estado atual.

---

#### Fase 3.5 — `etl-bigquery-ingest` → Python worker (OPCIONAL)

**Justificativa:** BQ scans podem levar 2-10min. Cap de 60s do edge runtime força a complexidade do daisy-chain (~40 LOC de `EdgeRuntime.waitUntil` + `chain_attempts` bookkeeping).

**Risco:** Alto. EF mais complexo do codebase. Mudança grande de runtime. **Avaliar ROI antes de retentar** — se o daisy-chain atual funciona, a dívida pode não justificar o trabalho.

---

#### Fase 3.6 — `routine-builder` → `agent_api` (OPCIONAL)

**Justificativa:** SSE + Anthropic + chat history são first-class Python concerns. `agent_api` já tem o pattern de streaming chat.

| # | Tarefa | LOC |
|---|---|---|
| 3.6.1 | Adicionar endpoint streaming `POST /v1/agents/routine-builder/chat` em `services/agent_api/.../agents_router.py` | +200 |
| 3.6.2 | Portar system prompt (carrega `agent_catalog` + `agent_action_catalog`) | +30 |
| 3.6.3 | Atualizar frontend | ±20 |
| 3.6.4 | Deletar `supabase/functions/routine-builder/` | -190 |

**Risco:** Médio. Mudança de protocolo (SSE over fetch vs `supabase.functions.invoke`).

---

#### Fase 3.7 — `polp-sync` → Python ou reusar webhook (OPCIONAL)

**Justificativa:** Loop sequencial de 750+ chamadas HTTP. Python async seria mais rápido. Alternativa: o webhook já faz a sync em `accounts.synchronized`; o botão "↻" no AdminScreen poderia disparar um evento sintético.

| # | Tarefa | LOC |
|---|---|---|
| 3.7.1 (A) | Reescrever em Python async, fazer chamadas paralelas | +200 |
| OU 3.7.1 (B) | Disparar evento sintético `accounts.synchronized` para o webhook | +30 |
| 3.7.2 | Deletar `supabase/functions/polp-sync/` | -147 |

**Risco:** Médio. (A) tem risco de Python async mal calibrado; (B) requer Polp aceitar eventos sintéticos (pode não ser o caso).

---

### Onda 4 — M7 e Fase 5.1 (REAVALIAR)

#### Fase 4.1 — M7 (kill `generate-context-report` EF) — REAVALIAR

**Estado:** Tentativa em `73c7080c` foi revertida em `cf33ffd1`. A reversão indica que matar o EF causou regressão (provavelmente o dispatcher pg_cron não estava atualizado, ou o agent_api ainda não tem o endpoint equivalente).

**Recomendação:** Investigar por que a tentativa anterior falhou antes de retentar. Hipótese: faltou adicionar endpoint `/v1/internal/context-report/run` no `agent_api` (que era o plano da Fase 4.1 original).

| # | Tarefa | LOC |
|---|---|---|
| 4.1.1 | Investigar `git revert -m 1 cf33ffd1` ou ler o PR revertido para entender o que quebrou | 0 |
| 4.1.2 | Se for falta de endpoint no `agent_api`: criar `POST /v1/internal/context-report/run` (chama `run_for_client` de `context_report.py`) | +30 |
| 4.1.3 | Reescrever `schedule_monthly_context_reports` SQL para chamar o endpoint | +30 |
| 4.1.4 | Deletar `supabase/functions/generate-context-report/` | -610 |

**Risco:** Médio (precisa entender por que a tentativa anterior falhou).

---

#### Fase 4.2 — Unificar agenda endpoints (3 → 1) — OPCIONAL

**Estado atual:** 3 EFs (get-agenda-events 1009 LOC, get-monday-subitems 162, google-calendar-events 348) = 1.519 LOC. Maior concentração de LOC em agenda.

**Risco:** Alto. 3 endpoints consumidos em 4+ lugares no frontend. Regressão silenciosa fácil.

**Recomendação:** Pular a menos que a Onda 3 entregue valor suficiente sem essa fase.

---

## 6. Métricas de sucesso (targets após todas as ondas)

| Métrica | Baseline | Target |
|---|---|---|
| Total de EFs | 25 | 18-20 |
| LOC de EFs | 8.494 | ~5.500 |
| Auth gaps abertos | 2 (match-columns + website-intel **FECHADOS** mas trigger DB ausente) | 0 |
| Funções com daisy-chain | 1 (`etl-bigquery-ingest`) | 0 (ou movido para Python) |
| Webhooks Polp | 2 | 1 |
| Comentários enganosos em config.toml | 1 (`match-columns` no auth gate) | 0 |
| Helpers em `_shared/` | 8 | 9-10 (adicionar `blu_schema_matcher` se Fase 3.2) |
| `reg_jobs` jobs sem propósito | 1 (refresh_dashboards EF) | 0 (mover para pg_cron) |
| EFs com `verify_jwt=false` + auth gate | 14 | 14 (manter — é o padrão) |
| RED tests no auth | 7 | 0 |

---

## 7. Riscos globais

| Risco | Prob. | Impacto | Mitigação |
|---|---|---|---|
| Auth fix 0.1 quebra fluxos OAuth (Google, Microsoft, Apple) | Média | Alto | Adicionar teste E2E que cobre todos os 4 fluxos antes de mergir |
| Trigger 0.2 duplica criação de `clientes_blu` (race com `ensure_tenant_row`) | Baixa | Médio | `ON CONFLICT (external_user_id) DO NOTHING` no `handle_new_auth_user` já é idempotente |
| Mover match-columns para Python quebra frontend (Fase 3.2) | Média | Médio | Testes comparativos com 20+ fontes reais antes de mergir |
| Polp webhook consolidation quebra live (Fase 2.1) | Baixa | Crítico | Janela de manutenção, dual-write por 1 release |
| Renomear `run-csv-etl` (Fase 1.2) quebra callers | Média | Baixo | Grep todos os callers antes, atualizar todos atomicamente |
| Daisychain do `etl-bigquery-ingest` refator causa regression | Alta | Alto | NÃO fazer sem antes validar com o dataset de 119k Polen rows |

---

## 8. Não-objetivos

- Migração completa para Python de todos os EFs
- Reescrita de qualquer serviço Python existente
- Mudanças em RLS, `get_my_client_id`, ou schema de DB (exceto a migration do trigger da Fase 0.2)
- Reorganização dos `services/` em microsserviços
- Mudança de auth (MFA, ES256) — fora do escopo deste plano

---

## 9. Sequência de execução recomendada

1. **Fase 0.1** — Auth fix (P0, 1 PR pequeno) — destrava 7 RED tests
2. **Fase 0.2** — Trigger recreation (P0, 1 migration + 1 PR pequeno) — destrava 1 RED test
3. **Fase 1.1** — Limpar config.toml (hygiene, 1 PR trivial)
4. **Fase 1.2-1.3** — Docs/rename das funções enganosas (1-2 PRs triviais)
5. **Fase 2.0-2.1** — Polp consolidation (depende de investigação manual)
6. **Fase 3.1** — etl-refresh-dashboards → pg_cron (1 PR pequeno)
7. **Fase 3.2-3.3** — match-columns e search-documents para Python (2 PRs médios)
8. **Fase 3.4** — website-intel reavaliação (decisão, não mudança)
9. **Fase 3.5-3.7** — Movimentos longos (opcional, ROI-dependent)
10. **Fase 4.1-4.2** — M7 retry e unificação agenda (alto risco, baixo ROI)

---

## 10. Próximos passos imediatos

1. **Code review** deste plano (1 reviewer)
2. **Aplicar Fase 0.1** (auth fix) — maior ROI do plano, destrava 7 tests
3. **Aplicar Fase 0.2** (trigger recreation) — 1 migration
4. **Iniciar Fase 2.0** (investigação Polp) em paralelo

---

## Apêndice A — Inventário de migrations (4 root + 23 applied = 27)

### Root (`supabase/migrations/`)

| File | LOC | Summary |
|---|---|---|
| `20260523999999_baseline_v2.sql` | 5196 | BASELINE v2 — schema completo (9 extensions, ~80 tables, 200+ RPCs, RLS, MVs). Inclui `handle_new_auth_user` (L2975) sem trigger. |
| `20260602000000_agent_lists.sql` | 72 | Generic persistent list store (replaces ad-hoc tables) |
| `20260604_onboarding_complete_fix.sql` | 36 | Fix `onboarding_complete` routine step 3 (on_failure=continue) + step 4 (knowledge.fill_masterprompt) |
| `20260625000001_fix_finance_indicators.sql` | 94 | BKL-024: implement `analytics_v2.get_finance_indicators` RPC body |

### Applied (`supabase/migrations/applied/`)

23 files, 2.557 LOC total. Highlights:
- `20260525_p0_fix_integration_tokens_rls.sql` — P0 fix
- `20260525_p3_2_drop_dead_password_auth.sql` — drop dead `verify_tenant_password`
- `20260525_p3_lockdown_secdef.sql` — lockdown SECURITY DEFINER functions
- `20260525_p4_rls_remaining_tables.sql` — RLS hardening
- `20260525_p11_tenant_wipe_worker.sql` — async paginated tenant deletion
- `20260525_p12_split_onboarding_completion.sql` — bootstrap ≠ finalize
- `20260601_agent_sessions_table.sql` — agent_sessions for agent_api
- `20260625_p13_is_onboarded_client.sql` — `is_onboarded_client()` RPC + backfill

---

## Apêndice B — Test inventory

- `tests/behaviors/`: **123 files** (incluindo 14+ específicos do auth: `b1_fluxo_signup`, `b1_trigger_on_auth_user_created`, `b2_signup_sessao_ativa`, `b2_reproduzir_erro_capturar_logs`, etc.)
- `tests/integration/`: 4 files (`test_sequential_signups.py` é o mais crítico — 4 RED tests esperando Fase 0.1)
- `tests/unit/`: 5 files
- `supabase/functions/onboarding-website-intel/index_test.ts`: 11 Deno tests (added in PR #210)
- `supabase/functions/_shared/fernet.test.ts`: 10 Deno tests
- `supabase/functions/onboarding-bootstrap/tests/mappers_test.ts`: 84 LOC Deno (pure module)

---

## Apêndice C — Convenções e padrões a manter (de `.github/skills/supabase`)

1. `verify_jwt = true` é a postura segura padrão; `verify_jwt = false` é exceção e precisa de justificativa
2. EFs com `verify_jwt = false` que atendem user-facing devem usar `requireAuth` de `_shared/blu_auth.ts`
3. Service-role só depois de auth check confirmado
4. `get_my_client_id()` no SQL para tenant scoping
5. EFs de sistema (chamadas por pg_net/cron) usam `isSystemInvocation` + `BLU_SYSTEM_INVOKE_KEY` ou `SUPABASE_SERVICE_ROLE_KEY`
6. SECURITY INVOKER para RPCs user-facing; SECURITY DEFINER só para admin
7. Toda migration de RLS ou `reg_jobs` schema precisa rodar `supabase db advisors` antes de commit

---

**Última atualização:** 2026-06-25 (após merge da main)
**Próxima revisão:** após merge da Fase 0.1
