# E2E JWT Smoke

This folder contains a small smoke script to validate the JWT authentication flow inside the `atendente_core` container.

Script: `run_jwt_smoke.sh`

What it does:
- Generates an HS256 JWT inside the target container using the container's `SUPABASE_JWT_SECRET` (or fallback envs).
- Includes `cliente_vizu_id` in the token claims (so the JWT strategy can map the token to an existing client).
- Posts a JSON chat payload to `http://127.0.0.1:8000/chat` inside the container and prints the response.

Usage

From the repo root:

```bash
# Make it executable (only needed once)
chmod +x ferramentas/e2e/run_jwt_smoke.sh

# Run against default service and seeded client id
./ferramentas/e2e/run_jwt_smoke.sh atendente_core 9930a61c-953e-47ba-86a2-c7ff03afe367

# Or use the Makefile shortcut (overriding vars if needed):
make e2e-jwt
# or
make e2e-jwt SERVICE=atendente_core CLIENTE_VIZU_ID=your-uuid-here
```

Notes

- The script runs the Python snippet inside the container so it uses the container runtime environment and secrets.
- Ensure `docker compose up` has been run and the `atendente_core` service is healthy before running the script.
- The expected `/chat` payload shape is `{"message": "...", "session_id": "..."}`.
