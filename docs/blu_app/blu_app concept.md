## 1. Blu — Product Philosophy & Design Vision

## Blu — Part 1: Product Philosophy

The Core Idea

Blu is an escritório virtual com IA — a bureau of AI agents that works for Brazilian business owners. Not a dashboard. Not a tool. A team.
The owner is the protagonist. The agents are the help. The interface is the space where they meet.
What We Believe
The owner already knows. They don't need to be told what to do. They need visibility — to see what they already suspect, to confirm what they already feel, to catch what almost slipped.
Decisions are the job. Everything else is preparation. The interface must surface decisions, not data. Data exists to make the decision obvious.
Approval is trust. Every action that touches money, people, or customers waits for the owner's say. This isn't friction. It's the product's core feature.
The team learns. Each approval, each edit, each rejection — the agents remember. The bureau becomes more yours the longer you use it.
Growth is calm. The owner works hard and knows their value. Blu helps them go further without panic, without overwhelm, without Sunday-night anxiety.
What Blu Is Not (Never)
Not an ERP. Not a replacement for Bling, Omie, Tiny.
Not a dashboard product. Numbers support decisions; they don't dominate the screen.
Not an autopilot. The owner decides. Always.
Not magic. AI is competent, trained staff — not sorcery.
The Promise
Your business runs more smoothly than you could make it run alone — and you stay in charge.

## 2. App Architecture

### 2.1 The Bureau Metaphor

The app is a **bureau of agents**. Each agent has a **room** (desk). The user moves between rooms. The **lobby** (home) is where urgent matters from all rooms collect.

HOME (Command Center)
├─ Decidir Agora [main]
│ └─ Cross-agent items = Mission cards
├─ Plano de Hoje
├─ Visão da Semana
├─ Insights
└─ Números (expandable)

LEFT NAV / HAMBURGER
├─ 🏠 Home
├─ 🤖 Compras (room)
├─ 📊 Financeiro (room)
├─ 📅 Agenda (room)
├─ ✍️ Documentos (room)
├─ 🎯 Estratégia (room)
├─ 👥 Clientes (room)
├─ 🔔 Atividade (stream view) ← from Strategy C
├─ 📚 Biblioteca
└─ ⚙️ Admin

INSIDE ANY AGENT ROOM
├─ Urgent (decisions needed)
├─ Active (running, upcoming)
├─ History (searchable archive)
├─ Config (behavior settings)
└─ [+ New Mission using this agent]

ADMIN
├─ Integrações
├─ Usuários
├─ Faturamento
├─ Auditoria
└─ LGPD
Mobile: Hamburger for agent rooms. Home is default. Bottom bar: Home | Atividade | +New | Perfil.
Desktop: Persistent left sidebar. Home center. Click agent → room opens in center. "Voltar ao início" always visible.

### 2.2 The Desk Pattern (Universal Room Structure)

Every agent room follows the **same physical metaphor** — a desk. This creates predictability. The user always knows where to look.
┌─────────────────────────────────────────┐
│ 🤖 [AGENT NAME] — [personalized greeting]│
│ │
│ ┌─────────────────────────────────────┐│
│ │ DESK SURFACE ││
│ │ (what the agent is working on now) ││
│ │ — decisions, active tasks, quick view│
│ └─────────────────────────────────────┘│
│ │
│ ┌─────────────────┐ ┌─────────────────┐│
│ │ LEFT DRAWER │ │ RIGHT DRAWER ││
│ │ (resources) │ │ (history) ││
│ └─────────────────┘ └─────────────────┘│
│ │
│ ┌─────────────────────────────────────┐│
│ │ CORKBOARD ││
│ │ (insights & suggestions) ││
│ └─────────────────────────────────────┘│
│ │
│ ┌─────────────────────────────────────┐│
│ │ UNDER DESK ││
│ │ (routines & configuration) ││
│ └─────────────────────────────────────┘│
│ │
│ [💬 Conversar] [📊 Ver dados] [⚙️ Configurar] [Voltar]│
└─────────────────────────────────────────┘
plain
Copy

### 2.3 Responsive Behavior

| Viewport               | Layout                 | Behavior                                                                                                       |
| ---------------------- | ---------------------- | -------------------------------------------------------------------------------------------------------------- |
| **Mobile (portrait)**  | Single column, stacked | All sections vertical. Drawers become bottom sheets. Desk surface full width.                                  |
| **Mobile (landscape)** | Two-column             | Left drawer + desk surface side by side, OR desk surface + right drawer. User toggles which drawer is visible. |
| **Tablet / Desktop**   | Three-column           | Left drawer (1/4) + Desk surface (2/4) + Right drawer (1/4). Corkboard below desk surface.                     |
| **Large desktop**      | Three-column + sidebar | Same as tablet, with optional persistent agent nav on far left.                                                |

