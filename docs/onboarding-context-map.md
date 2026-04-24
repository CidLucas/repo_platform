# Landing Onboarding — Context Map

> **Status:** Implemented (Phases 1–6 landed 2026-04-23/24).
> **Plan of record:** [`docs/plans/2026-04-23-landing-onboarding-wireup.md`](./plans/2026-04-23-landing-onboarding-wireup.md)

This document is the **one-stop reference** for how the landing onboarding wizard turns a fresh signup into a fully provisioned Vizu tenant. It maps every moving piece — UI step → service call → SQL/edge-function artefact → downstream consumer — so engineers extending the flow know exactly where to hook in.

---

## 1. High-level flow

```
                ┌───────────────────────── apps/landing (React SPA) ──────────────────────────┐
                │                                                                             │
  user ──►  /onboarding/auth ──► /welcome ──► /dna ──► /data ──► /agents ──► /rules ──► /launch ─► dashboard
                │     │            │           │         │         │          │         │
                │     │            │           │         │         │          │         │
                │     ▼            ▼           ▼         ▼         ▼          ▼         ▼
                │   signUp    hydrate+    saveContext  patch +   patch    patch    runBootstrap
                │   /OAuth    patch       + patch      capture   only     only     (edge fn)
                │     │       (merge RPC) + update                                       │
                └─────┼────────────────────────┬────────┼─────────────────────┬─────────┘
                      │                        │        │                     │
                      ▼                        ▼        ▼                     ▼
                 auth.users              clientes_vizu   integration_tokens   client_enabled_agents
                   (trigger)              .onboarding_state                   client_routines
                      │                   .company_profile                    clientes_vizu.*
                      ▼                   .team_structure                     (Langfuse prompts)
             clientes_vizu (stub)         .policies
                                          .current_moment
                                          .nome_empresa
                                          .onboarding_completed_at
```

**Two invariants that the whole design leans on:**

1. A `clientes_vizu` row **always exists** by the time any landing step runs, because the `handle_new_auth_user()` trigger fires `AFTER INSERT ON auth.users`. This closes the chicken-and-egg with `public.get_my_client_id()` (which resolves `external_user_id = auth.uid()::text`).
2. **Nothing except LaunchPad creates tenant-scoped side-effects.** Steps 2–5 only patch `onboarding_state` (JSONB blob) and, for BusinessDNA, the `company_profile` Context 2.0 section. `client_enabled_agents` + `client_routines` are written atomically inside `onboarding_bootstrap_tx()`. If the user bails before LaunchPad, nothing to roll back.

---

## 2. Wizard steps (frontend contract)

All step components live under [`apps/landing/src/onboarding/steps/`](../apps/landing/src/onboarding/steps/).
State is owned by `useOnboarding()` in [`apps/landing/src/onboarding/state.ts`](../apps/landing/src/onboarding/state.ts) — a hook that mirrors every edit to `localStorage` (fast-path cache) and debounces a server autosave (300 ms) via `patchOnboardingState()`.

| #   | Route                 | Component                                                                         | Writes triggered on `handleNext` / effect                                                                                                                                                                                                          | Source of truth after step                                 |
| --- | --------------------- | --------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| 0   | `/onboarding/auth`    | [`Auth.tsx`](../apps/landing/src/onboarding/steps/Auth.tsx)                       | `supabase.auth.signUp` / `signInWithOAuth('google')` → trigger creates `clientes_vizu` row                                                                                                                                                         | `auth.users` + stub `clientes_vizu`                        |
| 1   | `/onboarding/welcome` | [`Welcome.tsx`](../apps/landing/src/onboarding/steps/Welcome.tsx)                 | OAuth code exchange → hydrate name/email; `ensureTenantRow()` self-heal if row missing; `patchOnboardingState({nome,email,authMethod})`                                                                                                            | `clientes_vizu.onboarding_state.{nome,email,authMethod}`   |
| 2   | `/onboarding/dna`     | [`BusinessDNA.tsx`](../apps/landing/src/onboarding/steps/BusinessDNA.tsx)         | **Three parallel writes:** `patchOnboardingState`, `saveContextSections({company_profile})`, `updateClientColumn('nome_empresa')`                                                                                                                  | `onboarding_state` + `company_profile` + `nome_empresa`    |
| 3   | `/onboarding/data`    | [`DataFork.tsx`](../apps/landing/src/onboarding/steps/DataFork.tsx)               | `patchOnboardingState({dataPath,systems,csvUploaded,googleDriveConnected})`. Drive OAuth post-redirect: `captureDriveToken()` → `integration_tokens`. ERP/e-commerce: hand off to dashboard `/admin/fontes?connect=<slug>&return=/onboarding/data` | `onboarding_state.*` + (optional) `integration_tokens` row |
| 4   | `/onboarding/agents`  | [`AgentActivation.tsx`](../apps/landing/src/onboarding/steps/AgentActivation.tsx) | `patchOnboardingState({agents})` **only** — no `client_enabled_agents` write yet                                                                                                                                                                   | `onboarding_state.agents`                                  |
| 5   | `/onboarding/rules`   | [`CommandRules.tsx`](../apps/landing/src/onboarding/steps/CommandRules.tsx)       | `patchOnboardingState({approvalTasks,routines,notifyChannel})` — no `client_routines` write yet                                                                                                                                                    | `onboarding_state.*`                                       |
| 6   | `/onboarding/launch`  | [`LaunchPad.tsx`](../apps/landing/src/onboarding/steps/LaunchPad.tsx)             | `runBootstrap(state)` → edge function `onboarding-bootstrap` → `onboarding_bootstrap_tx` RPC + best-effort Langfuse prompt seeding                                                                                                                 | Full tenant provisioned; `onboarding_completed_at` stamped |

