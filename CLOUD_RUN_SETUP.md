# Cloud Run Deployment Setup Guide

This guide walks you through setting up Cloud Run deployment for the vizu-mono monorepo on Google Cloud Platform.

## Prerequisites

### 1. Install Google Cloud SDK

**macOS (using Homebrew):**
```bash
brew install --cask google-cloud-sdk
```

**Verify installation:**
```bash
gcloud --version
```

### 2. Authenticate with GCP

```bash
# Initialize gcloud and authenticate
gcloud init

# Login to your Google account
gcloud auth login

# Set your GCP project
gcloud config set project YOUR_PROJECT_ID
```

Replace `YOUR_PROJECT_ID` with your actual GCP project ID.

**Verify configuration:**
```bash
gcloud config get-value project
```

## Step 1: Create Artifact Registry Repository

The workflow pushes Docker images to Google Artifact Registry in `us-east1` region.

### Create the repository:

```bash
gcloud artifacts repositories create vizu \
  --repository-format=docker \
  --location=us-east1 \
  --description="Vizu monorepo Docker images" \
  --project=$(gcloud config get-value project)
```

**Verify creation:**
```bash
gcloud artifacts repositories list --location=us-east1
```

You should see output like:
```
REPOSITORY  FORMAT  LOCATION  DESCRIPTION
vizu        DOCKER  us-east1  Vizu monorepo Docker images
```

## Step 2: Grant IAM Permissions to Service Account

The GitHub Actions workflow uses a service account (from `GCP_SA_KEY` secret) to push images and deploy services.

### Get your service account email:

The email is stored in GitHub secrets as `GCP_SA_EMAIL`. You can retrieve it from the JSON key file:

```bash
cat $HOME/.config/gcloud/YOUR_SA_KEY.json | grep "client_email"
```

Or ask your GCP admin for the service account email if you don't have the key locally.

### Grant necessary IAM roles:

```bash
PROJECT_ID=$(gcloud config get-value project)
SA_EMAIL="your-service-account@project-id.iam.gserviceaccount.com"

# Role: Artifact Registry admin (push/pull images)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member=serviceAccount:"$SA_EMAIL" \
  --role=roles/artifactregistry.admin

# Role: Cloud Run admin (deploy services)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member=serviceAccount:"$SA_EMAIL" \
  --role=roles/run.admin

# Role: Service Account user (impersonate for deployments)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member=serviceAccount:"$SA_EMAIL" \
  --role=roles/iam.serviceAccountUser
```

**Verify permissions:**
```bash
gcloud projects get-iam-policy $(gcloud config get-value project) \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:YOUR_SA_EMAIL" \
  --format="table(bindings.role)"
```

## Step 3: Verify GitHub Secrets

The workflow expects these secrets in your GitHub repository:

- `GCP_PROJECT_ID` — Your GCP project ID
- `GCP_SA_KEY` — Service account JSON key (base64 encoded or raw JSON)
- `GCP_SA_EMAIL` — Service account email

**Check your secrets:**

1. Go to: `https://github.com/vizubr/vizu-mono/settings/secrets/actions`
2. Verify all three secrets are present and non-empty

If any are missing, add them:

```bash
# Set these in GitHub Actions Secrets
GCP_PROJECT_ID="your-gcp-project-id"
GCP_SA_KEY='{"type": "service_account", ...}'  # Full JSON from service account key file
GCP_SA_EMAIL="sa-account@project-id.iam.gserviceaccount.com"
```

## Step 4: Cloud Run Service Configuration

The workflow automatically deploys these services:

### Agents Pool (public/internal APIs):
- **atendente-core** (public entry point)
  - Memory: 2Gi, CPU: 2
  - Concurrency: 10, Timeout: 3600s
  - Min instances: 1, Max instances: 50
  - Allow unauthenticated access (public)

- **tool-pool-api** (internal)
  - Memory: 2Gi, CPU: 2
  - Concurrency: 5, Timeout: 3600s
  - Min instances: 1, Max instances: 20
  - Internal only (no unauthenticated access)

- **vendas-agent** (internal)
  - Memory: 2Gi, CPU: 2
  - Concurrency: 10, Timeout: 3600s
  - Min instances: 0, Max instances: 20
  - Internal only

