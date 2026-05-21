# Frontend Diagnostics — blu_v3

**Date:** 2026-05-20
**URL:** http://localhost:5175
**Method:** Full browser click inspection + source code analysis

---

## 1. Landing Page (`/`)

### Navigation Bar

| Element           | Type   | Points To                | Action                             | Status                                                       |
| ----------------- | ------ | ------------------------ | ---------------------------------- | ------------------------------------------------------------ |
| **Produto**       | Link   | `#screens`               | Anchor scroll to product section   | ⚠️ No visible scroll — section may be missing or ID mismatch |
| **Como funciona** | Link   | `#como-funciona`         | Anchor scroll                      | ⚠️ No visible scroll — section may be missing or ID mismatch |
| **Preços**        | Link   | `#precos`                | Anchor scroll to pricing section   | ✅ Works (URL changes to `/#precos`)                         |
| **Ir para o app** | Button | `/onboarding?mode=login` | Navigates to login/onboarding flow | ✅ Works                                                     |

### Hero Section

| Element                | Type   | Points To                                          | Action                         | Status |
| ---------------------- | ------ | -------------------------------------------------- | ------------------------------ | ------ |
| **Criar conta grátis** | Button | (not inspected — requires unauthenticated session) | Likely opens onboarding signup | —      |
| **Ver planos ↓**       | Button | `#precos`                                          | Scrolls to pricing section     | —      |

### Decision Card (demo widget)

| Element                | Type   | Action                             | Status             |
| ---------------------- | ------ | ---------------------------------- | ------------------ |
| **👍 Aprovar Silva**   | Button | Demo interaction — no backend call | ⚠️ Decorative only |
| **👁 Ver comparativo** | Button | Demo interaction                   | ⚠️ Decorative only |
| **⏰ Depois**          | Button | Demo interaction                   | ⚠️ Decorative only |

### Pricing Section

| Element                           | Type   | Action               | Status |
| --------------------------------- | ------ | -------------------- | ------ |
| **Começar grátis** (Starter)      | Button | Likely opens signup  | —      |
| **Começar grátis** (Pro)          | Button | Likely opens signup  | —      |
| **Falar com vendas** (Enterprise) | Button | Likely opens contact | —      |

### Footer

| Element         | Type | Points To | Status                      |
| --------------- | ---- | --------- | --------------------------- |
| **Privacidade** | Link | `#`       | ⚠️ Dead link — no real page |
| **Termos**      | Link | `#`       | ⚠️ Dead link — no real page |
| **LGPD**        | Link | `#`       | ⚠️ Dead link — no real page |

---

## 2. Onboarding / Login (`/onboarding?mode=login`)

| Element                  | Type   | Action                                                                | Status                               |
| ------------------------ | ------ | --------------------------------------------------------------------- | ------------------------------------ |
| **G Entrar com Google**  | Button | Google OAuth — if already authenticated, navigates directly to `/app` | ✅ Works                             |
| **Entrar**               | Button | Submits email/password login                                          | ⚠️ Disabled until both fields filled |
| **Email field**          | Input  | Controlled input                                                      | ✅                                   |
| **Senha field**          | Input  | Controlled input                                                      | ✅                                   |
| **Criar conta grátis →** | Link   | Switches mode to signup                                               | — (not clicked)                      |
| **Stepper (1–4)**        | Visual | Conta → Empresa → Dados → Mapeamento                                  | ✅ Visual only, non-clickable        |

---

## 3. App Shell — Header (all pages)

| Element                       | Type      | Action                                      | Status                                      |
| ----------------------------- | --------- | ------------------------------------------- | ------------------------------------------- |
| **blu logo**                  | Image     | —                                           | No click action                             |
| **☀️ / 🌙**                   | Button    | Toggles dark/light theme                    | ✅ Works — icon changes, theme applies      |
| **🔍 Search**                 | Button    | (onClick not implemented)                   | ⚠️ No visible action — no modal/input opens |
| **🔔 Bell**                   | Button    | (onClick not implemented)                   | ⚠️ No visible action — no dropdown          |
| **CI avatar**                 | Clickable | Toggles dropdown: shows email + Sair button | ✅ Works                                    |
| **Sair** (in avatar dropdown) | Button    | Logs out user                               | ✅ (not tested — would log out)             |

