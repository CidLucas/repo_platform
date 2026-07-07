# Product & UX

Blu is a **virtual AI office for Brazilian SME owners** — not a dashboard, not a chatbot. It's a team of agents working in the background. Source: `docs/system_reference/PRODUCT_CONCEPT.md`, `docs/llm_wiki/08_produto_ux.md`, `docs/llm_wiki/01_plataforma.md`.

---

## Philosophy

- **The owner already knows** — they need visibility to confirm what they suspect, not teaching.
- **Decisions are the job**; everything else is preparation. The UI surfaces *decisions*, not data.
- **Routines are the real product**, not chat. Value happens while the owner sleeps.
- **Routines do two things at once:** organize the owner (daily plan, alerts, reports) *and* create context for agents (`dimension_state`, `client_insights`) so the LLM already knows business state when action is needed.
- **Approval is enforcement, not suggestion** — architectural HITL gates. See [workflows/hitl](workflows/hitl.md).
- **High-quality AI, low config** — automatic onboarding: reads the client's site, parses invoices, builds the data schema.

---

## Rooms (frontend, `apps/blu_v3`)

| Room | Route | Owner agent | Purpose |
|---|---|---|---|
| Home | `/app` | `strategy` | Daily cockpit: plan, urgent alerts, pending approvals |
| Clientes | `/app/clientes` | `crm` | CRM, collection, follow-up, reactivation, NPS |
| Compras | `/app/compras` | `compras` | Suppliers, RFQ, buying list, PO |
| Financeiro | `/app/financeiro` | `financeiro` | Cash, reconciliation, anomaly alerts, reports |
| Agenda | `/app/agenda` | `agenda` | Calendar, briefs, Monday.com |
| Estratégia | `/app/estrategia` | `strategy` + `data-analyst` | Hidden patterns, competitive, cross-domain synthesis |
| Biblioteca | `/app/biblioteca` | `doc-writer` + `context-gatherer` | Knowledge base + document creation |
| AgentOpsRoom | `/app/agent-ops` | — | Internal Blu admin monitoring (not shown to end users) |

**Agents without a room** (infrastructure, background): `frontdesk` (global router), `data-entry` (write gateway), `platform` (routines/goals), `fiscal-agent` (called by others), `context-gatherer` (onboarding/curation).

**UI principles:** no hard-coded data — skeleton loaders while fetching; sidebar icons with hover tooltips; active routines shown in a bottom strip in each room's Config; Home shows only urgent/relevant items, depth lives in specific rooms.

---

## Chat — contextualized Frontdesk

There is **no separate chat per agent**. One Frontdesk understands the room context the user is in:
- In Financeiro → routes to `financeiro`.
- In Home → routes to `strategy` or answers directly if simple.
- Frontdesk never does deep analysis; if it needs >1–2 queries, it routes to the specialist.

Room context is injected into the Frontdesk prompt — the user never explains where they are or what they want there.

---

## Biblioteca (5 tabs)

1. **Ativos** — finalized, approved documents (view/edit/reuse).
2. **Rascunhos** — in-progress docs from `doc-writer` chat, awaiting approval to promote to Ativos.
3. **Modelos** — templates (proposals, SOPs, reports, canned responses).
4. **Base** — client vector KB. Documents indexed (PDFs, NF-e, contracts, CSVs) feed `executar_rag_cliente`. Upload via UI or chat; `context-gatherer` handles ingestion/curation.
5. **Config** — routine toggles, cron picker, `config_schema`.

**Document creation flow:**
1. User chats with `doc-writer`.
2. Agent searches KB, drafts, shows **inline preview**.
3. User edits in preview.
4. **Mandatory approval node** before persisting.
5. Destination: **Google Drive** (Google Doc) or **Base vetorial** (indexed for RAG).

---

## HITL (decision enforcement)

Operations requiring approval: register transactions, send messages, create/modify docs, create PO. States: `pending → approved` (+audit_log) | `edited` | `rejected` (+feedback) | `snooze` (reappears in Xh). Progressive trust via `client_approval_stats` (`trust_level=auto` lets agents skip HITL in user-defined low-risk contexts). See [workflows/hitl](workflows/hitl.md).

---

## Next

- Room ↔ agent mapping → [agents/catalog](agents/catalog.md)
- Routines that populate Home/rooms → [routines](architecture/routines.md)
- Onboarding that provisions the tenant → [onboarding](workflows/onboarding.md)
