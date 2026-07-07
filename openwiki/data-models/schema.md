# Data Models & Schema

Blu persists all business memory in **Supabase/PostgreSQL** (schemas `public`, `analytics_v2`, `polp_*`) with **pgvector** for RAG and **Redis** for agent state checkpointing + context cache. No Alembic — migrations in `supabase/migrations/` applied via `psql -f`.

Source: `docs/llm_wiki/07_dados_modelos.md`, `docs/system_reference/CODE_MAP.md`, `docs/system_reference/ROUTINES_SYSTEM.md`.

---

## Core tables (`public`)

| Table | Role |
|---|---|
| `clientes_blu` | Tenant identity + ops. Core fields: `company_profile` (jsonb), `brand_voice`, `team_structure`, `policies`, `data_schema`, `available_tools`, `onboarding_state`, `onboarding_completed_at`, `api_key`, `tier`, `external_user_id`. Also `active_clientes_blu` view. |
| `integration_tokens` | Provider tokens (encrypted). `provider`, `token`, `client_id` FK. |
| `integration_configs` | Per-client OAuth config (encrypted `client_id`/`client_secret`, scopes, redirect URI). |
| `client_knowledge_documents` | Documents indexed for RAG (`source`, `status` pending/active, `embedding`). |
| `approval_requests` | HITL gates. |
| `client_insights` | Insights with `severity` warning/critical. Field `room`. |
| `notifications` | Urgent alerts. |
| `client_goals` | Active goals. |
| `client_approval_stats` | Approval history → drives `trust_level` auto/manual. |
| `app_config` | Platform config (e.g. `agent_api_routine_dispatch_token`). |

---

## Routines tables

| Table | Role |
|---|---|
| `cross_agent_routines` | Catalog. PK = `id` (slug). `name`, `steps` (jsonb), `trigger_type`, `trigger_config`, `config_schema` (jsonb), `room`, `visibility`. |
| `client_routines` | Per-client subscription. `client_id` FK, `routine_id` FK (or UUID custom), `active`, `status` (active/suspended), `trigger_config`, `config` (jsonb overrides), `notify_channel`, `last_run_at`, `consecutive_failures`, `steps` (custom), `source` (catalog/ai), `created_by_ai`. |
| `client_routine_executions` | Execution log. `status`, `triggered_by` (NOT NULL), `trigger_data`, `dispatched_at`, `heartbeat_at`, `result_text`, `result_metadata` (checkpoint jsonb), `completed_at`, `worker_slug`, `failure_count`. |
| `artifact_delivery_claims` | Delivery dedupe. |
| `dimension_state` | Structured analysis per dimension (`financeiro`, `clientes`, …). `summary` (text), `structured` (jsonb), `valid_until`, `updated_at`. One row per dimension per client. |

Full routine schema → [routines](architecture/routines.md).

---

## Analytics (`analytics_v2`)

| Table | Notes |
|---|---|
| `fato_transacoes` | Fact table. PK `transacao_id`+`client_id`. |
| `dim_inventory` | Column `nome`. |
| `dim_clientes` | Customer dimension. |
| `dim_fornecedores` | Supplier dimension. |
| `client_insights` | Has `room` column. |
| `reg_jobs` | Regression/ETL jobs. |

Canonical `entry_type`: `revenue | purchase | expense | banking`.
`client_insights.room` slugs: `financeiro | clientes | compras | agenda | estrategia | home`.

---

## Polp / Open Finance (`polp_*`)

`polp_integrations`, `polp_accounts`, `polp_transactions`, `polp_bills`. Connected via `polp-connect` / `polp-webhook` / `polp-sync` edge functions.

---

## Shared memory & context

Agents are stateless — memory lives in the DB + Redis:

- **Immediate per-turn context** (budget ~6,000 chars) injected into the agent: pending `approval_requests` + urgent `notifications` + active `client_goals` + `dimension_state` for the room + `client_insights` severity warning/critical.
- **Persistent profile**: Redis cache (TTL 5 min) of `clientes_blu` fields, injected into agent system prompts.
- **Shared memory tools** (`shared_memory_*` in `memory_module.py`): `list`, `link`, `unlink`, `write` (`auto_link=True`), `get_links`; plus internal `shared_memory_post_flight` (persists `agent_result`/`agent_metadata`/`agent_link_pending` after an agent run, not exposed via MCP).

---

## Plano 2 (future schema split)

Separate `company_context` from `clientes_blu`:
- `clientes_blu` → identity + ops metadata (`tier`, `external_user_id`, `onboarding_state`, `onboarding_completed_at`, `api_key`).
- `company_context` (new) → `company_profile`, `brand_voice`, `team_structure`, `policies`, `data_schema`, `available_tools`.
- `ContextService` reads `company_context` first, with fallback to `clientes_blu` during transition.
- Enables different RLS/permissions: `brand_voice` editable by agents; ops more restricted.

---

## Migrations

- 82 migrations in `supabase/migrations/`.
- No Alembic. Apply with `psql -f <file>.sql`.
- Adding a column/table that routines or agents read → update `data_schema` in `clientes_blu` and any `column_mapping` logic.

Full recipe → [Dev Playbooks: migration](workflows/dev-playbooks.md#6-create-a-schema-migration).

---

## Next

- How routines write `dimension_state`/`client_insights` → [routines](architecture/routines.md)
- How context is loaded per turn → [architecture/overview](architecture/overview.md)
- HITL `approval_requests` → [workflows/hitl](workflows/hitl.md)
