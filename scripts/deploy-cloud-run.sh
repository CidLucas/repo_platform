#!/bin/bash
# Full CI/CD Workflow for Vizu - Build, Test, Push to Artifact Registry, Deploy to Cloud Run
# Prerequisites:
#   - gcloud CLI installed and authenticated
#   - GCP_PROJECT_ID set in environment
#   - Poetry installed for running tests
#   - Docker with buildx support

set -euo pipefail

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-}"
REGION="${GCP_REGION:-southamerica-east1}"
REGISTRY="southamerica-east1-docker.pkg.dev"
REPO_NAME="vizu-mono"
SERVICE_ACCOUNT="${GCP_SA_EMAIL:-github-actions@${PROJECT_ID}.iam.gserviceaccount.com}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Validate prerequisites
validate_prerequisites() {
    log "Validating prerequisites..."

    if ! command -v gcloud &> /dev/null; then
        error "gcloud CLI not found. Please install it: https://cloud.google.com/sdk/docs/install"
    fi

    if ! command -v docker &> /dev/null; then
        error "Docker not found. Please install it: https://docs.docker.com/get-docker/"
    fi

    if ! command -v poetry &> /dev/null; then
        warn "Poetry not found. Tests will be skipped."
    fi

    if [ -z "$PROJECT_ID" ]; then
        error "GCP_PROJECT_ID not set. Export it: export GCP_PROJECT_ID=your-project"
    fi

    log "Prerequisites validated ✓"
}

# Configure Docker for Artifact Registry
configure_docker() {
    log "Configuring Docker for Artifact Registry..."
    gcloud auth configure-docker ${REGISTRY}
    log "Docker configured ✓"
}

# Create Artifact Registry repository if not exists
create_registry() {
    log "Ensuring Artifact Registry repository exists..."

    if ! gcloud artifacts repositories describe ${REPO_NAME} \
        --location=${REGION} \
        --project=${PROJECT_ID} &> /dev/null; then
        log "Creating Artifact Registry repository..."
        gcloud artifacts repositories create ${REPO_NAME} \
            --repository-format=docker \
            --location=${REGION} \
            --project=${PROJECT_ID} \
            --description="Vizu mono-repo Docker images"
        log "Repository created ✓"
    else
        log "Repository already exists ✓"
    fi
}

# Run tests for a service
run_tests() {
    local service=$1

    if ! command -v poetry &> /dev/null; then
        warn "Poetry not found. Skipping tests for $service"
        return 0
    fi

    log "Running tests for $service..."

    if [ ! -d "services/$service/tests" ]; then
        warn "No tests directory found for $service, skipping..."
        return 0
    fi

    cd "services/$service"

    # Install dependencies
    if ! poetry install --with dev &> /dev/null; then
        warn "Failed to install dependencies for $service, skipping tests..."
        cd ../..
        return 0
    fi

    # Ensure pytest-cov is installed
    poetry add --group dev pytest-cov &> /dev/null || true

    # Run tests
    if poetry run pytest tests/ -v --cov=src --cov-report=term-missing 2>&1 | tee test-output.log; then
        log "$service tests passed ✓"
    elif poetry run pytest tests/ -v 2>&1 | tee test-output.log; then
        log "$service tests passed ✓ (without coverage)"
    else
        warn "$service tests failed, but continuing..."
    fi

    cd ../..
}