**Critical rule:** The desk surface is always the **anchor**. Drawers flank it. On small screens, drawers become **pills** or **bottom sheets** that the user pulls up.

---

## 3. The Lobby (Home / Command Center)

### 3.1 Purpose

The lobby is where the user **starts their day**. It surfaces only what needs their attention right now. It is not a dashboard to browse. It is a **decision inbox**.

### 3.2 Layout

**Mobile (portrait):**
┌─────────────────────────────────────────┐
│ Blu — Bom dia, Carlos. │
│ │
│ ⚡ DECIDIR AGORA │
│ ├─ Decision card 1 │
│ ├─ Decision card 2 │
│ └─ Decision card 3 │
│ │
│ 📋 PLANO DE HOJE │
│ ├─ 08:00 Revisar cotações │
│ ├─ 10:00 Aprovar NF-e │
│ └─ 14:00 Follow-up clientes │
│ │
│ 🔮 VISÃO DA SEMANA │
│ ├─ Ter: 2 decisões pendentes │
│ ├─ Qua: Fechamento mensal │
│ └─ Qui: Análise de margem │
│ │
│ 💡 INSIGHTS │
│ ├─ Cliente Central +40% este mês │
│ └─ 2 fornecedores com prazo crescendo │
│ │
│ 📊 NÚMEROS [▶] │
│ (collapsed, tap to expand) │
│ │
│ [🤖] [📊] [📅] [✍️] [🎯] [📦] │
│ Compr Finan Agenda Docs Estrat Estoq │
└─────────────────────────────────────────┘
plain
Copy

**Desktop / Tablet:**
┌─────────────────────────────────────────────────────────────┐
│ Blu — Bom dia, Carlos. │
│ │
│ ┌─────────────────────────────────────┐ ┌─────────────────┐│
│ │ ⚡ DECIDIR AGORA │ │ 📋 PLANO DE ││
│ │ │ │ HOJE ││
│ │ ┌─────────────────────────────┐ │ │ ││
│ │ │ 🤖 Compras — 3 cotações │ │ │ 08:00 Revisar ││
│ │ │ pendentes │ │ │ 10:00 Aprovar ││
│ │ │ [Aprovar] [Ver] [Depois] │ │ │ 14:00 Follow ││
│ │ └─────────────────────────────┘ │ │ ││
│ │ │ │ [Ver agenda →] ││
│ │ ┌─────────────────────────────┐ │ ├─────────────────┤│
│ │ │ 📊 Financeiro — Boleto │ │ │ 🔮 VISÃO DA ││
│ │ │ vence amanhã │ │ │ SEMANA ││
│ │ │ [Aprovar] [Agendar] │ │ │ ││
│ │ └─────────────────────────────┘ │ │ Ter: 2 pendentes││
│ │ │ │ Qua: Fechamento││
│ │ ┌─────────────────────────────┐ │ │ Qui: Análise ││
│ │ │ 📦 Estoque — Café: 2 dias │ │ │ ││
│ │ │ [Cotar agora] [Depois] │ │ │ [Expandir →] ││
│ │ └─────────────────────────────┘ │ └─────────────────┘│
│ │ │ │
│ │ [Ver todas as 8 decisões →] │ │
│ └─────────────────────────────────────┘ │
│ │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 💡 INSIGHTS │ │
│ │ ├─ Cliente Central +40% este mês │ │
│ │ └─ 2 fornecedores com prazo crescendo │ │
│ │ [Ver todos os 12 →] │ │
│ └─────────────────────────────────────────────────────┘ │
│ │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 📊 NÚMEROS [▶] │ │
│ │ (collapsed — tap to expand full analytics) │ │
│ └─────────────────────────────────────────────────────┘ │
│ │
│ [🤖] [📊] [📅] [✍️] [🎯] [📦] [👥] [🔧] │
│ Compr Finan Agenda Docs Estrat Estoq Client Admin │
└─────────────────────────────────────────────────────────────┘
plain
Copy

### 3.3 Sections