**Shared layout:** [`OnboardingLayout.tsx`](../apps/landing/src/onboarding/OnboardingLayout.tsx) (progress bar, `StepHeader`).
**Design tokens:** [`tokens.ts`](../apps/landing/src/onboarding/tokens.ts).

---

## 3. Service layer (typed Supabase wrapper)

[`apps/landing/src/onboarding/services/onboardingService.ts`](../apps/landing/src/onboarding/services/onboardingService.ts) — every wizard step goes through here. Never accepts a `client_id` argument; RLS resolves tenant from the JWT.

| Function                                    | Backing RPC / endpoint                                                               | Used by                                               |
| ------------------------------------------- | ------------------------------------------------------------------------------------ | ----------------------------------------------------- |
| `getOnboardingState()`                      | `SELECT onboarding_state, onboarding_completed_at FROM clientes_vizu` (RLS)          | `useOnboarding` hydrate                               |
| `patchOnboardingState(patch)`               | `merge_onboarding_state(p_patch jsonb)` RPC                                          | Every step's autosave + explicit `handleNext` flushes |
| `saveContextSections(partial)`              | `UPDATE clientes_vizu SET company_profile=… WHERE external_user_id=auth.uid()::text` | BusinessDNA only                                      |
| `updateClientColumn('nome_empresa', value)` | `UPDATE clientes_vizu SET nome_empresa=…`                                            | BusinessDNA                                           |
| `runBootstrap(state)`                       | Edge fn `onboarding-bootstrap` (POST, JWT-verified)                                  | LaunchPad                                             |
| `captureDriveToken()`                       | Edge fn `onboarding-capture-drive-token` (POST, JWT-verified)                        | DataFork `?drive=connected` handler                   |
| `ensureTenantRow()`                         | `public.ensure_tenant_row()` RPC (`SECURITY DEFINER`)                                | Welcome self-heal                                     |

**Mappers:** [`mappers.ts`](../apps/landing/src/onboarding/mappers.ts) (pure, unit-tested in `mappers.test.ts`). The edge function has a **parity copy** at [`supabase/functions/onboarding-bootstrap/mappers.ts`](../supabase/functions/onboarding-bootstrap/mappers.ts) — any change to the landing mapper must be mirrored there.

---

## 4. Database surface

All migrations live in [`supabase/migrations/`](../supabase/migrations/) and are idempotent (`IF NOT EXISTS`, `ON CONFLICT DO UPDATE`).

### Tables

| Object                         | Defined in                                       | Purpose                                                                                                                                                   | RLS                                                            |
| ------------------------------ | ------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| `clientes_vizu` (new columns)  | `20260423130100_onboarding_state_column.sql`     | `onboarding_state jsonb NOT NULL DEFAULT '{}'`, `onboarding_completed_at timestamptz`, partial index `idx_clientes_vizu_onboarding_incomplete`            | existing                                                       |
| `public.client_enabled_agents` | `20260423130200_client_enabled_agents.sql`       | Per-tenant enabled agents. `PRIMARY KEY (client_id, agent_slug)`; FK to `agent_catalog.slug`                                                              | 5 policies scoped via `get_my_client_id()` + service_role full |
| `public.client_routines`       | `20260423130300_client_routines.sql`             | Per-tenant built-in automations. `UNIQUE (client_id, routine_id)`; `notify_channel` CHECK                                                                 | Same pattern                                                   |
| `public.agent_catalog` (seed)  | `20260423130400_agent_catalog_landing_slugs.sql` | Upserts the 8 canonical landing slugs: `analytics, inventory, marketing, crm, scheduling, projects, documents, finance`. `prompt_name` = `landing/<slug>` | existing                                                       |

### Functions / RPCs

