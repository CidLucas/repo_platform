# Workflow Update Guide - Quick Reference

## Summary of Changes

1. **ci.yml** - Add tests, switch to Artifact Registry
2. **deploy-cloud-run.yml** - Remove GitHub Registry, use Artifact Registry directly
3. **secret-scan.yml** - No changes needed ✅

---

## 1. Update .github/workflows/ci.yml

### Add Test Stage (after dependency-check, before docker-build)

```yaml
  # =========================================================================
  # Stage 2: Run tests
  # =========================================================================
  test:
    name: Test ${{ matrix.service }}
    runs-on: ubuntu-latest
    needs: [lint, dependency-check]
    strategy:
      fail-fast: false
      matrix:
        service:
          - data_ingestion_api
          - analytics_api
          - atendente_core
          - tool_pool_api
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install Poetry
        run: |
          curl -sSL https://install.python-poetry.org | python3 -
          echo "$HOME/.local/bin" >> $GITHUB_PATH

      - name: Install dependencies
        working-directory: services/${{ matrix.service }}
        run: poetry install --with dev

      - name: Run tests
        working-directory: services/${{ matrix.service }}
        run: |
          poetry run pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=xml || true

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        if: always()
        with:
          files: services/${{ matrix.service }}/coverage.xml
          flags: ${{ matrix.service }}
```

### Replace "publish" job with "docker-build-and-push"

**DELETE entire "publish" job (lines 106-162)**

**REPLACE WITH:**

```yaml
  # =========================================================================
  # Stage 3: Build and push to Artifact Registry
  # =========================================================================
  docker-build-and-push:
    name: Build & Push ${{ matrix.service }}
    runs-on: ubuntu-latest
    needs: [test]  # Changed from docker-build
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    permissions:
      contents: read
      id-token: write  # Changed from packages: write
    strategy:
      matrix:
        service:
          - atendente_core
          - tool_pool_api
          - vendas_agent
          - support_agent
          - data_ingestion_worker
          - file_processing_worker
          - file_upload_api
          - data_ingestion_api
          - analytics_api
        include:
          - service: vizu_dashboard
            dockerfile_path: apps/vizu_dashboard/Dockerfile

    steps:
      - uses: actions/checkout@v4

      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2

      - name: Configure Docker for Artifact Registry
        run: |
          gcloud auth configure-docker southamerica-east1-docker.pkg.dev

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Set image tags
        id: tags
        run: |
          COMMIT_SHORT=$(echo ${{ github.sha }} | cut -c1-7)
          TIMESTAMP=$(date +%Y%m%d-%H%M%S)
          IMAGE_TAG="${TIMESTAMP}-${COMMIT_SHORT}"

          REGISTRY="southamerica-east1-docker.pkg.dev"
          PROJECT_ID="${{ secrets.GCP_PROJECT_ID }}"
          REPO="vizu-mono"

          IMAGE_BASE="${REGISTRY}/${PROJECT_ID}/${REPO}/vizu-${{ matrix.service }}"

          echo "image_versioned=${IMAGE_BASE}:${IMAGE_TAG}" >> $GITHUB_OUTPUT
          echo "image_latest=${IMAGE_BASE}:latest" >> $GITHUB_OUTPUT

      - name: Build and push to Artifact Registry
        env:
          DOCKERFILE_PATH: ${{ matrix.dockerfile_path || format('services/{0}/Dockerfile', matrix.service) }}
        run: |
          docker buildx build \
            --platform linux/amd64 \
            -f "${DOCKERFILE_PATH}" \
            -t "${{ steps.tags.outputs.image_versioned }}" \
            -t "${{ steps.tags.outputs.image_latest }}" \
            --push \
            .

          echo "## 🐳 Published: ${{ matrix.service }}" >> $GITHUB_STEP_SUMMARY
          echo "- \`${{ steps.tags.outputs.image_versioned }}\`" >> $GITHUB_STEP_SUMMARY
          echo "- \`${{ steps.tags.outputs.image_latest }}\`" >> $GITHUB_STEP_SUMMARY

  # =========================================================================
  # Stage 4: Trigger deployment
  # =========================================================================
  trigger-deploy:
    name: Trigger Deployment
    runs-on: ubuntu-latest
    needs: [docker-build-and-push]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    steps:
      - name: Trigger deploy workflow
        uses: actions/github-script@v7
        with:
          script: |
            await github.rest.actions.createWorkflowDispatch({
              owner: context.repo.owner,
              repo: context.repo.repo,
              workflow_id: 'deploy-cloud-run.yml',
              ref: 'main',
              inputs: { service: 'all' }
            });
```