| Section             | Content                                    | Max Items                  | Behavior                                                       |
| ------------------- | ------------------------------------------ | -------------------------- | -------------------------------------------------------------- |
| **Decidir Agora**   | Stacked decision cards from all agents     | 5 visible, scroll for more | Always top. Never empty (shows "Nada urgente" state if clear). |
| **Plano de Hoje**   | Time-ordered events and expected decisions | 5 items                    | Collapsible on mobile.                                         |
| **Visão da Semana** | 5-day preview with decision counts         | 5 days                     | Expandable to full week.                                       |
| **Insights**        | Non-urgent intelligence from all agents    | 3 visible                  | Expandable. Dismissible per insight.                           |
| **Números**         | Collapsed analytics summary                | 1 line when collapsed      | Expands to full analytics panel.                               |

### 3.4 Decision Card (Home)

┌─────────────────────────────────────────┐
│ 🤖 Agente de Compras — 10:32 │
│ │
│ "3 cotações prontas. Melhor opção: │
│ Fornecedor Silva, entrega 2 dias, │
│ R$ 1.240." │
│ │
│ • Toner HP 107A — urgente │
│ • Papel A4 — estoque 5 dias │
│ • Café — estoque 2 dias │
│ │
│ [👍 Aprovar] [👁️ Ver] [⏰ Depois] │
│ │
│ ───────────────────────────────────── │
│ 💡 "Silva é 15% mais caro, mas notas │
│ indicam melhor qualidade." │
│ [Ver notas] │
└─────────────────────────────────────────┘
plain
Copy

---

## 4. Agent Rooms (The Desk Pattern)

### 4.1 Universal Desk Structure

Every agent room has the **same five zones**:

| Zone             | Purpose                             | Collapsible?            | Mobile Behavior    |
| ---------------- | ----------------------------------- | ----------------------- | ------------------ |
| **Desk Surface** | Current work needing attention      | No                      | Full width, top    |
| **Left Drawer**  | Resources, databases, lists         | Yes                     | Bottom sheet       |
| **Right Drawer** | History, archive, documents         | Yes                     | Bottom sheet       |
| **Corkboard**    | Insights, suggestions, intelligence | Yes                     | Below desk surface |
| **Under Desk**   | Routines, configuration, settings   | Yes (default collapsed) | Bottom of screen   |

### 4.2 Responsive Drawer Behavior

**Mobile Portrait:**

- Drawers are **pills** at bottom of screen
- Tap pill → drawer slides up as bottom sheet
- Only one drawer visible at a time
- User toggles between Left/Right via pills
  ┌─────────────────────────────────────────┐
  │ 🤖 COMPRAS │
  │ │
  │ ┌─────────────────────────────────────┐│
  │ │ DESK SURFACE ││
  │ │ (full width, scrollable) ││
  │ └─────────────────────────────────────┘│
  │ │
  │ ┌─────────────────────────────────────┐│
  │ │ CORKBOARD ││
  │ │ (scrollable, below surface) ││
  │ └─────────────────────────────────────┘│
  │ │
  │ [📁 Fornecedores] [📜 Histórico] │
  │ (pills — tap to expand) │
  │ │
  │ [⚙️ Rotinas] │
  │ (pill — tap to expand) │
  └─────────────────────────────────────────┘
  plain
  Copy

**Mobile Landscape / Tablet / Desktop:**

- Drawers flank the desk surface
- Left drawer (1/4) + Desk surface (2/4) + Right drawer (1/4)
- Corkboard below desk surface, full width
- Under desk at bottom, collapsible
  ┌─────────────────────────────────────────────────────────────┐
  │ 🤖 COMPRAS │
  │ │
  │ ┌─────────────────┐ ┌─────────────────────┐ ┌─────────────┐│
  │ │ LEFT DRAWER │ │ DESK SURFACE │ │ RIGHT DRAWER││
  │ │ (1/4 width) │ │ (2/4 width) │ │ (1/4 width) ││
  │ │ │ │ │ │ ││
  │ │ Fornecedores │ │ Cotações ativas │ │ Histórico ││
  │ │ Categorias │ │ Decisões pendentes │ │ Últimas ││
  │ │ │ │ │ │ compras ││
  │ │ │ │ │ │ ││
  │ └─────────────────┘ └─────────────────────┘ └─────────────┘│
  │ │
  │ ┌─────────────────────────────────────────────────────┐ │
  │ │ CORKBOARD │ │
  │ │ (full width, below desk) │ │
  │ └─────────────────────────────────────────────────────┘ │
  │ │
  │ ┌─────────────────────────────────────────────────────┐ │
  │ │ UNDER DESK [▶] │ │
  │ │ (collapsed by default, expandable) │ │
  │ └─────────────────────────────────────────────────────┘ │
  │ │
  └─────────────────────────────────────────────────────────────┘
  plain
  Copy

---

## 5. Specific Agent Rooms

### 5.1 🤖 Compras (Procurement)

**Desk Surface:**

