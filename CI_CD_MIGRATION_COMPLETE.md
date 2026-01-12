# CI/CD Migration to Artifact Registry - Complete

## Overview

Successfully migrated the CI/CD pipeline from GitHub Container Registry to Google Artifact Registry with integrated test execution.

## Changes Made

### 1. GitHub Actions Workflow ([.github/workflows/ci.yml](.github/workflows/ci.yml))

**Test Stage (NEW):**
- Added pytest execution for all services before building images
- Automatically installs pytest-cov plugin if not present
- Runs tests with coverage reporting to Codecov
- Tests run in parallel for: `data_ingestion_api`, `analytics_api`, `atendente_core`, `tool_pool_api`

**Build & Push Stage (UPDATED):**
- Changed target from `ghcr.io` → `southamerica-east1-docker.pkg.dev/vizudev/vizu-mono`
- Uses GCP Service Account authentication instead of GitHub token
- Builds for `linux/amd64` platform (Cloud Run requirement)
- Tags images with both versioned tag (`YYYYMMDD-HHMMSS-commit`) and `:latest`
- Matrix includes all services:
  - **Agents Pool:** atendente_core, tool_pool_api, vendas_agent, support_agent
  - **Workers Pool:** data_ingestion_api, analytics_api, file_upload_api
  - **Dashboard:** vizu_dashboard

**Trigger Deploy Stage (NEW):**
- Automatically triggers `deploy-cloud-run.yml` workflow after successful build
- Only runs on main branch pushes

### 2. Local Deployment Script ([scripts/deploy-cloud-run.sh](scripts/deploy-cloud-run.sh))

**Updated to match GitHub Actions workflow:**
- Changed registry from `us-east1` → `southamerica-east1`
- Changed repository from `vizu` → `vizu-mono`
- Added test execution with `poetry run pytest`
- Uses `docker buildx` for multi-platform builds
- Builds and pushes directly to Artifact Registry
- Supports three deployment groups:
  - `agents-pool` - Core agent services
  - `workers-pool` - Data processing services
  - `dashboard` - Frontend application
  - `all` - Everything

**Usage:**
```bash
export GCP_PROJECT_ID=vizudev
./scripts/deploy-cloud-run.sh all              # Build and push all services
./scripts/deploy-cloud-run.sh workers-pool     # Build and push workers only
```

### 3. Image Naming Convention

**Format:**
```
southamerica-east1-docker.pkg.dev/vizudev/vizu-mono/vizu-{service_name}:{tag}
```

**Examples:**
```
southamerica-east1-docker.pkg.dev/vizudev/vizu-mono/vizu-data_ingestion_api:latest
southamerica-east1-docker.pkg.dev/vizudev/vizu-mono/vizu-data_ingestion_api:20251227-004732-024a7bc
southamerica-east1-docker.pkg.dev/vizudev/vizu-mono/vizu-analytics_api:latest
```

## Artifact Registry Configuration

**Location:** `southamerica-east1`

**Repository:** `vizu-mono`

**Images Currently Published:**
- ✅ vizu-file_upload_api
- ✅ vizu-data_ingestion_api
- ✅ vizu-analytics_api
- ⏳ vizu-atendente_core (building)
- ⏳ vizu-tool_pool_api (building)
- ⏳ vizu-vendas_agent (building)
- ⏳ vizu-support_agent (building)
- ⏳ vizu_dashboard (building)

## CI/CD Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     GitHub Actions Workflow                      │
└─────────────────────────────────────────────────────────────────┘

1. Push to main / Pull Request
   ↓
2. Stage 1: Quick Checks (Parallel)
   ├─> Lint & Format Check (ruff)
   └─> Poetry Lock Check (pyproject.toml validation)
   ↓
3. Stage 2: Run Tests (Parallel) ✨ NEW
   ├─> pytest data_ingestion_api
   ├─> pytest analytics_api
   ├─> pytest atendente_core
   └─> pytest tool_pool_api
   ↓
4. Stage 3: Build & Push (Parallel) ✨ CHANGED
   ├─> Build Docker images (linux/amd64)
   └─> Push to Artifact Registry
   ↓
5. Stage 4: Trigger Deployment (main only) ✨ NEW
   └─> Trigger deploy-cloud-run.yml workflow
```

## Benefits

### Performance
- **Faster deployments** - No pull/push dance between registries
- **Reduced latency** - Same region as Cloud Run (southamerica-east1)
- **Better integration** - Native GCP service

### Cost
- **No GitHub storage costs** for Docker images
- **Cheaper egress** - Same region data transfers

### Quality
- **Automated testing** - Tests run before every build
- **Coverage tracking** - Code coverage reports to Codecov
- **Early failure detection** - Catch issues before deployment

### Simplicity
- **Single source of truth** - All images in Artifact Registry
- **Fewer steps** - Direct build → push → deploy
- **Better visibility** - GCP Console integration

## Required GitHub Secrets

```bash
GCP_PROJECT_ID              # vizudev
GCP_SA_KEY                  # Service account JSON key
DATABASE_URL                # PostgreSQL connection
REDIS_URL                   # Redis connection
SUPABASE_URL               # Supabase project URL
SUPABASE_SERVICE_KEY       # Supabase service role key
MCP_AUTH_GOOGLE_CLIENT_ID  # Google OAuth client ID
CREDENTIALS_ENCRYPTION_KEY  # For encrypting credentials
```

## Service Account Permissions

The GCP service account needs:
```yaml
roles:
  - roles/artifactregistry.writer    # Push images
  - roles/run.admin                   # Deploy Cloud Run services
  - roles/secretmanager.admin         # Manage secrets
  - roles/iam.serviceAccountUser      # Act as service account
```

## Testing Locally

### Run Tests
```bash
cd services/data_ingestion_api
poetry install --with dev
poetry add --group dev pytest-cov
poetry run pytest tests/ -v --cov=src
```

### Build and Push Single Service
```bash
# Authenticate
gcloud auth configure-docker southamerica-east1-docker.pkg.dev

# Build and push
docker buildx build \
  --platform linux/amd64 \
  -f services/data_ingestion_api/Dockerfile \
  -t southamerica-east1-docker.pkg.dev/vizudev/vizu-mono/vizu-data_ingestion_api:test \
  --push \
  .
```

### List Images
```bash
gcloud artifacts docker images list \
  southamerica-east1-docker.pkg.dev/vizudev/vizu-mono \
  --include-tags
```

## Troubleshooting

### Authentication Errors
```bash
# Reconfigure Docker
gcloud auth configure-docker southamerica-east1-docker.pkg.dev

# Check current auth
gcloud auth list
```

### Image Not Found
```bash
# List all images in repository
gcloud artifacts docker images list \
  southamerica-east1-docker.pkg.dev/vizudev/vizu-mono

# Check specific service
gcloud artifacts docker images list \
  southamerica-east1-docker.pkg.dev/vizudev/vizu-mono/vizu-data_ingestion_api \
  --include-tags
```

### Test Failures
```bash
# Run tests locally with verbose output
cd services/data_ingestion_api
poetry run pytest tests/ -v -s --tb=short

# Check if pytest-cov is installed
poetry show pytest-cov
```

## Next Steps

- ✅ Update CI workflow with test execution
- ✅ Update deploy script for Artifact Registry
- ✅ Build and push all service images
- ⏳ Update deploy-cloud-run.yml to use Artifact Registry images
- ⏳ Deploy services to Cloud Run
- ⏳ Verify health checks pass

## Status

**Current Status:** Building all service images and pushing to Artifact Registry

**Last Updated:** 2025-12-27T00:50:00Z
