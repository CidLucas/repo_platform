# Architecture Overview — Blu

Source: `README.md`, `docs/system_reference/AGENT_SYSTEM.md`, `docs/system_reference/CODE_MAP.md`, `docs/system_reference/FEATURE_MAP.md`, `docs/llm_wiki/01_plataforma.md`.

---

## High-level runtime flow

```text
apps/blu_v3 (React)
   │  chat / room context
   ▼
agent_api  (FastAPI + LangGraph)
   │  builds & caches graphs via UnifiedAgentFactory / builder
   │  runs L4 frontdesk → routes to L3 specialists
   ▼
tool_pool_api  (MCP tool server)
   │  tools: execute_sql, RAG, Google, Monday, Notion, Slack, RFQ, OCR …
   ▼
Supabase/PostgreSQL (+pgvector)  +  Redis (state checkpointing, context cache)
```

Supporting pieces:
- `blu_agent_framework` builds LangGraph graphs (nodes, edges, tools, Redis checkpointer, orchestrator, approval flow, skill factory).
- `blu_prompt_management` loads prompts from **Langfuse first**, with builtin fallback in `templates.py`.
- `blu_context_service` provides a Redis-cached client context loader for every agent turn.
- `blu_tool_registry` enforces **tier-based tool access** via `ResourceResolver` (intersection of agent tools × active feature tools).

---

## Services

| Service | Responsibility | Key paths |
|---|---|---|
| `services/agent_api` | Agent orchestration, chat, routine dispatch receiver | `src/agent_api/core/routines.py`, `routine_functions.py`, `routine_artifacts.py`, `factory.py`, `service.py` |
| `services/tool_pool_api` | MCP tool server | `src/tool_pool_api/server/tool_modules/` (sql, context, google, monday, notion, slack, rfq, pm, rag, …) and `api/` routers |
| `services/routine_engine` | Routine execution engine (companion to agent_api) | see [routines](routines.md) |

> Frontend rooms live in `apps/blu_v3/src/pages/app/` (FinanceiroRoom, ClientesRoom, ComprasRoom, AgendaRoom, EstrategiaRoom, BibliotecaRoom, AdminScreen, AgentOpsRoom).

---

## Shared libraries (`libs/`)

Canonical libs (resolved by services via `../../libs/<name>` in `pyproject.toml`):

| Lib | Responsibility |
|---|---|
| `blu_agent_framework` | LangGraph: graphs, builder, skill_factory, Redis checkpointer, registry, orchestrator, approval flow |
| `blu_auth` | JWT auth + MCP middleware |
| `blu_context_service` | Redis-cached client context loader |
| `blu_tool_registry` | Tool catalog + tier/feature access (ResourceResolver) |
| `blu_prompt_management` | Langfuse-first prompt loader w/ builtin fallback |
| `blu_llm_service` | Multi-provider LLM client factory |
| `blu_rag_factory` | Hybrid RAG pipeline (embedding, indexing, pgvector search) |
| `blu_sql_factory` | Text-to-SQL with safety controls (allowlist, schema snapshot, validator) |
| `blu_db_connector` / `blu_supabase_client` | DB client + Supabase wrapper (`get_pooler_engine()`, `get_direct_engine()`) |
| `blu_models` | Shared Pydantic models |
| `blu_parsers` | Document parsers (NF-e, etc.) |
| `blu_observability_bootstrap` | OTEL + Langfuse setup |
| `blu_hitl_service` | Human-in-the-loop queues (Redis sorted sets) |
| misc | `blu_google_suite_client`, `blu_twilio_client`, `blu_data_connectors`, `blu_elicitation_service`, `blu_shared_utils` |

> **Caveat:** This checkout did not expose the `libs/` directory on disk, but services reference it via relative path and `tool_pool_api/pyproject.toml` pins `blu-agent-framework = {path = "../../libs/blu_agent_framework"}`. Treat the table above as the canonical layout from the reference docs; verify on your machine before editing.

---

## Tiers & Features

Tiers (cumulative): `FREE → BASIC → SME → PREMIUM → ENTERPRISE → ADMIN`.

Features mediate **Tier → Resources (agents + skills → tools)**. The `ResourceResolver` computes the intersection: `tools(agent) ∩ tools(active feature)`. Features are cumulative (PREMIUM includes everything in SME).

Representative feature → tier mapping (from `FEATURE_MAP.md`):

| Feature | Min tier |
|---|---|
| chat_basico, diagnostico | FREE |
| rag, onboarding, monitoramento_web | BASIC |
| sql_analytics, platform_ops, synthesis, compras_basico, financeiro, agenda_basico, ocr_extraction, notion, monday, whatsapp | SME |
| compras_avancado, crm_avancado, google_integrations, estrategia, slack, asana_linear | PREMIUM |
| fiscal, docker_mcp | ENTERPRISE |

> **Security note (P0):** per `TOOL_INVENTORY.md`, when a tool has no registry metadata (`meta=None`), the tier filter passes through (`is_accessible_by_tier` returns `True`). A BASIC client could invoke a PREMIUM tool by knowing its slug. Remediation: register all tools or deny when `meta=None`.

---

## Agent → graph construction

`factory.py` (agent_api) builds LangGraph graphs on three paths:
1. **frontdesk** — orchestrator path.
2. **standalone agent** — a single L3 specialist session.
3. **routine worker** — a routine execution (skill/function steps).

Tools are loaded from the MCP Tool Pool and tier enforcement is applied at graph build time.

---

## Observability

- **Langfuse** for traces/prompts (per-invocation handler sets `trace_id`/`session_id`/`user_id`).
- **OpenTelemetry** bootstrapped per service via `blu_observability_bootstrap`.

See `docs/observability/README.md` for the operational view.

---

## Next

- Routine execution internals → [routines](routines.md)
- Agent catalog & routing → [agents/catalog](agents/catalog.md)
- How tiers gate tools → [integrations/auth](integrations/auth.md)
