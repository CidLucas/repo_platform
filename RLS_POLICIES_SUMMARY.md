# Row Level Security (RLS) Policies Summary

## Overview

All analytics gold tables now have Row Level Security (RLS) enabled to ensure multi-tenant data isolation. This means:

- **Authenticated users** (Vizu Dashboard) can only SELECT their own client's data
- **Service role** (Analytics API) has full access to INSERT/UPDATE/DELETE/SELECT

## Tables with RLS Enabled

1. ✅ `analytics_gold_orders`
2. ✅ `analytics_gold_products`
3. ✅ `analytics_gold_customers`
4. ✅ `analytics_gold_suppliers`
5. ✅ `analytics_silver`

## RLS Policies Applied

### Policy 1: Authenticated Users - SELECT Only

Allows authenticated users to view only their own client's data.

```sql
-- Example for analytics_gold_orders
CREATE POLICY "Users can view own client gold orders"
    ON public.analytics_gold_orders
    FOR SELECT
    TO authenticated
    USING (
        client_id IN (
            SELECT cv.id::text
            FROM public.clientes_vizu cv
            WHERE cv.external_user_id = auth.uid()::text
        )
    );
```

**How it works:**
- When a user queries `analytics_gold_orders`, Supabase automatically adds a WHERE clause
- The clause filters rows where `client_id` matches the user's `clientes_vizu.id`
- Users can ONLY see data for their own client

**Applied to:**
- `analytics_gold_orders`
- `analytics_gold_products`
- `analytics_gold_customers`
- `analytics_gold_suppliers`
- `analytics_silver`

### Policy 2: Service Role - Full Access

Allows service role (Analytics API) to write and read all data without restrictions.

```sql
CREATE POLICY "Service role full access to gold orders"
    ON public.analytics_gold_orders
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
```

**How it works:**
- Analytics API uses `SUPABASE_SERVICE_KEY` which has `service_role` privileges
- `USING (true)` means no filtering on SELECT
- `WITH CHECK (true)` means no restrictions on INSERT/UPDATE/DELETE
- This allows Analytics API to write metrics for ANY client_id

**Applied to:**
- `analytics_gold_orders`
- `analytics_gold_products`
- `analytics_gold_customers`
- `analytics_gold_suppliers`
- `analytics_silver`

## Testing RLS

### Test 1: Verify RLS is Enabled

```sql
-- Run in Supabase SQL Editor
SELECT schemaname, tablename, rowsecurity
FROM pg_tables
WHERE tablename LIKE 'analytics_gold%' OR tablename = 'analytics_silver';

-- Expected output: rowsecurity = true for all tables
```

### Test 2: Test as Authenticated User

```sql
-- Set role to authenticated (simulates a logged-in user)
SET ROLE authenticated;
SET request.jwt.claims.sub TO '<user_supabase_uid>';

-- Try to query gold orders
SELECT * FROM public.analytics_gold_orders;

-- Should only return rows where client_id matches the user's clientes_vizu.id
-- If user has no client mapping, returns empty result
```

### Test 3: Test as Service Role

```sql
-- Set role to service_role (simulates Analytics API)
SET ROLE service_role;

-- Query gold orders
SELECT * FROM public.analytics_gold_orders;

-- Should return ALL rows regardless of client_id
```

## Security Benefits

1. **Multi-tenant Isolation**: Each client can only see their own data
2. **Zero Trust**: Even if a user gets another client's JWT token, they can't access that client's data (unless they're mapped to it in `clientes_vizu`)
3. **API Simplicity**: Analytics API doesn't need to add WHERE clauses for filtering - RLS does it automatically
4. **Audit Trail**: All queries go through Supabase Auth, providing built-in audit logging

## Common Patterns

### Pattern 1: User Has Multiple Clients

If a user should access data for multiple clients, add multiple rows in `clientes_vizu`:

```sql
INSERT INTO public.clientes_vizu (id, external_user_id)
VALUES
    ('client-1-uuid', 'user-supabase-uid'),
    ('client-2-uuid', 'user-supabase-uid');

-- Now this user can see analytics for both client-1 and client-2
```

### Pattern 2: Admin User Sees All Data

Create a special policy for admin users:

```sql
CREATE POLICY "Admins can view all gold orders"
    ON public.analytics_gold_orders
    FOR SELECT
    TO authenticated
    USING (
        -- Check if user is admin
        EXISTS (
            SELECT 1 FROM public.admin_users
            WHERE user_id = auth.uid()::text
        )
    );
```

### Pattern 3: Read-Only Analytics API

If you want a read-only analytics endpoint that can query across all clients:

```sql
-- Create a new role
CREATE ROLE analytics_readonly;

-- Grant SELECT on all gold tables
GRANT SELECT ON ALL TABLES IN SCHEMA public TO analytics_readonly;

-- Create policy for this role
CREATE POLICY "Analytics readonly full access"
    ON public.analytics_gold_orders
    FOR SELECT
    TO analytics_readonly
    USING (true);
```

## RLS SQL Code (Ready to Execute)

The complete SQL migration with all RLS policies is in:

```
supabase/migrations/20251226_create_analytics_tables_with_rls.sql
```

**To apply:**

```bash
# Using Supabase CLI
supabase db push

# Or manually in Supabase Dashboard SQL Editor
# Copy and paste the entire migration file
```

## Verification Checklist

After applying the migration:

- [ ] Verify all tables have RLS enabled
- [ ] Test SELECT as authenticated user (should filter by client_id)
- [ ] Test SELECT as service_role (should see all data)
- [ ] Test INSERT as service_role (should succeed)
- [ ] Test INSERT as authenticated user (should fail unless policy allows)
- [ ] Verify Dashboard can read gold tables
- [ ] Verify Analytics API can write to gold tables

## Troubleshooting

### Issue: User can't see any data

**Possible causes:**
1. User doesn't have a `clientes_vizu` record
2. `client_id` in gold tables doesn't match user's `clientes_vizu.id`
3. RLS policy is too restrictive

**Solution:**
```sql
-- Check user's client mapping
SELECT * FROM public.clientes_vizu WHERE external_user_id = '<user_uid>';

-- Check if data exists for that client
SELECT * FROM public.analytics_gold_orders WHERE client_id = '<client_id>';
```

### Issue: Analytics API can't write data

**Possible causes:**
1. Not using service_role key
2. Using authenticated key instead of service_role key

**Solution:**
```bash
# Verify Analytics API is using SUPABASE_SERVICE_KEY
# Check environment variables in docker-compose or .env
echo $SUPABASE_SERVICE_KEY
```

## Next Steps

1. Apply the migration to Supabase
2. Test RLS policies with different users
3. Configure Analytics API to use service_role key
4. Implement data writing logic in Analytics API
5. Test Dashboard reads from gold tables
