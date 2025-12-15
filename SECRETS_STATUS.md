# 🔐 Vizu-Mono Secrets Status & Configuration Guide

## Quick Summary

The deployment workflow now implements **GCP Secret Manager** approach for secure secrets management. All secrets are:
- ✅ Synced from GitHub to GCP Secret Manager during deployment
- ✅ Automatically granted to Cloud Run service accounts
- ✅ Encrypted at rest in GCP
- ✅ Never stored in container images

---

## 📋 Secrets by Cate

### ✅ REQUIRED (Critical - Services Won't Start Without These)

| Secret | Service(s) | Status | Example |
|--------|-----------|--------|---------|
| **DATABASE_URL** | All services | ❌ MISSING | `postgresql://user:pass@host:5432/db` |
| **REDIS_URL** | agents, workers | ❌ MISSING | `redis://host:6379/0` |

### ⚠️ CONDITIONAL (Required for Specific Features)

| Secret | Used By | Purpose | Example |
|--------|---------|---------|---------|
| **SUPABASE_URL** | atendente_core | Supabase backend | `https://xxxxx.supabase.co` |
| **SUPABASE_SERVICE_KEY** | atendente_core | API authentication | `eyJhbGciOi...` |
| **SUPABASE_ANON_KEY** | atendente_core | Client-side auth (optional) | `eyJhbGciOi...` |
| **LLM_PROVIDER** | Agents | LLM selection | `openai`, `anthropic`, `google`, `ollama` |
| **OPENAI_API_KEY** | Agents | OpenAI API | `sk-...` |
| **ANTHROPIC_API_KEY** | Agents | Claude API | `sk-ant-...` |
| **GOOGLE_API_KEY** | Agents | Gemini API | `AIza...` |
| **LANGFUSE_HOST** | Agents | Observability | `https://cloud.langfuse.com` |
| **LANGFUSE_PUBLIC_KEY** | Agents | Langfuse auth | `pk-lf-...` |
| **LANGFUSE_SECRET_KEY** | Agents | Langfuse auth | `sk-lf-...` |
| **OLLAMA_BASE_URL** | Agents | Local LLM | `http://ollama_service:11434` |
| **EMBEDDING_SERVICE_URL** | Agents | Embeddings | `http://embedding_service:11435` |
| **MCP_SERVER_URL** | Agents | Tool definitions | `http://tool-pool-api:8000/mcp/` |
| **TWILIO_AUTH_TOKEN** | Services | SMS/WhatsApp | `AC...` |
| **LANGCHAIN_API_KEY** | Agents | LangSmith (alt to Langfuse) | `ls_...` |
| **OTEL_EXPORTER_OTLP_ENDPOINT** | Services | OpenTelemetry | `http://otel-collector:4317` |

---

## 🔴 CRITICAL: Missing Secrets That WILL Break Deployment

### Required for Cloud Run to work:
1. **DATABASE_URL** ← **MUST CONFIGURE FIRST**
2. **REDIS_URL** ← **MUST CONFIGURE SECOND**

### At least ONE of these for LLM:
- **OPENAI_API_KEY** OR
- **ANTHROPIC_API_KEY** OR
- **GOOGLE_API_KEY** OR
- **OLLAMA_BASE_URL** (for local LLM)

### For observability (optional but recommended):
- **LANGFUSE_HOST**, **LANGFUSE_PUBLIC_KEY**, **LANGFUSE_SECRET_KEY**

---

## 🚀 Setup Steps

### Step 1: Configure Critical Secrets in GitHub

Go to **Settings → Secrets and variables → Actions** and add:

```yaml
# These are REQUIRED - services won't start without them
GCP_PROJECT_ID: vizudev
GCP_SA_KEY: (JSON from GCP service account)
GCP_SA_EMAIL: vizu-deployment@vizudev.iam.gserviceaccount.com
DATABASE_URL: postgresql://user:password@host:5432/vizu
REDIS_URL: redis://redis-host:6379/0
```

### Step 2: Configure LLM Provider

Choose ONE and configure:

