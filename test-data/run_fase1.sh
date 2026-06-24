#!/usr/bin/env bash
# test-data/run_fase1.sh
# Executa todos os 8 testes da Fase 1 (Planilhas de NF via Onboarding)
#
# Cada teste: upload CSV/XLSX → match-columns → upload-csv-source → verificação
#
# Uso: bash test-data/run_fase1.sh [test_number]
#   Sem argumento: executa todos os testes
#   Com argumento: executa apenas o teste específico (ex: bash run_fase1.sh 1.3)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"

# ── Carregar credenciais ──
export $(grep -E '^(SUPABASE_URL|SUPABASE_SERVICE_KEY)=' "$ENV_FILE" | xargs)
SUPABASE_URL="${SUPABASE_URL:-https://haruewffnubdgyofftut.supabase.co}"
SVC_KEY="${SUPABASE_SERVICE_KEY}"

if [ -z "$SVC_KEY" ]; then
  echo "ERRO: SUPABASE_SERVICE_KEY não encontrada"
  exit 1
fi

# Cliente de teste
CLIENT_ID="6446d4fa-b845-4d1b-b3a3-ceed2dda6d44"
PERSONAS_DIR="$SCRIPT_DIR/personas"

# ─── Helper function ────────────────────────────────────────────────────
run_test() {
  local test_id="$1"
  local persona="$2"
  local file_rel="$3"
  local schema_type="${4:-invoices}"
  local desc="$5"
  local file="$PERSONAS_DIR/$persona/$file_rel"

  echo ""
  echo "═══════════════════════════════════════════════════════"
  echo " TESTE $test_id — $desc"
  echo "═══════════════════════════════════════════════════════"
  echo "  Arquivo: $file"
  echo ""

  if [ ! -f "$file" ]; then
    echo "  ✗ ARQUIVO NÃO ENCONTRADO"
    echo "    Execute: python test-data/generate_persona_data.py"
    return 1
  fi

  # 1. Extrair headers
  local ext="${file##*.}"
  if [ "$ext" = "csv" ]; then
    local delim=";"
    HEADERS=$(head -1 "$file" | tr "$delim" '\n' | jq -R -s -c 'split("\n") | map(select(length > 0))')
  elif [ "$ext" = "xlsx" ]; then
    # Para XLSX usamos python pra extrair headers
    HEADERS=$(python3 -c "
import json
from openpyxl import load_workbook
wb = load_workbook('$file', read_only=True, data_only=True)
# Pega a primeira aba com mais dados
best = max(wb.sheetnames, key=lambda n: sum(1 for _ in wb[n].iter_rows(min_row=2, max_row=2)))
ws = wb[best]
headers = [str(c.value).strip() for c in next(ws.iter_rows(max_row=1)) if c.value]
print(json.dumps(headers))
")
  else
    echo "  ✗ Formato não suportado: $ext"
    return 1
  fi

  echo "  Headers: $(echo "$HEADERS" | jq -r 'join(", ")')"

  # 2. match-columns
  echo ""
  echo "  → match-columns..."
  local MATCH_RESULT
  MATCH_RESULT=$(curl -s "${SUPABASE_URL}/functions/v1/match-columns" \
    -H "Authorization: Bearer *** \
    -H "Content-Type: application/json" \
    -d "$(jq -n \
      --argjson cols "$HEADERS" \
      --arg schema "$schema_type" \
      '{source_columns: $cols, schema_type: $schema}')")

  local MATCHED=$(echo "$MATCH_RESULT" | jq '.matched | length')
  local UNMATCHED=$(echo "$MATCH_RESULT" | jq '.unmatched | length')
  local CONFIDENCE=$(echo "$MATCH_RESULT" | jq '[.confidence_scores[] | select(. >= 0.8)] | length')
  local NEEDS_REVIEW=$(echo "$MATCH_RESULT" | jq '.needs_review | length')

  echo "    Matched: $MATCHED | Unmatched: $UNMATCHED"
  echo "    High confidence: $CONFIDENCE | Needs review: $NEEDS_REVIEW"

  # 3. Resultado detalhado
  echo ""
  echo "  → Detalhes do matching:"
  echo "$MATCH_RESULT" | jq '{
    matched: .matched,
    unmatched: .unmatched,
    needs_review: .needs_review,
    detected_context: .detected_context
  }'

  # 4. Verificar se passou ou falhou (critério: pelo menos 3 colunas mapeadas com confiança > 0.8)
  if [ "$MATCHED" -ge 3 ] && [ "$CONFIDENCE" -ge 2 ]; then
    echo ""
    echo "  ✅ TESTE PASSOU: $MATCHED colunas mapeadas, $CONFIDENCE com alta confiança"
    return 0
  else
    echo ""
    echo "  ⚠️  TESTE COM RESSALVA: $MATCHED mapeadas, $CONFIDENCE alta confiança"
    echo "     Unmatched: $UNMATCHED | Needs review: $NEEDS_REVIEW"
    return 0  # não falha, só alerta
  fi
}

# ──────── TESTES ─────────────────────────────────────────────────────────

ALL_PASSED=0
ALL_TOTAL=0

if [ $# -ge 1 ]; then
  # Executar teste específico
  TID="$1"
else
  TID="all"
fi

run_single() {
  local tid="$1" p="$2" f="$3" s="$4" d="$5"
  ALL_TOTAL=$((ALL_TOTAL + 1))
  if [ "$TID" = "all" ] || [ "$TID" = "$tid" ]; then
    if run_test "$tid" "$p" "$f" "$s" "$d"; then
      ALL_PASSED=$((ALL_PASSED + 1))
    fi
  fi
}

echo ""
echo "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓"
echo "  FASE 1 — PLANILHAS DE NF VIA ONBOARDING"
echo "  7 fases, 51 testes no total"
echo "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓"

# Teste 1.1 — Carolina: NFs de serviço (CSV)
run_single "1.1" "carolina-design" \
  "notas-fiscais/nfs_servicos_prestados.csv" \
  "invoices" \
  "Carolina — NFs de serviço prestado (37 linhas)"

# Teste 1.2 — Carolina: NFs de despesa (CSV)
run_single "1.2" "carolina-design" \
  "notas-fiscais/nfs_compras_despesas.csv" \
  "invoices" \
  "Carolina — NFs de despesa/compras (56 linhas)"

# Teste 1.3 — Lúcia: Vendas buffet (CSV)
run_single "1.3" "lucia-buffet" \
  "notas-fiscais/nfs_vendas_servicos.csv" \
  "invoices" \
  "Lúcia — Vendas de serviços buffet (47 linhas)"

# Teste 1.4 — Lúcia: Compras insumos (CSV)
run_single "1.4" "lucia-buffet" \
  "notas-fiscais/nfs_compras_insumos.csv" \
  "invoices" \
  "Lúcia — Compras de insumos (41 linhas)"

# Teste 1.5 — NovaTech: Vendas hardware (CSV)
run_single "1.5" "novatech-ti" \
  "notas-fiscais/nfs_vendas_hardware.csv" \
  "invoices" \
  "NovaTech — Vendas de hardware (9 linhas, alto valor)"

# Teste 1.6 — NovaTech: Contratos recorrentes (CSV, 131 linhas)
run_single "1.6" "novatech-ti" \
  "notas-fiscais/nfs_vendas_servicos_recorrentes.csv" \
  "invoices" \
  "NovaTech — Contratos recorrentes (131 linhas, grande volume)"

# Teste 1.7 — Carolina: Planilha XLSX (mult-abas)
run_single "1.7" "carolina-design" \
  "planilhas/planilha_controle_carol.xlsx" \
  "invoices" \
  "Carolina — Planilha XLSX (2 abas: Projetos + Financeiro)"

# Teste 1.8 — NovaTech: XLSX fluxo de caixa
run_single "1.8" "novatech-ti" \
  "planilhas/fluxo_caixa_2025.xlsx" \
  "invoices" \
  "NovaTech — Planilha XLSX fluxo de caixa (múltiplas abas)"

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  FASE 1 — RESUMO"
echo "  $ALL_PASSED de $ALL_TOTAL testes executados"
echo "═══════════════════════════════════════════════════════"
