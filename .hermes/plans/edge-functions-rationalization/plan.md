# Plano: Racionalização das Edge Functions do Supabase

**Status:** Draft v1
**Owner:** TBD
**Prazo:** Sem prazo firme — qualidade > velocidade
**Estratégia:** Em ondas (cada fase mergeável e rollbackável independentemente)
**Estimativa total:** ~3.580 LOC afetadas (de 8.115 LOC = 44%), distribuídos em ~5 fases de 1 dia a 2 semanas cada.

---

## 0. Contexto e problema

`sus supabase/functions/` contém **26 edge functions e 8.115 LOC**. A análise estática (ver `docs/plans/edge-functions-rationalization-context.md` se criado, ou reler o relatório exploratório completo) identificou 4 problemas:

1. **Código morto** — referência a um EF (`enrich-metadata`) que foi absorvido por `process-document` mas continua no `config.toml` (L107-110).
2. **Duplicação interna** — 6 funções compartilham o mesmo helper Fernet (~250 LOC copiadas); 2 pares de funções (BQ discover/preview, sync-etl/run-csv-etl) compartilham 80–100% do código.
3. **Duplicação cross-runtime** — 2 implementações paralelas da mesma integração Polp/Open Finance (TS com vocabulário Polp atual + Python com vocabulário legado Pluggy) e do mesmo context report (TS EF + Python routine).
4. **Edge functions usadas por hábito** — funções que rodam por minutos (BQ ETL), funções de pura computação (match-columns), ou funções que só servem como wrapper SQL+1 chamada externa (etl-refresh-dashboards, search-documents).

**Princípio orientador** (herdado da skill `.github/skills/supabase`):
- Edge functions são apropriadas para: tempo < 60s, runtime isolated, validação JWT antes do body, ou URL pública como `redirect_uri` OAuth.
- Edge functions são **inadequadas** para: ETL longo, computação que poderia ser SQL, computação cliente, lógica de negócio em Python que já tem framework.

---

## 1. Decisões já tomadas

| ID | Decisão | Origem |
|---|---|---|
| D1 | Formato do plano: `docs/plans/edge-functions-rationalization.md` | Resposta do usuário |
| D2 | Execução em ondas (não big-bang, não vertical slice) | Resposta do usuário |
| D3 | **M6 (Polp webhook):** consolidar as 2 implementações da integração Polp/Open Finance em 1 runtime canônico; investigar logs do Polp dashboard antes de escolher | Resposta do usuário |
| D4 | **M7 (context-report):** manter Python `context_report.py`, **matar o EF** `generate-context-report` | Resposta do usuário |
| D5 | Sem prazo; cada fase revisada e testada antes de avançar | Resposta do usuário |

---

## 2. Fases

Cada fase é um conjunto de PRs pequenos (1-3 PRs) que pode ser mergeada e revertida de forma independente. A numeração abaixo é a **ordem de execução**, não de dependência rígida — fases dentro de uma mesma onda podem ser paralelizadas entre pessoas.

### Onda 1 — Quick wins + auth fixes (~1-2 dias, zero risco de runtime)

#### Fase 1.1 — Fechar buracos de auth e remover código morto

**Justificativa:** 2 funções estão completamente abertas (sem auth) e 1 referência morta no config. Tudo isso é hygiene sem mudança de comportamento para usuários legítimos.

| # | Tarefa | Arquivos | LOC |
|---|---|---|---|
| 1.1.1 | Adicionar `requireAuth` em `match-columns/index.ts` (validar Bearer + `verify_jwt=true` para chamadas frontend; service-role para EF-to-EF) | `supabase/functions/match-columns/index.ts`, `supabase/config.toml` (L78) | ~+15 |
| 1.1.2 | Adicionar `requireAuth` em `onboarding-website-intel/index.ts` (ou mover para client-side — ver Fase 3.2) | `supabase/functions/onboarding-website-intel/index.ts` | ~+5 |
| 1.1.3 | Remover bloco `[functions.enrich-metadata]` do `supabase/config.toml` (L107-110) | `supabase/config.toml` | -4 |
| 1.1.4 | Atualizar `HERMES.md` L333 para remover `enrich-metadata` e adicionar nota sobre match-columns agora autenticado | `HERMES.md` | ~±5 |

**Critérios de done:**
- `supabase functions deploy` aceita o config sem warnings.
- `match-columns` retorna 401 para chamadas sem Bearer; chamadas com Bearer de service-role ou user JWT continuam funcionando.
- `onboarding-website-intel` retorna 401 para chamadas sem Bearer; wizard do frontend (`OnboardingApp.tsx:491`) continua funcionando (usa o user JWT).
- CI verde.

**Risco:** Mínimo. Mudanças em auth são testáveis com curl.

---

#### Fase 1.2 — Helper Fernet compartilhado (M8)

