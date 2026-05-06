# Blu App — Schema Gaps

> Cross-reference of frontend component data needs vs. existing Supabase schema (`20260430000000_baseline.sql`).
> Each gap includes the component that needs it, what's missing, and the recommended SQL.

---

## Summary

| Gap | Type | Priority | Blocks |
|-----|------|----------|--------|
| `notifications` table | New table | P0 | `NotificationBell`, `NotificationDropdown`, push system |
| `approval_requests` — missing columns | Column additions | P0 | `DecisionCard`, `SnoozePicker`, `ApprovalCard` |
| `client_enabled_agents` — missing status fields | Column additions | P0 | `AgentStatusRow`, `AgentBadge`, red dot counts |
| `client_approval_rules` table | New table | P1 | Progressive trust (Phase 6.3 of concept) |
| `client_approval_stats` table | New table | P1 | Trust level unlock indicators |
| `suppliers` table | New table | P1 | `ComprasRoom` Left Drawer |
| `client_notification_preferences` table | New table | P1 | Admin notification settings |
| `client_kpi_snapshot` table | New table | P1 | `NumbersPanel` fast load, `FinanceiroRoom` header |
| `doc_templates` table | New table | P2 | `DocumentosRoom` `ModelDrawer` |
| `vector_db.document_versions` table | New table | P2 | `DocumentosRoom` `ArchiveDrawer`, `DiffViewer` |
| `vector_db.documents` — missing columns | Column additions | P2 | `DocumentosRoom` editor, template linking |
| `conversa` — missing agent context | Column additions | P2 | `ChatOverlay` routing to correct agent context |
| `approval_requests.scheduled_for` | Column addition | P2 | `PlanoDeHoje` synthesis |

---

## Gap 1 — `notifications` (new table) — P0

**Blocks:** `NotificationBell` badge count, `NotificationDropdown` list, push/email dispatch.

**What exists:** `client_insights` covers AI-generated insight cards on the corkboard. There is no table for the notification bell system (urgent alerts, decision ready, routine completed, threshold crossed).

**What's missing:**

```sql
CREATE TABLE public.notifications (
  id            uuid      DEFAULT gen_random_uuid() NOT NULL,
  client_id     uuid      NOT NULL,
  type          text      NOT NULL,  -- 'urgent' | 'decision' | 'insight' | 'routine' | 'alert'
  title         text      NOT NULL,
  body          text,
  agent_slug    text,                -- which agent originated this
  related_entity_type text,          -- 'approval_request' | 'insight' | 'routine' | 'report_run'
  related_entity_id   uuid,
  urgency_level text      DEFAULT 'normal', -- 'critical' | 'normal' | 'low'
  channels      text[]    DEFAULT ARRAY['in_app'], -- 'in_app' | 'push' | 'email'
  read_at       timestamptz,
  dismissed_at  timestamptz,
  created_at    timestamptz DEFAULT now() NOT NULL,

  CONSTRAINT notifications_pkey PRIMARY KEY (id),
  CONSTRAINT notifications_client_id_fkey
    FOREIGN KEY (client_id) REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE
);

CREATE INDEX idx_notifications_client_unread
  ON public.notifications (client_id, read_at, created_at DESC)
  WHERE dismissed_at IS NULL;
```

**Notes:**
- `read_at = NULL` → unread (drives badge count)
- `dismissed_at = NULL` → still in dropdown list
- The `related_entity_id` links back to the original `approval_requests.id` or `client_insights.id` so the frontend can navigate directly
- Urgent notifications (`urgency_level = 'critical'`) drive the pulsing red dot on `NotificationBell`

---

## Gap 2 — `approval_requests` missing columns — P0

**Blocks:** `DecisionCard` (priority border color), `SnoozePicker` (snooze state), `ApprovalCard` (agent attribution, insight text, card title).

**What exists:** `approval_requests` has `id, client_id, requested_by, action_type, payload, status, decided_by, decided_at, expires_at, created_at`.

**What's missing:**

