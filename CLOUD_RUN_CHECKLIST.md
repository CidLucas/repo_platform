# Cloud Run Setup Checklist

Complete this checklist to get your vizu-mono services running on Cloud Run.

## Phase 1: Local Setup

- [ ] **Install Google Cloud SDK**
  ```bash
  brew install --cask google-cloud-sdk
  ```
  Command to verify: `gcloud --version`

- [ ] **Initialize gcloud and authenticate**
  ```bash
  gcloud init
  gcloud auth login
  gcloud config set project YOUR_PROJECT_ID
  ```
  Verify: `gcloud config get-value project`

## Phase 2: GCP Infrastructure

- [ ] **Create Artifact Registry repository** (us-east1)
  ```bash
  gcloud artifacts repositories create vizu \
    --repository-format=docker \
    --location=us-east1 \
    --description="Vizu monorepo Docker images"
  ```
  Verify: `gcloud artifacts repositories list --location=us-east1`

- [ ] **Grant IAM permissions to service account**
  
  Get your service account email first:
  - Option A: From GitHub secret `GCP_SA_EMAIL`
  - Option B: From your service account JSON key file
  
  ```bash
  PROJECT_ID=$(gcloud config get-value project)
  SA_EMAIL="your-service-account@project-id.iam.gserviceaccount.com"
  
  # Grant 3 roles
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member=serviceAccount:"$SA_EMAIL" \
    --role=roles/artifactregistry.admin
  
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member=serviceAccount:"$SA_EMAIL" \
    --role=roles/run.admin
  
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member=serviceAccount:"$SA_EMAIL" \
    --role=roles/iam.serviceAccountUser
  ```
  
  Verify: `gcloud projects get-iam-policy $(gcloud config get-value project) --flatten="bindings[].members" --filter="bindings.members:serviceAccount:YOUR_SA_EMAIL" --format="table(bindings.role)"`

- [ ] **Verify GitHub secrets are set**
  
  Go to: https://github.com/vizubr/vizu-mono/settings/secrets/actions
  
  Required secrets:
  - [ ] `GCP_PROJECT_ID` = your project ID
  - [ ] `GCP_SA_KEY` = service account JSON key
  - [ ] `GCP_SA_EMAIL` = service account email

## Phase 3: Trigger Deployment

- [ ] **Deploy via GitHub Actions**
  
  Option A (UI):
  1. Go to: https://github.com/vizubr/vizu-mono/actions
  2. Select: "Deploy to Cloud Run" workflow
  3. Click: "Run workflow"
  4. Confirm deployment
  
  Option B (CLI):
  ```bash
  gh workflow run deploy-cloud-run.yml --ref main
  ```
  
  Option C (Git push):
  ```bash
  git push origin main
  ```

- [ ] **Monitor deployment progress**
  
  Go to: https://github.com/vizubr/vizu-mono/actions
  
  Expected jobs:
  - [ ] preflight-checks ✅
  - [ ] build-and-deploy (agents-pool) ✅
  - [ ] build-and-deploy (workers-pool) ✅
  - [ ] health-checks ✅

## Phase 4: Verify Deployment

- [ ] **List deployed services**
  ```bash
  gcloud run services list --region=us-east1
  ```
  
  Expected services (7 total):
  - [ ] atendente-core (public)
  - [ ] tool-pool-api (internal)
  - [ ] vendas-agent (internal)
  - [ ] support-agent (internal)
  - [ ] data-ingestion-worker (internal)
  - [ ] file-processing-worker (internal)
  - [ ] file-upload-api (public)

- [ ] **View images in Artifact Registry**
  ```bash
  gcloud artifacts docker images list \
    us-east1-docker.pkg.dev/$(gcloud config get-value project)/vizu/
  ```
  
  Expected images: 7 services with format `vizu-{service-name}:{timestamp}-{commit-sha}`

- [ ] **Test public service (atendente-core)**
  ```bash
  # Get service URL
  CORE_URL=$(gcloud run services describe atendente-core \
    --region=us-east1 --format='value(status.url)')
  
  # Test health endpoint
  curl "$CORE_URL/health"
  
  # Expected response: 200 OK with health status
  ```