- Active quotations (cotações)
- Pending approvals
- Urgent stock alerts

**Left Drawer — Fornecedores:**

- Supplier list with ratings (★★★★☆)
- Categories: [Escritório] [Insumos] [Limpeza]
- Performance metrics per supplier

**Right Drawer — Histórico:**

- Last 10 purchases
- Approval history
- Spending by category

**Corkboard Insights:**

- "Mais fornecedores de hortaliças?"
- "Silva é 15% mais caro, mas melhor qualidade"
- "Max: tomates com 40% reclamação. Criar política?"

**Under Desk — Rotinas:**

- Check stock every Monday 8h
- Monthly supply quotation
- Low stock auto-alert threshold

---

### 5.2 📊 Financeiro (Financial)

**Desk Surface:**

- Today's balance
- Pending payments (bills, invoices)
- Upcoming due dates

**Left Drawer — Contas:**

- Connected accounts (bank, digital)
- Account balances
- Transaction sources

**Right Drawer — Relatórios:**

- Last generated reports
- DRE, cash flow, margin analysis
- Documents for accountant

**Corkboard Insights:**

- "Internet subiu 15% nos últimos 3 meses"
- "Sua base de clientes cresceu e receita está em tendência positiva"

**Analytics Card (expandable):**
┌─────────────────────────────────────────┐
│ 📈 ANALYTICS [▶] │
│ (collapsed — one line summary) │
│ "Faturamento: R
543,8mil⋅Despesas:││R

312K · Margem: 42%" │
└─────────────────────────────────────────┘
plain
Copy

**Expanded Analytics:**

- KPI grid: Revenue, Active Tasks, AI Tasks Today
- Area cards: Pedidos, Clientes, Fornecedores, Produtos
- Charts: revenue trend, expense breakdown, cash flow
- Period selector: [7 dias] [30 dias] [90 dias] [1 ano]
- Activity feed: recent agent actions

**Under Desk — Rotinas:**

- Monthly closing automation
- Cost variation alert (>10%)
- DRE monthly auto-generation

---

### 5.3 📅 Agenda (Scheduler)

**Desk Surface:**

- Today's schedule
- Pending meeting approvals
- Routine check-ins

**Left Drawer — Calendários:**

- Connected calendars
- Routine templates
- Team availability

**Right Drawer — Eventos:**

- Past events
- Decision history per meeting
- Follow-up tracking

**Corkboard Insights:**

- "Você tem uma semana cheia. Postergar team building de quinta?"
- "Reunião de fornecedores: 3 itens pendentes de cotação"

**Under Desk — Rotinas:**

- Weekly planning every Monday
- Daily stand-up reminders
- Monthly review scheduling

---

### 5.4 ✍️ Documentos (Documents)

**Desk Surface:**

- Active draft (if editing)
- Recent documents
- Pending approvals

**Left Drawer — Modelos:**

- Templates: Handover, Delivery, Proposal, Meeting Minutes
- Searchable list
- [+ New template]

**Right Drawer — Arquivados:**

- Version history
- Past documents by category
- Shared documents

**Corkboard Insights:**

- "Handover e Delivery são 80% similares. Unificar?"
- "3 propostas este mês, 100% aprovação"

**Editor Canvas (when editing):**

- Full-width writing area
- Toolbar: [Modelo] [IA escrever] [Revisar] [Salvar] [Exportar]
- Citation tooltips for sources

**Under Desk — Rotinas:**

- Auto-save every 30 seconds
- Weekly backup to cloud
- Approval workflow rules

---

### 5.5 🎯 Estratégia (Strategy)

**Desk Surface:**

- Current analysis in progress
- Pending scenario reviews
- Anomaly alerts

**Left Drawer — Métricas:**

- Monitored KPIs
- Benchmarks
- Goals and targets

**Right Drawer — Análises:**

- Past analyses
- Predictions and forecasts
- Decision outcomes

**Corkboard Insights:**

- "Margem Produto Y acima da média do setor"
- "2 fornecedores com prazo de entrega crescendo"

**Under Desk — Rotinas:**

- Monthly margin analysis
- Quarterly trend report
- Competitor price monitoring

---

## 6. The Approval System

### 6.1 Universal Approval Card

Every proposal follows this structure:
┌─────────────────────────────────────────┐
│ 🔔 [AGENT NAME] PROPÕE │
│ │
│ "[Proposal with business context]" │
│ │
│ • Supporting data point 1 │
│ • Supporting data point 2 │
│ • Supporting data point 3 │
│ │
│ [👍 Aprovar] [✏️ Editar] [👎 Rejeitar] │
│ │
│ [💡 Me explique melhor] [⏰ Depois] │
│ │
│ ───────────────────────────────────── │
│ 💡 Insight relacionado: "Silva é 15% │
│ mais caro, mas notas indicam │
│ melhor qualidade." │
│ [Ver notas] │
└─────────────────────────────────────────┘
plain
Copy

