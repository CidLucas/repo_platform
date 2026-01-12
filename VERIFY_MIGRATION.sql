-- =====================================================================
-- VERIFICATION QUERIES - Run after migration
-- =====================================================================
-- Copy these queries one by one into Supabase SQL Editor
-- to verify everything is set up correctly
-- =====================================================================

-- =====================================================================
-- 1. CHECK TABLES EXIST (should show 5 tables)
-- =====================================================================
SELECT
    table_name,
    table_type,
    CASE
        WHEN table_type = 'BASE TABLE' THEN '✅ Correct (Table)'
        WHEN table_type = 'VIEW' THEN '❌ Wrong (Still a view)'
        ELSE '⚠️ Unknown type'
    END as status
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name LIKE 'analytics_%'
ORDER BY table_name;

-- Expected: 5 rows, all with table_type = 'BASE TABLE'
-- analytics_gold_customers   | BASE TABLE | ✅ Correct
-- analytics_gold_orders      | BASE TABLE | ✅ Correct
-- analytics_gold_products    | BASE TABLE | ✅ Correct
-- analytics_gold_suppliers   | BASE TABLE | ✅ Correct
-- analytics_silver           | BASE TABLE | ✅ Correct

-- =====================================================================
-- 2. CHECK RLS IS ENABLED (should show true for all)
-- =====================================================================
SELECT
    tablename,
    rowsecurity,
    CASE
        WHEN rowsecurity = true THEN '✅ RLS Enabled'
        ELSE '❌ RLS NOT Enabled'
    END as rls_status
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename LIKE 'analytics_%'
ORDER BY tablename;

-- Expected: All should have rowsecurity = t (true)

-- =====================================================================
-- 3. CHECK RLS POLICIES (should show 10 policies)
-- =====================================================================
SELECT
    tablename,
    policyname,
    roles,
    cmd as operation,
    CASE
        WHEN 'authenticated' = ANY(roles) THEN '👤 Dashboard Users'
        WHEN 'service_role' = ANY(roles) THEN '🔧 Analytics API'
        ELSE '⚠️ Other'
    END as who_can_use
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename LIKE 'analytics_%'
ORDER BY tablename, policyname;

-- Expected: 10 policies total (2 per table)
-- Each table should have:
--   1. "Users can view..." (SELECT, authenticated)
--   2. "Service role..." (ALL, service_role)

-- =====================================================================
-- 4. CHECK TABLE STRUCTURE (analytics_gold_orders example)
-- =====================================================================
SELECT
    column_name,
    data_type,
    column_default,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'analytics_gold_orders'
ORDER BY ordinal_position;

-- Expected: Should show all columns like id, client_id, total_orders, etc.

-- =====================================================================
-- 5. CHECK INDEXES (should show 5+ indexes)
-- =====================================================================
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename LIKE 'analytics_%'
ORDER BY tablename, indexname;

-- Expected: Should show indexes on client_id for all tables

-- =====================================================================
-- 6. CHECK PERMISSIONS (should show GRANT statements)
-- =====================================================================
SELECT
    grantee,
    table_name,
    privilege_type
FROM information_schema.role_table_grants
WHERE table_schema = 'public'
  AND table_name LIKE 'analytics_%'
  AND grantee IN ('authenticated', 'service_role')
ORDER BY table_name, grantee, privilege_type;

-- Expected:
--   authenticated: SELECT on all tables
--   service_role: ALL privileges on all tables

-- =====================================================================
-- 7. TEST INSERT (as service_role - this should work)
-- =====================================================================
-- Only run this if you're connected as service_role or postgres
INSERT INTO public.analytics_gold_orders (
    client_id,
    total_orders,
    total_revenue,
    avg_order_value,
    period_type
) VALUES (
    'test-client-123',
    100,
    50000.00,
    500.00,
    'all_time'
);

-- Expected: Should succeed
-- Then verify:
SELECT * FROM public.analytics_gold_orders WHERE client_id = 'test-client-123';

-- Clean up test data:
DELETE FROM public.analytics_gold_orders WHERE client_id = 'test-client-123';

-- =====================================================================
-- 8. FULL SUMMARY - Copy All Results
-- =====================================================================
-- Run this to get a complete summary to share:

SELECT
    'Tables' as check_type,
    COUNT(*)::text as count,
    STRING_AGG(table_name, ', ') as details
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name LIKE 'analytics_%'
  AND table_type = 'BASE TABLE'

UNION ALL

SELECT
    'Tables with RLS',
    COUNT(*)::text,
    STRING_AGG(tablename, ', ')
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename LIKE 'analytics_%'
  AND rowsecurity = true

UNION ALL

SELECT
    'RLS Policies',
    COUNT(*)::text,
    STRING_AGG(DISTINCT tablename, ', ')
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename LIKE 'analytics_%'

UNION ALL

SELECT
    'Indexes',
    COUNT(*)::text,
    STRING_AGG(DISTINCT tablename, ', ')
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename LIKE 'analytics_%';

-- Expected output:
-- check_type          | count | details
-- Tables              | 5     | analytics_gold_customers, analytics_gold_orders, ...
-- Tables with RLS     | 5     | analytics_gold_customers, analytics_gold_orders, ...
-- RLS Policies        | 10    | analytics_gold_customers, analytics_gold_orders, ...
-- Indexes             | 5     | analytics_gold_customers, analytics_gold_orders, ...

-- =====================================================================
-- ✅ If all checks pass, your migration is successful!
-- =====================================================================
