# Dashboard Mocks → Live Data — Implementation Plan

> **[ARCHIVE — completed]** Phases 1–6 shipped on 2026-04-26 and the work is
> now folded into the Blu MVP roadmap
> ([`../2026-04-26-blu-mvp-roadmap.md`](../2026-04-26-blu-mvp-roadmap.md)).
> Kept for historical reference only — do not extend.
>
> **For Claude Opus Work Session**
> **Project:** Releases de produto
> **Repository:** CidLucas/platform
> **Companion docs:** [`dashboard-placeholders.md`](../dashboard-placeholders.md), [`dashboard-live-metrics.md`](../dashboard-live-metrics.md)

---

## Executive Summary

**Goal:** Remove every hard-coded / mocked element from the user-facing dashboard and wire it to Supabase using existing patterns (`analytics_v2` views, RPCs, RLS via `public.get_my_client_id()`).

**Approach:** Strategy A across the board — connect every placeholder to a real data source. New SQL artefacts follow the established `SECURITY INVOKER` RPC pattern in `analytics_v2`/`public`. Frontend changes stay confined to [`apps/vizu_dashboard/src/services/analyticsService.ts`](../../apps/vizu_dashboard/src/services/analyticsService.ts), [`apps/vizu_dashboard/src/hooks`](../../apps/vizu_dashboard/src/hooks), and the affected pages. Google Calendar uses the existing [`GoogleCalendarClient`](../../libs/vizu_google_suite_client/src/vizu_google_suite_client/calendar/client.py) exposed through a new Supabase Edge Function.

**Estimated Complexity:** Medium

**Key Dependencies (existing):**

- `analytics_v2` schema (`v_resumo_dashboard`, `v_series_temporal`, `v_distribuicao_regional`, `v_ultimos_pedidos`, `fato_transacoes.status`, `dim_datas`)
- `public` tables: `standalone_agent_sessions`, `connector_sync_history`, `client_data_sources`, `rfq_requests`, `uploaded_files_metadata`
- `public.get_my_client_id()` (RLS resolver, already used by every analytics view)
- [`libs/vizu_google_suite_client`](../../libs/vizu_google_suite_client) → `GoogleCalendarClient.list_events`
- [`libs/vizu_supabase_client`](../../libs/vizu_supabase_client) for the Edge Function
- React Query + `useHomeMetrics` hook pattern

---

## Architecture Overview

### Data flow

```
┌────────────────────────────────────────────────────────────────────────┐
│ Browser (vizu_dashboard, React + React Query)                          │
│  HomePage / PedidosPage / DomainExpansionModal                         │
│        │                                                                │
│  hooks: useHomeMetrics, useRecentActivity, usePendencias,              │
│         useAgentRunsToday, useAgenda, useNps                           │
│        │                                                                │
│        ▼  supabase-js (PostgREST + .rpc + edge.invoke)                  │
└────────────────────────────────────────────────────────────────────────┘
       │                              │
       │ schema('analytics_v2')       │ schema('public')          │ functions.invoke
       ▼                              ▼                            ▼
┌──────────────────────┐  ┌──────────────────────────────┐  ┌───────────────────────┐
│ analytics_v2 RPCs    │  │ public RPCs                  │  │ Edge Function          │
│ (SECURITY INVOKER)   │  │ (SECURITY INVOKER)           │  │ google-calendar-events │
│                      │  │                              │  │ (Deno + service token) │
│ get_order_indicators │  │ get_recent_activity          │  └───────────────────────┘
│ get_order_status_…   │  │ get_pendencias               │            │
│ get_pedidos_overview │  │ get_agent_runs_today         │            │ uses
│ _scorecards          │  │ get_nps_score                │            ▼
└──────────────────────┘  └──────────────────────────────┘  ┌───────────────────────┐
       │                              │                     │ libs/vizu_google_     │
       ▼                              ▼                     │ suite_client (Python  │
┌──────────────────────┐  ┌──────────────────────────────┐  │ wrapper, called from  │
│ fato_transacoes,     │  │ standalone_agent_sessions,   │  │ a tiny FastAPI shim   │
│ dim_datas, dim_*     │  │ connector_sync_history,      │  │ OR re-implemented in  │
│ + MVs                │  │ rfq_requests,                │  │ Deno using stored     │
│                      │  │ client_data_sources,         │  │ refresh_token from    │
│                      │  │ public.nps_responses (NEW),  │  │ vault)                │
│                      │  │ public.calendar_settings(NEW)│  └───────────────────────┘
└──────────────────────┘  └──────────────────────────────┘
```

