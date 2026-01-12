# Analytics Tables Migration Instructions

## The Problem

Your Supabase database currently has **views** named:
- `analytics_gold_orders`
- `analytics_gold_products`
- `analytics_gold_customers`
- `analytics_gold_suppliers`
- `analytics_silver`

PostgreSQL RLS (Row Level Security) **cannot be applied to views**, only to tables. We need to replace these views with concrete tables.

## The Solution

I've created a migration that:
1. ✅ Drops existing views
2. ✅ Creates concrete tables with the same names
3. ✅ Enables RLS on all tables
4. ✅ Applies multi-tenant security policies

## Migration File

Location: `supabase/migrations/20251226_drop_views_create_tables_with_rls.sql`

## How to Apply (3 Options)

### Option 1: Supabase Dashboard (RECOMMENDED - Easiest)

This is the most reliable method when `supabase db push` fails with authentication errors.

**Steps:**

1. Open your Supabase project dashboard: https://supabase.com/dashboard
2. Navigate to your project: `haruewffnubdgyofftut`
3. Go to **SQL Editor** (left sidebar)
4. Click **"New Query"**
5. Copy the entire contents of `supabase/migrations/20251226_drop_views_create_tables_with_rls.sql`
6. Paste into the SQL editor
7. Click **"Run"** or press `Cmd+Enter`

**Expected Output:**
```
Success. No rows returned
```

**Verification:**
```sql
-- Run this query to verify tables were created with RLS
SELECT tablename, rowsecurity
FROM pg_tables
WHERE tablename LIKE 'analytics_%';

-- Expected: rowsecurity = true for all tables
```

### Option 2: Fix Supabase CLI Configuration

The error `password authentication failed for user "postgres"` suggests the Supabase CLI is not configured correctly.

**Steps:**

1. **Get your database password** from Supabase Dashboard:
   - Go to Project Settings → Database
   - Under "Connection string", find the password
   - Or reset it and copy the new one

2. **Link Supabase project:**
```bash
cd /Users/lucascruz/Documents/GitHub/vizu-mono
supabase link --project-ref haruewffnubdgyofftut
# Enter database password when prompted
```

3. **Apply migration:**
```bash
supabase db push
```

### Option 3: Direct psql Connection

If you have `psql` installed, connect directly:

**Steps:**

1. Get connection string from Supabase Dashboard (Project Settings → Database)
2. Run:
```bash
psql "postgresql://postgres:[YOUR-PASSWORD]@db.haruewffnubdgyofftut.supabase.co:5432/postgres" \
  -f supabase/migrations/20251226_drop_views_create_tables_with_rls.sql
```

Replace `[YOUR-PASSWORD]` with your actual database password.

## After Migration: Verify Everything Works

### Step 1: Check Tables Exist

Run in Supabase SQL Editor:
```sql
SELECT table_name, table_type
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name LIKE 'analytics_%'
ORDER BY table_name;
```

**Expected Output:**
```
analytics_gold_customers    | BASE TABLE
analytics_gold_orders       | BASE TABLE
analytics_gold_products     | BASE TABLE
analytics_gold_suppliers    | BASE TABLE
analytics_silver            | BASE TABLE
```

(Should show `BASE TABLE`, NOT `VIEW`)

### Step 2: Verify RLS is Enabled

```sql
SELECT schemaname, tablename, rowsecurity
FROM pg_tables
WHERE tablename LIKE 'analytics_%'
ORDER BY tablename;
```

**Expected:** All should have `rowsecurity = t` (true)

### Step 3: Check RLS Policies

```sql
SELECT schemaname, tablename, policyname, roles, cmd
FROM pg_policies
WHERE tablename LIKE 'analytics_%'
ORDER BY tablename, policyname;
```

**Expected:** Should see policies like:
- "Users can view own client gold orders" (SELECT, authenticated)
- "Service role full access to gold orders" (ALL, service_role)

### Step 4: Test from Analytics API

```bash
# Test that analytics_api can now connect
curl http://localhost:8004/health

# Expected: {"status":"ok","service":"analytics-api",...}

# Test gold orders endpoint (will be empty until you populate data)
curl http://localhost:8004/api/dashboard/home_gold

# Expected: {} or valid JSON (not "Internal Server Error" about missing table)
```

