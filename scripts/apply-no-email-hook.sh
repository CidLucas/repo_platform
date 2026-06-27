#!/usr/bin/env bash
# Apply the send_email hook + auto-confirm trigger to the remote Supabase
# project. This unlocks the 2/h email rate limit by replacing the built-in
# email provider with a no-op Postgres hook.
#
# Prereq: `supabase login` already run, project is linked
# (`supabase link --project-ref haruewffnubdgyofftut`).
#
# Usage:
#   ./scripts/apply-no-email-hook.sh
#
# What it does:
#   1. supabase db push     — applies the migration
#                             (20260627000000_disable_email_via_hook.sql)
#   2. supabase config push — applies [auth.hook.send_email] from config.toml
#
# After this, /auth/v1/signup uses the no-op hook instead of the built-in
# provider. Signups no longer send email and no longer count against the
# 2/h rate limit. The auto-confirm trigger makes users immediately loginable.

set -euo pipefail

PROJECT_REF="haruewffnubdgyofftut"

echo "→ Checking Supabase CLI is linked to project..."
LINKED=$(supabase status 2>/dev/null | grep -E "Project ID" || true)
if [ -z "${LINKED}" ]; then
  echo "  Linking to ${PROJECT_REF}..."
  supabase link --project-ref "${PROJECT_REF}"
fi

echo "→ Pushing database migrations..."
supabase db push

echo "→ Pushing auth hook config..."
supabase config push

echo ""
echo "✅ Done. Verify with:"
echo "   curl -s -H \"Authorization: Bearer \${SUPABASE_ACCESS_TOKEN}\" \\"
echo "     \"https://api.supabase.com/v1/projects/${PROJECT_REF}/config/auth\" \\"
echo "     | python3 -m json.tool | grep -A1 send_email"
echo ""
echo "Wait ~30s, then retry email signup — it should not 429 anymore."
