# Monitoring Implementation Guide

Quick-start guide for implementing the database monitoring plan from [DATABASE_MONITORING_PLAN.md](DATABASE_MONITORING_PLAN.md).

## Status: ✅ Code Changes Applied

- ✅ DATABASE_URL updated with `?pgbouncer=true` parameter (.env)
- ✅ DatabaseTimeoutMiddleware added to:
  - analytics_api
  - atendente_core
  - tool_pool_api
  - data_ingestion_api
- ✅ Diagnostic SQL queries created: [monitoring/diagnostic_queries.sql](monitoring/diagnostic_queries.sql)

---

## Immediate Next Steps (10 minutes)

### 1. Enable pg_stat_statements Extension

```bash
# Connect to Supabase database
psql $DATABASE_URL

# Enable extension
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

# Verify
SELECT * FROM pg_available_extensions WHERE name = 'pg_stat_statements';
```

### 2. Configure Supabase Pooler Settings

**A. Pool Size (Dashboard Setting)**

Navigate to: **Supabase Dashboard → Settings → Database**

Set **Pool Size: 15** (controls backend connections to Postgres)

**B. Connection String (Already Configured)**

Your `.env` already uses the correct connection string:
- Port **6543** = Transaction mode (automatic, no parameter needed)
- The port number alone determines the pooler mode

**C. Timeout Configuration (Database Level)**

Timeouts are set via Postgres ALTER DATABASE command:

```bash
psql $DATABASE_URL << 'EOF'
-- Statement timeout: kills queries > 30s
ALTER DATABASE postgres SET statement_timeout = '30s';

-- Idle transaction timeout: kills stuck transactions > 5min
ALTER DATABASE postgres SET idle_in_transaction_session_timeout = '5min';

-- Verify settings
SHOW statement_timeout;
SHOW idle_in_transaction_session_timeout;
EOF
```

**Note:** These settings apply database-wide. Our middleware also sets them per-request as defense-in-depth.

### 3. Set Up Alerts

Navigate to: **Supabase Dashboard → Settings → Alerts**

**Configure these alerts:**

| Alert Name | Condition | Threshold | Integration |
|------------|-----------|-----------|-------------|
| Connection Pool High | Active connections / Pool size | > 80% | Email + Slack |
| Long Query | Query duration | > 30s | Email |
| CPU High | CPU utilization | > 80% for 10min | Email + Slack |
| Memory Critical | Memory usage | > 90% | Email |

### 4. Verify Middleware Works

```bash
# Restart services to load new middleware
docker-compose restart analytics_api atendente_core tool_pool_api data_ingestion_api

# Check logs for confirmation message
docker logs vizu_analytics_api 2>&1 | grep "timeout middleware"

# Expected output:
# "Database timeout middleware configured (30s query, 5min idle)"
```

### 5. Test Timeout Protection

```bash
# This query should be killed after 30 seconds
psql $DATABASE_URL -c "SELECT pg_sleep(60);"

# Expected: ERROR:  canceling statement due to statement timeout
```

---

## Weekly Monitoring Routine (30 minutes)

### 1. Run Diagnostic Queries

```bash
# Execute all diagnostic queries
psql $DATABASE_URL -f monitoring/diagnostic_queries.sql > /tmp/diagnostics_$(date +%Y%m%d).txt

# Review output
cat /tmp/diagnostics_$(date +%Y%m%d).txt
```

**Key things to check:**
- ❌ Any "idle in transaction" connections > 1 minute
- ❌ Blocked queries waiting on locks
- ❌ Tables with dead_tup_percent > 20%
- ❌ Cache hit ratio < 95%
- ✅ Connection pool utilization < 80%

### 2. Check Pooler Logs

Navigate to: **Supabase Dashboard → Logs → Pooler Logs**

**Look for these errors:**
- `Max client connections reached` → Investigate app connection handling
- `idle_in_transaction_session_timeout` → Review app error handling
- `statement timeout` → Expected; review slow query patterns

### 3. Review Query Performance

Navigate to: **Supabase Dashboard → Database → Query Performance**

**Check top 10 queries by:**
1. Total execution time (identify expensive queries)
2. Number of calls (find hot paths)
3. Average execution time (slow queries)

**Action:** Add indexes or optimize queries > 1 second average.

---

## Emergency: Connection Pool Exhausted

**Symptoms:**
- Dashboard errors: "Max client connections reached"
- API requests timing out
- All services unresponsive

**Diagnosis:**
```sql
-- Find stuck connections
SELECT pid, state, NOW() - state_change as idle_duration, query
FROM pg_stat_activity
WHERE state = 'idle in transaction'
ORDER BY state_change;
```

**Fix:**
```sql
-- Terminate stuck connections (replace PIDs)
SELECT pg_terminate_backend(359001);
SELECT pg_terminate_backend(359027);

-- Or kill all idle in transaction > 5min
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle in transaction'
  AND NOW() - state_change > INTERVAL '5 minutes';
```

**Verify:**
```sql
-- Check for 0 stuck connections
SELECT COUNT(*)
FROM pg_stat_activity
WHERE state = 'idle in transaction';
```

---

## Monitoring Checklist

### Daily (5 minutes)
- [ ] Check Supabase Dashboard → Reports → Database
  - [ ] CPU/Memory graphs look normal
  - [ ] Connection pool < 80%
- [ ] Check Pooler Logs for errors
- [ ] Review any alerts in email/Slack

### Weekly (30 minutes)
- [ ] Run diagnostic SQL queries
- [ ] Review Query Performance dashboard
- [ ] Check for blocked queries
- [ ] Verify autovacuum ran on large tables
- [ ] Review application logs for database errors

### Monthly (2 hours)
- [ ] Full performance review with team
- [ ] Index optimization session
- [ ] Capacity planning (project growth)
- [ ] Update alert thresholds if needed

---

## Grafana Dashboards (Optional)

Navigate to: **Supabase Dashboard → Reports → Database → View in Grafana**

**Key metrics to watch:**
- Connection pool utilization over time
- Query latency percentiles (p50, p95, p99)
- Transaction commit/rollback rate
- Replication lag (if using read replicas)

---

## Reference

- Full plan: [DATABASE_MONITORING_PLAN.md](DATABASE_MONITORING_PLAN.md)
- Diagnostic queries: [monitoring/diagnostic_queries.sql](monitoring/diagnostic_queries.sql)
- Incident report: [DATABASE_CONNECTION_POOL_INCIDENT.md](DATABASE_CONNECTION_POOL_INCIDENT.md)
- Supabase docs: https://supabase.com/docs/guides/database/supavisor

---

**Next Action:** Configure Supabase Dashboard settings (Step 2 above)
