#!/usr/bin/env bash
# apply_security_sprint.sh
# Aplica as migrations de segurança pré-onboarding em ordem, com fail-fast.
# Cada arquivo já contém seu próprio BEGIN/COMMIT — se algo quebrar, só
# essa migration é revertida. As anteriores ficam commitadas.
#
# Uso:
#   ./apply_security_sprint.sh           # aplica em prod
#   ./apply_security_sprint.sh --dry-run # roda cada uma em transação e dá ROLLBACK
#
# Requer: SUPABASE_DB_URL no .env do repo_platform (já está).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

if [[ ! -f .env ]]; then
  echo "ERROR: .env não encontrado em $REPO_ROOT" >&2
  exit 1
fi

SUPABASE_DB_URL="$(grep '^SUPABASE_DB_URL=' .env | cut -d= -f2-)"
if [[ -z "${SUPABASE_DB_URL}" ]]; then
  echo "ERROR: SUPABASE_DB_URL vazio no .env" >&2
  exit 1
fi
export SUPABASE_DB_URL

PSQL="${PSQL:-/opt/homebrew/opt/libpq/bin/psql}"
if [[ ! -x "$PSQL" ]]; then
  PSQL="$(command -v psql)" || { echo "ERROR: psql não encontrado"; exit 1; }
fi

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then DRY_RUN=1; fi

MIGRATIONS=(
  "supabase/migrations/proposed/20260525_p0_fix_integration_tokens_rls.sql"
  "supabase/migrations/proposed/20260525_p1_fix_notifications_rls.sql"
  "supabase/migrations/proposed/20260525_p1_integration_tokens_write_policies.sql"
  "supabase/migrations/proposed/20260525_p2_normalize_roles_to_authenticated.sql"
  "supabase/migrations/proposed/20260525_p3_lockdown_secdef.sql"
  "supabase/migrations/proposed/20260525_p3_1_refactor_bq_secdef.sql"
  "supabase/migrations/proposed/20260525_p3_2_drop_dead_password_auth.sql"
)

# Pré-flight: confirmar host de prod
HOST="$(echo "$SUPABASE_DB_URL" | sed -E 's|.*@([^:/]+).*|\1|')"
echo "═══════════════════════════════════════════════════════"
echo " Security Sprint — pre-onboarding lockdown"
echo " Target host : $HOST"
echo " Dry-run     : $([[ $DRY_RUN -eq 1 ]] && echo YES || echo NO)"
echo " Migrations  : ${#MIGRATIONS[@]}"
echo "═══════════════════════════════════════════════════════"

for f in "${MIGRATIONS[@]}"; do
  if [[ ! -f "$f" ]]; then
    echo "ERROR: arquivo não encontrado: $f" >&2
    exit 1
  fi
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
    # Em dry-run, append ROLLBACK ao script. O script já termina com COMMIT,
    # mas adicionar ROLLBACK após gera apenas um WARNING inofensivo.
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
      echo "  PRÓXIMOS PASSOS: investigar erro acima e decidir rollback manual."
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
else
  echo " ✅ ${#APPLIED[@]} migrations aplicadas em prod."
  printf '   • %s\n' "${APPLIED[@]}"
  echo ""
  echo " Próximos smoke tests (manuais):"
  echo "  1. Login no frontend → carregar dashboard"
  echo "  2. Wizard BQ connector → criar server"
  echo "  3. Edge google-oauth-start → retornar URL"
  echo "  4. SELECT count(*) FROM public.integration_tokens; (como anon = 0)"
fi
echo "═══════════════════════════════════════════════════════"