---

## 4. Sidebar Navigation

### Main Icons (top to bottom)

| Position | Icon         | Room                           | Route Key    |
| -------- | ------------ | ------------------------------ | ------------ |
| 1        | 🏠 House     | **HomePage**                   | `home`       |
| 2        | 🛒 Cart      | **Compras**                    | `compras`    |
| 3        | 📊 Bar chart | **Financeiro**                 | `financeiro` |
| 4        | 📅 Calendar  | **Agenda**                     | `agenda`     |
| 5        | ✏️ Pencil    | **Documentos**                 | `documentos` |
| 6        | 🎯 Target    | **Estratégia**                 | `estrategia` |
| 7        | 👥 People    | **Clientes**                   | `clientes`   |
| 8        | 📚 Books     | **Biblioteca de Conhecimento** | `biblioteca` |

### Bottom Icons

| Icon       | Room          | Notes                                 |
| ---------- | ------------- | ------------------------------------- |
| 🔔 Bell    | **Atividade** | Real-time agent activity log          |
| ⚙️ Gear    | **Admin**     | Configurations, integrations, billing |
| 🖥️ Monitor | **AgentOps**  | Sessions, sync jobs, credentials      |

All sidebar icons: ✅ Navigate correctly to their respective rooms.

---

## 5. HomePage (`/app`)

| Element                                   | Type        | Action                                                                              | Status |
| ----------------------------------------- | ----------- | ----------------------------------------------------------------------------------- | ------ |
| **⚡ Decidir Agora — Ver todas →**        | Link        | Navigates to `compras` room                                                         | ✅     |
| **Agenda →** badge (Plano de Hoje header) | Link        | Navigates to `agenda` room                                                          | ✅     |
| **📋 Plano de Hoje** header               | Collapsible | Toggles section expand/collapse                                                     | ✅     |
| **🔮 Visão da Semana** header             | Collapsible | Toggles section expand/collapse                                                     | ✅     |
| **Day rows (Qua–Dom)**                    | Clickable   | Expands day detail                                                                  | ✅     |
| **Conectar Google Calendar** (×2)         | Button      | Initiates Google Calendar OAuth flow                                                | ✅     |
| **Insight cards (📈 ⚠️ 💡)**              | Clickable   | Opens popover with 3 action prompts: "Explique", "Como agir?", "Analisar tendência" | ✅     |
| **📊 Números chip**                       | Clickable   | Navigates to `financeiro` room                                                      | ✅     |
| **⚙ Rotinas** card rows                   | Clickable   | Navigates to routine config in relevant room                                        | ✅     |
| **Approval card — Approve**               | Button      | `approveMut.mutate(id)` — approves decision                                         | ✅     |
| **Approval card — Reject**                | Button      | `rejectMut.mutate(id)` — rejects decision                                           | ✅     |
| **Approval card — Snooze**                | Button      | `snoozeMut.mutate(id)` — snoozes decision                                           | ✅     |
| **📹 Entrar** (calendar events)           | Link        | Opens Google Meet/Hangout URL in new tab                                            | ✅     |
| **💬 Preparar pauta**                     | Button      | Opens chat assistant with meeting context pre-filled                                | ✅     |

---

## 6. Compras Room

### Header

| Element           | Action                    | Status         |
| ----------------- | ------------------------- | -------------- |
| **← Início**      | Navigates to HomePage     | ✅             |
| **+ Nova Missão** | No action (unimplemented) | ⚠️ Placeholder |

### Mesa de Trabalho Tabs

| Tab           | Content                                                 | Status |
| ------------- | ------------------------------------------------------- | ------ |
| **Decisões**  | Pending decisions list; empty state shown               | ✅     |
| **Tarefas**   | Scheduled routine tasks with "Ver →" links              | ✅     |
| **Histórico** | Past purchases — "Nenhuma compra registrada"            | ✅     |
| **Config**    | Routine management: "Criar com IA" + "+ Manual" buttons | ✅     |

### Config Tab Buttons

| Element            | Action                         | Status |
| ------------------ | ------------------------------ | ------ |
| **+ Criar com IA** | Opens AI routine creation flow | ✅     |
| **+ Manual**       | Opens manual routine creation  | ✅     |

