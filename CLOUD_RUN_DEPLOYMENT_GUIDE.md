# Cloud Run Deployment & Authentication Guide

## Current Issues & Solutions

### Issue 1: Dashboard Shows "placeholder.supabase.co"

**Root Cause:** Vite environment variables not passed during Docker build in CI.

**Solution:** Updated `.github/workflows/ci.yml` to pass build arguments for dashboard:

```yaml
# Build arguments for dashboard (Vite environment variables)
BUILD_ARGS=""
if [[ "${{ matrix.service }}" == "dashboard" ]]; then
  BUILD_ARGS="--build-arg VITE_SUPABASE_URL=${{ secrets.VITE_SUPABASE_URL }} \
    --build-arg VITE_SUPABASE_ANON_KEY=${{ secrets.VITE_SUPABASE_ANON_KEY }} \
    --build-arg VITE_GOOGLE_CLIENT_ID=${{ secrets.GOOGLE_CLIENT_ID }} \
    --build-arg VITE_API_URL_ANALYTICS=https://analytics-api-xxx.run.app"
fi
```

### Issue 2: CORS Errors from Backend

**Error:**
```
Access to XMLHttpRequest at 'http://localhost:8004/api/dashboard/home_gold'
from origin 'http://localhost:3001' has been blocked by CORS policy
```

**Root Cause:** The dashboard is trying to call `localhost:8004` but it's deployed to Cloud Run.

**Solution:** Update the Vite environment variables to use Cloud Run URLs instead of localhost:

```bash
# GitHub Secrets to update:
VITE_API_URL_ANALYTICS=https://analytics-api-qrfhgfkvja-rj.a.run.app
VITE_ATENDENTE_CORE=https://atendente-core-qrfhgfkvja-rj.a.run.app
VITE_DATA_INGESTION_API_URL=https://data-ingestion-api-qrfhgfkvja-rj.a.run.app
```

### Issue 3: Authentication Bypassed (Goes Straight to Home)

**Root Cause:** The authentication flow needs proper Supabase configuration.

**Check:**
1. Supabase OAuth is configured correctly
2. Google OAuth redirect URI matches Cloud Run URL
3. Authentication middleware is enabled

## Cloud Run Authentication Configuration

### Service-by-Service Authentication Settings

| Service | Authentication | Reason |
|---------|---------------|---------|
| **vizu-dashboard** | ❌ Allow unauthenticated | Public website - users access from browser |
| **analytics-api** | ❌ Allow unauthenticated | Dashboard calls from browser (CORS-enabled) |
| **data-ingestion-api** | ❌ Allow unauthenticated | Dashboard calls from browser |
| **atendente-core** | ❌ Allow unauthenticated | Dashboard calls from browser |
| **tool-pool-api** | ✅ Require authentication | Internal service (server-to-server only) |
| **file-upload-api** | ❌ Allow unauthenticated | Uploads from dashboard |

### IAM vs IAP

**Use IAM (Identity and Access Management):** ✅ **RECOMMENDED**
- For service-to-service communication
- Control which service accounts can invoke services
- Works with application-level authentication (Supabase)

**Use IAP (Identity-Aware Proxy):** ❌ NOT NEEDED
- Adds Google-based user authentication BEFORE app
- Creates additional auth layer (redundant with Supabase)
- More complex setup

**Your Configuration:**
```
✅ Use: Identity and Access Management (IAM)
❌ Don't use: Identity-Aware Proxy (IAP)
```

## Required GitHub Secrets

Verify these secrets are set correctly:

### Supabase
```bash
SUPABASE_URL=https://haruewffnubdgyofftut.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... (service_role key)
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... (same as SERVICE_KEY, for backward compat)
SUPABASE_JWT_SECRET=your-jwt-secret

# Frontend (Vite) - These are PUBLIC and embedded in bundle
VITE_SUPABASE_URL=https://haruewffnubdgyofftut.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... (anon/public key)
```

### Google OAuth
```bash
GOOGLE_CLIENT_ID=858493958314-pse71gsmcsqe8a7e392stjlravbhqdtc.apps.googleusercontent.com
VITE_GOOGLE_CLIENT_ID=858493958314-pse71gsmcsqe8a7e392stjlravbhqdtc.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxx
GOOGLE_REDIRECT_URI=https://haruewffnubdgyofftut.supabase.co/auth/v1/callback
```

### Backend API URLs (Production - Cloud Run)
```bash
VITE_API_URL_ANALYTICS=https://analytics-api-qrfhgfkvja-rj.a.run.app
VITE_ATENDENTE_CORE=https://atendente-core-qrfhgfkvja-rj.a.run.app
VITE_DATA_INGESTION_API_URL=https://data-ingestion-api-qrfhgfkvja-rj.a.run.app
```

### GCP
```bash
GCP_PROJECT_ID=vizudev
GCP_SA_EMAIL=github-actions@vizudev.iam.gserviceaccount.com
GCP_SA_KEY=<base64-encoded-service-account-json>
```

## Authentication Flow

### Correct Flow (Supabase Auth)

```
1. User visits: https://vizu-dashboard-xxx.run.app
   ↓
2. Dashboard loads with Supabase client (from VITE_SUPABASE_URL)
   ↓
3. User not authenticated → Show login page
   ↓
4. User clicks "Sign in with Google"
   ↓
5. Redirect to Supabase: https://haruewffnubdgyofftut.supabase.co/auth/v1/authorize?...
   ↓
6. Supabase redirects to Google OAuth
   ↓
7. User authorizes → Google redirects back to Supabase
   ↓
8. Supabase creates session → Redirects to dashboard with token
   ↓
9. Dashboard stores token in localStorage
   ↓
10. Dashboard makes API calls with Authorization: Bearer <token>
```

