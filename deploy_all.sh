#!/bin/bash
set -e

# Exporte variáveis de ambiente do Vite (frontend) e outras usadas nos serviços
export VITE_SUPABASE_URL="${VITE_SUPABASE_URL}"
export VITE_SUPABASE_ANON_KEY="${VITE_SUPABASE_ANON_KEY}"
export VITE_API_URL="${VITE_API_URL}"
export VITE_GOOGLE_REDIRECT_URI="${VITE_GOOGLE_REDIRECT_URI}"
export VITE_GOOGLE_CLIENT_SECRET="${VITE_GOOGLE_CLIENT_SECRET}"
export VITE_GOOGLE_CLIENT_ID="${VITE_GOOGLE_CLIENT_ID}"
export MCP_AUTH_GOOGLE_CLIENT_ID="${MCP_AUTH_GOOGLE_CLIENT_ID}"
export MCP_AUTH_GOOGLE_CLIENT_SECRET_DEV="${MCP_AUTH_GOOGLE_CLIENT_SECRET_DEV}"
export MCP_SERVER_URL="${MCP_SERVER_URL}"
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL}"
export OLLAMA_CLOUD_API_KEY="${OLLAMA_CLOUD_API_KEY}"
export QDRANT_API_KEY="${QDRANT_API_KEY}"
export DATABASE_URL="${DATABASE_URL}"

# Build do frontend (vizu_dashboard)
cd apps/vizu_dashboard
npm install
npm run build
docker build -t vizu-dashboard:manual -f Dockerfile .
docker tag vizu-dashboard:manual southamerica-east1-docker.pkg.dev/vizudev/vizu-mono/vizu-dashboard:manual
docker push southamerica-east1-docker.pkg.dev/vizudev/vizu-mono/vizu-dashboard:manual
cd ../..

# Build e push dos serviços backend
docker build -t analytics-api:manual -f services/analytics_api/Dockerfile .
docker tag analytics-api:manual southamerica-east1-docker.pkg.dev/vizudev/vizu-mono/analytics-api:manual
docker push southamerica-east1-docker.pkg.dev/vizudev/vizu-mono/analytics-api:manual

docker build -t data-ingestion-api:manual -f services/data_ingestion_api/Dockerfile .
docker tag data-ingestion-api:manual southamerica-east1-docker.pkg.dev/vizudev/vizu-mono/data-ingestion-api:manual
docker push southamerica-east1-docker.pkg.dev/vizudev/vizu-mono/data-ingestion-api:manual

docker build -t data-ingestion-worker:manual -f services/data_ingestion_worker/Dockerfile .
docker tag data-ingestion-worker:manual southamerica-east1-docker.pkg.dev/vizudev/vizu-mono/data-ingestion-worker:manual
docker push southamerica-east1-docker.pkg.dev/vizudev/vizu-mono/data-ingestion-worker:manual

# Limpa variáveis antigas antes do deploy de cada serviço (exceto jobs)
gcloud run services update vizu-dashboard --region=southamerica-east1 --clear-env-vars || true
gcloud run services update analytics-api --region=southamerica-east1 --clear-env-vars --clear-secrets || true
sleep 5
gcloud run services update data-ingestion-api --region=southamerica-east1 --clear-env-vars || true

# Deploy no Cloud Run (ajuste os nomes dos serviços conforme necessário)

# Frontend
gcloud run deploy vizu-dashboard \
  --image=southamerica-east1-docker.pkg.dev/vizudev/vizu-mono/vizu-dashboard:manual \
  --platform=managed \
  --region=southamerica-east1 \
  --no-allow-unauthenticated \
  --set-env-vars="VITE_SUPABASE_URL=${VITE_SUPABASE_URL},VITE_SUPABASE_ANON_KEY=${VITE_SUPABASE_ANON_KEY},VITE_API_URL=${VITE_API_URL},VITE_GOOGLE_REDIRECT_URI=${VITE_GOOGLE_REDIRECT_URI},VITE_GOOGLE_CLIENT_SECRET=${VITE_GOOGLE_CLIENT_SECRET},VITE_GOOGLE_CLIENT_ID=${VITE_GOOGLE_CLIENT_ID},MCP_AUTH_GOOGLE_CLIENT_ID=${MCP_AUTH_GOOGLE_CLIENT_ID},MCP_AUTH_GOOGLE_CLIENT_SECRET_DEV=${MCP_AUTH_GOOGLE_CLIENT_SECRET_DEV},MCP_SERVER_URL=${MCP_SERVER_URL},OLLAMA_BASE_URL=${OLLAMA_BASE_URL},OLLAMA_CLOUD_API_KEY=${OLLAMA_CLOUD_API_KEY},QDRANT_API_KEY=${QDRANT_API_KEY}"