**Justificativa:** O helper Fernet (Web-Crypto base64url + encrypt) está copiado verbatim em 6 arquivos. Extrair para `_shared/fernet.ts` é refactor puro — zero mudança de comportamento, ~250 LOC a menos.

| # | Tarefa | Arquivos | LOC |
|---|---|---|---|
| 1.2.1 | Criar `supabase/functions/_shared/fernet.ts` com `fernetEncrypt`, `fernetDecrypt`, `base64urlEncode`, `base64urlDecode`, `concatBytes` | `supabase/functions/_shared/fernet.ts` (novo) | +200 |
| 1.2.2 | Substituir implementações locais em: `google-oauth-callback`, `onboarding-capture-drive-token`, `save-api-token`, `google-calendar-events`, `get-monday-subitems`, `get-agenda-events` | 6 arquivos | -250 |
| 1.2.3 | Adicionar smoke test em `tests/` que cifra e decifra um payload em ambos os formatos (Web-Crypto custom + `npm:fernet`) | `tests/test_fernet_helper.py` ou `tests/edge-functions/fernet.test.ts` | +60 |

**Critérios de done:**
- `fernetEncrypt("secret", "plaintext")` produz output idêntico à implementação antiga.
- Tokens de integração já gravados em `integration_tokens.encrypted_token` continuam decifrando sem migração.
- Os 6 callers passam no smoke test.

**Risco:** Baixo. Compatibilidade de output é o único invariante crítico.

---

### Onda 2 — Merges internos (~1-2 semanas)

#### Fase 2.1 — Merge BQ discover/preview (M2)

**Justificativa:** `discover-bigquery-columns` (175 LOC) e `preview-bigquery-columns` (78 LOC) chamam o mesmo `getBigQuerySchema` com 95% do código idêntico. Diferença: `discover` escreve em DB, `preview` é read-only. Unificar com `?preview=true`.

| # | Tarefa | Arquivos | LOC |
|---|---|---|---|
| 2.1.1 | Adicionar `?preview=true` em `discover-bigquery-columns`; quando `preview=true`, pular writes em `client_data_sources` e `bigquery_foreign_tables` e não chamar `create_bigquery_foreign_table_from_schema` | `supabase/functions/discover-bigquery-columns/index.ts` | +30 |
| 2.1.2 | Atualizar `OnboardingApp.tsx:287` para chamar `discover-bigquery-columns?preview=true` no passo "Mapear colunas" | `apps/blu_v3/src/api/connectors.ts` | -10 |
| 2.1.3 | Atualizar `OnboardingApp.tsx:1583` para chamar `discover-bigquery-columns` (sem flag) no passo final | idem | -5 |
| 2.1.4 | Deletar `supabase/functions/preview-bigquery-columns/` inteira (incluindo `config.toml`) | deletar | -78 |
| 2.1.5 | Remover bloco `[functions.preview-bigquery-columns]` em `supabase/config.toml` (L62-66) | `supabase/config.toml` | -5 |

**Critérios de done:**
- Wizard completa o passo "Mapear colunas" usando apenas `discover-bigquery-columns`.
- Nenhuma regressão em `client_data_sources` ou `bigquery_foreign_tables`.

**Risco:** Baixo. É uma refatoração 1:1.

---

#### Fase 2.2 — Extrair `enqueue_sync_job` (M3)

**Justificativa:** `run-sync-etl` (184 LOC) e `run-csv-etl` (305 LOC) compartilham 80% do fluxo: auth → ownership → duplicate-guard → persist mapping → enqueue `reg_jobs` row → return `job_id`. Diferença: `run-csv-etl` baixa o arquivo de Storage e faz parse (CSV/XLSX) para staging.

| # | Tarefa | Arquivos | LOC |
|---|---|---|---|
| 2.2.1 | Criar `supabase/functions/_shared/enqueue_sync_job.ts` com `enqueueSyncJob({jobType, clientId, sourceId, columnMapping, forceFull})` retornando `{job_id, status: 'pending'}` ou erro 409 | `_shared/enqueue_sync_job.ts` (novo) | +60 |
| 2.2.2 | Reescrever `run-sync-etl/index.ts` para chamar o helper (sobram só auth + ownership) | `supabase/functions/run-sync-etl/index.ts` | -100 |
| 2.2.3 | Reescrever `run-csv-etl/index.ts` para chamar o helper depois do parse + staging | `supabase/functions/run-csv-etl/index.ts` | -50 |

**Critérios de done:**
- Comportamento de duplicate-guard preservado (409 quando já existe `pending|running` job para o mesmo `(client_id, source_id)`).
- Mapeamento de colunas persistido antes do enqueue.
- `reg_jobs.input_params` schema idêntico ao atual.

**Risco:** Baixo. Não toca dispatcher nem SQL.

---

#### Fase 2.3 — Merge upload-csv + upload-drive (M4)

