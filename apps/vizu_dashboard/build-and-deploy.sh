#!/bin/bash
set -e

# Exporte todas as variáveis necessárias para o build do Vite
export VITE_ATENDENTE_CORE="https://atendente-core-858493958314.southamerica-east1.run.app"
export VITE_SUPABASE_URL="https://haruewffnubdgyofftut.supabase.co"
export VITE_SUPABASE_ANON_KEY="sb_publishable_Oo3Z5cINPxI5q4wsP_0mtQ_2_OdR1t6"
export VITE_GOOGLE_CLIENT_ID="858493958314-pse71gsmcsqe8a7e392stjlravbhqdtc.apps.googleusercontent.com"
export VITE_GOOGLE_REDIRECT_URI="VITE_GOOGLE_REDIRECT_URI=https://vizu-dashboard-858493958314.southamerica-east1.run.app"
export VITE_API_URL="https://vizu-dashboard-858493958314.southamerica-east1.run.app"


# Instala dependências e faz o build do frontend
npm install
npm run build

# Build da imagem Docker
docker build -t vizu-dashboard:manual -f Dockerfile .

# Tag e push para o Artifact Registry do GCP
docker tag vizu-dashboard:manual southamerica-east1-docker.pkg.dev/vizudev/vizu-mono/vizu-dashboard:manual
docker push southamerica-east1-docker.pkg.dev/vizudev/vizu-mono/vizu-dashboard:manual

# Deploy no Cloud Run
gcloud run deploy vizu-dashboard \
  --image=southamerica-east1-docker.pkg.dev/vizudev/vizu-mono/vizu-dashboard:manual \
  --platform=managed \
  --region=southamerica-east1 \
  --allow-unauthenticated \
  --port=80

echo "Deploy concluído!"