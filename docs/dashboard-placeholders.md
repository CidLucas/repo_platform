# Dashboard — Placeholder / Mocked Elements

> **Status (Apr 2026):** Phases 1–6 of [`plans/2026-04-23-dashboard-mocks-removal.md`](./plans/2026-04-23-dashboard-mocks-removal.md) shipped. Sections 1 and 2 below are now **all wired to Supabase** (RPCs in `analytics_v2` / `public` + the `google-calendar-events` Edge Function). They are kept here as a historical reference; only Sections 3–4 still describe live placeholders.

This document originally listed every user-facing dashboard element that showed hard-coded / mocked content. The counterpart document with queries for live metrics is [`dashboard-live-metrics.md`](./dashboard-live-metrics.md).

All paths are relative to [`apps/vizu_dashboard/src`](../apps/vizu_dashboard/src).

---

## 1. Home — `/dashboard` ([`HomePage.tsx`](../apps/vizu_dashboard/src/pages/HomePage.tsx)) — ✅ RESOLVED (Phase 4)

| #   | Element                    | Status                                                                                                                                          | Source of truth                                                                                                                                         |
| --- | -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1.1 | "Active Tasks" label       | ✅ relabelled to "pedidos no total"                                                                                                             | `useHomeMetrics`                                                                                                                                        |
| 1.2 | "AI Tasks Today" tile      | ✅ live                                                                                                                                         | `public.get_agent_runs_today()` via [`useAgentRunsToday`](../apps/vizu_dashboard/src/hooks/useAgentRunsToday.ts)                                        |
| 1.3 | "Quick Insight" tile       | ✅ derived client-side from `useHomeMetrics` scorecards (no static string)                                                                      | `analyticsService.getDashboardOverview`                                                                                                                 |
| 1.4 | "Quick Actions"            | ✅ each tile wired to `useNavigate`                                                                                                             | n/a                                                                                                                                                     |
| 1.5 | "Recent Activity"          | ✅ live                                                                                                                                         | `public.get_recent_activity(limit)` via [`useRecentActivity`](../apps/vizu_dashboard/src/hooks/useRecentActivity.ts)                                    |
| 1.6 | "Agenda"                   | ✅ live (Google Calendar)                                                                                                                       | Edge Function [`google-calendar-events`](../supabase/functions/google-calendar-events) via [`useAgenda`](../apps/vizu_dashboard/src/hooks/useAgenda.ts) |
| 1.7 | "Pendências"               | ✅ live                                                                                                                                         | `public.get_pendencias()` via [`usePendencias`](../apps/vizu_dashboard/src/hooks/usePendencias.ts)                                                      |
| 1.8 | KPI rail — Conversão / NPS | ✅ "Taxa de Conversão" tile **removed**; NPS sourced from `public.get_nps_score(90)` via [`useNps`](../apps/vizu_dashboard/src/hooks/useNps.ts) | `nps_responses` table                                                                                                                                   |

---

## 2. Pedidos — `/dashboard/pedidos` ([`PedidosPage.tsx`](../apps/vizu_dashboard/src/pages/PedidosPage.tsx)) — ✅ RESOLVED (Phase 5)

| #   | Element                                                | Status                                                                                                                              | Source of truth                                                                               |
| --- | ------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| 2.1 | "Métricas" select                                      | ✅ controlled (`selectedMetric`) and feeds the chart                                                                                | `analyticsService.getPedidosTimeSeries(period, metric)` over `analytics_v2.v_series_temporal` |
| 2.2 | Period select                                          | ✅ now drives `getOrderIndicators(period)`, `getOrderStatusBreakdown(period)`, `getPedidosTimeSeries(period, metric)`               | `analytics_v2.get_order_indicators`                                                           |
| 2.3 | "Histórico de Pedidos" small card                      | ✅ removed (covered by Últimos Pedidos list)                                                                                        | n/a                                                                                           |
| 2.4 | "Distribuição Geográfica" map                          | ✅ uses `useGeoClusters('state')` + shared [`mapGeoClustersToMapData`](../apps/vizu_dashboard/src/utils/mapGeoClustersToMapData.ts) | analytics geo clusters RPC                                                                    |
| 2.5 | "Pedidos Concluídos" / "Pendentes"                     | ✅ real status breakdown via `summarizeOrderStatusBreakdown`                                                                        | `analytics_v2.get_order_status_breakdown(period)` reading `fato_transacoes.status`            |
| 2.6 | Overview scorecards (qtd média, recorrência, recência) | ✅ surfaced as `kpiItems` in the Métricas card                                                                                      | `analytics_v2.get_pedidos_overview_scorecards()`                                              |
| 2.7 | Pedido detail modal `status_pedido`                    | ✅ computed as most-common non-null status across the order's rows                                                                  | `fato_transacoes.status`                                                                      |

