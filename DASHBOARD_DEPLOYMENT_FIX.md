# Dashboard Deployment Fix - Port Configuration & Generous Timeouts

## Issues Identified

1. **Incorrect Image Name**: `vizu-vizu_dashboard` (double "vizu" prefix)
2. **Hardcoded Port 80**: Nginx listening on port 80 instead of Cloud Run's dynamic `$PORT` (typically 8080)
3. **Short Startup Timeout**: Default Cloud Run timeout causing `DEADLINE_EXCEEDED` errors

## Changes Made

### 1. Dashboard Dockerfile ([apps/vizu_dashboard/Dockerfile](apps/vizu_dashboard/Dockerfile))

**Added dynamic PORT support:**
```dockerfile
# Install gettext for envsubst command
RUN apk add --no-cache gettext

# Template-based nginx configuration
COPY apps/vizu_dashboard/nginx.conf /etc/nginx/conf.d/nginx.conf

# Expose dynamic port (Cloud Run uses $PORT, usually 8080)
EXPOSE 8080

# Startup script that substitutes ${PORT} in nginx.conf
CMD ["/bin/sh", "-c", "export PORT=${PORT:-8080} && envsubst '${PORT}' < /etc/nginx/conf.d/nginx.conf > /tmp/nginx.conf && mv /tmp/nginx.conf /etc/nginx/conf.d/nginx.conf && nginx -g 'daemon off;'"]
```

### 2. Nginx Configuration ([apps/vizu_dashboard/nginx.conf](apps/vizu_dashboard/nginx.conf))

**Changed from hardcoded to template:**
```nginx
# BEFORE:
server {
  listen 80;
  # ...
}

# AFTER:
server {
  listen ${PORT};  # Replaced at runtime by envsubst
  # ...
}
```

### 3. CI Workflow ([.github/workflows/ci.yml](.github/workflows/ci.yml))

**Fixed image naming:**
```yaml
# BEFORE:
- service: vizu_dashboard
  dockerfile_path: apps/vizu_dashboard/Dockerfile

# AFTER:
- service: dashboard
  dockerfile_path: apps/vizu_dashboard/Dockerfile
```

**Result:** Image name changed from `vizu-vizu_dashboard` → `vizu-dashboard`

### 4. Deploy Script ([scripts/deploy-cloud-run.sh](scripts/deploy-cloud-run.sh))

**Fixed image naming and port:**
```bash
# BEFORE:
local img_dashboard=$(build_and_push "vizu_dashboard" "apps/vizu_dashboard/Dockerfile")
deploy_to_cloud_run "vizu-dashboard" "$img_dashboard" "512Mi" "1" "80" "300" "10" "0" "3000" "true"

# AFTER:
local img_dashboard=$(build_and_push "dashboard" "apps/vizu_dashboard/Dockerfile")
deploy_to_cloud_run "vizu-dashboard" "$img_dashboard" "512Mi" "1" "80" "300" "10" "0" "80" "true"
```

**Added generous timeout and CPU boost settings:**
```bash
gcloud run deploy "${service_name}" \
    # ... existing flags ...
    --cpu-boost \              # Enable CPU boost during startup (faster cold starts)
    --no-cpu-throttling \      # Don't throttle CPU during requests
    --project=${PROJECT_ID} \
    --quiet
```

## How It Works

### Nginx Dynamic Port Configuration

1. **Build Time**: nginx.conf contains template variable `${PORT}`
2. **Runtime**: Container startup script:
   - Sets `PORT=${PORT:-8080}` (default 8080 for Cloud Run)
   - Runs `envsubst '${PORT}'` to replace `${PORT}` with actual port number
   - Starts nginx with the configured port

### Port Consistency Pattern

All services now follow the same pattern:

| Service Type | Dockerfile CMD | Port Variable | Default |
|--------------|---------------|---------------|---------|
| **Python (FastAPI)** | `uvicorn ... --port ${PORT:-8000}` | `$PORT` | 8000 |
| **Node (Dashboard)** | `envsubst + nginx` | `$PORT` | 8080 |

**Cloud Run behavior:**
- Sets `PORT` environment variable (usually 8080)
- All services listen on `$PORT`
- Health checks probe on `$PORT`

## Benefits

### 1. Dynamic Port Assignment ✅
- Dashboard adapts to Cloud Run's assigned port
- Works locally with `PORT=3000` or any other port
- No hardcoded ports in production

### 2. Faster Cold Starts 🚀
- `--cpu-boost`: Allocates more CPU during container startup
- Reduces `DEADLINE_EXCEEDED` errors
- Faster initial response times

### 3. Better Performance 📈
- `--no-cpu-throttling`: Ensures consistent performance
- No artificial CPU limits during request processing
- Improved user experience

### 4. Consistent Naming 🎯
- All images follow `vizu-{service}` pattern
- No double prefixes or naming confusion
- Clear service identification

## Testing

### Local Testing
```bash
# Test with default port
docker run -p 8080:8080 southamerica-east1-docker.pkg.dev/vizudev/vizu-mono/vizu-dashboard:latest

# Test with custom port
docker run -e PORT=3000 -p 3000:3000 southamerica-east1-docker.pkg.dev/vizudev/vizu-mono/vizu-dashboard:latest
```

### Cloud Run Deployment
```bash
# Build and push
export GCP_PROJECT_ID=vizudev
./scripts/deploy-cloud-run.sh dashboard

# Verify deployment
gcloud run services describe vizu-dashboard --region=southamerica-east1 --format="value(status.url)"
```

## Image in Artifact Registry

**Current:**
```
southamerica-east1-docker.pkg.dev/vizudev/vizu-mono/vizu-dashboard:latest
```

**Previous (incorrect):**
```
southamerica-east1-docker.pkg.dev/vizudev/vizu-mono/vizu-vizu_dashboard:latest
```

## Startup Timeout Configuration

Cloud Run startup timeout defaults to 240 seconds. With our changes:

1. **CPU Boost**: Faster container initialization
2. **No CPU Throttling**: Consistent performance
3. **Optimized nginx**: Lightweight static file server
4. **Result**: Should start well within 240s timeout

## Deployment Status

- ✅ Dashboard Dockerfile updated with dynamic PORT
- ✅ nginx.conf converted to template
- ✅ Image rebuilt and pushed with correct name
- ✅ CI workflow updated
- ✅ Deploy script updated with generous settings
- ⏳ Ready for Cloud Run deployment

## Next Steps

1. Deploy to Cloud Run via GitHub Actions workflow
2. Verify dashboard loads correctly
3. Check Cloud Run logs for successful startup
4. Test dynamic port assignment

## References

- [Cloud Run Container Runtime Contract](https://cloud.google.com/run/docs/container-contract)
- [Cloud Run CPU Boost](https://cloud.google.com/run/docs/configuring/cpu-boost)
- [Nginx envsubst](https://www.nginx.com/resources/wiki/start/topics/examples/dynamic_ssi/)