**Justificativa:** `upload-csv-source` (251 LOC) e `upload-drive-source` (323 LOC) compartilham parse → upload Storage → upsert `client_data_sources` → chamar `match-columns`. Diff é só o `fetch_fn` (multipart vs. Drive export).

| # | Tarefa | Arquivos | LOC |
|---|---|---|---|
| 2.3.1 | Criar `supabase/functions/_shared/intake_file.ts` com `intakeFile({fetchFn, fileMeta, sourceType, resourceType})` retornando `{sourceId, suggestedMapping, needsReview}` | `_shared/intake_file.ts` (novo) | +180 |
| 2.3.2 | Reescrever `upload-csv-source/index.ts` para usar `intakeFile` com `fetchFn = multipart` | `supabase/functions/upload-csv-source/index.ts` | -150 |
| 2.3.3 | Reescrever `upload-drive-source/index.ts` para usar `intakeFile` com `fetchFn = driveExportOrDownload` | `supabase/functions/upload-drive-source/index.ts` | -200 |

**Critérios de done:**
- Wizard "Enviar CSV" e "Conectar Google Drive" completam end-to-end.
- `client_data_sources` schema preservado (`source_type` ainda discrimina csv vs google_drive).
- Drive cap de 20MB mantido.

**Risco:** Baixo-médio. Drive tem mais edge cases (Sheets → XLSX export).

---

#### Fase 2.4 — Merge google-oauth-callback + onboarding-capture-drive-token (M1)

**Justificativa:** Ambos fazem Fernet encrypt + upsert `integration_tokens` + enable `calendar_settings`. Diff: um é OAuth-redirect (com `state` blob), outro é wizard-paste (com `requireAuth`).

| # | Tarefa | Arquivos | LOC |
|---|---|---|---|
| 2.4.1 | Criar `supabase/functions/_shared/store_google_token.ts` com `storeGoogleToken({clientId, provider, accountEmail, refreshToken, accessToken, scope})` | `_shared/store_google_token.ts` (novo) | +60 |
| 2.4.2 | Reescrever `google-oauth-callback` para usar o helper (mantém o `state` blob + token exchange) | `supabase/functions/google-oauth-callback/index.ts` | -60 |
| 2.4.3 | Reescrever `onboarding-capture-drive-token` para usar o helper (mantém o `requireAuth` + ownership check) | `supabase/functions/onboarding-capture-drive-token/index.ts` | -80 |

**Critérios de done:**
- OAuth roundtrip Google continua funcionando (smoke test manual ou Playwright).
- Wizard landing com paste de refresh_token continua funcionando.
- Tokens gravados são decifráveis por `google-calendar-events` e outros.

**Risco:** Médio. Fluxo OAuth é difícil de testar de forma totalmente automatizada.

---

### Onda 3 — Eliminações e movimentos para o runtime certo (~2-3 semanas)

#### Fase 3.1 — Consolidar as 2 implementações do webhook Polp/Open Finance (M6)

**Contexto:** Polp é a integração live com Open Finance (não código morto). Hoje ela tem 2 implementações paralelas:
- `supabase/functions/polp-webhook/index.ts` — vocabulário Polp atual (`integrations.updated`, `accounts.synchronized`, `transactions.created/updated/deleted`, `bills.created/updated`), segredo `POLP_WEBHOOK_SECRET`, header `X-Polp-Signature`.
- `services/tool_pool_api/src/tool_pool_api/api/polp_webhook_router.py` — vocabulário legado do Pluggy (`item/updated`, `transaction/created`, `account/updated`), segredo `PLUGGY_WEBHOOK_SECRET`, header `X-Pluggy-Signature`. Provavelmente é resíduo da migração Pluggy → Polp.

**Pré-requisito:** Investigação de logs. Ver seção 3.

**Tarefas (após decisão):**
- Se **TS polp-webhook vence** (esperado — vocabulário atual): deletar `services/tool_pool_api/src/tool_pool_api/api/polp_webhook_router.py` (~267 LOC), remover import de `services/tool_pool_api/src/tool_pool_api/main.py`, remover segredo `PLUGGY_WEBHOOK_SECRET` da env, deletar documentação/menções em `HERMES.md`.
- Se **Python polp_webhook_router vence** (improvável): deletar `supabase/functions/polp-webhook/` (~375 LOC), remover bloco `[functions.polp-webhook]` do config, reescrever configuração do Polp dashboard para apontar para `https://<tool_pool_api>/webhooks/polp`.

**Critérios de done:**
- Polp dashboard aponta para 1 único webhook canônico.
- Tabela `polp_webhook_events` continua sendo populada pelo webhook sobrevivente.
- Nenhum log de `404 webhook not found` nas últimas 24h em produção.
- A integração Polp/Open Finance continua funcionando (criar conexão de teste, ver eventos chegarem).

