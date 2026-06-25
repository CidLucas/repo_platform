# Investigação: 2º cadastro de email falha no pipeline de auth

**Status:** Investigação estática (sem acesso a logs/runtime)
**Owner:** TBD
**Severidade:** Alta — bloqueia onboarding de qualquer usuário após o primeiro em um mesmo browser/sessão

---

## TL;DR

A causa mais provável é a **sessão persistida do primeiro signup interferindo no segundo**. O `@blu/auth` cria um `supabase` singleton com `persistSession: true` + `autoRefreshToken: true`. Após o primeiro signup, a JWT do user A fica em `localStorage`. Quando o `signUp` do user B é chamado em seguida, a requisição é enviada com a sessão do user A — comportamento documentado do supabase-js que produz erros inconsistentes dependendo da config do projeto.

Hipóteses secundárias (menor probabilidade, mas precisam ser validadas):
- Webhook `on_user_created` configurado no Supabase dashboard chamando uma EF que falha silenciosamente no 2º evento
- Trigger/constraint DB ausente que faz o fluxo depender exclusivamente de `ensure_tenant_row` (chamado tarde demais)

**Evidência chave:** Não existe nenhum `CREATE TRIGGER` que invoque `handle_new_auth_user` (função definida em `baseline_v2.sql:2961` está morta). O `clientes_blu` row só é criado quando o frontend chama `onboarding-bootstrap` (que chama `ensure_tenant_row` internamente). A função `seed_client_owner` (linha 4159) é `AFTER INSERT ON public.clientes_blu` — também não roda para o 2º user se o 2º signup falhar antes de chegar ao EF.

---

## AC-1: Fluxo de signup mapeado (estático)

### Camadas e arquivos

```
┌────────────────────────────────────────────────────────────────────────┐
│ FRONTEND                                                               │
│                                                                        │
│  apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx (StepAuth, L316)   │
│   └─ handleSubmit()                                                    │
│      └─ signUp(email, password)  // @blu/auth                         │
│                                                                        │
│  packages/blu-auth/src/AuthContext.tsx:233                             │
│   └─ supabase.auth.signUp({email, password, options:{data:metadata}}) │
│      └─ NÃO chama signOut() antes                                     │
│      └─ supabase-js v2.86 (singleton, persistSession:true)             │
└────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────────┐
│ SUPABASE AUTH (GoTrue server) — projeto haruewffnubdgyofftut          │
│                                                                        │
│  1. Valida email/password                                              │
│  2. INSERT INTO auth.users (cria UUID, raw_user_meta_data)              │
│  3. SE email_confirm=ON:  dispara email de confirmação, retorna SEM    │
│     sessão.                                                            │
│     SE email_confirm=OFF: retorna COM sessão, persiste em localStorage │
│  4. SE webhook `on_user_created` configurado no dashboard: dispara    │
│     webhook server-to-server → alguma EF                              │
└────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────────┐
│ FRONTEND (reprise)                                                     │
│                                                                        │
│  AuthContext.onAuthStateChange (L141)                                  │
│   └─ Em SIGNED_IN/TOKEN_REFRESHED/USER_UPDATED: initClientId()        │
│      └─ Guard: clientIdFetchedRef.current (só roda 1x por mount)      │
│   └─ Se JWT do user A chega com SIGNED_IN do user B → estado vira     │
│      inconsistente (resolveClientId retorna client_id do A)           │
│                                                                        │
│  StepAuth.handleSubmit, L328-330:                                      │
│   ├─ if (error) → setError(error.message) → return                    │
│   └─ else      → onNext() → avança wizard                              │
└────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────────┐
│ LATER (depois do wizard completo)                                      │
│                                                                        │
│  Frontend chama onboarding-bootstrap EF (L84)                          │
│   └─ userClient.rpc("ensure_tenant_row")        -- SECURITY INVOKER   │
│      └─ INSERT clientes_blu ON CONFLICT (external_user_id) DO NOTHING │
│   └─ userClient.rpc("onboarding_bootstrap_tx")  -- atomic provision   │
│      └─ INSERT agentes, rotinas, policies                             │
│      └─ trigger seed_client_owner AFTER INSERT → INSERT client_users  │
└────────────────────────────────────────────────────────────────────────┘
```

### Tabelas e constraints relevantes