### Deviations from plan (recorded in PR)

- Time-series period filter is implemented client-side (slice trailing N months from monthly `v_series_temporal`); `week=1` collapses to last month.
- Scorecards surface as `kpiItems` inside the existing Métricas card (no new visual slots), per the plan's "no new UI" guidance.

---

## 3. Overview pages (Clientes / Fornecedores / Produtos)

Rendered by [`GenericOverviewPage.tsx`](../apps/vizu_dashboard/src/pages/GenericOverviewPage.tsx). All cards are driven by live data (see live-metrics doc §3). The only non-live touches:

### 3.1 Geo map center fallback

- When `useGeoClusters` returns no center, the map defaults to `center: [-14.235, -51.9253]` (geographic centre of Brazil) with `zoom: 4.5` (now centralised in [`mapGeoClustersToMapData`](../apps/vizu_dashboard/src/utils/mapGeoClustersToMapData.ts)). Acceptable fallback but worth noting.

### 3.2 `STATE_COORDINATES` lookup

- Map cluster coordinates are plotted using a **static** Brazilian state-capital coordinate table in [`analyticsService.ts`](../apps/vizu_dashboard/src/services/analyticsService.ts). Counts are live; coordinates are constants.

---

## 4. Pages outside the live-analytics scope

The admin/super-admin sections (`/dashboard/admin/**`, `/dashboard/super-admin/**`), Settings, Chat, Knowledge Base, Agent Builder, Onboarding and Connectors pages operate over their own tables (`client_data_sources`, `connector_credentials`, `agent_builder_configs`, `knowledge_base_*`, etc.) and do not present analytics metrics. They are out of scope for this document but are fully data-driven from Supabase.

---

## 5. Remaining follow-ups

1. **Geo coordinates** (§3.2) — replace the static `STATE_COORDINATES` lookup with a `dim_localidade` lookup or PostGIS centroid so cluster pins reflect real city centroids, not state capitals.
2. **NPS ingestion** — `public.nps_responses` is queryable but no in-product survey writes to it yet. Wire a survey component or an external source (e.g. Typeform webhook → Edge Function).
3. **Calendar onboarding** — surface the "Conectar Google Calendar" CTA from the Agenda card to the Connectors page so users can flip `calendar_settings.enabled` without a developer.

# Dashboard — Placeholder / Mocked Elements

This document lists **every user-facing dashboard element that still shows hard-coded, mocked, or constant content** (i.e. is _not_ connected to the database). The counterpart document with queries for live metrics is [`dashboard-live-metrics.md`](./dashboard-live-metrics.md).

All paths are relative to [`apps/vizu_dashboard/src`](../apps/vizu_dashboard/src).

---

## 1. Home — `/dashboard` ([`HomePage.tsx`](../apps/vizu_dashboard/src/pages/HomePage.tsx))

### 1.1 "Active Tasks" card

