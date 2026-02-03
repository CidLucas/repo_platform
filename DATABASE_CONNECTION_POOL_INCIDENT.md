# Database Connection Pool Incident - Resolved

**Date:** 2026-02-03
**Duration:** ~2 hours (15:10 - 16:57)
**Impact:** All database reads/writes timing out

---

## Symptoms

- ✗ All Supabase queries timing out (reads and writes)
- ✗ Only 1 pooler connection being used
- ✗ High memory usage constant
- ✗ Low CPU usage
- ✗ Shared pooler at max connections (8)
- ✗ Migration attempts failing with timeout

---

## Root Cause

**3 idle-in-transaction connections** from Supabase dashboard frontend:

```sql
-- PIDs: 359001, 359027, 359629
-- Status: "idle in transaction" for 1h 46m
-- Started: 2026-02-03 15:10:39-43
-- Locks held: AccessShareLock on dim_product, dim_customer, fact_sales, v_regional, v_time_series
```

### What Happened

1. **15:10:** Dashboard frontend initiated 3 analytics queries
2. **Queries completed** but **transactions never closed** (likely network issue or browser tab crash)
3. **Locks held** for 1h 46m blocking ALL:
   - New connections (pool exhausted)
   - DDL operations (CREATE/DROP VIEW)
   - Long-running reads (waiting on locks)
   - Writes to locked tables

### Why Connection Pool Exhausted

- **PostgreSQL transaction isolation:** Even read-only queries hold `AccessShareLock` until transaction commits/rollsback
- **Frontend failure:** Browser/network didn't send COMMIT or disconnect
- **Supabase pooler:** Held connections waiting for transaction completion
- **Cascading effect:** New connections queued, eventually timing out

---

## Resolution

### 1. Diagnostic Queries Used

```sql
-- Find long-running/stuck transactions
SELECT pid, usename, state, wait_event,
       NOW() - query_start AS duration,
       LEFT(query, 100) AS query_preview
FROM pg_stat_activity
WHERE state != 'idle' AND pid != pg_backend_pid()
ORDER BY query_start;

-- Check locks held
SELECT l.pid, l.mode, l.granted, c.relname AS table_name
FROM pg_locks l
JOIN pg_class c ON l.relation = c.oid
JOIN pg_stat_activity a ON l.pid = a.pid
WHERE l.pid IN (359001, 359027, 359629);
```

### 2. Fix Applied

```sql
-- Terminate stuck connections (safe - no data loss, just aborts reads)
SELECT pg_terminate_backend(359001),
       pg_terminate_backend(359027),
       pg_terminate_backend(359629);
```

**Result:** ✅ All 3 connections killed, locks released, pool recovered

### 3. Post-Recovery Health Check

```sql
SELECT
    COUNT(*) FILTER (WHERE state = 'idle in transaction') as stuck,
    COUNT(*) FILTER (WHERE state = 'active') as active,
    COUNT(*) FILTER (WHERE state = 'idle') as idle,
    COUNT(*) as total
FROM pg_stat_activity;
```

**Result:**
- ✅ 0 stuck transactions
- ✅ 15 total connections (healthy pool)
- ✅ 7 idle, 0 active (normal state)

---

## Successfully Applied After Recovery

### Regional View Update

**Applied:** [migrations/fix_regional_view_with_regions.sql](migrations/fix_regional_view_with_regions.sql)

```sql
DROP VIEW IF EXISTS analytics_v2.v_regional CASCADE;
CREATE VIEW analytics_v2.v_regional AS ...
```

**Changes:**
- ❌ Removed: `region_name` (state code), `region_type` (useless)
- ✅ Added: `state` (UF), `region` (Norte/Nordeste/Centro-Oeste/Sudeste/Sul)

**Verification:**
```sql
SELECT state, region, total FROM analytics_v2.v_regional
WHERE client_id = 'e0e9c949...' AND chart_type = 'clientes_por_regiao'
ORDER BY total DESC LIMIT 10;

-- Result sample:
-- SP → Sudeste (28.77%)
-- PR → Sul (14.18%)
-- RJ → Sudeste (10.07%)
-- PE → Nordeste (8.47%)
```

✅ **Working perfectly** with Brazilian region mapping

---

## Prevention Strategies

### Short-Term (Immediate) ✅

