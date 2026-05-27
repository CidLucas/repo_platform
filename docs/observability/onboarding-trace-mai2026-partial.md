# Relatório Parcial — Trace de Onboarding (Mai/2026)

**Data:** 25–26/Mai/2026
**Tenant teste:** `cid.lucas@gmail.com` (Lucas Cid, empresa "Polen")
**client_id:** `7db89c8f-f8bc-4465-ba71-ec9295b1df51` (apagado ao fim da sessão)
**Status:** parcial — onboarding não chegou a completar (travou em "Iniciando seu bureau"), apenas etapas 1–3 cobertas

---

## Sumário executivo

Em uma sessão de 1h tentando completar um onboarding ponta-a-ponta com tracing DB + docker logs ativos, identificamos **10 bugs/UX gaps**, sendo **5 críticos**. O bloqueador principal (`prompts_seeded=0/6`) foi rastreado até **inconsistência de namespace entre `agent_catalog.prompt_name` (`agents/<slug>`) e a edge function `onboarding-bootstrap` (que busca em `landing/<slug>`)**. Adicionalmente: o worker P11 de wipe de tenant está quebrado em prod (ambiguidade SQL em `tenant_wipe_tick`).

---

## Timeline da sessão (eventos DB)

```
23:55:53.302  clientes_blu          INSERT  (Supabase Auth trigger → handle_new_auth_user)
23:55:53.332  client_routines       INSERT × 10 (template seed)
23:55:53.360  client_users          INSERT  (vincula user→client)
23:56:02.458  client_routines       UPDATE  last_run_at (daily_insights tick)
23:56:03.352  client_routines       UPDATE  last_run_at (context_report_monthly tick)
00:06:29.111  clientes_blu          UPDATE  (Edge Fn onboarding-bootstrap)
00:06:29.149  client_enabled_agents INSERT × 6 (compras, financeiro, clientes,
                                                agenda, documentos, estrategia)
00:06:29.413  clientes_blu          UPDATE  onboarding_state.langfuse_seed_status
              └─ {seeded: 0, requested: 6, at: 00:06:29.266Z}
```

**Total:** 18 eventos. **Nenhuma chamada chegou em `blu_agent_api` ou `blu_tool_pool_api` durante toda a sessão.** Toda a persistência foi via PostgREST + Edge Function `onboarding-bootstrap`.

---

## Etapas mapeadas

### Passo 1 — Conta (Google OAuth)
- **Frontend:** redirect `/onboarding` → `accounts.google.com/v3/signin` (`client_id 9601...apps.googleusercontent.com`, scope `email profile`, callback `haruewffnubdgyofftut.supabase.co/auth/v1/callback`)
- **Backend Blu:** **0 chamadas** — OAuth bypassa containers Blu
- **DB:** trigger `handle_new_auth_user` insere `clientes_blu` + `client_users` + 10 `client_routines` template
- **Tempo:** ~60ms entre auth.users.created_at e client_users.created_at

### Passo 2 — Empresa (crawl + dados)
- **Crawl:** disparado ao colar URL, **invisível ao tracing atual** (não tocou nenhuma das 19 tabelas instrumentadas; não bateu em containers Blu)
  - Hipótese: edge function `website-context-builder` ou chamada client-side
- **Save incremental:** **inexistente** — wizard mantém tudo em React state até clicar "Avançar" na etapa Dados
- **DB:** 0 eventos durante preenchimento

