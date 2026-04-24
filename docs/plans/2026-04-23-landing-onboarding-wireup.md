# Landing Onboarding Wizard — Wire-up to Supabase & Backend Libs

> **For Claude Opus Work Session**
> **Project:** Releases de produto
> **Repository:** vizu-mono
> **Companion docs:** [`docs/plans/2026-04-23-dashboard-mocks-removal.md`](./2026-04-23-dashboard-mocks-removal.md), [`docs/plans/2026-04-22-analytics-v2-minimal-schema-cleanup.md`](./2026-04-22-analytics-v2-minimal-schema-cleanup.md)

---

## Executive Summary

**Goal:** Wire the landing onboarding wizard at [apps/landing/src/onboarding/steps/](../../apps/landing/src/onboarding/steps/) (Auth → Welcome → BusinessDNA → DataFork → AgentActivation → CommandRules → LaunchPad) to Supabase so that each step persists server-side (resumable), triggers the right backend services (Drive OAuth vault, dashboard connector handoff, agent provisioning, Langfuse prompt seeding), and the final LaunchPad fully bootstraps the tenant (clientes_vizu row, Context 2.0 sections, default agents, default prompts, routines, onboarding marked complete).

**Approach:**

1. Bootstrap the tenant eagerly on signup via a Postgres trigger `handle_new_auth_user()` that inserts a stub `clientes_vizu` row keyed by `auth.uid()` — closes the chicken-and-egg where `public.get_my_client_id()` (email-based) needs the row to already exist.
2. Add a single `onboarding_state JSONB` column plus `onboarding_completed_at TIMESTAMPTZ` to `clientes_vizu`. Each step autosaves server-side via a typed service (mirroring [`apps/vizu_dashboard/src/services/onboardingService.ts`](../../apps/vizu_dashboard/src/services/onboardingService.ts)).
3. Introduce two new RLS-scoped tables: `client_enabled_agents` and `client_routines`, plus a small migration that extends `agent_catalog` with the landing's "canonical" agent slugs (analytics, crm, marketing, inventory, scheduling, projects, documents, finance) so the wizard's selections map 1:1 to real catalog rows.
4. Drive OAuth refresh token → `integration_tokens` (existing). ERP/e-commerce connectors continue to use the dashboard's `/admin/fontes?connect=<slug>&return=/onboarding/data` handoff (already coded in `DataFork.tsx`).
5. Final LaunchPad step calls **one edge function `onboarding-bootstrap`** that (a) writes Context 2.0 JSONB from wizard state, (b) provisions `client_enabled_agents`, (c) ensures per-client default Langfuse prompts (idempotent copy from `default/*` label), (d) inserts `client_routines`, (e) stamps `onboarding_completed_at`. Uses service role for Langfuse seeding.

**Estimated Complexity:** Medium-High (schema + trigger + edge function + 6 React steps to re-wire + idempotency + RLS validation).

**Key Dependencies (existing, reused):**

