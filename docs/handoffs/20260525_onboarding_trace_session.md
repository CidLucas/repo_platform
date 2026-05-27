# Handoff — Sessão de Tracing do Onboarding (E3 prep)

**Data:** 25/Mai/2026
**Objetivo:** Acompanhar passo-a-passo um onboarding real (cliente de teste) capturando frontend (Network + Console), backend (Docker logs) e banco (triggers de auditoria), para mapear qual informação cada etapa gera, onde é gravada e como.

---

## Estado já instalado em prod

✅ **DB tracing ativo:** 19 triggers `_trace_capture` em tabelas-chave gravando em `_trace.onboarding_events`
✅ **P11 (Tenant Wipe Worker)** aplicado — permite resetar cliente teste rapidamente via `SELECT admin.request_client_deletion('<uuid>', 'reason')`
✅ **Ambiente prod limpo:** 0 clientes, 0 vault órfãos, 0 BQ foreign servers órfãos
⏳ **Pendência manual do usuário:** apagar 2 arquivos em `knowledge-base` no painel Supabase Storage (não dá via SQL pela trigger `storage.protect_delete()`)

---

## Setup a refazer na nova sessão

> Tudo abaixo é idempotente — pode rodar sem medo.

### 1. Verificar tracing DB ativo
```bash
cd /Users/lucascruz/Documents/GitHub/repo_platform
export SUPABASE_DB_URL=$(grep '^SUPABASE_DB_URL=' .env | cut -d= -f2-)
psql "$SUPABASE_DB_URL" -c "SELECT count(*) FROM pg_trigger WHERE tgname='_trace_capture' AND NOT tgisinternal;"
# Esperado: 19
```

Se zerado, reinstalar: `psql "$SUPABASE_DB_URL" -f /tmp/onboarding_trace_install.sql`
(script salvo em `/tmp/onboarding_trace_install.sql`)

### 2. Limpar trace antigo (começar timeline do zero)
```sql
TRUNCATE _trace.onboarding_events RESTART IDENTITY;
```

### 3. Iniciar logs Docker em background
```bash
# Agent API
docker logs -f --tail 0 blu_agent_api 2>&1 | ts '[%H:%M:%S]'    # → background notify_on_complete=false
# Tool pool API
docker logs -f --tail 0 blu_tool_pool_api 2>&1 | ts '[%H:%M:%S]' # → background
```

### 4. Abrir browser controlado
```
browser_navigate("http://localhost:5175")
```

---

## Como vamos trabalhar (passo-a-passo)

Para cada ação do onboarding:

1. **Usuário dita a próxima ação** ("clica em criar conta", "preenche email X", etc.)
2. **Agent executa via browser tool** e captura:
   - Network: URL, método, status, payload, response, timing
   - Console: logs, warnings, errors, JS exceptions
3. **Agent consulta `_trace.onboarding_events`** desde o último checkpoint
4. **Agent consulta `docker logs` recent (tail novo desde último passo)**
5. **Agent entrega mini-relatório:**
   ```
   ▸ HTTP:    POST /api/auth/signup → 201 (340ms)
              payload: {email, name, password (REDACTED)}
              response: {user_id, session}
   ▸ Console: nada relevante
   ▸ DB:      [22:41:03.123] clientes_blu INSERT id=...
              [22:41:03.156] client_users INSERT user_id=...
   ▸ Backend: "INFO: New tenant created: <uuid>"
   ▸ Próximo passo sugerido: …
   ```

Usuário digita login manualmente (credenciais NUNCA passam pelo chat).

---

## Queries úteis durante a sessão

### Timeline cronológica completa
```sql
SELECT at, table_name, op, pk, client_id, changed_cols
FROM _trace.onboarding_events
ORDER BY at;
```

### Diff de colunas em updates de clientes_blu
```sql
SELECT at, changed_cols, payload->>'status' AS status, payload->>'deletion_status' AS del_status
FROM _trace.onboarding_events
WHERE table_name='public.clientes_blu' AND op='UPDATE'
ORDER BY at;
```

