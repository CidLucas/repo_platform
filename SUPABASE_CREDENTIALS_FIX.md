# Fix: Supabase Credentials Configuration

## Issue

The `data_ingestion_api` was returning `500 Internal Server Error` with DNS resolution errors:

```
httpx.ConnectError: [Errno -2] Name or service not known
```

Even after adding DNS servers to the container, the error persisted.

## Root Cause

The issue had **two parts**:

### Part 1: Missing DNS Configuration (Fixed Previously)
Docker containers need explicit DNS servers to resolve external hostnames.

### Part 2: Missing Supabase Credentials in Root `.env` ⚠️ **THIS WAS THE BLOCKER**

The `docker-compose.yml` uses `<<: *common-env` which reads environment variables from the **root `.env` file**, but the root `.env` had **placeholder values**:

```bash
# ROOT .env (WRONG - placeholders)
SUPABASE_URL=https://<your-supabase>.supabase.co
SUPABASE_SERVICE_KEY=<supabase_service_key>
```

The **real credentials** were in `services/data_ingestion_api/.env`:

```bash
# services/data_ingestion_api/.env (CORRECT)
SUPABASE_URL=https://haruewffnubdgyofftut.supabase.co
SUPABASE_KEY=sb_secret_WDttwpfT6_SAAm7xYYwpjA_Wf6_oSxo
SUPABASE_JWT_SECRET=e4231cf2-75a4-4846-b7f9-afcc2d71abd7
```

## How docker-compose Loads Environment Variables

```yaml
data_ingestion_api:
  environment:
    <<: *common-env          # ← Loads from ROOT .env
  env_file:
    - ./services/data_ingestion_api/.env  # ← Loads from service-specific .env
```

**Precedence**: `environment` (common-env) overrides `env_file`

So even though the service-specific `.env` had correct values, `common-env` was overriding them with placeholder values from root `.env`.

## The Fix

Updated the root `.env` file with real Supabase credentials:

**File**: [.env](/.env)

**Before**:
```bash
SUPABASE_URL=https://<your-supabase>.supabase.co
SUPABASE_SERVICE_KEY=<supabase_service_key>
# SUPABASE_JWT_SECRET not present
```

**After**:
```bash
SUPABASE_URL=https://haruewffnubdgyofftut.supabase.co
SUPABASE_SERVICE_KEY=sb_secret_WDttwpfT6_SAAm7xYYwpjA_Wf6_oSxo
SUPABASE_JWT_SECRET=e4231cf2-75a4-4846-b7f9-afcc2d71abd7
```

## How vizu_supabase_client Reads Credentials

The shared library `libs/vizu_supabase_client` expects these environment variables:

```python
# libs/vizu_supabase_client/src/vizu_supabase_client/client.py

@classmethod
def from_env(cls) -> "SupabaseConfig":
    """Load configuration from environment variables."""
    url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    anon_key = os.getenv("SUPABASE_ANON_KEY")

    if not url:
        raise ValueError("SUPABASE_URL is required")

    if not service_key:
        raise ValueError("SUPABASE_SERVICE_KEY (or SUPABASE_KEY) is required")

    return cls(url=url, service_key=service_key, anon_key=anon_key)
```

**Required Variables**:
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_SERVICE_KEY` (or `SUPABASE_KEY`) - Service role key (bypasses RLS)

**Optional**:
- `SUPABASE_ANON_KEY` - Anonymous key (for RLS-enforced operations)

## Verification

After fixing the credentials, verify they're loaded in the container:

```bash
docker exec vizu_data_ingestion_api env | grep SUPABASE_
```

**Expected Output**:
```
SUPABASE_URL=https://haruewffnubdgyofftut.supabase.co
SUPABASE_SERVICE_KEY=sb_secret_WDttwpfT6_SAAm7xYYwpjA_Wf6_oSxo
SUPABASE_JWT_SECRET=e4231cf2-75a4-4846-b7f9-afcc2d71abd7
```

**Test DNS Resolution**:
```bash
docker exec vizu_data_ingestion_api python -c "
import socket, os
url = os.getenv('SUPABASE_URL', '').replace('https://', '')
print(f'DNS: {url} → {socket.gethostbyname(url)}')
"
```

**Expected Output**:
```
✅ DNS Resolution: haruewffnubdgyofftut.supabase.co → 172.64.149.246
```

## Why This Confused Things

The `analytics_api` service **works fine** because it doesn't have a service-specific `.env` file - it only uses `common-env` from root `.env`. Since we use the `analytics_api` for reference, we assumed `data_ingestion_api` would work the same way.

**Difference**:
- `analytics_api`: Only reads from root `.env` via `common-env` ✅
- `data_ingestion_api`: Has both root `.env` (via `common-env`) AND service-specific `.env` ⚠️

## Services Using Supabase Credentials

| Service                | Uses Supabase? | Gets Credentials From          | Status |
|------------------------|----------------|--------------------------------|--------|
| analytics_api          | ✅ Yes         | Root `.env` via `common-env`   | ✅ Works |
| data_ingestion_api     | ✅ Yes         | Root `.env` via `common-env`   | ✅ Fixed |
| atendente_core         | ❌ No          | Uses local PostgreSQL          | N/A    |
| tool_pool_api          | ❌ No          | Uses local PostgreSQL          | N/A    |

## Complete Fix Summary

To fix the `data_ingestion_api` DNS/connection issues, we needed **both fixes**:

### Fix 1: Add DNS Servers (docker-compose.yml)
```yaml
data_ingestion_api:
  dns:
    - 8.8.8.8
    - 8.8.4.4
    - 1.1.1.1
```

### Fix 2: Add Real Supabase Credentials (root .env)
```bash
SUPABASE_URL=https://haruewffnubdgyofftut.supabase.co
SUPABASE_SERVICE_KEY=sb_secret_WDttwpfT6_SAAm7xYYwpjA_Wf6_oSxo
SUPABASE_JWT_SECRET=e4231cf2-75a4-4846-b7f9-afcc2d71abd7
```

**Without Fix 1**: Container can't resolve `haruewffnubdgyofftut.supabase.co` → DNS error
**Without Fix 2**: Container tries to connect to `https://<your-supabase>.supabase.co` → DNS error (invalid hostname)

## Files Modified

1. [.env](/.env) - Added real Supabase credentials (replacing placeholders)
2. [docker-compose.yml](/docker-compose.yml#L343-L347) - Added DNS servers (already done)

---

**Fix Applied**: 2026-01-06
**Status**: Complete ✅
**Container Restarted**: Yes ✅
**DNS Resolution**: Working ✅
**Credentials Loaded**: Working ✅