```yaml
# Option A: OpenAI
LLM_PROVIDER: openai
OPENAI_API_KEY: sk-...

# Option B: Anthropic (Claude)
LLM_PROVIDER: anthropic
ANTHROPIC_API_KEY: sk-ant-...

# Option C: Google Gemini
LLM_PROVIDER: google
GOOGLE_API_KEY: AIza...

# Option D: Local Ollama
LLM_PROVIDER: ollama
OLLAMA_BASE_URL: http://ollama_service:11434
```

### Step 3: Configure Supabase (if using)

```yaml
SUPABASE_URL: https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY: eyJhbGciOi...
SUPABASE_ANON_KEY: eyJhbGciOi...  # optional
```

### Step 4: Configure Observability

```yaml
LANGFUSE_HOST: https://cloud.langfuse.com
LANGFUSE_PUBLIC_KEY: pk-lf-...
LANGFUSE_SECRET_KEY: sk-lf-...
```

### Step 5: Configure Internal Services

```yaml
OLLAMA_BASE_URL: http://ollama_service:11434
EMBEDDING_SERVICE_URL: http://embedding_service:11435
MCP_SERVER_URL: http://tool-pool-api:8000/mcp/
```

---

## 🔍 How to Find Missing Secrets

1. **Trigger a deployment** via GitHub Actions
2. Look for the step: **"Syncing GitHub Secrets to GCP Secret Manager"**
3. Check the log output for **"⚠️ Missing: ..."** lines
4. Add those missing secrets to GitHub

Example log output:
```
✓ Created: DATABASE_URL
✓ Updated: REDIS_URL
⚠️ Missing: OPENAI_API_KEY (not configured in GitHub)
⚠️ Missing: LANGFUSE_SECRET_KEY (not configured in GitHub)
```

---

## ✅ Verification Checklist

After configuring secrets:

- [ ] GitHub secrets are configured in **Settings → Secrets**
- [ ] Deploy workflow has run successfully
- [ ] Check Cloud Run logs: `gcloud run services describe <service> --region=southamerica-east1`
- [ ] Service is showing as "Ready" (green checkmark)
- [ ] Test service endpoint: `curl https://<service-url>`

---

## 🆘 Troubleshooting

### "Container failed to start" Error
→ Missing required environment variables. Check the "Syncing Secrets" step in workflow logs.

### "Permission denied" When Accessing Secrets
→ Service account doesn't have access. Workflow should auto-grant, but verify with:
```bash
gcloud secrets get-iam-policy DATABASE_URL --project=vizudev
```

### Secrets Not Updating
→ Create a new deployment or manually update in Secret Manager:
```bash
echo -n "new-value" | gcloud secrets versions add DATABASE_URL --data-file=-
```

### Service Can't Connect to Database
→ Verify DATABASE_URL is correct for Cloud Run (must use public IP or Cloud SQL proxy)

---

## 📚 Documentation

- **Full secrets reference**: See [`docs/GITHUB_SECRETS_SETUP.md`](./GITHUB_SECRETS_SETUP.md)
- **Deployment workflow**: See [`.github/workflows/deploy-cloud-run.yml`](./.github/workflows/deploy-cloud-run.yml)
- **Secrets management script**: See [`scripts/manage-gcp-secrets.sh`](./scripts/manage-gcp-secrets.sh)

---

## 🔗 Service Communication Map

### Agent Pool Services (All Internal)
- `atendente-core` (main entry) → talks to all pools
- `tool-pool-api` → provides tool definitions
- `vendas_agent`, `support_agent` → use tools via MCP

### Workers Pool Services (Async)
- `data-ingestion-worker`, `file-processing-worker`
- `file-upload-api`, `data-ingestion-api`, `analytics-api`

### URLs in Cloud Run
```
https://atendente-core-xxxxx-rj.a.run.app
https://tool-pool-api-xxxxx-rj.a.run.app
https://vendas-agent-xxxxx-rj.a.run.app
https://support-agent-xxxxx-rj.a.run.app
https://data-ingestion-worker-xxxxx-rj.a.run.app
https://file-processing-worker-xxxxx-rj.a.run.app
https://file-upload-api-xxxxx-rj.a.run.app
https://data-ingestion-api-xxxxx-rj.a.run.app
https://analytics-api-xxxxx-rj.a.run.app
```

---

## ❓ Questions?

Check the full setup guide in `docs/GITHUB_SECRETS_SETUP.md` for detailed instructions on where to find each secret value.
