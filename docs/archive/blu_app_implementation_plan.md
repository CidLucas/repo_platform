# Blu App — Implementation Plan

> **Stack:** React 18 + TypeScript + Vite + Tailwind v3 + React Router v6 + @supabase/supabase-js + TanStack Query v5 + @radix-ui/react-dialog + Tiptap + Recharts
>
> Shares Supabase backend with `blu_dashboard`. Auth via existing `blu_auth` edge function.
> No Framer Motion — all animations are CSS-only to keep the bundle light.

---

## Prerequisites — Schema Migrations

All P0 and P1 migrations from [`blu_app_schema_gaps.md`](./blu_app_schema_gaps.md) **must be applied before Sprint 1 begins**. The frontend cannot be built without:

- `approval_requests` column additions (priority, agent_slug, title, insight_text, snooze_until, snooze_count, scheduled_for)
- `client_enabled_agents` column additions (current_status, last_activity_at, pending_count)
- `notifications` table
- `client_kpi_snapshot` table
- `suppliers` table
- `client_approval_stats` + `client_approval_rules` tables

P2 migrations (document versions, conversa agent context, etc.) must be applied before Sprint 5.

---

## Global Rules (enforced everywhere)

| Rule                             | Detail                                                                                                     |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| **Token names only**             | No inline hex in components. Use `bg-surface`, `text-gray-200`, `border-border`. Never `bg-[#111E33]`.     |
| **`dvh` not `vh`**               | All full-height layouts use `min-h-dvh` / `h-dvh`. Never `h-screen` or `100vh` — iOS Safari clips content. |
| **`touch-action: manipulation`** | Applied globally on `button, a, [role="button"]` in `globals.css` to eliminate 300ms tap delay.            |
| **Lucide icons only**            | No emojis as UI icons. No mixed icon sets.                                                                 |
| **`cursor-pointer`**             | All interactive elements: buttons, cards, clickable rows.                                                  |
| **Error boundaries**             | Every `RoomContainer` wraps content in `RoomErrorBoundary`. Crash in one room never takes down the shell.  |
| **Mobile-first Tailwind**        | Breakpoint order: `base → md → lg → xl`. Desktop enhancements are additive.                                |

---

## Phase 0 — Project Bootstrap

**Goal:** Runnable skeleton with design tokens, routing, and auth wired.

- [ ] `vite.config.ts` — configure aliases (`@/` → `src/`), env vars
- [ ] `tsconfig.json` — strict mode, path aliases
- [ ] `tailwind.config.js` — full token set from `blu_visual_ref.md` (colors, spacing, radius, shadows, font sizes, keyframes, animations)
- [ ] `src/styles/tokens.css` — CSS custom properties mirroring the Tailwind config (for components that need raw CSS variables)
- [ ] `src/styles/globals.css`:
  - Body defaults: `bg-base text-white font-sans text-body`
  - `touch-action: manipulation` on all interactive elements
  - `prefers-reduced-motion` reset (disables all animations/transitions to 0ms)
  - `overscroll-behavior: contain` on scroll containers (prevents pull-to-refresh hijack)
- [ ] `src/styles/animations.css` — all keyframes: `orb-pulse`, `orb-idle`, `orb-attention`, `fade-in`, `slide-up`, `expand`, `glow-pulse`, `scale-press`
- [ ] Supabase client in `src/api/client.ts` (singleton, env-based URL + anon key)
- [ ] TanStack Query `QueryClient` configured with sensible defaults:
  - `staleTime: 60_000` (1 min)
  - `gcTime: 300_000` (5 min)
  - `retry: 1`
  - Global error handler → `ErrorHuman` toast
- [ ] `AuthContext` + `useAuth` — reads Supabase session, resolves `client_id` from `clientes_blu` via `external_user_id`, redirects to login if unauthenticated
- [ ] React Router v6 routes (all behind `<RequireAuth>`):
  - `/` → `HomePage`
  - `/compras` → `ComprasRoom`
  - `/financeiro` → `FinanceiroRoom`
  - `/agenda` → `AgendaRoom`
  - `/documentos` → `DocumentosRoom`
  - `/estrategia` → `EstrategiaRoom`
  - `/clientes` → `ClientesRoom`
  - `/admin` → `AdminPage`

**Deliverable:** `npm run dev` shows the home route behind auth with design tokens loaded.

---

## Phase 1 — Primitive Components