### Analytics Bar

| Element                     | Action                           | Status |
| --------------------------- | -------------------------------- | ------ |
| **Analytics header**        | Toggles expanded analytics panel | ✅     |
| **30d / 90d / 1 ano** pills | Filters analytics by period      | ✅     |
| **Retry link**              | Refetches supply data            | ✅     |

### Right Panel

| Element                          | Action                       | Status         |
| -------------------------------- | ---------------------------- | -------------- |
| **Todos / Escritório / Insumos** | Filter suppliers by category | ✅             |
| **＋ Fornecedores**              | No action (unimplemented)    | ⚠️ Placeholder |
| **Supplier rows**                | Clickable (detail view)      | ✅             |
| **Ver na aba Tarefas →**         | Switches to Tarefas tab      | ✅             |

---

## 7. Financeiro Room

### Header

| Element           | Action                    | Status         |
| ----------------- | ------------------------- | -------------- |
| **← Início**      | Navigates to HomePage     | ✅             |
| **+ Nova Missão** | No action (unimplemented) | ⚠️ Placeholder |

### Tabs

| Tab              | Content                                             | Status |
| ---------------- | --------------------------------------------------- | ------ |
| **Decisões**     | Pending payment approvals                           | ✅     |
| **Compromissos** | Bills with "Pagar agora" CTA — shows **12 pending** | ✅     |
| **Tarefas**      | Scheduled tasks                                     | ✅     |
| **Histórico**    | Transaction history with category dropdown          | ✅     |
| **Config**       | Routine management                                  | ✅     |

### Key Interactions

| Element                           | Action                                                           | Status            |
| --------------------------------- | ---------------------------------------------------------------- | ----------------- |
| **Pagar agora**                   | `payBillMut.mutate({bill, cardName})` — creates payment approval | ✅                |
| **Category dropdown** (Histórico) | Saves transaction category                                       | ✅                |
| **Category edit button**          | Enters edit mode for category                                    | ✅                |
| **＋ Contas**                     | No action (unimplemented)                                        | ⚠️ Placeholder    |
| **Bank account rows**             | Listed with balance, sync status                                 | ✅ (display only) |

---

## 8. Agenda Room

### Header

| Element           | Action                    | Status         |
| ----------------- | ------------------------- | -------------- |
| **← Início**      | Navigates to HomePage     | ✅             |
| **+ Novo evento** | No action (unimplemented) | ⚠️ Placeholder |

### Tabs

| Tab              | Content                    | Status |
| ---------------- | -------------------------- | ------ |
| **Visão Mensal** | Monthly calendar view      | ✅     |
| **Hoje**         | Today's events             | ✅     |
| **Pendentes**    | Pending approval decisions | ✅     |
| **Config**       | Routine management         | ✅     |

### Key Interactions

| Element                      | Action                  | Status |
| ---------------------------- | ----------------------- | ------ |
| **Conectar Google Calendar** | Initiates OAuth         | ✅     |
| **Approval — 👍 Aprovar**    | `approveMut.mutate(id)` | ✅     |
| **Approval — ⏰ Depois**     | `snoozeMut.mutate(id)`  | ✅     |

---

## 9. Documentos Room

### Header

| Element              | Action                             | Status |
| -------------------- | ---------------------------------- | ------ |
| **← Início**         | Navigates to HomePage              | ✅     |
| **+ Novo documento** | Likely opens creation — not tested | —      |

### Tabs

| Tab           | Content                                     | Status |
| ------------- | ------------------------------------------- | ------ |
| **Ativos**    | Active documents — "Nenhum documento ainda" | ✅     |
| **Rascunhos** | Draft documents                             | ✅     |
| **Modelos**   | Document templates                          | ✅     |
| **Config**    | Routine management                          | ✅     |

---

## 10. Estratégia Room

### Header

| Element            | Action                    | Status         |
| ------------------ | ------------------------- | -------------- |
| **← Início**       | Navigates to HomePage     | ✅             |
| **+ Nova Análise** | No action (unimplemented) | ⚠️ Placeholder |

### Tabs

| Tab           | Content                      | Status |
| ------------- | ---------------------------- | ------ |
| **Decisões**  | Strategic approval decisions | ✅     |
| **Análises**  | Reports/analysis selection   | ✅     |
| **Histórico** | History                      | ✅     |
| **Config**    | Routine management           | ✅     |