| Tabela | Constraints únicas | Observação |
|---|---|---|
| `auth.users` | (interno Supabase) | Cada `id` é único. `email` pode ter índices. |
| `public.clientes_blu` | `clientes_blu_pkey` (client_id), `clientes_blu_api_key_key` (api_key), `clientes_blu_external_user_id_key` (external_user_id) | Linha só é criada via `ensure_tenant_row` ou `onboarding_bootstrap_tx` — NÃO tem trigger automático |
| `public.client_users` | `client_users_pkey` (id), `client_users_unique_email` (client_id, email) | Preenchido pelo trigger `seed_client_owner` (only AFTER clientes_blu insert) |

### Triggers encontradas (que importam aqui)

| Trigger | Quando | Efeito |
|---|---|---|
| `trg_seed_client_owner` (L5011) | `AFTER INSERT ON public.clientes_blu` | Insere `client_users` com role=owner |

**Ausência crítica:** NÃO existe trigger `AFTER INSERT ON auth.users FOR EACH ROW EXECUTE FUNCTION handle_new_auth_user()`. A função existe (L2961) e está correta, mas é código morto. O `onboarding-bootstrap` chama `ensure_tenant_row` (L84) como workaround.

### Helpers e serviços compartilhados (verificação de singleton)

- `packages/blu-auth/src/client.ts:11` — `export const supabase = createClient(...)`. **Singleton module-level** (mesma instância para todos os imports no mesmo bundle JS).
- `persistSession: true` → sessão em `localStorage`
- `autoRefreshToken: true` → refresh automático
- `detectSessionInUrl: true` → captura tokens OAuth no hash
- `flowType: 'pkce'` → OAuth flow

---

## AC-2: Reprodução (não executada — limitações do ambiente)

Não tenho acesso ao Supabase dashboard, ao browser do tester, nem aos logs. Para reproduzir:

### Plano de reprodução (você pode rodar)

```js
// No DevTools console, após o primeiro signup bem-sucedido:
console.log('session:', await window.supabase.auth.getSession())
console.log('localStorage key:', localStorage.getItem('sb-<project>-auth-token')?.slice(0, 60))

// Limpar e tentar de novo (com email diferente):
await window.supabase.auth.signOut()
localStorage.clear()
// ... agora tente signUp com email B
```

### O que capturar

- **Frontend console:** mensagem de erro exata (AuthApiError? AuthRetryableFetchError? string?)
- **Network tab:** request para `/auth/v1/signup` — status code, response body, headers
- **Supabase Auth logs:** dashboard → Authentication → Logs (filtrar por email)
- **Supabase Edge Function logs:** dashboard → Edge Functions → Logs (se webhook chama EF)
- **Postgres logs:** se webhook insere em alguma tabela via EF, ver erros de UNIQUE violation

---

## AC-3: Causas específicas investigadas

### ❌ Falso: tabela `profiles` ou `client_profiles`

O issue menciona `public.profiles, public.client_profiles`, mas **essas tabelas não existem em nenhuma migration** do repo (verifiquei com `rg "CREATE TABLE.*profile"` — zero matches em `supabase/migrations/`). A única tabela de tenant é `clientes_blu`. Se elas existem em produção, foram criadas via SQL ad-hoc no dashboard (anti-pattern — deveriam ser migration).

### ❌ Falso: rate limit do Supabase

O issue já descarta rate limit. Confirmo pela config: `supabase/config.toml` não tem seção `[auth.rate_limit]` customizada, então os defaults do Supabase se aplicam (30 logins/hora por IP, 60 logins/hora por email — source: Supabase docs). Esses limites não batem com "primeiro funciona, segundo falha imediato".

### ⚠️ Provável: sessão persistida interfere no 2º signup

**Evidência:**
- `supabase` é singleton module-level (`client.ts:11`)
- `persistSession: true` no client config
- `signUp` em `AuthContext.tsx:233` NÃO chama `signOut()` antes
- `signOut()` só é invocado manualmente via `Topbar.tsx:127`

**Mecanismo provável:**
1. User A cadastra → `auth.users(A)` criado → sessão A persistida em `localStorage` (caso `email_confirm=OFF`) OU email de confirmação enviado (caso `email_confirm=ON`)
2. User B tenta cadastrar → supabase-js v2.86 envia `POST /auth/v1/signup` — o helper de `_request` adiciona `Authorization: Bearer <token A>` se há sessão
3. O servidor GoTrue:
   - Se reconhece a sessão, trata o signup como "add new user authenticated as A" — comportamento varia
   - Possíveis respostas: 422, 200 com user novo mas sessão ainda amarrada a A
4. O frontend exibe erro genérico e o user não consegue prosseguir