| Name                             | Migration                                         | Security           | Callers                                                   |
| -------------------------------- | ------------------------------------------------- | ------------------ | --------------------------------------------------------- |
| `handle_new_auth_user()`         | `20260423130000_onboarding_bootstrap_trigger.sql` | `SECURITY DEFINER` | Trigger `on_auth_user_created AFTER INSERT ON auth.users` |
| `ensure_tenant_row()`            | same                                              | `SECURITY DEFINER` | `Welcome.tsx` fallback, any future self-heal              |
| `merge_onboarding_state(jsonb)`  | `20260423130100_onboarding_state_column.sql`      | `SECURITY INVOKER` | `patchOnboardingState()`                                  |
| `onboarding_bootstrap_tx(jsonb)` | `20260423130500_onboarding_bootstrap_tx.sql`      | `SECURITY INVOKER` | Edge fn `onboarding-bootstrap`                            |

### Row-level security

All three writable tables (`clientes_vizu`, `client_enabled_agents`, `client_routines`) are scoped to the caller's tenant via the single resolver `public.get_my_client_id()` (defined upstream in `20260225_fix_analytics_v2_rls_policies.sql`, which resolves `external_user_id = auth.uid()::text`). Service role gets full access everywhere.

---

## 5. Edge functions

### `onboarding-bootstrap` — [`supabase/functions/onboarding-bootstrap/`](../supabase/functions/onboarding-bootstrap/)

Final atomic provisioning. Called by LaunchPad.

