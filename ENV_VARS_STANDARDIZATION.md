# Environment Variables Standardization

## Current State Analysis

### Variables Found Across Codebase

#### Supabase-related (INCONSISTENT ❌)
- `SUPABASE_URL` ✅ (standardized)
- `SUPABASE_SERVICE_KEY` ✅ (primary)
- `SUPABASE_KEY` ⚠️ (legacy fallback)
- `SUPABASE_ANON_KEY` (optional, rarely used)
- `VITE_SUPABASE_URL` (frontend only)

#### Database-related (INCONSISTENT ❌)
- `DATABASE_URL` ⚠️ (legacy PostgreSQL direct connection)
- `ANALYTICS_DATABASE_URL` ⚠️ (legacy)
- `TEST_DATABASE_URL` (testing only)
- `SUPABASE_DB_URL` ⚠️ (legacy, commented out)

### Current Usage Pattern

**✅ Correct (Supabase REST API):**
```python
# libs/vizu_supabase_client/src/vizu_supabase_client/client.py
url = os.getenv("SUPABASE_URL")
service_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
```

**❌ Legacy (Direct PostgreSQL):**
```python
# services/analytics_api/src/analytics_api/core/config.py
DATABASE_URL: str = "postgresql+psycopg2://user:password@localhost:5433/vizu_db"
```

## Standardization Plan

### Phase 1: Standardize Supabase Variables ✅

**Standard Variable Names:**
```bash
# Primary (required)
SUPABASE_URL=https://haruewffnubdgyofftut.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Optional
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  # For RLS-enforced operations
```

**Actions:**
1. ✅ Keep `SUPABASE_URL` - already standardized
2. ✅ Keep `SUPABASE_SERVICE_KEY` as primary
3. ⚠️ Deprecate `SUPABASE_KEY` (but keep as fallback for backward compatibility)
4. ❌ Remove all `DATABASE_URL` usage in favor of Supabase REST API

### Phase 2: Eliminate Direct PostgreSQL Access ⚠️

**Files Using DATABASE_URL (to be updated):**