### 6.2 Decision Feedback

| Action       | Agent Response                                                             |
| ------------ | -------------------------------------------------------------------------- |
| **Aprovar**  | "Blu anotou. Vou sugerir abordagens similares quando relevante."           |
| **Editar**   | "Blu aprendeu sua preferência. Da próxima, proponho mais próximo disso."   |
| **Rejeitar** | "Blu anotou. Não vou sugerir este tipo de ação novamente sem novos dados." |
| **Depois**   | "Lembrete agendado. Voltarei a isso [tempo escolhido]."                    |

### 6.3 Progressive Trust

| Approvals | Unlock                                                   |
| --------- | -------------------------------------------------------- |
| 0-10      | All manual review                                        |
| 10-25     | "Auto-approve similar" toggle for specific routine types |
| 25-50     | "Approval rules" — e.g., "Auto-approve under R$ 500"     |
| 50+       | Full auto-approval configuration with guardrails         |

**Never auto-approve:**

- Transactions > R$ 10,000
- New supplier/customer creation
- Contract modifications
- Payroll changes
- Any anomaly flagged by Analyst (3+ standard deviations)

---

## 7. Notifications & Alerts

### 7.1 Red Dot System

| Location              | Meaning                     | Behavior                                       |
| --------------------- | --------------------------- | ---------------------------------------------- |
| **Agent icon in nav** | Agent has pending proposals | Pulsing red dot with count                     |
| **Notification bell** | Cross-agent urgent alerts   | Red dot with total count                       |
| **Decision card**     | Urgency level               | Red left border = critical, yellow = attention |

### 7.2 Notification Types

| Type         | Trigger                                      | Channel                 |
| ------------ | -------------------------------------------- | ----------------------- |
| **Urgent**   | Critical stock, payment due, contract expiry | In-app + push + email   |
| **Decision** | Agent proposal ready                         | In-app + push           |
| **Insight**  | Pattern detected, suggestion available       | In-app (corkboard)      |
| **Routine**  | Scheduled task completed                     | In-app (activity feed)  |
| **Alert**    | Anomaly, threshold crossed                   | In-app + optional email |

### 7.3 Notification Card

┌─────────────────────────────────────────┐
│ 🔴 URGENTE — Agente de Compras │
│ │
│ "Estoque de café: 1 dia restante. │
│ Última compra: 15 dias atrás. │
│ Risco de ruptura." │
│ │
│ [Cotar agora] [Ver estoque] [Ignorar] │
│ │
│ 10:32 — Há 2 minutos │
└─────────────────────────────────────────┘
plain
Copy

---

## 8. Empty States

### 8.1 Empty Desk

┌─────────────────────────────────────────┐
│ 🤖 COMPRAS │
│ │
│ ┌─────────────────────────────────────┐ │
│ │ │ │
│ │ 🟢 Nada urgente agora. │ │
│ │ │ │
│ │ Seu time está trabalhando. │ │
│ │ Quando houver algo para decidir, │ │
│ │ aparece aqui. │ │
│ │ │ │
│ │ [Ver histórico →] │ │
│ │ │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
plain
Copy

### 8.2 Empty Drawer

┌─────────────────────────────────────────┐
│ 📁 Fornecedores │
│ │
│ Nenhum fornecedor cadastrado ainda. │
│ │
│ Adicione seu primeiro fornecedor para │
│ começar a cotar. │
│ │
│ [Adicionar primeiro fornecedor →] │
└─────────────────────────────────────────┘
plain
Copy

### 8.3 First Use Onboarding

┌─────────────────────────────────────────┐
│ 🤖 COMPRAS │
│ │
│ ┌─────────────────────────────────────┐ │
│ │ 👋 Primeira vez aqui? │ │
│ │ │ │
│ │ Conecte sua planilha de estoque │ │
│ │ ou envie uma lista de compras. │ │
│ │ │ │
│ │ Seu Agente de Compras começará │ │
│ │ a trabalhar em segundos. │ │
│ │ │ │
│ │ [Conectar planilha] [Enviar lista] │ │
│ │ [Ver exemplo] │ │
│ │ │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
plain
Copy

---

## 9. Admin (Back Office)

### 9.1 Structure

Tabbed layout, not desk pattern:

