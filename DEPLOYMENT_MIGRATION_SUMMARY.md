# Deployment Migration Summary - GitHub Registry → Artifact Registry

## Overview

Updated CI/CD workflows to:
1. **Run tests before building** Docker images
2. **Build and push directly to Google Artifact Registry** (no more GitHub Container Registry)
3. **Simplify deployment** by removing the pull-from-GitHub step

## Key Changes

### 1. CI Workflow (.github/workflows/ci.yml)

**BEFORE:**
- Build Docker images
- Push to GitHub Container Registry (ghcr.io)
- deploy-cloud-run.yml pulls from GitHub and re-pushes to Artifact Registry

**AFTER:**
- Run lint + dependency checks
- **Run tests** (pytest with coverage)
- Build Docker images
- **Push directly to Artifact Registry**
- Trigger deployment workflow

**New Stages:**
1. **Lint & Format Check** - Ruff linter
2. **Dependency Check** - Poetry lock validation
3. **Test** - Run pytest for each service ✨ NEW
4. **Build & Push** - Build and push to Artifact Registry (not GitHub)
5. **Trigger Deploy** - Auto-trigger deployment

### 2. Deploy Workflow (.github/workflows/deploy-cloud-run.yml)

**BEFORE:**
- Pull images from GitHub Container Registry
- Re-tag and push to Artifact Registry
- Deploy to Cloud Run

**AFTER:**
- **Directly use images from Artifact Registry**
- Deploy to Cloud Run
- Run health checks

**Removed:**
- All GitHub Container Registry login/pull/push steps
- Duplicate image handling

### 3. Secret Scan Workflow (.github/workflows/secret-scan.yml)

**No changes needed** - Already working correctly with detect-secrets

## Migration Steps Completed

### ✅ Step 1: Update CI Workflow

**File:** `.github/workflows/ci.yml`

**Changes:**
1. Added test stage with pytest execution
2. Changed publish target from `ghcr.io` to `southamerica-east1-docker.pkg.dev`
3. Updated authentication to use GCP credentials instead of GitHub token
4. Added coverage upload to Codecov
5. Added workflow dispatch trigger for deployment

**Test Matrix:**
```yaml
matrix:
  service:
    - data_ingestion_api  ✨
    - analytics_api        ✨
    - atendente_core       ✨
    - tool_pool_api        ✨
```

### ✅ Step 2: Update Deploy Workflow

**File:** `.github/workflows/deploy-cloud-run.yml`

**Changes:**
1. Removed GitHub Container Registry steps
2. Updated image references to point to Artifact Registry
3. Simplified deployment logic (no pull/push dance)
4. Kept secret sync and service account permissions

**Image Path:**
```
BEFORE: ghcr.io/${{ github.repository_owner }}/vizu-{service}:latest
AFTER:  southamerica-east1-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/vizu-mono/vizu-{service}:latest
```

### ✅ Step 3: Keep Secret Scan Unchanged

**File:** `.github/workflows/secret-scan.yml`

No changes needed - works independently

## New CI/CD Flow

```
┌────────────────────────────────────────────────────────────┐
│                  GitHub Actions Workflow                    │
└────────────────────────────────────────────────────────────┘

1. Push to main / Pull Request
   ↓
2. CI Workflow (.github/workflows/ci.yml)
   ├─> Lint & Format Check (parallel)
   ├─> Dependency Check (parallel)
   ↓
   ├─> Run Tests ✨ NEW
   │   ├─> pytest data_ingestion_api
   │   ├─> pytest analytics_api
   │   ├─> pytest atendente_core
   │   └─> pytest tool_pool_api
   ↓
   ├─> Build Docker Images
   │   └─> Build for linux/amd64
   ↓
   ├─> Push to Artifact Registry ✨ CHANGED
   │   └─> southamerica-east1-docker.pkg.dev
   ↓
   └─> Trigger Deployment (main branch only)

3. Deploy Workflow (.github/workflows/deploy-cloud-run.yml)
   ├─> Preflight Checks
   ├─> Sync Secrets to GCP Secret Manager
   ├─> Deploy Services ✨ SIMPLIFIED
   │   └─> Use images from Artifact Registry
   └─> Health Checks
```

## Registry Configuration

### Google Artifact Registry

**Location:** `southamerica-east1-docker.pkg.dev`

**Repository:** `vizu-mono`

**Image Naming:**
```
{REGISTRY}/{PROJECT_ID}/vizu-mono/vizu-{service}:{tag}

Example:
southamerica-east1-docker.pkg.dev/your-project/vizu-mono/vizu-data_ingestion_api:latest
southamerica-east1-docker.pkg.dev/your-project/vizu-mono/vizu-analytics_api:20251226-abc1234
```

**Tags:**
- `latest` - Latest build from main branch
- `{timestamp}-{commit}` - Versioned build (e.g., `20251226-143022-abc1234`)

## Test Execution

### Services with Tests

1. **data_ingestion_api**
   - ETL service tests
   - Schema mapping tests
   - Connector tests

2. **analytics_api**
   - Metrics calculation tests
   - Repository tests
   - API endpoint tests

3. **atendente_core**
   - Agent orchestration tests
   - Integration tests

4. **tool_pool_api**
   - Tool execution tests
   - MCP integration tests

### Test Command

```bash
poetry run pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=xml
```

### Coverage Reporting

- Coverage reports uploaded to Codecov
- Flags used to track per-service coverage
- XML format for integration with GitHub Actions

