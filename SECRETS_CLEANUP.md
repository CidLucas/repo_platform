# Environment Variables Cleanup - Quick Reference

## Status: ✅ COMPLETE

All analysis done. Code already uses standardized names. Ready to clean up GitHub secrets.

---

## 7 Secrets to DELETE from GitHub

Go to: **Settings → Secrets and variables → Actions** and delete these:

1. ❌ `OLLAMA_CLOUD_API_KEY` (never used in code)
2. ❌ `QDRANT_API_KEY` (Qdrant doesn't need auth)
3. ❌ `SUPABASE_DB_PASSWORD` (embedded in DATABASE_URL)
4. ❌ `SUPABASE_DB_URL` (duplicate of DATABASE_URL)
5. ❌ `SUPABASE_JWT_SECRET` (never used)
6. ❌ `SUPABASE_ACCESS_TOKEN` (use SUPABASE_SERVICE_KEY instead)
7. ❌ `SUPABASE_PROJECT_ID` (never referenced)

---

## 13 Secrets to KEEP (Already in GitHub)

### Critical (Services won't start without these):
- ✅ `DATABASE_URL` ← All services
- ✅ `REDIS_URL` ← Agents, analytics_api
- ✅ `GCP_PROJECT_ID` ← file_upload_api, workers
- ✅ `GCP_SA_EMAIL` ← Deploy workflow
- ✅ `GCP_SA_KEY` ← Deploy workflow
- ✅ `SUPABASE_URL` ← data_ingestion_api
- ✅ `SUPABASE_SERVICE_KEY` ← data_ingestion_api
- ✅ `MCP_AUTH_GOOGLE_CLIENT_ID` ← tool_pool_api
- ✅ `CREDENTIALS_ENCRYPTION_KEY` ← tool_pool_api

### Optional (Features/Observability):
- ✅ `LANGFUSE_PUBLIC_KEY` ← vendas_agent, support_agent
- ✅ `LANGFUSE_SECRET_KEY` ← vendas_agent, support_agent
- ✅ `OLLAMA_BASE_URL` ← atendente_core (if using Ollama)
- ✅ `GRAFANA_API_KEY` ← Observability dashboards

---

## No Service Code Changes Needed ✅

All your services already use these standardized names! Nothing to refactor.

---

## Deploy Workflow Updated ✅

The workflow now syncs only the 13 standardized secrets to GCP Secret Manager.

**Changes made:**
- Removed 18 unused secret references from workflow
- Added comments pointing to `ENVIRONMENT_VARIABLES_AUDIT.md`
- Cleaned up service account permission granting

---

## What This Achieves

| Issue | Before | After |
|-------|--------|-------|
| Duplicate secrets | 20 with 7 unused | 13 core + 3 optional |
| DATABASE_URL mapping | 5 different names | 1 standardized name |
| Workflow clarity | 18 secrets to sync | 13 clean secrets |
| Maintenance | Confusing redundancy | Clear, minimal, focused |

---

## Next: Manual GitHub Cleanup (5 minutes)

Since GitHub doesn't provide API to delete secrets yet, you must do it manually:

1. Go to: https://github.com/vizubr/vizu-mono/settings/secrets/actions
2. For each secret listed above ❌, click its name
3. Click "Delete this secret"
4. Confirm

Done! Then your deploy workflow will work with clean, minimal secrets.

---

## Reference Document

See: **`ENVIRONMENT_VARIABLES_AUDIT.md`** for:
- Complete mapping of all services
- Why each secret is kept/deleted
- Architecture decisions
- Service-by-service breakdown