### Key Interactions

| Element                              | Action                                      | Status |
| ------------------------------------ | ------------------------------------------- | ------ |
| **Report row**                       | Selects report and switches to Análises tab | ✅     |
| **Analytics toggle**                 | Expands/collapses analytics panel           | ✅     |
| **👍 Aprovar / ⏰ Depois / Ignorar** | Approve/snooze/reject                       | ✅     |

---

## 11. Clientes Room

### Header

| Element            | Action                    | Status         |
| ------------------ | ------------------------- | -------------- |
| **← Início**       | Navigates to HomePage     | ✅             |
| **+ Novo contato** | No action (unimplemented) | ⚠️ Placeholder |

### Tabs

| Tab           | Content                     | Status |
| ------------- | --------------------------- | ------ |
| **Follow-up** | "Nenhum follow-up pendente" | ✅     |
| **Ativos**    | Active clients list         | ✅     |
| **Histórico** | History                     | ✅     |
| **Config**    | Links to Config tab         | ✅     |

### Right Panel

| Element                  | Content                               | Status     |
| ------------------------ | ------------------------------------- | ---------- |
| **Segmentos**            | Alto (885), Médio (1151), Baixo (178) | ✅ Display |
| **Receita por Segmento** | Alto 97%, Médio 3%, Baixo 0%          | ✅ Display |
| **Últimas Ações**        | "Nenhuma ação recente"                | ✅ Display |

### ⚠️ Console Error

**Duplicate React keys** in ClientesRoom list — 84 errors generated when navigating here. Affects list stability and can cause rendering bugs.

---

## 12. Biblioteca de Conhecimento Room

### Header

| Element                       | Action                  | Status |
| ----------------------------- | ----------------------- | ------ |
| **← Início**                  | Navigates to HomePage   | ✅     |
| **Dados de Negócio** dropdown | Selects upload category | ✅     |
| **+ Adicionar arquivo**       | Triggers file upload UI | ✅     |

### Main Panel

| Element                          | Action                       | Status |
| -------------------------------- | ---------------------------- | ------ |
| **Buscar documento** search      | Filters document list        | ✅     |
| **Todas as categorias** dropdown | Filters by category          | ✅     |
| **Todos os status** dropdown     | Filters by processing status | ✅     |
| **Grid / List view toggle**      | Switches display mode        | ✅     |
| **Document cards**               | Clickable (detail view)      | ✅     |
| **Drop zone**                    | Drag & drop file upload      | ✅     |
| **+ Escolher arquivo**           | Opens file picker            | ✅     |

### Right Panel — Stats

| Section        | Data                                                                  | Status |
| -------------- | --------------------------------------------------------------------- | ------ |
| Total arquivos | 4                                                                     | ✅     |
| Processados    | 4                                                                     | ✅     |
| Por categoria  | Dados de Negócio, Contexto da Empresa, Documentos, Conhecimento da IA | ✅     |

---

## 13. Atividade Room (Bell icon)

| Element                  | Content                                                                  | Status     |
| ------------------------ | ------------------------------------------------------------------------ | ---------- |
| **Feed de atividades**   | "Nenhuma atividade registrada"                                           | ✅ Display |
| **Agentes Ativos panel** | Compras, Financeiro, Agenda, Documentos, Estratégia — all "Nada urgente" | ✅         |
| **Resumo do Dia**        | Decisões pendentes: 0, Aprovadas hoje: 0                                 | ✅         |
| **Bottom status cards**  | OK, SISTEMA (BigQuery Sync), CONCLUÍDO badges                            | ✅ Display |

---

## 14. Admin Room (Gear icon)

### Tabs

| Tab              | Content                                     |
| ---------------- | ------------------------------------------- |
| **Integrações**  | ERPs, Google, Open Finance connection cards |
| **Usuários**     | User management + invite modal              |
| **Auditoria**    | Searchable audit log                        |
| **Notificações** | Channel and event kind toggles              |
| **Faturamento**  | Plan info + external upgrade/billing links  |
| **LGPD**         | Data export + account deletion              |
| **Contexto**     | Business context editor                     |

### Integrações Tab

