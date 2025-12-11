# VIZU Cloud Run Deployment Guide

## Overview

VIZU is deployed to Google Cloud Run using a **3-group architecture**. The CI/CD pipeline builds images, publishes to GHCR, and deploys to Cloud Run automatically on push to `main`.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    CI/CD Pipeline                                       │
├─────────────────────────────────────────────────────────────────────────┤
│  1. Lint (ruff) → 2. Dependency Check → 3. Docker Build                │
│  4. Publish to GHCR → 5. Deploy to Cloud Run                           │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                    Google Cloud Run Services                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  GROUP 1: agents-pool (PUBLIC)                                         │
│  ├─ atendente-core     → Main LLM agent (entry point)                 │
│  ├─ tool-pool-api      → Tool orchestration (internal)                │
│  ├─ vendas-agent       → Sales agent (internal)                       │
│  └─ support-agent      → Support agent (internal)                     │
│                                                                         │
│  GROUP 2: workers-pool                                                 │
│  ├─ data-ingestion-worker  → Data processing (internal)               │
│  ├─ file-processing-worker → File processing (internal)               │
│  └─ file-upload-api        → File upload (public)                     │
│                                                                         │
│  GROUP 3: embedding-service (INTERNAL)                                 │
│  └─ embedding-service  → Shared embedding inference                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## GitHub Actions Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | Push/PR to main | Lint, build Docker images, publish to GHCR |
| `deploy-cloud-run.yml` | Push to main (services/libs changes) | Build & deploy to Cloud Run |
| `secret-scan.yml` | Push/PR | Detect leaked secrets |

## Prerequisites

### 1. Install gcloud CLI
```bash
# macOS
brew install --cask google-cloud-sdk

# Linux
curl https://sdk.cloud.google.com | bash
```

### 2. Authenticate
```bash
gcloud auth login
gcloud config set project YOUR_GCP_PROJECT_ID
```

### 3. Enable APIs
```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com
```

## Step 1: Create Artifact Registry

```bash
gcloud artifacts repositories create vizu \
  --repository-format=docker \
  --location=us-east1 \
  --description="VIZU container images"
```

## Step 2: Create Service Account

```bash
# Create service account
gcloud iam service-accounts create vizu-deployer \
  --display-name="VIZU Cloud Run Deployer"

# Grant permissions
PROJECT_ID=$(gcloud config get-value project)

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:vizu-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:vizu-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:vizu-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Create and download key
gcloud iam service-accounts keys create ~/vizu-deployer-key.json \
  --iam-account=vizu-deployer@$PROJECT_ID.iam.gserviceaccount.com
```

## Step 3: Create Secrets in Google Secret Manager

```bash
# Database URL
echo -n "postgresql://user:pass@host:5432/db" | \
  gcloud secrets create database-url --data-file=-

# Google API Key
echo -n "your-google-api-key" | \
  gcloud secrets create google-api-key --data-file=-

# Supabase Key
echo -n "your-supabase-key" | \
  gcloud secrets create supabase-key --data-file=-

# Langfuse Secret
echo -n "your-langfuse-secret" | \
  gcloud secrets create langfuse-secret --data-file=-
```

## Step 4: Configure GitHub Secrets

Add these secrets in GitHub repo settings (Settings → Secrets → Actions):

| Secret | Description | Required |
|--------|-------------|----------|
| `GCP_PROJECT_ID` | Your GCP project ID | ✅ |
| `GCP_SA_KEY` | Service account key JSON (NOT base64) | ✅ |
| `GCP_SA_EMAIL` | Service account email | ✅ |
| `GITHUB_TOKEN` | Auto-provided by GitHub for GHCR | Auto |

> **Note**: The `GCP_SA_KEY` should be the raw JSON key file content, not base64-encoded.

## Step 5: Deploy

### Automatic Deployment (Recommended)
Push to `main` branch triggers the full CI/CD pipeline:
1. **ci.yml**: Lint → Build → Publish to GHCR
2. **deploy-cloud-run.yml**: Build → Push to Artifact Registry → Deploy to Cloud Run

### Manual Deployment via GitHub Actions
Go to Actions → "Deploy to Cloud Run" → Run workflow → Select service group.

### Manual Deployment via CLI
```bash
# Deploy all services
./scripts/deploy-cloud-run.sh all

# Deploy specific group
./scripts/deploy-cloud-run.sh agents-pool
./scripts/deploy-cloud-run.sh workers-pool
./scripts/deploy-cloud-run.sh embedding-service
```

## Service Configuration

### agents-pool

| Service | Memory | CPU | Concurrency | Timeout | Min | Max |
|---------|--------|-----|-------------|---------|-----|-----|
| atendente-core | 2Gi | 2 | 10 | 3600s | 1 | 50 |
| tool-pool-api | 2Gi | 2 | 5 | 3600s | 1 | 20 |
| vendas-agent | 2Gi | 2 | 10 | 3600s | 0 | 20 |
| support-agent | 2Gi | 2 | 10 | 3600s | 0 | 20 |

### workers-pool

| Service | Memory | CPU | Concurrency | Timeout | Min | Max |
|---------|--------|-----|-------------|---------|-----|-----|
| data-ingestion-worker | 1Gi | 2 | 50 | 600s | 0 | 100 |
| file-processing-worker | 2Gi | 2 | 20 | 1800s | 0 | 50 |
| file-upload-api | 1Gi | 2 | 50 | 300s | 0 | 50 |

### embedding-service

| Service | Memory | CPU | Concurrency | Timeout | Min | Max |
|---------|--------|-----|-------------|---------|-----|-----|
| embedding-service | 2Gi | 2 | 50 | 60s | 1 | 50 |

## Monitoring

### View Logs
```bash
gcloud run logs read atendente-core --region=us-east1 --limit=50
```

### Check Service Status
```bash
gcloud run services list --region=us-east1
```

### Get Service URL
```bash
gcloud run services describe atendente-core --region=us-east1 --format='value(status.url)'
```

## Troubleshooting

### Service not starting
```bash
# Check detailed logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=atendente-core" --limit=50

# Check revision status
gcloud run revisions list --service=atendente-core --region=us-east1
```

### Permission denied
```bash
# Verify service account permissions
gcloud projects get-iam-policy $PROJECT_ID \
  --filter="bindings.members:vizu-deployer"
```

### Secret not accessible
```bash
# Grant secret access
gcloud secrets add-iam-policy-binding database-url \
  --member="serviceAccount:vizu-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## Cost Estimation

| Service Group | Est. Monthly Cost |
|---------------|-------------------|
| agents-pool | $150-250 |
| workers-pool | $50-100 |
| embedding-service | $80-150 |
| **Total** | **$280-500** |

*Based on moderate usage. Actual costs vary with traffic.*