```sql
ALTER TABLE public.approval_requests
  ADD COLUMN IF NOT EXISTS agent_slug       text,          -- which agent created this proposal
  ADD COLUMN IF NOT EXISTS priority         text DEFAULT 'normal', -- 'urgent' | 'normal'
  ADD COLUMN IF NOT EXISTS title            text,          -- short summary for card header
  ADD COLUMN IF NOT EXISTS insight_text     text,          -- related insight shown at card bottom
  ADD COLUMN IF NOT EXISTS snooze_until     timestamptz,   -- set by SnoozePicker "Depois"
  ADD COLUMN IF NOT EXISTS snooze_count     int  DEFAULT 0,
  ADD COLUMN IF NOT EXISTS scheduled_for    timestamptz;   -- for PlanoDeHoje time-ordered list
```

**Notes:**
- `priority = 'urgent'` → red left border on `DecisionCard`. `'normal'` → yellow (attention).
- `title` avoids parsing `payload` JSONB to render the card header — keeps the component dumb.
- `insight_text` is the "💡 Silva é 15% mais caro, mas..." line shown below action buttons.
- `snooze_until` drives filtering: pending approvals with `snooze_until > now()` are hidden from `DecidirAgora` but still visible in the agent's room Desk Surface.
- `scheduled_for` is different from `expires_at` — it's when the owner expects to deal with it, used to place the item in `PlanoDeHoje`.

---

## Gap 3 — `client_enabled_agents` missing status fields — P0

**Blocks:** `AgentStatusRow` (home screen), `AgentBadge` orb animation state, nav red dot counts.

**What exists:** `client_enabled_agents` has `client_id, agent_slug, config, enabled_at`.

**What's missing:**

```sql
ALTER TABLE public.client_enabled_agents
  ADD COLUMN IF NOT EXISTS current_status   text DEFAULT 'idle', -- 'idle' | 'working' | 'attention' | 'offline'
  ADD COLUMN IF NOT EXISTS last_activity_at timestamptz,
  ADD COLUMN IF NOT EXISTS pending_count    int  DEFAULT 0;      -- cached count of pending approvals
```

**Notes:**
- `current_status` drives the orb animation: `idle → orb-idle`, `working → orb-pulse`, `attention → orb-attention`, `offline → no animation + 30% opacity`.
- `pending_count` is a denormalized cache so the nav red dots don't require a join on every render. Updated by the backend each time an `approval_request` is created/resolved.
- A trigger or edge function should keep `pending_count` in sync with `approval_requests` count per agent.

---

## Gap 4 — `client_approval_rules` (new table) — P1

**Blocks:** Progressive trust system (concept §6.3). Without this, the frontend cannot offer "auto-approve similar" toggles or "approve under R$500" rules.

**What exists:** Nothing. Rules are described in the concept but have no persistence layer.

```sql
CREATE TABLE public.client_approval_rules (
  id          uuid    DEFAULT gen_random_uuid() NOT NULL,
  client_id   uuid    NOT NULL,
  agent_slug  text,                 -- NULL = applies to all agents
  rule_type   text    NOT NULL,     -- 'amount_limit' | 'category' | 'supplier' | 'similarity'
  condition   jsonb   NOT NULL,     -- {"max_amount": 500} | {"category": "insumos"} | ...
  action      text    DEFAULT 'auto_approve', -- 'auto_approve' | 'skip_review'
  active      boolean DEFAULT true,
  created_at  timestamptz DEFAULT now() NOT NULL,

  CONSTRAINT client_approval_rules_pkey PRIMARY KEY (id),
  CONSTRAINT client_approval_rules_client_id_fkey
    FOREIGN KEY (client_id) REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE
);
```

**Notes:**
- Rules are only accessible to clients above the threshold approval count (enforced by the backend, not the frontend).
- The `RuleBuilder` component in `UnderDesk` writes to this table.

---

## Gap 5 — `client_approval_stats` (new table) — P1

**Blocks:** Trust level indicator in `RuleBuilder`, progressive unlock UI, onboarding progress.

**What exists:** `audit_log` has approval actions but requires an expensive aggregation query for the home screen.

