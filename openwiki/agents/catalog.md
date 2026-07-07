# Agents Catalog

Blu has **12 canonical agents** across the L4/L3 layers. This is the authoritative catalog (source: `docs/system_reference/AGENT_SYSTEM.md`, `docs/llm_wiki/02_agentes.md`). Ghost agents previously listed (`synthesis`, `supplier-agent`, `scheduler-agent`, `documentos`, `estrategia`) were **removed** — they do not exist in the registry.

---

## L4 — Orchestrator

### `frontdesk`
Single entry point for all user interaction. Answers simple queries directly (RAG, basic SQL); routes complex/domain tasks to the correct specialist via `route_to_specialist`. **Never does deep analysis** — if it needs >1–2 simple queries, route.
- Skills: `data_access`, `sql_analytics`
- Extra tool: `route_to_specialist`
- Model: FAST · Max turns: 10 · Memory: session

---

## L3 — Domain Specialists

### `data-entry` — Write Gateway
**The only agent authorized to write operational transactions.** Receives NL (sale, client/supplier registration, expense, event), does structured parsing, persists via `register_transaction`. Any other agent that receives a write request **must redirect to `data-entry`** — never write itself.
- Skills: `ledger`, `data_access`, `csv_analytics`, `sql_analytics`
- Model: DEFAULT · Max turns: 6 · Memory: session

### `platform` — Platform Configuration
Converts NL into operational config: create routines, define goals, manage automations. Triggered by imperatives ("cria uma rotina", "define uma meta").
- Skills: `platform_ops`, `data_access`
- Model: DEFAULT · Max turns: 6

### `financeiro` — Financial Health (read-only)
Cash flow, revenue trends, expense patterns, anomalies, structured reports w/ charts. Used by monitor routines.
- Skills: `data_access`, `sql_analytics`, `analytics_charts`, `csv_analytics`
- Model: POWERFUL · Max turns: 5

### `compras` — Procurement & Suppliers
Full buying cycle: supplier catalog, buying-list pipeline (parse → validate → optimize → PO), RFQ dispatch via WhatsApp/email, reply parsing, PO creation, supplier risk.
- Skills: `data_access`, `sql_analytics`, `communication`
- Model: DEFAULT · Max turns: 6

### `crm` — Customer Relationships
LTV, churn risk, NPS, segmentation, reactivation. Drafts personalized WhatsApp/email. Used by collection/follow-up/satisfaction routines.
- Skills: `data_access`, `sql_analytics`, `analytics_charts`, `communication`
- Model: POWERFUL · Max turns: 8

### `agenda` — Calendar & Agenda
Scheduling, availability, conflict detection, Monday.com boards/items, meeting briefs, agenda digests. (Google Calendar = PREMIUM; Google Docs/Sheets/Gmail = `doc-writer`.)
- Skills: `data_access`, `sql_analytics`, `monday`, `calendar`, `meeting_brief`
- Model: DEFAULT · Max turns: 5

### `data-analyst` — Quantitative Analysis
Deep quantitative analysis: trends, correlations, scenario modeling across financial/purchasing/customer data. Exports to Google Docs/Sheets. Activated for analytical questions without a single domain.
- Skills: `data_access`, `sql_analytics`, `analytics_charts`, `csv_analytics`, `document_io`
- Model: POWERFUL · Max turns: 6

### `strategy` — Cross-Domain Strategy
Cross-domain analysis (finance × compras × clientes × agenda). KPI patterns, growth opportunities, competitive positioning. Produces morning/EOD digests.
- Topology: `fanout` (collects from finance + CRM + market in parallel, then reduces).
- Skills: `data_access`, `sql_analytics`, `analytics_charts`, `strategy_ops`
- Model: POWERFUL · Max turns: 8

### `doc-writer` — Document Creation
Strategic documents: KB search, draft structured docs (briefs, SOPs, proposals, reports), export to Google Docs/Sheets, persist approved content to KB.
- Skills: `data_access`, `knowledge_base_write`, `document_io`, `document_curation`, `notion`
- Model: POWERFUL · Max turns: 8

### `fiscal-agent` — Invoicing (ENTERPRISE stub)
NF-e/NFS-e emission, fiscal validation, SEFAZ status. Candidate to merge into `financeiro` post-MVP.
- Skills: `fiscal`, `data_access`, `sql_analytics`
- Model: DEFAULT · Max turns: 4

### `context-gatherer` — Context Collection (background, not visible)
Background agent. Maps client data sources to platform schema, processes ingested docs (OCR, extraction, summarization), persists structured context to KB. Runs on schedule + webhooks (`onboarding_complete`, `doc_ingested`). **Never a chat option; never writes transactions.**
- Skills: `data_access`, `sql_analytics`, `knowledge_base_write`, `onboarding`, `document_curation`
- Model: DEFAULT · Max turns: 8 · Memory: none (stateless per trigger)

---

## Routing rules (Frontdesk)

| User intent | Route to |
|---|---|
| Register sale / purchase / expense / event | `data-entry` |
| Financial report, cash flow | `financeiro` |
| Suppliers, RFQ, PO | `compras` |
| Clients, churn, reactivation, CRM | `crm` |
| Agenda, meetings, Monday.com | `agenda` |
| Written doc, SOP, proposal | `doc-writer` |
| Deep quantitative analysis (no single domain) | `data-analyst` |
| Strategy, business overview, 2+ domains | `strategy` |
| Create routine / define goal / config | `platform` |
| NF-e / NFS-e / fiscal | `fiscal-agent` |
| Simple KB/SQL query | Resolve directly (no route) |

---

## Agent × Skills matrix

```text
                       data_access  sql_analytics  analytics_charts  communication  ledger  knowledge_base_write  document_io
frontdesk                  ✓             ✓
data-entry                 ✓             ✓                                              ✓
platform                   ✓
financeiro                 ✓             ✓               ✓
compras                    ✓             ✓                                  ✓
crm                        ✓             ✓               ✓                  ✓
agenda                     ✓             ✓
data-analyst               ✓             ✓               ✓                                                             ✓
strategy                   ✓             ✓               ✓
doc-writer                 ✓                                                                        ✓                   ✓
context-gatherer           ✓             ✓                                                          ✓
fiscal-agent               ✓             ✓
```

(Domain and routine skills omitted for clarity — see [skills](skills.md).)

---

## Handoff via shared memory

Agents do **not** talk directly. When `frontdesk` routes via `route_to_specialist`, a `handoff_hook` (in `blu_agent_framework/handoff/handoff_hook.py`) optionally writes learning notes to shared memory (`source="specialist"`, `confidence=0.8`) and records `agent_result`. The destination specialist loads enriched context via `shared_memory_context.py`. Hook timeout 2s → graceful degradation.

Affected: `frontdesk` triggers; all L3 receive context; `data-entry` is not a handoff *recipient*.

---

## Open decisions

- **Memory Agent** — post-conversation lightweight skill writing to `shared_business_memory`; L2 skill or L3 specialist? (Blu Intelligent Memory PRD).
- **`fiscal-agent`** — merge into `financeiro` post-MVP.
- **`compras_ops` sub-skills** — split into `supplier_mgmt` + `procurement_pipeline` + `rfq_ops` planned (D9) but not executed.
- **Supplier-agent** — appears in FEATURE_MAP but not in registry; remove or create.

---

## Next

- Skill definitions → [skills](skills.md)
- How frontdesk routes in code → [architecture/overview](architecture/overview.md)
- Routine skills invoked by engine → [routines](architecture/routines.md)
