-- ================================================
-- CONFIGURE DATABASE TIMEOUTS
-- ================================================
-- Run this in: Supabase Dashboard → SQL Editor → New Query
-- Paste this entire file and click "Run"
--
-- Purpose: Prevent connection pool incidents by auto-killing:
--   - Queries running > 30 seconds
--   - Transactions idle > 5 minutes
--
-- Context: Prevents today's incident (3 connections stuck for 1h 46m)
-- ================================================

-- Statement timeout: kills queries running longer than 30 seconds
ALTER DATABASE postgres SET statement_timeout = '30s';

-- Idle in transaction timeout: kills transactions idle > 5 minutes
-- CRITICAL: Prevents stuck "idle in transaction" connections
ALTER DATABASE postgres SET idle_in_transaction_session_timeout = '5min';

-- Verify configuration
SELECT
    name,
    setting,
    unit,
    CASE
        WHEN name = 'statement_timeout' THEN '✅ Queries > 30s will be killed'
        WHEN name = 'idle_in_transaction_session_timeout' THEN '✅ Idle transactions > 5min will be killed'
    END as description
FROM pg_settings
WHERE name IN ('statement_timeout', 'idle_in_transaction_session_timeout');

-- ================================================
-- Expected output:
--   statement_timeout | 30s | ms | ✅ Queries > 30s will be killed
--   idle_in_transaction_session_timeout | 5min | ms | ✅ Idle transactions > 5min will be killed
-- ================================================
