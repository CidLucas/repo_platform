#!/bin/bash
# Script to manage GCP Secrets for Cloud Run deployment
# Required GitHub secrets to be set: All the below MUST be configured

set -e

PROJECT_ID="${1:-vizudev}"
REGION="southamerica-east1"

echo "🔐 GCP Secret Manager Configuration Script"
echo "=========================================="
echo "Project: $PROJECT_ID"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Required secrets with descriptions
declare -A SECRETS=(
  # Database & Infrastructure
  [DATABASE_URL]="PostgreSQL/Supabase connection string"
  [SUPABASE_URL]="Supabase project URL"
  [SUPABASE_SERVICE_KEY]="Supabase service role key"
  [SUPABASE_ANON_KEY]="Supabase anonymous key (optional)"

  # LLM Providers
  [LLM_PROVIDER]="LLM provider: ollama, openai, anthropic, or google"
  [OPENAI_API_KEY]="OpenAI API key (if using OpenAI)"
  [ANTHROPIC_API_KEY]="Anthropic API key (if using Claude)"
  [GOOGLE_API_KEY]="Google API key (if using Gemini)"

  # Redis
  [REDIS_URL]="Redis connection string"

  # Observability
  [LANGFUSE_HOST]="Langfuse host URL"
  [LANGFUSE_PUBLIC_KEY]="Langfuse public key"
  [LANGFUSE_SECRET_KEY]="Langfuse secret key"

  # Service Communication
  [MCP_SERVER_URL]="Tool Pool API MCP server URL"
  [OLLAMA_BASE_URL]="Ollama service base URL"
  [EMBEDDING_SERVICE_URL]="Embedding service URL"

  # Other
  [TWILIO_AUTH_TOKEN]="Twilio authentication token (if needed)"
  [LANGCHAIN_API_KEY]="LangChain API key (if using LangSmith)"
  [OTEL_EXPORTER_OTLP_ENDPOINT]="OpenTelemetry collector endpoint"
)

echo "📋 Required Secrets Checklist:"
echo ""
echo "Please ensure the following GitHub secrets are configured:"
echo "Settings → Secrets and variables → Actions"
echo ""

MISSING=0
for SECRET_NAME in "${!SECRETS[@]}"; do
  echo "□ $SECRET_NAME"
  echo "  → ${SECRETS[$SECRET_NAME]}"
  MISSING=$((MISSING + 1))
done

echo ""
echo "Total required: $MISSING secrets"
echo ""

# Function to create or update a secret
create_or_update_secret() {
  local SECRET_NAME=$1
  local SECRET_VALUE=$2

  if [ -z "$SECRET_VALUE" ]; then
    echo -e "${RED}✗ $SECRET_NAME${NC} - Value is empty, skipping"
    return 1
  fi

  if gcloud secrets describe "$SECRET_NAME" --project="$PROJECT_ID" &>/dev/null; then
    # Update existing secret
    echo -n "$SECRET_VALUE" | gcloud secrets versions add "$SECRET_NAME" \
      --data-file=- \
      --project="$PROJECT_ID" &>/dev/null
    echo -e "${GREEN}✓ $SECRET_NAME${NC} - Updated"
  else
    # Create new secret
    echo -n "$SECRET_VALUE" | gcloud secrets create "$SECRET_NAME" \
      --replication-policy="automatic" \
      --data-file=- \
      --project="$PROJECT_ID" &>/dev/null
    echo -e "${GREEN}✓ $SECRET_NAME${NC} - Created"
  fi
}

# Function to grant service account access to secret
grant_access() {
  local SECRET_NAME=$1
  local SERVICE_ACCOUNT=$2

  gcloud secrets add-iam-policy-binding "$SECRET_NAME" \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor" \
    --project="$PROJECT_ID" &>/dev/null || true
}

echo ""
echo "🔑 Secrets stored in GCP Secret Manager:"
echo ""
gcloud secrets list --project="$PROJECT_ID" --format="table(name, created)" 2>/dev/null || echo "No secrets yet"

echo ""
echo "✅ To create/update secrets, call this script with GitHub Actions:"
echo ""
echo "Example in your deploy workflow:"
echo '  - name: Sync GitHub Secrets to GCP'
echo '    run: |'
echo '      create_or_update_secret "DATABASE_URL" "${{ secrets.DATABASE_URL }}"'
echo '      create_or_update_secret "OPENAI_API_KEY" "${{ secrets.OPENAI_API_KEY }}"'
echo '      ...'
