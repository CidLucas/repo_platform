# Blu — CRO & UX Revamp Plan

**Date:** 2026-04-27
**Owner:** Lucas
**Scope:** `apps/landing`, `apps/vizu_dashboard`, supporting backend
(`libs/vizu_context_service`, `kpi_catalog`, agent suggestion service).
**Goal:** Make Blu feel like _point, click and chat_ — fast time-to-value,
mission-control home, smart context-driven onboarding.

> This plan replaces the chat-first home idea from the initial audit. The home
> is a **personal mission control**; chat is a persistent, visible companion,
> not the whole screen.

---

## 1. North-star principles

1. **Mission control, not metrics dump.** Home tells the user, in 5 seconds:
   _what needs my attention today, what's coming this week, what Blu is
   suggesting next._
2. **Chat is the right hand, not the room.** Always visible (right rail or
   docked panel), can expand to full screen when the user explicitly asks. It
   never replaces the dashboard.
3. **Earn context, don't ask for it.** After signup we scrape the user's
   website + a couple of clarifying questions and _propose_ a complete starter
   pack (agents + routines + KPIs). User approves or tweaks. No 7-step form.
4. **Aha in 60 seconds, full activation in 7 days.** First "wow" before signup
   (interactive demo). Real activation = first connector + first approved
   action.
5. **One thing at a time, in context.** Cognitive load deferred to the moment
   each decision actually matters.

---

## 2. Current state — pain summary

(See full audit in chat history; condensed here. Observations from screenshots
in `docs/screenshots/` are reflected below.)

| Area           | Today                                                                                                                    | Problem                                                   |
| -------------- | ------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------- |
| Landing        | Static, no demo, 1 testimonial, no FAQ                                                                                   | Visitor commits OAuth before tasting                      |
| Onboarding     | 7 screens (Auth → Welcome → DNA → DataFork → Agents → Rules → Launch)                                                    | All friction, zero value, mid-flow redirects out          |
| Dashboard home | Metrics-heavy `HomePage`, all zeros for new tenant                                                                       | No "what should I do today?"                              |
| Chat           | `ChatPanel` slide-in, hidden trigger                                                                                     | Differentiator buried                                     |
| Menu           | Header has 2 routes; ~22 sub-routes nested under `/admin/*`                                                              | Daily-use surfaces buried inside settings                 |
| KPIs           | `kpi_catalog` exists (5 dims × N KPIs) but no per-tenant selection                                                       | Generic dashboards for everyone                           |
| Approvals      | `/inbox` is one route among many                                                                                         | HITL — _the_ differentiator — is invisible                |
| i18n           | Visible UI mixes pt-BR and English ("REVENUE THIS MONTH", "AI TASKS TODAY") + typos ("Planos contratado")                | Brand-damaging for a pt-BR-only product                   |
| Demo data      | Demo numbers leak into UI without flag (e.g. "41.343 tasks in progress") and deltas have inverted icon/sign (`↗ -85,8%`) | Trust-killer; redesign on top of broken numbers is wasted |
| Header chrome  | Undocumented app-grid icon next to bell/avatar                                                                           | Undefined icon in primary chrome is an antipattern        |

---

## 3. Target architecture

### 3.1 Mission Control home (`/dashboard`)

Layout (desktop, 1440px reference):

