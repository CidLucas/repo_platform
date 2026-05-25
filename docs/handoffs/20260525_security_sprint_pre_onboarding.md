# Handoff — Security Sprint pré-Onboarding

**Data:** 2026-05-25
**Autor:** Lucas + Hermes (claude-opus-4.7)
**Status:** ✅ Migrations aplicadas em produção · ⚠️ 2 ações operacionais pendentes
**Banco alvo:** `aws-0-us-west-2.pooler.supabase.com` (Supabase prod)

---

## 1. Contexto

Antes de iniciar o onboarding de clientes de teste reais, foi feita uma auditoria
completa de segurança da plataforma Blu. O foco foi backend/dados/integrações —
front-end e UX ficam para etapa seguinte, depois de validar interações reais.

O trabalho cobriu três bloqueadores estruturais:

1. **RLS frágil** — políticas referenciando claim raiz `client_id` que JWTs
   Supabase não populam, e cláusulas `sub IS NULL` que abriam vazamento entre
   tenants.
2. **SECURITY DEFINER expostas para PUBLIC/anon/authenticated** — 14 funções no
   schema `public` + 30 no `analytics_v2`, várias retornando segredos
   (`get_platform_google_oauth_config` retorna `client_secret` Google em claro).
3. **Auth morta** — função `verify_tenant_password` e coluna
   `clientes_blu.password` (legacy de auth pré-Supabase Auth), zero callers,
   atacavam superfície sem benefício.

---

## 2. O que foi aplicado em prod

### Migrations (`supabase/migrations/proposed/`)

| # | Arquivo | Status |
|---|---|---|
| P0 | `20260525_p0_fix_integration_tokens_rls.sql` | ✅ aplicado (sessão anterior) |
| P1 | `20260525_p1_fix_notifications_rls.sql` | ✅ aplicado (sessão anterior) |
| P1 | `20260525_p1_integration_tokens_write_policies.sql` | ✅ aplicado (sessão anterior) |
| P2 | `20260525_p2_normalize_roles_to_authenticated.sql` | ✅ aplicado (sessão anterior) |
| **P3** | `20260525_p3_lockdown_secdef.sql` | ✅ aplicado nesta sessão |
| **P3.1** | `20260525_p3_1_refactor_bq_secdef.sql` | ✅ aplicado nesta sessão |
| **P3.2** | `20260525_p3_2_drop_dead_password_auth.sql` | ✅ aplicado (no-op — coluna já não existia) |

### Mudanças efetivas no schema

- **RLS reforçado** em `integration_tokens`, `notifications`, `clientes_blu`,
  `bigquery_foreign_tables`, `client_routine_executions`. Todas as policies
  usam `get_my_client_id()` ou `auth.jwt() ->> 'sub'`, todas escopadas a
  `authenticated` (não mais `public`).
- **45 funções SECURITY DEFINER revogadas** de `PUBLIC/anon/authenticated`,
  restritas a `postgres, service_role`. Inclui: `get_platform_google_oauth_config`,
  `get_user_oauth_tokens`, `upsert_user_oauth_tokens`, família `set_current_*_id`,
  `offboard_client*`, `soft_delete_client`, `bootstrap_knowledge_from_onboarding`,
  `enqueue_routine`, `enqueue_custom_routine`, `enqueue_monthly_close`,
  `schedule_monthly_context_reports`, `create_bigquery_foreign_table_from_schema`,
  + 30 funções em `analytics_v2`.
- **Família BigQuery FDW refatorada (fix durável — Opção A):**
  `create_bigquery_server`, `drop_bigquery_server`,
  `create_bigquery_foreign_table` agora **ignoram o parâmetro `p_client_id`** e
  derivam o tenant exclusivamente de `get_my_client_id()`. O parâmetro continua
  na assinatura por compat com o frontend, mas cross-tenant access ficou
  estruturalmente impossível.
- **Catálogos read-only:** writes revogados de `cnpj_enrichments` e
  `canonical_columns` para anon/authenticated.
- **Auth morta:** `verify_tenant_password` e `clientes_blu.password` —
  confirmadas inexistentes (já foram dropadas em sweep anterior). Migration
  ficou idempotente por `IF EXISTS` + recriação da view `active_clientes_blu`.

### Código modificado

- `supabase/functions/google-oauth-start/index.ts` — passou a usar
  service-role client para chamar `get_platform_google_oauth_config`, agora
  que a RPC está restrita.
  **Aguardando deploy** (`supabase functions deploy google-oauth-start`).
- `supabase/functions/get-agenda-events/index.ts` — sem mudança necessária
  (já usava service client).
- `supabase/functions/google-oauth-callback/index.ts` — sem mudança necessária
  (já usava admin client).
