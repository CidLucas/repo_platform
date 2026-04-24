# Phase 6 — Manual Smoke Checklist (Dashboard mocks → live data)

> Reference: [`2026-04-23-dashboard-mocks-removal.md`](./2026-04-23-dashboard-mocks-removal.md)
> Goal: validate Phases 1–5 in a running dev environment before merge.

Copy this checklist into the PR description and tick each box during QA.

---

## Pre-flight

- [ ] All Phase 1 migrations applied (`supabase migration list` shows the four `20260423120*` files).
- [ ] `pnpm --filter vizu_dashboard typecheck` clean (only the pre-existing `useGeoClusters.tsx` warning, unchanged from Phase 4).
- [ ] `npm test` inside `apps/vizu_dashboard` passes (vitest — Phase 6 unit tests).
- [ ] `pytest tests/test_dashboard_rpcs.py -m integration` passes against dev Supabase.
- [ ] `supabase db advisors` (or `mcp_supabase_get_advisors security`) shows **no new** warnings.

## HomePage (`/dashboard`)

- [ ] **Active Tasks** label reads "pedidos no total" (not "tasks in progress").
- [ ] **AI Tasks Today** tile shows a real integer from `get_agent_runs_today` (refreshes ≤ 1 min).
- [ ] **Quick Insight** tile renders one of the three derived strings (revenue↑/recurrence/fallback) — never the static placeholder.
- [ ] **Quick Actions** — clicking each tile navigates somewhere (no dead clicks).
- [ ] **Recent Activity** shows up to 4 rows from `get_recent_activity`. Mock strings ("3 minutes ago — Pedido criado por João Silva") are gone.
- [ ] **Agenda** shows real Google Calendar events when `calendar_settings.enabled = true`; otherwise a "Conectar Google Calendar" CTA is rendered (no items).
- [ ] **Pendências** shows real items from `get_pendencias`; clicking an item navigates to `target_route`.
- [ ] **NPS Score** is a real number from `get_nps_score(90)` with `n respostas` subtitle. The "Taxa de Conversão" KPI card is removed.
- [ ] **Ticket Médio** (already live) still renders.
- [ ] No literal placeholder strings remain — `grep -nE "tasks in progress|3 minutes ago|placeholder" apps/vizu_dashboard/src/pages/HomePage.tsx` returns nothing.

## PedidosPage (`/dashboard/pedidos`)

- [ ] **Period select** — switching `Semana → Mês → Trimestre → Ano` updates Total Vendido, Concluídos, Pendentes, growth %, and the chart.
- [ ] **Métricas select** is bound — switching `Receita → Quantidade → Ticket Médio` updates the chart's `graphData` and the `scorecardLabel` ("Total Vendido (Receita|Quantidade|Ticket Médio)").
- [ ] **Concluídos / Pendentes** scorecards are non-zero on both buckets given seeded data (sourced from `summarizeOrderStatusBreakdown`).
- [ ] **Distribuição Geográfica** map shows ≥ 2 clusters (real `useGeoClusters('state')` data) — not the single hard-coded SP marker.
- [ ] **Métricas de Pedidos** card lists the three real KPI items (qtd média / taxa recorrência / recência média) — no zero placeholders.
- [ ] **"Histórico de Pedidos"** small card is gone (covered by Últimos Pedidos list).
- [ ] **Pedido detail modal** — `status_pedido` reflects the real most-common `fato_transacoes.status` for the order, not the literal `'completed'`.

## DomainExpansionModal (regression)

- [ ] Opening the modal still works; `useHomeMetrics` data (revenue, tickets, etc.) is unchanged after the wiring.

## Edge Function — `google-calendar-events`

- [ ] `supabase functions invoke google-calendar-events --body '{"rangeDays":7}'` returns `{ events, fetched_at }` for an authenticated test user with `calendar_settings.enabled = true`.
- [ ] Returns `{ events: [], disabled: true, reason: 'reauth_required' }` when refresh token is invalid (no 5xx).
- [ ] `mcp_supabase_get_logs(service='edge-function')` shows structured logs `{ client_id, calendar_id, status, latency_ms }`.

## RLS isolation (defence-in-depth)

- [ ] Authenticate as `client_a` → call `get_recent_activity`/`get_pendencias`/`get_agent_runs_today`/`get_nps_score`/`get_order_*` — only `client_a` rows returned.
- [ ] Re-auth as `client_b` → numbers and feeds change. No row from `client_a` leaks.
- [ ] Anon JWT → all RPCs return zero/empty (no error) because `public.get_my_client_id()` resolves to NULL.

## Documentation

- [ ] [`docs/dashboard-placeholders.md`](../dashboard-placeholders.md) updated; resolved entries removed.
- [ ] PR description links this checklist and the original plan.

---

**QA sign-off:** _name / date_