```
┌─────────────────────────────────────────────────────────────────────┐
│  Header (logo, search, profile, notifications, "Aprovar (3)")       │
├──────────────────────────────────────────────────┬──────────────────┤
│                                                  │                  │
│  [Hello, Lucas. Aqui está o seu dia.]           │   CHAT COMPANION │
│                                                  │   (collapsible   │
│  ┌─ AGORA ──────────────────────────┐            │    rail, ~360px) │
│  │ • 3 aprovações pendentes →       │            │                  │
│  │ • 2 alertas críticos             │            │   "Pergunte ao   │
│  │ • 1 cliente sem resposta há 3d   │            │    Blu sobre     │
│  └──────────────────────────────────┘            │    seus dados…"  │
│                                                  │                  │
│  ┌─ HOJE ───────────────────────────┐            │   [chips:        │
│  │ Agenda · 3 compromissos          │            │    "vendas hoje" │
│  │ Rotinas rodando · 4              │            │    "estoque"     │
│  │ Próxima ação: ligar Cliente X    │            │    "follow-ups"] │
│  └──────────────────────────────────┘            │                  │
│                                                  │   [history…]     │
│  ┌─ SEUS KPIs ──────────────────────┐            │                  │
│  │ (5 KPIs escolhidos pelo cliente, │            │                  │
│  │  por dimensão ativa)             │            │                  │
│  └──────────────────────────────────┘            │   [Expandir ⤢]   │
│                                                  │                  │
│  ┌─ ESTA SEMANA ────────────────────┐            │                  │
│  │ Forecast / pipeline / agenda     │            │                  │
│  └──────────────────────────────────┘            │                  │
│                                                  │                  │
│  ┌─ INSIGHTS ACIONÁVEIS ────────────┐            │                  │
│  │ • "Seu CAC subiu 18% — investigar?"           │                  │
│  │ • "5 SKUs sem giro há 30d — pausar?"          │                  │
│  │ Cada card vira um mini-onboarding             │                  │
│  │ que abre chat com prompt pré-pronto           │                  │
│  └──────────────────────────────────┘            │                  │
│                                                  │                  │
└──────────────────────────────────────────────────┴──────────────────┘
```

Key behaviors:

- **Chat rail** is always visible on `xl+` (≥1440px); collapses to a 64px
  icon strip on `lg` (1280–1440px); becomes a docked button on mobile.
  "Expandir ⤢" makes it full-screen overlay (current `ChatPanel` behavior
  preserved as the _expanded_ mode).
- **Insight cards** open chat with a pre-filled prompt + scroll relevant
  dashboard panel into view, then **return focus to the originating card**
  on close (WCAG 2.4.3). Every insight is also a guided tour.
- **"Aprovar (N)"** badge in header is the daily return hook. Screen-reader
  text must read "N aprovações pendentes", not just the number.
- **Vanity-card antipattern is out.** No bare-number cards. Every KPI card
  must answer three questions in one glance: _where am I_ (number),
  _is that good_ (delta + sparkline + color), _what now_ (one inline action).

#### 3.1.1 State machine (REQUIRED — not just a layout)

Mission Control renders one of four states. Without this, the redesign is
cosmetic and new tenants will see the same wall of suspiciously round
numbers as today.

| State   | When                                        | What renders                                                                                |
| ------- | ------------------------------------------- | ------------------------------------------------------------------------------------------- |
| `empty` | Pre-demo seed (very rare; first paint only) | Only "Agora" + onboarding checklist + 1 hero insight. KPIs and Forecast hidden.             |
| `demo`  | Tenant has only `is_sample = true` rows     | Full layout. Every panel carries an `Exemplo` chip. Sticky banner: "Conectar minha loja →". |
| `live`  | At least one connector has synced real data | Full layout, banner gone. Demo rows soft-hidden (toggle to switch back).                    |
| `power` | User opt-in (toggle in Configurar)          | Drag-handles on each card; user can reorder/hide sections. Persisted per device.            |

- Demo banner copy: _"🧪 Você está vendo dados de exemplo. **Conectar minha loja →**"_.
- KPIs render as **3 primary (large) + 2 secondary (compact)** by default.
  In `demo` state, only the 3 primary are shown until first sync.
- Insight cards must reference a specific number, imply causation, and end
  with one verb ("Investigar →"). Generic celebration insights are forbidden.

### 3.2 Chat companion (right rail)

**Sizing & breakpoints (revised):**

