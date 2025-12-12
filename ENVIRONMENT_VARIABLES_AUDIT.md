# Environment Variables Audit & Standardization

**Date:** December 12, 2025  
**Status:** Complete Audit & Recommendations Ready

---

## 1. GitHub Secrets Audit (Current)

Your actual GitHub secrets (20 total):

| Secret | Usage | Category | Action |
|--------|-------|----------|--------|
| **CREDENTIALS_ENCRYPTION_KEY** | tool_pool_api | Required | ✅ KEEP |
| **DATABASE_URL** | All services via settings | Critical | ✅ KEEP |
| **GCP_PROJECT_ID** | file_upload_api, file_processing_worker | Critical | ✅ KEEP |
| **GCP_SA_EMAIL** | Deploy workflow | Deploy | ✅ KEEP |
| **GCP_SA_KEY** | Deploy workflow | Deploy | ✅ KEEP |
| **GRAFANA_API_KEY** | Observability | Optional | ✅ KEEP (for OTEL monitoring) |
| **LANGFUSE_PUBLIC_KEY** | Agents (vendas, support) | Optional | ✅ KEEP |
| **LANGFUSE_SECRET_KEY** | Agents (vendas, support) | Optional | ✅ KEEP |
| **MCP_AUTH_GOOGLE_CLIENT_ID** | tool_pool_api | Required | ✅ KEEP |
| **MCP_AUTH_GOOGLE_CLIENT_SECRET_DEV** | tool_pool_api (dev only) | Conditional | ⚠️ REMOVE from workflow, keep for dev |
| **OLLAMA_BASE_URL** | atendente_core, settings | Optional | ✅ KEEP |
| **OLLAMA_CLOUD_API_KEY** | Unused (legacy) | Deprecated | ❌ DELETE |
| **QDRANT_API_KEY** | Unused (not in code) | Deprecated | ❌ DELETE |
| **SUPABASE_ACCESS_TOKEN** | data_ingestion_api (via SUPABASE_URL) | Deprecated | ❌ DELETE |
| **SUPABASE_DB_PASSWORD** | Not used directly | Deprecated | ❌ DELETE |
| **SUPABASE_DB_URL** | Deprecated (use DATABASE_URL) | Deprecated | ❌ DELETE |
| **SUPABASE_JWT_SECRET** | Not used directly | Deprecated | ❌ DELETE |
| **SUPABASE_PROJECT_ID** | Not used directly | Deprecated | ❌ DELETE |
| **SUPABASE_SERVICE_KEY** | data_ingestion_api | Required | ✅ KEEP |
| **SUPABASE_URL** | data_ingestion_api | Required | ✅ KEEP |

---

## 2. Redundancy Analysis

### Problem: Supabase Duplicates
Your repo has **5 Supabase-related secrets**, but only **2 are actually used**:

```
SUPABASE_DB_URL          ← DUPLICATES DATABASE_URL
SUPABASE_DB_PASSWORD     ← DUPLICATES DATABASE_URL
SUPABASE_JWT_SECRET      ← NOT USED ANYWHERE
SUPABASE_ACCESS_TOKEN    ← DEPRECATED (use SUPABASE_SERVICE_KEY)
SUPABASE_PROJECT_ID      ← NOT USED DIRECTLY
```

**Solution:** Use only `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` + `DATABASE_URL`

### Problem: Duplicate Ollama Keys
```
OLLAMA_CLOUD_API_KEY     ← NEVER REFERENCED IN CODE
```

**Solution:** Delete `OLLAMA_CLOUD_API_KEY`

### Problem: Qdrant Key
```
QDRANT_API_KEY           ← NEVER REFERENCED IN CODE
```

**Solution:** Delete `QDRANT_API_KEY` (Qdrant runs in Docker Compose with no auth)

---

## 3. Unused Secrets (Can Be Deleted)

These secrets exist in GitHub but are **NOT referenced anywhere in code**:

1. ❌ **OLLAMA_CLOUD_API_KEY** - Not imported/used in any service
2. ❌ **QDRANT_API_KEY** - Qdrant doesn't authenticate in docker-compose
3. ❌ **SUPABASE_DB_PASSWORD** - Embedded in DATABASE_URL
4. ❌ **SUPABASE_DB_URL** - Duplicate of DATABASE_URL
5. ❌ **SUPABASE_JWT_SECRET** - Not used anywhere
6. ❌ **SUPABASE_ACCESS_TOKEN** - Deprecated, use SUPABASE_SERVICE_KEY
7. ❌ **SUPABASE_PROJECT_ID** - Not used directly

---

## 4. Environment Variables Scan Results

### By Service

**atendente_core:**
- DATABASE_URL ✅
- REDIS_URL ✅
- OLLAMA_BASE_URL ✅
- LANGCHAIN_API_KEY (optional)
- TWILIO_AUTH_TOKEN (optional, only if used)
- OTEL_EXPORTER_OTLP_ENDPOINT (optional)
- SERVICE_NAME (hardcoded)

