# Integrations & Auth

How platform integrations authenticate, how services obtain tokens, and how routines safely call Google/Monday. Source: `docs/system_reference/INTEGRATIONS_AUTH.md`, `docs/system_reference/TOOL_INVENTORY.md`, `services/tool_pool_api/src/tool_pool_api/api/integrations_router.py`.

---

## Google — OAuth2 with account list + default account

**Backend:** `services/tool_pool_api/src/tool_pool_api/api/integrations_router.py`

Endpoints:
- `POST /integrations/google/config` — save per-client OAuth client config
- `POST /integrations/google/auth/initiate` — start OAuth2 flow
- `GET /integrations/google/callback` — complete OAuth2 flow
- `GET /integrations/google/accounts` — list connected accounts
- `POST /integrations/google/accounts/default` — set default account
- `DELETE /integrations/google/auth/revoke` — revoke token(s)
- `GET /integrations/google/status` — connection status

**Flow:**
1. Per-client config in `integration_configs` (encrypted `client_id`/`client_secret`, scopes, redirect URI).
2. Platform fallback: `context.get_platform_oauth_config("google")` from Supabase Vault when no per-client config exists.
3. Auth state in Redis at `oauth_state:{state}` mapped to `auth.client_id`.
4. Callback exchanges code for tokens, saved via `context.save_integration_tokens(...)` with account metadata (`access_token`, `refresh_token`, `expires_at`, `account_email`, `account_name`, `is_default`).
5. Token resolution for tool calls uses `context.get_integration_tokens(..., auto_refresh=True)` when available.

**Routine use:** routine steps call Google via `google.*` wrappers in `routine_functions.py`:
- `google.list_connected_accounts`
- `google.calendar.events`
These delegate to MCP Google tools through `_call_mcp_tool()` and return plain dicts for routine state.

---

## Monday — shortcut token lookup (no OAuth router)

**Backend module:** `services/tool_pool_api/src/tool_pool_api/server/tool_modules/monday_module.py`
**MCP tools:** `monday_query`, `monday_write`, `monday_brief`

**Flow:** There is **no** OAuth init/callback router in `integrations_router.py`. Auth uses a shortcut token:
1. Token stored in `integration_tokens` with `provider='monday'`.
2. `_get_monday_token(client_id)` loads it via `context.get_integration_tokens(...)`.
3. On missing token, tool fails closed: *"Monday.com não conectado. Vá em Admin → Integrações para conectar."*

**Routine use:** `monday.*` wrappers:
- `monday.list_boards`
- `monday.board_summary`

---

## Routine-callable integration summary

| Integration | Routine wrapper | MCP tool(s) | Auth source |
|---|---|---|---|
| Google | `google.list_connected_accounts` | `google_list_accounts` | `integration_tokens` via `_call_mcp_tool` + context |
| Google | `google.calendar.events` | `google_calendar_events` | same |
| Monday | `monday.list_boards` | `monday_list_boards` | `integration_tokens` via `_get_monday_token` |
| Monday | `monday.board_summary` | `monday_get_board_summary` | same |

**Operational rules:**
- Never hardcode provider tokens in routine functions or docs.
- Keep Google's multi-account pattern.
- Monday does not expose an OAuth router in the same backend module.
- Use `on_failure: continue` when integrations are optional.

---

## Other tool modules (MCP)

`tool_pool_api/server/tool_modules/` includes: `sql_module` (`execute_sql`, `get_schema`), `context_module`, `google_module`, `monday_module`, `notion_module`, `slack_module`, `rfq_module`, `rfq_whatsapp_module`, `pm_module`, `document_intelligence_module`, `ocr_extraction_module`, `rag_module`, `report_module`, `web_crawl_module`, `web_monitor_module`, `fiscal_module`, `consumer_inbox_module`, `platform_module`, `routines_module`, `prompt_module`, `config_helper_module`, `whatsapp_client_module`, and formatters.

---

## Tier gating caveat (P0 security)

Per `TOOL_INVENTORY.md`: when a tool has **no registry metadata** (`meta=None`), the tier filter passes through (`is_accessible_by_tier` returns `True`). A client on BASIC could invoke a PREMIUM tool by knowing its slug. Remediation: register all tools or deny access when `meta=None`. See [backlog](operations/backlog.md).

---

## Next

- Tool registry & ghost/dead tools → [backlog](operations/backlog.md)
- Adding a token integration → [Dev Playbooks](workflows/dev-playbooks.md)
