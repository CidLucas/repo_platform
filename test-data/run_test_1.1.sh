#!/usr/bin/env bash
# test-data/run_test_1.1.sh
# Teste 1.1: Upload CSV NFs de serviço — Carolina Mendes (Designer)
# 
# Pré-requisitos: .env com SUPABASE_URL e SUPABASE_SERVICE_KEY
# Uso: bash test-data/run_test_1.1.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PERSONA_DIR="$SCRIPT_DIR/personas/carolina-design"
ENV_FILE="$SCRIPT_DIR/../.env"

# ── Carregar credenciais ──
export $(grep -E '^(SUPABASE_URL|SUPABASE_SERVICE_KEY)=' "$ENV_FILE" | xargs)

SUPABASE_URL="${SUPABASE_URL:-https://haruewffnubdgyofftut.supabase.co}"
SVC_KEY="${SUPABASE_SERVICE_KEY}"

if [ -z "$SVC_KEY" ]; then
  echo "ERRO: SUPABASE_SERVICE_KEY não encontrada no .env"
  exit 1
fi

CLIENT_ID="6446d4fa-b845-4d1b-b3a3-ceed2dda6d44"  # cliente de teste 1
CSV_FILE="$PERSONA_DIR/notas-fiscais/nfs_servicos_prestados.csv"

echo "════════════════════════════════════════════"
echo " TESTE 1.1 — Upload CSV Carolina (Serviços)"
echo "════════════════════════════════════════════"
echo ""
echo "Arquivo: $CSV_FILE"
echo "Cliente: $CLIENT_ID"
echo ""

# ── PASSO 1: Verificar arquivo ──
if [ ! -f "$CSV_FILE" ]; then
  echo "✗ Arquivo não encontrado: $CSV_FILE"
  echo "  Execute primeiro: python test-data/generate_persona_data.py"
  exit 1
fi

LINHAS=$(wc -l < "$CSV_FILE")
echo "✓ Arquivo encontrado: $CSV_FILE ($LINHAS linhas)"

# ── PASSO 2: Chamar match-columns com os headers ──
HEADERS=$(head -1 "$CSV_FILE" | tr ';' '\n' | jq -R -s -c 'split("\n") | map(select(length > 0))')
echo ""
echo "Headers detectados: $(echo "$HEADERS" | jq -r 'join(", ")')"

echo ""
echo "→ Chamando match-columns EF..."
MATCH_RESULT=$(curl -s "${SUPABASE_URL}/functions/v1/match-columns" \
  -H "Authorization: Bearer $SVC_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --argjson cols "$HEADERS" '{source_columns: $cols, schema_type: "invoices"}')")

echo ""
echo "Resultado match-columns:"
echo "$MATCH_RESULT" | jq .

MATCHED=$(echo "$MATCH_RESULT" | jq '.matched | length')
UNMATCHED=$(echo "$MATCH_RESULT" | jq '.unmatched | length')
echo ""
echo "  Colunas mapeadas automaticamente: $MATCHED"
echo "  Colunas sem match: $UNMATCHED"

# ── PASSO 3: Simular confirmação do usuário ──
# Pegar o mapping automático e usar como confirmed_mapping
CONFIRMED_MAPPING=$(echo "$MATCH_RESULT" | jq '.matched')
echo ""
echo "→ Mapping confirmado (automático):"
echo "$CONFIRMED_MAPPING" | jq .

# ── PASSO 4: Upload do CSV para Storage ──
echo ""
echo "→ Fazendo upload do CSV para o Storage (bucket: csv_datasets)..."

STORAGE_PATH="test-uploads/carolina/nfs_servicos_${CLIENT_ID:0:8}.csv"

UPLOAD_RESULT=$(curl -s "${SUPABASE_URL}/storage/v1/object/csv_datasets/${STORAGE_PATH}" \
  -H "Authorization: Bearer $SVC_KEY" \
  -H "Content-Type: text/csv" \
  --data-binary "@$CSV_FILE")

echo "Upload result: $UPLOAD_RESULT"

# ── PASSO 5: Chamar upload-csv-source ──
echo ""
echo "→ Chamando upload-csv-source EF..."
UPLOAD_EF_RESULT=$(curl -s "${SUPABASE_URL}/functions/v1/upload-csv-source" \
  -H "Authorization: Bearer $SVC_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -n \
    --arg client_id "$CLIENT_ID" \
    --arg storage_path "$STORAGE_PATH" \
    --argjson headers "$HEADERS" \
    --argjson mapping "$CONFIRMED_MAPPING" \
    '{client_id: $client_id, storage_path: $storage_path, headers: $headers, column_mapping: $mapping}')")

echo "$UPLOAD_EF_RESULT" | jq . 2>/dev/null || echo "Resposta: $UPLOAD_EF_RESULT"

# ── PASSO 6: Chamar run-csv-etl ──
echo ""
echo "→ Chamando run-csv-etl EF..."
ETL_RESULT=$(curl -s "${SUPABASE_URL}/functions/v1/run-csv-etl" \
  -H "Authorization: Bearer $SVC_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -n \
    --arg client_id "$CLIENT_ID" \
    --arg storage_path "$STORAGE_PATH" \
    --argjson mapping "$CONFIRMED_MAPPING" \
    '{client_id: $client_id, storage_path: $storage_path, column_mapping: $mapping}')")

echo "$ETL_RESULT" | jq . 2>/dev/null || echo "Resposta: $ETL_RESULT"

# ── PASSO 7: Verificar dados em fato_transacoes ──
echo ""
echo "→ Verificando dados em analytics_v2.fato_transacoes..."
sleep 2
FATO_CHECK=$(curl -s "${SUPABASE_URL}/rest/v1/rpc/verify_fato_transacoes" \
  -H "Authorization: Bearer $SVC_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"p_client_id\": \"$CLIENT_ID\"}" 2>/dev/null)

echo "$FATO_CHECK" | jq . 2>/dev/null || echo "RPC não encontrada — verificando direto:"

# Fallback: select direto na tabela
curl -s "${SUPABASE_URL}/rest/v1/fato_transacoes?client_id=eq.${CLIENT_ID}&select=count:exact" \
  -H "apikey: $SVC_KEY" \
  -H "Authorization: Bearer $SVC_KEY" | jq .

echo ""
echo "════════════════════════════════════════════"
echo " TESTE 1.1 — CONCLUÍDO"
echo "════════════════════════════════════════════"
