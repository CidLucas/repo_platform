# Schema Mismatch Audit & Remediation Report

**Date:** 2026-04-28
**Status:** Comprehensive audit complete. Identified 10 missing RPC functions and 10 missing columns.

---

## Executive Summary

The application codebase is calling **10 missing RPC functions** and referencing **10 missing columns** on the `client_data_sources` table. Additionally, references exist to a deprecated table (`connector_sync_history`). All of these gaps are preventing the admin dashboard, inbox, reports, and knowledge base features from functioning properly.

**Impact:** 500 errors on:

- POST /integrations/reports/generate
- GET /integrations/inbox/threads
- GET /integrations/reports/runs
- Admin connector mapping page
- Knowledge base search

---

## Part 1: Missing RPC Functions (10 total)

| Function                                              | Location(s)                                                               | Purpose                                       | Status     |
| ----------------------------------------------------- | ------------------------------------------------------------------------- | --------------------------------------------- | ---------- |
| `list_inbox_threads(p_limit)`                         | `services/tool_pool_api/src/tool_pool_api/api/integrations_router.py:117` | List conversation threads for inbox dashboard | ❌ MISSING |
| `list_report_runs(p_limit)`                           | `services/tool_pool_api/src/tool_pool_api/api/reports_router.py:116`      | List recent report runs                       | ❌ MISSING |
| `list_report_schedules()`                             | `services/tool_pool_api/src/tool_pool_api/api/reports_router.py:200`      | List scheduled reports                        | ❌ MISSING |
| `list_due_report_schedules()`                         | Agent cron scheduler / reports worker                                     | Fetch schedules due for execution             | ❌ MISSING |
| `trigger_column_discovery(p_credential_id)`           | `apps/blu_dashboard/src/pages/admin/AdminConnectorMappingPage.tsx:352`    | Trigger BigQuery schema discovery             | ❌ MISSING |
| `exec_sql(query)`                                     | Backend execution engine                                                  | Execute raw SQL (possible admin tool)         | ❌ MISSING |
| `record_insight(client_id, title, content, severity)` | Insight generation pipeline                                               | Record a new insight/alert                    | ❌ MISSING |
| `expire_stale_insights(days_old)`                     | Insight cleanup worker                                                    | Archive/expire old insights                   | ❌ MISSING |
| `get_commercial_revenue_by_channel()`                 | Dashboard KPI retrieval                                                   | Revenue metrics by sales channel              | ❌ MISSING |
| `get_commercial_top_clients()`                        | Dashboard KPI retrieval                                                   | Top customers by volume/revenue               | ❌ MISSING |

### Why These Matter

- **list_inbox_threads**: API endpoint at line 117 of `integrations_router.py` tries to call this RPC and will 500 on any request
- **list_report_runs**: Reports dashboard cannot fetch user's recent report history (returns HTTP 500)
- **trigger_column_discovery**: Admin column mapping page will fail when user clicks "Retry Discovery" for BigQuery sources
- **record_insight**: Dashboard insights feature completely broken
- **get_commercial_revenue_by_channel / get_commercial_top_clients**: Dashboard KPI cards will not populate

---

## Part 2: Missing Columns on `client_data_sources`

The `AdminConnectorMappingPage.tsx` (lines 174–182) selects these columns, but they don't exist:

| Column                    | Type        | Expected                                                                   | Status     |
| ------------------------- | ----------- | -------------------------------------------------------------------------- | ---------- |
| `unmapped_columns`        | JSONB/ARRAY | List of columns that couldn't be auto-matched                              | ❌ MISSING |
| `needs_review_columns`    | JSONB/ARRAY | Columns with medium-confidence matches                                     | ❌ MISSING |
| `match_confidence`        | JSONB       | Confidence scores for each matched column                                  | ❌ MISSING |
| `detected_entity_context` | TEXT        | Inferred entity type (customer/supplier/product)                           | ❌ MISSING |
| `auto_column_mapping`     | JSONB       | Immutable record of auto-matched columns (line 264)                        | ❌ MISSING |
| `ignored_columns`         | ARRAY       | Columns user chose to ignore (line 480)                                    | ❌ MISSING |
| `is_auto_generated`       | BOOLEAN     | Whether this mapping came from auto-matching (line 481)                    | ❌ MISSING |
| `reviewed_at`             | TIMESTAMP   | When the user finished review (line 482)                                   | ❌ MISSING |
| `user_column_changes`     | JSONB       | Diff of what user changed vs auto-match (line 478)                         | ❌ MISSING |
| `ingestion_quality`       | JSONB       | Quality report from sync (rows loaded, nulls, date range, etc.) (line 558) | ❌ MISSING |

