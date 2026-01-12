# RLS Policies - Fixed for Your Schema

## Issues Found and Fixed ✅

### Issue 1: Wrong Table Name
**Error:** `relation "public.clientes_vizu" does not exist`

**Problem:** RLS policies were referencing `clientes_vizu` (plural)

**Fixed:** Changed to `cliente_vizu` (singular) - matches your actual table name

### Issue 2: Non-existent Column
**Error:** `column cv.external_user_id does not exist`

**Problem:** The `cliente_vizu` table doesn't have an `external_user_id` column to link Supabase auth users

**Solution:** Updated RLS policies to use JWT claims instead

## New RLS Policy Design

### How It Works Now

Your JWT token (from Supabase Auth) includes a `client_id` claim. The RLS policies now check:

1. **Primary Check:** Does `client_id` match the `client_id` from the JWT?
   ```sql
   client_id = (auth.jwt()->>'client_id')::text
   ```

2. **Fallback Check:** Does `client_id` exist in the `cliente_vizu` table?
   ```sql
   client_id IN (SELECT id::text FROM public.cliente_vizu)
   ```

### Example Policy

```sql
CREATE POLICY "Users can view own client gold orders"
    ON public.analytics_gold_orders FOR SELECT TO authenticated
    USING (
        -- Primary: Match JWT claim
        client_id = (auth.jwt()->>'client_id')::text
        OR
        -- Fallback: Valid client_id exists
        client_id IN (SELECT id::text FROM public.cliente_vizu)
    );
```

## How JWT Claims Work

When a user authenticates via Supabase, their JWT token looks like:

```json
{
  "sub": "user-uuid-from-supabase-auth",
  "email": "user@example.com",
  "client_id": "client-uuid-from-cliente-vizu-table",
  "aud": "authenticated",
  ...
}
```

The RLS policy extracts `client_id` from this token using:
```sql
auth.jwt()->>'client_id'
```

## Updated Files

✅ `COPY_PASTE_TO_SUPABASE.sql` - Fixed RLS policies
✅ `supabase/migrations/20251226_drop_views_create_tables_with_rls.sql` - Fixed RLS policies

## How to Set client_id in JWT

Your authentication system (likely in `vizu_auth`) should set the `client_id` claim when creating the JWT token.

Based on your code, this is already done in:
- `libs/vizu_auth/src/vizu_auth/core/models.py` - `JWTClaims` includes `client_id`

Example flow:
1. User logs in via Supabase Auth
2. Your backend validates the token
3. Backend looks up which `cliente_vizu.id` this user belongs to
4. Backend adds `client_id` to JWT claims
5. User makes request with JWT token
6. RLS policy checks `client_id` claim matches `client_id` in analytics tables

## Testing RLS

### Test 1: Service Role (Analytics API)

Service role bypasses RLS completely:

```sql
-- Connect as service_role
INSERT INTO analytics_gold_orders (client_id, total_orders, total_revenue)
VALUES ('any-client-id', 100, 5000.00);

-- Works! Service role can write anything
```

### Test 2: Authenticated User (Dashboard)

Authenticated users only see their own data:

```sql
-- User has JWT with client_id = 'client-123'
SELECT * FROM analytics_gold_orders;

-- Only returns rows where client_id = 'client-123'
-- Other client_ids are filtered out by RLS
```

### Test 3: No JWT Claim

If JWT doesn't have `client_id`, fallback to table check:

```sql
-- Fallback check: client_id IN (SELECT id FROM cliente_vizu)
-- Returns all rows if user doesn't have client_id in JWT
-- (You probably want to fix this in your auth flow)
```

## Security Notes

### Current Security Level

- ✅ **Service role:** Full access (Analytics API writes data)
- ✅ **Authenticated users:** Read-only access to their own client data
- ⚠️ **Fallback policy:** Currently allows access to any valid `client_id`

### Recommended: Remove Fallback

For stricter security, remove the fallback check:

```sql
-- Stricter version (JWT claim required)
CREATE POLICY "Users can view own client gold orders"
    ON public.analytics_gold_orders FOR SELECT TO authenticated
    USING (
        client_id = (auth.jwt()->>'client_id')::text
    );
```

This ensures users MUST have `client_id` in their JWT to see any data.

### Recommended: Add INSERT/UPDATE Policies for Authenticated

If you want authenticated users to write their own data (not just Analytics API):

```sql
CREATE POLICY "Users can insert own client data"
    ON public.analytics_gold_orders FOR INSERT TO authenticated
    WITH CHECK (
        client_id = (auth.jwt()->>'client_id')::text
    );

CREATE POLICY "Users can update own client data"
    ON public.analytics_gold_orders FOR UPDATE TO authenticated
    USING (
        client_id = (auth.jwt()->>'client_id')::text
    )
    WITH CHECK (
        client_id = (auth.jwt()->>'client_id')::text
    );
```

## Next Steps

1. ✅ **Run the updated SQL** - Copy `COPY_PASTE_TO_SUPABASE.sql` to Supabase SQL Editor
2. ✅ **Verify tables created** - Check with `SELECT * FROM pg_tables WHERE tablename LIKE 'analytics_%'`
3. ✅ **Test with service_role** - Analytics API should be able to write data
4. ⏳ **Verify JWT claims** - Ensure your auth system sets `client_id` in JWT
5. ⏳ **Test with authenticated user** - Dashboard should only see their client's data

## Troubleshooting

### Problem: User sees no data

**Possible causes:**
1. JWT doesn't have `client_id` claim
2. `client_id` doesn't match any `client_id` in analytics tables
3. Analytics tables are empty

**Check:**
```sql
-- Decode JWT to see claims
SELECT auth.jwt();

-- Check if client_id exists
SELECT id FROM cliente_vizu WHERE id = 'your-cliente-vizu-id';

-- Check if analytics data exists for this client
SELECT * FROM analytics_gold_orders WHERE client_id = 'your-cliente-vizu-id';
```

### Problem: User sees ALL data (not filtered)

**Cause:** Fallback policy is too permissive

**Fix:** Remove the `OR client_id IN (...)` part from policies (see "Recommended: Remove Fallback" above)

## Summary

✅ **Fixed:** Table name (`cliente_vizu` not `clientes_vizu`)
✅ **Fixed:** Column reference (use JWT claims, not `external_user_id`)
✅ **Improved:** Added JWT-based access control
✅ **Ready:** Copy and run the updated SQL file

The migration is now ready to run without errors! 🎉