- Default width: **320px** (not 360px — preserves a 4-col KPI grid in main column at 1440px).
- `≥1440px`: docked open by default at 320px.
- `1280–1439px`: collapsed to **64px icon strip**; click expands as overlay.
- `<1280px`: bottom-sheet trigger; full-screen on tap.
- Keyboard shortcut: **`⌘\` / `Ctrl+\`** to toggle (industry standard).
- User collapse preference is persisted per device.
- The current right rail (Agenda + Atividade Recente) is **folded into
  "Hoje"** in the main column. The right rail is chat-only after the redesign.

States:

1. **Docked (default on xl+)** — 320px rail, last 3 messages + input + up to
   **3 suggestion chips** (hard cap; more reads as noise). ~85% of value here.
2. **Expanded** — full-screen overlay (current `ChatPanel` slide). For
   long-running analyses or deep conversations.
3. **Inline artifact** — when user clicks an insight or table cell, chat
   docks open with the relevant query already typed.

Suggestion chips are **dynamic, context-aware** (max 3 visible):

- New tenant: "Conectar minha loja", "Importar planilha", "Ver agentes"
- After first connector: "Vendas dessa semana", "Ticket médio", "Top produtos"
- After first insight: "Por que isso aconteceu?", "O que faço?"

A **focus mode** toggle (in user menu) hides the rail entirely for
keyboard-driven workflows.

### 3.3 Information architecture (reframe — header is already 2 routes)

The header today only exposes 2 routes (Dashboard / Admin). The 22 sub-routes
live **inside Admin's sidebar**. The work is therefore not "22→5 at the top
level"; it is to **promote the daily-use surfaces out of Admin** and **rename
Admin → Configurar**.

Final top-level (header):

| Top-level           | Replaces                                                          | Notes                                                                                  |
| ------------------- | ----------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| **Mission Control** | `/dashboard` (HomePage)                                           | New layout above                                                                       |
| **Aprovações**      | `/dashboard/inbox`                                                | Promoted; badge in header                                                              |
| **Painéis**         | `/dashboard/{fornecedores, produtos, clientes, pedidos, reports}` | Sidebar group, **inline-expanded** (not a wrapper page) so daily-use is one click      |
| **Configurar**      | All `/dashboard/admin/*` (renamed)                                | Keeps current Admin sidebar (Fonte de Dados, Base de Conhecimento, Agentes, Planos, …) |
| **Ajuda**           | `/dashboard/admin/ajuda` + chat fallback                          |                                                                                        |

The undocumented app-grid icon currently in the header is **either defined
as a workspace switcher or removed** before C-phase ships. Undefined icons
in primary chrome are an antipattern.

Super-admin (`/dashboard/super-admin/*`) stays on its own gated namespace.

---

## 4. Onboarding redesign — context-driven, not form-driven

### 4.1 New flow (honest 4 steps)

Context Confirmation **is folded into the top of Package Proposal** — one
screen with two sections, one CTA. This makes the website-scrape payoff
visible on the same surface as the input that triggered it, and keeps the
flow at a real 4 steps (Auth → Website → Package → Launch).

```
LANDING
  ├─ Hero + value props
  ├─ INTERACTIVE DEMO (no auth) — types a question against seed tenant
  └─ [Salvar este resultado] → opens signup modal at the moment of intent
       │
       ▼
SIGNUP (Google one-tap, magic-link fallback)
       │
       ▼
WEBSITE STEP            ← THIS IS NEW
   "Qual o site da sua empresa?"
   [acme.com.br]
   [Não tenho site / pular] (always available)
       │
       ▼ (scrape kicked off in PARALLEL with auth callback —
          Package Proposal renders immediately with defaults;
          personalized swaps stream in. Hard timeout: 6s.)
       │
PACKAGE PROPOSAL (single screen — the big "wow")
   ┌─ ACHEI ISTO SOBRE VOCÊS ────────────┐
   │ Empresa: Acme Distribuidora [✏️]    │
   │ Setor:   Distribuição B2B   [✏️]    │
   │ Porte:   ~30 funcionários   [✏️]    │
   │ Foco principal: ?           ← required
   │   ◯ Vendas crescer                  │
   │   ◯ Operação travada                │
   │   ◯ Atendimento ruim                │
   │   ◯ Estoque sangrando               │
   │   ◯ Outro                           │
   └─────────────────────────────────────┘
   "Para uma {Distribuidora B2B} focada em {Operação}, eu sugiro:"
   ┌─ AGENTES ────────────────────────────┐
   │ ✓ Análise          ✓ Compras          │
   │ ✓ Atendimento      ☐ Documentos       │
   │ ☐ Agenda           ☐ Planejamento     │
   └──────────────────────────────────────┘
   ┌─ ROTINAS ────────────────────────────┐
   │ ✓ Resumo diário de vendas             │
   │ ✓ Alerta de estoque baixo             │
   │ ✓ Cobrança de inadimplentes           │
   │ ☐ Sinal de churn                      │
   │ + 4 outras…                           │
   └──────────────────────────────────────┘
   ┌─ KPIs DO SEU PAINEL (5 por dimensão) ┐
   │ Comercial: Receita, NRR, Ticket,      │
   │            Top Clientes, Pipeline     │
   │ Estoque:   Giro, Stockout, Cobertura, │
   │            Top SKU sem giro, Margem   │
   │ Compras:   Spend, SLA, % cobertura,   │
   │            Economia, RFQ ativos       │
   │ [edit per dimension]                  │
   └──────────────────────────────────────┘
   [Vamos com isto] [Ajustar tudo →]
       │
       ▼
MISSION CONTROL (LaunchPad is FOLDED IN as a first-run coach-mark overlay
   pointing at: Agora → 1st Insight card → Chat rail, in 3 beats.)
   Persistent checklist card (dismissible per item):
   ☐ Conectar dados reais (você está em modo demo)
   ☐ Aprovar primeira ação
   ☐ Convidar 1 colega
   ☐ Personalizar regras de aprovação
```

What we kill:

- `/onboarding/welcome` (becomes part of the website-step transition)
- `/onboarding/dna` (replaced by context confirmation)
- `/onboarding/data` mid-flow connector redirect (moved to in-product modal)
- `/onboarding/rules` (defaults: every external action requires approval; per-task
  config surfaces _the first time each task is actually attempted_)

What we keep:

- `/onboarding/auth`, `/onboarding/agents` (recast as "Pacote sugerido").
- `/onboarding/launch` (LaunchPad) is **deprecated as a route** and replaced
  by a first-run overlay on Mission Control. This is intentional: a separate
  LaunchPad reintroduces the step we just removed and contradicts the
  "mission control = home" thesis.

### 4.2 Website-scrape context service

New service: `libs/vizu_landing_intel` (or extend
`libs/vizu_context_service`).

Inputs: `website_url: str`
Outputs:

```python
@dataclass
class LandingIntel:
    company_name: str | None
    industry_tags: list[str]      # mapped to our verticals + sub-verticals
    suggested_size: str | None    # "solo|micro|pequena|media|grande"
    products_or_services: list[str]
    likely_pain_points: list[str] # ranked
    suggested_agents: list[str]
    suggested_routines: list[RoutineId]
    suggested_kpis: dict[DimensionKey, list[str]]  # 5 per dim, slugs from kpi_catalog
    raw_summary: str              # for transparency / debug
    confidence: float
```

Implementation:

1. Fetch URL with timeout (~5s) via existing HTTP utils.
2. Extract main content (readability-style strip).
3. Send to LLM with a structured-output prompt that reasons about
   industry → which agents/routines/KPIs from our catalog fit.
4. Map outputs against `kpi_catalog` slugs (must exist), `agent_catalog`
   slugs (must exist), and `RoutineId` enum (must exist) — drop unknowns.
5. Persist raw + structured output in `clientes_vizu.onboarding_state.intel`
   for audit and re-run.

**Latency contract — REQUIRED (CRO time-bomb if missed):**

- Scrape is triggered **on the auth callback**, in parallel with the redirect
  to the Website step. By the time the user submits a URL, intel is often
  already underway against a cached fetch.
- Package Proposal screen renders **immediately with the catalog defaults**
  (`is_default=true`, ranked by `default_dimension_rank`). Personalized swaps
  stream in as intel completes — never blocks paint.
- **Hard timeout: 6s.** On timeout, the screen stays on defaults and the
  "focus" question alone drives the suggestion.
- The "Próximo / Vamos com isto" CTA is **never disabled by intel state**.
  Skip-without-shame is the rule.
- Loading affordance: a skeleton chip on each personalized field ("ajustando…")
  that swaps to the value when ready. No spinners over the whole screen.

Fallbacks: if scrape fails → defaults + focus question. The "focus" answer
alone yields a usable starter pack.

### 4.3 KPI selection (5 slots × dimension)

Backend

- New table `client_dimension_kpis(client_id, dimension, kpi_slug, slot_index 0-4)`
  with PK `(client_id, dimension, slot_index)` and FK to `kpi_catalog.slug`.
- RLS: tenant-scoped (read/write own rows).
- New RPC `set_client_dimension_kpis(p_dimension, p_slugs text[])` that
  validates each slug against `kpi_catalog`, validates count ≤ 5, replaces
  the dimension's set atomically.
- New RPC `get_my_dashboard_kpis()` returning `dimension → ordered KPI list`,
  joined with `kpi_catalog` for label/unit/formula/data_status.

Frontend

- Mission Control reads via `analyticsService.getMyDashboardKpis()`.
- KPIs render as **3 primary (large cards) + 2 secondary (compact)**. Slot
  indices `0..2` are primary; `3..4` are secondary. In `demo` state, only
  the 3 primary are shown until first connector sync.
- "Configurar > KPIs do painel" page: per-dimension picker with drag-to-reorder;
  shows `data_status` badge (live/proxy/external/pending_data) so users know
  which still need data.
- Onboarding "Package proposal" pre-selects up to 5/dim from `LandingIntel`;
  user can edit per dimension via accordion.

Defaults (used when intel is unavailable):

- Provided as `kpi_catalog.is_default boolean` plus `default_dimension_rank`
  so the same suggestion logic works in product without LLM.

### 4.4 Demo-mode seed data

Every new tenant is provisioned with **read-only demo data flagged
`is_sample = true`** in core fact tables (orders, customers, suppliers,
products, conversations, approvals). Mission Control renders a persistent
banner:

> 🧪 Você está vendo dados de exemplo. **Conectar minha loja →**

When the first real connector finishes its first sync, demo rows are hidden
(soft-flag, not deleted, so the user can switch back).

**Visual enforcement (REQUIRED):** every chart, table cell and KPI card that
renders sample rows must carry an `Exemplo` chip. The current bug —
_"41.343 tasks in progress" leaking unflagged_ — is the antipattern this
rule exists to kill.

**Sanity bounds:** delta calculations must validate sign vs. icon. The
current bug — _green up-arrow next to `-85,8%`_ — must be impossible after
the fix: a single helper formats `(value, delta) → {label, color, icon}` and
is the only path KPI cards use.

This is what makes "aha in 60 seconds" possible: the first load of Mission
Control shows a fully populated, opinionated dashboard _with the KPIs the
user just chose_, not zeros.

---

## 5. Landing — see `docs/internal/landing-guideline.md`

Quick wins (not the full guideline — that's its own doc):

- Add interactive demo block above the fold (seed tenant, no auth).
- Logo bar + 3 testimonials with concrete numbers.
- 3-question FAQ (LGPD, integração, cancelamento).
- Replace "Ver como funciona" scroll with embedded product Loom or Storylane.
- Add soft secondary CTA ("Ver demo de 60s").
- 3 paid-traffic landing variants (Compras, Atendimento, Análise) for ad
  message-match.

Long-form copy + section structure lives in the guideline file.

---

## 6. Phasing & sequencing

### Phase A0 — Foundation hygiene (1-2 days, BLOCKS everything else)

Without these the redesign builds on top of broken foundations.

| #    | Item                                                                                                                                                                                                   | Files                                                                  |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------- |
| A0.1 | i18n lockdown: every visible string in pt-BR. Audit "REVENUE THIS MONTH", "AI TASKS TODAY", "ACTIVE", "AI Agents", "Início", "Fonte de Dados" mix, fix typo "Planos contratado" → "Planos contratados" | `apps/vizu_dashboard/src/**/*.tsx`                                     |
| A0.2 | KPI card formatter helper (single source for `value, delta → {label, color, icon}`). Kills the `↗ -85,8%` bug.                                                                                         | `apps/vizu_dashboard/src/components/KpiCard.tsx`                       |
| A0.3 | Demo-data sanity bounds: cap displayed numbers, mandatory `Exemplo` chip on any row where `is_sample = true`.                                                                                          | shared `<SampleBadge/>`, KPI/table primitives                          |
| A0.4 | Decide & document the header app-grid icon (workspace switcher) or remove it.                                                                                                                          | `apps/vizu_dashboard/src/components/Header.tsx`                        |
| A0.5 | Deprecate generic celebration insights (e.g. "Sua base cresceu… Continue assim! 🎉"); enforce specific-number rule.                                                                                    | `apps/vizu_dashboard/src/components/QuickInsight.tsx` (or replacement) |

### Phase A — Quick wins (1-2 weeks)

| #   | Item                                                                                                              | Files                                                           |
| --- | ----------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| A1  | Landing: demo block, logos, testimonials, FAQ, secondary CTA                                                      | `apps/landing/src/pages/LandingPage.tsx`                        |
| A2  | Demo-data seed for new tenants (migration + flag)                                                                 | `supabase/migrations/...`, `services/file_upload_api` skip rule |
| A3  | Persistent onboarding checklist card on Mission Control                                                           | `apps/vizu_dashboard/src/components/OnboardingChecklist.tsx`    |
| A4  | Approvals badge in header (with SR text "N aprovações pendentes")                                                 | `apps/vizu_dashboard/src/components/Header.tsx`                 |
| A5  | Mission Control reorder: "Agora / Hoje / KPIs / Esta semana / Insights" + state machine (`empty/demo/live/power`) | `apps/vizu_dashboard/src/pages/HomePage.tsx`                    |
| A6  | Replace vanity "Áreas de Negócio" 4-card row with 3 actionable cards (number + delta + sparkline + inline action) | `apps/vizu_dashboard/src/pages/HomePage.tsx`                    |

### Phase B — Onboarding core (2-3 weeks)

| #   | Item                                                                                                                                                    |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| B1  | `libs/vizu_landing_intel` + `LandingIntel` schema + LLM prompt + 6s hard timeout + parallel kickoff on auth callback                                    |
| B2  | New onboarding step: Website (replaces Welcome+DNA)                                                                                                     |
| B3  | New onboarding step: Package Proposal (folds Context Confirmation as top section). Optimistic render with defaults, streamed personalized swaps.        |
| B4  | `client_dimension_kpis` table + RPCs + RLS, with `default_dimension_rank` on `kpi_catalog` (same migration)                                             |
| B5  | Just-in-time approval rule prompt — **single binary** ("Sempre pedir aprovação? [Sim] [Só desta vez]"). Anything granular goes to `/configurar/regras`. |
| B6  | Convert connector flow from full-page redirect to dashboard modal callable from inside onboarding                                                       |
| B7  | Fold LaunchPad into Mission Control first-run coach-mark overlay; deprecate `/onboarding/launch` route                                                  |

### Phase C — Information architecture (3-4 weeks)

Status (2026-04-27): **C1-C5 implementados (fase C concluída)** — atalho `⌘\` / `Ctrl+\` no `ChatContext`; `ChatRail` responsivo no `MainLayout` com focus mode sincronizado (rail + menu do usuário); `InsightsCard` no fluxo principal do Mission Control com deep-link para chat, scroll contextual de seção e retorno de foco no fechamento (WCAG 2.4.3); header com `Aprovações` (badge + texto SR) + grupo `Painéis`; aliases do namespace `/dashboard/configurar/*` com compatibilidade ao legado `/dashboard/admin/*`; chat mobile em bottom-sheet com trigger fixo; e interações principais do dashboard respeitando `prefers-reduced-motion`.

| #   | Item                                                                                                                                                                                                                    |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| C1  | Chat companion right-rail (`ChatRail.tsx`) wrapping current `ChatPanel` logic. Sizing: 320px / 64px / bottom-sheet. `⌘\` shortcut. Focus mode toggle.                                                                   |
| C2  | Mission Control "Insights acionáveis" section with deep-link prompts into chat (and focus return on close, WCAG 2.4.3)                                                                                                  |
| C3  | Promote daily-use surfaces out of Admin into header (Aprovações, Painéis, Configurar, Ajuda); rename `/admin/*` → `/configurar/*` (keep redirects); render Painéis as inline-expanded sidebar group, not a wrapper page |
| C4  | Mobile pass: chat as bottom sheet, MC as scrollable single column                                                                                                                                                       |
| C5  | `prefers-reduced-motion`: kill radial-glow animations on dashboard the same way landing does                                                                                                                            |

### Phase D — Engagement loops (4-6 weeks)

| #   | Item                                                                           |
| --- | ------------------------------------------------------------------------------ |
| D1  | Email triggers: 5min resume, 24h first approval, 72h stalled, 7d weekly digest |
| D2  | WhatsApp/email digest of pending approvals                                     |
| D3  | First-connector celebration toast + suggested next prompts                     |
| D4  | Per-tenant activation funnel dashboard (internal only)                         |

---

## 7. Success metrics

| Metric                               | Source                                                         | Target                                                                                   |
| ------------------------------------ | -------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Landing → demo-tried                 | Posthog event `landing.demo.try`                               | establish baseline, then 30%                                                             |
| Demo → signup                        | Posthog `signup.completed` after demo                          | >25%                                                                                     |
| Signup → website provided            | `clientes_vizu.onboarding_state.website` not null              | >70%                                                                                     |
| Signup → package accepted            | `client_enabled_agents` rows after `set_client_dimension_kpis` | >80%                                                                                     |
| **Insight card CTR (D1)**            | Posthog `mc.insight.click`                                     | leading indicator — establish baseline                                                   |
| **Chat-rail message sent (D1)**      | Posthog `chat.rail.message_sent`                               | leading indicator — establish baseline                                                   |
| Signup → first connector synced (D1) | `fonte_de_dados.synced_at`                                     | >40%                                                                                     |
| **Demo → live switch event**         | Posthog `tenant.sample_data.disabled` (distinct from sync)     | >40% within D7                                                                           |
| Signup → first approval acted (D7)   | `approval_requests.decided_at`                                 | >50% (this is the activation event)                                                      |
| D7 retention                         | `auth.sessions`                                                | establish baseline                                                                       |
| Wizard steps to first dashboard      | route count                                                    | down from 7 → **3 routes** (Auth, Website, Package) — Mission Control replaces LaunchPad |
| Mission Control LCP                  | `web-vitals` event                                             | <2.5s                                                                                    |

The three leading indicators (insight CTR, chat-rail D1 use, demo→live
switch) close the gap between "package accepted" and "first connector synced"
so failures are diagnosable, not just observable.

Instrument via Posthog (frontend) and Langfuse traces (LLM intel
extraction). All events must include `client_id` for tenant rollups.

---

## 8. Risks & mitigations

| Risk                                              | Mitigation                                                                                                                       |
| ------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| Website scrape returns garbage / blocked          | Always allow "skip"; manual focus question alone yields a usable starter pack                                                    |
| Scrape latency tanks Package Proposal conversion  | Optimistic render with defaults; 6s hard timeout; scrape kicked off in parallel with auth callback; CTA never blocked            |
| LLM suggests agents/KPIs we don't have            | Strict mapping against `agent_catalog` and `kpi_catalog`; drop unknowns silently                                                 |
| Demo data confuses users into thinking it's real  | Persistent banner + mandatory `Exemplo` chip on every sample row/chart; auto-hide on first real sync                             |
| 5-KPI limit feels arbitrary                       | 3 primary + 2 secondary by default; demo state shows only the 3 primary; power-users reorder freely; "ver todos" reveals catalog |
| Chat rail steals content density on `lg`          | Collapse to 64px icon strip below 1440px (not 1280px); `⌘\` shortcut; persisted per device; focus mode toggle                    |
| Mid-flow redirects (DataFork pattern) regress     | Strict invariant: onboarding never leaves `/onboarding/*` — connectors are modals                                                |
| JIT approval-rules prompt becomes a decision tree | Constrained to a single binary at first-task moment; granular config lives only in `/configurar/regras`                          |
| Vanity-card antipattern reappears in MC           | Lint rule: KPI primitives must accept `delta` + `action`; bare-number cards fail PR review                                       |

---

## 9. Out of scope (this plan)

- Pricing page redesign
- Mobile native app
- Advanced KPI builder (custom formulas) — current scope is selection from
  catalog only
- Whitelabel / multi-brand landing
- Internationalization (PT-BR only for now)

---

## 10. Decisions (resolved from review 2026-04-27)

1. **Scrape lives in an edge function** calling `vizu_landing_intel`,
   triggered on the auth callback (parallel to redirect), not on form submit.
2. **LaunchPad is folded** into a Mission Control first-run coach-mark
   overlay. The `/onboarding/launch` route is deprecated.
3. **`default_dimension_rank`** ships in the same migration as
   `client_dimension_kpis` — required for the LLM-fallback path.
4. **Demo-data seed** uses a dedicated migration + a trigger on
   `clientes_vizu` insert that copies the seed snapshot per new tenant.

Decisions logged in `/memories/repo/blu-cro-revamp.md`.

## 11. Open questions (still open)

- Should the header app-grid icon become a workspace switcher, or be
  removed outright? (Default: remove until we have a real second workspace.)
- Should the Painéis sidebar group expand inline (recommended) or open as a
  flyout panel? Test with 5 children visible vs. hover-flyout.
- For pt-BR i18n lockdown, do we add an ESLint rule against hard-coded
  English strings, or rely on a one-pass audit?