- [ ] **Test file upload API (public)**
  ```bash
  # Get service URL
  UPLOAD_URL=$(gcloud run services describe file-upload-api \
    --region=us-east1 --format='value(status.url)')
  
  # Test health endpoint
  curl "$UPLOAD_URL/health"
  ```

## Phase 5: Post-Deployment (Optional)

- [ ] **View service logs**
  ```bash
  # Recent logs
  gcloud run services logs read atendente-core \
    --region=us-east1 --limit=100
  ```

- [ ] **Check service configuration**
  ```bash
  gcloud run services describe atendente-core \
    --region=us-east1 --format=json | jq '.spec.template.spec'
  ```

- [ ] **View metrics in Cloud Console**
  
  Go to: https://console.cloud.google.com/run?region=us-east1
  
  For each service, check:
  - [ ] Status = ACTIVE
  - [ ] Latest revision deployed
  - [ ] No errors in "Requests" metric

- [ ] **Set up custom domain (optional)**
  
  If you want to use your own domain:
  ```bash
  gcloud run domain-mappings create \
    --service=atendente-core \
    --domain=api.yourdomain.com \
    --region=us-east1
  ```
  
  Then update DNS to point to Cloud Run.

- [ ] **Configure secret manager for sensitive data (optional)**
  
  For environment variables that need to be secrets:
  ```bash
  # Create a secret
  echo -n "my-secret-value" | gcloud secrets create MY_SECRET --data-file=-
  
  # Grant access to service
  gcloud secrets add-iam-policy-binding MY_SECRET \
    --member=serviceAccount:YOUR_SA_EMAIL \
    --role=roles/secretmanager.secretAccessor
  
  # Update service to use secret
  gcloud run services update atendente-core \
    --region=us-east1 \
    --set-secrets="SECRET_VAR=MY_SECRET:latest"
  ```

## Troubleshooting

### Problem: "Permission denied" during deployment

**Check IAM roles:**
```bash
gcloud projects get-iam-policy $(gcloud config get-value project) \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:YOUR_SA_EMAIL"
```

Should show at least 3 roles (artifactregistry.admin, run.admin, iam.serviceAccountUser).

### Problem: Images not found in Artifact Registry

**Check image push:**
```bash
# List images
gcloud artifacts docker images list \
  us-east1-docker.pkg.dev/$(gcloud config get-value project)/vizu/

# If empty, check GitHub Actions logs for build failures
```

### Problem: Cloud Run service won't start

**View detailed logs:**
```bash
gcloud run services logs read <service-name> \
  --region=us-east1 --limit=500
```

**Check latest revision:**
```bash
gcloud run revisions list --service=<service-name> --region=us-east1
```

### Problem: "Repository not found" when building

**Verify repository exists:**
```bash
gcloud artifacts repositories list --location=us-east1
```

Should show repository named `vizu` in `DOCKER` format.

## Success Criteria

✅ Deployment is complete when:
1. All 7 Cloud Run services are in `ACTIVE` status
2. All 7 Docker images are in Artifact Registry (us-east1)
3. Public endpoints respond to health checks:
   - `https://atendente-core-xxx.run.app/health` → 200 OK
   - `https://file-upload-api-xxx.run.app/health` → 200 OK
4. GitHub Actions workflow "Deploy to Cloud Run" shows success ✅
5. No errors in service logs from last 10 minutes

## Quick Reference: Service URLs

After deployment, services will be available at:

```
Public Services:
- atendente-core (entry point): https://atendente-core-[hash].run.app
- file-upload-api: https://file-upload-api-[hash].run.app

Internal Services (Cloud Run only):
- tool-pool-api: https://tool-pool-api-[hash].run.app
- vendas-agent: https://vendas-agent-[hash].run.app
- support-agent: https://support-agent-[hash].run.app
- data-ingestion-worker: https://data-ingestion-worker-[hash].run.app
- file-processing-worker: https://file-processing-worker-[hash].run.app
```

To get actual URLs:
```bash
gcloud run services list --region=us-east1 --format="table(name,status.url)"
```

## Documentation

- **Full Setup Guide:** See `CLOUD_RUN_SETUP.md`
- **Architecture Guide:** See `.github/copilot-instructions.md`
- **Deployment Workflow:** `.github/workflows/deploy-cloud-run.yml`