**tool_pool_api:**
- DATABASE_URL ✅
- REDIS_URL ✅
- MCP_AUTH_GOOGLE_CLIENT_ID ✅
- MCP_AUTH_GOOGLE_CLIENT_SECRET_DEV (dev only)
- CREDENTIALS_ENCRYPTION_KEY ✅
- OTEL_EXPORTER_OTLP_ENDPOINT (optional)

**vendas_agent:**
- DATABASE_URL ✅
- REDIS_URL ✅
- MCP_SERVER_URL (internal service discovery)
- LANGFUSE_HOST (optional)
- LANGFUSE_PUBLIC_KEY (optional)
- LANGFUSE_SECRET_KEY (optional)
- OTEL_EXPORTER_OTLP_ENDPOINT (optional)

**support_agent:** (Same as vendas_agent)
- DATABASE_URL ✅
- REDIS_URL ✅
- MCP_SERVER_URL (internal service discovery)
- LANGFUSE_HOST (optional)
- LANGFUSE_PUBLIC_KEY (optional)
- LANGFUSE_SECRET_KEY (optional)
- OTEL_EXPORTER_OTLP_ENDPOINT (optional)

**analytics_api:**
- DATABASE_URL ✅
- REDIS_URL ✅
- GOOGLE_CLIENT_ID (for OAuth)
- GOOGLE_CLIENT_SECRET (for OAuth)
- GOOGLE_REDIRECT_URI (for OAuth)

**file_upload_api:**
- GCP_PROJECT_ID ✅
- GCS_BUCKET_NAME (hardcoded/config)
- PUBSUB_TOPIC_ID (hardcoded/config)
- OTEL_EXPORTER_OTLP_ENDPOINT (optional)

**file_processing_worker:**
- GCP_PROJECT_ID ✅
- GCS_BUCKET_NAME (hardcoded/config)
- PUBSUB_SUBSCRIPTION_ID (hardcoded/config)
- OTEL_EXPORTER_OTLP_ENDPOINT (optional)

**data_ingestion_api:**
- DATABASE_URL ✅
- SUPABASE_URL ✅
- SUPABASE_SERVICE_KEY ✅

**data_ingestion_worker:**
- DATABASE_URL ✅

**embedding_service:**
- (No external secrets needed)

---

## 5. Recommended GitHub Secrets (Final List)

### Critical (Services Won't Start)
- ✅ **DATABASE_URL** → postgresql://...
- ✅ **REDIS_URL** → redis://localhost:6379/0
- ✅ **GCP_PROJECT_ID** → vizudev
- ✅ **GCP_SA_EMAIL** → vizu-deployment@vizudev.iam.gserviceaccount.com
- ✅ **GCP_SA_KEY** → {GCP service account JSON}

### Integration Keys
- ✅ **SUPABASE_URL** → https://project.supabase.co
- ✅ **SUPABASE_SERVICE_KEY** → service_key_...
- ✅ **MCP_AUTH_GOOGLE_CLIENT_ID** → ...apps.googleusercontent.com
- ✅ **CREDENTIALS_ENCRYPTION_KEY** → for oauth credential storage

### Optional (For Features/Observability)
- ✅ **LANGFUSE_PUBLIC_KEY** → pk_...
- ✅ **LANGFUSE_SECRET_KEY** → sk_...
- ✅ **OLLAMA_BASE_URL** → http://ollama_service:11434
- ✅ **GRAFANA_API_KEY** → for metrics dashboard

### Development Only (NOT for Cloud Run)
- ℹ️ **MCP_AUTH_GOOGLE_CLIENT_SECRET_DEV** → Keep locally, don't sync to cloud

---

## 6. Secrets to REMOVE from GitHub

These are redundant and should be deleted from GitHub Settings:

```bash
# Run these commands to remove unused secrets:
# 1. OLLAMA_CLOUD_API_KEY (duplicate, never used)
# 2. QDRANT_API_KEY (Qdrant needs no auth in docker-compose)
# 3. SUPABASE_DB_PASSWORD (embedded in DATABASE_URL)
# 4. SUPABASE_DB_URL (same as DATABASE_URL)
# 5. SUPABASE_JWT_SECRET (never used)
# 6. SUPABASE_ACCESS_TOKEN (deprecated, use SUPABASE_SERVICE_KEY)
# 7. SUPABASE_PROJECT_ID (never used directly)
```

**How to delete:**
1. Go to: Settings → Secrets and variables → Actions
2. Find each secret above and click "Delete"

---

## 7. Mapping: Current Code → Standardized Names