```sql
CREATE TABLE public.client_approval_stats (
  client_id       uuid NOT NULL,
  total_approved  int  DEFAULT 0,
  total_rejected  int  DEFAULT 0,
  total_edited    int  DEFAULT 0,
  total_snoozed   int  DEFAULT 0,
  trust_level     text DEFAULT 'manual', -- 'manual' | 'similar_toggle' | 'rules' | 'full_config'
  updated_at      timestamptz DEFAULT now(),

  CONSTRAINT client_approval_stats_pkey PRIMARY KEY (client_id),
  CONSTRAINT client_approval_stats_client_id_fkey
    FOREIGN KEY (client_id) REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE
);
```

**Trust level thresholds (from concept §6.3):**
| `total_approved` | `trust_level` | Unlocks |
|---|---|---|
| 0–9 | `manual` | All manual review |
| 10–24 | `similar_toggle` | "Auto-approve similar" per routine type |
| 25–49 | `rules` | `client_approval_rules` UI |
| 50+ | `full_config` | Full auto-approval configuration |

**Notes:**
- Updated by a trigger on `approval_requests` status changes.
- Never auto-approve: transactions > R$10,000, new supplier/customer creation, contract changes, payroll, anomaly-flagged items — enforced server-side regardless of rules.

---

## Gap 6 — `suppliers` (new table) — P1

**Blocks:** `ComprasRoom` Left Drawer (Fornecedores list with ratings, categories, notes).

**What exists:** `analytics_v2.dim_fornecedores` is a reporting/analytics dimension populated from transaction data. It has aggregate metrics (total purchases, ticket medio) but no operational data: no ratings, no categories, no contact info, no agent-added notes.

```sql
CREATE TABLE public.suppliers (
  id            uuid    DEFAULT gen_random_uuid() NOT NULL,
  client_id     uuid    NOT NULL,
  name          text    NOT NULL,
  cnpj          text,
  category      text,               -- 'Escritório' | 'Insumos' | 'Limpeza' | 'Alimentos' | ...
  tags          text[]  DEFAULT '{}',
  rating        numeric,            -- 1.0 to 5.0 (set by owner or agent from feedback)
  contact_phone text,
  contact_email text,
  city          text,
  state         text,
  notes         text,               -- agent/owner notes (drives corkboard insights)
  is_active     boolean DEFAULT true,
  created_at    timestamptz DEFAULT now() NOT NULL,
  updated_at    timestamptz DEFAULT now() NOT NULL,

  CONSTRAINT suppliers_pkey PRIMARY KEY (id),
  CONSTRAINT suppliers_client_id_cnpj_key UNIQUE (client_id, cnpj),
  CONSTRAINT suppliers_client_id_fkey
    FOREIGN KEY (client_id) REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE
);

CREATE INDEX idx_suppliers_client ON public.suppliers (client_id, is_active);
```

**Notes:**
- The `Compras` agent links `dim_fornecedores.cnpj` ↔ `suppliers.cnpj` to join analytics data with operational metadata.
- `rating` shown as stars (★★★★☆) in the Left Drawer.
- `notes` feed the Corkboard insights: "Silva é 15% mais caro, mas notas indicam melhor qualidade."

---

## Gap 7 — `client_notification_preferences` (new table) — P1

**Blocks:** Admin > notification settings UI (which channels to use per notification type, quiet hours).

**What exists:** Nothing. Notification channel defaults are hardcoded in the concept doc.

```sql
CREATE TABLE public.client_notification_preferences (
  client_id          uuid NOT NULL,
  notification_type  text NOT NULL, -- 'urgent' | 'decision' | 'insight' | 'routine' | 'alert'
  in_app             boolean DEFAULT true,
  push               boolean DEFAULT true,
  email              boolean DEFAULT false,
  quiet_hours_start  time,          -- e.g., '22:00'
  quiet_hours_end    time,          -- e.g., '07:00'
  timezone           text DEFAULT 'America/Sao_Paulo',

  CONSTRAINT client_notification_preferences_pkey
    PRIMARY KEY (client_id, notification_type),
  CONSTRAINT client_notification_preferences_client_id_fkey
    FOREIGN KEY (client_id) REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE
);
```

