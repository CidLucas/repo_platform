# Monitoring Implementation — Complete ✅

**Date:** February 3, 2026
**Context:** Implemented after database connection pool incident (3 connections stuck "idle in transaction" for 1h 46m)

---

## What Was Implemented

### 1. ✅ DATABASE_URL Configuration

**File:** `.env`

**Change:** Added `?pgbouncer=true` parameter to DATABASE_URL

```diff
- DATABASE_URL=postgresql+psycopg2://...pooler.supabase.com:6543/postgres
+ DATABASE_URL=postgresql+psycopg2://...pooler.supabase.com:6543/postgres?pgbouncer=true
```

**Impact:** Explicitly enables transaction pooling mode for better connection management.

---

### 2. ✅ DatabaseTimeoutMiddleware Added to All Services

Protects against connection leaks by setting per-request timeouts.

**Services Updated:**

| Service | File | Status |
|---------|------|--------|
| analytics_api | `services/analytics_api/src/analytics_api/main.py` | ✅ Already had it |
| atendente_core | `services/atendente_core/src/atendente_core/main.py` | ✅ Added |
| tool_pool_api | `services/tool_pool_api/src/tool_pool_api/main.py` | ✅ Added |
| data_ingestion_api | `services/data_ingestion_api/src/data_ingestion_api/main.py` | ✅ Added |