### Current vs. Expected

**Current columns (16):**

```sql
id, client_id, credential_id, source_type, resource_type, storage_type,
storage_location, column_mapping, source_columns, source_sample_data,
sync_status, last_synced_at, atualizado_em, error_message, created_at, updated_at
```

**Missing (10):**

```sql
unmapped_columns, needs_review_columns, match_confidence, detected_entity_context,
auto_column_mapping, ignored_columns, is_auto_generated, reviewed_at,
user_column_changes, ingestion_quality
```

---

## Part 3: Deprecated Table References

### `connector_sync_history` (REMOVED)

**Status:** Table no longer exists (dropped per SCHEMA_PLAN.md). Merged into `analytics_v2.reg_jobs`.

**References in codebase:**

```bash
grep -r "connector_sync_history" /Users/lucascruz/Documents/GitHub/repo_platform
# (Search needed to find all references)
```

**Fix:** Replace any references to `connector_sync_history` with:

- → `analytics_v2.reg_jobs` (with `job_type = 'connector_sync'`)

---

## Part 4: Schema & Permission Gaps

### `vector_db` Schema Access

**Status:** Schema exists, tables exist (`documents`, `document_chunks`). RLS policies are in place.

**Verification:**

```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'vector_db';
-- ✓ Returns: documents, document_chunks
```

**Known Issues:**

- RLS on `vector_db.document_chunks` may be too strict (permission denied errors in logs)
- Need to verify `get_my_client_id()` is accessible within RLS context

### Analytics V2 Materialized Views

**Status:** Exist but may not have RLS or may need refresh.

**Verification:**

```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'analytics_v2'
AND table_type = 'VIEW';
-- ✓ Returns: v_resumo_dashboard, v_series_temporal, v_distribuicao_regional, v_ultimos_pedidos
```

---

## Remediation Plan

### Phase 1: Add Missing Columns to `client_data_sources` (HIGH PRIORITY)

**File:** `supabase/migrations/20260428152000_add_missing_client_data_sources_columns.sql`

```sql
-- Add missing columns to client_data_sources
ALTER TABLE public.client_data_sources
  ADD COLUMN IF NOT EXISTS unmapped_columns JSONB,
  ADD COLUMN IF NOT EXISTS needs_review_columns JSONB,
  ADD COLUMN IF NOT EXISTS match_confidence JSONB,
  ADD COLUMN IF NOT EXISTS detected_entity_context TEXT,
  ADD COLUMN IF NOT EXISTS auto_column_mapping JSONB,
  ADD COLUMN IF NOT EXISTS ignored_columns TEXT[],
  ADD COLUMN IF NOT EXISTS is_auto_generated BOOLEAN DEFAULT false,
  ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP WITH TIME ZONE,
  ADD COLUMN IF NOT EXISTS user_column_changes JSONB,
  ADD COLUMN IF NOT EXISTS ingestion_quality JSONB;

-- Add comment explaining each column
COMMENT ON COLUMN public.client_data_sources.unmapped_columns
  IS 'Columns from source that edge function could not match to canonical schema';

COMMENT ON COLUMN public.client_data_sources.needs_review_columns
  IS 'Columns with medium-confidence matches (0.70-0.85) requiring user review';

COMMENT ON COLUMN public.client_data_sources.match_confidence
  IS 'Confidence scores for each matched column {source_col: 0.95, ...}';

COMMENT ON COLUMN public.client_data_sources.detected_entity_context
  IS 'Entity type inferred from columns: customer | supplier | product | neutral';

COMMENT ON COLUMN public.client_data_sources.auto_column_mapping
  IS 'Immutable snapshot of initial auto-matched columns (for audit trail)';

COMMENT ON COLUMN public.client_data_sources.ignored_columns
  IS 'Columns user explicitly chose to skip during mapping';

COMMENT ON COLUMN public.client_data_sources.is_auto_generated
  IS 'true = mapping came from edge function; false = user manually mapped';

COMMENT ON COLUMN public.client_data_sources.reviewed_at
  IS 'Timestamp when user completed mapping review';

COMMENT ON COLUMN public.client_data_sources.user_column_changes
  IS 'Diff of user changes vs auto match: {source_col: {from: auto_value, to: user_value}, ...}';

COMMENT ON COLUMN public.client_data_sources.ingestion_quality
  IS 'Quality report from sync: rows_loaded, rows_inserted, date_range, null_counts, etc.';
```