# Analytics API
# Usa o Secret Manager para DATABASE_URL

gcloud run deploy analytics-api \
  --image=southamerica-east1-docker.pkg.dev/vizudev/vizu-mono/analytics-api:manual \
  --platform=managed \
  --region=southamerica-east1 \
  --no-allow-unauthenticated \
  --set-env-vars="DATABASE_URL=${DATABASE_URL},SUPABASE_KEY=${SUPABASE_KEY},GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID},MCP_AUTH_GOOGLE_CLIENT_ID=${MCP_AUTH_GOOGLE_CLIENT_ID},MCP_AUTH_GOOGLE_CLIENT_SECRET_DEV=${MCP_AUTH_GOOGLE_CLIENT_SECRET_DEV},MCP_SERVER_URL=${MCP_SERVER_URL},OLLAMA_BASE_URL=${OLLAMA_BASE_URL},OLLAMA_CLOUD_API_KEY=${OLLAMA_CLOUD_API_KEY},QDRANT_API_KEY=${QDRANT_API_KEY}"

# Data Ingestion API
# Usa o Secret Manager para SUPABASE_JWT_SECRET
gcloud run services update data-ingestion-api --region=southamerica-east1 --remove-secrets=DATABASE_URL || true
gcloud run deploy data-ingestion-api \
  --image=southamerica-east1-docker.pkg.dev/vizudev/vizu-mono/data-ingestion-api:manual \
  --platform=managed \
  --region=southamerica-east1 \
  --no-allow-unauthenticated \
  --set-env-vars="DATABASE_URL=${DATABASE_URL},SUPABASE_KEY=${SUPABASE_KEY},GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID},GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET},GCP_PROJECT_ID=${GCP_PROJECT_ID},MCP_AUTH_GOOGLE_CLIENT_ID=${MCP_AUTH_GOOGLE_CLIENT_ID},MCP_AUTH_GOOGLE_CLIENT_SECRET_DEV=${MCP_AUTH_GOOGLE_CLIENT_SECRET_DEV},MCP_SERVER_URL=${MCP_SERVER_URL},OLLAMA_BASE_URL=${OLLAMA_BASE_URL},OLLAMA_CLOUD_API_KEY=${OLLAMA_CLOUD_API_KEY},QDRANT_API_KEY=${QDRANT_API_KEY}" \
  --set-secrets=SUPABASE_JWT_SECRET=SUPABASE_JWT_SECRET:latest

# Data Ingestion Worker como Cloud Run Job
gcloud run jobs deploy data-ingestion-worker-job \
  --image=southamerica-east1-docker.pkg.dev/vizudev/vizu-mono/data-ingestion-worker:manual \
  --region=southamerica-east1 \
  --set-env-vars="DATABASE_URL=${DATABASE_URL},GCP_PROJECT_ID=${GCP_PROJECT_ID},GOOGLE_APPLICATION_CREDENTIALS=${GOOGLE_APPLICATION_CREDENTIALS},MCP_AUTH_GOOGLE_CLIENT_ID=${MCP_AUTH_GOOGLE_CLIENT_ID},MCP_AUTH_GOOGLE_CLIENT_SECRET_DEV=${MCP_AUTH_GOOGLE_CLIENT_SECRET_DEV},MCP_SERVER_URL=${MCP_SERVER_URL},OLLAMA_BASE_URL=${OLLAMA_BASE_URL},OLLAMA_CLOUD_API_KEY=${OLLAMA_CLOUD_API_KEY},QDRANT_API_KEY=${QDRANT_API_KEY}"

echo "Deploy concluído!"