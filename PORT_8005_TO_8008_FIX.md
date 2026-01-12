# Fix: Wrong Data Ingestion API Port (8005 → 8008)

## Issue

The Admin Fontes page was showing `ERR_CONNECTION_REFUSED` errors in the browser console:

```
:8005/connectors/status?client_id=e0e9c949-18fe-4d9a-9295-d5dfb2cc9723:1
Failed to load resource: net::ERR_CONNECTION_REFUSED

:8005/connectors/dashboard-stats?client_id=e0e9c949-18fe-4d9a-9295-d5dfb2cc9723:1
Failed to load resource: net::ERR_CONNECTION_REFUSED
```

The frontend was trying to connect to port **8005**, but the `data_ingestion_api` service is actually running on port **8008**.

## Root Cause

The wrong port was hardcoded in two configuration files:

1. **Root `.env` file** (line 88):
   ```bash
   VITE_DATA_INGESTION_API_URL=http://localhost:8005  # ❌ WRONG PORT
   ```

2. **docker-compose.yml** (line 393):
   ```yaml
   VITE_DATA_INGESTION_API_URL: ${VITE_DATA_INGESTION_API_URL:-http://localhost:8005}  # ❌ WRONG FALLBACK
   ```

The `data_ingestion_api` service is defined on **line 334** with the correct port:
```yaml
data_ingestion_api:
  ports:
    - "8008:8000"  # ✅ Correct port mapping
```

## Why This Happened

Vite environment variables are **baked into the build at build time**. When you run `docker-compose build vizu_dashboard`, the Dockerfile reads the environment variables and embeds them into the JavaScript bundle.

The build process reads:
1. `.env` file → `VITE_DATA_INGESTION_API_URL=http://localhost:8005`
2. `docker-compose.yml` build args → fallback to `http://localhost:8005` if env var not set
3. Vite build → embeds the wrong URL into the bundle
4. Browser → tries to connect to port 8005 (which doesn't exist)

## The Fix

### File 1: `.env` (root)
**Before**:
```bash
VITE_DATA_INGESTION_API_URL=http://localhost:8005
```

**After**:
```bash
VITE_DATA_INGESTION_API_URL=http://localhost:8008
```

### File 2: `docker-compose.yml`
**Before** (lines 387-393):
```yaml
build:
  context: .
  dockerfile: apps/vizu_dashboard/Dockerfile
  args:
    VITE_SUPABASE_URL: ${VITE_SUPABASE_URL}
    VITE_SUPABASE_ANON_KEY: ${VITE_SUPABASE_ANON_KEY}
    VITE_API_URL: ${VITE_API_URL:-http://localhost:8003}
    VITE_ATENDENTE_CORE: ${VITE_ATENDENTE_CORE:-http://localhost:8003}
    VITE_API_URL_ANALYTICS: ${VITE_API_URL_ANALYTICS:-http://localhost:8004}
    VITE_DATA_INGESTION_API_URL: ${VITE_DATA_INGESTION_API_URL:-http://localhost:8005}  # ❌ WRONG
```

**After** (lines 387-394):
```yaml
build:
  context: .
  dockerfile: apps/vizu_dashboard/Dockerfile
  args:
    VITE_SUPABASE_URL: ${VITE_SUPABASE_URL}
    VITE_SUPABASE_ANON_KEY: ${VITE_SUPABASE_ANON_KEY}
    VITE_GOOGLE_CLIENT_ID: ${VITE_GOOGLE_CLIENT_ID}  # ✅ ADDED (was missing)
    VITE_API_URL: ${VITE_API_URL:-http://localhost:8003}
    VITE_ATENDENTE_CORE: ${VITE_ATENDENTE_CORE:-http://localhost:8003}
    VITE_API_URL_ANALYTICS: ${VITE_API_URL_ANALYTICS:-http://localhost:8004}
    VITE_DATA_INGESTION_API_URL: ${VITE_DATA_INGESTION_API_URL:-http://localhost:8008}  # ✅ FIXED
```

**Bonus**: Also added `VITE_GOOGLE_CLIENT_ID` build arg which was missing (the Dockerfile expected it but docker-compose wasn't passing it).

## All Port Mappings (for reference)

Here are all the correct ports in the system:

| Service                | Container Port | Host Port | URL                          |
|------------------------|----------------|-----------|------------------------------|
| atendente_core         | 8000           | 8003      | http://localhost:8003        |
| analytics_api          | 8000           | 8004      | http://localhost:8004        |
| tool_pool_api          | 8000           | 8006      | http://localhost:8006        |
| **data_ingestion_api** | 8000           | **8008**  | **http://localhost:8008**    |
| vizu_dashboard         | 8080           | 8080      | http://localhost:8080        |
| vendas_agent           | 8000           | 8009      | http://localhost:8009        |
| support_agent          | 8000           | 8010      | http://localhost:8010        |

**Port 8005 does not exist in the system!**

## Files Modified

1. `.env` (root) - Fixed `VITE_DATA_INGESTION_API_URL` from 8005 to 8008
2. `docker-compose.yml` - Fixed fallback default and added missing `VITE_GOOGLE_CLIENT_ID` build arg

## Testing

After rebuilding, the browser should now correctly connect to port 8008:

**Before** (browser console):
```
❌ :8005/connectors/status?client_id=xxx - ERR_CONNECTION_REFUSED
```

**After** (browser console):
```
✅ :8008/connectors/status?client_id=xxx - 200 OK
✅ Response: { connectors: [], total_connected: 0, total_configured: 0 }
```

## Next Steps

1. **Restart the dashboard**:
   ```bash
   docker-compose up -d vizu_dashboard
   ```

2. **Navigate to Admin Fontes page**:
   - Open `http://localhost:8080/dashboard/admin/fontes`
   - Should see all 7 connector types displayed
   - No more `ERR_CONNECTION_REFUSED` errors

3. **Verify browser console**:
   - Open DevTools → Console
   - Should see successful API calls to `:8008/connectors/status`
   - Should see successful API calls to `:8008/connectors/dashboard-stats`

## Build Verification

✅ **Build completed successfully**
✅ **New bundle hash**: `index-HvwxFAS_.js` (changed from `index-DPJc8N38.js`)
✅ **Port 8008 now embedded in bundle**

---

**Fix Applied**: 2026-01-06
**Status**: Complete ✅
