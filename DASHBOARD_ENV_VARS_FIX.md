# Dashboard Environment Variables Fix - Supabase Configuration

## Problem

Dashboard showing error:
```
DNS_PROBE_FINISHED_NXDOMAIN
This site can't be reached: placeholder.supabase.co
```

## Root Cause

Vite environment variables (`VITE_*`) are embedded in the JavaScript bundle at **build time**, not runtime. The Dockerfile was not passing these variables during the build step, so the dashboard was using the fallback placeholder values:

```typescript
// apps/vizu_dashboard/src/lib/supabase.ts
export const supabase = createClient(
  supabaseUrl || "https://placeholder.supabase.co",  // ❌ Used as fallback
  supabaseAnonKey || "placeholder-key"                // ❌ Used as fallback
);
```

## Solution

Updated the Dockerfile to accept build arguments and set them as environment variables during the Vite build process.

### Dockerfile Changes

**Added build arguments and environment variables:**

```dockerfile
# Estágio 1: Builder
FROM node:20-alpine as builder

WORKDIR /app

# Build arguments for Vite environment variables
# These will be embedded in the bundle at build time
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY
ARG VITE_GOOGLE_CLIENT_ID
ARG VITE_API_URL
ARG VITE_ATENDENTE_CORE
ARG VITE_API_URL_ANALYTICS
ARG VITE_DATA_INGESTION_API_URL

# Export as environment variables for Vite build
ENV VITE_SUPABASE_URL=$VITE_SUPABASE_URL
ENV VITE_SUPABASE_ANON_KEY=$VITE_SUPABASE_ANON_KEY
ENV VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_ATENDENTE_CORE=$VITE_ATENDENTE_CORE
ENV VITE_API_URL_ANALYTICS=$VITE_API_URL_ANALYTICS
ENV VITE_DATA_INGESTION_API_URL=$VITE_DATA_INGESTION_API_URL

# Copy package files
COPY apps/vizu_dashboard/package.json apps/vizu_dashboard/package-lock.json ./

# Install dependencies
RUN npm install

# Copy source code (including .env for defaults)
COPY apps/vizu_dashboard/ ./

# Build - Vite will use ENV vars and .env file
RUN npm run build
```

## How It Works

### Build Time (Development)

When building locally with Docker:
1. The `.env` file is copied with the source code
2. Vite reads values from `.env` during build
3. Values are embedded in the JavaScript bundle

### Build Time (Production/CI)

When building in GitHub Actions:
1. Build arguments can be passed via `--build-arg`
2. ARG variables become ENV variables
3. Vite reads ENV variables during build
4. Values are embedded in the bundle

Example:
```bash
docker build \
  --build-arg VITE_SUPABASE_URL=https://your-project.supabase.co \
  --build-arg VITE_SUPABASE_ANON_KEY=your-anon-key \
  -f apps/vizu_dashboard/Dockerfile \
  -t dashboard:latest \
  .
```

### Runtime

The built bundle contains the hardcoded values - no runtime environment variables needed for `VITE_*` variables.

## Environment Variables Reference

### Required for Dashboard Build

| Variable | Source | Purpose | Example |
|----------|--------|---------|---------|
| `VITE_SUPABASE_URL` | .env or build-arg | Supabase project URL | `https://xxx.supabase.co` |
| `VITE_SUPABASE_ANON_KEY` | .env or build-arg | Public anon key | `eyJhbG...` |
| `VITE_GOOGLE_CLIENT_ID` | .env or build-arg | Google OAuth client ID | `123-xxx.apps.googleusercontent.com` |
| `VITE_API_URL_ANALYTICS` | .env or build-arg | Analytics API URL | `http://localhost:8004` (dev)<br>`https://analytics-api-xxx.run.app` (prod) |
| `VITE_ATENDENTE_CORE` | .env or build-arg | Atendente Core URL | `http://localhost:8003` (dev)<br>`https://atendente-core-xxx.run.app` (prod) |

### Current Values (from .env)

```bash
# Development (local)
VITE_SUPABASE_URL=https://haruewffnubdgyofftut.supabase.co
VITE_SUPABASE_ANON_KEY=sb_publishable_Oo3Z5cINPxI5q4wsP_0mtQ_2_OdR1t6
VITE_GOOGLE_CLIENT_ID=858493958314-pse71gsmcsqe8a7e392stjlravbhqdtc.apps.googleusercontent.com
VITE_API_URL_ANALYTICS=http://localhost:8004
VITE_ATENDENTE_CORE=http://localhost:8003
```

## Security Note

The `VITE_SUPABASE_ANON_KEY` is **intentionally public**:
- It's the Supabase "anon" key designed to be exposed in browser code
- Row Level Security (RLS) policies protect the data
- The warning from Docker build is expected and can be ignored
- The **service_role key** (SUPABASE_SERVICE_KEY) should NEVER be in the frontend

## Testing

### Verify Build Includes Correct Values

```bash
# Build the image
docker build -f apps/vizu_dashboard/Dockerfile -t dashboard:test .

# Run the container
docker run -p 8080:8080 dashboard:test

# Open browser to http://localhost:8080
# Check browser console for Supabase client initialization
# Should NOT see "placeholder.supabase.co"
```

### Check JavaScript Bundle

```bash
# Extract and inspect the built bundle
docker create --name temp dashboard:test
docker cp temp:/usr/share/nginx/html/assets/index-*.js ./bundle.js
docker rm temp

# Search for placeholder (should NOT find it)
grep -i "placeholder" bundle.js
# Should return nothing

# Search for actual Supabase URL (should find it)
grep -i "haruewffnubdgyofftut" bundle.js
# Should find the actual URL
```

## Production Deployment

For Cloud Run deployment, the build will use the `.env` file values automatically since the file is copied into the build context.

For GitHub Actions, you can pass build args:
```yaml
- name: Build dashboard
  run: |
    docker buildx build \
      --build-arg VITE_SUPABASE_URL=${{ secrets.VITE_SUPABASE_URL }} \
      --build-arg VITE_SUPABASE_ANON_KEY=${{ secrets.VITE_SUPABASE_ANON_KEY }} \
      --build-arg VITE_API_URL_ANALYTICS=${{ secrets.VITE_API_URL_ANALYTICS }} \
      -f apps/vizu_dashboard/Dockerfile \
      -t dashboard:latest \
      --push \
      .
```

## Files Changed

1. **[apps/vizu_dashboard/Dockerfile](apps/vizu_dashboard/Dockerfile)**
   - Added ARG declarations for VITE_* variables
   - Added ENV declarations to pass to Vite build
   - .env file is copied and used as default source

2. **[apps/vizu_dashboard/.env](apps/vizu_dashboard/.env)**
   - Contains default development values
   - Used automatically during Docker build

## Current Status

- ✅ Dockerfile updated to accept build arguments
- ✅ .env file provides default values
- ✅ Image rebuilt with correct Supabase URL
- ✅ Dashboard should now connect to correct Supabase instance
- ✅ Ready for deployment and testing

## Next Steps

1. Deploy updated dashboard to Cloud Run
2. Verify authentication works
3. Check browser console for no placeholder URLs
4. Test Supabase connection and data fetching