### Passo 3 — Dados (submit final)
- **Frontend → Edge Function:** POST `/functions/v1/onboarding-bootstrap`
- **Edge Function (síncrona):**
  1. `requireAuth(JWT)` ✅
  2. `ensure_tenant_row()` RPC ✅
  3. `onboarding_bootstrap_tx(payload)` ✅ — UPDATE clientes_blu (nome, profile, policies, **`onboarding_completed_at`**), INSERT × 6 client_enabled_agents
  4. `bootstrap_knowledge_from_onboarding()` ✅ (service role)
  5. `seedLangfusePrompts()` ⚠️ — **0/6 seeded** (ver Bug #5)
  6. `merge_onboarding_state()` ✅ — grava status do seed
  7. `waitUntil()`: website-context-builder + generate-context-report + dispatch_routine_event(`onboarding_complete`) — fire-and-forget
- **UX:** tela "Iniciando seu bureau" travou (provavelmente esperando fetches Langfuse com latência alta)
- **DB:** 8 eventos em 302ms

### Passo 4 — Mapeamento BigQuery
- **Não alcançado.** Após reload (tentando ver o console), o app entrou direto autenticado porque `onboarding_completed_at` já estava setado.
- **BigQuery:** o link inserido na etapa Dados **não persistiu em lugar nenhum** (0 `integration_configs`, 0 `bigquery_servers`, 0 `bigquery_foreign_tables`, 0 vault entries).

---

## Estado final do tenant (antes do wipe)

| Item | Esperado | Atual |
|---|---|---|
| `auth.users` | 1 | 1 ✅ |
| `clientes_blu` (nome_empresa) | "Polen" | "Polen" ✅ |
| `clientes_blu.email` | `cid.lucas@gmail.com` | **NULL** ❌ |
| `clientes_blu.company_profile` | preenchido | ✅ (crawl OK: tagline, industry, employee_count_range) |
| `clientes_blu.onboarding_completed_at` | NULL (etapa 4 pendente) | ⚠️ **setado** prematuramente |
| `client_enabled_agents` | 6 | 6 ✅ |
| `client_routines` (template) | 10 | 10 ✅ |
| `client_routines` (active automáticas) | 3 | 3 ✅ (daily_insights, context_report_monthly, context_report_post_ingestion) |
| `client_routine_executions` (onboarding_complete) | ≥1 | **a verificar — usuário relata não disparado** |
| `integration_configs` | ≥1 (BQ) | **0** ❌ |
| `bigquery_servers` | 1 | **0** ❌ |
| `bigquery_foreign_tables` | N | **0** ❌ |
| `vault.secrets` (tenant) | ≥1 (SA key BQ) | **0** ❌ |
| Langfuse prompts `tenant/<cid>/<slug>` | 6 | **0** ❌ |

---

## Bugs encontrados (priorizados)

### 🔴 CRÍTICO

#### Bug #1 — Langfuse seed silent fail (0/6) trava UX
**Onde:** `supabase/functions/onboarding-bootstrap/index.ts:118-149` (`seedLangfusePrompts`)
**Causa raiz:** Edge function busca em `landing/<slug>` (linha 134) mas os 6 slugs habilitados (`compras, financeiro, clientes, agenda, documentos, estrategia`) têm `prompt_name = agents/<slug>` em `agent_catalog`. Os slugs com `landing/<slug>` no catalog são outros (analytics, crm, finance, marketing, scheduling, projects, documents, inventory — EN-US, set diferente, são os agentes da landing/marketing). Resultado: 6 GETs em `landing/compras`, `landing/financeiro`, etc → 404 em todos → `0 seeded`.
**Sintoma adicional:** seed é síncrono na response da edge function (linha 233). Mesmo com 404 rápido, em rede com latência alta a tela "Iniciando seu bureau" trava esperando 6 round-trips a `us.cloud.langfuse.com`.
**Decisão do usuário:** "nenhum prompt relativo ao cliente vai para o Langfuse" — **o seedLangfusePrompts não deveria existir**. Tenant-scoped prompts vivem em `blu_prompt_management/templates.py` (key: `skill:*:system`), override via Langfuse só de prompts globais.
**Fix recomendado:** **remover `seedLangfusePrompts()` inteiro** da edge function. Não há prompts tenant-scoped no Langfuse por design.

#### Bug #2 — `onboarding_completed_at` setado prematuramente
**Onde:** dentro de `onboarding_bootstrap_tx` (passo 3 da edge function)
**Sintoma:** o flag é marcado **antes** do passo 4 (Mapeamento BQ). Combinado com Bug #1 (travamento), permite que reload entregue ao app **sem** integração BQ, **sem** vault, **sem** dados.
**Fix:** mover `onboarding_completed_at` para após a conexão BQ + mapeamento bem-sucedidos. Ou separar em dois flags: `onboarding_company_profile_done_at` + `onboarding_completed_at`.

#### Bug #3 — Rotina `onboarding_complete` não dispara
**Reportado pelo usuário.** Edge function chama `dispatch_routine_event('onboarding_complete', ...)` via `waitUntil` (linha 326), mas nenhuma execução foi gerada.
**Possíveis causas a investigar:**
- `dispatch_routine_event` retornou null por "guard blocked or no subscription" (linha 336 do log esperado)
- Trigger `event_type='onboarding_completed'` da routine está com config diferente
- `waitUntil` foi abortado quando edge function timeoutou no Langfuse seed (Bug #1)
**Fix:** primeiro corrigir Bug #1 (assim a edge function não trava e `waitUntil` completa). Depois validar `dispatch_routine_event` retorna execution_id ≠ null.

#### Bug #4 — Worker P11 (Tenant Wipe) quebrado em prod
**Onde:** função `admin.tenant_wipe_tick(integer, integer)`
**Erro SQL:**
```
ERROR: column reference "table_fqn" is ambiguous
QUERY: SELECT * FROM admin.v_wipe_target_tables
       WHERE (v_job.current_table IS NULL)
          OR (table_fqn >= v_job.current_table)
       ORDER BY priority, table_fqn
CONTEXT: PL/pgSQL function tenant_wipe_tick(integer,integer) line 34
```
**Causa raiz:** PL/pgSQL não consegue desambiguar `table_fqn` (variável local da função vs coluna da view `v_wipe_target_tables`).
**Fix:** prefixar coluna na view (`v.table_fqn`) ou renomear variável local. Patch trivial, 3 linhas.
**Impacto:** **handoff afirmava P11 testado e funcional — não está**. Wipe de tenant teve que ser feito manualmente via DELETE em cascata.

#### Bug #5 — Link BigQuery inserido não persiste
**Sintoma:** usuário insere link/project_id BQ e clica "Avançar" → **0 traces no DB, 0 chamadas backend, link evapora**. Combinado com Bug #2, app entra autenticado sem BQ.
**Possíveis causas a investigar:**
- Etapa "Mapeamento" (passo 4/4) é onde de fato persistiria — usuário não chegou lá
- Frontend acumula em React state até passo 4
**Fix:** save incremental por etapa em `onboarding_state` JSONB (resolve junto com Bug #6).

### 🟡 MÉDIO

#### Bug #6 — Sem save incremental no wizard
Wizard de 4 passos mantém tudo em React state. Refresh/crash = perde tudo. Sem audit trail de drafts.
**Fix:** patch incremental em `clientes_blu.onboarding_state` JSONB a cada submit de etapa.

#### Bug #7 — `clientes_blu.email` NULL após signup Google
Coluna `email` fica vazia apesar do email estar disponível em `auth.users.email`. Como `email_domain` é GENERATED a partir dela, também fica NULL.
**Fix:** trigger `handle_new_auth_user` deve popular `clientes_blu.email = NEW.email`.

#### Bug #8 — `nome_empresa` populado com email no signup
Antes do passo Empresa, `nome_empresa = "cid.lucas@gmail.com"`. UX ruim em logs/admin views se onboarding for abandonado.
**Fix:** deixar `nome_empresa = NULL` até usuário preencher, OU usar nome do Google (`raw_user_meta_data.full_name`).

#### Bug #9 — Observability gap: crawl + Langfuse fora do escopo dos containers logados
Toda a sessão, `blu_agent_api` e `blu_tool_pool_api` ficaram **silenciosos**. Persistência real foi via edge function Supabase (rodando em deploy remoto, não local) e PostgREST direto.
**Implicação:** docker logs locais são **insuficientes** pra debugar onboarding. Precisamos de:
- Acesso a logs de edge functions (Supabase Studio → Functions logs)
- Tracing dos calls do frontend pra edge function (Network tab manual ou OpenTelemetry)

### 🟢 UX / Melhorias

#### #10 — Refatoração da tela Empresa
- ❌ Ordem atual: nome empresa → cnpj → setor → foco → link
- ✅ Ordem proposta: **link primeiro** → crawl → auto-preenche `nome_empresa`, `setor`, `principal_produto_ou_servico`
- ❌ Campo "nome do responsável": redundante (já temos `raw_user_meta_data.full_name`)
- ❌ Campo "foco atual do negócio": remover (não é dado estrutural)

---

## Achados positivos

1. ✅ Tracing DB com 19 triggers `_trace_capture` funcionou perfeitamente — todos os INSERTs/UPDATEs capturados com timestamps milissegundo
2. ✅ `handle_new_auth_user` trigger é idempotente e cobre OAuth Google
3. ✅ `onboarding_bootstrap_tx` é atômico — sucesso ou rollback completo
4. ✅ Seed de 10 rotinas template + 3 active automáticas funcionou
5. ✅ Dispatcher de rotinas pegou tenant novo em < 10s (`daily_insights` e `context_report_monthly` rodaram já no minuto seguinte)
6. ✅ Crawl preencheu `company_profile` com qualidade (`tagline`, `industry`, `employee_count_range`)

---

## Próximos passos (priorizados)

### Sprint imediata (bloqueadores)
1. **[#1]** Remover `seedLangfusePrompts()` da `onboarding-bootstrap` edge function
2. **[#4]** Corrigir ambiguidade em `tenant_wipe_tick`
3. **[#2]** Adiar `onboarding_completed_at` para após etapa Mapeamento
4. **[#3]** Re-rodar onboarding após #1 e validar que `onboarding_complete` routine dispara

### Sprint seguinte
5. **[#5+#6]** Save incremental + persistência de input BQ desde etapa Dados
6. **[#7]** Trigger popula `clientes_blu.email` no signup
7. **[#10]** Refatorar formulário Empresa (link primeiro, remover redundantes)

### Observability débito
8. **[#9]** Habilitar pull de logs Supabase Edge Functions no fluxo de tracing
9. **[#8]** Decidir política de `nome_empresa` placeholder

---

## Anexos

- Trace install script: `/tmp/onboarding_trace_install.sql`
- Edge function inspecionada: `supabase/functions/onboarding-bootstrap/index.ts`
- Handoff original: `docs/handoffs/20260525_onboarding_trace_session.md`
- Tenant client_id (apagado): `7db89c8f-f8bc-4465-ba71-ec9295b1df51`
- auth user (apagado): `6fcc4aef-d831-4ea2-8e32-558a87d35c1b`
