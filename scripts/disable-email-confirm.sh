#!/usr/bin/env bash
# Disable email confirmation on the remote Supabase project.
#
# Why: the built-in email provider limits /auth/v1/signup to 2 emails/hour.
# When email confirmation is ON, every signup sends a confirmation email and
# counts against that limit. Turning it OFF makes signup silent and lifts the
# 2/h cap (the remaining limit is 30/h by IP — plenty for dev).
#
# Usage:
#   1. Get a token at https://supabase.com/dashboard/account/tokens
#   2. export SUPABASE_ACCESS_TOKEN=<paste>
#   3. ./scripts/disable-email-confirm.sh
#
# Verify after running:
#   curl -s -H "Authorization: Bearer $SUPABASE_ACCESS_TOKEN" \
#     "https://api.supabase.com/v1/projects/haruewffnubdgyofftut/config/auth" \
#     | python3 -c "import sys, json; print(json.load(sys.stdin)['mailer_autoconfirm'])"

set -euo pipefail

: "${SUPABASE_ACCESS_TOKEN:?Set SUPABASE_ACCESS_TOKEN (https://supabase.com/dashboard/account/tokens)}"

PROJECT_REF="haruewffnubdgyofftut"
URL="https://api.supabase.com/v1/projects/${PROJECT_REF}/config/auth"

echo "→ Fetching current auth config..."
CURRENT=$(curl -s -H "Authorization: Bearer ${SUPABASE_ACCESS_TOKEN}" "${URL}")
echo "   mailer_autoconfirm = $(echo "${CURRENT}" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("mailer_autoconfirm"))')"

echo "→ Setting mailer_autoconfirm=true..."
RESULT=$(curl -s -X PATCH \
  -H "Authorization: Bearer ${SUPABASE_ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{ "mailer_autoconfirm": true }' \
  "${URL}")

echo "→ New value:"
echo "   mailer_autoconfirm = $(echo "${RESULT}" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("mailer_autoconfirm"))')"

if [ "$(echo "${RESULT}" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("mailer_autoconfirm"))')" = "True" ]; then
  echo "✅ Done. New signups will not send confirmation emails."
  echo "   Wait ~1 minute for the change to propagate, then retry signup."
else
  echo "❌ Failed. Response:"
  echo "${RESULT}"
  exit 1
fi
