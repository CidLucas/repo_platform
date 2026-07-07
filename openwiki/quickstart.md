# Blu Mono — OpenWiki Quickstart

This wiki is a navigable, grounded documentation set for the **repo_platform (Blu)** monorepo. It was bootstrapped from the existing `docs/system_reference/` and `docs/llm_wiki/` knowledge bases, and cross-checked against the actual repository layout (`services/`, `supabase/`, `apps/`).

> **Primary existing sources** (still authoritative, linked from here):
> - `docs/system_reference/` — agent system, skills, routines, tool inventory, code map, onboarding, integrations.
> - `docs/llm_wiki/` — a knowledge-graph style index (00_INDEX → 09_backlog) in PT-BR.
> - `README.md` — repo overview and tech stack.
>
> This wiki consolidates those into a stable, English-first structure. Where the two sources disagree (e.g. tool counts), both are noted.

---

## What is Blu?

Blu is a **multi-tenant AI "virtual office" for Brazilian SME owners** — not a dashboard, not a chatbot. A team of specialized AI agents works in the background to deliver business intelligence with minimal configuration.

**Core product beliefs:**
- The owner already knows their business; the product surfaces *decisions*, not raw data.
- **Routines are the product**, not chat. Value is created while the owner is away (agents run on schedules/triggers).
- **Approval is enforcement, not a prompt suggestion.** Any world-affecting action (register a sale, send a message, create a PO) is blocked at an architectural approval node until the user explicitly responds.
- High-quality AI, low configuration: onboarding is automatic (the system reads the client's site, fiscal notes, and builds the data schema).

**Platform focus areas:**
- Natural language → SQL with safety controls
- Hybrid RAG over tenant documents
- Agent orchestration with tool calling through MCP
- Secure tenant isolation via JWT and Supabase RLS

---

## Repository Layout

```text
apps/
  blu_v3/                 Main React frontend (dashboard + chat, "salas")
  landing/                Landing web app

services/
  agent_api/              Primary agent orchestration service (LangGraph-based)
  tool_pool_api/          MCP tool server API
  routine_engine/         Routine execution engine service

libs/                     Shared Python libraries (blu_agent_framework, blu_auth,
                          blu_tool_registry, blu_prompt_management, blu_rag_factory, …)
                          (referenced by services via ../../libs/* in pyproject)

supabase/
  migrations/             SQL migrations (no Alembic; apply via psql -f)
  functions/              Edge Functions (Deno)

docs/                     Internal documentation (system_reference, llm_wiki, plans)
tests/                    Cross-service and integration tests
```

Tech stack: Python 3.11+ / FastAPI / LangGraph (backend), React + TypeScript + Vite (frontend), Supabase/PostgreSQL + pgvector + Redis (data), Docker Compose (local) + Cloud Run (deploy), OpenTelemetry + Langfuse (observability).

---

## The 4-Layer Agent Model

Blu uses **progressive context disclosure** across four layers:

```text
L4  Orchestrator (frontdesk)   — receives user input, classifies, routes
L3  Domain Specialists         — financeiro, compras, crm, agenda, strategy, …
L2  Skills                     — ephemeral focused units (prompt + tools), stateless
L1  Tools (Tool Pool API)      — execute_sql, executar_rag_cliente, Google, OCR …
```

**Iron rules (from `AGENT_SYSTEM.md`):**
- Agents are **stateless** — all business memory lives in Supabase/Redis.
- Agents **do not talk to each other directly** — they communicate via shared memory.
- **No agent skips a layer** in the L1→L4 hierarchy.
- **Only `data-entry` writes transactions** — every other agent is read-only.

See [architecture/overview](architecture/overview.md) for the full runtime flow and tier model.

---

## Major Documentation Sections

| Section | What it covers |
|---|---|
| [Architecture](architecture/overview.md) | Services, libs, runtime flow, tiers, ResourceResolver |
| [Routines](architecture/routines.md) | Background automation pipeline, step engine, resilience, catalog |
| [Agents](agents/catalog.md) | 12 canonical agents, roles, routing rules, skill matrix |
| [Skills](agents/skills.md) | Skill concept, skill catalog, governance rules |
| [Data Models](data-models/schema.md) | Core tables, routines tables, shared memory, Plano 2 |
| [Integrations & Auth](integrations/auth.md) | Google OAuth, Monday, routine-callable integrations |
| [Onboarding](workflows/onboarding.md) | 5-step wizard, edge functions, tenant provisioning |
| [HITL](workflows/hitl.md) | Approval flow, states, progressive trust |
| [Dev Playbooks](workflows/dev-playbooks.md) | How to add a routine, skill, tool, migration, edge fn |
| [Backlog & Decisions](operations/backlog.md) | Known gaps, dead/ghost tools, decisions D1–D12, lessons |

---

## Where to start as a developer

- **Adding a background job?** → [Routines](architecture/routines.md) + [Dev Playbooks](workflows/dev-playbooks.md).
- **Adding a new capability/tool?** → [Skills](agents/skills.md) + [Tool Inventory source](../../docs/system_reference/TOOL_INVENTORY.md).
- **Understanding agent routing?** → [Agents catalog](agents/catalog.md).
- **Changing the data schema?** → [Data Models](data-models/schema.md) + migrations note.
- **Wiring an integration?** → [Integrations & Auth](integrations/auth.md).

---

## Operational budget (defaults)

- Immediate per-turn context budget: ~6,000 chars (~1,500 tokens)
- Routine execution timeout: 120s
- Routine heartbeat: 20s
- Max parallel routine executions per client: 4 (semaphore)
- Profile Redis cache TTL: 5 min

---

*Note: This wiki is a consolidation layer. For the single most current catalogs (agents, skills, tools, routines) always also check `docs/system_reference/` — those files are maintained as the system's source of truth and may be more recently updated than this wiki.*