**Goal:** Atomic design tokens expressed as typed, accessible React components.
All primitives live in `src/components/primitives/`.

| Component    | Variants / Key Rules                                                                                                                                                                                                                 |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `Button`     | `primary \| secondary \| ghost \| danger` × `sm/md/lg`. Loading state shows `Spinner` + disables. Scale-press animation (`scale-press` keyframe, 100ms). `cursor-pointer`. Visible focus ring (`focus-visible:ring-2 ring-blu-500`). |
| `IconButton` | Icon-only. `aria-label` required prop. Same hover/focus as Button. Min 44×44px touch target.                                                                                                                                         |
| `Badge`      | `status` (ok/urgent/attention/info) \| `count` (number). Semantic color tokens.                                                                                                                                                      |
| `Card`       | Base container (`bg-surface border border-border rounded-md shadow`). Hover lift variant (`hover:bg-elevated hover:shadow-md`). Active border variant (`border-blu glow-blu`).                                                       |
| `Input`      | All states: default/hover/focus/filled/error/disabled. Focus: `border-blu-500 shadow-glow-blu`. `inputmode` prop for numeric fields.                                                                                                 |
| `Select`     | Styled select. Same state machine as Input.                                                                                                                                                                                          |
| `Toggle`     | On/off switch. Animated thumb slide via CSS `transform` (200ms ease).                                                                                                                                                                |
| `TabGroup`   | Horizontal tabs. Active: `border-b-2 border-blu-500`. Accessible: `role="tablist"` + `aria-selected`.                                                                                                                                |
| `Avatar`     | User photo or initials fallback. `sm/md/lg` sizes.                                                                                                                                                                                   |
| `Divider`    | `1px solid var(--border)`. Horizontal and vertical variants.                                                                                                                                                                         |
| `Spinner`    | Rotating ring via CSS `@keyframes spin`. Respects `prefers-reduced-motion`.                                                                                                                                                          |

---

## Phase 2 — App Shell & Navigation

**Goal:** Persistent layout with agent nav, notification bell, responsive behavior — zero data dependencies.

### Components

**`AppShell`** — Root layout. `QueryClientProvider` + `AuthProvider` + `NotificationProvider` wrapping everything. No data fetching here.

- Mobile: `AgentNav` hidden by default, opens as slide-in overlay via CSS `transform: translateX`
- Desktop (`lg:`): persistent `AgentNav` sidebar (240px) + main content area

**`NavBar`** — Top bar, floating style: `fixed top-4 left-4 right-4 z-50`.

- Left: Blu logo + current room name (from route)
- Right: `GlobalSearch` + `NotificationBell` + `Avatar`
- Content below accounts for navbar height via `pt-20` on page containers

**`AgentNav`** — Left sidebar / hamburger content.

- Items: Home + 6 agent rooms + Atividade + Biblioteca + Admin
- Each: agent orb icon + label + `RedDot` badge with `pending_count`
- Active: `bg-elevated border-l-2 border-blu-500`
- Mobile: hamburger toggle → CSS `translate-x-0` / `-translate-x-full` transition (300ms ease)
- On mobile, `AgentStatusRow` at the bottom of Home is **hidden** (`hidden md:flex`) — the nav already covers this

**`AgentBadge`** — Orb SVG + agent name + status dot.

- Orb shape per agent identity (Hexagon/Circle/Triangle/Square/Diamond/Pentagon)
- Status drives CSS animation class: `animate-orb-idle` / `animate-orb-pulse` / `animate-orb-attention` / `opacity-30` (offline)

**`NotificationBell`** — Bell icon + `Badge` count.

- Unread count from `NotificationContext` (driven by Supabase Realtime, see Phase 4)
- Click → `NotificationDropdown` (absolutely positioned panel)
- Critical notifications: red dot with `animate-orb-attention`

**`NotificationDropdown`** — Grouped notification list.

- Groups by type; most recent first
- Each item links to the relevant room/approval via `react-router` navigate
- `read_at` marked on open via `UPDATE notifications SET read_at = now()`

**`RoomContainer`** — Wraps every agent room. Sets `max-w-7xl mx-auto` and `pt-20` (navbar offset). Contains `RoomErrorBoundary`.

**`RoomErrorBoundary`** — React Error Boundary. Renders `ErrorHuman` with retry on any uncaught room error.

**`BackToLobby`** — Persistent return button inside any agent room. Navigates to `/`.

---

## Phase 3 — Data Layer (TanStack Query + Supabase Realtime)