**Risco:** Médio. Mudança de URL no Polp dashboard; precisa de janela de manutenção se ambos forem atingidos por um tempo durante a transição.

---

#### Fase 3.2 — Mover `onboarding-website-intel` para client-side

**Justificativa:** É 100ms de regex + fetch + 1 JSON de retorno. Não toca DB, não toca secrets, não precisa de auth. Pode ser uma util de 50 linhas no `apps/landing/` (ou `apps/blu_v3/` se for consumido por ambos).

| # | Tarefa | Arquivos | LOC |
|---|---|---|---|
| 3.2.1 | Portar `normalizeUrl`, `stripHtml`, `detectVertical`, `suggestFromVertical` para `apps/blu_v3/src/lib/onboarding-website-intel.ts` (ou `apps/landing/src/lib/`) | novo arquivo | +120 |
| 3.2.2 | Atualizar `OnboardingApp.tsx:491` para chamar a util local em vez de `supabase.functions.invoke` | `apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx` | -3 |
| 3.2.3 | Deletar `supabase/functions/onboarding-website-intel/` | deletar | -136 |
| 3.2.4 | Adicionar teste unitário da util (input HTML → vertical detection) | `apps/blu_v3/src/lib/__tests__/onboarding-website-intel.test.ts` | +50 |

**Critérios de done:**
- Wizard "Conte sobre seu negócio" completa usando a util client-side.
- Vertical detection tem a mesma accuracy (smoke test com 3-5 sites reais).
- Fetch com timeout de 5s.

**Risco:** Baixo. Lógica determinística.

---

#### Fase 3.3 — Mover `etl-refresh-dashboards` para `pg_cron`

**Justificativa:** É 1 chamada RPC `refresh_client_dashboards(p_client_id)`. Edge function é overhead puro.

| # | Tarefa | Arquivos | LOC |
|---|---|---|---|
| 3.3.1 | Nova migration: estender `analytics_v2.process_pending_jobs` para também processar `job_type='refresh_dashboards'` (chamar `refresh_client_dashboards(reg_jobs.client_id)`) | `supabase/migrations/<ts>_refresh_dashboards_in_dispatcher.sql` | +30 |
| 3.3.2 | Garantir que `pg_cron` agenda a função atualizada (já está, ver `20260526090000_g1_dispatcher_tuning.sql`) | nenhum | 0 |
| 3.3.3 | Deletar `supabase/functions/etl-refresh-dashboards/` | deletar | -132 |
| 3.3.4 | Remover bloco `[functions.etl-refresh-dashboards]` do config | `supabase/config.toml` | -6 |

**Critérios de done:**
- `REFRESH MATERIALIZED VIEW CONCURRENTLY` continua rodando para os 4 MVs.
- `reg_jobs` rows de tipo `refresh_dashboards` são processados pelo dispatcher SQL.
- Logs do `process_pending_jobs` mostram a chamada RPC.

**Risco:** Baixo. Mudança é puramente SQL.

---

#### Fase 3.4 — Mover `match-columns` para `services/` Python

**Justificativa:** Dice coefficient + alias table é CPU-bound trivial. Movê-lo para Python remove a necessidade de deploy edge function para essa lógica e elimina a dependência `npm:string-similarity`.

| # | Tarefa | Arquivos | LOC |
|---|---|---|---|
| 3.4.1 | Criar `services/blu_schema_matcher/` (ou módulo dentro de `tool_pool_api`) com `match_columns(source_columns, target_table)` retornando `{matched, unmatched, needs_review, confidence_scores, detected_context}` | novo | +500 |
| 3.4.2 | Reescrever `upload-csv-source` e `upload-drive-source` (já refatorados na Fase 2.3) para chamar `services/blu_schema_matcher` via HTTP em vez de `supabase.functions.invoke('match-columns')` | 2 EFs | -10 |
| 3.4.3 | Atualizar `services/tool_pool_api/.../context_module.py:521` para usar o módulo local em vez de chamar o EF | 1 arquivo Python | -5 |
| 3.4.4 | Deletar `supabase/functions/match-columns/` | deletar | -487 |
| 3.4.5 | Adicionar testes unitários em `tests/test_schema_matcher.py` | novo | +200 |

**Critérios de done:**
- Wizard completa o passo "Mapear colunas" usando o serviço Python.
- Output idêntico ao EF anterior (testes comparativos com 20+ fontes reais).
- Aliases e context-specific mappings preservados.

**Risco:** Médio. Precisa de cobertura de teste ampla para garantir equivalência de output.

---

#### Fase 3.5 — Mover `search-documents` para direct SQL + Cohere no Python RAG

**Justificativa:** É wrapper fino sobre `vector_db.match_documents` / `vector_db.hybrid_match_documents` + 1 chamada Cohere. Pode ser inlined no `services/blu_rag_factory/.../retriever.py`.