- **support-agent** (internal)
  - Memory: 2Gi, CPU: 2
  - Concurrency: 10, Timeout: 3600s
  - Min instances: 0, Max instances: 20
  - Internal only

### Workers Pool (background/async processing):
- **data-ingestion-worker** (internal)
  - Memory: 1Gi, CPU: 2
  - Concurrency: 50, Timeout: 600s
  - Min instances: 0, Max instances: 100
  - For PubSub-triggered data ingestion

- **file-processing-worker** (internal)
  - Memory: 2Gi, CPU: 2
  - Concurrency: 20, Timeout: 1800s
  - Min instances: 0, Max instances: 50
  - For file processing tasks

- **file-upload-api** (public)
  - Memory: 1Gi, CPU: 2
  - Concurrency: 50, Timeout: 300s
  - Min instances: 0, Max instances: 50
  - Allow unauthenticated access (public file upload)

## Step 5: Trigger Deployment

### Option A: Deploy via GitHub UI (Recommended)

1. Go to: `https://github.com/vizubr/vizu-mono/actions`
2. Select workflow: **"Deploy to Cloud Run"**
3. Click **"Run workflow"** dropdown
4. Select branch: `main`
5. Optional: Choose specific service pool:
   - Leave empty for all services
   - Or specify: `agents-pool` or `workers-pool`
6. Click **"Run workflow"**

Monitor the deployment in the Actions tab.

### Option B: Deploy via Git Push

Simply push to main and the workflow will automatically run:

```bash
git push origin main
```

Or trigger manually with the GitHub CLI:

```bash
gh workflow run deploy-cloud-run.yml --ref main
```

## Step 6: Verify Deployment

### View deployed services:

```bash
gcloud run services list --region=us-east1
```

Expected output:
```
SERVICE                  STATUS  LAST DEPLOYED            REGION    URL
atendente-core           ACTIVE  2025-12-12T10:30:00Z    us-east1  https://atendente-core-xyz.run.app
tool-pool-api            ACTIVE  2025-12-12T10:30:00Z    us-east1  https://tool-pool-api-xyz.run.app
vendas-agent             ACTIVE  2025-12-12T10:30:00Z    us-east1  https://vendas-agent-xyz.run.app
support-agent            ACTIVE  2025-12-12T10:30:00Z    us-east1  https://support-agent-xyz.run.app
data-ingestion-worker    ACTIVE  2025-12-12T10:30:00Z    us-east1  https://data-ingestion-worker-xyz.run.app
file-processing-worker   ACTIVE  2025-12-12T10:30:00Z    us-east1  https://file-processing-worker-xyz.run.app
file-upload-api          ACTIVE  2025-12-12T10:30:00Z    us-east1  https://file-upload-api-xyz.run.app
```

### Check service details:

```bash
# View service configuration
gcloud run services describe atendente-core --region=us-east1

# View service logs
gcloud run services logs read atendente-core --region=us-east1 --limit=100

# Test health endpoint (public services)
curl https://atendente-core-xyz.run.app/health
```

### View images in Artifact Registry:

```bash
gcloud artifacts docker images list us-east1-docker.pkg.dev/$(gcloud config get-value project)/vizu/
```

## Troubleshooting

### Permission Denied Errors

**Error:** `Permission denied: artifactregistry.repositories.uploadArtifacts`

**Solution:** Ensure the service account has the `roles/artifactregistry.admin` role:

```bash
gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
  --member=serviceAccount:YOUR_SA_EMAIL \
  --role=roles/artifactregistry.admin
```

### Image Pull Errors in Cloud Run

**Error:** `Failed to pull image: "us-east1-docker.pkg.dev/..."`

**Solution:** Ensure Cloud Run has permission to pull from Artifact Registry. The service account used by Cloud Run needs the `roles/run.admin` and `roles/iam.serviceAccountUser` roles (already granted in Step 2).

### Deployment Timeout

**Error:** `Deployment failed: timeout`

**Solution:** Check logs:

```bash
gcloud run services logs read <service-name> --region=us-east1 --limit=200
```

Or check the GitHub Actions workflow logs in the repository.

### Service Won't Start

**Debug steps:**