**Goal:** Centralized data fetching, caching, and live update infrastructure before any data-dependent screens are built.

### Query hooks (`src/hooks/`)

All hooks follow the pattern: `useQuery` / `useMutation` wrapping a Supabase call. Mutations call `queryClient.invalidateQueries` to keep UI consistent across the app after any write.

| Hook                  | Query Key                            | Source                                                                                                                                            |
| --------------------- | ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `usePendingApprovals` | `['approvals', 'pending', clientId]` | `approval_requests` WHERE `status='pending'` AND `snooze_until IS NULL OR snooze_until < now()` ORDER BY `priority='urgent' DESC, created_at ASC` |
| `useApprovalsByAgent` | `['approvals', agentSlug, clientId]` | Same table filtered by `agent_slug`                                                                                                               |
| `useApproveRequest`   | — (mutation)                         | UPDATE + INSERT `audit_log` + invalidate `['approvals']` + `['agents']`                                                                           |
| `useSnoozeRequest`    | — (mutation)                         | UPDATE `snooze_until` + invalidate `['approvals']`                                                                                                |
| `useInsights`         | `['insights', clientId]`             | `client_insights` WHERE `dismissed=false` ORDER BY `generated_at DESC`                                                                            |
| `useDismissInsight`   | — (mutation)                         | UPDATE `dismissed=true` + invalidate `['insights']`                                                                                               |
| `useAgents`           | `['agents', clientId]`               | `client_enabled_agents` JOIN `agent_catalog`                                                                                                      |
| `useKpiSnapshot`      | `['kpi', period, clientId]`          | `client_kpi_snapshot` WHERE `period=?`                                                                                                            |
| `useNotifications`    | `['notifications', clientId]`        | `notifications` WHERE `dismissed_at IS NULL` ORDER BY `created_at DESC` LIMIT 30                                                                  |
| `useApprovalStats`    | `['approval-stats', clientId]`       | `client_approval_stats`                                                                                                                           |

### Supabase Realtime Subscriptions (`src/hooks/useRealtime.ts`)

Mounted once in `AppShell` on auth. Uses `supabase.channel()`:

```
channel('app-realtime')
  .on('postgres_changes', { table: 'approval_requests', event: 'INSERT', filter: `client_id=eq.${clientId}` })
    → invalidate ['approvals', 'pending', clientId]
    → invalidate ['agents', clientId]  (pending_count changed)
  .on('postgres_changes', { table: 'approval_requests', event: 'UPDATE', filter: `client_id=eq.${clientId}` })
    → invalidate ['approvals', 'pending', clientId]
  .on('postgres_changes', { table: 'notifications', event: 'INSERT', filter: `client_id=eq.${clientId}` })
    → invalidate ['notifications', clientId]
    → show SuccessToast if urgency_level='critical'
  .on('postgres_changes', { table: 'client_enabled_agents', event: 'UPDATE', filter: `client_id=eq.${clientId}` })
    → invalidate ['agents', clientId]
  .subscribe()
```

This means: when an agent creates a new approval, the Home page red dots and `DecidirAgora` list update **live** without any user action.

### API layer (`src/api/`)

Thin Supabase query functions — no business logic. Hooks import these.

```
src/api/
  client.ts        — Supabase singleton
  approvals.ts     — CRUD for approval_requests
  insights.ts      — read/dismiss client_insights
  agents.ts        — client_enabled_agents + agent_catalog
  analytics.ts     — client_kpi_snapshot + analytics_v2 RPCs
  notifications.ts — notifications read/dismiss
  chat.ts          — conversa + messages + streaming
  admin.ts         — integrations, audit_log, billing
  suppliers.ts     — suppliers CRUD
  routines.ts      — client_routines CRUD
  approval-rules.ts — client_approval_rules + client_approval_stats
```

---

## Phase 4 — Home / Command Center

**Goal:** The owner's daily decision inbox. The most important screen.

### Layout

```
Mobile (base):  DecidirAgora → PlanoDeHoje → VisaoSemana → InsightsPanel → NumbersPanel
Desktop (lg:):  [DecidirAgora 2/3 max-w-[520px]] [PlanoDeHoje + VisaoSemana 1/3] → InsightsPanel → NumbersPanel
```

On large desktops (`xl:`), a third column emerges: `[DecidirAgora max-520] [Plano/Visao] [Insights]`. Decision cards are capped at `max-w-[520px]` regardless of column width — they were designed for that width.

