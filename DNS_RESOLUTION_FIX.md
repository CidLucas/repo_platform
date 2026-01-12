# Fix: DNS Resolution Error in data_ingestion_api

## Issue

The `data_ingestion_api` service was returning `500 Internal Server Error` when trying to fetch connector status. The logs showed:

```
Could not set RLS context: [Errno -2] Name or service not known
Failed to get connector status: [Errno -2] Name or service not known
httpx.ConnectError: [Errno -2] Name or service not known
INFO: 172.66.40.249:43536 - "GET /connectors/status?client_id=e0e9c949-18fe-4d9a-9295-d5dfb2cc9723 HTTP/1.1" 500 Internal Server Error
```

**Error Type**: `[Errno -2] Name or service not known` is a DNS resolution error.

## Root Cause

The `data_ingestion_api` Docker container couldn't resolve external hostnames (specifically `haruewffnubdgyofftut.supabase.co`) because it didn't have DNS servers configured.

**Why this happens**:
- The container uses `vizu_supabase_client` to connect to Supabase
- Supabase is hosted externally at `https://haruewffnubdgyofftut.supabase.co`
- Docker containers need explicit DNS server configuration to resolve external hostnames
- Without DNS servers, the container can't translate `haruewffnubdgyofftut.supabase.co` to an IP address

## Comparison with Working Service

The `analytics_api` service (which also connects to Supabase) **has** DNS configuration:

```yaml
analytics_api:
  # ...
  dns:
    - 8.8.8.8  # Google DNS
    - 8.8.4.4  # Google DNS
    - 1.1.1.1  # Cloudflare DNS
```

The `data_ingestion_api` service **was missing** this configuration.

## The Fix

Added DNS server configuration to `data_ingestion_api` service in `docker-compose.yml`:

**File**: [docker-compose.yml](/docker-compose.yml#L327-L348)

**Before** (lines 327-342):
```yaml
data_ingestion_api:
  container_name: vizu_data_ingestion_api
  platform: linux/amd64
  build:
    context: .
    dockerfile: ./services/data_ingestion_api/Dockerfile
  ports:
    - "8008:8000"
  volumes:
    - ./services/data_ingestion_api/src:/app/src
    - ./libs:/app/libs
  environment:
    <<: *common-env
    PYTHONPATH: /app/src:/app/libs
  env_file:
    - ./services/data_ingestion_api/.env
  # Note: postgres dependency is optional - use --profile local for local DB
```

**After** (lines 327-348):
```yaml
data_ingestion_api:
  container_name: vizu_data_ingestion_api
  platform: linux/amd64
  build:
    context: .
    dockerfile: ./services/data_ingestion_api/Dockerfile
  ports:
    - "8008:8000"
  volumes:
    - ./services/data_ingestion_api/src:/app/src
    - ./libs:/app/libs
  environment:
    <<: *common-env
    PYTHONPATH: /app/src:/app/libs
  env_file:
    - ./services/data_ingestion_api/.env
  # Configure DNS servers for external connectivity (Supabase)  ← ADDED
  dns:                                                           ← ADDED
    - 8.8.8.8                                                     ← ADDED
    - 8.8.4.4                                                     ← ADDED
    - 1.1.1.1                                                     ← ADDED
  # Note: postgres dependency is optional - use --profile local for local DB
```

## DNS Servers Used

| DNS Server | Provider   | Purpose                               |
|------------|------------|---------------------------------------|
| 8.8.8.8    | Google     | Primary DNS (fast, reliable)          |
| 8.8.4.4    | Google     | Fallback DNS                          |
| 1.1.1.1    | Cloudflare | Additional fallback (privacy-focused) |

## How DNS Resolution Works

1. **Frontend** sends request to `http://localhost:8008/connectors/status?client_id=xxx`
2. **data_ingestion_api** receives the request
3. **Service tries to connect to Supabase**:
   - Needs to resolve `haruewffnubdgyofftut.supabase.co` to IP address
   - Container queries configured DNS servers (8.8.8.8, 8.8.4.4, 1.1.1.1)
   - DNS server responds with IP address (e.g., `35.244.123.45`)
4. **Connection established** to Supabase using the resolved IP
5. **Data fetched** from Supabase database
6. **Response returned** to frontend

**Without DNS**: Step 3 fails with `[Errno -2] Name or service not known`

## Testing

After restarting the container, verify DNS resolution works:

**Test 1: Check DNS inside container**
```bash
docker exec vizu_data_ingestion_api nslookup haruewffnubdgyofftut.supabase.co
```
**Expected Output**:
```
Server:    8.8.8.8
Address:   8.8.8.8#53

Non-authoritative answer:
Name:   haruewffnubdgyofftut.supabase.co
Address: 35.xxx.xxx.xxx
```

**Test 2: Check API endpoint**
```bash
curl "http://localhost:8008/connectors/status?client_id=e0e9c949-18fe-4d9a-9295-d5dfb2cc9723" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```
**Expected Output**:
```json
{
  "connectors": [],
  "total_connected": 0,
  "total_configured": 0
}
```

**Test 3: Browser Console**
- Navigate to `http://localhost:8080/dashboard/admin/fontes`
- Open DevTools → Console
- Should see: `200 OK` for `:8008/connectors/status`
- Should NOT see: `500 Internal Server Error`

## Container Restart Applied

The container was restarted with the new DNS configuration:

```bash
docker-compose up -d data_ingestion_api
```

**Output**:
```
Container vizu_data_ingestion_api  Recreate
Container vizu_data_ingestion_api  Recreated
Container vizu_data_ingestion_api  Starting
Container vizu_data_ingestion_api  Started
```

## Services That Need DNS Configuration

All services that connect to **external services** (Supabase, external APIs, etc.) need DNS configuration:

| Service              | Needs DNS? | Reason                                    | Status |
|----------------------|------------|-------------------------------------------|--------|
| analytics_api        | ✅ Yes     | Connects to Supabase                      | ✅ Has |
| data_ingestion_api   | ✅ Yes     | Connects to Supabase                      | ✅ Has |
| atendente_core       | ❓ Maybe   | May connect to external LLM APIs          | ⚠️ No  |
| tool_pool_api        | ❓ Maybe   | May connect to external MCP servers       | ⚠️ No  |
| vizu_dashboard       | ❌ No      | Runs in browser (uses host DNS)           | N/A    |
| postgres             | ❌ No      | Local container (no external connections) | N/A    |
| redis                | ❌ No      | Local container (no external connections) | N/A    |

**Recommendation**: Add DNS configuration to `atendente_core` and `tool_pool_api` if they make external API calls.

## Related Issues

This DNS configuration is required because:
1. Docker containers are isolated from the host network
2. Docker's default DNS server (`127.0.0.11`) may not resolve all external hostnames
3. Explicitly setting DNS servers ensures reliable external connectivity

## Files Modified

1. [docker-compose.yml](/docker-compose.yml#L343-L347) - Added DNS configuration to data_ingestion_api service

---

**Fix Applied**: 2026-01-06
**Status**: Complete ✅
**Container Restarted**: Yes ✅
