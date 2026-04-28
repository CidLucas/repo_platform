# Schema Baseline Plan — 2026-04-28

## Context

132 legacy migrations were squashed into a clean baseline. The production Supabase project had only the original `20241209` migration applied; all subsequent migrations had never been pushed due to a project hard reset.

Old migrations archived to `supabase/migrations/archived/`. New baseline consists of 8 files under `supabase/migrations/`.

---

## Migration Files

| File | Purpose |
|---|---|
| `20260428000000_cleanup_legacy_analytics.sql` | Drops all `analytics_gold_*` and `analytics_silver` legacy tables |
| `20260428141000_phase1_public_core_tables.sql` | Core tenant, credential, integration, audit, and event tables |
| `20260428141001_phase1_agent_conversation_tables.sql` | `conversa` and `mensagem` tables for agent chat history |
| `20260428142000_phase1_public_additional_tables.sql` | Business, reporting, agent catalog, and session tables |
| `20260428143000_phase2_analytics_v2_tables.sql` | analytics_v2 star schema (fact + dimensions + job registry) |
| `20260428144000_phase3_vector_db_tables.sql` | vector_db schema for RAG (documents + chunks with HNSW) |
| `20260428145000_phase4_bigquery_fdw_tables.sql` | BigQuery FDW server and table registry |
| `20260428146000_phase5_core_functions.sql` | All RPCs: tenant resolution, onboarding, KPI, audit, RAG search |
| `20260428147000_phase6_rls_policies.sql` | RLS enabled on all tables; tenant isolation via `get_my_client_id()` |
| `20260428148000_phase7_storage_buckets.sql` | `knowledge-base` and `file-uploads` storage buckets with RLS |
| `20260428149000_post_baseline_messaging_cleanup.sql` | Drop consumer_contacts, consumer_messages, twilio_inbound_routes, mensagem, purchase_orders, rfq_requests; create unified messages table |

---

## Schema Decisions

### clientes_blu (tenant anchor)

**Kept:**
- `client_id`, `external_user_id`, `api_key`
- `nome_empresa`, `tier`, `collection_rag`
- `company_profile`, `team_structure`, `policies` (Context 2.0 JSONB blobs)
- `onboarding_state`, `onboarding_completed_at`

**Removed:**
- `tipo_cliente` — was a free-text field with no downstream enforcement; tier system covers this
- `prompt_base` — prompts live in the agent catalog and edge function code, not in the DB
- `horario_funcionamento` — operational detail that belongs in `company_profile` if needed
- `current_moment` — ephemeral; never belonged in persistent storage

### connector_sync_history → merged into analytics_v2.reg_jobs

`reg_jobs` is the central async job registry. It was extended with:
- `credential_id`, `resource_type`, `sync_mode` (incremental/full)
- `rows_inserted`, `progress_pct`, `error_message`, `duration_seconds`
- `job_type` CHECK includes `'connector_sync'`

This eliminates a duplicate table and gives a unified job history across BQ syncs, connector syncs, and analytics ETL.

### supplier_roster — removed

Supplier operational data lives in `analytics_v2.dim_fornecedores`, populated via BigQuery FDW. A separate `supplier_roster` table would duplicate that data. RFQ/PO flows reference supplier IDs directly (`BIGINT` on `rfq_requests.supplier_ids`).

### calendar_settings — kept

Required by the `google-calendar-events` edge function which reads `calendar_id`, `enabled`, `range_days`, and `timezone` per client. Removing it would break agent calendar tooling.

### purchase_orders and rfq_requests — removed

Procurement operations produce audit log entries when they happen; if they materialize as a completed transaction (nota fiscal), they enter via `analytics_v2.fato_transacoes`. There is no value in a separate staging table — agent workflows operate statelessly and outcome data belongs in the fact layer.

### consumer_contacts — removed

Contact data lives in `analytics_v2.dim_clientes`, populated from the client's operational data via BigQuery FDW. A separate `consumer_contacts` table would duplicate that data and require its own sync.

### twilio_inbound_routes — removed

Route config belongs in application config or agent catalog metadata, not in the database. The agent slug mapping doesn't need tenant isolation semantics or a relational table.

### consumer_messages + mensagem → merged into messages

Both tables stored messages but for different channels. `consumer_messages` (Twilio/WhatsApp) and `mensagem` (agent chat) are now unified as `public.messages`:
- `channel` column: `chat | whatsapp | sms | email | api`
- `direction`: `inbound | outbound` (null for system/agent messages)
- `role`: `user | assistant | system | tool` (for agent chat threads)
- `provider`: vendor name (`twilio`, `sendgrid`, etc.)
- `sender_ref`: external identifier (phone number, email, dim_clientes ref)
- `session_id` → `conversa.id`: links agent chat messages to a conversation thread

