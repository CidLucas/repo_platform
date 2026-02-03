-- Diagnostic SQL Queries for Database Monitoring
-- Run these queries weekly or when investigating performance issues
-- Based on: DATABASE_MONITORING_PLAN.md

-- ================================================
-- 1. CONNECTION HEALTH CHECK
-- ================================================
-- Shows current connection state breakdown
-- Expected: idle (5-10), active (1-3), idle in transaction (0)

SELECT
    state,
    COUNT(*) as count,
    MAX(EXTRACT(EPOCH FROM (now() - state_change)))::int as max_seconds
FROM pg_stat_activity
WHERE datname = current_database()
  AND pid != pg_backend_pid()
GROUP BY state
ORDER BY count DESC;

-- ================================================
-- 2. BLOCKED QUERIES (LOCKS)
-- ================================================
-- Find queries waiting on locks
-- If returns rows: investigate blocking query and optimize or kill it

SELECT
    blocked.pid AS blocked_pid,
    blocked.usename AS blocked_user,
    blocking.pid AS blocking_pid,
    blocking.usename AS blocking_user,
    blocked.query AS blocked_query,
    blocking.query AS blocking_query,
    EXTRACT(EPOCH FROM (now() - blocked.state_change))::int as blocked_seconds
FROM pg_stat_activity AS blocked
JOIN pg_stat_activity AS blocking
    ON blocking.pid = ANY(pg_blocking_pids(blocked.pid))
WHERE blocked.datname = current_database();

-- ================================================
-- 3. MISSING INDEXES (SEQUENTIAL SCANS)
-- ================================================
-- Tables with high sequential scans may need indexes
-- High seq_tup_read indicates missing indexes

SELECT
    schemaname,
    tablename,
    seq_scan,
    seq_tup_read,
    idx_scan,
    CASE
        WHEN seq_scan > 0 THEN (seq_tup_read / seq_scan)::bigint
        ELSE 0
    END AS avg_seq_tup_read,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS table_size
FROM pg_stat_user_tables
WHERE seq_scan > 0
  AND schemaname = 'analytics_v2'
ORDER BY seq_tup_read DESC
LIMIT 10;

-- ================================================
-- 4. TABLE BLOAT (DEAD TUPLES)
-- ================================================
-- Check for bloated tables (wasted space)
-- If dead_tup_percent > 20%: Run VACUUM ANALYZE

SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    n_dead_tup,
    n_live_tup,
    ROUND(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_tup_percent,
    last_vacuum,
    last_autovacuum
FROM pg_stat_user_tables
WHERE schemaname = 'analytics_v2'
  AND n_dead_tup > 1000
ORDER BY n_dead_tup DESC;

-- ================================================
-- 5. LONG RUNNING QUERIES
-- ================================================
-- Find queries running longer than 10 seconds

SELECT
    pid,
    usename,
    state,
    EXTRACT(EPOCH FROM (now() - query_start))::int as seconds,
    LEFT(query, 100) as query_preview
FROM pg_stat_activity
WHERE state != 'idle'
  AND datname = current_database()
  AND EXTRACT(EPOCH FROM (now() - query_start)) > 10
ORDER BY seconds DESC;

-- ================================================
-- 6. CONNECTION POOL UTILIZATION
-- ================================================
-- Calculate connection pool usage (assumes 15 connection limit)

SELECT
    COUNT(*) FILTER (WHERE state = 'active') as active_connections,
    COUNT(*) FILTER (WHERE state = 'idle') as idle_connections,
    COUNT(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction,
    COUNT(*) as total_connections,
    15 as pool_limit,
    ROUND((COUNT(*) * 100.0 / 15), 2) as utilization_percent
FROM pg_stat_activity
WHERE datname = current_database()
  AND pid != pg_backend_pid();

-- ================================================
-- 7. TOP QUERIES BY TOTAL TIME (pg_stat_statements)
-- ================================================
-- Requires pg_stat_statements extension
-- Run: CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

SELECT
    LEFT(query, 100) as query_preview,
    calls,
    ROUND(total_exec_time::numeric, 2) as total_time_ms,
    ROUND((total_exec_time / calls)::numeric, 2) as avg_time_ms,
    ROUND((100.0 * shared_blks_hit / NULLIF(shared_blks_hit + shared_blks_read, 0))::numeric, 2) as cache_hit_ratio
FROM pg_stat_statements
WHERE userid = (SELECT usesysid FROM pg_user WHERE usename = 'postgres')
  AND query NOT LIKE '%pg_stat_statements%'
ORDER BY total_exec_time DESC
LIMIT 20;

-- ================================================
-- 8. CACHE HIT RATIO (DATABASE)
-- ================================================
-- Cache hit ratio should be > 95%
-- If < 90%: Add more RAM or optimize queries

SELECT
    SUM(heap_blks_read) as heap_read,
    SUM(heap_blks_hit) as heap_hit,
    ROUND(100.0 * SUM(heap_blks_hit) / NULLIF(SUM(heap_blks_hit) + SUM(heap_blks_read), 0), 2) as cache_hit_ratio
FROM pg_statio_user_tables;

-- ================================================
-- 9. INDEX USAGE STATISTICS
-- ================================================
-- Identify unused indexes (candidates for removal)

SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'analytics_v2'
  AND idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;

-- ================================================
-- 10. DATABASE SIZE AND GROWTH
-- ================================================
-- Monitor database size for capacity planning

SELECT
    pg_size_pretty(pg_database_size(current_database())) as current_size,
    current_database() as database_name;

-- Schema sizes
SELECT
    schemaname,
    pg_size_pretty(SUM(pg_total_relation_size(schemaname||'.'||tablename))::bigint) as total_size
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
GROUP BY schemaname
ORDER BY SUM(pg_total_relation_size(schemaname||'.'||tablename)) DESC;

-- ================================================
-- 11. EMERGENCY: KILL STUCK CONNECTIONS
-- ================================================
-- USE WITH CAUTION: Terminates connections
-- Replace <pid> with actual PIDs from connection health check

-- Preview connections to kill
SELECT pid, state, NOW() - state_change as idle_duration, LEFT(query, 50)
FROM pg_stat_activity
WHERE state = 'idle in transaction'
  AND NOW() - state_change > INTERVAL '5 minutes';

-- Uncomment to execute:
-- SELECT pg_terminate_backend(pid)
-- FROM pg_stat_activity
-- WHERE state = 'idle in transaction'
--   AND NOW() - state_change > INTERVAL '5 minutes';

-- ================================================
-- 12. ENABLE pg_stat_statements EXTENSION
-- ================================================
-- Run once to enable query performance tracking

-- CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- ================================================
-- END OF DIAGNOSTIC QUERIES
-- ================================================