**Como verificar:**
- Inspecionar Network tab: o request do 2º signup tem `Authorization` header? Se sim, hipótese confirmada.
- Tentar `await supabase.auth.signOut()` antes do 2º `signUp` e ver se funciona — se funcionar, hipótese confirmada.
- Tentar `localStorage.clear()` antes do 2º `signUp` — mesma coisa.

**Fix estrutural (não workaround):**

```ts
// packages/blu-auth/src/AuthContext.tsx
const signUp = async (email: string, password: string, metadata?: Record<string, unknown>) => {
  // Garantir que não há sessão residual de um signup/login anterior.
  // O supabase-js v2 não limpa a sessão automaticamente em signUp — se
  // houver JWT em localStorage, ele é enviado junto e causa falha
  // intermitente ("User already exists", "Anonymous signups disabled",
  // ou signup silenciosamente associado ao user errado).
  const { data: { session } } = await supabase.auth.getSession()
  if (session) {
    await supabase.auth.signOut()
  }
  const { error } = await supabase.auth.signUp({
    email,
    password,
    options: { data: metadata },
  })
  return { error }
}
```

A verificação `if (session)` evita um `signOut()` desnecessário no caso comum (primeiro signup, sem sessão anterior) — custo de uma chamada local, sem rede.

### ⚠️ Possível: webhook `on_user_created` no Supabase dashboard

**Evidência:** o issue menciona "Supabase Auth webhooks — on_user_created", mas não há configuração disso em `config.toml` nem em migrations. Isso indica que o webhook é configurado no dashboard Supabase, e não consigo ver daqui.

**Mecanismo possível:**
1. Webhook configurado para chamar `${SUPABASE_URL}/functions/v1/onboarding-bootstrap` (ou outra EF)
2. Quando `auth.users(B)` é criado, webhook dispara com payload do novo user
3. EF `onboarding-bootstrap` valida JWT e exige `OnboardingState` no body — sem o body completo, retorna 500 com "Body must be an OnboardingState object"
4. Webhook pode estar configurado para reentregar em caso de falha → loop de retries → engole o request de signup
5. OU: a primeira execução funciona porque a EF é tolerante a body vazio (não — não é, vide L65-67 do EF)

**Como verificar:**
- Dashboard Supabase → Database → Webhooks (ou Auth → Hooks) — listar webhooks ativos
- Se houver, ver o target URL e o secret
- Dashboard → Edge Functions → Logs → filtrar por timestamp dos signups que falharam
- Verificar se há retries no painel de webhooks

**Fix estrutural (se confirmado):**
- Webhook deveria chamar uma EF dedicada para provisionamento inicial (criar `clientes_blu` + `client_users`) que aceita payload mínimo `{user_id, email}` do webhook do Supabase
- OU remover o webhook e fazer o frontend chamar `onboarding-bootstrap` após o signup (fluxo atual, que parece depender do trigger morto)

### ⚠️ Possível: race entre webhook e frontend

Mesmo se o webhook estiver OK, pode haver:
- User A faz signup → webhook dispara, roda em background
- User B faz signup imediatamente → webhook do B dispara
- Os dois webhooks competem por recursos ou causam lock contention no DB
- O webhook do B pode falhar (deadlock, timeout) e o Supabase reporta o signup como falho (depende de como o webhook está configurado)

**Como verificar:** logs do webhook no Supabase dashboard + ordenação temporal dos eventos.

### ❌ Descartado: violação de UNIQUE no DB

As UNIQUE constraints (`clientes_blu_external_user_id_key`, `client_users_unique_email`) operam em `(external_user_id, email)` e `(client_id, email)` — emails diferentes de users diferentes não colidem. Cada `auth.users` tem UUID único, então `clientes_blu.external_user_id` também é único. **Não pode ser causa de falha no 2º signup.**

### ❌ Descartado: CAPTCHA / rate limit por IP

Já descartado pelo issue. Confirmado pela config: `config.toml` não tem CAPTCHA habilitado.

### ❌ Descartado: limit por domínio de email

Já descartado pelo issue. Supabase Auth não tem rate limit por email domain nativo.

---

## AC-4: Causa raiz + recomendação

### Ranking de probabilidade

| # | Hipótese | Prob. | Como confirmar em 5 min |
|---|---|---|---|
| 1 | Sessão persistida interfere no 2º signUp | **Alta** | DevTools Network tab: ver se 2º request tem `Authorization: Bearer <token A>` |
| 2 | Webhook `on_user_created` configurado no dashboard com EF errada | Média | Dashboard Supabase → Webhooks |
| 3 | Race condition entre webhook e próximo signup | Baixa | Logs do webhook |
| 4 | Estado do frontend (React) reutilizado entre signups | Baixa | React DevTools: inspecionar `AuthContext.state` antes do 2º signup |