| Integration         | Status                         | Buttons                                   |
| ------------------- | ------------------------------ | ----------------------------------------- |
| **Conta Azul**      | Desconectado                   | "Conectar" → opens modal (email/password) |
| **Google Calendar** | Conectado (Sync: 20/05, 03:59) | "↻ Sincronizar" + "Config"                |
| **Google Drive**    | Desconectado                   | "Conectar" → Google OAuth                 |
| **Open Finance**    | Conectado (Sync: 20/05, 02:20) | "↻ Sincronizar" + "Config"                |

### Faturamento Tab

| Element                         | Action                                      | Status                               |
| ------------------------------- | ------------------------------------------- | ------------------------------------ |
| **Fazer upgrade para Growth ↗** | Opens `https://blu.ai/planos` in new tab    | ⚠️ External URL — may be placeholder |
| **Ver faturas ↗**               | Opens `https://blu.ai/faturas` in new tab   | ⚠️ External URL — may be placeholder |
| **Gerenciar ↗**                 | Opens `https://blu.ai/pagamento` in new tab | ⚠️ External URL — may be placeholder |

### LGPD Tab

| Element                  | Action                | Status                                          |
| ------------------------ | --------------------- | ----------------------------------------------- |
| **Exportar tudo (JSON)** | `exportData.mutate()` | ✅                                              |
| **Excluir conta**        | `deleteData.mutate()` | ⚠️ Destructive — no confirmation dialog visible |

---

## 15. AgentOps Room (Monitor icon)

| Tab             | Content                           | Status |
| --------------- | --------------------------------- | ------ |
| **Sessões**     | "Nenhuma sessão registrada ainda" | ✅     |
| **Sync Jobs**   | Sync job history                  | ✅     |
| **Credenciais** | Agent credentials                 | ✅     |

---

## 16. Floating Chat Assistant Button

| Element                                                                      | Action                              | Status |
| ---------------------------------------------------------------------------- | ----------------------------------- | ------ |
| **🌊 Abrir assistente** (bottom-right FAB)                                   | Opens full-screen dark chat overlay | ✅     |
| **Chat overlay — close (✕)**                                                 | Closes the panel                    | ✅     |
| **Onboarding option buttons** ("Só eu", "Eu e um sócio", "Tenho uma equipe") | Send response to agent              | ✅     |
| **Text input**                                                               | Free-text to agent                  | ✅     |
| **➤ Send**                                                                   | Submits message                     | ✅     |

---

## Summary of Issues Found

### 🔴 Bugs / Broken

| Issue                               | Location                                 | Impact                                                                  |
| ----------------------------------- | ---------------------------------------- | ----------------------------------------------------------------------- |
| **84 duplicate React key errors**   | `ClientesRoom.tsx`                       | Can cause list rendering bugs / items duplicated or omitted             |
| **"Produto" nav link no-ops**       | Landing page (`#screens`)                | Anchor doesn't scroll — likely missing `id="screens"` on target section |
| **"Como funciona" nav link no-ops** | Landing page (`#como-funciona`)          | Same — missing target ID                                                |
| **Footer links dead**               | Landing page (Privacidade, Termos, LGPD) | All point to `#` — legal pages not implemented                          |

### 🟡 Unimplemented Placeholders

| Button              | Location                    |
| ------------------- | --------------------------- |
| **+ Nova Missão**   | Compras, Financeiro headers |
| **+ Novo evento**   | Agenda header               |
| **+ Novo contato**  | Clientes header             |
| **+ Nova Análise**  | Estratégia header           |
| **＋ Fornecedores** | Compras right panel         |
| **＋ Contas**       | Financeiro right panel      |

### 🟡 No Visible Action (possibly by design)

| Element                        | Location      |
| ------------------------------ | ------------- |
| **Search icon** (header)       | All app pages |
| **Notification bell** (header) | All app pages |

### ⚠️ UX Concerns

| Issue                                          | Location                             |
| ---------------------------------------------- | ------------------------------------ |
| **"Excluir conta" has no confirmation dialog** | Admin → LGPD tab                     |
| **blu.ai billing URLs may be placeholders**    | Admin → Faturamento tab              |
| **Onboarding stepper steps 2–4 not inspected** | `/onboarding` (requires signup flow) |