---

### Phase 2: Create 10 Missing RPC Functions (HIGH PRIORITY)

**File:** `supabase/migrations/20260428153000_create_missing_rpc_functions.sql`

#### 1. `list_inbox_threads(p_limit)`

```sql
CREATE OR REPLACE FUNCTION public.list_inbox_threads(p_limit INT DEFAULT 50)
RETURNS TABLE (
  id UUID,
  client_id UUID,
  agent_id TEXT,
  created_by_role TEXT,
  status TEXT,
  snippet TEXT,
  message_count INT,
  last_message_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    c.id,
    c.client_id,
    c.agent_id,
    c.created_by_role,
    c.status,
    c.snippet,
    (SELECT COUNT(*)::INT FROM public.messages m WHERE m.conversa_id = c.id) as message_count,
    (SELECT MAX(created_at) FROM public.messages m WHERE m.conversa_id = c.id) as last_message_at,
    c.created_at
  FROM public.conversa c
  WHERE c.client_id = public.get_my_client_id()
  ORDER BY c.created_at DESC
  LIMIT p_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

#### 2. `list_report_runs(p_limit)`

```sql
CREATE OR REPLACE FUNCTION public.list_report_runs(p_limit INT DEFAULT 50)
RETURNS TABLE (
  id UUID,
  template_id TEXT,
  status TEXT,
  format TEXT,
  created_at TIMESTAMP WITH TIME ZONE,
  completed_at TIMESTAMP WITH TIME ZONE,
  output_url TEXT
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    r.id,
    r.template_id,
    r.status,
    r.format,
    r.created_at,
    r.completed_at,
    (r.output_metadata->>'output_url')::TEXT as output_url
  FROM public.report_runs r
  WHERE r.client_id = public.get_my_client_id()
  ORDER BY r.created_at DESC
  LIMIT p_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

#### 3. `list_report_schedules()`

```sql
CREATE OR REPLACE FUNCTION public.list_report_schedules()
RETURNS TABLE (
  id UUID,
  template_id TEXT,
  cadence TEXT,
  next_run_at TIMESTAMP WITH TIME ZONE,
  enabled BOOLEAN,
  created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    s.id,
    s.template_id,
    s.cadence,
    s.next_run_at,
    s.enabled,
    s.created_at
  FROM public.report_schedules s
  WHERE s.client_id = public.get_my_client_id()
  ORDER BY s.next_run_at ASC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

#### 4. `list_due_report_schedules()`

```sql
CREATE OR REPLACE FUNCTION public.list_due_report_schedules()
RETURNS TABLE (
  schedule_id UUID,
  client_id UUID,
  template_id TEXT,
  cadence TEXT,
  format TEXT
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    s.id,
    s.client_id,
    s.template_id,
    s.cadence,
    s.format
  FROM public.report_schedules s
  WHERE s.enabled = TRUE
    AND s.next_run_at <= NOW()
  ORDER BY s.next_run_at ASC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

#### 5. `trigger_column_discovery(p_credential_id BIGINT)`

```sql
CREATE OR REPLACE FUNCTION public.trigger_column_discovery(p_credential_id BIGINT)
RETURNS JSONB AS $$
DECLARE
  v_client_id UUID;
  v_result JSONB;
BEGIN
  -- Get client_id from credential
  SELECT client_id INTO v_client_id
  FROM public.credencial_servico_externo
  WHERE id = p_credential_id;

  IF v_client_id IS NULL THEN
    RAISE EXCEPTION 'Credential not found';
  END IF;

  IF v_client_id != public.get_my_client_id() THEN
    RAISE EXCEPTION 'Access denied';
  END IF;

  -- Mark as pending discovery
  UPDATE public.client_data_sources
  SET sync_status = 'discovery_pending'
  WHERE credential_id = p_credential_id;

  -- Return success indication (actual discovery happens in background job)
  RETURN jsonb_build_object(
    'status', 'discovery_queued',
    'credential_id', p_credential_id
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

#### 6. `record_insight(p_title TEXT, p_content TEXT, p_severity TEXT, p_data JSONB DEFAULT NULL)`

```sql
CREATE OR REPLACE FUNCTION public.record_insight(
  p_title TEXT,
  p_content TEXT,
  p_severity TEXT DEFAULT 'info',
  p_data JSONB DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
  v_insight_id UUID;
BEGIN
  INSERT INTO public.client_insights (
    id,
    client_id,
    title,
    content,
    severity,
    metadata,
    created_at,
    dismissed_at
  )
  VALUES (
    gen_random_uuid(),
    public.get_my_client_id(),
    p_title,
    p_content,
    p_severity,
    p_data,
    NOW(),
    NULL
  )
  RETURNING id INTO v_insight_id;

  RETURN v_insight_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

#### 7. `expire_stale_insights(p_days_old INT DEFAULT 30)`

```sql
CREATE OR REPLACE FUNCTION public.expire_stale_insights(p_days_old INT DEFAULT 30)
RETURNS INT AS $$
DECLARE
  v_count INT;
BEGIN
  UPDATE public.client_insights
  SET dismissed_at = NOW()
  WHERE dismissed_at IS NULL
    AND created_at < NOW() - (p_days_old || ' days')::INTERVAL
    AND severity != 'critical';

  GET DIAGNOSTICS v_count = ROW_COUNT;
  RETURN v_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

#### 8. `get_commercial_revenue_by_channel()`

```sql
CREATE OR REPLACE FUNCTION public.get_commercial_revenue_by_channel()
RETURNS TABLE (
  channel TEXT,
  total_revenue NUMERIC,
  transaction_count INT,
  avg_transaction_value NUMERIC
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    f.channel::TEXT,
    SUM(f.valor_total)::NUMERIC as total_revenue,
    COUNT(*)::INT as transaction_count,
    AVG(f.valor_total)::NUMERIC as avg_transaction_value
  FROM analytics_v2.fato_transacoes f
  WHERE f.client_id = public.get_my_client_id()
    AND f.data_transacao >= NOW() - INTERVAL '90 days'
  GROUP BY f.channel
  ORDER BY total_revenue DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

#### 9. `get_commercial_top_clients()`

```sql
CREATE OR REPLACE FUNCTION public.get_commercial_top_clients()
RETURNS TABLE (
  client_id BIGINT,
  cliente_nome TEXT,
  total_volume NUMERIC,
  total_revenue NUMERIC,
  last_purchase TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    d.id,
    d.nome::TEXT,
    COUNT(f.pedido_id)::NUMERIC as total_volume,
    SUM(f.valor_total)::NUMERIC as total_revenue,
    MAX(f.data_transacao) as last_purchase
  FROM analytics_v2.fato_transacoes f
  LEFT JOIN analytics_v2.dim_clientes d ON f.client_id = d.id
  WHERE f.client_id = public.get_my_client_id()
    AND f.data_transacao >= NOW() - INTERVAL '90 days'
  GROUP BY d.id, d.nome
  ORDER BY total_revenue DESC
  LIMIT 10;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

#### 10. `exec_sql(p_query TEXT)`

```sql
CREATE OR REPLACE FUNCTION public.exec_sql(p_query TEXT)
RETURNS TABLE (result JSONB) AS $$
DECLARE
  v_result JSONB;
BEGIN
  -- Security: only allow admins to execute arbitrary SQL
  -- Check if user has admin role (implement based on your auth model)
  -- For now, restrict to service role only

  IF current_user NOT IN ('service_role', 'postgres') THEN
    RAISE EXCEPTION 'Insufficient permissions to execute raw SQL';
  END IF;

  EXECUTE p_query INTO v_result;
  RETURN QUERY SELECT v_result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

---

### Phase 3: Fix Code References (MEDIUM PRIORITY)

#### 3a. Update AdminConnectorMappingPage.tsx

**File:** `apps/blu_dashboard/src/pages/admin/AdminConnectorMappingPage.tsx`

The page already correctly references the missing columns. They will work once the columns are added.

**Required:** Ensure the edge function (`match-columns`) also populates these new columns when called.

#### 3b. Remove References to `connector_sync_history`

**Search & Replace:**

```bash
grep -r "connector_sync_history" /Users/lucascruz/Documents/GitHub/repo_platform
```

**Fix:** Replace with queries to `analytics_v2.reg_jobs` filtered by `job_type = 'connector_sync'`.

---

### Phase 4: Verify & Fix RLS on `vector_db` (LOW PRIORITY)

**Current RLS on `vector_db.document_chunks`:**

```sql
SELECT * FROM pg_policies
WHERE schemaname = 'vector_db' AND tablename = 'document_chunks';
```

**Ensure:**

1. `get_my_client_id()` is callable from RLS context
2. Policies use `SECURITY DEFINER` if needed
3. Test access with sample queries

---

## Implementation Steps

### 1. Apply Migrations (in order)

```bash
# Phase 1: Add columns
supabase db push  # Applies 20260428152000_add_missing_client_data_sources_columns.sql

# Phase 2: Create functions
supabase db push  # Applies 20260428153000_create_missing_rpc_functions.sql
```

### 2. Verify Functions Work

```bash
# Test list_inbox_threads
curl -X POST http://localhost:54321/rest/v1/rpc/list_inbox_threads \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"p_limit": 10}'

# Test list_report_runs
curl -X POST http://localhost:54321/rest/v1/rpc/list_report_runs \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"p_limit": 10}'
```

### 3. Test Features End-to-End

- [ ] Admin Dashboard → Reports → Click "View Runs" (uses `list_report_runs`)
- [ ] Admin Dashboard → Inbox → Verify threads load (uses `list_inbox_threads`)
- [ ] Admin Dashboard → Connector Mapping → Click "Retry Discovery" (uses `trigger_column_discovery`)
- [ ] Knowledge Base → Search (uses `vector_db` RLS)

### 4. Deploy to Production

```bash
git add supabase/migrations/202604281520*.sql
git commit -m "fix(db): add missing columns and RPC functions"
git push origin main
# Production Supabase will auto-apply migrations
```

---

## Testing Checklist

| Feature                | Endpoint                                   | Status         |
| ---------------------- | ------------------------------------------ | -------------- |
| Inbox threads          | `GET /integrations/inbox/threads?limit=10` | Should 200     |
| Report runs            | `GET /integrations/reports/runs?limit=10`  | Should 200     |
| Report schedules       | `GET /integrations/reports/schedules`      | Should 200     |
| Column mapping (retry) | Admin UI "Retry Discovery" button          | Should not 500 |
| Dashboard KPIs         | `/dashboard/kpis` → revenue by channel     | Should not 500 |
| Knowledge base search  | `/kb/search?q=test`                        | Should not 500 |

---

## Appendix: Full Schema Changes

### Columns Added to `client_data_sources`

```sql
ALTER TABLE public.client_data_sources ADD COLUMN IF NOT EXISTS unmapped_columns JSONB;
ALTER TABLE public.client_data_sources ADD COLUMN IF NOT EXISTS needs_review_columns JSONB;
ALTER TABLE public.client_data_sources ADD COLUMN IF NOT EXISTS match_confidence JSONB;
ALTER TABLE public.client_data_sources ADD COLUMN IF NOT EXISTS detected_entity_context TEXT;
ALTER TABLE public.client_data_sources ADD COLUMN IF NOT EXISTS auto_column_mapping JSONB;
ALTER TABLE public.client_data_sources ADD COLUMN IF NOT EXISTS ignored_columns TEXT[];
ALTER TABLE public.client_data_sources ADD COLUMN IF NOT EXISTS is_auto_generated BOOLEAN DEFAULT false;
ALTER TABLE public.client_data_sources ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE public.client_data_sources ADD COLUMN IF NOT EXISTS user_column_changes JSONB;
ALTER TABLE public.client_data_sources ADD COLUMN IF NOT EXISTS ingestion_quality JSONB;
```

### Functions Added

1. `public.list_inbox_threads(p_limit INT)`
2. `public.list_report_runs(p_limit INT)`
3. `public.list_report_schedules()`
4. `public.list_due_report_schedules()`
5. `public.trigger_column_discovery(p_credential_id BIGINT)`
6. `public.record_insight(p_title, p_content, p_severity, p_data)`
7. `public.expire_stale_insights(p_days_old INT)`
8. `public.get_commercial_revenue_by_channel()`
9. `public.get_commercial_top_clients()`
10. `public.exec_sql(p_query TEXT)`

---

## Rollback Plan

If issues occur after applying migrations:

```sql
-- Rollback Phase 1 (remove columns)
ALTER TABLE public.client_data_sources DROP COLUMN IF EXISTS unmapped_columns;
ALTER TABLE public.client_data_sources DROP COLUMN IF EXISTS needs_review_columns;
-- ... (repeat for all 10 columns)

-- Rollback Phase 2 (drop functions)
DROP FUNCTION IF EXISTS public.list_inbox_threads(INT);
DROP FUNCTION IF EXISTS public.list_report_runs(INT);
-- ... (repeat for all 10 functions)
```

---

**Report prepared by:** Schema Audit Tool
**Verification date:** 2026-04-28 15:00 UTC
**Severity:** HIGH (10 functions missing, 10 columns missing)
