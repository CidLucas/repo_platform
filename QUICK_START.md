# 🚀 Local Dev Environment - Quick Start Checklist

## Current Status

✅ `.env` file configured with Supabase
⚠️ **Action needed:** Docker Desktop needs to be started

## Setup Steps

### 1. Start Docker Desktop

```bash
# Option A: Open from Applications
open -a Docker

# Option B: Launch via command line (if symlink exists)
open /Applications/Docker.app
```

**Wait for Docker Desktop to fully start** (whale icon in menu bar should be solid, not animated)

### 2. Verify Docker is Running

```bash
# This should show Docker version (not "command not found")
docker --version

# If still not found, add Docker to PATH:
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"

# Add to your ~/.zshrc to make permanent:
echo 'export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### 3. Start Your Dev Environment

```bash
cd /Users/lucascruz/Documents/GitHub/vizu-mono

# Start core dev services (dashboard + backend + tools)
make dev
```

Expected output:
```
🚀 Starting core dev stack...
   ✓ vizu_dashboard (frontend)
   ✓ atendente_core (main backend)
   ✓ tool_pool_api (MCP tools)
   ✓ redis + qdrant (dependencies)

✅ Dev stack ready!

📋 Services:
   🎨 Dashboard:      http://localhost:8080
   🤖 Atendente:      http://localhost:8003
   🔧 Tool Pool:      http://localhost:8006
```

### 4. Verify Services Are Running

```bash
# Check container status
docker compose ps

# View logs
make dev-logs

# Test endpoints
curl http://localhost:8003/health
curl http://localhost:8006/health
```

### 5. Open Dashboard

```bash
# Automatically open in browser
open http://localhost:8080
```

## Development Workflow

### Making Code Changes

Your code is **hot-reloaded**. Just edit and save:

```bash
# Frontend changes
vim apps/vizu_dashboard/src/App.tsx

# Backend changes
vim services/atendente_core/src/atendente_core/main.py

# Shared library changes
vim libs/vizu_models/src/vizu_models/cliente.py
```

**Changes apply automatically!** No rebuild needed (unless you change pyproject.toml).

### Testing Your Changes

```bash
# Quick chat test
make chat

# Test specific agents
make test-vendas
make test-support

# Run unit tests
make test
```

### Stopping Services

```bash
# Stop but keep containers (fast restart)
make dev-down

# Stop and remove containers
make down
```

## Troubleshooting

### Docker won't start services

```bash
# Check if Docker daemon is running
docker info

# Restart Docker Desktop if needed
killall Docker && open -a Docker
```

### Port conflicts (8080, 8003, 8006 already in use)

```bash
# Find what's using the port
lsof -i :8080
lsof -i :8003
lsof -i :8006

# Kill the process (replace PID with actual PID from lsof)
kill -9 <PID>
```

### Supabase connection errors

Check your .env has valid credentials:
```bash
grep SUPABASE_URL .env
grep SUPABASE_SERVICE_KEY .env
```

### Need to rebuild after dependency changes

```bash
make dev-down
docker compose build --no-cache atendente_core tool_pool_api vizu_dashboard
make dev
```

## Cost Savings 💰

**Before this setup:**
- Push to GitHub → GitHub Actions → Cloud Build → Cloud Run
- **Cost:** ~$5-20 per build depending on size
- **Time:** 5-15 minutes per build

**With local dev:**
- Edit code → Auto-reload locally → Test immediately
- **Cost:** $0 (only Docker Desktop running locally)
- **Time:** Instant feedback

**Only deploy to Cloud Run when ready for staging/prod!**

## Architecture

Your local setup connects to:
- ✅ **Remote Supabase** (production/staging database)
- ✅ **Local Redis** (session cache)
- ✅ **Local Qdrant** (vector search)
- ✅ **Local services** (dashboard, backend, tools)

```
┌─────────────────┐
│  Your MacBook   │
├─────────────────┤
│ 🎨 Dashboard    │ :8080
│ 🤖 Atendente    │ :8003  ──┐
│ 🔧 Tool Pool    │ :8006    │
│ 📦 Redis        │ :6379    │ All connect to
│ 🔍 Qdrant       │ :6333    │ remote Supabase
└─────────────────┘          │
                              ↓
                    ┌──────────────────┐
                    │  ☁️ Supabase     │
                    │  (Remote Cloud)  │
                    └──────────────────┘
```

## Next Steps

1. ✅ Start Docker Desktop
2. ✅ Run `make dev`
3. ✅ Open http://localhost:8080
4. 🚀 Start building!

For more details, see [DEV_SETUP.md](./DEV_SETUP.md)