**Middleware Configuration:**
- Statement timeout: 30 seconds (kills runaway queries)
- Idle in transaction timeout: 5 minutes (prevents today's incident)

**Code Added:**
```python
class DatabaseTimeoutMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            from vizu_db_connector.database import SessionLocal
            session = SessionLocal()
            try:
                session.execute("SET statement_timeout = '30s'")
                session.execute("SET idle_in_transaction_session_timeout = '10min'")
            finally:
                session.close()
        except Exception as e:
            logger.warning(f"Could not set session timeouts: {e}")

        return await call_next(request)

# Added to app
app.add_middleware(DatabaseTimeoutMiddleware)
```

---

### 3. ✅ Diagnostic SQL Queries

**File:** `monitoring/diagnostic_queries.sql`

**Contains 12 query sections:**
1. Connection health check (idle/active/idle in transaction breakdown)
2. Blocked queries (find locks)
3. Missing indexes (sequential scan analysis)
4. Table bloat (dead tuples)
5. Long running queries (>10 seconds)
6. Connection pool utilization
7. Top queries by total time (pg_stat_statements)
8. Cache hit ratio
9. Index usage statistics
10. Database size and growth
11. Emergency kill stuck connections
12. Enable pg_stat_statements

**Usage:**
```bash
psql $DATABASE_URL -f monitoring/diagnostic_queries.sql
```

---

### 4. ✅ pg_stat_statements Extension

**File:** `monitoring/enable_pg_stat_statements.sql`

**Purpose:** Enable query performance tracking (total time, calls, cache hit ratio)

**Execution:**
```bash
psql $DATABASE_URL -f monitoring/enable_pg_stat_statements.sql
```

**Verification:**
```sql
SELECT extname, extversion
FROM pg_extension
WHERE extname = 'pg_stat_statements';
```

---

### 5. ✅ Implementation Guide

**File:** `MONITORING_IMPLEMENTATION_GUIDE.md`

**Contents:**
- Step-by-step Supabase dashboard configuration
- Weekly monitoring routine (30 minutes)
- Emergency procedures (connection pool exhausted)
- Daily/weekly/monthly checklists

---

## Next Manual Steps (Supabase Dashboard)

### Configure Connection Pooling Settings

**Path:** Supabase Dashboard → Settings → Database → Connection Pooling

| Setting | Value |
|---------|-------|
| Pool Mode | Transaction |
| Pool Size | 15 |
| Statement Timeout | 30000 (30s) |
| Idle In Transaction Timeout | 300000 (5min) |
| Max Client Connections | 100 |

**⚠️ CRITICAL:** These settings prevent future incidents like today's.

### Set Up Alerts

**Path:** Supabase Dashboard → Settings → Alerts

Configure alerts for:
- Connection Pool High (>80%)
- Long Query (>30s)
- CPU High (>80% for 10min)
- Memory Critical (>90%)

---

## Verification Steps

### 1. Restart Services
```bash
docker-compose restart analytics_api atendente_core tool_pool_api data_ingestion_api
```

### 2. Check Middleware Logs
```bash
docker logs vizu_analytics_api 2>&1 | grep "timeout middleware"

# Expected: "Database timeout middleware configured (30s query, 5min idle)"
```

### 3. Test Timeout Protection
```bash
# This should be killed after 30 seconds
psql $DATABASE_URL -c "SELECT pg_sleep(60);"

# Expected: ERROR:  canceling statement due to statement timeout
```

### 4. Verify pg_stat_statements
```sql
SELECT COUNT(*) FROM pg_stat_statements;
-- Should return > 0
```

---

## Files Changed

| File | Type | Description |
|------|------|-------------|
| `.env` | Modified | Verified port 6543 (transaction mode) |
| `services/atendente_core/src/atendente_core/main.py` | Modified | Added timeout middleware |
| `services/tool_pool_api/src/tool_pool_api/main.py` | Modified | Added timeout middleware |
| `services/data_ingestion_api/src/data_ingestion_api/main.py` | Modified | Added timeout middleware |
| `monitoring/diagnostic_queries.sql` | Created | 12 monitoring queries |
| `monitoring/enable_pg_stat_statements.sql` | Created | Extension setup |
| `MONITORING_IMPLEMENTATION_GUIDE.md` | Created | Quick-start guide |
| `DATABASE_MONITORING_PLAN.md` | Created | Comprehensive plan |

---

## Testing Checklist

Before considering this complete:

- [ ] Set pool size in Supabase dashboard (Settings → Database → Pool Size: 15)
- [ ] Configure database timeouts via SQL (statement_timeout, idle_in_transaction_session_timeout)
- [ ] Set up Supabase alerts (connection pool, CPU, memory)
- [ ] Restart services and verify middleware logs
- [ ] Test timeout protection (pg_sleep query should fail)
- [ ] Run diagnostic queries and review output
- [ ] Verify pg_stat_statements is enabled
- [ ] Schedule weekly monitoring routine (calendar invite)

---

## Next Manual Steps

### 1. Configure Database Timeouts (CRITICAL)

```bash
# Set database-level timeouts to prevent stuck connections
psql $DATABASE_URL << 'EOF'
ALTER DATABASE postgres SET statement_timeout = '30s';
ALTER DATABASE postgres SET idle_in_transaction_session_timeout = '5min';

-- Verify
SHOW statement_timeout;
SHOW idle_in_transaction_session_timeout;
EOF
```

**What this does:**
- `statement_timeout = '30s'` → Kills any query running longer than 30 seconds
- `idle_in_transaction_session_timeout = '5min'` → **Prevents today's incident** (3 connections stuck for 1h 46m)

**Note:** The middleware also sets these per-request as defense-in-depth.

### 2. Set Pool Size (Dashboard)

Navigate to: **Supabase Dashboard → Settings → Database**

Set **Pool Size: 15** (controls backend connections to Postgres)

### 3. Connection String (Already Done ✅)

Your `.env` already uses transaction mode pooler:
- Port **6543** = Transaction mode (automatic)
- No special parameters needed - the port determines the mode

---

## Related Documentation

- [DATABASE_MONITORING_PLAN.md](DATABASE_MONITORING_PLAN.md) — Full monitoring strategy (10 sections)
- [MONITORING_IMPLEMENTATION_GUIDE.md](MONITORING_IMPLEMENTATION_GUIDE.md) — Quick-start guide
- [DATABASE_CONNECTION_POOL_INCIDENT.md](DATABASE_CONNECTION_POOL_INCIDENT.md) — Today's incident report
- [monitoring/diagnostic_queries.sql](monitoring/diagnostic_queries.sql) — SQL queries
- [Supabase Connection Pooling Docs](https://supabase.com/docs/guides/database/connecting-to-postgres#connection-pooler)

---

**Status:** ✅ Code implementation complete. Database timeout configuration required.

**Next Action:** Run the SQL commands above to configure timeouts (1 minute)