```bash
# Check service status
gcloud run services describe <service-name> --region=us-east1 --format='value(status)'

# View recent revisions
gcloud run revisions list --service=<service-name> --region=us-east1

# Check container logs
gcloud run services logs read <service-name> --region=us-east1 --limit=500 --format=json | jq '.[] | "\(.time): \(.jsonPayload.message // .textPayload)"'
```

## Environment Variables & Configuration

Services are deployed with basic environment variables:

```
ENVIRONMENT=production
LOG_LEVEL=INFO
```

To add additional environment variables or secrets:

### Option A: Update via gcloud CLI

```bash
gcloud run services update atendente-core \
  --region=us-east1 \
  --set-env-vars="VAR1=value1,VAR2=value2"
```

### Option B: Update deployment workflow

Edit `.github/workflows/deploy-cloud-run.yml` and add `--set-env-vars` arguments in the `deploy_service` calls.

### Option C: Use Cloud Run secret manager

For sensitive values, use Google Secret Manager:

```bash
# Create a secret
echo -n "my-secret-value" | gcloud secrets create MY_SECRET --data-file=-

# Grant Cloud Run access
gcloud secrets add-iam-policy-binding MY_SECRET \
  --member=serviceAccount:YOUR_SA_EMAIL \
  --role=roles/secretmanager.secretAccessor

# Deploy with secret
gcloud run services update atendente-core \
  --region=us-east1 \
  --set-secrets="SECRET_VAR=MY_SECRET:latest"
```

## Networking & Service Communication

### Internal Service Communication

Services deployed with `--ingress internal` can only be called from other Cloud Run services in the same project.

**From atendente-core to tool-pool-api:**

```python
# Use the Cloud Run service URL
BASE_URL = "https://tool-pool-api-xxxxxxxx.run.app"

async def call_tool_pool():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/tools")
```

Cloud Run automatically handles authentication between services using ID tokens.

### Public Service Access

Services with `--allow-unauthenticated` are accessible via public URLs:
- `atendente-core` → `https://atendente-core-xxx.run.app`
- `file-upload-api` → `https://file-upload-api-xxx.run.app`

### Custom Domains (Optional)

To use your own domain:

```bash
gcloud run domain-mappings create \
  --service=atendente-core \
  --domain=api.yourdomain.com \
  --region=us-east1
```

Then point your DNS to the Cloud Run service.

## Monitoring & Scaling

### View metrics:

```bash
# CPU/Memory utilization
gcloud monitoring timeseries list \
  --filter='resource.type="cloud_run_revision" AND metric.type="run.googleapis.com/request_count"'
```

Or use the Cloud Console:
1. Go to: https://console.cloud.google.com/run
2. Click on a service
3. View "Metrics" tab for CPU, memory, request count, latency

### Auto-scaling configuration:

Services are already configured with:
- `--max-instances`: Maximum number of concurrent instances
- `--min-instances`: Minimum number to keep warm (0 = cold start)
- `--concurrency`: Max concurrent requests per instance

To adjust:

```bash
gcloud run services update atendente-core \
  --region=us-east1 \
  --max-instances=100 \
  --min-instances=2 \
  --concurrency=20
```

## Cost Optimization

Cloud Run billing is based on:
1. **vCPU-seconds** (compute time)
2. **Memory-seconds** (memory allocation)
3. **Requests** (first 2M free per month)

### Tips to reduce costs:

- Set `--min-instances=0` for non-critical services (they start on-demand)
- Lower `--memory` if workload allows (minimum: 128Mi)
- Use internal ingress where possible (saves egress bandwidth)
- Optimize container image size (reduce layers, base image size)
- Monitor and adjust concurrency settings based on load

## Next Steps

1. **Install gcloud SDK** (Step 1 of this guide)
2. **Authenticate and set up Artifact Registry** (Steps 1-2)
3. **Verify GitHub secrets** (Step 3)
4. **Review and adjust Cloud Run service config** if needed (Step 4)
5. **Trigger first deployment** (Step 5)
6. **Monitor deployment and verify services are running** (Step 6)

## References

- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Artifact Registry Documentation](https://cloud.google.com/artifact-registry/docs)
- [GitHub Actions gcloud Setup](https://github.com/google-github-actions/setup-gcloud)
- [Cloud Run Pricing](https://cloud.google.com/run/pricing)
