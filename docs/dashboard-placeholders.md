# Dashboard — Placeholder / Mocked Elements

> **[HISTORICAL]** Replaced by Blu MVP Phase 1 (K1.1 ✅ — Apr 2026). All
> dashboard placeholders are now wired to live RPCs in `analytics_v2`. See
> [`docs/internal/kpi-catalog.md`](./internal/kpi-catalog.md) for the canonical
> KPI definitions and [`dashboard-live-metrics.md`](./dashboard-live-metrics.md)
> for the RPC mapping. The original mock-removal plan is archived at
> [`plans/archive/2026-04-23-dashboard-mocks-removal.md`](./plans/archive/2026-04-23-dashboard-mocks-removal.md).
>
> This document is preserved for traceability only — do not extend.

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

---

## 6. Phase 1 — Per-dimension KPI RPCs (Apr 2026, K1.1–K1.5) — ✅ SHIPPED

The Blu MVP roadmap Phase 1 wired five per-dimension indicator RPCs (Finance / Commercial / Inventory / Supply / Marketing) and the dashboard primitives that consume them. No placeholder values remain at the indicator layer — every KPI surfaced by `useDimensionKpis` is computed from `analytics_v2` views over `fato_transacoes` and tenant tables, RLS-scoped.

| #   | Element                                                                   | Source of truth                                                                                                                                         |
| --- | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 6.1 | Finance KPIs (receita líquida, margem, ticket médio, YoY)                 | `analytics_v2.get_finance_indicators(p_period)` via [`useDimensionKpis('finance', period)`](../apps/vizu_dashboard/src/hooks/useDimensionKpis.ts)       |
| 6.2 | Commercial KPIs (pedidos, clientes únicos/novos, recência)                | `analytics_v2.get_commercial_indicators(p_period)` via [`useDimensionKpis('commercial', period)`](../apps/vizu_dashboard/src/hooks/useDimensionKpis.ts) |
| 6.3 | Inventory KPIs (SKUs ativos, giro, cobertura top-20)                      | `analytics_v2.get_inventory_indicators(p_period)` via [`useDimensionKpis('inventory', period)`](../apps/vizu_dashboard/src/hooks/useDimensionKpis.ts)   |
| 6.4 | Supply KPIs (RFQs, taxa resposta, POs, concentração)                      | `analytics_v2.get_supply_indicators(p_period)` via [`useDimensionKpis('supply', period)`](../apps/vizu_dashboard/src/hooks/useDimensionKpis.ts)         |
| 6.5 | Marketing KPIs (PRO flag — novos clientes, conversão, CAC)                | `analytics_v2.get_marketing_indicators(p_period)` via [`useDimensionKpis('marketing', period)`](../apps/vizu_dashboard/src/hooks/useDimensionKpis.ts)   |
| 6.6 | Standardized period selector (`7d \| 30d \| 90d \| mtd \| ytd \| custom`) | [`PeriodSelector`](../apps/vizu_dashboard/src/components/PeriodSelector.tsx) — single component reused across pages                                     |
| 6.7 | Empty / degraded states ("Conexão indisponível", retry CTA)               | [`EmptyStateCard`](../apps/vizu_dashboard/src/components/EmptyStateCard.tsx) — variants: `empty \| disconnected \| error`                               |
| 6.8 | "Última atualização: há X h" warning pill (MV staleness >25 h)            | [`StaleDataPill`](../apps/vizu_dashboard/src/components/StaleDataPill.tsx)                                                                              |

> **Note:** Marketing KPIs return zeroed structure for clients not on the PRO plan (feature-flag enforced server-side); the UI should hide or gate the card accordingly.
