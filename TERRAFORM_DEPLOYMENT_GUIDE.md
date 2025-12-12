# VM Deployment Setup - Status Summary

**Date:** December 12, 2025
**Region:** southamerica-east1 (São Paulo)
**Project:** vizudev

## ✅ Completed Tasks

### 1. Git Repository Cleanup
- ✅ Added `.gitignore` entries for:
  - `terraform/.terraform/` (provider binaries - 113.92 MB)
  - `terraform/terraform.tfvars` (local secrets)
  - `*.tfplan`, `crash.log`, etc.
  - Build scripts (local only)
- ✅ Pushed clean code to GitHub (removed large terraform provider files)
- ✅ Commit: `f5af321`

### 2. Terraform Infrastructure Code
- ✅ Created `/terraform/main.tf` (280+ lines)
  - VPC network with 4 subnets (agents, workers, dashboard, redis)
  - 4 Compute Engine VMs with proper sizing
  - Firewall rules (SSH, HTTP/HTTPS, internal)
  - Service account with required IAM roles
  - Static IPs for all VMs
  - Region: southamerica-east1 (zones: a, b, c)

- ✅ Created `/terraform/variables.tf`
  - Parameterized: project_id, region, environment, docker_registry

- ✅ Created `/terraform/terraform.tfvars.example`
  - Reference config for users to copy

- ✅ Created startup scripts (4 files):
  - `startup-agents.sh` - atendente_core, tool_pool_api, vendas_agent, support_agent
  - `startup-workers.sh` - data_ingestion_worker, file_processing_worker, file_upload_api, analytics_api, data_ingestion_api
  - `startup-dashboard.sh` - vizu_dashboard (React frontend)
  - `startup-redis.sh` - Redis with persistence

- ✅ Terraform validated successfully
  - Commit: `5f1a25c`

### 3. Configuration
- ✅ Created `terraform/terraform.tfvars` locally (gitignored)
  - gcp_project_id: vizudev
  - gcp_region: southamerica-east1
  - docker_registry: us-east1-docker.pkg.dev/vizudev/vizu-mono

- ✅ GCP Artifact Registry repository created
  - `us-east1-docker.pkg.dev/vizudev/vizu-mono/`
  - Ready to push Docker images

## 📋 Next Steps

### 1. Push Docker Images to GCP Artifact Registry
Currently, images are in GitHub Container Registry. Need to:
```bash
# Pull from GitHub and push to GCP
gcloud auth configure-docker us-east1-docker.pkg.dev

# For each service:
docker pull ghcr.io/vizubr/<service>:latest
docker tag ghcr.io/vizubr/<service>:latest us-east1-docker.pkg.dev/vizudev/vizu-mono/<service>:latest
docker push us-east1-docker.pkg.dev/vizudev/vizu-mono/<service>:latest
```

Services to push:
- Backend (13): atendente_core, tool_pool_api, vendas_agent, support_agent, data_ingestion_api, file_upload_api, file_processing_worker, analytics_api, embedding_service, migration_runner, data_ingestion_worker, data_processing, ollama_service
- Frontend (1): vizu_dashboard

### 2. Deploy Infrastructure with Terraform
```bash
cd terraform

# Create terraform.tfvars (use terraform.tfvars.example as template)
# Ensure GCP authentication:
gcloud auth application-default login
gcloud config set project vizudev

# Plan and apply
terraform plan -out=tfplan
terraform apply tfplan
```

### 3. Verify Deployment
```bash
# List created VMs
gcloud compute instances list --region=southamerica-east1

# Get public IPs
terraform output

# SSH into VMs
gcloud compute ssh ubuntu@vizu-agents-pool --zone=southamerica-east1-a

# Check service status (on VM)
docker ps
docker-compose logs -f
```

### 4. Configure Google Secret Manager
Startup scripts reference these secrets (should already exist):
- `DATABASE_URL` - Supabase PostgreSQL connection
- `REDIS_URL` - Redis connection (set in startup script)
- `OLLAMA_BASE_URL` - Ollama API endpoint
- `LANGFUSE_HOST` - Langfuse traces endpoint
- `GOOGLE_API_KEY` - Google API key for integrations

Service account `vizu-deployment@vizudev.iam.gserviceaccount.com` has:
- roles/artifactregistry.reader
- roles/secretmanager.secretAccessor

## 📂 File Structure

```
terraform/
  ├── main.tf                          # VPC, subnets, VMs, firewall
  ├── variables.tf                     # Variable definitions
  ├── terraform.tfvars.example         # Example config (commit to git)
  ├── terraform.tfvars                 # Local config (gitignored)
  ├── .terraform/                      # Provider cache (gitignored)
  ├── .terraform.lock.hcl              # Lock file (gitignored)
  ├── startup-agents.sh                # Agents pool initialization
  ├── startup-workers.sh               # Workers pool initialization
  ├── startup-dashboard.sh             # Dashboard initialization
  └── startup-redis.sh                 # Redis initialization

.gitignore                             # Updated with terraform entries
```

## 🏗️ Infrastructure Overview

### VMs
| VM Name | Zone | Type | IP (Internal) | Purpose |
|---------|------|------|---|---------|
| vizu-agents-pool | southamerica-east1-a | e2-standard-4 | 10.0.1.10 | LLM agents, tool pool |
| vizu-workers-pool | southamerica-east1-b | e2-standard-4 | 10.0.2.10 | Background workers |
| vizu-dashboard | southamerica-east1-c | e2-standard-2 | 10.0.3.10 | React frontend |
| vizu-redis | southamerica-east1-a | e2-standard-2 | 10.0.4.10 | Cache & session store |

### Services per VM

**Agents Pool** (port 8003, 9000, 8009, 8010):
- atendente_core (LLM chat agent)
- tool_pool_api (tool orchestration)
- vendas_agent (sales agent)
- support_agent (support agent)

**Workers Pool** (port 8001, 8004, 8008, background):
- data_ingestion_api (data ingestion endpoint)
- data_ingestion_worker (background)
- file_upload_api (file upload endpoint)
- file_processing_worker (background)
- analytics_api (metrics endpoint)

**Dashboard**:
- vizu_dashboard (React app on port 80/443)

**Redis** (port 6379):
- Redis with AOF persistence
- Shared cache for all services

## 🔐 Security Notes

- Service account has minimal required IAM roles
- Firewall allows SSH from 0.0.0.0/0 (consider restricting in production)
- HTTP/HTTPS open to 0.0.0.0/0
- Internal services communicate via VPC (10.0.0.0/16)
- Secrets managed via Google Secret Manager (not in code)

## 🚀 Deployment Timeline

1. Push Docker images to GCP Artifact Registry (1-2 hours, depends on network)
2. Run `terraform plan` and review (5 minutes)
3. Run `terraform apply` to create VMs (10-15 minutes)
4. Startup scripts run automatically:
   - Docker installation (2-3 minutes)
   - Service startup (5-10 minutes)
5. Verify all services are healthy (5 minutes)

**Total estimated time: 2-3 hours from start to fully operational deployment**

## 📞 Support

For issues:
1. Check startup script output: `gcloud compute instances describe vizu-agents-pool --zone=southamerica-east1-a`
2. View serial console: `gcloud compute instances tail-serial-port-output vizu-agents-pool --zone=southamerica-east1-a`
3. SSH and check logs: `docker logs <container-name>`
4. Verify service status: `docker ps` and `docker-compose logs`