- **Integrações** — Connect Bling, Omie, Tiny, Calendar, Bank
- **Usuários** — Team members, roles, permissions
- **Faturamento** — Plan, usage, upgrade
- **Auditoria** — Decision log, who approved what when
- **LGPD** — Data privacy, export, deletion

### 9.2 Integration Card

┌─────────────────────────────────────────┐
│ 🔗 Bling │
│ │
│ Status: ✅ Conectado │
│ Última sincronização: 10:32 │
│ NF-e lidas: 47 este mês │
│ │
│ [Sincronizar agora] [Configurar] │
│ [Desconectar] │
└─────────────────────────────────────────┘
plain
Copy

---

## 10. Design Tokens (Foundation)

### 10.1 Typography

| Token        | Usage                  | Size         |
| ------------ | ---------------------- | ------------ |
| `heading-xl` | Room titles            | 24px         |
| `heading-lg` | Section headers        | 20px         |
| `heading-md` | Card titles            | 16px         |
| `body`       | Descriptions, insights | 14px         |
| `body-sm`    | Metadata, timestamps   | 12px         |
| `mono`       | Numbers, codes         | 14px tabular |

### 10.2 Color

| Token            | Hex     | Usage                                    |
| ---------------- | ------- | ---------------------------------------- |
| `urgent`         | #EF4444 | Critical alerts, red dots, reject button |
| `attention`      | #F59E0B | Warnings, soon-due, snooze               |
| `ok`             | #10B981 | Approved, on-track, positive trend       |
| `insight`        | #3B82F6 | Suggestions, information, links          |
| `surface`        | #1F2937 | Card backgrounds                         |
| `drawer`         | #111827 | Drawer backgrounds (slightly darker)     |
| `text-primary`   | #F9FAFB | Headings, primary text                   |
| `text-secondary` | #9CA3AF | Metadata, secondary text                 |
| `border`         | #374151 | Dividers, card borders                   |

### 10.3 Spacing

| Token      | Value | Usage                      |
| ---------- | ----- | -------------------------- |
| `space-xs` | 4px   | Tight gaps, icon padding   |
| `space-sm` | 8px   | Inner card padding         |
| `space-md` | 16px  | Card gaps, section spacing |
| `space-lg` | 24px  | Major section breaks       |
| `space-xl` | 32px  | Page-level padding         |

### 10.4 Elevation

| Token           | Shadow                      | Usage           |
| --------------- | --------------------------- | --------------- |
| `shadow-card`   | 0 1px 3px rgba(0,0,0,0.3)   | Cards           |
| `shadow-drawer` | 0 4px 6px rgba(0,0,0,0.4)   | Drawers, modals |
| `shadow-modal`  | 0 10px 15px rgba(0,0,0,0.5) | Overlays        |

### 10.5 Radius

| Token       | Value | Usage           |
| ----------- | ----- | --------------- |
| `radius-sm` | 4px   | Buttons, pills  |
| `radius-md` | 8px   | Cards, inputs   |
| `radius-lg` | 12px  | Modals, drawers |

---

## 11. Component Inventory Summary

### Layout & Shell (7)

- `AppShell` — Root layout
- `NavBar` — Top bar
- `AgentNav` — Left sidebar / hamburger
- `RoomContainer` — Main content wrapper
- `HomeLayout` — 2/3 + 1/3 grid
- `MobileStack` — Vertical stack
- `DesktopGrid` — Three-column grid

### Navigation & Wayfinding (7)

- `AgentBadge` — Icon + name + status
- `BackToLobby` — Return button
- `Breadcrumb` — Deep navigation
- `QuickActions` — Floating actions
- `NotificationBell` — Badge + dropdown
- `GlobalSearch` — Search input
- `NotificationDropdown` — Alert list panel

### Desk Surface (10)

- `DeskSurface` — Main work card
- `DecisionCard` — Urgent decision
- `ApprovalCard` — Full proposal
- `StatusPill` — Count/urgency badge
- `MetricCard` — Big number + trend
- `MiniList` — Vertical item list
- `ActionBar` — Button row
- `AlertBanner` — Full-width urgent
- `RedDot` — Pulsing indicator
- `EmptyDesk` — Clear state

### Drawers (8)

- `LeftDrawer` — Resources panel
- `RightDrawer` — History panel
- `DrawerHeader` — Title + toggle
- `ResourceList` — Scrollable resources
- `HistoryList` — Time-ordered history
- `CategoryTags` — Horizontal pills
- `DocumentPreview` — Doc thumbnail
- `EmptyDrawer` — Empty state

### Corkboard (4)