1. **Supabase Pooler Configuration (PRIMARY SOLUTION):**
   - Go to: Supabase Dashboard → Settings → Database → Connection Pooling
   - Set **Pool Mode: Transaction** (efficient connection reuse)
   - Set **Statement Timeout: 30s** (kills long queries)
   - Set **Idle In Transaction Timeout: 5min** (auto-rollback stuck transactions)
   - Update DATABASE_URL to use pooler: `...@pooler.supabase.com:6543/...?pgbouncer=true`
   - **See:** [SUPABASE_POOLER_CONFIGURATION.md](SUPABASE_POOLER_CONFIGURATION.md) for complete guide

2. **Application middleware (defense in depth):**
   ```python
   # services/analytics_api/src/analytics_api/main.py
   class DatabaseTimeoutMiddleware(BaseHTTPMiddleware):
       async def dispatch(self, request: Request, call_next):
           session = SessionLocal()
           session.execute("SET statement_timeout = '30s'")
           session.execute("SET idle_in_transaction_session_timeout = '5min'")
           session.close()
           return await call_next(request)
   ```

3. **Supabase Dashboard Alerts:**
   - Settings → Alerts → Add alert
   - Alert on: Connection pool > 80%, Query duration > 30s

### Medium-Term (This Week)

4. **Monitor Supabase metrics:**
   - Database → Connection pooling → Check utilization weekly
   - Database → Query Performance → Identify slow queries

5. **Dashboard query optimization:**
   - Move to materialized views (refresh every 5 min)
   - Implement query result caching (Redis)
   - Add query timeouts in frontend (30s max)

6. **Code review for connection leaks:**
   ```python
   # Always use context managers
   with PostgresRepository() as repo:
       repo.do_work()
   # Connection auto-closed
   ```

### Long-Term (Next Sprint)

7. **Read replicas** (if high dashboard traffic):
   - Upgrade Supabase plan to get read replicas
   - Point dashboard queries to replica

8. **Circuit breaker pattern:**
   ```python
   # Fail fast if DB unavailable
   if not health_check_db():
       raise ServiceUnavailableError("Database unavailable")
   ```

9. **Graceful degradation:**
   - Cache last successful dashboard query
   - Show stale data with warning if DB unavailable

---

## Key Learnings

1. **Use Supabase's native pooler:**
   - Built-in timeout enforcement
   - Connection reuse (transaction mode)
   - Monitoring and alerts included
   - No custom services needed

2. **"Idle in transaction" is dangerous:**
   - Even read-only queries hold locks until COMMIT
   - Frontend crashes don't auto-rollback transactions
   - Can exhaust connection pool silently

3. **High memory + low CPU = stuck connections:**
   - Memory: Connections held in pool + query buffers
   - Low CPU: Nothing actually processing, just waiting

4. **Dashboard queries need special handling:**
   - Use short timeouts (30s max)
   - Prefer materialized views over live aggregations
   - Implement read replicas for analytics

5. **Monitoring is critical:**
   - Use Supabase dashboard metrics (built-in)
   - Alert on connection pool > 80%
   - Track query performance trends

---

## Related Documentation

- [SUPABASE_POOLER_CONFIGURATION.md](SUPABASE_POOLER_CONFIGURATION.md) - **PRIMARY GUIDE** for prevention
- [DATA_QUALITY_FIXES_FINAL_POLISHING.md](DATA_QUALITY_FIXES_FINAL_POLISHING.md) - Changes applied after recovery
- [migrations/fix_regional_view_with_regions.sql](migrations/fix_regional_view_with_regions.sql) - Regional mapping migration
- [Supabase Connection Pooling Docs](https://supabase.com/docs/guides/database/connecting-to-postgres#connection-pooler)

---

## Diagnostic Commands Reference

```bash
# Check Supabase dashboard connection stats
# Settings → Database → Connection pooling

# Monitor connection pool in real-time
watch -n 5 "psql $DATABASE_URL -c \"
SELECT state, COUNT(*) FROM pg_stat_activity
GROUP BY state;
\""

# Find queries holding locks
psql $DATABASE_URL -c "
SELECT l.pid, a.usename, c.relname, l.mode, a.query_start
FROM pg_locks l
JOIN pg_stat_activity a ON l.pid = a.pid
JOIN pg_class c ON l.relation = c.oid
WHERE l.granted AND a.state != 'idle'
ORDER BY a.query_start;
"

# Kill stuck transaction (replace PID)
psql $DATABASE_URL -c "SELECT pg_terminate_backend(359001);"
```