### Data (parallel `useQueries` on mount)

```ts
useQueries([
  usePendingApprovals(), // DecidirAgora
  useInsights(), // InsightsPanel
  useAgents(), // AgentStatusRow (desktop) + nav dots
  useKpiSnapshot("30d"), // NumbersPanel collapsed line
  // Calendar events via Edge Function if calendar_settings.enabled
]);
```

### Components

**`DecidirAgora`**

- Fixed-height scrollable container (`max-h-[480px] overflow-y-auto`), does NOT flow into page scroll
- Maximum 5 cards visible; "Ver todas X decisões →" navigates to `/aprovacoes` (dedicated queue page)
- Empty state: sand background, "🟢 Nada urgente agora. Seu time está trabalhando."
- Loading: 3 × `SkeletonCard`

**`DecisionCard`** (home variant — compact)

- Agent orb + name + relative timestamp (`Há 2 min`)
- `title` field as card header (not parsed from `payload`)
- Proposal text (2 lines, `line-clamp-2`)
- Supporting bullets from `payload.bullets` (max 3)
- Priority: red left border (`border-l-4 border-urgent`) for `'urgent'`, yellow for `'normal'`
- Actions: `[Aprovar]` (ok-color) `[Ver]` (ghost → expands ApprovalCard) `[Depois]` (ghost → SnoozePicker)
- `insight_text` shown below actions in `text-blu-300 text-caption` if present
- Swipe gesture (mobile): right = Aprovar (green overlay), left = Rejeitar (red overlay)
  - Implemented with native `onPointerDown/Move/Up` + CSS `transform: translateX` — no library
  - First-use: show drag handle icon (⋮⋮) on first card + one-time hint toast "Deslize para aprovar ou rejeitar"
  - `touch-action: pan-y` on the card to prevent browser back-navigation conflict on iOS

**`ApprovalCard`** (expanded, shown via "Ver" or in desk room)

- Full proposal paragraph from `payload.description`
- 3-bullet supporting data from `payload.bullets`
- Actions: `[Aprovar]` `[Editar]` `[Rejeitar]` (primary) + `[Me explique melhor]` `[Depois]` (secondary)
- `insight_text` block (muted, collapsible)
- `snooze_until` indicator if previously snoozed: "Adiado de [date]"
- After any action: inline feedback text per concept §6.2 (not a toast — inline, below buttons)

**`SnoozePicker`** (bottom sheet on mobile, popover on desktop)

- Options: `[Em 1 hora]` `[Hoje à tarde]` `[Amanhã]` `[Próxima semana]` `[Escolher data →]`
- "Escolher data" opens a minimal date+time input (`<input type="datetime-local">`)
- Writes `snooze_until` to `approval_requests` via `useSnoozeRequest` mutation
- Toast: "Lembrete agendado. Voltarei a isso [formatted date]."

**`PlanoDeHoje`**

- Time-ordered list (calendar events + `approval_requests.scheduled_for` for today)
- Each item: time pill + agent orb + description
- Collapsible on mobile (`max-h-[200px] overflow-hidden` with "Ver mais →")

**`VisaoSemana`**

- 5-day strip. Each day: weekday + decision count badge (attention/urgent color)
- Tap a day → inline expand (CSS max-height transition) showing that day's items

**`InsightsPanel`**

- 3 visible `InsightCard` items. Dismiss button (×) per card
- "Ver todos X →" link to `/insights` or inline expand
- Dismissal → `useDismissInsight` mutation

**`NumbersPanel`**

- Collapsed (default): single line from `client_kpi_snapshot` WHERE `period='30d'`
  - `Faturamento: R$ 543,8K · Despesas: R$ 312K · Margem: 42%`
- Expand toggle → inline `AnalyticsCard` (CSS max-height accordion, 300ms ease-in-out)
- Loading: `SkeletonCard` matching collapsed line height

**`AgentStatusRow`** — `hidden md:flex`. Desktop-only horizontal strip of `AgentBadge` × 6. Click navigates to room.

---

## Phase 5 — The Desk Pattern

**Goal:** Universal room structure reused across all 6 agent rooms. Build it once, configure per room.

### Layout rules

