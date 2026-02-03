# Supabase Connection Pool Configuration Guide

## The Right Way: Use Supabase's Built-In Features

Instead of running custom monitoring services, **configure Supabase's native pooler (Supavisor)** to handle connection management automatically.

---

## 1. Configure Supabase Pooler Settings

### Access Supabase Dashboard

1. Go to your project: https://supabase.com/dashboard/project/YOUR_PROJECT_ID
2. Navigate to: **Settings → Database → Connection Pooling**

### Recommended Configuration

```
Pool Mode: Transaction
Default Pool Size: 15
Statement Timeout: 30s (30000ms)
Idle In Transaction Timeout: 5min (300000ms)
Max Client Connections: 100
```

### What Each Setting Does

**Pool Mode: Transaction**
- ✅ Connection returned to pool immediately after each SQL statement
- ✅ Most efficient for API workloads (FastAPI, REST)
- ✅ Prevents connections from being held during frontend delays
- ❌ Can't use: prepared statements, LISTEN/NOTIFY, cursors
- 📌 **Use this for analytics_api**

**Pool Mode: Session** (alternative)
- ✅ Connection held for entire client session
- ✅ Supports all PostgreSQL features
- ❌ More vulnerable to connection leaks
- 📌 Use only if you need prepared statements/cursors

**Pool Size: 15**
- Number of actual PostgreSQL connections
- Default is good for most workloads
- Increase if you see "connection limit reached" errors

**Statement Timeout: 30s**
- Kills any query running longer than 30 seconds
- ✅ **Critical protection** against runaway queries
- Frontend queries should complete < 5s

**Idle In Transaction Timeout: 5min**
- Auto-rollback transactions idle > 5 minutes
- ✅ **Critical protection** against stuck dashboard queries
- Today's incident would've been prevented with this

**Max Client Connections: 100**
- Number of concurrent API requests that can connect
- Supavisor queues requests if limit exceeded
- Increase if you have high traffic

---

## 2. Update Your DATABASE_URL

Supabase provides 3 connection strings:

### ❌ Don't Use: Direct Connection
```bash
# Direct to PostgreSQL (bypasses pooler)
postgresql://postgres.[project].supabase.co:5432/postgres
```
**Problem:** No timeout protection, limited connections (15 max)

### ✅ Use: Transaction Mode Pooler
```bash
# Connection string from Supabase Dashboard
postgresql://postgres.[project]:[password]@aws-0-us-east-1.pooler.supabase.com:6543/postgres?pgbouncer=true
```
**Benefits:** Statement timeout enforced, efficient connection reuse

### 🔄 Alternative: Session Mode Pooler
```bash
# If you need prepared statements (not recommended for API)
postgresql://postgres.[project]:[password]@aws-0-us-east-1.pooler.supabase.com:5432/postgres
```

### Update .env File

```bash
# .env
DATABASE_URL=postgresql://postgres.[YOUR_PROJECT]:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres?pgbouncer=true
```

**How to find your connection string:**
1. Supabase Dashboard → Settings → Database
2. Copy **Connection pooling** → **Transaction mode** URL
3. Replace `[YOUR-PASSWORD]` with your actual password

---

## 3. Application-Level Protection (Keep This)

The middleware in [analytics_api/main.py](services/analytics_api/src/analytics_api/main.py) provides **defense in depth**:

```python
class DatabaseTimeoutMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        session = SessionLocal()
        session.execute("SET statement_timeout = '30s'")
        session.execute("SET idle_in_transaction_session_timeout = '5min'")
        session.close()
        return await call_next(request)
```

**Why keep this:**
- ✅ Works even if Supabase settings fail to apply
- ✅ Per-request override (can set longer timeout for specific endpoints)
- ✅ Logged in application logs (easier debugging)
- ✅ Defense in depth (multiple layers of protection)

---

## 4. Verify Configuration

### Check Pooler is Active

```bash
# Your current DATABASE_URL should contain "pooler.supabase"
echo $DATABASE_URL | grep pooler

# Expected: postgresql://...@aws-0-us-east-1.pooler.supabase.com:6543/...
```

### Test Statement Timeout

```sql
-- Should fail after 30 seconds
SELECT pg_sleep(60);

-- Expected error: "ERROR: canceling statement due to statement timeout"
```

### Test Idle Transaction Timeout

```sql
-- Start transaction but don't finish
BEGIN;
SELECT 1;
-- Wait 5+ minutes without COMMIT

-- Expected: "ERROR: terminating connection due to idle-in-transaction timeout"
```

### Monitor Active Connections

```sql
-- Check how many connections are active
SELECT
    COUNT(*) as total_connections,
    COUNT(*) FILTER (WHERE state = 'active') as active,
    COUNT(*) FILTER (WHERE state = 'idle') as idle,
    COUNT(*) FILTER (WHERE state = 'idle in transaction') as stuck
FROM pg_stat_activity
WHERE pid != pg_backend_pid();
```

