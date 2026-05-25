# Auditoria RLS — Tabelas tenant-scoped remanescentes

**Data:** 2026-05-25
**Autor:** Hermes (subagent A1 — Pre-Onboarding Hardening)
**Banco:** Supabase prod (`aws-0-us-west-2.pooler.supabase.com`)
**Escopo:** tabelas multi-tenant NÃO cobertas pelo Security Sprint anterior
  (excluídas: `integration_tokens`, `notifications`, `clientes_blu`,
  `bigquery_foreign_tables`, `client_routine_executions`).

---

## 0. Sumário executivo

| Severidade | Contagem | Itens |
|---|---|---|
| 🔴 P0 (cross-tenant aberto / RLS off) | 0 | — |
| 🟡 P1 (RLS habilitado mas frágil) | 14 | grants amplos a `anon`, policies sem `WITH CHECK`, polp_* usando role `public` |
| 🟢 OK | 0 tabelas totalmente limpas | — |
| 🪦 Dropada | 1 | `analytics_v2.fato_compras` (confirmado inexistente) |

**Verdict:** nenhum vazamento estrutural aberto, mas há **3 classes de fragilidade** que tornam o modelo dependente de RLS funcionar 100% e expõem superfície que pode virar bug em refactors futuros. Recomenda-se aplicar a migration P4 antes do primeiro cliente externo.

---

## 1. Resultados por tabela

| Schema | Tabela | RLS | Force | Policies | Roles | Grants extras | Severidade |
|---|---|---|---|---|---|---|---|
| analytics_v2 | fato_transacoes | ✅ | ❌ | ALL own client | authenticated | — | 🟡 P1 (sem WITH CHECK) |
| analytics_v2 | dim_inventory | ✅ | ❌ | ALL own client | authenticated | — | 🟡 P1 (sem WITH CHECK) |
| analytics_v2 | dim_clientes | ✅ | ❌ | ALL own client | authenticated | — | 🟡 P1 (sem WITH CHECK) |
| analytics_v2 | dim_fornecedores | ✅ | ❌ | ALL own client | authenticated | — | 🟡 P1 (sem WITH CHECK) |
| public | approval_requests | ✅ | ❌ | ALL own client | authenticated | **anon ALL** | 🟡 P1 |
| public | client_insights | ✅ | ❌ | ALL own client | authenticated | **anon ALL** | 🟡 P1 |
| public | client_routines | ✅ | ❌ | ALL own client | authenticated | **anon ALL** | 🟡 P1 |
| public | messages | ✅ | ❌ | ALL own client | authenticated | **anon ALL** | 🟡 P1 |
| public | standalone_agent_sessions | ✅ | ❌ | ALL own client | authenticated | **anon ALL** | 🟡 P1 |
| public | frontend_events | ✅ | ❌ | só INSERT own client | authenticated | **anon ALL** | 🟡 P1 |
| public | polp_integrations | ✅ | ❌ | só SELECT, role=`public`, via client_users | public | **anon ALL** | 🟡 P1 |
| public | polp_accounts | ✅ | ❌ | só SELECT, role=`public`, via client_users | public | **anon ALL** | 🟡 P1 |
| public | polp_transactions | ✅ | ❌ | só SELECT, role=`public`, via client_users | public | **anon ALL** | 🟡 P1 |
| public | polp_bills | ✅ | ❌ | só SELECT, role=`public`, via client_users | public | **anon ALL** | 🟡 P1 |
| analytics_v2 | fato_compras | — | — | — | — | — | 🪦 dropada (correto) |

---

## 2. Análise por classe de gap

### 🟡 P1-A — `anon` tem TABLE GRANT amplo em 10 tabelas `public.*`

Toda tabela em `public` listada acima tem `GRANT ALL` a `anon` (default do Supabase ao criar tabelas via UI/SQL editor). RLS está habilitado então requests anônimos esbarram em policies que exigem `auth.uid()`/`get_my_client_id()` — bloqueio funciona hoje.

**Por que isso é P1, não 🟢:** é defesa em uma única camada. Qualquer policy nova que esqueça filtro, qualquer função SECDEF nova que opere em `public.<tabela>` chamada por `anon`, e o leak abre. O padrão das tabelas já endurecidas (`integration_tokens`, `notifications`, `clientes_blu`) é **revogar grants de `anon` e `PUBLIC` em writes**. Aplicar mesmo tratamento aqui.

### 🟡 P1-B — Policies `FOR ALL` sem `WITH CHECK`