| Viewport                  | Layout                                                                     |
| ------------------------- | -------------------------------------------------------------------------- |
| Mobile portrait (`base:`) | Single column: DeskSurface full width → Corkboard → drawer pills at bottom |
| Tablet (`md:`)            | Two-column: Left drawer (1/3) + Desk surface (2/3), right drawer as pill   |
| Desktop (`lg:`)           | Three-column: Left (1/4) + Desk (2/4) + Right (1/4). Corkboard below.      |
| Large desktop (`xl:`)     | Three-column + persistent `AgentNav` far left (from Phase 2 shell)         |

### Components

**`DeskSurface`**

- Sections: Urgent decisions (stacked `DecisionCard`) → Active tasks → History tab
- `bg-surface border border-border rounded-md shadow-md`

**`LeftDrawer` / `RightDrawer`**

- Desktop: flanking panels with `DrawerHeader` (title + collapse toggle). `bg-gray-900` (darker than surface).
- Mobile: rendered as pill buttons at bottom of screen (`min-h-[44px]`)
- Tap pill → slides up as bottom sheet: `@radix-ui/react-dialog` for accessibility (focus trap, ARIA, ESC close) with CSS `transform: translateY(0)` / `translateY(100%)` transition (300ms ease-out)
- Only one drawer open at a time on mobile

**`Corkboard`** — Below desk surface, full width. `InsightCard` tiles in responsive grid (`grid-cols-1 md:grid-cols-2 lg:grid-cols-3`). Collapsed to 1 row by default with "Ver mais" expand.

**`UnderDesk`** — `[▶ Rotinas e Configurações]` pill at bottom. Expands via CSS max-height accordion. Contains `RoutineList` + `ConfigPanel`. Trust-gated sections appear based on `trust_level` from `useApprovalStats`.

**`MetricCard`** — Big number (`font-mono text-mono-lg text-white`) + trend arrow + label. Used in desk surface for financial rooms.

**`StatusPill`** — `bg-urgent/attention/ok` rounded pill with count or label.

**`AlertBanner`** — Full-width critical alert. Red gradient background, icon + text + CTA button.

**`RedDot`** — Pulsing indicator using `animate-orb-attention`. Absolutely positioned on parent.

**`EmptyDesk`** — Sand background card: "🟢 Nada urgente agora. Seu time está trabalhando." + "Ver histórico →".

---

## Phase 6 — Interaction Patterns

**`ApprovalModal`**

- Full-screen on mobile, centered modal on desktop
- Uses `@radix-ui/react-dialog` (focus trap, ARIA, ESC closes)
- Full `ApprovalCard` content + expanded payload context
- Keyboard: `Enter` = Aprovar, `Escape` = dismiss
- Also handles: `j/k` navigation between multiple approvals (desktop power-user shortcut)

**`ChatOverlay`**

- Slide-up panel from bottom: `@radix-ui/react-dialog` + CSS `transform: translateY`
- Full chat interface scoped to `conversa.agent_slug` for the current room
- Message streaming:
  - User sends message → `INSERT` into `messages` (role='user')
  - Call streaming Edge Function → `fetch()` + `Response.body.getReader()` for SSE chunks
  - Chunks render progressively in a local state buffer (not persisted until complete)
  - On stream complete → `INSERT` full assistant message into `messages`
  - Typing indicator: CSS `animate-orb-pulse` on the agent orb while streaming
  - Stream cancellation: `AbortController` wired to close button
- Close: swipe down or close button → unmount, abort any active stream

**`ExpandableSection`** — Accordion using CSS `max-height` transition (300ms ease-in-out). No layout shift on open.

**`Tooltip`** — Hover delay 300ms. `@radix-ui/react-tooltip` for positioning + accessibility.

**`Popover`** — Click-triggered menu. `@radix-ui/react-popover`. Closes on outside click. Focus trapped.

---

## Phase 7 — ComprasRoom (Reference Implementation)

The first complete agent room. All other rooms follow the same pattern — build this one right.

| Zone         | Content                                                     | Data Source                                           |
| ------------ | ----------------------------------------------------------- | ----------------------------------------------------- |
| Desk Surface | Active quotations, pending approvals, urgent stock alerts   | `approval_requests` WHERE `agent_slug='compras'`      |
| Left Drawer  | Supplier list with star ratings + category pills            | `suppliers` table                                     |
| Right Drawer | Last 10 purchases, approval history, spending by category   | `audit_log` + `analytics_v2.fato_transacoes`          |
| Corkboard    | Supplier quality/pricing insights                           | `client_insights` WHERE `dimension='compras'`         |
| Under Desk   | Stock check routines, quotation schedules, alert thresholds | `client_routines` WHERE `routine_id LIKE 'compras/%'` |

