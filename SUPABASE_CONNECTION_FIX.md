# Supabase Connection Issue Fix

## Problem

The hostname `db.haruewffnubdgyofftut.supabase.co` does not resolve, causing this error:

```
could not translate host name "db.haruewffnubdgyofftut.supabase.co" to address: No address associated with hostname
```

## Root Causes

### 1. Supabase Project is Paused (Most Likely)

Free tier Supabase projects auto-pause after 7 days of inactivity.

**Solution:** Unpause your project

1. Go to https://supabase.com/dashboard
2. Select project: `haruewffnubdgyofftut`
3. If you see a "Paused" or "Restore" button, click it
4. Wait for project to become active (takes ~2 minutes)

### 2. Using Wrong Connection String

Supabase has two connection types:
- **Direct connection:** `db.PROJECT.supabase.co` (for serverless/edge functions)
- **Connection pooler:** `aws-0-REGION.pooler.supabase.com` (for traditional apps)

**For Docker/traditional apps, use the pooler!**

## How to Fix

### Step 1: Get Correct Connection String

1. Go to Supabase Dashboard → Your Project
2. Click "Database" in left sidebar → "Connection Pooling"
3. Copy the **Connection Pooling** URI (should look like):
   ```
   postgresql://postgres:[PASSWORD]@aws-0-us-west-1.pooler.supabase.com:6543/postgres
   ```

### Step 2: Update Your .env File

Replace the DATABASE_URL in `.env`:

**BEFORE (Direct - doesn't work from Docker):**
```bash
DATABASE_URL=postgresql+psycopg2://postgres:tMz1us7KsAHQs6QT@db.haruewffnubdgyofftut.supabase.co:5432/postgres
```

**AFTER (Pooler - works from Docker):**
```bash
# Get this from Supabase Dashboard → Database → Connection Pooling
DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@aws-0-REGION.pooler.supabase.com:6543/postgres
```

**Important differences:**
- Host: `aws-0-REGION.pooler.supabase.com` (not `db.PROJECT.supabase.co`)
- Port: `6543` (not `5432`)
- Add `?pgbouncer=true` if using session pooling

### Step 3: Verify Project is Active

Test connection from your host machine:

```bash
# Replace with your actual connection string
psql "postgresql://postgres:YOUR_PASSWORD@aws-0-REGION.pooler.supabase.com:6543/postgres" -c "SELECT 1"
```

If this fails, your project might be paused.

### Step 4: Restart Analytics API

```bash
docker-compose up -d --force-recreate analytics_api
```

### Step 5: Check Logs

```bash
docker logs analytics_api --tail 20
```

Should see:
```
INFO:src.analytics_api.main:DATABASE_URL em uso: postgresql+psycopg2://postgres:...@aws-0-REGION.pooler.supabase.com:6543/postgres
INFO:     Started server process [6]
INFO:     Application startup complete.
```

## Alternative: Check Supabase Project Status

### Via Supabase CLI

```bash
supabase projects list
supabase db start --project-ref haruewffnubdgyofftut
```

### Via Dashboard

1. Go to https://supabase.com/dashboard/project/haruewffnubdgyofftut
2. Check project status in top-right corner
3. If "Paused", click "Restore Project"

## Common Issues

### Issue: "Connection refused"

**Cause:** Project is paused

**Fix:** Restore project in dashboard

### Issue: "FATAL: remaining connection slots are reserved"

**Cause:** Too many direct connections

**Fix:** Use connection pooler (pooler.supabase.com) instead of direct connection

### Issue: "FATAL: password authentication failed"

**Cause:** Wrong password or reset needed

**Fix:**
1. Go to Supabase Dashboard → Settings → Database
2. Reset database password
3. Update .env file with new password

## Quick Fix Summary

1. ✅ Added DNS servers to docker-compose (already done)
2. ⏳ **Get pooler connection string from Supabase Dashboard**
3. ⏳ **Update .env with pooler URL (port 6543, not 5432)**
4. ⏳ **Ensure project is active (not paused)**
5. ⏳ Restart analytics_api container

## Expected Connection String Format

```bash
# Direct Connection (doesn't work well from Docker)
❌ postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres

# Connection Pooler (recommended for Docker)
✅ postgresql://postgres:PASSWORD@aws-0-REGION.pooler.supabase.com:6543/postgres?pgbouncer=true

# Transaction Mode (for some ORMs like Prisma)
✅ postgresql://postgres:PASSWORD@aws-0-REGION.pooler.supabase.com:5432/postgres?pgbouncer=true&connection_limit=1
```

## Next Steps

1. Check if project is paused in Supabase Dashboard
2. Get the correct pooler connection string
3. Update .env file
4. Restart analytics_api
5. Test: `curl http://localhost:8004/health`