- [`libs/vizu_supabase_client`](../../libs/vizu_supabase_client) — Python Supabase client with RLS helpers (used by edge function proxy if Python-side needed; direct Deno use for the edge fn itself).
- [`libs/vizu_auth`](../../libs/vizu_auth) — JWT/email resolvers for FastAPI services (not used directly by landing, but by downstream services that consume the new tables).
- [`libs/vizu_context_service`](../../libs/vizu_context_service) — already reads `company_profile / current_moment / team_structure / policies / available_tools` JSONB on `clientes_vizu`. LaunchPad only has to populate those columns — no code change in this lib.
- [`libs/vizu_tool_registry`](../../libs/vizu_tool_registry) — `ToolRegistry.get_available_tools(enabled_tools, tier)` is the source of truth for which tool names are valid. Wizard's agent → tools mapping lives in `agent_catalog.agent_config.enabled_tools`.
- [`libs/vizu_agent_framework`](../../libs/vizu_agent_framework) — `AgentConfig` dataclass shape is already mirrored 1:1 by `agent_catalog.agent_config`. No change.
- [`libs/vizu_prompt_management`](../../libs/vizu_prompt_management) — `PromptLoader` resolves Langfuse prompts by `label` (default `production`). Bootstrap uses the Langfuse public API (same pattern as [`scripts/create_standalone_prompts.py`](../../scripts/create_standalone_prompts.py)) to ensure tenant-scoped labels exist.
- [`libs/vizu_data_connectors`](../../libs/vizu_data_connectors) — connectors are configured through the dashboard's `/admin/fontes` flow which already writes to `credencial_servico_externo` + `client_data_sources`. Landing only hands off via URL.
- `public.get_my_client_id()` ([migration 20260225](../../supabase/migrations/20260225_fix_analytics_v2_rls_policies.sql#L7)) — email-based RLS resolver.
- Existing tables: `clientes_vizu`, `agent_catalog`, `integration_configs`, `integration_tokens`, `credencial_servico_externo`, `client_data_sources`, `uploaded_files_metadata`.
- Existing Vault RPCs: `store_credential_in_vault`, `get_credential_from_vault` (for Google refresh token if storing in vault instead of `integration_tokens`).

---

## Architecture Overview

### Data flow

```
┌───────────────────────────────────────────────────────────────────────────┐
│ Browser (apps/landing, React + Chakra + react-router)                     │
│                                                                           │
│  Auth  ─────────▶  supabase.auth.signUp / signInWithOAuth(google)         │
│    │                           │                                          │
│    │                           ▼                                          │
│    │                  auth.users INSERT   ──trigger──▶  clientes_vizu     │
│    │                                                   (stub row, RLS ok) │
│    ▼                                                                      │
│  Welcome (OAuth callback) — hydrate name/email                            │
│    │                                                                      │
│    ▼                                                                      │
│  BusinessDNA ──┐                                                          │
│  DataFork      │    apps/landing/src/onboarding/services/                 │
│  AgentActiv.   ├──▶ onboardingService.ts  (NEW)                           │
│  CommandRules  │         │                                                │
│                │         ▼  PostgREST (schema=public, RLS)                │
│                │   UPDATE clientes_vizu.onboarding_state  (JSONB patch)   │
│                │                                                          │
│  DataFork ─────┼──▶ supabase.auth.signInWithOAuth('google', scopes=drive) │
│                │         │                                                │
│                │         ▼  post-redirect hook                            │
│                │   onboarding-seed-drive-token edge fn  ──▶ vault /       │
│                │                                             integration_tokens
│                │                                                          │
│                │   ERP/e-commerce connectors: window.location → dashboard │
│                │   /admin/fontes?connect=<slug>&return=/onboarding/data   │
│                │                                                          │
│  LaunchPad ────┴──▶ supabase.functions.invoke('onboarding-bootstrap')     │
│                                       │                                   │
└───────────────────────────────────────┼───────────────────────────────────┘
                                        │ service role
                                        ▼
                 ┌──────────────────────┴────────────────────────┐
                 │  Edge Function: onboarding-bootstrap (Deno)   │
                 │  1. Validate JWT → client_id                  │
                 │  2. UPSERT Context 2.0 JSONB on clientes_vizu │
                 │  3. INSERT client_enabled_agents (idempotent) │
                 │  4. INSERT client_routines      (idempotent)  │
                 │  5. Ensure Langfuse labels via public API     │
                 │  6. Stamp onboarding_completed_at             │
                 └──────────────────┬────────────────────────────┘
                                    │
                                    ▼
                 Langfuse (prompt labels) + Postgres (RLS-scoped writes)
```

### Component interaction

- **Service layer (new):** [`apps/landing/src/onboarding/services/onboardingService.ts`](../../apps/landing/src/onboarding/services/onboardingService.ts) — CRUD against `clientes_vizu.onboarding_state` + Context 2.0 columns. **Mirror shape of [`apps/vizu_dashboard/src/services/onboardingService.ts`](../../apps/vizu_dashboard/src/services/onboardingService.ts)** (same typed helpers, same error handling).
- **State hook:** extend [`apps/landing/src/onboarding/state.ts`](../../apps/landing/src/onboarding/state.ts) `useOnboarding()` so `update(patch)` debounces a server autosave (300 ms) once a session is present. Keep localStorage as fast-path cache; server is the source of truth after login.
- **Mappers (new):** [`apps/landing/src/onboarding/mappers.ts`](../../apps/landing/src/onboarding/mappers.ts) — pure functions turning `OnboardingState` → `{ company_profile, current_moment, team_structure, policies }` Context 2.0 payloads (reuses shapes from [`apps/vizu_dashboard/src/types/onboarding.ts`](../../apps/vizu_dashboard/src/types/onboarding.ts)).
- **Edge Function:** [`supabase/functions/onboarding-bootstrap/index.ts`](../../supabase/functions/onboarding-bootstrap/index.ts) (new). `verify_jwt: true`. Orchestrates tenant provisioning.
- **Drive OAuth capture:** new tiny edge function `onboarding-capture-drive-token` invoked right after the Drive OAuth redirect in `DataFork.tsx` (via the `?drive=connected` handler). Reads the provider token from `supabase.auth.getSession()` (Supabase returns `provider_refresh_token` when `access_type=offline` + `prompt=consent`) and persists it via `integration_tokens` (encrypted) using service role. Alternative covered in Risks.
- **Connector handoff:** no new code — `DataFork.tsx` already redirects to `/dashboard/admin/fontes?connect=<slug>&return=/onboarding/data`. The dashboard's existing flow writes to `credencial_servico_externo` + `client_data_sources`. We only add a post-return hook that re-persists onboarding state (already handled by the existing `?drive=connected` parser pattern).

### Reusable assets created

| Type              | Name                                                                                                                       | Where                                                                                                          | Why reusable                                                                                                             |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `[NEW TRIGGER]`   | `handle_new_auth_user()` on `auth.users` AFTER INSERT                                                                      | new migration                                                                                                  | Fixes the "no tenant row yet" problem across the whole product, not just onboarding.                                     |
| `[NEW COLUMNS]`   | `clientes_vizu.onboarding_state JSONB`, `onboarding_completed_at TIMESTAMPTZ`                                              | new migration                                                                                                  | Server-side resumable state; also exposed to dashboard to show "continue onboarding" banners.                            |
| `[NEW TABLE]`     | `public.client_enabled_agents (client_id, agent_slug, enabled, activated_at, source)`                                      | new migration                                                                                                  | Becomes the single source of truth for "which agents does this client have" — consumed later by dashboard/agent gallery. |
| `[NEW TABLE]`     | `public.client_routines (client_id, routine_id, enabled, config JSONB, notify_channel, created_at)`                        | new migration                                                                                                  | First-class routine registry — reused by future automation/cron scheduler and by CommandRules UI in the dashboard.       |
| `[NEW MIGRATION]` | Extend `agent_catalog` with landing slugs (analytics, crm, marketing, inventory, scheduling, projects, documents, finance) | new migration                                                                                                  | Landing UI maps 1:1 to the canonical catalog; no translation layer needed at runtime.                                    |
| `[NEW EDGE FN]`   | `onboarding-bootstrap`                                                                                                     | [supabase/functions/onboarding-bootstrap/](../../supabase/functions/onboarding-bootstrap/)                     | Reusable for admin "re-bootstrap" button + future tenant migration scripts.                                              |
| `[NEW EDGE FN]`   | `onboarding-capture-drive-token`                                                                                           | [supabase/functions/onboarding-capture-drive-token/](../../supabase/functions/onboarding-capture-drive-token/) | Pure Drive-token capture — isolates provider-token handling so it can be reused by any future Google scope expansion.    |
| `[NEW TS MODULE]` | `apps/landing/src/onboarding/services/onboardingService.ts`                                                                | —                                                                                                              | Mirrors dashboard service. Both can later be extracted to `apps/shared/` if a third surface needs it.                    |
| `[NEW TS MODULE]` | `apps/landing/src/onboarding/mappers.ts`                                                                                   | —                                                                                                              | Pure wizard-state → Context 2.0 converter; covered by unit tests.                                                        |

---

## Phase 1: Foundation — Schema, Trigger, RLS

**Objective:** Land every schema change so that (a) `clientes_vizu` row exists at first sign-in, (b) wizard state can be written server-side under RLS, (c) downstream tables for agents + routines exist.

**Success Criteria:**

- After a fresh `auth.signUp`, `SELECT public.get_my_client_id()` returns the new `client_id` (not null).
- `supabase db advisors` clean (no new RLS / search_path warnings).
- RLS smoke: two test users cannot read each other's `onboarding_state`, `client_enabled_agents`, `client_routines`.

### Tasks

1. **Read existing patterns to copy verbatim**
   - Trigger + `SECURITY DEFINER` pattern: study [`20260225_fix_analytics_v2_rls_policies.sql:7`](../../supabase/migrations/20260225_fix_analytics_v2_rls_policies.sql#L7) (`get_my_client_id`). Copy its preamble (`LANGUAGE sql STABLE SECURITY DEFINER`).
   - RLS scope pattern (per `get_my_client_id()`): [`20260227_fix_dim_inventory_rls_and_regional_view.sql:13`](../../supabase/migrations/20260227_fix_dim_inventory_rls_and_regional_view.sql#L13) and [`20260423120300_public_calendar_settings.sql`](../../supabase/migrations/20260423120300_public_calendar_settings.sql) — use exact same `USING` + `WITH CHECK` structure.
   - Column-add pattern: [`20260410_add_context_sections_to_clientes_vizu.sql`](../../supabase/migrations/20260410_add_context_sections_to_clientes_vizu.sql) — use `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`.

2. **Migration: `onboarding_bootstrap_trigger`**
   - File: `supabase migration new onboarding_bootstrap_trigger`.
   - Function `public.handle_new_auth_user()` (`SECURITY DEFINER`, search_path pinned to `public`): INSERT into `clientes_vizu` `(client_id, external_user_id, email, nome_empresa)` with values `(NEW.id, NEW.id::text, NEW.email, coalesce(NEW.raw_user_meta_data->>'full_name','Empresa'))` `ON CONFLICT (client_id) DO NOTHING`. Email MUST be present so `get_my_client_id()` (email lookup) resolves on the next request.
   - Trigger `on_auth_user_created AFTER INSERT ON auth.users FOR EACH ROW EXECUTE FUNCTION public.handle_new_auth_user()`.
   - **Guard:** `clientes_vizu_auth_check` currently requires `api_key IS NOT NULL OR external_user_id IS NOT NULL` — already satisfied. `clientes_vizu.email` column does **not** exist today; add it in the same migration (`ADD COLUMN IF NOT EXISTS email TEXT`). Backfill: `UPDATE clientes_vizu c SET email = u.email FROM auth.users u WHERE c.external_user_id = u.id::text AND c.email IS NULL;`.

3. **Migration: `onboarding_state_column`**
   - `ALTER TABLE public.clientes_vizu ADD COLUMN IF NOT EXISTS onboarding_state JSONB NOT NULL DEFAULT '{}'::jsonb, ADD COLUMN IF NOT EXISTS onboarding_completed_at TIMESTAMPTZ;`.
   - Existing RLS on `clientes_vizu` (update by owner) already covers writes — no new policy needed.
   - Index: `CREATE INDEX IF NOT EXISTS idx_clientes_vizu_onboarding_incomplete ON clientes_vizu(client_id) WHERE onboarding_completed_at IS NULL;` (used by dashboard "resume onboarding" banner).

4. **Migration: `client_enabled_agents`**
   - Table outline:
     ```
     public.client_enabled_agents (
       client_id UUID NOT NULL REFERENCES clientes_vizu(client_id) ON DELETE CASCADE,
       agent_slug TEXT NOT NULL REFERENCES agent_catalog(slug),
       enabled BOOLEAN NOT NULL DEFAULT true,
       source TEXT NOT NULL DEFAULT 'onboarding',  -- 'onboarding' | 'admin'
       activated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
       PRIMARY KEY (client_id, agent_slug)
     )
     ```
   - RLS enabled; SELECT/INSERT/UPDATE/DELETE policies for role `authenticated` scoped via `client_id::text = public.get_my_client_id()`. Service role full access.

5. **Migration: `client_routines`**
   - Table outline:
     ```
     public.client_routines (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       client_id UUID NOT NULL REFERENCES clientes_vizu(client_id) ON DELETE CASCADE,
       routine_id TEXT NOT NULL,                    -- matches landing RoutineId enum
       enabled BOOLEAN NOT NULL DEFAULT true,
       config JSONB NOT NULL DEFAULT '{}'::jsonb,   -- per-routine params (cron, thresholds, …)
       notify_channel TEXT NOT NULL DEFAULT 'email',
       created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
       UNIQUE (client_id, routine_id)
     )
     ```
   - Same RLS pattern as `client_enabled_agents`.
   - Comment on `routine_id`: "Enum mirrored from `apps/landing/src/onboarding/state.ts::RoutineId`. Backing scheduler TBD."

6. **Migration: `agent_catalog_landing_slugs`**
   - Upsert rows for landing's 8 canonical agents (analytics, crm, marketing, inventory, scheduling, projects, documents, finance).
   - `agent_config` JSONB must be `AgentConfig`-shaped (see [`libs/vizu_agent_framework/src/vizu_agent_framework/config.py`](../../libs/vizu_agent_framework/src/vizu_agent_framework/config.py)). `enabled_tools` must only use names present in `ToolRegistry.BUILTIN_TOOLS` or existing Docker MCP tool slugs (validate against [`libs/vizu_tool_registry/src/vizu_tool_registry/registry.py`](../../libs/vizu_tool_registry/src/vizu_tool_registry/registry.py)).
   - `prompt_name` values: `landing/analytics`, `landing/crm`, … — these get auto-seeded in Langfuse by Phase 4 edge function.
   - `INSERT … ON CONFLICT (slug) DO UPDATE` so re-runs are idempotent.

7. **Advisor + smoke**
   - Run `mcp_supabase_get_advisors type=security` and `type=performance`. No new warnings allowed.
   - Manual: `SET LOCAL ROLE authenticated; SET request.jwt.claim.email = '<user>'` → SELECT from each new table, assert only own rows visible.

---

## Phase 2: Landing Service Layer

**Objective:** A single typed module that every wizard step uses to autosave and read onboarding state. Mirrors dashboard shape so later consolidation is trivial.

**Dependencies:** Phase 1 applied to dev DB.

**Success Criteria:**

- `pnpm --filter landing typecheck` passes.
- Refreshing the landing app at any step rehydrates server state (not just localStorage).

### Tasks

1. **Copy dashboard service as starting point**
   - Reference: [`apps/vizu_dashboard/src/services/onboardingService.ts`](../../apps/vizu_dashboard/src/services/onboardingService.ts) (very small file; use same functional style).
   - New file: `apps/landing/src/onboarding/services/onboardingService.ts`.

2. **Function signatures (interfaces only — no bodies here)**

   ```ts
   getOnboardingState(): Promise<OnboardingStateRecord | null>     // SELECT onboarding_state, onboarding_completed_at
   patchOnboardingState(patch: Partial<OnboardingState>): Promise<void>   // jsonb_set-style merge via UPDATE
   saveContextSections(partial: Partial<OnboardingData>): Promise<void>    // reuses dashboard pattern
   runBootstrap(payload: BootstrapPayload): Promise<BootstrapResult>       // invokes edge fn
   captureDriveToken(): Promise<{ connected: boolean }>                    // invokes drive-token edge fn
   ```

   - `BootstrapPayload` = the full wizard state (server re-validates). Keeping this explicit means the wizard can call bootstrap even if a user arrived with stale server state.

3. **Merge strategy for `patchOnboardingState`**
   - Use Postgres `jsonb_set` / `||` via an RPC helper `public.merge_onboarding_state(p_patch jsonb)` — avoids read-modify-write races when Drive OAuth and BusinessDNA autosave concurrently.
   - Add the RPC in the same migration as `onboarding_state_column` (move up to Phase 1 if needed — decision deferred to implementation). `SECURITY INVOKER`, writes to `clientes_vizu WHERE client_id = public.get_my_client_id()::uuid`.

4. **Type contracts**
   - Add `apps/landing/src/onboarding/types.ts` that imports the Context 2.0 types from `apps/vizu_dashboard/src/types/onboarding.ts` via a relative path. Do **not** duplicate — use a shared import or lift to `apps/shared/onboarding-types.ts` if path awkward (decision point for implementation).

5. **Autosave in `state.ts::useOnboarding`**
   - Add a `useEffect` with `useDebouncedCallback` (300 ms) that, if `supabase.auth.getSession()` returns a session, calls `patchOnboardingState`. Failures log + continue (localStorage remains authoritative until recovery).
   - Hydrate: on first mount, if session present, call `getOnboardingState()` and merge server state on top of localStorage default.

---

## Phase 3: Step-by-step Wire-up (BusinessDNA, DataFork, AgentActivation, CommandRules)

**Objective:** Every `handleNext` writes the relevant slice to Supabase before navigating. No navigation happens on a failed write (toast + retry).

**Dependencies:** Phases 1 & 2.

**Success Criteria:**

- Every step navigation corresponds to a Supabase write visible in `supabase logs(service='postgres')`.
- Leaving the wizard mid-flow and returning reconstitutes exact state from the server (localStorage cleared in test).

### Tasks

1. **BusinessDNA** ([`steps/BusinessDNA.tsx`](../../apps/landing/src/onboarding/steps/BusinessDNA.tsx))
   - `handleNext` (line 37) additionally calls:
     - `patchOnboardingState({ empresa, vertical, porte, website })`
     - `saveContextSections({ company_profile: mapBusinessDNAToCompanyProfile(state) })` — via `mappers.ts`.
   - Also UPDATE `clientes_vizu.nome_empresa = empresa` (top-level column used by `ContextService`).
   - Add error boundary: block navigation on failure.

2. **DataFork** ([`steps/DataFork.tsx`](../../apps/landing/src/onboarding/steps/DataFork.tsx))
   - `handleNext` persists `{ dataPath, systems, csvUploaded, googleDriveConnected }` into `onboarding_state`.
   - CSV upload: on file select, call existing file-upload API ([`services/file_upload_api/`](../../services/file_upload_api/)) — the endpoint already writes to `uploaded_files_metadata`. Pass `source='onboarding'` tag.
   - Drive OAuth post-redirect (`?drive=connected` branch, line 55): call **new** `captureDriveToken()` which invokes `onboarding-capture-drive-token` edge fn. Persist `googleDriveConnected=true` only if that returns success.
   - Connector redirect (`openConnector`, line 114): no backend change — dashboard already handles it. Just ensure the current persisted state is flushed (`await patchOnboardingState(...)`) **before** `window.location.href = …` so the autosave debounce doesn't get cut off.

3. **AgentActivation** ([`steps/AgentActivation.tsx`](../../apps/landing/src/onboarding/steps/AgentActivation.tsx))
   - `handleNext` persists `{ agents }` into `onboarding_state`.
   - No insert into `client_enabled_agents` yet — that happens atomically in LaunchPad bootstrap. Rationale: if user backs out before Launch, we don't want half-provisioned agents.

4. **CommandRules** ([`steps/CommandRules.tsx`](../../apps/landing/src/onboarding/steps/CommandRules.tsx))
   - `handleNext` persists `{ approvalTasks, routines, notifyChannel }` into `onboarding_state`.
   - Same "no side-effects until Launch" rule.

5. **Welcome** ([`steps/Welcome.tsx`](../../apps/landing/src/onboarding/steps/Welcome.tsx))
   - On OAuth callback hydrate (line 19), after `update({...})`, also call `patchOnboardingState({ nome, email, authMethod })` so the server state matches.

6. **Auth** ([`steps/Auth.tsx`](../../apps/landing/src/onboarding/steps/Auth.tsx))
   - No change needed — the trigger from Phase 1 creates the `clientes_vizu` row automatically. Add a fallback: in `Welcome.tsx`, after session is present, call a no-op `getOnboardingState()` and if it returns `null` (row missing for any reason), call an idempotent `public.ensure_tenant_row()` RPC to self-heal.

---

## Phase 4: LaunchPad — Bootstrap Edge Function

**Objective:** One atomic, idempotent call that turns a wizard-complete user into a fully provisioned tenant.

**Dependencies:** Phases 1–3.

**Success Criteria:**

- Running LaunchPad twice is a no-op on the second run (idempotency validated by test).
- After successful run: Context 2.0 columns populated, `client_enabled_agents` has one row per selected agent, `client_routines` has rows for each selected routine, Langfuse has `landing/<slug>` labels pointing at production for this client, `onboarding_completed_at` is set.
- Dashboard at `/dashboard` renders without mocks for this user.

### Tasks

1. **Read existing edge-fn skeletons**
   - Study [`supabase/functions/run-sync/`](../../supabase/functions/run-sync/) and [`supabase/functions/process-document/`](../../supabase/functions/process-document/) for the canonical Deno + `jsr:@supabase/functions-js/edge-runtime.d.ts` layout and JWT→`client_id` resolution pattern.

2. **Create `supabase/functions/onboarding-bootstrap/index.ts`**
   - `verify_jwt: true`.
   - Inputs (POST body): `{ state: OnboardingState }`. Redundancy over server state is intentional — makes the function self-contained and re-runnable.
   - Steps, all inside a single SQL transaction via `supabase.rpc('onboarding_bootstrap_tx', { p_payload })`:
     1. Resolve `client_id` via JWT email → `clientes_vizu`. Fail closed if missing.
     2. UPDATE `clientes_vizu` with mapped Context 2.0 (`company_profile`, `current_moment`, `team_structure`, `policies`, `available_tools`). Use the same mappers as the landing but server-side (TS module shared via `import_map`).
     3. UPSERT `client_enabled_agents` for each slug in `state.agents`. Validate each slug exists in `agent_catalog` (Phase 1 seed guarantees it).
     4. UPSERT `client_routines` for each `routines[]` with `notify_channel`.
     5. UPDATE `clientes_vizu.onboarding_completed_at = now()` (only once; use `COALESCE` to preserve earlier value on re-run).
   - Side-effect step (outside the transaction, best-effort, logged): 6. For each selected agent, ensure a Langfuse prompt label exists. Strategy: call Langfuse `/api/public/v2/prompts` (same auth as [`scripts/create_standalone_prompts.py:453`](../../scripts/create_standalone_prompts.py#L453)) to POST a new prompt named `tenant/<client_id>/<agent_slug>` copying body from `default/<agent_slug>` with label `production`. If already exists, no-op. Use Langfuse keys from env (same env vars `LANGFUSE_PUBLIC_KEY/SECRET_KEY` as the scripts).
   - Return: `{ client_id, agents: n, routines: m, prompts_seeded: k }`.

3. **Create wrapping RPC `public.onboarding_bootstrap_tx(p_payload jsonb)`**
   - `SECURITY INVOKER`. All writes pass through RLS; no service-role bypass needed because all writes are in the caller's tenant. (Service role is only used for the Langfuse HTTP side-effect step 6, which happens outside SQL.)
   - Wraps steps 2–5 in a single statement block for atomicity.

4. **Wire LaunchPad** ([`steps/LaunchPad.tsx`](../../apps/landing/src/onboarding/steps/LaunchPad.tsx))
   - Add a "Ativando seu time de agentes…" loading state on mount. Call `runBootstrap(state)`. On success, redirect to dashboard. On failure, show retry button (keep current visual "checklist" as-is).
   - Do not redirect to `/dashboard` until bootstrap resolves — otherwise dashboard will load without `client_enabled_agents` rows.

5. **Dashboard entry gate**
   - In [`apps/vizu_dashboard`](../../apps/vizu_dashboard/) root route, if `onboarding_completed_at IS NULL` AND `client_id` exists, show a single-line banner with "Continuar onboarding →" link to `/onboarding/dna` on the landing origin. No redirect loop.

---

## Phase 5: Drive OAuth Token Capture

**Objective:** After the Google Drive scope is granted in `DataFork`, persist the refresh token securely so downstream agents can actually read Drive on the user's behalf.

**Dependencies:** Phase 1 (stub row exists).

**Success Criteria:**

- After Drive OAuth, a row exists in `integration_tokens` for `(client_id, provider='google', account_email=<user>)`.
- No access tokens are ever logged or stored in plain text.

### Tasks

1. **Read existing pattern**
   - [`supabase/migrations/20260316_create_integration_tokens.sql`](../../supabase/migrations/20260316_create_integration_tokens.sql) — confirm Fernet encryption is done application-side.
   - [`scripts/seed_google_oauth_vault.py`](../../scripts/seed_google_oauth_vault.py) — shows the vault path for platform-level creds (not per-client). Per-client stays in `integration_tokens`.

2. **Edge function `supabase/functions/onboarding-capture-drive-token/index.ts`**
   - `verify_jwt: true`.
   - Reads the current Supabase session's `provider_refresh_token` (Supabase exposes this on the admin user object; the function pulls via the admin API using service role because a pure browser session token does not expose `provider_refresh_token` after the first read). Pattern: `supabaseAdmin.auth.admin.getUserById(user.id)` then read `identities[].identity_data.provider_token` / `provider_refresh_token`. Confirm exact field names against Supabase docs during implementation.
   - Fernet-encrypt refresh token using `CREDENTIALS_ENCRYPTION_KEY` env (same key already used by `ContextService`).
   - UPSERT `integration_tokens (client_id, provider='google', account_email, refresh_token_encrypted, scopes, is_default=true)`.
   - Response: `{ connected: true, account_email }` (no token material leaked).

3. **Client call**
   - In `DataFork.tsx`'s `?drive=connected` branch, invoke this function before flipping `driveConnected=true`. If it fails, show a toast and keep `driveConnected=false`.

---

## Phase 6: Testing

**Objective:** Automated coverage for RLS, mapping, idempotency, and E2E wizard.

**Success Criteria:**

- New pytest file for RLS isolation on the three new tables.
- Vitest unit tests for `mappers.ts` (wizard state → Context 2.0) — 100 % branch coverage on the mapper.
- Cypress/Playwright E2E: signup → complete all 6 steps → land on dashboard with populated home metrics.

### Tasks

1. **SQL RLS tests** (Python, pytest — pattern like [`tests/test_dashboard_rpcs.py`](../../tests/test_dashboard_rpcs.py))
   - Create two seed users via `auth.admin.create_user`.
   - For each new table: user A writes; user B reads → must be empty; user B writes own; user A reads own only.
   - Assert `handle_new_auth_user` trigger produces `clientes_vizu` row with `email` populated within the same transaction window.

2. **Edge function tests**
   - Deno test file under `supabase/functions/onboarding-bootstrap/tests/`. Mock Langfuse HTTP with `msw`-equivalent or a local stub. Assert idempotency by calling twice and checking row counts.

3. **Frontend unit tests**
   - `mappers.test.ts` — table-driven cases for each vertical + dataPath combination.
   - `onboardingService.test.ts` — mocks `supabase` client and asserts the correct RPC / invoke calls.

4. **E2E smoke**
   - Add a single Playwright spec under `apps/landing/e2e/` (new folder) that walks the wizard end to end against a local Supabase stack. Use the existing docker-compose setup ([`docker-compose.yml`](../../docker-compose.yml)).

---

## DB Migration Inventory (summary)

| Order | File                                        | Summary                                                                                                                        |
| ----- | ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| 1     | `YYYYMMDD_onboarding_bootstrap_trigger.sql` | Add `clientes_vizu.email`; trigger on `auth.users` → stub `clientes_vizu` row; backfill email for existing rows.               |
| 2     | `YYYYMMDD_onboarding_state_column.sql`      | Add `onboarding_state JSONB`, `onboarding_completed_at TIMESTAMPTZ`; index on incomplete; `merge_onboarding_state(jsonb)` RPC. |
| 3     | `YYYYMMDD_client_enabled_agents.sql`        | New table + RLS (`get_my_client_id`) + service-role full-access policy.                                                        |
| 4     | `YYYYMMDD_client_routines.sql`              | New table + RLS + service-role full-access policy.                                                                             |
| 5     | `YYYYMMDD_agent_catalog_landing_slugs.sql`  | Upsert 8 canonical slugs with validated `agent_config.enabled_tools`.                                                          |
| 6     | `YYYYMMDD_onboarding_bootstrap_tx.sql`      | `public.onboarding_bootstrap_tx(jsonb)` RPC used by edge fn.                                                                   |

---

## Edge Function / RPC Inventory

| Name                                    | Type    | Auth               | Purpose                                                      |
| --------------------------------------- | ------- | ------------------ | ------------------------------------------------------------ |
| `onboarding-bootstrap`                  | Edge Fn | `verify_jwt`       | Provisions tenant at LaunchPad.                              |
| `onboarding-capture-drive-token`        | Edge Fn | `verify_jwt`       | Persists Google Drive refresh token in `integration_tokens`. |
| `public.handle_new_auth_user`           | Trigger | `SECURITY DEFINER` | Auto-create `clientes_vizu` row on signup.                   |
| `public.merge_onboarding_state(jsonb)`  | RPC     | `SECURITY INVOKER` | Race-free JSONB merge into `onboarding_state`.               |
| `public.ensure_tenant_row()`            | RPC     | `SECURITY INVOKER` | Self-heal for missing rows (fallback).                       |
| `public.onboarding_bootstrap_tx(jsonb)` | RPC     | `SECURITY INVOKER` | Transactional write of Context 2.0 + agents + routines.      |

---

## Risks & Mitigations

| Risk                                                                                                                                   | Likelihood | Mitigation                                                                                                                                                                                                                                                                                                                                        |
| -------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --- | ---------------------------------- |
| `get_my_client_id()` lookup is by `email`, but signup with unconfirmed email may produce a session before `email_confirmed_at` is set. | M          | Landing already uses `email` from the signUp payload. Trigger stores the raw email regardless of confirmation. RLS resolver uses `auth.jwt()->>'email'` which is always populated.                                                                                                                                                                |
| Trigger on `auth.users` can fail silently on existing deployments with non-standard schemas.                                           | L          | Use `ON CONFLICT (client_id) DO NOTHING`; add `EXCEPTION WHEN OTHERS THEN NULL` wrapper with `RAISE WARNING`. Backfill migration handles pre-existing users.                                                                                                                                                                                      |
| Provider refresh token not accessible from pure browser session (Supabase only exposes it once, usually via the admin API).            | M          | Capture via server-side edge fn using service role right after redirect. Document in code comment; fall back to re-prompting user if capture fails.                                                                                                                                                                                               |
| Langfuse seeding depends on an external service being reachable from the edge function.                                                | M          | Treat as best-effort, outside the transaction. Record `langfuse_seed_status` in `onboarding_state` so a retry job can re-run. Langfuse fallback already handled by `PromptLoader` circuit breaker ([`libs/vizu_prompt_management/src/vizu_prompt_management/loader.py`](../../libs/vizu_prompt_management/src/vizu_prompt_management/loader.py)). |
| Wizard `agents[]` IDs drift from `agent_catalog.slug`.                                                                                 | M          | Phase 1 seed migration establishes the canonical slugs; `client_enabled_agents.agent_slug` has a FK so any drift is caught at write time in tests.                                                                                                                                                                                                |
| Autosave races between Drive OAuth redirect and BusinessDNA step.                                                                      | L          | `merge_onboarding_state` RPC uses `jsonb                                                                                                                                                                                                                                                                                                          |     | ` server-side — commutative merge. |
| Connector handoff to dashboard (`/admin/fontes?connect=...`) leaves the landing session and may lose local state.                      | L          | Already handled by current `DataFork.tsx` pattern. Add an `await patchOnboardingState(...)` before the redirect so server state is authoritative.                                                                                                                                                                                                 |
| Cross-app session (landing → dashboard) requires shared Supabase session.                                                              | L          | Already set up: [`apps/landing/src/lib/supabase.ts`](../../apps/landing/src/lib/supabase.ts) uses the same PKCE + `detectSessionInUrl` config as dashboard.                                                                                                                                                                                       |
| `clientes_vizu_auth_check` CHECK constraint blocks trigger insert if email column is missing.                                          | L          | Column added in same migration; backfill runs before trigger is enabled (use `CREATE TRIGGER` after backfill statement).                                                                                                                                                                                                                          |

---

## Library / Schema Reuse Decisions

- **Do** reuse `clientes_vizu` JSONB Context 2.0 columns — do not invent a separate `onboarding_answers` table. The wizard's output shape already maps cleanly onto Context 2.0.
- **Do** reuse `agent_catalog` — do not introduce a landing-specific catalog. Extend it with the 8 landing slugs in the seed migration.
- **Do** reuse `integration_tokens` for Drive — do not use Vault (Vault is for platform-level secrets per the existing pattern in [`seed_google_oauth_vault.py`](../../scripts/seed_google_oauth_vault.py)).
- **Do not** duplicate the Context 2.0 TypeScript types — import from [`apps/vizu_dashboard/src/types/onboarding.ts`](../../apps/vizu_dashboard/src/types/onboarding.ts) (or lift to a shared module in a later refactor).
- **Do** keep the Drive + ERP connector flows split: Drive is a Supabase-native OAuth (scope added to the same Google provider), ERP/e-commerce stays in the dashboard's existing `credencial_servico_externo` admin flow.

---

## Open Questions (flag for PM before implementation)

1. Should ERP/e-commerce connectors (Shopify, VTEX, etc.) be completable from within the landing, or is the dashboard handoff (current) acceptable long-term? The plan assumes the latter.
2. Is there a tier gate on routines (e.g., `churn_signal` only for BASIC+)? If yes, add `tier_required` to `client_routines` and enforce in bootstrap.
3. Who owns the actual scheduler for `client_routines`? This plan only provisions the table — execution belongs to a future plan.