| # | Tarefa | Arquivos | LOC |
|---|---|---|---|
| 3.5.1 | Em `services/blu_rag_factory/src/.../retriever.py`: substituir a chamada `supabase.functions.invoke('search-documents')` por `cohere.embed()` direto + `supabase.rpc('vector_db.hybrid_match_documents', {...})` | 1 arquivo Python | ±20 |
| 3.5.2 | Verificar que o SQL RPC `hybrid_match_documents` aceita todos os filtros que o EF repassava (scope, categories, document_ids, themes) | revisão | 0 |
| 3.5.3 | Deletar `supabase/functions/search-documents/` | deletar | -212 |
| 3.5.4 | Remover bloco `[functions.search-documents]` do config | `supabase/config.toml` | -5 |

**Critérios de done:**
- `services/blu_rag_factory` continua retornando os mesmos documentos.
- Latência p95 dentro de ±10% do EF anterior.
- Teste comparativo com 5 queries reais em 3 clientes.

**Risco:** Médio. SQL RPC precisa ter grants corretos para o service-role do RAG factory.

---

### Onda 4 — M7 + movimentos longos (várias semanas)

#### Fase 4.1 — Matar EF `generate-context-report` (M7)

**Justificativa (D4):** Python `libs/blu_agent_framework/.../context_report.py` é o original auditado, tem jinja2 templating, tem shared-memory write-back, e tem audit log. O EF é um port verbatim. Manter o Python e matar o EF.

**Callers atuais do EF:**
- `supabase/migrations/20260523999999_baseline_v2.sql:4147` — `schedule_monthly_context_reports` (pg_cron mensal) → `net.http_post` para o EF
- `supabase/functions/onboarding-bootstrap/index.ts:159-179` — `EdgeRuntime.waitUntil` (best-effort, no submit do wizard)
- `HERMES.md:333` — doc

**O `agent_api` já tem o routine function wired:**
- `services/agent_api/src/agent_api/core/routine_functions.py:223` chama `run_for_client` do `context_report.py` via `analytics.generate_context_report`.

| # | Tarefa | Arquivos | LOC |
|---|---|---|---|
| 4.1.1 | Adicionar endpoint `POST /v1/internal/context-report/run` em `services/agent_api/src/agent_api/api/routines_router.py` (aceita `{client_id}`, requer Bearer service-role) | 1 arquivo | +30 |
| 4.1.2 | Nova migration: reescrever `schedule_monthly_context_reports` (do `baseline_v2.sql:4127-4157`) para chamar o novo endpoint via `net.http_post` (com URL configurada em `app.agent_api_url` setting) | `supabase/migrations/<ts>_context_report_via_agent_api.sql` | +30 |
| 4.1.3 | Atualizar `supabase/functions/onboarding-bootstrap/index.ts:159-179` para chamar `${AGENT_API_URL}/v1/internal/context-report/run` em vez do EF | 1 arquivo | -5 |
| 4.1.4 | Adicionar setting `app.agent_api_url` via nova migration (similar ao `app.supabase_url` que já existe) | nova migration | +15 |
| 4.1.5 | Adicionar `app.agent_api_url` à config de produção (env var `AGENT_API_URL`) | `supabase/config.toml` + env | 0 |
| 4.1.6 | Deletar `supabase/functions/generate-context-report/` | deletar | -610 |
| 4.1.7 | Remover bloco `[functions.generate-context-report]` do config | `supabase/config.toml` | -6 |
| 4.1.8 | Atualizar `HERMES.md` L333 para remover `generate-context-report` e listar o endpoint Python | `HERMES.md` | ~±5 |

**Critérios de done:**
- Relatório mensal continua sendo gerado e aparecendo no Storage + vector DB.
- Wizard onboarding dispara o relatório via agent_api (best-effort, mesmo comportamento de skip).
- `reg_jobs.input_params` com `client_id` chega corretamente.
- Shared memory e audit log do Python continuam sendo escritos.
- `tests/test_context_report.py` continua passando.

**Risco:** Médio. Mudança na URL base do cron, precisa de:
- Validação que `net.http_post` no Postgres pode chamar o agent_api (CORS, network).
- Validação que o `app.agent_api_url` setting é propagado para o Postgres runtime.

---

#### Fase 4.2 — Mover `etl-bigquery-ingest` para Python worker

**Justificativa:** BQ scans podem levar 2-10 minutos. O cap de 60s do edge runtime força a complexidade do daisy-chain (40 LOC de `EdgeRuntime.waitUntil` + `chain_attempts` em `etl-bigquery-ingest/index.ts:338-376`). Python em `services/etl_worker/` elimina isso.

