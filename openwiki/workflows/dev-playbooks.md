# Dev Playbooks

Step-by-step recipes for recurring development tasks. Consolidated from `docs/system_reference/TASK_PLAYBOOKS.md`. Each playbook names the files involved so an agent can implement without re-deriving structure.

---

## 1. Add a new routine

**Files:** `supabase/migrations/` (seed `cross_agent_routines`), `services/agent_api/src/agent_api/core/routine_functions.py`, `routine_artifacts.py`, `libs/blu_agent_framework/.../routines/`, `blu_prompt_management/templates.py`, Langfuse.

**Steps:**
1. Seed `cross_agent_routines`:
   ```sql
   INSERT INTO cross_agent_routines (
     id,            -- english slug, e.g. 'daily_cash_alert'
     name,          -- PT-BR readable, e.g. 'Alerta de Caixa Diário'
     room,          -- financeiro|clientes|compras|agenda|estrategia|home
     trigger_type,  -- 'cron' | 'event' | 'manual'
     trigger_config,-- e.g. '{"expression": "0 8 * * *"}'
     steps,         -- jsonb array of step objects
     agent_slug,    -- responsible agent slug
     active         -- true
   ) VALUES (...);
   ```
2. If new data needed, add `async def get_xxx(client_id, ...) -> dict` in `routine_functions.py` and register in the top dispatch dict.
3. For `type=skill` steps: create file under `libs/blu_agent_framework/.../routines/`, add prompt to `templates.py` (`skill:{name}:system`, `type=skill`) **and** Langfuse (production).
4. Persist output via `routine_artifacts.py`: `save_insights()` (with `room`) or `save_report()`.
5. Activate for a client: `INSERT INTO client_routines (client_id, routine_id, active, status, source, trigger_config) VALUES (..., 'catalog', '{}');`
6. Test (see playbook 9).

**Pitfalls:**
- `triggered_by` is NOT NULL on `client_routine_executions` — always pass `'cron'` on manual INSERT.
- `{{variable}}` in steps needs a default in the *step*, not in client config.
- `client_routines.source` accepts only `catalog | custom | system`.
- `active=false` silently blocks dispatch — check before testing.
- Never use `is_active` (doesn't exist) — use `active`.

---

## 2. Add a fetch function

File: `services/agent_api/src/agent_api/core/routine_functions.py`.
- Add `async def get_xxx(client_id: str, ...) -> dict`.
- Register in the dispatch dict at top of file.
- Routine step `type="function"` references it by name.

---

## 3. Add an L3 skill (Langfuse prompt)

- Create skill file under `libs/blu_agent_framework/.../routines/` (if routine skill) or register in skill system.
- Add fallback prompt to `blu_prompt_management/templates.py` with key `skill:{name}:system`, `type=skill`.
- Create equivalent prompt in **Langfuse** (label `production`) — prod source of truth.
- Document in `docs/system_reference/SKILLS_SYSTEM.md`.

See [skills](agents/skills.md) for catalog + governance.

---

## 4. Add an API token integration

- Backend: `services/tool_pool_api/src/tool_pool_api/api/integrations_router.py`.
- For Google: add `config`/`initiate`/`callback`/`accounts`/`default`/`revoke`/`status` routes; store per-client config in `integration_configs` (encrypted), tokens in `integration_tokens` via `context.save_integration_tokens(...)`.
- For shortcut-token providers (e.g. Monday): store token in `integration_tokens` with the provider name; load via `context.get_integration_tokens(...)`.
- Encrypt secrets with Fernet (see `_shared` in edge functions).

---

## 5. Add a tool module

- Create module in `services/tool_pool_api/src/tool_pool_api/server/tool_modules/`.
- Register tools with the MCP server.
- **Register the tool in `blu_tool_registry`** (see [backlog](operations/backlog.md) for why unregistered tools are a P0 security issue).
- If tier-gated, ensure `meta` is set so `is_accessible_by_tier` works.

---

## 6. Create a schema migration

- Add SQL file in `supabase/migrations/` (no Alembic).
- Apply via `psql -f <file>.sql`.
- If routines/agents read the new column/table, update `data_schema` in `clientes_blu` and `column_mapping` logic.
- 82 migrations exist; follow naming/ordering convention.

---

## 7. Add an Edge Function

- Add Deno function in `supabase/functions/`.
- Use `_shared` helpers: `requireAuth`, `resolveClientId`, `fernetEncrypt`.
- Expose via `supabase/functions/<name>/index.ts`; register route if called from frontend/backend.
- Onboarding-related functions listed in [onboarding](onboarding.md).

---

## 8. Add a frontend room

- Add room page under `apps/blu_v3/src/pages/app/` (e.g. `FinanceiroRoom.tsx`).
- Wire route + sidebar; associate with its responsible agent (see [agents/catalog](agents/catalog.md)).
- Surface routines via the room's Config tab; surface pending approvals (HITL) in Home.

---

## 9. Test a routine manually

- Insert into `client_routine_executions` with `status='dispatched'` and `triggered_by='manual'`.
- Trigger the pg_cron → pg_net dispatch, or call `/v1/internal/routines/run-dispatched` with the correct dispatch token (`app_config.agent_api_routine_dispatch_token`).
- Watch `heartbeat_at` (every 20s) and `status` transitions.
- If `summary=""`: check Langfuse prompt, `model_tier`, skill registry, tag match.

---

## 10. Onboard a test client

- Run the onboarding wizard against a test tenant (or call edge functions directly: `ensure_tenant_row` → `onboarding-bootstrap` → `upload-*` → `run-*-etl` → `match-columns`).
- Seed routines from `cross_agent_routines` into `client_routines`.
- Verify `dimension_state` / `client_insights` populate after a monitor routine runs.

---

## Next

- Routine internals → [routines](architecture/routines.md)
- Tool registry gaps → [backlog](operations/backlog.md)
- Agent/skill catalog → [agents/catalog](agents/catalog.md)
