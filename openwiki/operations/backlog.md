# Backlog, Decisions & Operational Notes

A live reference of known gaps, dead/ghost tools, architecture decisions, and operational lessons. Source: `docs/llm_wiki/09_backlog_status.md`, `docs/llm_wiki/04_tools.md`, `docs/system_reference/TOOL_INVENTORY.md`, `docs/system_reference/AGENT_SYSTEM.md`.

> Tool counts differ between sources (`TOOL_INVENTORY.md` ~70; `llm_wiki/04_tools.md` ~67 registry / 110 implemented / 52 ghost / 9 dead / 24 unreachable). Both reflect the same underlying problem: **the ToolRegistry is out of sync with implemented MCP modules.** Treat the structural categories below as the source of truth, not the exact counts.

---

## Active backlog

- **Plano 2:** split `company_context` out of `clientes_blu` (after Plano 1 validated). See [data-models/schema](data-models/schema.md).
- **P0:** Register ~42 tools implemented in MCP modules but missing from `ToolRegistry`.
- **P1:** Remove 9 dead `ToolRegistry` entries (no real implementation).
- Fix `tier_required` for all agents.
- Reconcile WhatsApp naming: `whatsapp_enviar_mensagem` vs `send_whatsapp_message`.
- Rename Docker MCP `slack_*` to avoid conflict with real `slack_module`.
- Move `fiscal_preparar_dados_nfe` / `fiscal_status_integracao` from GOOGLE_TOOLS → BUILTIN_TOOLS.
- Fix `send_whatsapp_message` slug in `features.py` (`crm_avancado`).

---

## Tool registry categories (from `llm_wiki/04_tools.md`)

- **BUILTIN_TOOLS:** ~43 (e.g. `executar_rag_cliente`, `execute_sql`, `register_transaction`, `shared_memory_*`).
- **GOOGLE_TOOLS:** 13 (`write_to_sheet`, `read_emails`, `query_calendar`, `google_calendar_write`, `google_docs_*`, …).
- **DOCKER_MCP_TOOLS:** 9 (`github_*`, `slack_*`, `stripe_*`, `postgres_query`, `jira_*`) — **mostly stubs**.

### Dead registry (no real implementation — P1 remove/implement)
`github_read`, `github_write`, `jira_read`, `jira_write`, `postgres_query`, `slack_read`, `slack_send`, `stripe_read`, `stripe_charge`.

### Ghost tools (implemented, invisible to feature/tier system — P0 register)
- Platform/Routines: `criar_rotina`, `listar_rotinas_catalogo` (duplicate), `listar_rotinas_personalizadas`, `criar_rotina_personalizada`, `enviar_rotina_para_aprovacao`, `definir_meta`, `listar_metas`.
- Communication: `send_message`, `send_rfq_via_channel`, `parse_incoming_reply`.
- Monday: `monday_query`, `monday_write`, `monday_brief`.
- Notion (9): `notion_search`, `notion_read_page`, `notion_query_database`, `notion_list_databases`, `notion_list_pages`, `notion_create_page`, `notion_update_page`, `notion_append_blocks`, `notion_delete_block`.
- Google Calendar Write: `google_calendar_write`.
- Slack (5 in `slack_module`): `slack_list_channels`, `slack_read_channel`, `slack_summarize_channel`, `slack_post_message`, `slack_get_unread`.
- Asana/Linear (10): `asana_*`, `linear_*`.

### Unreachable (registered + implemented, no active feature)
`executar_sql_agent` (DEPRECATED D1 — remove), `dispatch_rfq_whatsapp` (SUPERSEDED D5), `parse_supplier_reply` (SUPERSEDED D5), `submit_mock_response` (dev tool), `route_to_specialist` (hardcoded in frontdesk), `ativar_rotina_catalogo` (dangling), `crawl_website`, `extract_company_context`, `generate_report`, `list_report_templates`, `whatsapp_status_mensagem`, `read_emails`, `list_google_accounts` (orphans).

---

## Conflicts to resolve

1. **WhatsApp naming:** `whatsapp_enviar_mensagem` (registry/`whatsapp_client_module`) vs `send_whatsapp_message` (features.py/skills). Standardize on the real implementation.
2. **Slack:** Docker MCP stubs `slack_read`/`slack_send` vs real `slack_module` tools. Rename/remove Docker stubs.
3. **`listar_rotinas_catalogo`:** duplicated in `platform_module` + `routines_module`. Consolidate ownership.
4. **`send_whatsapp_message`** in `features.py` `crm_avancado`: slug doesn't exist. Fix to `whatsapp_enviar_mensagem`.
5. **`fiscal_preparar_dados_nfe`** declared in GOOGLE_TOOLS but category CUSTOM. Move to BUILTIN.

---

## P0 Security: Tier bypass

When a tool has no registry metadata (`meta=None`), the tier filter passes through (`is_accessible_by_tier` returns `True`). A BASIC client could invoke a PREMIUM tool by knowing its slug. **Fix:** register all tools, or deny access when `meta=None`.

---

## Architecture decisions (canonical IDs)

| ID | Decision |
|---|---|
| D1 | `execute_sql` absorbed `executar_sql_agent` (mode direct/agent) |
| D3 | Only `data-entry` may write transactions (via `ledger`) |
| D5 | `parse_business_reply` absorbed `parse_supplier_reply` |
| D6 | `calendar` separated from `document_io`; Google Calendar = PREMIUM |
| D7 | `knowledge_base_write` (write) separated from `document_curation` (ingest) |
| D8 | 13 supplier tools consolidated into `compras_ops` (sub-split deferred) |
| D9 | Sub-split `compras_ops` into 3 skills — planned, not executed |
| D12 | RAG + catalog unified into `data_access` |

---

## Operational lessons (retest, Jun/2026)

- Routine doesn't fire: check `active=true`, `status=active`, `consecutive_failures < 3`, valid `trigger_config`.
- `summary=""` in skill: empty Langfuse prompt, invalid `model_tier`, skill not in registry, tag mismatch.
- `{{var}}` not resolved: prior step `outputs` key ≠ next step template key.
- `column does not exist`: `cross_agent_routines` PK is `id`, not `name`; JSONB accessed with `->>`, not `.`.
- Manual dispatch 401: verify token in `app_config.agent_api_routine_dispatch_token`.
- `insights_synthesis` prompt empty → create `skill:insights_synthesis:system` with label production.
- Artifacts live in `result_metadata` (`storage_path`, `document_id`); direct filesystem writes blocked without service key.
- `website_url` empty in `extract_company_context` → empty doc, non-fatal if `on_failure=continue`.
- Missing inventory/supply integrations → insight flagged critical until connected.

---

## Next

- Tool modules on disk → [integrations/auth](integrations/auth.md)
- Routine resilience details → [routines](architecture/routines.md)
- Adding/repairing a tool → [Dev Playbooks](workflows/dev-playbooks.md)