- `Corkboard` — Insight container
- `InsightCard` — Suggestion card
- `InsightSeverity` — Color coding
- `InsightAction` — Action buttons

### Analytics (8)

- `AnalyticsCard` — Expandable container
- `AnalyticsHeader` — Title + controls
- `KpiGrid` — Big number row
- `AreaCards` — Icon + metric cards
- `ChartContainer` — Tabbed charts
- `PeriodSelector` — Time pills
- `InsightBanner` — Contextual insight
- `ActivityFeed` — Recent actions

### Under Desk (5)

- `UnderDesk` — Collapsible bottom
- `RoutineList` — Active routines
- `RoutineItem` — Single routine
- `ConfigPanel` — Settings form
- `RuleBuilder` — Visual rules

### Interaction Patterns (7)

- `SwipeableCard` — Mobile swipe
- `ExpandableSection` — Toggle
- `ChatOverlay` — Slide-up chat
- `ApprovalModal` — Full-screen decision
- `SnoozePicker` — Time selector
- `Tooltip` — Hover info
- `Popover` — Click menu

### Documents Room (6)

- `EditorCanvas` — Writing area
- `DocToolbar` — Editor toolbar
- `ModelDrawer` — Templates
- `ArchiveDrawer` — History
- `DiffViewer` — Comparison
- `CitationTooltip` — Source hover

### Admin & System (7)

- `AdminLayout` — Tabbed layout
- `IntegrationCard` — Provider status
- `UserTable` — Team members
- `PermissionToggle` — Access matrix
- `AuditLog` — Decision history
- `BillingCard` — Plan & usage
- `DataPrivacyPanel` — LGPD controls

### Home / Command Center (6)

- `DecidirAgora` — Main decision inbox
- `PlanoDeHoje` — Today's plan
- `VisaoSemana` — Week preview
- `InsightsPanel` — Intelligence
- `NumbersPanel` — Collapsed analytics
- `AgentStatusRow` — Agent health strip

### Feedback & States (5)

- `LoadingAgent` — Animated loading
- `SuccessToast` — Post-action feedback
- `ErrorHuman` — Friendly error
- `SkeletonCard` — Loading placeholder
- `EmptyState` — Generic empty

### Foundation / Primitives (12)

- `Button` — Primary, secondary, ghost, danger
- `IconButton` — Icon-only
- `Badge` — Status, count
- `Card` — Base container
- `Input` — Text input
- `Select` — Dropdown
- `Toggle` — On/off switch
- `TabGroup` — Horizontal tabs
- `Avatar` — User/agent image
- `Divider` — Separator
- `Spinner` — Loading indicator

**Total: 82 components**

---

## 12. File Structure