| # | Tarefa | Arquivos | LOC |
|---|---|---|---|
| 4.2.1 | Criar `services/etl_worker/` com consumer que puxa `reg_jobs` rows tipo `bigquery_sync` | novo | +200 |
| 4.2.2 | Portar `queryBigQueryPaginated` para Python (`google-cloud-bigquery`) | novo módulo | +200 |
| 4.2.3 | Portar lógica de staging → `apply_staging_to_facts` para Python (mantendo md5 + ON CONFLICT) | novo | +150 |
| 4.2.4 | Reescrever `analytics_v2.process_pending_jobs` para chamar o worker Python (HTTP) em vez do EF | migration | +20 |
| 4.2.5 | Deletar `supabase/functions/etl-bigquery-ingest/` | deletar | -491 |
| 4.2.6 | Remover bloco `[functions.etl-bigquery-ingest]` do config | `supabase/config.toml` | -6 |

**Critérios de done:**
- BQ sync end-to-end completa sem daisy-chain.
- `reg_jobs` status transitions (`pending → running → completed/failed`) preservados.
- Idempotência de `apply_staging_to_facts` preservada (testes comparativos).
- 119k-row Polen dataset completa em < 10min (atualmente bounded por daisy-chain).

**Risco:** Alto. É o EF mais complexo. Mudança grande de runtime. **Avaliar se vale a pena — se o daisy-chain atual funciona, talvez a dívida técnica não justifique o trabalho.**

---

#### Fase 4.3 — Mover `routine-builder` para `services/agent_api/`

**Justificativa:** SSE + Anthropic + chat history são first-class Python concerns. O `agent_api` já tem o pattern de streaming chat.

| # | Tarefa | Arquivos | LOC |
|---|---|---|---|
| 4.3.1 | Adicionar endpoint streaming `POST /v1/agents/routine-builder/chat` em `services/agent_api/.../agents_router.py` (ou novo router) | 1 arquivo | +200 |
| 4.3.2 | Portar system prompt (carrega `agent_catalog` + `agent_action_catalog`) | 1 arquivo | +30 |
| 4.3.3 | Atualizar frontend para usar o endpoint streaming do agent_api em vez de `supabase.functions.invoke('routine-builder')` | `apps/...` | ~±20 |
| 4.3.4 | Deletar `supabase/functions/routine-builder/` | deletar | -190 |
| 4.3.5 | Remover bloco `[functions.routine-builder]` do config | `supabase/config.toml` | -5 |

**Critérios de done:**
- UX do chat streaming idêntica.
- JSON `routine` block extraído corretamente da resposta do Claude.
- AAL2 enforcement preservado.

**Risco:** Médio. Mudança de protocolo (SSE over fetch vs `supabase.functions.invoke`).

---

#### Fase 4.4 — Mover `polp-sync` para Python ou reusar webhook (Opcional)

**Justificativa:** Loop sequencial de 750+ chamadas HTTP. Python async seria mais rápido. Alternativa: o webhook já faz a sync em `accounts.synchronized`; o botão "↻" no AdminScreen poderia disparar um evento sintético.

| # | Tarefa | Arquivos | LOC |
|---|---|---|---|
| 4.4.1 (A) | Reescrever `polp-sync` em Python em `services/polp_sync/`, fazer chamadas paralelas | novo | +200 |
| OU 4.4.1 (B) | Botão "↻" chama endpoint que dispara evento sintético `accounts.synchronized` para o webhook | refactor frontend | +30 |
| 4.4.2 | Deletar `supabase/functions/polp-sync/` | deletar | -147 |
| 4.4.3 | Remover bloco `[functions.polp-sync]` do config | `supabase/config.toml` | -5 |

**Critérios de done:**
- Botão "↻" completa full sync em < 30s para um cliente típico.
- Polp rate limits respeitados.

**Risco:** Médio. (A) tem risco de Python async mal calibrado; (B) requer Polp aceitar eventos sintéticos (pode não ser o caso).

---

### Onda 5 — Last mile: agenda merge (M5, opcional)

#### Fase 5.1 — Unificar `get-agenda-events` + `google-calendar-events` + `get-monday-subitems`

**Justificativa:** Os 3 endpoints servem o mesmo "feed unificado de eventos" mas em escopos diferentes. Maior economia de LOC (~700), mas é o refactor mais arriscado porque o frontend chama os 3 endpoints separadamente em lugares diferentes (`apps/blu_v3/src/api/agenda.ts:264, 276` e `apps/blu_v3/src/api/analytics.ts:294`).