### Recomendação de ação (em ordem)

#### Imediato (1-2 horas)
1. **Reproduzir localmente** com DevTools aberto:
   - Limpar console + network
   - Signup user A
   - **Sem fazer logout**, signup user B
   - Capturar: console error, network request (especialmente headers), Supabase Auth logs
2. **Testar fix da hipótese #1**: adicionar `signOut()` condicional no `signUp` (snippet acima) e tentar de novo
3. **Auditar dashboard Supabase**: webhooks ativos, config de email confirm, rate limits customizados

#### Curto prazo (se hipótese #1 confirmada)
1. Aplicar o fix em `packages/blu-auth/src/AuthContext.tsx:233`
2. Adicionar teste E2E que:
   - Signup user A
   - Signup user B sem logout
   - Garante que ambos são criados com sessões distintas
3. Considerar tornar o `signUp` mais explícito sobre o estado (loading state dedicado, evitar chamar `onNext()` se a sessão não foi confirmada)

#### Médio prazo (higiene do pipeline de auth)
1. **Recriar o trigger `on_auth_user_created`** que está faltando:
   ```sql
   CREATE TRIGGER on_auth_user_created
     AFTER INSERT ON auth.users
     FOR EACH ROW EXECUTE FUNCTION public.handle_new_auth_user();
   ```
   Isso garante que `clientes_blu` é criado imediatamente, sem depender do frontend chamar `onboarding-bootstrap` (mais robusto a falhas de frontend).
2. **Mover `clientes_blu` creation para fora do `onboarding-bootstrap`** — o EF deveria apenas provisionar agents/routines, não criar o tenant. A criação do tenant é responsabilidade do trigger.
3. **Decidir sobre o webhook `on_user_created`**: se existir, fazer com que chame uma EF dedicada (ex: `provision-tenant`) que recebe `{user_id, email}` e chama `handle_new_auth_user` via service-role. Remover a dependência de `ensure_tenant_row` no `onboarding-bootstrap`.

---

## Não-objetivos desta investigação

- Não foi analisada a stack de OAuth (Google, Microsoft, Apple) — issue foca em signup por email/senha
- Não foi analisado `client_users` permissions/RLS — fora do escopo do signup
- Não foi analisado o comportamento de `confirm_email` no fluxo de confirmação pós-signup

---

## Anexos

### A. Função `handle_new_auth_user` (morta)

```sql
-- supabase/migrations/20260523999999_baseline_v2.sql:2961
CREATE OR REPLACE FUNCTION public.handle_new_auth_user()
RETURNS trigger LANGUAGE plpgsql AS $function$
DECLARE
  v_client_id uuid;
  v_api_key text;
BEGIN
  v_api_key := gen_random_uuid()::text;
  INSERT INTO public.clientes_blu (external_user_id, api_key, nome_empresa, created_at, updated_at)
  VALUES (NEW.id::text, v_api_key, COALESCE(NEW.email, 'Empresa'), now(), now())
  ON CONFLICT (external_user_id) DO NOTHING
  RETURNING client_id INTO v_client_id;
  -- ... (audit log)
  RETURN NEW;
END; $function$;
-- ⚠️ Nenhum CREATE TRIGGER em qualquer migration referencia esta função
```

### B. `onboarding-bootstrap` chama `ensure_tenant_row` como workaround

```ts
// supabase/functions/onboarding-bootstrap/index.ts:84
const { error: ensureError } = await userClient.rpc("ensure_tenant_row");
if (ensureError) {
  console.error("[onboarding-bootstrap] ensure_tenant_row failed:", ensureError);
  return json({ error: "Failed to initialize tenant", details: ensureError.message }, 500);
}
```

O comentário do código admite: "ensure_tenant_row() is SECURITY DEFINER — it inserts the row bypassing RLS **if the handle_new_auth_user trigger missed it** (e.g. some OAuth flows)." — a admissão explícita de que o trigger deveria existir.

### C. `signUp` em `@blu/auth` não limpa sessão

```ts
// packages/blu-auth/src/AuthContext.tsx:233
const signUp = async (email: string, password: string, metadata?: Record<string, unknown>) => {
  const { error } = await supabase.auth.signUp({
    email,
    password,
    options: { data: metadata },
  })
  return { error }
}
```

Compare com `signOut` (L242-244) e `signInWithEmail` (L204-207) — nenhum dos dois limpa estado de sessões anteriores.
