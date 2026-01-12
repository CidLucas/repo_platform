# Analytics API Setup and Configuration

This document explains how to set up and configure the Analytics API to work with both local PostgreSQL (development) and Supabase (production).

## Architecture Overview

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐      ┌──────────────┐
│  BigQuery /     │ ───> │ Data Ingestion   │ ───> │  Analytics API  │ ───> │   Supabase   │
│  Data Sources   │      │  API (via FDW)   │      │  (Processing)   │      │ Gold Tables  │
└─────────────────┘      └──────────────────┘      └─────────────────┘      └──────────────┘
                                                                                      │
                                                                                      ▼
                                                                              ┌──────────────┐
                                                                              │     Vizu     │
                                                                              │  Dashboard   │
                                                                              └──────────────┘
```

**Data Flow:**
1. **Data Ingestion API** connects to BigQuery/data sources via Foreign Data Wrappers (FDW)
2. **Analytics API** reads from BigQuery, processes/aggregates data, and writes to Supabase gold tables
3. **Vizu Dashboard** connects to Supabase and displays metrics from analytics_gold_* tables

## Database Tables

### Gold Layer Tables (Written by Analytics API, Read by Dashboard)

All tables have Row Level Security (RLS) enabled to ensure multi-tenant data isolation:

1. **`analytics_gold_orders`** - Aggregated order metrics per client
2. **`analytics_gold_products`** - Product performance metrics per client
3. **`analytics_gold_customers`** - Customer analytics per client
4. **`analytics_gold_suppliers`** - Supplier metrics per client
5. **`analytics_silver`** - Optional cached denormalized data from BigQuery

## Setup Instructions

### 1. Apply Database Migration to Supabase

The migration file creates all necessary tables with RLS policies.

```bash
# Navigate to project root
cd /Users/lucascruz/Documents/GitHub/vizu-mono

# Apply migration to Supabase (requires Supabase CLI)
supabase db push

# Or manually apply via Supabase Dashboard SQL Editor
# Copy contents of: supabase/migrations/20251226_create_analytics_tables_with_rls.sql
```

### 2. Configure Environment Variables

#### For Production (Supabase)

In `.env`, ensure these are set:

```bash
# Supabase connection (already configured)
DATABASE_URL=postgresql+psycopg2://postgres:tMz1us7KsAHQs6QT@db.haruewffnubdgyofftut.supabase.co:5432/postgres
DB_MODE=supabase_api

# Analytics API will use DATABASE_URL (Supabase)
# ANALYTICS_DATABASE_URL is NOT set - defaults to DATABASE_URL
```

#### For Local Development (Local PostgreSQL)

In `.env`, uncomment the analytics override:

```bash
# Main DB still points to Supabase (for other services)
DATABASE_URL=postgresql+psycopg2://postgres:tMz1us7KsAHQs6QT@db.haruewffnubdgyofftut.supabase.co:5432/postgres

# Analytics API Override - uses local postgres
ANALYTICS_DATABASE_URL=postgresql+psycopg2://user:password@postgres:5432/vizu_db

# Run with local profile
COMPOSE_PROFILES=local
```

### 3. Start Services

#### Production Mode (Supabase)

```bash
# Start services without local postgres
docker-compose up -d analytics_api

# Analytics API will connect to Supabase
```

#### Local Development Mode

```bash
# Start with local postgres
docker-compose --profile local up -d

# This starts:
# - postgres (local)
# - analytics_api (connects to local postgres)
# - All other services
```

### 4. Verify Connection

```bash
# Check analytics_api logs
docker logs analytics_api --tail 50

# Should see:
# INFO:src.analytics_api.main:DATABASE_URL em uso: postgresql+psycopg2://postgres:...@db.haruewffnubdgyofftut.supabase.co:5432/postgres
# (or local postgres URL if ANALYTICS_DATABASE_URL is set)

# Test health endpoint
curl http://localhost:8004/health

