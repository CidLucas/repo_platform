# Required GitHub Secrets for Vizu-Mono CI/CD

This document lists all the secrets that must be configured in GitHub for the deployment workflow to work properly.

## Setup Instructions

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** for each secret below
4. Configure the values based on your environment

---

## Required Secrets Checklist

### Infrastructure & Cloud Platform
- [ ] **GCP_PROJECT_ID** - Your Google Cloud Project ID (e.g., `vizudev`)
- [ ] **GCP_SA_KEY** - GCP Service Account key (JSON format, downloaded from GCP)
- [ ] **GCP_SA_EMAIL** - GCP Service Account email (e.g., `vizu-deployment@vizudev.iam.gserviceaccount.com`)

### Database
- [ ] **DATABASE_URL** - PostgreSQL/Supabase connection string
  ```
  postgresql://user:password@host:5432/database_name
  # OR for Supabase:
  postgresql://postgres.xxxxx:password@db.xxxxx.supabase.co:5432/postgres
  ```

- [ ] **SUPABASE_URL** - Supabase project URL (if using Supabase)
  ```
  https://xxxxx.supabase.co
  ```

- [ ] **SUPABASE_SERVICE_KEY** - Supabase service role key
  ```
  eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
  ```

- [ ] **SUPABASE_ANON_KEY** - Supabase anonymous key (optional)
  ```
  eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
  ```

### Cache & Message Queue
- [ ] **REDIS_URL** - Redis connection string
  ```
  redis://user:password@host:6379
  # OR for local:
  redis://redis:6379/0
  ```

### LLM Provider Configuration
- [ ] **LLM_PROVIDER** - Which LLM provider to use
  ```
  Values: ollama, openai, anthropic, google
  ```

- [ ] **OPENAI_API_KEY** - OpenAI API key (if using OpenAI)
  ```
  sk-...
  ```

- [ ] **ANTHROPIC_API_KEY** - Anthropic API key (if using Claude)
  ```
  sk-ant-...
  ```

- [ ] **GOOGLE_API_KEY** - Google API key (if using Gemini)
  ```
  AIza...
  ```

### Local Services
- [ ] **OLLAMA_BASE_URL** - Ollama service URL
  ```
  http://ollama_service:11434
  # OR for Cloud Run internal communication:
  https://ollama-service-xxxxx-rj.a.run.app
  ```

- [ ] **EMBEDDING_SERVICE_URL** - Embedding service URL
  ```
  http://embedding_service:11435
  ```

- [ ] **MCP_SERVER_URL** - MCP/Tool Pool API server URL
  ```
  http://tool-pool-api:8000/mcp/
  # OR for Cloud Run:
  https://tool-pool-api-xxxxx-rj.a.run.app/mcp/
  ```

### Observability & Monitoring
- [ ] **LANGFUSE_HOST** - Langfuse server URL
  ```
  https://cloud.langfuse.com
  # OR for self-hosted:
  http://langfuse:3000
  ```

- [ ] **LANGFUSE_PUBLIC_KEY** - Langfuse public key
  ```
  pk-lf-...
  ```

- [ ] **LANGFUSE_SECRET_KEY** - Langfuse secret key
  ```
  sk-lf-...
  ```

- [ ] **OTEL_EXPORTER_OTLP_ENDPOINT** - OpenTelemetry collector endpoint (optional)
  ```
  http://otel-collector:4317
  # OR for GCP Cloud Trace:
  https://cloudtrace.googleapis.com/opentelemetry.proto.collector.trace.v1.TraceService
  ```

- [ ] **LANGCHAIN_API_KEY** - LangChain/LangSmith API key (optional, if using instead of Langfuse)
  ```
  ls_...
  ```

### External Services
- [ ] **TWILIO_AUTH_TOKEN** - Twilio authentication token (if using Twilio)
  ```
  AC...
  ```

---

## Secrets by Service

### atendente_core (Agent Pool)
Uses:
- DATABASE_URL
- SUPABASE_URL
- SUPABASE_SERVICE_KEY
- SUPABASE_ANON_KEY
- LLM_PROVIDER
- OPENAI_API_KEY
- ANTHROPIC_API_KEY
- GOOGLE_API_KEY
- OLLAMA_BASE_URL
- EMBEDDING_SERVICE_URL
- LANGFUSE_HOST
- LANGFUSE_PUBLIC_KEY
- LANGFUSE_SECRET_KEY

### tool_pool_api (Agent Pool)
Uses:
- DATABASE_URL
- REDIS_URL

### vendas_agent (Agent Pool)
Uses:
- DATABASE_URL
- REDIS_URL
- MCP_SERVER_URL
- LLM_PROVIDER
- OPENAI_API_KEY
- LANGFUSE_HOST
- LANGFUSE_PUBLIC_KEY
- LANGFUSE_SECRET_KEY

### support_agent (Agent Pool)
Uses:
- DATABASE_URL
- REDIS_URL
- MCP_SERVER_URL
- LLM_PROVIDER
- OPENAI_API_KEY
- LANGFUSE_HOST
- LANGFUSE_PUBLIC_KEY
- LANGFUSE_SECRET_KEY

### data_ingestion_worker (Workers Pool)
Uses:
- DATABASE_URL
- REDIS_URL

### file_processing_worker (Workers Pool)
Uses:
- DATABASE_URL
- REDIS_URL

### file_upload_api (Workers Pool)
Uses:
- DATABASE_URL
- REDIS_URL

### data_ingestion_api (Workers Pool)
Uses:
- DATABASE_URL
- REDIS_URL

### analytics_api (Workers Pool)
Uses:
- DATABASE_URL
- REDIS_URL

### vizu_dashboard (Frontend)
Uses:
- (No secrets required - frontend only)

---

## How Secrets Are Used in Deployment

1. **GitHub Secrets → GCP Secret Manager**
   - The deployment workflow reads secrets from GitHub
   - Creates/updates them in Google Cloud Secret Manager
   - Grants the Cloud Run service account access

2. **GCP Secret Manager → Cloud Run Services**
   - Cloud Run services reference secrets using `--set-secrets` flag
   - Injected as environment variables at runtime
   - Never stored in container images

3. **Secure Isolation**
   - Each secret is accessible only to authorized service accounts
   - Secrets are encrypted at rest in GCP
   - Rotation is handled through Secret Manager versions

---

## Commands to Create/Update Secrets via CLI

If you prefer to manage secrets manually via CLI:

```bash
# Create a secret
echo -n "your-secret-value" | gcloud secrets create SECRET_NAME \
  --replication-policy="automatic" \
  --data-file=- \
  --project=vizudev

# Update a secret
echo -n "new-secret-value" | gcloud secrets versions add SECRET_NAME \
  --data-file=- \
  --project=vizudev

# List all secrets
gcloud secrets list --project=vizudev

# Grant service account access
gcloud secrets add-iam-policy-binding SECRET_NAME \
  --member="serviceAccount:vizu-deployment@vizudev.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project=vizudev
```

---

## Verification

After configuring secrets, verify in the deployment logs:
- Look for the "Syncing GitHub Secrets to GCP Secret Manager" step
- Check for "✓ Created" or "✓ Updated" messages
- If you see "⚠️ Missing: ...", that secret needs to be added

Services will fail to start if critical secrets (like DATABASE_URL) are missing.