1. **services/analytics_api/**
   - `src/analytics_api/core/config.py` - Remove `DATABASE_URL`
   - `src/analytics_api/main.py` - Remove `DATABASE_URL` logging
   - Status: ⚠️ Currently uses Supabase client, but config has legacy field

2. **services/atendente_core/**
   - `src/atendente_core/core/config.py` - `DATABASE_URL: str | None = None`
   - `tests/conftest.py` - Keep for testing only
   - Status: ✅ Optional, not actively used

3. **services/support_agent/**
   - `src/support_agent/core/config.py` - `DATABASE_URL: str | None = None`
   - Status: ✅ Optional, not actively used

4. **services/tool_pool_api/**
   - `src/tool_pool_api/core/config.py` - `DATABASE_URL: str | None = None`
   - `.env` - Has `DATABASE_URL` and `TEST_DATABASE_URL`
   - Status: ⚠️ Used for testing, keep but document as test-only

5. **services/vendas_agent/**
   - `src/vendas_agent/core/config.py` - `DATABASE_URL: str | None = None`
   - Status: ✅ Optional, not actively used

### Phase 3: Update Configuration Files

#### docker-compose.yml
**Current (INCONSISTENT):**
```yaml
x-common-env: &common-env
  DATABASE_URL: ${DATABASE_URL}
  SUPABASE_KEY: ${SUPABASE_KEY}
  SUPABASE_URL: ${SUPABASE_URL}

analytics_api:
  environment:
    DATABASE_URL: ${ANALYTICS_DATABASE_URL:-${DATABASE_URL}}
```

**Proposed (STANDARDIZED):**
```yaml
x-common-env: &common-env
  SUPABASE_URL: ${SUPABASE_URL}
  SUPABASE_SERVICE_KEY: ${SUPABASE_SERVICE_KEY}

# Remove DATABASE_URL unless needed for local postgres (testing)
```

#### .github/workflows/deploy-cloud-run.yml
**Current:**
```yaml
--set-secrets="DATABASE_URL=DATABASE_URL:latest,SUPABASE_URL=SUPABASE_URL:latest,SUPABASE_SERVICE_KEY=SUPABASE_SERVICE_KEY:latest"
```

**Proposed:**
```yaml
--set-secrets="SUPABASE_URL=SUPABASE_URL:latest,SUPABASE_SERVICE_KEY=SUPABASE_SERVICE_KEY:latest"
# Remove DATABASE_URL from production deployments
```

#### .env Files
**Files to Update:**
- `services/data_ingestion_api/.env` ✅ Already correct (SUPABASE_URL, SUPABASE_KEY)
- `apps/vizu_dashboard/.env` ✅ Already correct (SUPABASE_URL, VITE_SUPABASE_URL)
- `services/tool_pool_api/.env` ⚠️ Has DATABASE_URL (keep for testing)
- All `.env.example` files ⚠️ Need standardization

## Recommended Standard

### Production Environment Variables

```bash
# ============================================================================
# SUPABASE (Primary Data Store)
# ============================================================================
SUPABASE_URL=https://haruewffnubdgyofftut.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  # service_role key
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...     # Optional: for RLS

# ============================================================================
# REDIS (Session/Cache)
# ============================================================================
REDIS_URL=redis://localhost:6379

# ============================================================================
# GCP (Infrastructure)
# ============================================================================
GCP_PROJECT_ID=vizudev
GCP_SA_EMAIL=github-actions@vizudev.iam.gserviceaccount.com
GCP_SA_KEY=<base64-encoded-service-account-json>

# ============================================================================
# OBSERVABILITY
# ============================================================================
OTEL_EXPORTER_OTLP_ENDPOINT=https://your-otel-collector:4318
LANGFUSE_HOST=https://cloud.langfuse.com
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...

# ============================================================================
# AI SERVICES
# ============================================================================
GOOGLE_API_KEY=AIza...
ANTHROPIC_API_KEY=sk-ant-...
OLLAMA_BASE_URL=http://ollama:11434

# ============================================================================
# AUTHENTICATION
# ============================================================================
MCP_AUTH_GOOGLE_CLIENT_ID=123456789-xxx.apps.googleusercontent.com
MCP_AUTH_GOOGLE_CLIENT_SECRET_DEV=GOCSPX-xxx
MCP_AUTH_BASE_URL=http://localhost:8006
CREDENTIALS_ENCRYPTION_KEY=your-32-char-encryption-key

# ============================================================================
# DEPRECATED (Remove from production)
# ============================================================================
# DATABASE_URL - Use SUPABASE_URL + SUPABASE_SERVICE_KEY instead
# SUPABASE_KEY - Use SUPABASE_SERVICE_KEY instead
# ANALYTICS_DATABASE_URL - Use SUPABASE_URL + SUPABASE_SERVICE_KEY instead
```

### Testing Environment Variables (Local Only)

```bash
# For integration tests that need direct PostgreSQL access
DATABASE_URL=postgresql://user:password@localhost:5432/vizu_db
TEST_DATABASE_URL=postgresql://user:password@localhost:5432/vizu_db_test
```

## Migration Checklist

### Immediate Actions (No Breaking Changes)

- [x] ✅ All services use `vizu_supabase_client` which already supports both variable names
- [x] ✅ `SUPABASE_SERVICE_KEY` is the primary variable
- [x] ✅ `SUPABASE_KEY` works as fallback (backward compatible)

### Phase 1: Documentation & Warnings (This PR)

- [ ] Update all `.env.example` files with standard variable names
- [ ] Add deprecation comments for `DATABASE_URL` in config files
- [ ] Update docker-compose.yml to use standard names (backward compatible)
- [ ] Document migration in README

### Phase 2: Code Cleanup (Future PR)

- [ ] Remove unused `DATABASE_URL` fields from config classes
- [ ] Update all config classes to use only Supabase variables
- [ ] Remove `ANALYTICS_DATABASE_URL` from analytics_api
- [ ] Clean up legacy comments about PostgreSQL direct connections

### Phase 3: Secrets Cleanup (After Code Deployment)

- [ ] Remove `DATABASE_URL` from GitHub Secrets
- [ ] Remove `DATABASE_URL` from GCP Secret Manager
- [ ] Update deploy workflows to only use Supabase secrets

## Impact Analysis

### Services Already Compliant ✅
- ✅ `data_ingestion_api` - Uses Supabase client only
- ✅ `analytics_api` - Uses Supabase client (has legacy config field but not used)
- ✅ `file_upload_api` - Uses Supabase client

### Services Partially Compliant ⚠️
- ⚠️ `atendente_core` - Has `DATABASE_URL` field but doesn't use it
- ⚠️ `tool_pool_api` - Has `DATABASE_URL` for OAuth credential storage
- ⚠️ `support_agent` - Has `DATABASE_URL` field but doesn't use it
- ⚠️ `vendas_agent` - Has `DATABASE_URL` field but doesn't use it

### Special Cases
- **tool_pool_api OAuth**: Currently stores encrypted credentials in PostgreSQL via `DATABASE_URL`. Should migrate to Supabase table.

## Benefits of Standardization

1. **Simplicity**: Single source of truth for database access
2. **Consistency**: All services use the same environment variables
3. **Security**: Supabase REST API with RLS instead of direct PostgreSQL
4. **Scalability**: Supabase connection pooling handled automatically
5. **Maintainability**: Fewer configuration variations to manage
6. **Cost**: Reduced secret management overhead

## Current Standard (As Implemented)

**Primary Variables (Required):**
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_SERVICE_KEY` - service_role key (bypasses RLS)

**Fallback Variables (Deprecated but Supported):**
- `SUPABASE_KEY` - Falls back to SUPABASE_SERVICE_KEY

**Test-Only Variables:**
- `DATABASE_URL` - Local PostgreSQL for integration tests
- `TEST_DATABASE_URL` - Dedicated test database

**Frontend Variables:**
- `VITE_SUPABASE_URL` - Exposed to browser (Vite prefix required)
- `VITE_SUPABASE_ANON_KEY` - Public anon key for client-side

## Next Steps

1. ✅ Rebuild all services with updated configuration
2. ⏳ Test services with standard environment variables
3. ⏳ Update `.env.example` files
4. ⏳ Clean up legacy DATABASE_URL references
5. ⏳ Update documentation
