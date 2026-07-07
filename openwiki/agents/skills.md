# Skills System

A **skill** is an ephemeral, focused sub-agent activated by a specialist to perform one specific task. Each skill has:
- its own **Langfuse prompt** (`skill:{name}:system`, label `production`),
- a **whitelist of tools** (only what the task needs),
- a **turn budget** (`max_turns`) to prevent infinite loops,
- a **failure policy** (`on_max_turns`): `return_partial` for read tasks; `raise` for transactional tasks.

> **Golden rule:** Skill ≠ Agent. A skill executes *one task*; an agent has *one identity*. If the skill's scope == the whole agent's scope, that logic belongs in the agent's Langfuse config, not as a skill.

Source: `docs/system_reference/SKILLS_SYSTEM.md`, `docs/llm_wiki/03_skills.md`.

---

## Transverse skills (used by many agents)

| Skill | What it does | Tools | max_turns | on_max_turns |
|---|---|---|---|---|
| `data_access` | Unified read: KB semantic search + data catalog | `executar_rag_cliente`, `query_data_catalog` | 4 | return_partial |
| `sql_analytics` | SQL over structured business data (always `scope=read`) | `execute_sql` (direct\|agent) | 5 | return_partial |
| `analytics_charts` | Self-contained Chart.js HTML (bar/line/pie/doughnut/scatter) | `generate_chart_html` | 3 | return_partial |
| `csv_analytics` | Inspect CSV columns before import/analysis | `peek_csv_columns` | 2 | return_partial |
| `communication` | Draft + send WhatsApp/email; parse replies | `send_whatsapp_message`, `send_email`, `parse_business_reply` | 4 | raise |
| `document_io` | Create/read/edit Google Docs & Sheets | `google_docs_*`, `write_to_sheet`, `export_to_sheet` | 5 | raise |
| `ledger` | **Transactional write — `data-entry` only** | `register_transaction`, `execute_sql` | 3 | raise |
| `knowledge_base_write` | Persist content to client KB | `write_summary_to_kb`, `update_context_document` | 3 | raise |

---

## Domain skills

| Skill | Primary agent | What it does |
|---|---|---|
| `platform_ops` | `platform` | Create/list routines, define goals, confirm before executing |
| `financeiro_ops` | `financeiro` | Read-only financial analysis (cash flow, revenue, expenses) |
| `compras_ops` | `compras` | Full buying pipeline (parse → validate → PO → RFQ) |
| `crm_ops` | `crm` | Read-only customer analysis (churn, LTV, NPS, segmentation) |
| `agenda_ops` | `agenda` | Scheduling context via SQL/RAG (no Google Calendar) |
| `calendar` | `agenda` | Google Calendar query/write/import (PREMIUM) |
| `monday` | `agenda` | Monday.com boards, items, status, updates |
| `meeting_brief` | `agenda` | Pre-meeting briefing with participant context (pure LLM) |
| `strategy_ops` | `strategy` | Cross-domain KPI analysis + strategic priorities |
| `document_curation` | `context-gatherer`, `doc-writer` | OCR + extraction + summarization |
| `onboarding` | `context-gatherer` | Initial mapping: config, data sources, schema |
| `notion` | `doc-writer` | Notion page/database CRUD |
| `fiscal` | `fiscal-agent` | NF-e/NFS-e emission, fiscal validation, SEFAZ status |

---

## Routine (narrative) skills — pure LLM, no tools

Invoked by the routine engine (`type="skill"`). Context is pre-injected by the engine; `required_tool_names=[]`.

`morning_plan`, `end_of_day_digest`, `weekly_summary`, `insights_synthesis`, `hidden_patterns`, `competitor_analysis`, `reconciliation_report`, `finance_monitor_report`, `clients_monitor_report`, `agenda_monitor_report`, `inventory_digest`, `followup_draft`, `collection_messages`, `reactivation_proposal`, `satisfaction_survey`.

---

## Governance rules

1. Skill ≠ Agent.
2. Single write gateway (`ledger`/`data-entry`) — no other skill writes transactions.
3. Separation: extraction (`document_curation`) vs persistence (`knowledge_base_write`).
4. HITL is **middleware**, not a skill.
5. Routine skills are pure-LLM.
6. Langfuse prompts are mandatory (production label).
7. Naming: skill = `snake_case`; prompt key = `skill:{name}:system`; agent = `kebab-case`.

---

## Adding a skill (summary)

1. Add skill file under `libs/blu_agent_framework/.../routines/` (for routine skills) or register in the skill system.
2. Add prompt to `blu_prompt_management/templates.py` with key `skill:{name}:system`, `type=skill` (fallback).
3. Create the equivalent prompt in **Langfuse** (production) — this is the source of truth in prod.
4. Document the skill in `docs/system_reference/SKILLS_SYSTEM.md`.

Full recipe → [Dev Playbooks](workflows/dev-playbooks.md).

---

## Next

- Which agent uses which skill → [agents/catalog](catalog.md)
- Tool whitelist audit → [operations/backlog](operations/backlog.md)
- Routine skills in the engine → [routines](architecture/routines.md)