- `scripts/apply_security_sprint.sh` — script idempotente com dry-run que
  aplica as 7 migrations em ordem com fail-fast. Reusável.

---

## 3. Achado crítico — leak comprovado

Durante a validação do Vault, foi confirmado que o `client_secret` Google
OAuth esteve **legível por qualquer JWT autenticado (e até `anon`)** entre
**2026-05-08** (criação do secret) e **2026-05-25** (lockdown aplicado) —
17 dias de exposição via `get_platform_google_oauth_config()`.

A edge function `google-oauth-start` chamava a RPC com `userClient` (JWT do
usuário), então o response `{client_id, client_secret}` chegava ao browser e
ficava visível no DevTools → Network. Não há logs de RPC no Supabase para
verificar se algum cliente real explorou — assumir comprometido.

---

## 4. ⚠️ Ações pendentes antes do primeiro onboarding

**Estas 3 ações são bloqueadoras. Não pular.**

### 4.1 Rotacionar Google OAuth client_secret

1. Acessar https://console.cloud.google.com → APIs & Services → Credentials
2. Selecionar o OAuth 2.0 Client em uso pela Blu
3. "Reset secret" → copiar o novo `client_secret`
4. Atualizar no Vault. O `secret_id` é
   `7d7d8c90-806b-4938-abad-ef0c327f01b7` (nome: `google_oauth_config`).
   Passar o JSON novo via arquivo local (não pelo chat) e rodar:
   ```sql
   SELECT vault.update_secret(
     '7d7d8c90-806b-4938-abad-ef0c327f01b7'::uuid,
     jsonb_build_object(
       'client_id',     '<mesmo_ou_novo>',
       'client_secret', '<novo_secret>'
     )::text,
     'google_oauth_config'
   );
   ```

### 4.2 Redeploy da edge function

```
cd /Users/lucascruz/Documents/GitHub/repo_platform
supabase functions deploy google-oauth-start
```

Sem isso, o fluxo "Conectar Google Calendar" no app vai falhar com
`oauth_not_configured` (a RPC só responde para service_role agora).

### 4.3 Smoke tests no frontend

Antes do primeiro cliente real, validar manualmente:
- Login no app → dashboard carrega sem erros 401/403 no console
- Wizard de BigQuery connector cria server com sucesso
- Iniciar e completar fluxo Google OAuth (calendar)
- Listar rotinas, executar `enqueue_routine_for_me` de pelo menos uma

---

## 5. Backlog imediato (próximas sessões)

Itens identificados durante a auditoria mas fora do escopo deste sprint:

1. **ADR de auth Polp** — decidir entre `client_users`-only vs
   `client_users OR get_my_client_id()`. Hoje policies polp_* usam OR,
   suportando multi-user mas com semântica dupla.
2. **Observabilidade de rotinas** — não há logging estruturado de quem
   chamou cada RPC nem latência. Pré-onboarding aceitável, mas precisamos
   antes de N clientes simultâneos.
3. **Rate limits** — Supabase tem default, mas não há throttling
   por-tenant nas RPCs caras (ETL, BQ FDW).
4. **Idempotência de rotinas** — `enqueue_routine_for_me` aceita disparos
   duplicados. Adicionar dedupe por `(client_id, routine_id, window)`.
5. **Plano de rollback de onboarding** — `offboard_client` existe e foi
   restrita a service_role. Testar end-to-end com cliente sintético.
6. **Audit log de Vault** — Supabase não loga acesso a `vault.secrets`.
   Avaliar trigger custom para auditoria de `decrypted_secrets`.

---

## 6. Artefatos

- Migrations: `supabase/migrations/proposed/20260525_*.sql`
- Script: `scripts/apply_security_sprint.sh` (dry-run + apply idempotente)
- Edge function modificada: `supabase/functions/google-oauth-start/index.ts`
- Este handoff: `docs/handoffs/20260525_security_sprint_pre_onboarding.md`

---

## 7. Verificação final (rodada 2026-05-25)

```
=== 1. SECDEF grants críticas — só postgres+service_role ===
15 funções listadas, todas com grantees = {postgres, service_role}

=== 2. BigQuery refactor ===
create_bigquery_server, drop_bigquery_server, create_bigquery_foreign_table
recriadas com prosecdef=t e SET search_path=public,pg_temp

=== 3. clientes_blu.password ===
0 rows (coluna inexistente)

=== 4. active_clientes_blu sem referência a password ===
references_password = f

=== 5. analytics_v2 ===
6 funções verificadas: todas com grantees = {postgres} ou {postgres, service_role}
```

Status final: **prod consistente com o desenho de segurança proposto.**