---

## Gap 8 — `client_kpi_snapshot` (new table) — P1

**Blocks:** `NumbersPanel` collapsed 1-line on home screen, `FinanceiroRoom` desk surface header. Computing live from `analytics_v2.fato_transacoes` on every home load is expensive at scale.

**What exists:** `analytics_v2` dimensional model exists and can compute these values, but has no cache layer.

```sql
CREATE TABLE public.client_kpi_snapshot (
  client_id    uuid NOT NULL,
  period       text NOT NULL,  -- '7d' | '30d' | '90d' | '1y'
  metrics      jsonb NOT NULL, -- {receita, despesas, margem_pct, pedidos, clientes_ativos, ticket_medio}
  computed_at  timestamptz DEFAULT now() NOT NULL,

  CONSTRAINT client_kpi_snapshot_pkey PRIMARY KEY (client_id, period),
  CONSTRAINT client_kpi_snapshot_client_id_fkey
    FOREIGN KEY (client_id) REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE
);
```

**Example `metrics` payload:**
```json
{
  "receita": 543800,
  "despesas": 312000,
  "margem_pct": 42.6,
  "pedidos": 128,
  "clientes_ativos": 47,
  "ticket_medio": 4248,
  "currency": "BRL"
}
```

**Notes:**
- Updated by a scheduled job (pg_cron) every hour or on-demand after a sync job completes.
- Frontend reads the `30d` period for the home screen collapsed line.
- On period toggle in `FinanceiroRoom`, fetches the appropriate row.

---

## Gap 9 — `doc_templates` (new table) — P2

**Blocks:** `DocumentosRoom` `ModelDrawer` (template picker). Without this, templates are hardcoded.

**What exists:** `vector_db.documents` exists for RAG but is oriented toward uploaded/processed files, not editable templates.

```sql
CREATE TABLE public.doc_templates (
  id          uuid    DEFAULT gen_random_uuid() NOT NULL,
  client_id   uuid,                 -- NULL = system-wide template (shipped by Blu)
  name        text    NOT NULL,
  category    text,                 -- 'Handover' | 'Delivery' | 'Proposta' | 'Ata de Reunião' | ...
  description text,
  content     text    NOT NULL,     -- template body (markdown)
  variables   jsonb   DEFAULT '[]', -- [{name, label, required, default}]
  is_system   boolean DEFAULT false,
  created_at  timestamptz DEFAULT now() NOT NULL,
  updated_at  timestamptz DEFAULT now() NOT NULL,

  CONSTRAINT doc_templates_pkey PRIMARY KEY (id),
  CONSTRAINT doc_templates_client_id_fkey
    FOREIGN KEY (client_id) REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE
);

CREATE INDEX idx_doc_templates_client ON public.doc_templates (client_id)
  WHERE client_id IS NOT NULL;
```

**Notes:**
- System templates (`client_id IS NULL, is_system = true`) are visible to all clients.
- Client-custom templates only visible to their `client_id`.
- `variables` drives placeholder substitution in the `EditorCanvas` (e.g., `{{nome_empresa}}`).

---

## Gap 10 — `vector_db.document_versions` (new table) — P2

**Blocks:** `DocumentosRoom` `ArchiveDrawer` version history, `DiffViewer` comparison.

**What exists:** `vector_db.documents` has a single `status` and `content_hash` but no version history. The concept explicitly requires version history in the Right Drawer.

```sql
CREATE TABLE vector_db.document_versions (
  id              uuid  DEFAULT gen_random_uuid() NOT NULL,
  document_id     uuid  NOT NULL,
  version_number  int   NOT NULL,
  content         text  NOT NULL,
  change_summary  text,             -- brief auto-generated diff summary
  created_by      text,             -- user ref or 'agent:{slug}'
  created_at      timestamptz DEFAULT now() NOT NULL,

  CONSTRAINT document_versions_pkey PRIMARY KEY (id),
  CONSTRAINT document_versions_document_version_uniq UNIQUE (document_id, version_number),
  CONSTRAINT document_versions_document_id_fkey
    FOREIGN KEY (document_id) REFERENCES vector_db.documents(id) ON DELETE CASCADE
);

CREATE INDEX idx_doc_versions_document ON vector_db.document_versions (document_id, version_number DESC);
```