blu_app/
├── src/
│ ├── components/
│ │ ├── layout/
│ │ │ ├── AppShell.tsx
│ │ │ ├── NavBar.tsx
│ │ │ ├── AgentNav.tsx
│ │ │ ├── RoomContainer.tsx
│ │ │ ├── HomeLayout.tsx
│ │ │ ├── MobileStack.tsx
│ │ │ ├── DesktopGrid.tsx
│ │ │ └── ModalOverlay.tsx
│ │ ├── navigation/
│ │ │ ├── AgentBadge.tsx
│ │ │ ├── BackToLobby.tsx
│ │ │ ├── Breadcrumb.tsx
│ │ │ ├── QuickActions.tsx
│ │ │ ├── NotificationBell.tsx
│ │ │ ├── GlobalSearch.tsx
│ │ │ └── NotificationDropdown.tsx
│ │ ├── desk/
│ │ │ ├── DeskSurface.tsx
│ │ │ ├── DecisionCard.tsx
│ │ │ ├── ApprovalCard.tsx
│ │ │ ├── StatusPill.tsx
│ │ │ ├── MetricCard.tsx
│ │ │ ├── MiniList.tsx
│ │ │ ├── ActionBar.tsx
│ │ │ ├── AlertBanner.tsx
│ │ │ ├── RedDot.tsx
│ │ │ └── EmptyDesk.tsx
│ │ ├── drawers/
│ │ │ ├── LeftDrawer.tsx
│ │ │ ├── RightDrawer.tsx
│ │ │ ├── DrawerHeader.tsx
│ │ │ ├── ResourceList.tsx
│ │ │ ├── HistoryList.tsx
│ │ │ ├── CategoryTags.tsx
│ │ │ ├── DocumentPreview.tsx
│ │ │ └── EmptyDrawer.tsx
│ │ ├── corkboard/
│ │ │ ├── Corkboard.tsx
│ │ │ ├── InsightCard.tsx
│ │ │ ├── InsightSeverity.tsx
│ │ │ └── InsightAction.tsx
│ │ ├── analytics/
│ │ │ ├── AnalyticsCard.tsx
│ │ │ ├── AnalyticsHeader.tsx
│ │ │ ├── KpiGrid.tsx
│ │ │ ├── AreaCards.tsx
│ │ │ ├── ChartContainer.tsx
│ │ │ ├── PeriodSelector.tsx
│ │ │ ├── InsightBanner.tsx
│ │ │ └── ActivityFeed.tsx
│ │ ├── underdesk/
│ │ │ ├── UnderDesk.tsx
│ │ │ ├── RoutineList.tsx
│ │ │ ├── RoutineItem.tsx
│ │ │ ├── ConfigPanel.tsx
│ │ │ └── RuleBuilder.tsx
│ │ ├── interactions/
│ │ │ ├── SwipeableCard.tsx
│ │ │ ├── ExpandableSection.tsx
│ │ │ ├── ChatOverlay.tsx
│ │ │ ├── ApprovalModal.tsx
│ │ │ ├── SnoozePicker.tsx
│ │ │ ├── Tooltip.tsx
│ │ │ └── Popover.tsx
│ │ ├── documents/
│ │ │ ├── EditorCanvas.tsx
│ │ │ ├── DocToolbar.tsx
│ │ │ ├── ModelDrawer.tsx
│ │ │ ├── ArchiveDrawer.tsx
│ │ │ ├── DiffViewer.tsx
│ │ │ └── CitationTooltip.tsx
│ │ ├── admin/
│ │ │ ├── AdminLayout.tsx
│ │ │ ├── IntegrationCard.tsx
│ │ │ ├── UserTable.tsx
│ │ │ ├── PermissionToggle.tsx
│ │ │ ├── AuditLog.tsx
│ │ │ ├── BillingCard.tsx
│ │ │ └── DataPrivacyPanel.tsx
│ │ ├── home/
│ │ │ ├── DecidirAgora.tsx
│ │ │ ├── PlanoDeHoje.tsx
│ │ │ ├── VisaoSemana.tsx
│ │ │ ├── InsightsPanel.tsx
│ │ │ ├── NumbersPanel.tsx
│ │ │ └── AgentStatusRow.tsx
│ │ ├── feedback/
│ │ │ ├── LoadingAgent.tsx
│ │ │ ├── SuccessToast.tsx
│ │ │ ├── ErrorHuman.tsx
│ │ │ ├── SkeletonCard.tsx
│ │ │ └── EmptyState.tsx
│ │ └── primitives/
│ │ ├── Button.tsx
│ │ ├── IconButton.tsx
│ │ ├── Badge.tsx
│ │ ├── Card.tsx
│ │ ├── Input.tsx
│ │ ├── Select.tsx
│ │ ├── Toggle.tsx
│ │ ├── TabGroup.tsx
│ │ ├── Avatar.tsx
│ │ ├── Divider.tsx
│ │ └── Spinner.tsx
│ ├── hooks/
│ │ ├── useAgent.ts
│ │ ├── useApproval.ts
│ │ ├── useAnalytics.ts
│ │ ├── useDrawer.ts
│ │ ├── useNotification.ts
│ │ ├── useChat.ts
│ │ └── useAuth.ts
│ ├── utils/
│ │ ├── formatters.ts
│ │ ├── constants.ts
│ │ └── helpers.ts
│ ├── types/
│ │ ├── agent.ts
│ │ ├── approval.ts
│ │ ├── analytics.ts
│ │ ├── user.ts
│ │ └── notification.ts
│ ├── styles/
│ │ ├── globals.css
│ │ ├── tokens.css
│ │ └── animations.css
│ ├── api/
│ │ ├── client.ts
│ │ ├── agents.ts
│ │ ├── approvals.ts
│ │ ├── analytics.ts
│ │ └── auth.ts
│ ├── contexts/
│ │ ├── AgentContext.tsx
│ │ ├── ApprovalContext.tsx
│ │ ├── AuthContext.tsx
│ │ └── NotificationContext.tsx
│ └── pages/
│ ├── HomePage.tsx
│ ├── ComprasRoom.tsx
│ ├── FinanceiroRoom.tsx
│ ├── AgendaRoom.tsx
│ ├── DocumentosRoom.tsx
│ ├── EstrategiaRoom.tsx
│ ├── ClientesRoom.tsx
│ └── AdminPage.tsx
├── public/
│ ├── manifest.json
│ └── robots.txt
└── tests/
├── setup.ts
└── example.test.ts