| # | Tarefa | Arquivos | LOC |
|---|---|---|---|
| 5.1.1 | Adicionar `?sources=calendar,monday,notion&include_subitems=true&lazy_subitem_id=...` em `get-agenda-events` | 1 arquivo | +50 |
| 5.1.2 | Mover `fetchGoogleCalendarEvents` e `fetchMondaySubitems` para `_shared/agenda_sources.ts` | `_shared/agenda_sources.ts` (novo) | +200 |
| 5.1.3 | Reescrever `google-calendar-events` e `get-monday-subitems` como thin shims que chamam o helper e reformatam | 2 arquivos | -250 |
| 5.1.4 | Frontend: unificar as 3 chamadas em 1 (com params), preservar comportamento lazy-load do Gantt | `apps/...` | ~±40 |
| 5.1.5 | Deletar `google-calendar-events/` e `get-monday-subitems/` (depois de 1 release de shim) | deletar | -529 |
| 5.1.6 | Remover blocos do config | `supabase/config.toml` | -10 |

**Critérios de done:**
- Agenda card renderiza igual.
- MonthlyGantt lazy-load ainda funciona (subitems carregam sob demanda).
- analytics.ts:294 (`google-calendar-events` chamado do analytics page) continua funcionando.

**Risco:** Alto. 3 endpoints consumidos em 4+ lugares no frontend. Regressão silenciosa fácil.

**Recomendação:** Avaliar se vale a pena. Se a separação atual for útil (ex.: Gantt só quer Monday, agenda quer tudo), os shims são fine. **Pular esta fase se as outras entregarem valor suficiente.**

---

## 3. Investigação pré-Fase 3.1 (M6 — escolher runtime canônico do webhook Polp)

**Objetivo:** Determinar qual das 2 implementações do webhook Polp/Open Finance está recebendo eventos em produção. A integração Polp em si é live; a questão é qual runtime (Supabase Edge ou Python FastAPI em `tool_pool_api`) é o canônico.

| # | Tarefa | Como | Quem |
|---|---|---|---|
| 3.0.1 | Buscar logs do Supabase Edge runtime para `polp-webhook` (últimos 30 dias) | Supabase dashboard → Edge Functions → Logs | Eng |
| 3.0.2 | Buscar logs do `services/tool_pool_api` (FastAPI access log) para `/webhooks/polp` (últimos 30 dias) | Fly/Render logs, ou `journalctl` no host | Eng |
| 3.0.3 | Contar `event_type` distintos recebidos em cada um (`integrations.updated` vs `item/updated`) | `SELECT event_type, COUNT(*) FROM polp_webhook_events WHERE ... GROUP BY event_type` | Eng |
| 3.0.4 | Checar config no Polp dashboard: qual URL está registrada? | Painel Polp | Ops |
| 3.0.5 | Decidir: TS (esperado) ou Python vence | baseado em 3.0.1-3.0.4 | Owner |

**Critério de parada:** Se ambos receberem eventos nos últimos 30 dias, investigar por que (pode ser redirect ou re-configuração pendente do Polp).

---

## 4. Métricas de sucesso globais

| Métrica | Baseline | Target após todas as fases |
|---|---|---|
| Total de edge functions | 26 | 12-14 |
| Total LOC em `supabase/functions/` | 8.115 | ~4.500 |
| Funções com `verify_jwt=false` sem auth | 2 (`match-columns`, `onboarding-website-intel`) | 0 |
| Helper Fernet duplicado | 6 cópias | 1 |
| Edge functions > 500 LOC | 4 | ≤1 (`process-document`) |
| Webhook Polp/Open Finance implementations | 2 | 1 (mesma integração live consolidada em 1 runtime) |
| Context report implementations | 2 (TS + Python) | 1 (Python) |
| Daisy-chain complex code (etl-bigquery-ingest) | ~40 LOC | 0 (se Fase 4.2 executada) |

---

## 5. Riscos e mitigações globais

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Quebrar fluxo OAuth Google em produção | Média | Alto | Smoke test manual após cada fase OAuth; manter ability de rollback por 1 release |
| Regressão em dispatcher ETL | Baixa | Crítico | Migration com `BEGIN; ... ROLLBACK` se teste falhar; rodar dispatcher 1x manualmente antes de deletar EF |
| Mover lógica para runtime errado criar nova dívida | Média | Médio | Cada movimento de runtime precisa de PR separado com justificativa de capacidade (60s edge vs Python) |
| Mudança de URL Polp webhook durante transição M6 | Média | Alto | Investigar logs PRIMEIRO (Fase 3.0); janelão de manutenção se necessário |
| Testes de carga revelarem que `process-document` também precisa de worker Python | Baixa | Médio | Avaliar após Fase 4.2; se acontecer, abrir Fase 4.5 |
| _shared/ refactor quebrar compat de tokens Fernet já gravados | Baixa | Crítico | Smoke test obrigatório na Fase 1.2 (round-trip com 1 token real de produção) |

---

## 6. Não-objetivos (out of scope)

- Migração completa para Python de **todos** os EFs.
- Reescrita de qualquer um dos serviços Python existentes.
- Mudanças em RLS, `get_my_client_id`, ou no schema de DB (a não ser migrations explícitas mencionadas).
- Reorganização dos `services/` em microsserviços.
- Mudança de auth (MFA, ES256) — fora do escopo deste plano.

