# Quick Fix: Artifact Registry Setup for vizudev

## Run these commands to fix the deployment issue

### 1. Install gcloud CLI (if not already installed)
```bash
brew install --cask google-cloud-sdk
```

### 2. Authenticate and configure
```bash
gcloud init
gcloud auth login
gcloud config set project vizudev
```

### 3. Create the vizu-mono repository in Artifact Registry
```bash
gcloud artifacts repositories create vizu-mono \
  --repository-format=docker \
  --location=us-east1 \
  --description="Vizu monorepo Docker images"
```

**Verify it was created:**
```bash
gcloud artifacts repositories list --location=us-east1
```

Output should show:
```
REPOSITORY   FORMAT  LOCATION  DESCRIPTION
vizu-mono    DOCKER  us-east1  Vizu monorepo Docker images
```

### 4. Grant IAM permissions to your service account

Replace `YOUR_SA_EMAIL` with the email from your `GCP_SA_EMAIL` GitHub secret:

```bash
PROJECT_ID=vizudev
SA_EMAIL="YOUR_SA_EMAIL"  # Replace this with the actual email

# Grant Artifact Registry Admin
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member=serviceAccount:"$SA_EMAIL" \
  --role=roles/artifactregistry.admin

# Grant Cloud Run Admin
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member=serviceAccount:"$SA_EMAIL" \
  --role=roles/run.admin

# Grant Service Account User
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member=serviceAccount:"$SA_EMAIL" \
  --role=roles/iam.serviceAccountUser
```

**Verify permissions were granted:**
```bash
gcloud projects get-iam-policy vizudev \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:YOUR_SA_EMAIL" \
  --format="table(bindings.role)"
```

Should show 3 roles:
- `roles/artifactregistry.admin`
- `roles/run.admin`
- `roles/iam.serviceAccountUser`

## 5. Trigger deployment

Once the repository is created and permissions are set, the workflow will automatically:
1. Build Docker images for all 7 services
2. Push them to `us-east1-docker.pkg.dev/vizudev/vizu-mono/`
3. Deploy to Cloud Run services

### Option A: Push to main (automatic trigger)
```bash
git push origin main
```

### Option B: Manually trigger via GitHub Actions
Go to: https://github.com/vizubr/vizu-mono/actions/workflows/deploy-cloud-run.yml
Click "Run workflow" → Select "main" → Confirm

### Option C: Use GitHub CLI
```bash
gh workflow run deploy-cloud-run.yml --ref main
```

## 6. Verify deployment

After the workflow completes, check that services are deployed:

```bash
# List all Cloud Run services
gcloud run services list --region=us-east1

# View images in Artifact Registry
gcloud artifacts docker images list \
  us-east1-docker.pkg.dev/vizudev/vizu-mono/

# Check logs of a service
gcloud run services logs read atendente-core --region=us-east1 --limit=50
```

## What Changed in the Workflow

The deployment workflow was updated to use the correct repository name:

**Before:**
```
us-east1-docker.pkg.dev/vizudev/vizu/vizu-{service}
```

**After (Updated):**
```
us-east1-docker.pkg.dev/vizudev/vizu-mono/vizu-{service}
```

The commit `7000cac` fixed the workflow to use `vizu-mono` as the repository name in all places.

## Summary of What You Need to Do

1. ✅ Workflow updated (already done - commit 7000cac)
2. ⏭️ **Create the `vizu-mono` repository in Artifact Registry** (run step 3 above)
3. ⏭️ **Grant IAM permissions** (run step 4 above)
4. ⏭️ **Trigger deployment** (run step 5 above)
5. ⏭️ **Verify services are running** (run step 6 above)

Questions? Check `CLOUD_RUN_SETUP.md` for detailed troubleshooting.