**Healthy state:**
- Total connections: 5-15 (well within pool size)
- Stuck: 0 (no idle transactions)

---

## 5. Supabase Dashboard Monitoring

### Connection Pool Health

**Path:** Project → Database → Connection pooling → Metrics

**What to watch:**
- **Connection pool utilization:** Should stay < 80%
- **Wait time:** Should be < 1ms
- **Connection errors:** Should be 0

### Query Performance

**Path:** Project → Database → Query Performance

**Red flags:**
- Queries taking > 5 seconds
- High `pg_stat_activity` wait events
- "Lock wait" or "Client read" wait events

### Set Up Alerts

**Path:** Project → Settings → Alerts

**Recommended alerts:**
1. **Connection pool > 80% utilized** → Email/Slack
2. **Query duration > 30s** → Email/Slack
3. **Idle in transaction > 1 minute** → Email/Slack

---

## 6. Manual Intervention (Emergency Only)

If Supabase pooler fails to kill stuck connections:

### View Stuck Connections

```sql
SELECT
    pid,
    usename,
    application_name,
    state,
    NOW() - state_change AS idle_duration,
    query
FROM pg_stat_activity
WHERE state = 'idle in transaction'
  AND NOW() - state_change > INTERVAL '5 minutes'
ORDER BY state_change;
```

### Kill Stuck Connection

```sql
-- Replace <pid> with actual PID from above query
SELECT pg_terminate_backend(<pid>);
```

### One-Time Cleanup Script

If you need to manually clean up (saved for emergency use):

```bash
# Run locally with your DATABASE_URL
python ferramentas/monitor_kill_idle_connections.py
```

**Note:** This is a **last resort** - Supabase pooler should handle it automatically.

---

## Summary: What You Need to Do

### Required (Do Now)

1. ✅ **Update DATABASE_URL** to use Supabase pooler (transaction mode)
   ```bash
   # .env
   DATABASE_URL=postgresql://...@pooler.supabase.com:6543/...?pgbouncer=true
   ```

2. ✅ **Configure Supabase timeouts** in dashboard:
   - Statement timeout: 30s
   - Idle in transaction timeout: 5min

3. ✅ **Keep application middleware** (already done)
   - Provides defense in depth
   - No changes needed

4. ✅ **Set up Supabase alerts**
   - Connection pool > 80%
   - Query duration > 30s

### Optional (Nice to Have)

- 📊 Monitor Supabase connection pool metrics weekly
- 🔔 Add Slack webhook for critical alerts
- 📝 Document your specific query timeout requirements

### NOT Needed

- ❌ Custom Docker monitoring service
- ❌ Cron jobs to kill connections
- ❌ Additional connection pool managers

**Supabase handles everything natively!**

---

## Troubleshooting

### "Connection pool exhausted"

**Check:**
```sql
SELECT COUNT(*) FROM pg_stat_activity WHERE pid != pg_backend_pid();
```

**Fix:**
1. Increase pool size in Supabase dashboard (Settings → Database → Connection Pooling)
2. Check for connection leaks in application (ensure `.close()` is called)
3. Verify DATABASE_URL uses pooler (contains `pooler.supabase.com`)

### "Statement timeout" errors on legitimate long queries

**Option 1:** Override timeout for specific endpoint
```python
@app.post("/ingest/recompute")
async def recompute():
    session = SessionLocal()
    session.execute("SET statement_timeout = '10min'")  # Allow 10 min
    # ... rest of endpoint
```

**Option 2:** Use async tasks for long operations
```python
# Queue long task in background worker (Celery, etc.)
# API returns immediately with job_id
```

### "Idle in transaction timeout" killing valid sessions

**Check:** Are you using `BEGIN` without `COMMIT`?

**Fix:** Always use context managers:
```python
with PostgresRepository() as repo:
    # Transaction auto-commits on exit
    repo.do_work()
```

---

## Migration Checklist

- [ ] Update DATABASE_URL to pooler connection string
- [ ] Set statement_timeout = 30s in Supabase
- [ ] Set idle_in_transaction_session_timeout = 5min in Supabase
- [ ] Verify middleware is active in analytics_api
- [ ] Set up Supabase alerts
- [ ] Remove Docker monitor service (already done)
- [ ] Test with `SELECT pg_sleep(60)` (should timeout)
- [ ] Monitor for 1 week, adjust timeouts if needed

---

## Related Files

- [services/analytics_api/src/analytics_api/main.py](services/analytics_api/src/analytics_api/main.py) - Application middleware
- [DATABASE_CONNECTION_POOL_INCIDENT.md](DATABASE_CONNECTION_POOL_INCIDENT.md) - Original incident
- [Supabase Connection Pooling Docs](https://supabase.com/docs/guides/database/connecting-to-postgres#connection-pooler)

---

**Status:** ✅ Ready to implement. Update DATABASE_URL and configure Supabase dashboard settings.