### Component interaction

- **Service layer:** All new fetches live in `apps/vizu_dashboard/src/services/analyticsService.ts` (extending the same module — do **not** create a parallel service file). Pattern: typed response interface → `supabase.schema('…').rpc(…)` or `supabase.functions.invoke(…)` → `throwIfError` → mapped DTO.
- **Hook layer:** Mirror `useHomeMetrics` (React Query, 5-min `staleTime`, `{ data, loading, error, refetch }`).
- **RLS:** All RPCs are `SECURITY INVOKER` and filter by `public.get_my_client_id()` exactly like the existing `analytics_v2` RPCs (`get_client_top_products`, etc.).
- **Edge Function:** Single new function `google-calendar-events` reads OAuth refresh token from the vault (already seeded by `scripts/seed_google_oauth_vault.py`) and calls Google Calendar API directly (Deno fetch, no Python).

### Reusable assets created

| Type            | Name                                                                                                                              | Where                                       | Why reusable                                                                 |
| --------------- | --------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- | ---------------------------------------------------------------------------- |
| `[NEW RPC]`     | `analytics_v2.get_order_indicators(p_period text)`                                                                                | new migration                               | Backs PedidosPage scorecards + can be reused by future order-focused widgets |
| `[NEW RPC]`     | `analytics_v2.get_order_status_breakdown(p_period text)`                                                                          | new migration                               | First real read of `fato_transacoes.status`; future status widgets reuse     |
| `[NEW RPC]`     | `analytics_v2.get_pedidos_overview_scorecards()`                                                                                  | new migration                               | Computes qtd média / recorrência / recência once; usable in any pedidos card |
| `[NEW RPC]`     | `public.get_recent_activity(p_limit int)`                                                                                         | new migration                               | Cross-table activity feed; reusable by any "what just happened?" widget      |
| `[NEW RPC]`     | `public.get_pendencias()`                                                                                                         | new migration                               | Cross-table action items; reusable by future inbox/notifications             |
| `[NEW RPC]`     | `public.get_agent_runs_today()`                                                                                                   | new migration                               | Single source for all "agent activity today" widgets                         |
| `[NEW TABLE]`   | `public.nps_responses` + `public.get_nps_score(p_window_days int)` RPC                                                            | new migration                               | First-class NPS storage, can later feed survey product                       |
| `[NEW TABLE]`   | `public.calendar_settings` (per-client calendar id + sync prefs)                                                                  | new migration                               | Reusable for any calendar feature                                            |
| `[NEW EDGE FN]` | `google-calendar-events`                                                                                                          | `supabase/functions/google-calendar-events` | Reusable for Pedidos page deadlines, RFQ scheduling, etc.                    |
| `[NEW HOOKS]`   | `useRecentActivity`, `usePendencias`, `useAgentRunsToday`, `useAgenda`, `useNps` | `apps/vizu_dashboard/src/hooks/`            | Mirror `useHomeMetrics` shape; consumed by Home + future pages               |

---

## Phase 1: Foundation — Schema & RPCs (analytics + activity)

**Objective:** Land all SQL artefacts (RPCs, NPS table, calendar table) so the frontend can be wired without backend blockers.
**Success Criteria:**

- All new RPCs callable via `psql` and return correctly-shaped rows for a seeded test client.
- `supabase db advisors` clean (no new RLS / search_path warnings).
- Existing `analytics_v2` RPC tests still green.