### Onboarding por agente — quais integrações foram criadas
```sql
SELECT at, table_name, op, payload->>'integration_type' AS type, payload->>'status' AS status
FROM _trace.onboarding_events
WHERE table_name IN ('public.integration_configs','public.integration_tokens','public.client_data_sources')
ORDER BY at;
```

### Visualizar último N segundos
```sql
SELECT at, table_name, op, pk
FROM _trace.onboarding_events
WHERE at > now() - interval '30 seconds'
ORDER BY at;
```

---

## Roteiro provável do onboarding (a confirmar durante)

Baseado no fluxo conhecido do Blu:

1. **Landing** http://localhost:5175 → clica "Criar conta grátis"
2. **Signup** email + senha → cria `auth.users` + `clientes_blu` + `client_users`
3. **Onboarding step 1 — Empresa** nome, CNPJ, segmento → UPDATE `clientes_blu`
4. **Onboarding step 2 — Integração Google** (OAuth)
   - Cria `integration_configs`, `integration_tokens`
   - Vault: `oauth_google_<cid>_<email>`
5. **Onboarding step 3 — BigQuery setup** (se aplicável)
   - Cria foreign server `bigquery_<cid>`
   - Cria `bigquery_servers`, `bigquery_foreign_tables`
   - Vault: `bigquery_service_account_<cid>` ou `bigquery_<cid>_sa_key`
6. **Onboarding step 4 — Sheets / Polp / Monday** (integrações restantes)
7. **Onboarding step 5 — Agentes habilitados** → `client_enabled_agents`
8. **Onboarding step 6 — Goals/preferências** → `client_goals`, `client_notification_preferences`
9. **Primeira rotina criada/executada** → `client_routines`, `client_routine_executions`
10. **Conversa inicial / mensagem boas-vindas** → `conversa`, `messages`, `notifications`

---

## Entregáveis ao fim da sessão

1. **`docs/observability/onboarding-trace-mai2026.md`** — relatório completo:
   - Timeline cronológica unificada (DB + backend + frontend)
   - Mapa "tela X → endpoint Y → tabelas Z"
   - Lista de campos coletados em cada etapa (LGPD inventory)
   - Performance: tempo gasto em cada passo
   - Bugs / inconsistências encontradas
2. **`docs/observability/onboarding-data-inventory-mai2026.md`** — inventário LGPD:
   - Cada PII coletado → onde está armazenado → quanto tempo
3. **Backlog atualizado** com gaps observados

---

## Cleanup ao final

```sql
-- Remove triggers de trace
DO $$
DECLARE t text;
BEGIN
  FOR t IN
    SELECT format('%I.%I', n.nspname, c.relname)
    FROM pg_trigger tg JOIN pg_class c ON c.oid=tg.tgrelid
    JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE tg.tgname='_trace_capture' AND NOT tg.tgisinternal
  LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS _trace_capture ON %s', t);
  END LOOP;
END $$;

-- Mantém _trace.onboarding_events como artefato pra análise post-mortem
-- (drop manual quando relatório estiver pronto)
```

---

## Referências

- Migration P11: `supabase/migrations/applied/20260525_p11_tenant_wipe_worker.sql`
- Script trace install: `/tmp/onboarding_trace_install.sql`
- Smoke test E3: `scripts/e3_smoke.py`
- Checklist E3: `docs/security/test-onboarding-checklist-mai2026.md`

## Containers Docker locais
```
blu_agent_api          :8003 → 8000
blu_tool_pool_api      :8006 → 8000
blu_dashboard          :8081 (frontend prod build, NÃO usar nesta sessão)
blu_landing            :8080
blu_redis_dev          :6379
```
Frontend dev: http://localhost:5175 (Vite, fora do Docker)

## Pré-requisitos antes de iniciar
- [ ] Vite dev server rodando em :5175
- [ ] 5 containers Docker UP (`docker ps`)
- [ ] Conta de teste pronta para signup (email + senha que o usuário vai digitar)
- [ ] (Opcional) Apagar 2 arquivos storage manuais via painel Supabase