---

## 7. Próximos passos imediatos

1. **Revisar este plano com o time** — owner + 1 reviewer.
2. **Criar issues no GitHub linkando as fases** — 1 issue por fase, labels `refactor`, `edge-functions`.
3. **Abrir PR da Fase 1.1** (quick wins) — primeiro a ser mergeado.
4. **Executar Fase 3.0 (investigação Polp)** em paralelo — bloqueador da Fase 3.1.
5. **Estimativa por fase** — owner de cada fase quebra em sub-tasks (½ dia a 2 semanas cada).

---

## Apêndice A — Inventário completo das 26 funções

| # | Função | LOC | Decisão |
|---|---|---|---|
| 1 | `google-oauth-start` | 85 | Manter (entrada OAuth) |
| 2 | `google-oauth-callback` | 252 | Merge na Fase 2.4 |
| 3 | `onboarding-capture-drive-token` | 237 | Merge na Fase 2.4 |
| 4 | `save-api-token` | 333 | Manter; absorve helper Fernet (Fase 1.2) |
| 5 | `onboarding-bootstrap` | 228 | Manter; redireciona context-report (Fase 4.1) |
| 6 | `onboarding-website-intel` | 136 | Mover para client-side (Fase 3.2) |
| 7 | `website-context-builder` | 486 | Manter |
| 8 | `generate-context-report` | 610 | **Matar** (Fase 4.1) |
| 9 | `discover-bigquery-columns` | 175 | Merge com `preview-` (Fase 2.1) |
| 10 | `preview-bigquery-columns` | 78 | Deletado na Fase 2.1 |
| 11 | `run-sync-etl` | 184 | Extrai helper (Fase 2.2) |
| 12 | `etl-bigquery-ingest` | 491 | Mover para Python (Fase 4.2) — opcional/avaliar |
| 13 | `etl-refresh-dashboards` | 132 | Mover para pg_cron (Fase 3.3) |
| 14 | `run-csv-etl` | 305 | Extrai helper (Fase 2.2) |
| 15 | `upload-csv-source` | 251 | Extrai helper (Fase 2.3) |
| 16 | `upload-drive-source` | 323 | Extrai helper (Fase 2.3) |
| 17 | `process-document` | 715 | Manter (choke point RAG) |
| 18 | `search-documents` | 212 | Mover para direct SQL+Python (Fase 3.5) |
| 19 | `polp-connect` | 136 | Manter |
| 20 | `polp-sync` | 147 | Mover para Python (Fase 4.4) — opcional |
| 21 | `polp-webhook` | 375 | Polp/Open Finance webhook (TS, vocabulário atual). Consolidar (Fase 3.0 + 3.1) |
| — | `services/.../polp_webhook_router.py` | 267 | Polp/Open Finance webhook (Python, vocabulário legado Pluggy). Consolidar (Fase 3.0 + 3.1) |
| 22 | `google-calendar-events` | 360 | Unificar (Fase 5.1) — opcional |
| 23 | `get-monday-subitems` | 169 | Unificar (Fase 5.1) — opcional |
| 24 | `get-agenda-events` | 1018 | Unificar (Fase 5.1) — opcional |
| 25 | `match-columns` | 487 | Mover para Python (Fase 3.4) |
| 26 | `routine-builder` | 190 | Mover para agent_api (Fase 4.3) |

**LOC total:** 8.115 (EFs TS) + 267 (Python polp_webhook) = **8.382 LOC**.
**LOC após plano (excluindo Fase 5.1):** ~4.800 EF TS.
**LOC após plano (incluindo Fase 5.1):** ~4.300 EF TS.

---

## Apêndice B — Convenções e padrões a manter

Estas convenções estão em `.github/skills/supabase/SKILL.md` e devem ser respeitadas em qualquer movimento:

1. `verify_jwt = true` é a postura segura padrão; `verify_jwt = false` é exceção e precisa de justificativa no comentário do config.
2. Edge functions com `verify_jwt = false` que atendem user-facing devem usar `requireAuth` de `_shared/blu_auth.ts`.
3. Service-role só depois de auth check confirmado.
4. `get_my_client_id()` no SQL para tenant scoping; nunca confiar em `client_id` do payload.
5. Edge functions de sistema (chamadas por pg_net/cron) usam `isSystemInvocation` + `BLU_SYSTEM_INVOKE_KEY` ou `SUPABASE_SERVICE_ROLE_KEY`.
6. SECURITY INVOKER para RPCs user-facing; SECURITY DEFINER só para admin.
7. Toda migration de RLS ou `reg_jobs` schema precisa rodar `supabase db advisors` antes de commit.

---

**Última atualização:** 2026-06-25
**Próxima revisão:** Após merge da Fase 1.1.