## Common Issues and Solutions

### Issue 1: "relation already exists"

If you see this error, the table was already created. Safe to ignore, or drop and recreate:

```sql
DROP TABLE IF EXISTS public.analytics_gold_orders CASCADE;
-- Then run the migration again
```

### Issue 2: "permission denied for schema public"

You need to be connected as a user with sufficient privileges (usually `postgres` user via dashboard).

### Issue 3: RLS policies not working

Verify user has a `clientes_vizu` record:

```sql
SELECT * FROM public.clientes_vizu WHERE external_user_id = '<your-supabase-user-id>';
```

If no record exists, RLS will filter out all rows (user sees nothing).

### Issue 4: Still getting "cannot create index on relation"

This means there's still a view with that name. Drop it manually:

```sql
DROP VIEW IF EXISTS public.analytics_gold_orders CASCADE;
DROP VIEW IF EXISTS public.analytics_gold_products CASCADE;
DROP VIEW IF EXISTS public.analytics_gold_customers CASCADE;
DROP VIEW IF EXISTS public.analytics_gold_suppliers CASCADE;
DROP VIEW IF EXISTS public.analytics_silver CASCADE;

-- Then run the migration again
```

## What Changed

### Before (Views - RLS Not Possible)
```sql
CREATE VIEW analytics_gold_orders AS
SELECT ... FROM some_query;

-- ❌ This fails:
ALTER TABLE analytics_gold_orders ENABLE ROW LEVEL SECURITY;
-- ERROR: cannot enable RLS on a view
```

### After (Tables - RLS Working)
```sql
CREATE TABLE analytics_gold_orders (
    id UUID PRIMARY KEY,
    client_id TEXT NOT NULL,
    total_orders INTEGER,
    ...
);

-- ✅ This works:
ALTER TABLE analytics_gold_orders ENABLE ROW LEVEL SECURITY;
CREATE POLICY "..." ON analytics_gold_orders ...;
```

## Data Population

After the migration, the tables will be **empty**. You need to populate them:

### Option A: Analytics API Writes Directly

The Analytics API should process data from BigQuery and INSERT into these tables:

```python
# Example in Analytics API
def refresh_gold_orders(client_id: str):
    # Process data from BigQuery
    metrics = calculate_metrics_from_bigquery(client_id)

    # Insert into gold table
    db.execute(
        """
        INSERT INTO analytics_gold_orders
        (client_id, total_orders, total_revenue, ...)
        VALUES (:client_id, :total_orders, :total_revenue, ...)
        ON CONFLICT (client_id, period_type, period_start)
        DO UPDATE SET ...
        """,
        metrics
    )
```

### Option B: Scheduled Refresh Function

Create a function to refresh from BigQuery foreign tables:

```sql
-- Example: Refresh gold orders from BigQuery
CREATE OR REPLACE FUNCTION refresh_analytics_gold_orders()
RETURNS void AS $$
BEGIN
    -- Aggregate from BigQuery foreign tables
    INSERT INTO analytics_gold_orders (client_id, total_orders, ...)
    SELECT
        client_id,
        COUNT(*) as total_orders,
        ...
    FROM bigquery.client_transactions
    GROUP BY client_id
    ON CONFLICT (client_id, period_type, period_start)
    DO UPDATE SET ...;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Schedule with pg_cron (Supabase supports this)
-- Or call from your Analytics API on a schedule
```

## Quick Reference

| File | Purpose |
|------|---------|
| `20251226_drop_views_create_tables_with_rls.sql` | Main migration - Run this in Supabase |
| `ANALYTICS_SETUP.md` | Architecture and configuration docs |
| `RLS_POLICIES_SUMMARY.md` | RLS policies reference |

## Need Help?

If you encounter issues:

1. Check the error message carefully
2. Verify you're using the correct database password
3. Try the Dashboard SQL Editor method first (most reliable)
4. Check that you're connected to the right project (`haruewffnubdgyofftut`)

## Next Steps After Migration

1. ✅ Apply migration (using one of the 3 options above)
2. ✅ Verify tables exist and RLS is enabled
3. ⏳ Update Analytics API to write to these tables
4. ⏳ Test Dashboard can read from tables
5. ⏳ Implement data refresh logic