9 tabelas têm uma única policy `FOR ALL TO authenticated USING (client_id = get_my_client_id())` **sem cláusula `WITH CHECK`**:
- analytics_v2: fato_transacoes, dim_inventory, dim_clientes, dim_fornecedores
- public: approval_requests, client_insights, client_routines, messages, standalone_agent_sessions

Em PostgreSQL, sem `WITH CHECK`, um UPDATE pode passar pela cláusula `USING` (a row pertence ao tenant) e ainda **alterar `client_id` para outro tenant** — efetivamente um cross-tenant write disfarçado de UPDATE. Mesmo problema para INSERT (sem WITH CHECK, qualquer `client_id` é aceito desde que outras constraints permitam).

Fix obrigatório: cláusula `WITH CHECK (client_id = get_my_client_id())` em todas.

### 🟡 P1-C — Tabelas `polp_*` usam role `public` em vez de `authenticated` e só cobrem SELECT

As 4 tabelas Polp têm policy `FOR SELECT TO public USING (client_id IN (SELECT client_users.client_id FROM client_users WHERE auth_user_id = auth.uid()))`.

Problemas:
1. Role `public` é o universo (anon + authenticated + service_role). Para `anon`, `auth.uid()` retorna NULL e o subquery vira vazio — fica seguro por acidente.
2. Não há policy para INSERT/UPDATE/DELETE → RLS bloqueia por default, mas escrita só funciona via `service_role` (pular RLS). Funcionalmente correto, mas a ausência de policy explícita é um booby trap para a próxima pessoa que tentar uma migration UPDATE de manutenção autenticada.

Fix: restringir role a `authenticated`, adicionar policies INSERT/UPDATE/DELETE com `client_users` check (consistente com o ADR aberto no backlog do handoff).

### 🟡 P1-D — `frontend_events` só tem policy INSERT

Sem policy SELECT/UPDATE/DELETE; o GRANT é amplo para anon/authenticated. Pelo design da tabela (telemetria write-only do frontend), faz sentido bloquear leitura por authenticated comum. Status efetivo: seguro, mas implícito demais. Recomendação: deixar declarativo (zero policies de SELECT + revogar SELECT do GRANT a anon/authenticated) ou adicionar policy SELECT restritiva para postgres/service_role.

---

## 3. Tabelas auditadas — confirmações pontuais

- **`fato_compras`** — confirmada inexistente (`fato_compras_exists = f`). Tabela foi dropada na migration `20260523120000_entry_type_and_email_cleanup.sql` conforme HERMES.md. Sem ação.
- **`dim_inventory`** está em `analytics_v2` (não em `public`).
- Todas as 14 tabelas auditadas têm coluna `client_id` (validado no item 5 do query bundle).

---

## 4. Recomendação operacional

Aplicar a migration `supabase/migrations/proposed/20260525_p4_rls_remaining_tables.sql` (gerada junto com este relatório). Ela é idempotente, segue o padrão das P1 do Security Sprint, e cobre:

1. Revoga grants amplos de `anon` e `PUBLIC` (writes + selects desnecessários) em todas as 10 tabelas `public.*` em escopo.
2. Adiciona `WITH CHECK (client_id = get_my_client_id())` nas 9 policies `FOR ALL` em analytics_v2 + public.
3. Recria policies `polp_*` com role = `authenticated` e cobertura INSERT/UPDATE/DELETE.
4. Mantém policy INSERT de `frontend_events` e remove grants de SELECT a anon/authenticated.

Não aplica `FORCE ROW LEVEL SECURITY` — coerente com a decisão documentada em `blu-supabase-patterns` §6.3 (FORCE RLS é parcialmente teatro porque `postgres` role tem `rolbypassrls=true`; a defesa real é SECDEF lockdown + revogar grants).

---

## 5. Limitações desta auditoria

- Não testei dynamic via JWT real (auth.uid). Validação funcional fica para A2.
- Não auditei funções SECDEF que internamente fazem `SELECT FROM` nessas tabelas; o Security Sprint anterior já lockou as 45 funções críticas.
- Não auditei tabelas fora do escopo (`client_dimension_kpis`, `client_keys`, `polp_drafts`, `polp_executions`, `client_data_sources`, `calendar_settings`, `audit_log`, etc.) — verificar em sprint dedicada se faltarem do Security Sprint.

---

## 6. Anexo — query bundle usada

Arquivo: `/tmp/audit_rls.sql`. Resultado: `/tmp/rls_results.txt`. Reexecução:
```bash
cd /Users/lucascruz/Documents/GitHub/repo_platform
export SUPABASE_DB_URL=$(grep '^SUPABASE_DB_URL=' .env | cut -d= -f2-)
psql "$SUPABASE_DB_URL" -f /tmp/audit_rls.sql > /tmp/rls_results.txt
```