1. Verify JWT via `${SUPABASE_URL}/auth/v1/user`.
2. Parse body as `OnboardingState` (wizard's full state).
3. Build Context 2.0 payload via mappers (`mapBusinessDNAToCompanyProfile`, `mapStateToCurrentMoment`, `mapContactToTeamStructure`, `mapRulesToPolicies`) + pass through `agents`, `routines`, `notify_channel`, `nome_empresa`.
4. Call `public.onboarding_bootstrap_tx(p_payload jsonb)` **with the caller's JWT** (user-scoped client, SECURITY INVOKER, RLS applies). The RPC UPDATEs `clientes_vizu`, UPSERTs `client_enabled_agents`, UPSERTs `client_routines`, stamps `onboarding_completed_at`, all in one transaction.
5. **Best-effort** Langfuse prompt seeding (outside the TX): for each selected agent slug, GET `landing/<slug>` @ `label=production` and POST a `tenant/<client_id>/<slug>` copy tagged `client:<id>`, `agent:<slug>`. Uses `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY`. Failures are logged and recorded to `onboarding_state.langfuse_seed_status` via `merge_onboarding_state` so a retry job can re-run.
6. Return `{ client_id, agents, routines, prompts_seeded }`.

**Idempotency:** re-running with the same payload is a no-op — `ON CONFLICT DO UPDATE` + `COALESCE(onboarding_completed_at, now())`.

### `onboarding-capture-drive-token` — [`supabase/functions/onboarding-capture-drive-token/`](../supabase/functions/onboarding-capture-drive-token/)

Captures the Google Drive refresh token that `supabase.auth.getSession()` exposes immediately after the OAuth redirect (Supabase does **not** persist `provider_refresh_token` server-side).

1. Verify JWT.
2. Resolve `client_id` via `get_my_client_id()` RPC under the caller's JWT.
3. Fernet-encrypt `provider_refresh_token` (and `provider_token` if present) using `CREDENTIALS_ENCRYPTION_KEY` — same scheme as `libs/vizu_context_service` + `google-calendar-events`.
4. Upsert into `integration_tokens` via service role with `onConflict: "client_id,provider,account_email"`, scopes default to Drive + Sheets read-only.
5. Return `{ connected, account_email }`. **No token material ever returned or logged.**

---

## 6. Downstream consumers

| Consumer                                                                                                                | Reads                                                                                    | Notes                                                                                                                                       |
| ----------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| [`apps/vizu_dashboard/src/components/OnboardingBanner.tsx`](../apps/vizu_dashboard/src/components/OnboardingBanner.tsx) | `clientes_vizu.onboarding_completed_at`                                                  | "Continuar onboarding →" banner on HomePage; links back to landing origin `/onboarding/dna` (no redirect loop). `VITE_LANDING_URL` env var. |
| [`libs/vizu_context_service`](../libs/vizu_context_service/)                                                            | `clientes_vizu.{company_profile,current_moment,team_structure,policies,available_tools}` | Already reads these JSONB columns; no code change needed — LaunchPad just populates them.                                                   |
| [`libs/vizu_tool_registry`](../libs/vizu_tool_registry/)                                                                | `agent_catalog.agent_config.enabled_tools`                                               | Source of truth for which tool names are valid. Landing seed validated against `BUILTIN_TOOLS`.                                             |
| [`libs/vizu_prompt_management`](../libs/vizu_prompt_management/)                                                        | Langfuse `tenant/<client_id>/<slug>` @ `label=production`                                | `PromptLoader` resolves per-tenant prompts. Falls back to `landing/<slug>` if tenant copy missing (Langfuse seeding is best-effort).        |
| Future scheduler                                                                                                        | `client_routines WHERE enabled`                                                          | Table is contract-first; backing scheduler TBD.                                                                                             |
| Future agent gallery (dashboard)                                                                                        | `client_enabled_agents`                                                                  | Source of truth for "which agents does this client have".                                                                                   |

---

## 7. Environment variables

| Var                                                                                    | Where                      | Purpose                                                                           |
| -------------------------------------------------------------------------------------- | -------------------------- | --------------------------------------------------------------------------------- |
| `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`                                          | `apps/landing/.env`        | Supabase client ([`lib/supabase.ts`](../apps/landing/src/lib/supabase.ts))        |
| `VITE_DASHBOARD_URL`                                                                   | `apps/landing/.env`        | DataFork connector handoff + LaunchPad redirect target (defaults to `/dashboard`) |
| `VITE_LANDING_URL`                                                                     | `apps/vizu_dashboard/.env` | OnboardingBanner's link back to `/onboarding/dna`                                 |
| `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`                       | Supabase edge runtime      | Both edge fns                                                                     |
| `CREDENTIALS_ENCRYPTION_KEY`                                                           | Supabase edge runtime      | Fernet key (same value used by `libs/vizu_context_service`)                       |
| `LANGFUSE_HOST` (or `LANGFUSE_BASE_URL`), `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` | Supabase edge runtime      | `onboarding-bootstrap` prompt seeding (keys optional — skipped if missing)        |

---

## 8. Testing

| Test                                         | File                                                                                                                                  | Runs                                                                                          |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Pure mapper unit tests (18)                  | [`apps/landing/src/onboarding/mappers.test.ts`](../apps/landing/src/onboarding/mappers.test.ts)                                       | `pnpm --filter landing test` (vitest)                                                         |
| Service layer unit tests (18)                | [`apps/landing/src/onboarding/services/onboardingService.test.ts`](../apps/landing/src/onboarding/services/onboardingService.test.ts) | same                                                                                          |
| Deno parity mapper test                      | [`supabase/functions/onboarding-bootstrap/tests/mappers_test.ts`](../supabase/functions/onboarding-bootstrap/tests/mappers_test.ts)   | `deno test` / CI                                                                              |
| SQL trigger + RLS + bootstrap_tx integration | [`tests/test_landing_onboarding.py`](../tests/test_landing_onboarding.py)                                                             | `pytest tests/test_landing_onboarding.py` (needs `SUPABASE_DB_URL` for RLS role-switch tests) |

**Last run (2026-04-24):** 36/36 vitest + 9 pytest pass, 1 pytest skipped (`exec_sql` not available in hosted Supabase).

---

## 9. Known gotchas / operational notes

- **`supabase db push` is out of sync** with the remote (remote has ~200 migrations not in this repo's `supabase/migrations/`). Apply onboarding migrations with direct `psql "$SUPABASE_DB_URL"`. The pooler connection has an implicit `SET ROLE authenticated` — issue `RESET ROLE;` before any DDL.
- **Deno is not installed locally.** `mappers_test.ts` runs in CI or via `supabase functions serve`.
- **The landing mapper and the edge-fn mapper are two files.** If you change `mappers.ts` in the landing, change it in `supabase/functions/onboarding-bootstrap/mappers.ts` too. A future refactor can lift both to `apps/shared/` and wire path aliases.
- **BusinessDNA writes `company_profile` directly** (bypassing the `onboarding_bootstrap_tx` flow). The RPC uses `COALESCE(v_company_profile, company_profile)` so LaunchPad still merges correctly, but be aware that `company_profile` is non-null before LaunchPad finishes.
- **Drive refresh token.** Google only returns `provider_refresh_token` on the first consent — the DataFork OAuth call sets `access_type=offline` + `prompt=consent` to force it. If a returning user reconnects, they must revoke and re-consent, or the capture step reports `connected: false` with a clear error.
- **Langfuse seeding is best-effort.** If the keys aren't set or the API is unreachable, bootstrap still succeeds; the status is recorded in `onboarding_state.langfuse_seed_status`. A future retry job can re-run by calling the edge function with `langfuse_retry: true` (not yet implemented).
- **Legacy fields removed.** `approvalLimit` and `riskProfile` were kept in `OnboardingState` for backwards-compat with older `localStorage` blobs. They are now fully removed (2026-04-24) since no step or mapper consumed them.