**Left Drawer specifics:** `ResourceList` showing `suppliers` rows. Each row: star rating (`★★★★☆`), supplier name, category pill, performance summary. `CategoryTags` filter strip at top (`[Todos] [Escritório] [Insumos] [Limpeza]`). Empty state → `EmptyDrawer` with "Adicionar primeiro fornecedor →".

---

## Phase 8 — Remaining Agent Rooms

Pattern identical to ComprasRoom. Room-specific content below.

### FinanceiroRoom

| Zone         | Content                                                                     | Data Source                                                                 |
| ------------ | --------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Desk Surface | `MetricCard` (today's balance) + pending payments list + upcoming due dates | `approval_requests` WHERE `agent_slug='financeiro'` + `client_kpi_snapshot` |
| Left Drawer  | Connected accounts with balances                                            | `credencial_servico_externo` + `integration_tokens`                         |
| Right Drawer | Generated reports list (DRE, cash flow, margin)                             | `report_schedules` + `report_runs`                                          |
| Corkboard    | Cost trend insights                                                         | `client_insights` WHERE `dimension='financeiro'`                            |
| Under Desk   | Monthly close routine, cost variance alert, DRE auto-gen                    | `client_routines`                                                           |
| **Extra**    | `AnalyticsCard` (expandable, full KPI grid + charts) below Corkboard        | `analytics_v2`                                                              |

### AgendaRoom

| Zone         | Content                                                     | Data Source                                                              |
| ------------ | ----------------------------------------------------------- | ------------------------------------------------------------------------ |
| Desk Surface | Today's schedule (time-ordered) + pending meeting approvals | `approval_requests` WHERE `agent_slug='agenda'` + Calendar Edge Function |
| Left Drawer  | Connected calendars + routine templates                     | `calendar_settings` + `client_routines`                                  |
| Right Drawer | Past events + decision history per meeting                  | `audit_log` filtered by `entity_type='agenda'`                           |
| Corkboard    | Scheduling insights                                         | `client_insights` WHERE `dimension='agenda'`                             |
| Under Desk   | Weekly planning, stand-up reminders                         | `client_routines`                                                        |

### DocumentosRoom

| Zone         | Content                                                    | Data Source                                           |
| ------------ | ---------------------------------------------------------- | ----------------------------------------------------- |
| Desk Surface | Active draft (if editing) OR recent documents list         | `vector_db.documents` WHERE `agent_slug='documentos'` |
| Left Drawer  | Template library (`ModelDrawer`)                           | `doc_templates` (system + client)                     |
| Right Drawer | Archived docs + version history (`ArchiveDrawer`)          | `vector_db.document_versions`                         |
| Corkboard    | Document pattern insights                                  | `client_insights` WHERE `dimension='documentos'`      |
| Under Desk   | Auto-save config, backup routines, approval workflow rules | `client_routines`                                     |
| **Extra**    | `EditorCanvas` expands full-width when editing             | `vector_db.documents.editor_content`                  |

**Editor specifics:** Tiptap (not ContentEditable). Extensions: StarterKit, Placeholder, CharacterCount. Auto-save: debounced 30s → `UPDATE vector_db.documents SET editor_content = ?` + status indicator (`Spinner → CheckCircle`). `DocToolbar` sticky: `[Modelo] [IA escrever] [Revisar] [Salvar] [Exportar PDF]`. EditorCanvas expands to full viewport width when active, collapsing Left/Right drawers.

### EstrategiaRoom

| Zone         | Content                                                                  | Data Source                                         |
| ------------ | ------------------------------------------------------------------------ | --------------------------------------------------- |
| Desk Surface | Current analyses in progress + pending scenario reviews + anomaly alerts | `approval_requests` WHERE `agent_slug='estrategia'` |
| Left Drawer  | Monitored KPIs, benchmarks, goals                                        | `client_dimension_kpis` + `kpi_catalog`             |
| Right Drawer | Past analyses, predictions, decision outcomes                            | `audit_log` + `analytics_v2`                        |
| Corkboard    | Strategic insights (margins, supplier trends)                            | `client_insights` WHERE `dimension='estrategia'`    |
| Under Desk   | Monthly margin routine, quarterly trend report                           | `client_routines`                                   |

### ClientesRoom

| Zone         | Content                                        | Data Source                                                                     |
| ------------ | ---------------------------------------------- | ------------------------------------------------------------------------------- |
| Desk Surface | Top customers + recent activity + churn alerts | `approval_requests` WHERE `agent_slug='clientes'` + `analytics_v2.dim_clientes` |
| Left Drawer  | Customer segments (Alto/Médio/Baixo cluster)   | `analytics_v2.dim_clientes` grouped by `nivel_cluster`                          |
| Right Drawer | Customer history + transaction list            | `analytics_v2.fato_transacoes` filtered by `client_id`                          |
| Corkboard    | Customer growth and frequency insights         | `client_insights` WHERE `dimension='clientes'`                                  |
| Under Desk   | Follow-up routines                             | `client_routines`                                                               |

---

## Phase 9 — Analytics

Used inside `FinanceiroRoom` (`AnalyticsCard`) and `NumbersPanel` (Home).

**`AnalyticsCard`** — Collapsible container (CSS max-height accordion). Header shows 1-line summary when collapsed from `client_kpi_snapshot`.

**`KpiGrid`** — 2×2 or 4-across responsive grid. Each cell: big number (`font-mono text-mono-lg`) + label + trend arrow + period delta. Numbers from `client_kpi_snapshot.metrics`.

**`AreaCards`** — Icon + metric cards for Pedidos / Clientes / Fornecedores / Produtos from `kpi_snapshot`.

**`ChartContainer`** — Tabbed: `Receita | Despesas | Fluxo de Caixa`. Recharts components:

- Receita: `AreaChart` (blu-500 fill, smooth curves)
- Despesas: `BarChart` (stacked by category)
- Fluxo: `LineChart` (two lines: entrada/saída)
- All charts: no grid lines, `blu-500` strokes, custom `Tooltip`, responsive container
- Data from `analytics_v2.mv_series_temporal` via RPC

**`PeriodSelector`** — Pill group: `[7 dias] [30 dias] [90 dias] [1 ano]`. On change: invalidate + refetch `kpi_snapshot` for selected period + rerender charts.

**`ActivityFeed`** — Scrollable list from `audit_log` (client_id, recent 20 entries). Each: agent orb + action text + timestamp.

---

## Phase 10 — Progressive Trust UX

**Goal:** The trust milestones are gamification moments, not silent backend flags.

### Trust Level Detection

`useApprovalStats` reads `client_approval_stats`. On every approval action mutation, after invalidation, check if `total_approved` crossed a threshold that wasn't previously crossed (stored in local `sessionStorage` to avoid re-showing on refresh).

### Milestone Triggers

| Threshold    | Trigger                                   | UI Moment                                                                                                                                           |
| ------------ | ----------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| 10 approvals | `trust_level` changes to `similar_toggle` | Corkboard insight card appears: "Você aprovou 10 missões. Quer automatizar aprovações similares em Compras?" + [Configurar] CTA → opens `UnderDesk` |
| 25 approvals | `trust_level` changes to `rules`          | Corkboard insight: "Você aprovou 25 missões. Desbloqueou regras avançadas — ex: aprovar automaticamente compras abaixo de R$ 500."                  |
| 50 approvals | `trust_level` changes to `full_config`    | Corkboard insight + `SuccessToast`: "Configuração completa desbloqueada. Blu conhece o seu negócio."                                                |

### `RuleBuilder` (in UnderDesk, trust-gated)

- Hidden until `trust_level >= 'rules'`
- Visual rule creator: `[Agente ▼] [Tipo de regra ▼] [Condição]` → `[Salvar regra]`
- Writes to `client_approval_rules`
- Never-auto-approve list displayed as locked items (enforced server-side; shown for transparency)

---

## Phase 11 — Admin

Tabbed layout (not desk pattern). `AdminLayout` with `TabGroup` header.

| Tab          | Component                        | Data Source                                         |
| ------------ | -------------------------------- | --------------------------------------------------- |
| Integrações  | `IntegrationCard` × N providers  | `credencial_servico_externo` + `integration_tokens` |
| Usuários     | `UserTable` + `PermissionToggle` | Supabase auth + `clientes_blu`                      |
| Faturamento  | `BillingCard`                    | `clientes_blu.tier`                                 |
| Auditoria    | `AuditLog`                       | `audit_log` (paginated, 50/page)                    |
| LGPD         | `DataPrivacyPanel`               | client data export / deletion request               |
| Notificações | `NotificationPreferences`        | `client_notification_preferences`                   |

**`IntegrationCard`** — Provider logo + status (`✅ Conectado / ⚠️ Erro / ⬜ Não conectado`) + last sync time + `[Sincronizar agora] [Configurar] [Desconectar]`. Status from `credencial_servico_externo.status`.

---

## Phase 12 — Feedback & States

| Component      | Trigger                                               | Behavior                                                                                    |
| -------------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| `SkeletonCard` | While fetching                                        | Matches target component dimensions exactly. Animated shimmer via CSS `@keyframes shimmer`. |
| `LoadingAgent` | Agent orb with `animate-orb-pulse`                    | "Processando..." text. Used inside `DeskSurface` when agent is `current_status='working'`.  |
| `SuccessToast` | After Aprovar/Rejeitar/save                           | ok-color, 3s auto-dismiss, slides up from bottom.                                           |
| `ErrorHuman`   | Network/API error (via TanStack Query global handler) | Friendly message + retry button. Never shows stack trace.                                   |
| `EmptyState`   | Generic empty (drawers, lists, rooms)                 | Icon + title + body + CTA. Warm sand background.                                            |

**Toast implementation:** CSS-only slide-up (`transform: translateY(100%) → 0`, 200ms ease-out). Auto-dismiss with `setTimeout`. Stack-aware (multiple toasts stack vertically). No library needed.

---

## Delivery Order — Sprint Sequence

| Sprint | Phases                            | Output                                                             |
| ------ | --------------------------------- | ------------------------------------------------------------------ |
| 0      | Schema P0+P1 migrations           | DB ready for frontend                                              |
| 1      | Phase 0 + Phase 1                 | Running app, design tokens, all primitives                         |
| 2      | Phase 2 + Phase 3                 | App shell, navigation, full data layer + Realtime wired            |
| 3      | Phase 4                           | Full Home screen with live approvals, insights, KPI panel          |
| 4      | Phase 5 + Phase 6                 | Desk pattern (generic) + all interaction patterns                  |
| 5      | Phase 7                           | ComprasRoom complete (reference for desk pattern)                  |
| 6      | Phase 8 (first 2 rooms)           | FinanceiroRoom + AgendaRoom                                        |
| 7      | Phase 8 (last 3 rooms) + Phase 10 | DocumentosRoom + EstrategiaRoom + ClientesRoom + Progressive Trust |
| 8      | Phase 9                           | Analytics (charts, KPI grid, period selector)                      |
| 9      | Phase 11 + Phase 12               | Admin + Feedback states + polish                                   |

---

## Key Decisions

1. **No Framer Motion** — All animations are CSS keyframes + transitions. The bundle stays light. Bottom sheets use `@radix-ui/react-dialog` + CSS `transform`. Swipe cards use native pointer events + CSS.
2. **Tailwind v3** — The visual reference config is v3 syntax (`tailwind.config.js`). v4 migration can happen later. All tokens are Tailwind class names, not inline CSS variables.
3. **TanStack Query as source of truth** — No `ApprovalContext` holding approval data. All components read from the query cache. Mutations invalidate queries — state stays consistent across Home and agent rooms automatically.
4. **Supabase Realtime for live updates** — Single channel mounted in `AppShell`. Approval inserts → live red dots + `DecidirAgora` refresh. Notification inserts → bell badge update.
5. **Tiptap for document editing** — Not ContentEditable. ProseMirror-based, React-native, extensible. `editor_content` stored in `vector_db.documents` (separate from RAG chunk pipeline).
6. **@radix-ui for accessible primitives** — `Dialog`, `Tooltip`, `Popover` from Radix. Handles focus trapping, ARIA, keyboard navigation. Styled with Tailwind tokens.
7. **Streaming chat** — `fetch()` + `ReadableStream` for SSE from Edge Function. Local state buffer during stream; persisted to `messages` only on completion.
8. **Mobile-first breakpoints** — `base` (mobile) → `md` (tablet) → `lg` (desktop) → `xl` (large desktop). Every component defaults to mobile layout, enhanced upward.
9. **Context strategy** — `AuthContext` (global, session only) + `NotificationContext` (global, drives bell badge) + `RealtimeContext` (global, mounts one channel). Agent/room data via TanStack Query hooks, fetched locally per page.
10. **Schema gaps** — All tracked in [`blu_app_schema_gaps.md`](./blu_app_schema_gaps.md). Migration order defined there. Frontend phases assume the corresponding migrations are already applied.