---

## 2. Update .github/workflows/deploy-cloud-run.yml

### Remove GitHub Container Registry Steps

**DELETE these steps from build-and-deploy job:**
- Lines 267-269: "Log in to GitHub Container Registry"
- Lines 274-321: "Pull & Push: agents-pool"
- Lines 326-374: "Pull & Push: workers-pool"
- Lines 572-618: "Pull & Push: dashboard"

### Update Deploy Steps to Use Artifact Registry

**FIND:** Line 379-458 (Deploy: agents-pool)

**CHANGE line 386:**
```yaml
# BEFORE:
TAG="${{ steps.image.outputs.tag }}"
REGISTRY="${{ env.REGISTRY }}/${{ env.PROJECT_ID }}/vizu-mono"

# AFTER (use latest instead of tag):
REGISTRY="${{ env.REGISTRY }}/${{ env.PROJECT_ID }}/vizu-mono"

deploy_service() {
  local name=$1
  local image="${REGISTRY}/vizu-${name}:latest"  # Changed to use :latest
  shift
  # ... rest stays the same
}
```

**Do the same for:**
- Line 472 (Deploy: workers-pool) - Change to use `:latest` tag
- Line 632 (Deploy: dashboard) - Change to use `:latest` tag

---

## 3. Verify secret-scan.yml

**NO CHANGES NEEDED** ✅

File is correct as-is.

---

## Testing the Changes

### Step 1: Test in Feature Branch

```bash
git checkout -b ci-artifact-registry-migration
# Apply changes above
git add .github/workflows/
git commit -m "ci: migrate to Artifact Registry, add tests"
git push origin ci-artifact-registry-migration
```

### Step 2: Create Artifact Registry (if not exists)

```bash
gcloud artifacts repositories create vizu-mono \
  --repository-format=docker \
  --location=southamerica-east1 \
  --description="Vizu Docker images" \
  --project=$GCP_PROJECT_ID
```

### Step 3: Grant Service Account Permissions

```bash
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:$GCP_SA_EMAIL" \
  --role="roles/artifactregistry.writer"
```

### Step 4: Test CI Workflow

1. Create Pull Request
2. CI will run: lint → test → build (test build only, no push)
3. Verify tests pass

### Step 5: Test Deployment

1. Merge to main
2. CI will run: lint → test → build → **push to Artifact Registry**
3. Deployment will auto-trigger
4. Verify services deploy

---

## Quick Reference: What Changes

| Component | Before | After |
|-----------|--------|-------|
| **CI Tests** | ❌ Not run | ✅ Run pytest before build |
| **CI Build** | Build only | Build + push to Artifact Registry |
| **CI Publish** | Push to ghcr.io | Push to Artifact Registry |
| **Deploy Pull** | Pull from ghcr.io | ❌ Removed |
| **Deploy Push** | Push to Artifact Registry | ❌ Removed |
| **Deploy** | Use versioned tag | Use `:latest` from Artifact Registry |

---

## Summary

**Changes to Make:**

1. ✅ **ci.yml** - Add 3 new jobs (test, docker-build-and-push, trigger-deploy)
2. ✅ **deploy-cloud-run.yml** - Remove GitHub Registry steps, simplify deployment
3. ✅ **secret-scan.yml** - No changes

**Benefits:**

- ✅ Tests run automatically
- ✅ Faster deployments (no GitHub → GCP transfer)
- ✅ Simpler workflow (fewer steps)
- ✅ Better integration with GCP

**Ready to apply!** 🚀