---

## Gap 11 — `vector_db.documents` missing columns — P2

**Blocks:** Linking documents to templates, document sharing, agent attribution.

**What exists:** `vector_db.documents` has `id, client_id, title, file_name, file_type, storage_path, source, processing_mode, status, scope, category, content_hash, chunk_count`.

**What's missing:**

```sql
ALTER TABLE vector_db.documents
  ADD COLUMN IF NOT EXISTS template_id  uuid,       -- which doc_template was used
  ADD COLUMN IF NOT EXISTS agent_slug   text,        -- which agent created/manages this doc
  ADD COLUMN IF NOT EXISTS is_shared    boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS editor_content text;      -- live editable content (separate from RAG chunks)
```

**Notes:**
- `editor_content` stores the user-editable rich text. `chunk` processing is a separate pipeline that operates on the saved version. Keeping them separate avoids overwriting the editor state during chunk ingestion.
- `template_id` links to `doc_templates` for the Corkboard insight "Handover e Delivery são 80% similares."

---

## Gap 12 — `conversa` missing agent context — P2

**Blocks:** `ChatOverlay` routing — the component needs to know which agent it's talking to and in which room context, so it can pass the correct system prompt context to the backend.

**What exists:** `conversa` has only `id, client_id, created_at, updated_at`.

**What's missing:**

```sql
ALTER TABLE public.conversa
  ADD COLUMN IF NOT EXISTS agent_slug   text,   -- 'compras' | 'financeiro' | 'agenda' | ...
  ADD COLUMN IF NOT EXISTS room_context text;   -- which desk room originated the chat
```

**Notes:**
- `standalone_agent_sessions` already has `agent_catalog_id` and serves a different flow (configuration sessions). The `conversa` table is the persistent conversation record for the in-room `ChatOverlay`.
- The backend uses `agent_slug` to select the correct system prompt and tool set.

---

## What Does NOT Need Schema Changes

These frontend needs are already covered:

| Frontend Need | Existing Table |
|---|---|
| Approval list | `approval_requests` (with column additions above) |
| Corkboard insights | `client_insights` |
| Agent routines (UnderDesk) | `client_routines` |
| Analytics data | `analytics_v2.*` |
| Integration status (Admin) | `credencial_servico_externo` + `integration_tokens` |
| Audit log (Admin) | `audit_log` |
| File uploads | `uploaded_files_metadata` |
| Document RAG | `vector_db.documents` + `vector_db.document_chunks` |
| Calendar connection | `calendar_settings` |
| Agent catalog | `agent_catalog` + `client_enabled_agents` (with additions above) |
| Activity feed | `audit_log` (filtered by client, ordered DESC) |
| User tier/plan | `clientes_blu.tier` |

---

## Migration Order (if implementing all gaps)

```
1. ALTER TABLE approval_requests    (P0 — needed before any approval UI)
2. ALTER TABLE client_enabled_agents (P0 — needed before home screen)
3. CREATE TABLE notifications        (P0 — needed before notification bell)
4. CREATE TABLE client_kpi_snapshot  (P1 — needed before NumbersPanel)
5. CREATE TABLE suppliers            (P1 — needed before ComprasRoom)
6. CREATE TABLE client_approval_stats (P1 — needed before trust UI)
7. CREATE TABLE client_approval_rules (P1 — needed before RuleBuilder)
8. CREATE TABLE client_notification_preferences (P1)
9. ALTER TABLE conversa              (P2)
10. ALTER TABLE vector_db.documents  (P2)
11. CREATE TABLE doc_templates        (P2)
12. CREATE TABLE vector_db.document_versions (P2)
```
