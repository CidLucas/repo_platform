#!/usr/bin/env bash
# apply_security_fixes_20260528.sh
# Aplica fixes de segurança pós-auditoria:
#   1. Reescreve process_pending_jobs para usar Vault (sem service_role_key em app_config)
#   2. Remove service_role_key de public.app_config em produção
#
# Uso:
#   ./apply_security_fixes_20260528.sh           # aplica em prod
#   ./apply_security_fixes_20260528.sh --dry-run # testa sem commitar

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

[[ -f .env ]] || { echo "ERROR: .env não encontrado" >&2; exit 1; }

SUPABASE_DB_URL="$(grep '^SUPABASE_DB_URL=' .env | cut -d= -f2-)"
[[ -n "${SUPABASE_DB_URL}" ]] || { echo "ERROR: SUPABASE_DB_URL vazio" >&2; exit 1; }
export SUPABASE_DB_URL

PSQL="${PSQL:-/opt/homebrew/opt/libpq/bin/psql}"
[[ -x "$PSQL" ]] || PSQL="$(command -v psql)" || { echo "ERROR: psql não encontrado"; exit 1; }

DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

MIGRATIONS=(
  "supabase/migrations/proposed/20260526120000_dispatcher_config_from_app_config.sql"
  "supabase/migrations/proposed/20260528000000_cleanup_service_role_key_from_app_config.sql"
)

HOST="$(echo "$SUPABASE_DB_URL" | sed -E 's|.*@([^:/]+).*|\1|')"
echo "═══════════════════════════════════════════════════════"
echo " Security Fixes — dispatcher Vault + app_config cleanup"
echo " Target host : $HOST"
echo " Dry-run     : $([[ $DRY_RUN -eq 1 ]] && echo YES || echo NO)"
echo " Migrations  : ${#MIGRATIONS[@]}"
echo "═══════════════════════════════════════════════════════"

for f in "${MIGRATIONS[@]}"; do
  [[ -f "$f" ]] || { echo "ERROR: arquivo não encontrado: $f" >&2; exit 1; }
done

if [[ $DRY_RUN -eq 0 ]]; then
  echo ""
  read -r -p "Confirmar APPLY em prod? Digite 'apply' para continuar: " confirm
  [[ "$confirm" == "apply" ]] || { echo "Abortado."; exit 1; }
fi

APPLIED=()
for f in "${MIGRATIONS[@]}"; do
  name="$(basename "$f")"
  echo ""
  echo "───────────────────────────────────────────────────────"
  echo " ▶ $name"
  echo "───────────────────────────────────────────────────────"

  if [[ $DRY_RUN -eq 1 ]]; then
    if ! (cat "$f"; echo "ROLLBACK;") | "$PSQL" "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 --quiet 2>&1 | tail -8; then
      echo "✗ FAILED (dry-run): $name"
      exit 1
    fi
    echo "✓ dry-run OK"
  else
    if ! "$PSQL" "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 --quiet -f "$f" 2>&1 | tail -8; then
      echo ""
      echo "✗ FAILED em produção: $name"
      echo "  Migrations já commitadas: ${APPLIED[*]:-nenhuma}"
      exit 1
    fi
    echo "✓ applied"
    APPLIED+=("$name")
  fi
done

echo ""
echo "═══════════════════════════════════════════════════════"
if [[ $DRY_RUN -eq 1 ]]; then
  echo " ✅ Todos os ${#MIGRATIONS[@]} scripts passaram em dry-run."
  echo " Próximo passo: rodar sem --dry-run para aplicar em prod."
else
  echo " ✅ ${#APPLIED[@]} migrations aplicadas em prod."
  printf '   • %s\n' "${APPLIED[@]}"
  echo ""
  echo " Smoke tests:"
  echo "  1. SELECT key, length(value) FROM public.app_config WHERE key='service_role_key';"
  echo "     → deve retornar 0 rows"
  echo "  2. SELECT analytics_v2.process_pending_jobs(); → deve executar sem erro"
fi
echo "═══════════════════════════════════════════════════════"