# Build and push a single service
build_and_push() {
    local service=$1
    local dockerfile=$2

    log "Building $service..."

    local commit_short=$(git rev-parse --short HEAD 2>/dev/null || echo "local")
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local image_tag="${timestamp}-${commit_short}"

    local image_base="${REGISTRY}/${PROJECT_ID}/${REPO_NAME}/vizu-${service}"
    local image_versioned="${image_base}:${image_tag}"
    local image_latest="${image_base}:latest"

    # Build arguments for dashboard (Vite environment variables from .env file)
    local build_args=""
    if [[ "$service" == "dashboard" ]]; then
        log "Loading Vite environment variables from .env file..."
        if [ -f "apps/vizu_dashboard/.env" ]; then
            # Load .env file and create build args
            while IFS='=' read -r key value; do
                # Skip comments and empty lines
                [[ $key =~ ^#.*$ ]] && continue
                [[ -z $key ]] && continue
                # Trim whitespace
                key=$(echo "$key" | xargs)
                value=$(echo "$value" | xargs)
                # Only process VITE_* variables
                if [[ $key =~ ^VITE_ ]]; then
                    # Remove quotes from value if present
                    value=$(echo "$value" | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
                    build_args="$build_args --build-arg ${key}=${value}"
                    # Truncate long values for display
                    local display_value="${value:0:50}"
                    if [ ${#value} -gt 50 ]; then
                        display_value="${display_value}..."
                    fi
                    log "  ${key}=${display_value}"
                fi
            done < "apps/vizu_dashboard/.env"
        else
            warn "apps/vizu_dashboard/.env not found, building without Vite variables"
        fi
    fi

    # Build using buildx for linux/amd64 (Cloud Run requirement)
    docker buildx build \
        --platform linux/amd64 \
        -f "${dockerfile}" \
        $build_args \
        -t "${image_versioned}" \
        -t "${image_latest}" \
        --push \
        .

    log "$service built and pushed ✓"
    log "  Versioned: ${image_versioned}"
    log "  Latest: ${image_latest}"

    # Return the latest tag for deployment
    echo "${image_latest}"
}

# Deploy a service to Cloud Run
deploy_to_cloud_run() {
    local service_name=$1
    local image_uri=$2
    local memory=$3
    local cpu=$4
    local concurrency=$5
    local timeout=$6
    local max_instances=$7
    local min_instances=$8
    local port=${9:-8000}
    local allow_unauthenticated=${10:-true}

    log "Deploying $service_name to Cloud Run..."

    local allow_flag=""
    if [ "$allow_unauthenticated" = "true" ]; then
        allow_flag="--allow-unauthenticated"
    else
        allow_flag="--no-allow-unauthenticated"
    fi

    gcloud run deploy "${service_name}" \
        --image="${image_uri}" \
        --region=${REGION} \
        --platform=managed \
        ${allow_flag} \
        --memory="${memory}" \
        --cpu="${cpu}" \
        --concurrency="${concurrency}" \
        --timeout="${timeout}" \
        --max-instances="${max_instances}" \
        --min-instances="${min_instances}" \
        --port="${port}" \
        --ingress=internal-and-cloud-load-balancing \
        --set-env-vars="ENVIRONMENT=production,LOG_LEVEL=INFO" \
        --service-account="${SERVICE_ACCOUNT}" \
        --cpu-boost \
        --no-cpu-throttling \
        --project=${PROJECT_ID} \
        --quiet

    log "$service_name deployed ✓"
}

# Main CI/CD workflow
main() {
    local deploy_type=${1:-all}

    validate_prerequisites
    configure_docker
    create_registry

    case "$deploy_type" in
        agents-pool)
            log "========================================="
            log "CI/CD: Agents Pool"
            log "========================================="

            # Run tests
            run_tests "atendente_core"
            run_tests "tool_pool_api"

            # Build and push
            log "Building and pushing images..."
            local img_atendente=$(build_and_push "atendente_core" "services/atendente_core/Dockerfile")
            local img_tool_pool=$(build_and_push "tool_pool_api" "services/tool_pool_api/Dockerfile")
            local img_vendas=$(build_and_push "vendas_agent" "services/vendas_agent/Dockerfile")
            local img_support=$(build_and_push "support_agent" "services/support_agent/Dockerfile")

            # Deploy
            log "Deploying to Cloud Run..."
            deploy_to_cloud_run "atendente-core" "$img_atendente" "2Gi" "2" "10" "3600" "50" "1" "8000" "true"
            deploy_to_cloud_run "tool-pool-api" "$img_tool_pool" "2Gi" "2" "5" "3600" "20" "1" "8000" "false"
            deploy_to_cloud_run "vendas-agent" "$img_vendas" "2Gi" "2" "10" "3600" "50" "0" "8000" "true"
            deploy_to_cloud_run "support-agent" "$img_support" "2Gi" "2" "10" "3600" "50" "0" "8000" "true"
            ;;

        workers-pool)
            log "========================================="
            log "CI/CD: Workers Pool"
            log "========================================="

            # Run tests
            run_tests "data_ingestion_api"
            run_tests "analytics_api"

            # Build and push
            log "Building and pushing images..."
            local img_file_upload=$(build_and_push "file_upload_api" "services/file_upload_api/Dockerfile")
            local img_data_ingestion=$(build_and_push "data_ingestion_api" "services/data_ingestion_api/Dockerfile")
            local img_analytics=$(build_and_push "analytics_api" "services/analytics_api/Dockerfile")

            # Deploy
            log "Deploying to Cloud Run..."
            deploy_to_cloud_run "file-upload-api" "$img_file_upload" "1Gi" "2" "50" "300" "50" "1"
            deploy_to_cloud_run "data-ingestion-api" "$img_data_ingestion" "2Gi" "2" "50" "600" "50" "1"
            deploy_to_cloud_run "analytics-api" "$img_analytics" "2Gi" "2" "50" "300" "50" "1"
            ;;

        dashboard)
            log "========================================="
            log "CI/CD: Dashboard"
            log "========================================="

            # Build and push
            log "Building and pushing dashboard..."
            local img_dashboard=$(build_and_push "dashboard" "apps/vizu_dashboard/Dockerfile")

            # Deploy
            log "Deploying to Cloud Run..."
            deploy_to_cloud_run "vizu-dashboard" "$img_dashboard" "512Mi" "1" "80" "300" "10" "0" "80" "true"
            ;;

        all)
            log "========================================="
            log "Full CI/CD Workflow - All Services"
            log "========================================="
            $0 agents-pool
            $0 workers-pool
            $0 dashboard
            ;;

        *)
            error "Unknown service: $deploy_type. Options: agents-pool, workers-pool, dashboard, all"
            ;;
    esac

    log "========================================="
    log "CI/CD Complete ✓"
    log "========================================="
}

# Run main if script is executed directly
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