### Tasks

1. **Analyze existing RPC pattern**
   - Read: [`supabase/migrations/20260422200100_analytics_v2_cleanup_phase_b_slim_fato.sql`](../../supabase/migrations/20260422200100_analytics_v2_cleanup_phase_b_slim_fato.sql) lines 130–200 (`get_client_top_products`, etc.) — copy exact preamble (`LANGUAGE sql STABLE SECURITY INVOKER SET search_path = analytics_v2, public`) and grant pattern.
   - Confirm the slim `fato_transacoes` columns: `client_id, tipo_id, data_competencia_id, cliente_id, fornecedor_id, produto_id, documento, quantidade, valor_unitario, valor, status` (see [`20260422200300_analytics_v2_cleanup_phase_d_etl_rewrite.sql`](../../supabase/migrations/20260422200300_analytics_v2_cleanup_phase_d_etl_rewrite.sql#L231)).

2. **Create migration: `analytics_v2_pedidos_rpcs`**
   - File via: `supabase migration new analytics_v2_pedidos_rpcs`
   - Add three functions, all `SECURITY INVOKER`, `SET search_path = analytics_v2, public`, scoped by `client_id = public.get_my_client_id()`:
     - `analytics_v2.get_order_indicators(p_period text DEFAULT 'month')` returning `(total bigint, revenue numeric, avg_order_value numeric, growth_rate numeric, period text)`. Period → `dd.data >= now() - interval` mapping (`week=7d`, `month=30d`, `quarter=90d`, `year=365d`). Growth = current vs previous equal-length window.
     - `analytics_v2.get_order_status_breakdown(p_period text DEFAULT 'month')` returning `(status text, count bigint)`. Source: `fato_transacoes.status`, GROUP BY `status`.
     - `analytics_v2.get_pedidos_overview_scorecards()` returning a single row `(qtd_media_produtos_por_pedido numeric, taxa_recorrencia_clientes_perc numeric, recencia_media_entre_pedidos_dias numeric)`. CTE-based: orders-per-customer for recurrence, median day-diff between consecutive orders for recência (use `lag()`).
   - `GRANT EXECUTE ... TO authenticated;` for each.

3. **Create migration: `public_dashboard_activity_rpcs`**
   - File via: `supabase migration new public_dashboard_activity_rpcs`
   - `public.get_recent_activity(p_limit int DEFAULT 10)` returning `(kind text, title text, subtitle text, occurred_at timestamptz, severity text)`.
     - UNION ALL across:
       - `connector_sync_history` (`status='completed' OR 'error'`, last 7 days) → kind `'ingestion'`.
       - `standalone_agent_sessions` (last 7 days) → kind `'agent_session'`.
       - `rfq_requests` (last 7 days) → kind `'rfq'`.
       - `uploaded_files_metadata` (last 7 days) → kind `'upload'`.
     - Filter every branch by `client_id = public.get_my_client_id()`.
     - ORDER BY `occurred_at DESC LIMIT p_limit`.
   - `public.get_pendencias()` returning `(kind text, title text, severity text, occurred_at timestamptz, target_route text)`.
     - UNION ALL: `rfq_requests WHERE status='pending'`, `connector_sync_history WHERE status='error'`, `client_data_sources WHERE sync_status='pending' OR 'error'`.
   - `public.get_agent_runs_today()` returning `(total bigint, by_agent jsonb)`.
     - Source: `standalone_agent_sessions WHERE created_at >= date_trunc('day', now() AT TIME ZONE 'America/Sao_Paulo')`.
     - `by_agent` aggregates count per `agent_type` (or whichever column denotes agent identity — confirm in [`20260311_create_standalone_agent_sessions.sql`](../../supabase/migrations/20260311_create_standalone_agent_sessions.sql)).
     - Future-proof note: token-cost rollup intentionally deferred (no DB persistence today; `TokenBudget` is in-memory).
   - `GRANT EXECUTE ... TO authenticated;` for each.

4. **Create migration: `public_nps_responses`**
   - File via: `supabase migration new public_nps_responses`
   - Table:
     ```
     public.nps_responses (
       id uuid pk default gen_random_uuid(),
       client_id text not null references cliente_vizu(...),
       respondent_user_id uuid null references auth.users(id),
       score smallint not null check (score between 0 and 10),
       comment text null,
       source text null,                 -- 'in_app' | 'email' | …
       created_at timestamptz not null default now()
     )
     ```
   - `ALTER TABLE … ENABLE ROW LEVEL SECURITY;`
   - Policies (mirror existing `client_id`-scoped tables): SELECT/INSERT for `authenticated` where `client_id = public.get_my_client_id()`.
   - `public.get_nps_score(p_window_days int DEFAULT 90)` returning `(score numeric, total_responses int, promoters int, passives int, detractors int)`.
     - Standard NPS formula: `(promoters% - detractors%)` rounded.

5. **Create migration: `public_calendar_settings`**
   - File via: `supabase migration new public_calendar_settings`
   - Table:
     ```
     public.calendar_settings (
       client_id text pk references cliente_vizu(...),
       google_calendar_id text not null default 'primary',
       enabled boolean not null default true,
       updated_at timestamptz not null default now()
     )
     ```
   - RLS enabled; policies scoped to `public.get_my_client_id()`.
   - **No data fetch RPC here** — the calendar pull happens in the Edge Function (Phase 3) which reads this table.

6. **Run advisors + smoke test**
   - `supabase db advisors` (CLI ≥ 2.81.3) or MCP `get_advisors`.
   - Manual smoke (psql / Supabase SQL editor):
     - `SET request.jwt.claim.sub = '…test user…'` → call each new RPC, assert non-error result.
     - Confirm RLS isolation by switching JWT and ensuring different `client_id` returns different data.

---

## Phase 2: Service & Hook Layer (extend `analyticsService.ts`)

**Objective:** Surface every new RPC through the canonical service module + dedicated React Query hook.
**Dependencies:** Phase 1 migrations applied to dev DB.
**Success Criteria:**

- `pnpm --filter vizu_dashboard typecheck` passes.
- Manual smoke in dashboard dev mode: each new hook returns non-empty data for the seeded client.

### Tasks

1. **Extend [`analyticsService.ts`](../../apps/vizu_dashboard/src/services/analyticsService.ts) with typed wrappers**
   - Mirror the existing wrapper pattern (interface → `supabase.schema(...).rpc(...)` → `throwIfError` → mapped object).
   - Add (signatures only):
     ```ts
     getOrderIndicators(period: PeriodType): Promise<OrderMetricsResponse>      // REWRITE existing stub
     getOrderStatusBreakdown(period: PeriodType): Promise<{status:string;count:number}[]>
     getPedidosOverviewScorecards(): Promise<{qtdMediaProdutos:number; taxaRecorrencia:number; recenciaMediaDias:number}>
     getRecentActivity(limit?: number): Promise<RecentActivityItem[]>
     getPendencias(): Promise<PendenciaItem[]>
     getAgentRunsToday(): Promise<{total:number; byAgent:Record<string,number>}>
     getNpsScore(windowDays?: number): Promise<NpsScoreResponse>
     getAgendaEvents(rangeDays?: number): Promise<AgendaEvent[]>   // calls Edge Function
     ```
   - **Rewrite** existing `getOrderIndicators` body to call the new RPC instead of reading `v_resumo_dashboard`. Keep the same response shape (`OrderMetricsResponse`) so `PedidosPage` stays compatible — only `by_status` becomes real.
   - **Update** `getPedidosOverview` to merge in real scorecards from `getPedidosOverviewScorecards()` (replaces the three hardcoded zeros at [`analyticsService.ts:406`](../../apps/vizu_dashboard/src/services/analyticsService.ts#L406)).

2. **Create hooks under [`apps/vizu_dashboard/src/hooks/`](../../apps/vizu_dashboard/src/hooks/)**
   - One file per hook; copy [`useHomeMetrics.ts`](../../apps/vizu_dashboard/src/hooks/useHomeMetrics.ts) verbatim and swap `queryFn`/`queryKey`.
   - Files:
     - `useRecentActivity.ts`
     - `usePendencias.ts`
     - `useAgentRunsToday.ts`
     - `useAgenda.ts`
     - `useNps.ts`
   - All `staleTime: 5 * 60 * 1000` except `useAgentRunsToday` (1 min) and `useAgenda` (2 min).

3. **Type updates**
   - Add new exported interfaces: `RecentActivityItem`, `PendenciaItem`, `NpsScoreResponse`, `AgendaEvent`.

---

## Phase 3: Google Calendar Integration

**Objective:** Replace the 4 hardcoded Agenda items on HomePage with real events from the user's Google Calendar.
**Dependencies:** Phase 1 (`calendar_settings` table) + existing OAuth vault seed (`seed_google_oauth_vault.py`) + existing `connector_credentials` table holding the refresh token.
**Success Criteria:**

- Edge Function returns next 7 days of events for an authenticated dashboard user.
- HomePage Agenda card renders real events (or empty state if calendar disabled).
- Onboarding hook present so an unconnected user sees a "Connect Google Calendar" CTA instead of an error.

### Tasks

1. **Read existing OAuth pattern**
   - Read: [`scripts/seed_google_oauth_vault.py`](../../scripts/seed_google_oauth_vault.py) and `connector_credentials` schema to confirm where the Google `refresh_token` is stored per client.
   - Read: [`libs/vizu_google_suite_client/src/vizu_google_suite_client/calendar/client.py`](../../libs/vizu_google_suite_client/src/vizu_google_suite_client/calendar/client.py) for the request shape (`timeMin`, `timeMax`, `singleEvents`, `orderBy`).

2. **Create Edge Function `google-calendar-events`**
   - Path: `supabase/functions/google-calendar-events/index.ts`
   - `verify_jwt: true` (per [supabase skill](../../.github/skills/supabase/SKILL.md) defaults) — derive `client_id` from JWT exactly the way other client-scoped functions do (see existing functions under `supabase/functions/` for the auth helper pattern).
   - Flow:
     - Resolve `client_id` from JWT.
     - Read `calendar_settings` row → `google_calendar_id`. If `enabled=false`, return `{ events: [], disabled: true }`.
     - Read `connector_credentials` row for provider `google` and exchange `refresh_token` → access token via Google `oauth2/v4/token` (Deno `fetch`).
     - Call Google Calendar `events.list` with `timeMin=now`, `timeMax=now+7d`, `singleEvents=true`, `orderBy='startTime'`, `maxResults=20`.
     - Map each event → `AgendaEvent { id, title, starts_at, ends_at, location, hangout_link, type }`. `type` derived from `eventType` or simple keyword match (`call|reuniao|deadline`).
     - Return `{ events, fetched_at }`.
   - Error handling: Google 401 → mark `calendar_settings.enabled=false` and return `{ events: [], disabled: true, reason: 'reauth_required' }`. Surface a typed code, no stack traces.

3. **Wire `getAgendaEvents` in `analyticsService.ts`**
   - Use `supabase.functions.invoke('google-calendar-events', { body: { rangeDays } })`.
   - Map to `AgendaEvent[]`.

4. **Optional bootstrap migration**
   - Backfill `calendar_settings` rows for all existing `cliente_vizu` rows with `enabled=false` so the function gracefully no-ops until each client opts in (one-line `INSERT … ON CONFLICT DO NOTHING`).

---

## Phase 4: Frontend Wiring — HomePage

**Objective:** Replace every mocked block in [`HomePage.tsx`](../../apps/vizu_dashboard/src/pages/HomePage.tsx) with real data from Phase 2/3 hooks. Keep visual layout pixel-identical.
**Dependencies:** Phases 2 & 3 complete.
**Success Criteria:**

- No literal placeholder strings remain in `HomePage.tsx` (audited via grep).
- Loading + empty + error states render gracefully (no spinner overlay over individual cards — match existing per-section pattern).
- React Query devtools show all queries firing and resolving.

### Tasks

1. **Active Tasks card label fix** ([`HomePage.tsx:241`](../../apps/vizu_dashboard/src/pages/HomePage.tsx#L241))
   - Replace `"tasks in progress"` literal with `"pedidos no total"` (the value is `totalPedidos`, not tasks). Pure copy fix.

2. **AI Tasks Today tile** ([`HomePage.tsx:340`](../../apps/vizu_dashboard/src/pages/HomePage.tsx#L340))
   - Drop `Math.floor(totalPedidos * 0.12)`.
   - Use `useAgentRunsToday()`. Display `data.total`. Tooltip / popover (optional) lists `byAgent`.
   - Empty state: render `0` (do not hide the tile).

3. **Quick Insight tile** ([`HomePage.tsx:370`](../../apps/vizu_dashboard/src/pages/HomePage.tsx#L370))
   - Replace static text with derived insight string built client-side from existing `metricsData.scorecards`:
     - If `crescimento_receita > 0` → `"Receita cresceu {x}% vs. mês anterior."`
     - Else if `crescimento_clientes > 0` → cliente growth message.
     - Else fallback → `"Acompanhe os indicadores principais para identificar oportunidades."`
   - **No new RPC.** Pure derivation from existing `useHomeMetrics` data — keeps the tile honest.

4. **Quick Actions** ([`HomePage.tsx:393`](../../apps/vizu_dashboard/src/pages/HomePage.tsx#L393))
   - Wire `onClick`. Targets:
     - "Novo Pedido" → `/dashboard/pedidos` (open new-order modal once it exists; for now navigate).
     - "Enviar Relatório" → `/dashboard/admin/agent-builder/new`.
     - "Email Cliente" → `/dashboard/clientes`.
     - "Definir Meta" → `/dashboard/settings` (placeholder route — confirm with PM).
   - Use `useNavigate()` (same hook used in [`Header.tsx:29`](../../apps/vizu_dashboard/src/components/Header.tsx#L29)).

5. **Recent Activity** ([`HomePage.tsx:435`](../../apps/vizu_dashboard/src/pages/HomePage.tsx#L435))
   - Replace mock array with `useRecentActivity(4)`.
   - Render with same item layout; map `kind` → existing color palette (ingestion=`#3b82f6`, agent_session=`#10b981`, rfq=`#f97316`, upload=`#a855f7`).
   - Format `occurred_at` via `formatDistanceToNow` (date-fns is already a transitive dep — confirm in `package.json`; if not, use simple `Intl.RelativeTimeFormat`).

6. **Agenda card** ([`HomePage.tsx:515`](../../apps/vizu_dashboard/src/pages/HomePage.tsx#L515))
   - Replace mock array with `useAgenda(7)`.
   - When response is `{ disabled: true }`, render the empty state with a "Conectar Google Calendar" link (to `/dashboard/admin/connectors` or onboarding route — confirm in [`MenuDrawer.tsx`](../../apps/vizu_dashboard/src/components/MenuDrawer.tsx)).
   - Map `type` → icon (`call|deadline|meeting`). Show `starts_at` formatted as `HH:mm`.

7. **Pendências card** ([`HomePage.tsx:565`](../../apps/vizu_dashboard/src/pages/HomePage.tsx#L565))
   - Replace mock array with `usePendencias()`.
   - Click on item → `navigate(item.target_route)`.
   - Badge count bound to `data.length`.

8. **KPI rail — drop Conversão, keep NPS** ([`HomePage.tsx:488-490`](../../apps/vizu_dashboard/src/pages/HomePage.tsx#L488))
   - Remove the `Taxa de Conversão` literal entry.
   - Replace `NPS Score = '72'` with `useNps(90)` → `data.score` (formatted as integer). Label sub-text shows `n respostas`.
   - Keep `Ticket Médio` (already live).

---

## Phase 5: Frontend Wiring — PedidosPage

**Objective:** Make every card on [`PedidosPage.tsx`](../../apps/vizu_dashboard/src/pages/PedidosPage.tsx) period-aware and source-truthful.
**Dependencies:** Phases 1 & 2 complete.
**Success Criteria:**

- Period select changes the numbers visible in scorecards and chart.
- "Métricas" select toggles the chart series shown on "Métricas de Pedidos".
- Geo card shows real customer distribution (no SP-only marker).
- "Pedidos Pendentes" reflects actual pending status from `fato_transacoes.status`.

### Tasks

1. **Period select → real period filter**
   - Confirmed refetch fires via `useEffect([selectedPeriod])`. [ARCHIVED - hooks removed Apr 2026]

2. **"Métricas" select → real binding** ([`PedidosPage.tsx:158`](../../apps/vizu_dashboard/src/pages/PedidosPage.tsx#L158))
   - Add `selectedMetric` state (`'receita' | 'quantidade' | 'ticket_medio'`).
   - Bind `value` and `onChange`.
   - Pass to a new helper `getPedidosTimeSeries(period, metric)` (extend `analyticsService.ts`) that queries `v_series_temporal` filtered by `tipo_grafico='pedidos'` + `dimensao=metric`. Re-use existing query, just parametrise the `dimensao` filter.
   - Feed result into the "Métricas de Pedidos" `DashboardCard`'s `graphData`.

3. **Status header scorecards** ([`PedidosPage.tsx:147-156`](../../apps/vizu_dashboard/src/pages/PedidosPage.tsx#L147))
   - [ARCHIVED - hooks removed Apr 2026]

4. **Geo card → useGeoClusters** ([`PedidosPage.tsx:296`](../../apps/vizu_dashboard/src/pages/PedidosPage.tsx#L296))
   - Replace static SP marker with the `useGeoClusters('state')` hook (already used by `GenericOverviewPage`).
   - Render s** ([`PedidosPage.tsx:296`](../../apps/vizu_dashboard/src/pages/PedidosPage.tsx#L296))
   - [ARCHIVED - hook removed Apr 2026]
   - Pure delete — the `ListCard "Últimos Pedidos"` already covers it and links to `/dashboard/pedidos/lista`.
   - Confirm with PM before removal (record decision in PR description).

6. **Scorecards from real data**
   - Wire `overviewData.scorecard_qtd_media_produtos_por_pedido` etc. to the scorecard slots that currently render zeros (no UI yet — surface them as KPI items inside "Métricas de Pedidos" card via `kpiItems`).

7. **Pedido detail status fix** ([`analyticsService.ts:458`](../../apps/vizu_dashboard/src/services/analyticsService.ts#L458))
   - `getPedidoDetails` now reads `fato_transacoes.status` (column exists post-slim — see [phase D ETL](../../supabase/migrations/20260422200300_analytics_v2_cleanup_phase_d_etl_rewrite.sql#L242)). Return the most-common status across the order's rows (or first non-null) instead of literal `'completed'`.

---

## Phase 6: Testing & Validation

**Objective:** Catch regressions and confirm RLS isolation.
**Dependencies:** Phases 1–5 merged on a feature branch.
**Success Criteria:**

- Unit: every new mapper function in `analyticsService.ts` covered.
- Integration: every new RPC has at least one psql / Supabase test asserting RLS isolation across two clients.
- Manual: dashboard E2E checklist passes (see below).

### Tasks

1. **SQL RPC tests**
   - Pattern: mirror existing analytics RPC tests under `tests/` (run via `pytest` against a local Supabase). Use the seeded test client from [`scripts/seed_test_suppliers.py`](../../scripts/seed_test_suppliers.py).
   - Assertions per RPC: returns expected shape, RLS denies cross-client read, period filter changes result count.

2. **Frontend unit tests**
   - For each new hook: render with React Query test client + mocked `supabase` (existing harness in `apps/vizu_dashboard/src/__tests__` if present; otherwise add a minimal one).

3. **Manual smoke checklist** (record in PR)
   - HomePage: revenue, AI tasks count, recent activity (4 items), agenda (real events or empty CTA), pendências, NPS, ticket médio.
   - PedidosPage: change period → numbers update; change métrica → chart updates; map shows ≥ 2 clusters; status header non-zero on both completed and pending given seeded data.
   - DomainExpansionModal still works (no regression on shared `useHomeMetrics`).

4. **Update placeholder doc**
   - When all done, update [`docs/dashboard-placeholders.md`](../dashboard-placeholders.md) to remove resolved entries; only Section 4 (admin pages) and any deferred items remain.

---

## Technical Considerations

- **Database:** Five new migrations; no breaking schema change; no MV refresh required (RPCs read live `fato_transacoes`). New tables (`nps_responses`, `calendar_settings`) ship with RLS enabled and policies scoped to `public.get_my_client_id()`.
- **Breaking changes:** `getOrderIndicators` body is rewritten but its response interface is preserved → no consumer change needed beyond Pedidos page.
- **Performance:** All RPCs hit indexed columns (`fato_transacoes(client_id, data_competencia_id)`, `standalone_agent_sessions(client_id, created_at)`). Activity feed UNION limited to 7 days. NPS RPC O(rows in window).
- **Security:** Every RPC `SECURITY INVOKER` + `SET search_path` (per [supabase skill](../../.github/skills/supabase/SKILL.md) checklist). Edge Function uses `verify_jwt=true` and reads OAuth secrets from vault, never returns them. New tables RLS-enabled; advisors must pass before merge.
- **Observability:** Edge Function logs structured `{ client_id, calendar_id, status, latency_ms }` to `console.log` (picked up by `mcp_supabase_get_logs(service='edge-function')`).

---

## Library / Schema Reuse Decisions

- **Do not** create a parallel "dashboardService" file — every fetch belongs in [`analyticsService.ts`](../../apps/vizu_dashboard/src/services/analyticsService.ts) for consistency with how Pedidos/Clientes/Fornecedores pages already work.
- **Do not** add a Python service for Google Calendar — the existing `GoogleCalendarClient` is referenced for _request shape_; the actual call is reimplemented in Deno inside the Edge Function to avoid a new microservice. The Python client stays for backend agents that already use it.
- **Do not** persist token usage to the DB just to feed the AI Tasks tile. `standalone_agent_sessions` is the existing source of truth; if richer cost tracking is needed later, that is its own epic.

---

## GitHub Issues to Create (after approval)

1. **EPIC** — `[EPIC] Dashboard mocks → live data (Apr 2026)` — labels `epic`, `tracking`; project **Releases de produto**; description links to this plan and lists each phase issue.
2. `[Dashboard] Phase 1: SQL RPCs + NPS/Calendar tables` — labels `planning`, `phase-1`, `database`.
3. `[Dashboard] Phase 2: Service & Hook layer` — labels `planning`, `phase-2`, `frontend`; depends on #Phase1.
4. `[Dashboard] Phase 3: Google Calendar Edge Function` — labels `planning`, `phase-3`, `edge-function`; depends on #Phase1.
5. `[Dashboard] Phase 4: HomePage wiring` — labels `planning`, `phase-4`, `frontend`; depends on #Phase2 + #Phase3.
6. `[Dashboard] Phase 5: PedidosPage wiring` — labels `planning`, `phase-5`, `frontend`; depends on #Phase2.
7. `[Dashboard] Phase 6: Testing + placeholders.md cleanup` — labels `planning`, `phase-6`, `testing`; depends on #Phase4 + #Phase5.