`conversa` is kept as the thread/session container for agent conversations.

### agent_catalog and client_enabled_agents — kept as-is

`agent_catalog` is a global catalog (read-only for authenticated users). `client_enabled_agents` is the per-tenant enablement join table. Access gating (tier-based) is enforced at the RPC/edge function layer, not via additional DB columns — the `tier_required` field on `agent_catalog` is the source of truth read by the API.

### kpi_catalog and client_dimension_kpis — kept

`kpi_catalog` is the master KPI definition table (global read-only). `client_dimension_kpis` stores which KPIs a client has enabled per dimension. The `list_kpi_catalog()` RPC merges both.

---

## Schemas

### public — tenant operations
Core multi-tenant data: clients, integrations, agents, sessions, files, messages, approvals, events.

### analytics_v2 — star schema
- `fato_transacoes` — transaction fact table, populated from BigQuery FDW
- `dim_clientes`, `dim_fornecedores`, `dim_inventory` — dimension tables
- `dim_datas` — date dimension (static)
- `reg_jobs` — unified async job registry

### vector_db — RAG storage
- `documents` — file metadata and processing status
- `document_chunks` — chunked content with `halfvec(384)` embeddings (HNSW index) and Portuguese FTS

---

## Key Functions (phase5)

| Function | Role |
|---|---|
| `get_my_client_id()` | Resolves JWT `uid` → `client_id`; used in all RLS policies |
| `ensure_tenant_row()` | Idempotent first-login provisioning |
| `set_current_cliente_id(uuid)` | Sets `app.current_client_id` config for service-role callers |
| `merge_onboarding_state(jsonb)` | Race-free JSONB patch merge into `clientes_blu.onboarding_state` |
| `onboarding_bootstrap_tx(jsonb)` | Atomic tenant provisioning: updates profile, enables agents + routines |
| `list_kpi_catalog(dimension, only_enabled)` | Returns catalog joined with client enablement |
| `set_client_dimension_kpis(dimension, slugs[])` | Replaces KPI selection for a dimension |
| `record_audit(action, ...)` | Writes to `audit_log` with current client/user context |
| `request_approval(action_type, payload)` | Creates approval request |
| `decide_approval(id, decision)` | Resolves pending approval |
| `dismiss_insight(id)` | Marks insight as dismissed |
| `hybrid_match_documents(...)` | Semantic + FTS hybrid search over `vector_db.document_chunks` |
| `get_platform_google_oauth_config()` | Reads `google_oauth_config` from Vault |

---

## RLS Pattern

All tenant-scoped tables use one of two patterns:

```sql
-- Pattern A: direct client_id match (UUID)
USING (client_id = public.get_my_client_id())

-- Pattern B: via join (mensagem has no client_id)
USING (EXISTS (
  SELECT 1 FROM public.conversa c
  WHERE c.id = mensagem.conversa_id
  AND c.client_id = public.get_my_client_id()
))
```

`clientes_blu` itself uses `external_user_id = auth.uid()::text` (users only see their own row).

Global catalog tables (`agent_catalog`, `kpi_catalog`) are SELECT-only for all authenticated users.

---

## match-columns Edge Function

The `match-columns` edge function does fuzzy column mapping using `string-similarity`. It does **not** write to the DB — it returns match results for the caller to store in `client_data_sources.column_mapping`.

Canonical schema types it knows: `invoices`, `fato_transacoes`, `dim_clientes`, `dim_inventory`, `dim_categoria` (legacy alias), plus legacy aliases `vendas → fato_transacoes`, `customers → dim_clientes`.

`dim_categoria` is a legacy schema type that still exists in the function but the table was dropped. Safe to leave; it only affects fuzzy matching output.

---

## Storage Buckets

| Bucket | Public | Size limit | MIME filter |
|---|---|---|---|
| `knowledge-base` | No | 50 MB | PDF, TXT, MD, DOCX, PPTX |
| `file-uploads` | No | 50 MB | None |

Both buckets use folder-based client isolation: `/{client_id}/...` enforced by RLS on `storage.objects`.

---

## Extensions Required

| Extension | Schema | Purpose |
|---|---|---|
| `vector` | `extensions` | `halfvec(384)` type + HNSW index for RAG |
| `pgcrypto` | `extensions` | UUID generation |
| `pg_net` | `extensions` | Async HTTP from DB |
| `pg_cron` | `pg_catalog` | Scheduled sync workers |
| `wrappers` | `extensions` | BigQuery FDW |
| `supabase_vault` | `vault` | Encrypted secret storage |
| `uuid-ossp` | `extensions` | Legacy UUID functions |
| `pg_stat_statements` | `extensions` | Query analytics |
