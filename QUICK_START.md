# Analytics Setup - Quick Start Guide

## 🚀 3-Step Setup

### Step 1: Run SQL in Supabase Dashboard (5 minutes)

1. Open [Supabase Dashboard](https://supabase.com/dashboard)
2. Select project: `haruewffnubdgyofftut`
3. Go to **SQL Editor** → **New Query**
4. Copy entire contents of `COPY_PASTE_TO_SUPABASE.sql`
5. Paste and click **Run**

**✅ Expected Result:** "Success. No rows returned"

### Step 2: Verify Tables Were Created (1 minute)

Run this query in Supabase SQL Editor:

```sql
SELECT tablename, rowsecurity FROM pg_tables WHERE tablename LIKE 'analytics_%';
```

**✅ Expected Result:** 5 tables with `rowsecurity = t`

### Step 3: Test Analytics API (1 minute)

```bash
curl http://localhost:8004/health
# ✅ Should return: {"status":"ok",...}

curl http://localhost:8004/api/dashboard/home_gold
# ✅ Should return: {} (empty but no error)
```

## 📊 What You Just Created

5 tables with RLS (Row Level Security):

| Table | Purpose |
|-------|---------|
| `analytics_gold_orders` | Aggregated order metrics |
| `analytics_gold_products` | Product performance |
| `analytics_gold_customers` | Customer analytics |
| `analytics_gold_suppliers` | Supplier metrics |
| `analytics_silver` | Cached BigQuery data |

## 🔒 Security Model

- **Dashboard Users** (authenticated): Can only SELECT their own `client_id` data
- **Analytics API** (service_role): Can INSERT/UPDATE/DELETE all data

## 📁 Files Reference

| File | Use When |
|------|----------|
| `COPY_PASTE_TO_SUPABASE.sql` | ⭐ START HERE - Easiest method |
| `MIGRATION_INSTRUCTIONS.md` | Need detailed instructions |
| `ANALYTICS_SETUP.md` | Understanding architecture |
| `RLS_POLICIES_SUMMARY.md` | Security reference |

## ⚠️ Troubleshooting

### Problem: "cannot create index on relation"

**Cause:** Still have views with the same name

**Fix:**
```sql
DROP VIEW IF EXISTS public.analytics_gold_orders CASCADE;
-- Then run the migration again
```

### Problem: `supabase db push` fails with password error

**Fix:** Use Supabase Dashboard SQL Editor instead (recommended)

### Problem: Analytics API returns "relation does not exist"

**Fix:** Run the SQL migration first (Step 1 above)

### Problem: Empty results from gold endpoints

**Cause:** Tables are empty (expected initially)

**Fix:** Populate data via Analytics API write operations

## 🎯 Next Steps

After setup:

1. ✅ Tables created with RLS
2. ⏳ Configure Analytics API to write metrics to gold tables
3. ⏳ Implement data refresh logic (BigQuery → Gold tables)
4. ⏳ Test Dashboard displays metrics correctly

## 🆘 Need Help?

Check these in order:
1. `MIGRATION_INSTRUCTIONS.md` - Detailed steps
2. Supabase SQL Editor error messages
3. Analytics API logs: `docker logs analytics_api`