| Current Usage | Service(s) | Standardized Name | GitHub Secret |
|---------------|-----------|------------------|---------------|
| DATABASE_URL | All SQL services | DATABASE_URL | DATABASE_URL |
| SUPABASE_DB_URL | (deprecated) | DATABASE_URL | ❌ DELETE |
| SUPABASE_DB_PASSWORD | (deprecated) | Part of DATABASE_URL | ❌ DELETE |
| REDIS_URL | Agents, analytics_api | REDIS_URL | REDIS_URL |
| OLLAMA_BASE_URL | atendente_core | OLLAMA_BASE_URL | OLLAMA_BASE_URL |
| OLLAMA_CLOUD_API_KEY | (unused) | ❌ DELETE | ❌ DELETE |
| LANGFUSE_* | vendas_agent, support_agent | LANGFUSE_* | LANGFUSE_* |
| MCP_AUTH_GOOGLE_CLIENT_ID | tool_pool_api | MCP_AUTH_GOOGLE_CLIENT_ID | MCP_AUTH_GOOGLE_CLIENT_ID |
| MCP_AUTH_GOOGLE_CLIENT_SECRET_DEV | tool_pool_api (dev) | (dev only) | ⚠️ Don't sync to cloud |
| GCP_PROJECT_ID | file_upload_api, worker | GCP_PROJECT_ID | GCP_PROJECT_ID |
| CREDENTIALS_ENCRYPTION_KEY | tool_pool_api | CREDENTIALS_ENCRYPTION_KEY | CREDENTIALS_ENCRYPTION_KEY |
| SUPABASE_URL | data_ingestion_api | SUPABASE_URL | SUPABASE_URL |
| SUPABASE_SERVICE_KEY | data_ingestion_api | SUPABASE_SERVICE_KEY | SUPABASE_SERVICE_KEY |
| GOOGLE_CLIENT_ID | analytics_api | GOOGLE_CLIENT_ID | (create new) |
| GOOGLE_CLIENT_SECRET | analytics_api | GOOGLE_CLIENT_SECRET | (create new) |

---

## 8. Action Items

### Phase 1: Remove Redundant Secrets (5 min)
1. Delete from GitHub: OLLAMA_CLOUD_API_KEY
2. Delete from GitHub: QDRANT_API_KEY
3. Delete from GitHub: SUPABASE_DB_PASSWORD
4. Delete from GitHub: SUPABASE_DB_URL
5. Delete from GitHub: SUPABASE_JWT_SECRET
6. Delete from GitHub: SUPABASE_ACCESS_TOKEN
7. Delete from GitHub: SUPABASE_PROJECT_ID

**Remaining GitHub secrets: 13 core + 3 optional = 16 total**

### Phase 2: Update Deploy Workflow (10 min)
Replace the secret sync in `.github/workflows/deploy-cloud-run.yml`:

```yaml
sync_secret "DATABASE_URL" "${{ secrets.DATABASE_URL }}"
sync_secret "REDIS_URL" "${{ secrets.REDIS_URL }}"
sync_secret "GCP_PROJECT_ID" "${{ secrets.GCP_PROJECT_ID }}"
sync_secret "GCP_SA_EMAIL" "${{ secrets.GCP_SA_EMAIL }}"
sync_secret "GCP_SA_KEY" "${{ secrets.GCP_SA_KEY }}"
sync_secret "SUPABASE_URL" "${{ secrets.SUPABASE_URL }}"
sync_secret "SUPABASE_SERVICE_KEY" "${{ secrets.SUPABASE_SERVICE_KEY }}"
sync_secret "MCP_AUTH_GOOGLE_CLIENT_ID" "${{ secrets.MCP_AUTH_GOOGLE_CLIENT_ID }}"
sync_secret "CREDENTIALS_ENCRYPTION_KEY" "${{ secrets.CREDENTIALS_ENCRYPTION_KEY }}"
sync_secret "LANGFUSE_PUBLIC_KEY" "${{ secrets.LANGFUSE_PUBLIC_KEY }}"
sync_secret "LANGFUSE_SECRET_KEY" "${{ secrets.LANGFUSE_SECRET_KEY }}"
sync_secret "OLLAMA_BASE_URL" "${{ secrets.OLLAMA_BASE_URL }}"
sync_secret "GRAFANA_API_KEY" "${{ secrets.GRAFANA_API_KEY }}"
```

### Phase 3: No Code Changes Needed ✅
All services already use the correct standardized names!

---

## 9. Summary Table

| Type | Count | Examples |
|------|-------|----------|
| Critical Secrets | 5 | DATABASE_URL, REDIS_URL, GCP_*, SUPABASE_* |
| Integration Keys | 4 | MCP_AUTH_*, CREDENTIALS_ENCRYPTION_KEY |
| Optional (Features) | 4 | LANGFUSE_*, OLLAMA_BASE_URL, GRAFANA_API_KEY |
| **Total to Keep** | **13** | |
| **Unused (Delete)** | **7** | OLLAMA_CLOUD_API_KEY, QDRANT_API_KEY, etc. |
| **Development Only** | **1** | MCP_AUTH_GOOGLE_CLIENT_SECRET_DEV (local only) |

---

## 10. Next Steps

1. ✅ **Done:** Code audit complete - no changes needed in services
2. 🔄 **TODO:** Delete 7 unused secrets from GitHub
3. 🔄 **TODO:** Update deploy workflow with clean secret list
4. 🔄 **TODO:** Test deployment with new secret config
5. ✅ **Result:** Unified, clean, dependency-free secret management