- Big number: **live** (uses `totalPedidos` from `v_resumo_dashboard`).
- Label: hard-coded string **"tasks in progress"** ([HomePage.tsx:241](../apps/vizu_dashboard/src/pages/HomePage.tsx#L241)) — misleading, because the card shows orders, not tasks.

### 1.2 "AI Tasks Today" tile

- Value = `Math.floor(totalPedidos * 0.12)` ([HomePage.tsx:340](../apps/vizu_dashboard/src/pages/HomePage.tsx#L340)). Arbitrary 12 % of orders, no real AI-task counter.

### 1.3 "Quick Insight" tile

- Entire text is a static string ([HomePage.tsx:370](../apps/vizu_dashboard/src/pages/HomePage.tsx#L370)).

### 1.4 "Quick Actions" card

- 4-tile grid of hard-coded actions, none of the tiles have `onClick` wiring ([HomePage.tsx:393](../apps/vizu_dashboard/src/pages/HomePage.tsx#L393)).

### 1.5 "Recent Activity" card

- 4 hard-coded activity lines ([HomePage.tsx:435](../apps/vizu_dashboard/src/pages/HomePage.tsx#L435)). No feed source.

### 1.6 "Agenda" card

- 4 hard-coded calendar events ([HomePage.tsx:515](../apps/vizu_dashboard/src/pages/HomePage.tsx#L515)). No calendar integration.

### 1.7 "Pendências" card

- 3 hard-coded pending items ([HomePage.tsx:565](../apps/vizu_dashboard/src/pages/HomePage.tsx#L565)).

### 1.8 KPI rail — Taxa de Conversão & NPS Score

- `Taxa de Conversão = '3.2%'` ([HomePage.tsx:488](../apps/vizu_dashboard/src/pages/HomePage.tsx#L488)) — literal string.
- `NPS Score = '72'` ([HomePage.tsx:490](../apps/vizu_dashboard/src/pages/HomePage.tsx#L490)) — literal string.

---

## 2. Pedidos — `/dashboard/pedidos` ([`PedidosPage.tsx`](../apps/vizu_dashboard/src/pages/PedidosPage.tsx))

### 2.1 Select "Métricas"

- Has `placeholder="Métricas"` and options Receita / Quantidade / Ticket Médio, but **no `value` / `onChange` binding** ([PedidosPage.tsx:158](../apps/vizu_dashboard/src/pages/PedidosPage.tsx#L158)). Selecting an option has no effect.

### 2.2 Period Select (Semana / Mês / Trimestre / Ano)

- Binding exists and triggers a refetch, but [`getOrderIndicators()`](../apps/vizu_dashboard/src/services/analyticsService.ts#L973) **ignores the `period` argument** — it always returns totals from `v_resumo_dashboard`. The UI updates "timestamp" but the underlying numbers don't change.

### 2.3 Card "Histórico de Pedidos"

- Only renders a static sentence ("Histórico completo de todos os pedidos.") — no `graphData`, no data fetch ([PedidosPage.tsx:282](../apps/vizu_dashboard/src/pages/PedidosPage.tsx#L282)).

### 2.4 Card "Distribuição Geográfica"

- Map uses a **hard-coded São Paulo marker**: `center: [-23.55052, -46.633308]` + a single marker popup "São Paulo" ([PedidosPage.tsx:296](../apps/vizu_dashboard/src/pages/PedidosPage.tsx#L296)). Not a query — unlike the geo map on the Clientes/Fornecedores/Produtos pages which uses `useGeoClusters`.

### 2.5 "Pedidos Concluídos" / "Pedidos Pendentes" header scorecards

- `by_status` in the response is populated only as `{ completed: total_pedidos }` ([analyticsService.ts:988](../apps/vizu_dashboard/src/services/analyticsService.ts#L988)). There is no real status breakdown — the "Concluídos" card shows every order and "Pendentes" always shows `0`.

### 2.6 `getPedidosOverview` zero-scorecards

The following fields in the `PedidosOverviewResponse` are currently hard-zero ([analyticsService.ts:406](../apps/vizu_dashboard/src/services/analyticsService.ts#L406)):

- `scorecard_qtd_media_produtos_por_pedido`
- `scorecard_taxa_recorrencia_clientes_perc`
- `scorecard_recencia_media_entre_pedidos_dias`

They are not currently read by any rendered card, but they exist in the response shape and should either be computed or removed.

### 2.7 Pedido Details Modal — status

- `status_pedido` is always set to the literal `'completed'` ([analyticsService.ts:458](../apps/vizu_dashboard/src/services/analyticsService.ts#L458)) because `fato_transacoes` no longer carries a per-transaction status column after the slim-down.

---

## 3. Overview pages (Clientes / Fornecedores / Produtos)

Rendered by [`GenericOverviewPage.tsx`](../apps/vizu_dashboard/src/pages/GenericOverviewPage.tsx). All cards are driven by live data (see live-metrics doc §3). The only non-live touches:

### 3.1 Geo map center fallback

- When `useGeoClusters` returns no center, the map defaults to `center: [-14.235, -51.9253]` (geographic centre of Brazil) with `zoom: 4.5` ([GenericOverviewPage.tsx:137](../apps/vizu_dashboard/src/pages/GenericOverviewPage.tsx#L137)). Acceptable fallback but worth noting.

### 3.2 `STATE_COORDINATES` lookup

- Map cluster coordinates are plotted using a **static** Brazilian state-capital coordinate table in [`analyticsService.ts`](../apps/vizu_dashboard/src/services/analyticsService.ts#L1014). Counts are live; coordinates are constants.

---

## 4. Pages outside the live-analytics scope

The admin/super-admin sections (`/dashboard/admin/**`, `/dashboard/super-admin/**`), Settings, Chat, Knowledge Base, Agent Builder, Onboarding and Connectors pages operate over their own tables (`client_data_sources`, `connector_credentials`, `agent_builder_configs`, `knowledge_base_*`, etc.) and do not present analytics metrics. They are out of scope for this document but are fully data-driven from Supabase.

---

## 5. Suggested next steps

1. **Home page dressing** — Quick Actions, Recent Activity, Agenda, Pendências, Taxa de Conversão, NPS — design + wire real sources or hide behind a feature flag until data exists.
2. **Pedidos page** —
   - Drop or wire the "Métricas" select.
   - Pass `period` through to an aggregate that respects it (e.g. fetch `v_series_temporal` windowed by period).
   - Replace the hard-coded São Paulo marker with `useGeoClusters('city')`.
   - Replace the single-bucket `by_status` with a real breakdown once `fato_transacoes.status` is reintroduced or derived.
3. **AI Tasks Today** — either expose a real counter from the agent tables or remove the tile.