### What You're Seeing (Bypassed)

```
1. User visits dashboard
   ↓
2. Immediately goes to home page (no login)
   ↓
❌ Problem: Authentication check not working or session persisted
```

**Possible causes:**
1. Session stored in localStorage from previous login
2. Authentication guard not implemented
3. Supabase session auto-refresh enabled

## Fixing the Issues

### Step 1: Update GitHub Secrets

Update these secrets to use Cloud Run URLs (not localhost):

```bash
# Go to: https://github.com/your-org/vizu-mono/settings/secrets/actions

# Update:
VITE_API_URL_ANALYTICS → https://analytics-api-qrfhgfkvja-rj.a.run.app
VITE_ATENDENTE_CORE → https://atendente-core-qrfhgfkvja-rj.a.run.app
VITE_DATA_INGESTION_API_URL → https://data-ingestion-api-qrfhgfkvja-rj.a.run.app
```

### Step 2: Rebuild Dashboard with CI

Push changes to trigger CI build:
```bash
git add .github/workflows/ci.yml
git commit -m "fix: add Vite build args for dashboard"
git push origin main
```

This will rebuild the dashboard with the correct environment variables embedded.

### Step 3: Configure Cloud Run Authentication

For each service, set authentication:

```bash
# Dashboard - Public
gcloud run services update vizu-dashboard \
  --region=southamerica-east1 \
  --allow-unauthenticated

# Analytics API - Public (called from browser)
gcloud run services update analytics-api \
  --region=southamerica-east1 \
  --allow-unauthenticated

# Data Ingestion API - Public (called from browser)
gcloud run services update data-ingestion-api \
  --region=southamerica-east1 \
  --allow-unauthenticated

# Atendente Core - Public (called from browser)
gcloud run services update atendente-core \
  --region=southamerica-east1 \
  --allow-unauthenticated

# Tool Pool API - Private (server-to-server only)
gcloud run services update tool-pool-api \
  --region=southamerica-east1 \
  --no-allow-unauthenticated
```

Or via Cloud Console:
1. Go to Cloud Run
2. Click on service
3. Click "Edit & Deploy New Revision"
4. Under "Authentication"
   - For public services: Select "Allow unauthenticated invocations"
   - For private services: Uncheck "Allow unauthenticated invocations"
5. Deploy

### Step 4: Verify CORS Configuration

All backend services should have CORS configured for the dashboard URL:

```python
# In each backend service (analytics_api, data_ingestion_api, atendente_core)
from fastapi.middleware.cors import CORSMiddleware

origins = [
    "https://vizu-dashboard-qrfhgfkvja-rj.a.run.app",  # Production dashboard
    "http://localhost:3001",  # Local development
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Testing After Deployment

### 1. Check Dashboard Loads Correct Supabase URL

```bash
# Open browser console on dashboard
# Run:
console.log(import.meta.env.VITE_SUPABASE_URL)

# Should show:
"https://haruewffnubdgyofftut.supabase.co"

# NOT:
"https://placeholder.supabase.co"
```

### 2. Test API Connectivity

```bash
# In browser console on dashboard
fetch('https://analytics-api-qrfhgfkvja-rj.a.run.app/health')
  .then(r => r.json())
  .then(console.log)

# Should return:
{status: "healthy", service: "analytics_api"}
```

### 3. Test Authentication Flow

1. Clear browser cache and localStorage
2. Visit dashboard in incognito mode
3. Should show login page
4. Click "Sign in with Google"
5. Should redirect to Supabase → Google → back to dashboard
6. Should be logged in and see home page

## Common Issues

### Issue: "placeholder.supabase.co" still showing

**Solution:** Dashboard image not rebuilt with build args
```bash
# Trigger CI rebuild by pushing to main branch
git commit --allow-empty -m "trigger rebuild"
git push origin main
```

### Issue: CORS errors from backend

**Solution:** Backend origins need to include dashboard URL
```python
origins = [
    "https://vizu-dashboard-qrfhgfkvja-rj.a.run.app",  # Add this
    "http://localhost:3001",
]
```

### Issue: Authentication bypassed

**Solution:** Check if session is cached in localStorage
```javascript
// In browser console
localStorage.clear()
// Reload page
```

### Issue: 401 Unauthorized from APIs

**Solution:** APIs need to accept Supabase JWT tokens
- Verify JWT verification is implemented
- Check SUPABASE_JWT_SECRET is set correctly

## Deployment Checklist

- [ ] Update GitHub Secrets with Cloud Run URLs
- [ ] Push CI workflow changes to rebuild dashboard
- [ ] Configure Cloud Run authentication (allow unauthenticated for public services)
- [ ] Update CORS origins in backend services
- [ ] Test dashboard loads with correct Supabase URL
- [ ] Test API connectivity from dashboard
- [ ] Test authentication flow end-to-end
- [ ] Verify JWT token validation works

## Service URLs Reference

```bash
# Production (Cloud Run)
Dashboard:        https://vizu-dashboard-qrfhgfkvja-rj.a.run.app
Analytics API:    https://analytics-api-qrfhgfkvja-rj.a.run.app
Data Ingestion:   https://data-ingestion-api-qrfhgfkvja-rj.a.run.app
Atendente Core:   https://atendente-core-qrfhgfkvja-rj.a.run.app
Tool Pool API:    https://tool-pool-api-qrfhgfkvja-rj.a.run.app (private)

# Supabase
Auth & Database:  https://haruewffnubdgyofftut.supabase.co
```