## Required GitHub Secrets

### Google Cloud

```bash
GCP_PROJECT_ID       # Your GCP project ID
GCP_SA_KEY           # Service account JSON key (with Artifact Registry permissions)
GCP_SA_EMAIL         # Service account email (optional)
```

### Database & Infrastructure

```bash
DATABASE_URL                  # PostgreSQL connection string
REDIS_URL                     # Redis connection string
SUPABASE_URL                  # Supabase project URL
SUPABASE_SERVICE_KEY          # Supabase service role key
```

### Authentication

```bash
MCP_AUTH_GOOGLE_CLIENT_ID    # Google OAuth client ID
CREDENTIALS_ENCRYPTION_KEY    # For encrypting stored credentials
```

### Optional (Observability)

```bash
LANGFUSE_PUBLIC_KEY
LANGFUSE_SECRET_KEY
OLLAMA_BASE_URL
GRAFANA_API_KEY
```

## Service Account Permissions

The GCP service account needs:

```yaml
roles:
  - roles/artifactregistry.writer     # ✨ NEW - Push images
  - roles/run.admin                    # Deploy Cloud Run services
  - roles/secretmanager.admin          # Manage secrets
  - roles/iam.serviceAccountUser       # Act as service account
```

### Create Repository (One-time)

```bash
gcloud artifacts repositories create vizu-mono \
  --repository-format=docker \
  --location=southamerica-east1 \
  --description="Vizu mono-repo Docker images" \
  --project=$GCP_PROJECT_ID
```

## Local Testing

### Run Tests Locally

```bash
cd services/data_ingestion_api
poetry install --with dev
poetry run pytest tests/ -v --cov=src
```

### Build Image Locally

```bash
# Build
cd services/data_ingestion_api
docker build -t data-ingestion-api:test -f Dockerfile ../..

# Push to Artifact Registry (if authenticated)
docker tag data-ingestion-api:test \
  southamerica-east1-docker.pkg.dev/$PROJECT_ID/vizu-mono/vizu-data_ingestion_api:test

docker push southamerica-east1-docker.pkg.dev/$PROJECT_ID/vizu-mono/vizu-data_ingestion_api:test
```

## Deployment Workflow

### Automatic (Main Branch)

1. Push to `main` branch
2. CI runs: lint → test → build → push
3. Deployment auto-triggered
4. Images pulled from Artifact Registry
5. Services deployed to Cloud Run
6. Health checks run

### Manual

```bash
# Trigger via GitHub UI
# Actions → Deploy to Cloud Run → Run workflow
# Select service: all / agents-pool / workers-pool / dashboard
```

### Manual Deploy via gcloud

```bash
# Deploy specific service
gcloud run deploy data-ingestion-api \
  --image southamerica-east1-docker.pkg.dev/$PROJECT_ID/vizu-mono/vizu-data_ingestion_api:latest \
  --region southamerica-east1 \
  --platform managed
```

## Rollback Procedure

### Rollback to Previous Version

```bash
# Find previous version
gcloud artifacts docker images list \
  southamerica-east1-docker.pkg.dev/$PROJECT_ID/vizu-mono/vizu-data_ingestion_api \
  --sort-by=~CREATE_TIME \
  --limit=5

# Deploy specific version
gcloud run deploy data-ingestion-api \
  --image southamerica-east1-docker.pkg.dev/$PROJECT_ID/vizu-mono/vizu-data_ingestion_api:20251225-143022-xyz5678 \
  --region southamerica-east1
```

## Migration Checklist

- [x] Update CI workflow to run tests
- [x] Update CI workflow to push to Artifact Registry
- [x] Update deploy workflow to use Artifact Registry
- [x] Remove GitHub Container Registry dependencies
- [ ] Create Artifact Registry repository (if not exists)
- [ ] Grant service account permissions
- [ ] Test CI workflow on feature branch
- [ ] Test deployment workflow
- [ ] Update documentation

## Benefits of Migration

### Performance

- **Faster deployments** - No pull/push dance
- **Reduced latency** - Same region as Cloud Run
- **Better integration** - Native GCP service

### Cost

- **No GitHub storage costs** for large images
- **Cheaper egress** - Same region transfers

### Simplicity

- **Single source of truth** - Artifact Registry
- **Fewer steps** - Direct build → push → deploy
- **Better visibility** - GCP Console integration

## Troubleshooting

### Authentication Errors

```bash
# Check service account has permissions
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:$GCP_SA_EMAIL"

# Grant permissions if missing
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$GCP_SA_EMAIL" \
  --role="roles/artifactregistry.writer"
```

### Image Not Found

```bash
# List images
gcloud artifacts docker images list \
  southamerica-east1-docker.pkg.dev/$PROJECT_ID/vizu-mono

# Check tags
gcloud artifacts docker tags list \
  southamerica-east1-docker.pkg.dev/$PROJECT_ID/vizu-mono/vizu-data_ingestion_api
```

### Test Failures

```bash
# Run tests locally to debug
cd services/data_ingestion_api
poetry run pytest tests/ -v -s --tb=short

# Check coverage
poetry run pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

## Next Steps

1. ✅ Review updated workflow files
2. ⏳ Create Artifact Registry repository
3. ⏳ Update GitHub secrets with GCP credentials
4. ⏳ Test CI workflow on feature branch
5. ⏳ Merge to main and verify deployment

**Status:** Ready for testing 🚀
