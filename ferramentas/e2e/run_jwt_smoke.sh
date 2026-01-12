#!/usr/bin/env bash
set -euo pipefail

# Simple JWT e2e smoke test that runs a Python snippet inside the
# `atendente_core` container. The script:
#  - generates an HS256 JWT using the container's `SUPABASE_JWT_SECRET` (if present),
#  - includes `client_id` claim (either from argument or default seed),
#  - posts JSON {"message":..., "session_id":...} to `http://127.0.0.1:8000/chat` inside the container,
#  - prints token and HTTP response.
#
# Usage (from repo root):
#   ./ferramentas/e2e/run_jwt_smoke.sh [SERVICE_NAME] [CLIENTE_VIZU_ID]
# Example:
#   ./ferramentas/e2e/run_jwt_smoke.sh atendente_core 9930a61c-953e-47ba-86a2-c7ff03afe367

SERVICE_NAME=${1:-atendente_core}
CLIENTE_VIZU_ID=${2:-9930a61c-953e-47ba-86a2-c7ff03afe367}

echo "Running JWT e2e smoke against service: $SERVICE_NAME (client_id=$CLIENTE_VIZU_ID)"

# Run a Python one-liner inside the container, setting E2E_CLIENTE_VIZU_ID env
docker compose exec -T -e E2E_CLIENTE_VIZU_ID="$CLIENTE_VIZU_ID" "$SERVICE_NAME" python - <<'PY'
import os, json, base64, hmac, hashlib, time, urllib.request, traceback

def b64(u: bytes) -> str:
	return base64.urlsafe_b64encode(u).rstrip(b"=").decode()

secret = os.environ.get('SUPABASE_JWT_SECRET') or os.environ.get('JWT_SECRET') or os.environ.get('VIZU_JWT_SECRET') or 'secret'
header = {'alg': 'HS256', 'typ': 'JWT'}
cliente_id = os.environ.get('E2E_CLIENTE_VIZU_ID') or '00000000-0000-0000-0000-000000000000'

payload = {
	'sub': cliente_id,
	'aud': 'authenticated',
	'exp': int(time.time()) + 300,
	'client_id': cliente_id,
	'role': 'authenticated'
}

hdr = b64(json.dumps(header).encode())
pl = b64(json.dumps(payload).encode())
sign_input = hdr + '.' + pl
sig = hmac.new(secret.encode(), sign_input.encode(), hashlib.sha256).digest()
token = sign_input + '.' + b64(sig)

print('\n---TOKEN-BEGIN---')
print(token)
print('---TOKEN-END---\n')

body = json.dumps({'message': 'E2E JWT smoke', 'session_id': 's-e2e-jwt-script'}).encode()
req = urllib.request.Request('http://127.0.0.1:8000/chat', data=body, headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'})
try:
	resp = urllib.request.urlopen(req, timeout=120)
	print('---HTTP-STATUS---', resp.status)
	print(resp.read().decode())
	raise SystemExit(0)
except Exception as e:
	print('---HTTP-ERROR---', str(e))
	traceback.print_exc()
	raise SystemExit(2)
PY

echo "Done."