# Should return:
# {"status":"ok","service":"analytics-api","client_id_configurado":"e2e-test-client"}
```

## Row Level Security (RLS)

All analytics gold tables have RLS enabled with the following policies:

### For Authenticated Users (Dashboard)
- **SELECT only** - Can view their own client's data
- RLS filters by `client_id` matching their `clientes_vizu` record

### For Service Role (Analytics API)
- **Full access** (INSERT, UPDATE, DELETE, SELECT)
- Bypasses RLS
- Used for writing processed analytics data

### Security Model

```sql
-- Users can only see data for their client_id
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

-- Service role (Analytics API) has full access
CREATE POLICY "Service role full access to gold orders"
    ON public.analytics_gold_orders
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
```

## Testing RLS

### Test with Service Role (Analytics API)

```bash
# The Analytics API uses SUPABASE_SERVICE_KEY which has service_role privileges
# It can write to all gold tables regardless of client_id

# Example: Insert test data
curl -X POST http://localhost:8004/api/test/insert-gold-data \
  -H "Authorization: Bearer <service_role_key>"
```

### Test with Authenticated User (Dashboard)

```bash
# Dashboard users authenticate via Supabase Auth
# They receive a JWT token with their user_id

# RLS automatically filters results to show only their client's data
curl http://localhost:8004/api/dashboard/home_gold \
  -H "Authorization: Bearer <user_jwt_token>"

# Returns only data where client_id matches the user's clientes_vizu.id
```

## API Endpoints

### Dashboard Endpoints (Read Gold Tables)

- `GET /api/dashboard/home_gold` - Aggregated order metrics
- `GET /api/dashboard/produtos/gold` - Product metrics
- `GET /api/dashboard/clientes/gold` - Customer metrics
- `GET /api/dashboard/fornecedores/gold` - Supplier metrics

All endpoints respect RLS and return only the authenticated user's client data.

## Troubleshooting

### Issue: "relation 'analytics_gold_orders' does not exist"

**Solution:** Run the migration on Supabase:
```bash
supabase db push
```

### Issue: Analytics API can't connect to Supabase

**Symptoms:**
```
sqlalchemy.exc.OperationalError: could not translate host name "db.haruewffnubdgyofftut.supabase.co"
```

**Solutions:**
1. Check `DATABASE_URL` in `.env` is correct
2. Verify network connectivity to Supabase
3. Ensure Supabase database is not paused (free tier auto-pauses after inactivity)

### Issue: CORS errors from dashboard

**Symptom:**
```
Access to XMLHttpRequest at 'http://localhost:8004/api/...' from origin 'http://localhost:3001'
has been blocked by CORS policy
```

**Solution:** CORS is already configured in `analytics_api/main.py`. If you see this error, the API is likely not running. Check:
```bash
docker logs analytics_api
curl http://localhost:8004/health
```

### Issue: RLS blocking authenticated users

**Symptoms:**
- User can't see any data
- Empty results from gold endpoints

**Solution:**
1. Verify user has a `clientes_vizu` record with their `external_user_id`
2. Check JWT token is valid
3. Verify `client_id` in gold tables matches user's `clientes_vizu.id`

```sql
-- Check user's client mapping
SELECT * FROM public.clientes_vizu WHERE external_user_id = '<user_supabase_id>';

-- Check if gold tables have data for that client_id
SELECT * FROM public.analytics_gold_orders WHERE client_id = '<client_id>';
```

## Configuration Summary

| Mode | DATABASE_URL | ANALYTICS_DATABASE_URL | Result |
|------|-------------|------------------------|--------|
| Production | Supabase | (not set) | Analytics API → Supabase |
| Local Dev | Supabase | Local Postgres | Analytics API → Local Postgres |
| Local Dev (all) | Local Postgres | (not set) | All services → Local Postgres |

## Next Steps

1. ✅ Apply migration to Supabase
2. ✅ Configure `.env` for your environment
3. ✅ Start analytics_api
4. ⏳ Test endpoints with authenticated user
5. ⏳ Implement data processing logic in Analytics API
6. ⏳ Set up scheduled jobs to refresh gold tables

## Migration File Location

```
supabase/migrations/20251226_create_analytics_tables_with_rls.sql
```

This file contains:
- Table definitions for all gold layer tables
- RLS policies for multi-tenant security
- Indexes for performance
- Grant statements for permissions
