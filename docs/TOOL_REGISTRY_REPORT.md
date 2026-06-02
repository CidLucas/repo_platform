# Tool Registry Full Report
Generated: 2026-06-02

## Summary

| Layer | Count |
|-------|-------|
| ToolRegistry (blu_tool_registry) | 67 tools |
| Implemented in MCP modules (tool_pool_api) | 110 tools |
| Referenced in features.py | 96 tools |
| **Ghost MCP** (implemented, NOT in ToolRegistry) | **52** |
| **Dead Registry** (in ToolRegistry, NOT implemented) | **9** |
| **Unreachable** (implemented + in registry, but no feature route to agents) | **24** |

---

## 🔴 CRITICAL: Dead Registry Entries
Tools in `ToolRegistry` but with **no implementation** in any MCP module.
These are Docker MCP stubs — placeholders that expect a running Docker MCP container.
No real code behind them today.

| Tool | Category | Notes |
|------|----------|-------|
| `github_read` | DOCKER_MCP | Expects docker-mcp/github container |
| `github_write` | DOCKER_MCP | Expects docker-mcp/github container |
| `jira_read` | DOCKER_MCP | Expects docker-mcp/jira container |
| `jira_write` | DOCKER_MCP | Expects docker-mcp/jira container |
| `postgres_query` | DOCKER_MCP | Expects docker-mcp/postgres container |
| `slack_read` | DOCKER_MCP | Expects docker-mcp/slack container |
| `slack_send` | DOCKER_MCP | **CONFLICT**: real slack tools are in slack_module.py with different names |
| `stripe_read` | DOCKER_MCP | Expects docker-mcp/stripe container |
| `stripe_charge` | DOCKER_MCP | Expects docker-mcp/stripe container |

**Action**: Either implement docker-mcp bridge or remove these from ToolRegistry.
The slack ones conflict with `slack_module.py` tools — rename or remove.

---

## 🟡 Ghost MCP Tools
Implemented in `tool_pool_api` modules but **not registered** in `ToolRegistry`.
Agents cannot receive them — they exist in the MCP server but are invisible to the feature/tier system.

### Platform / Routines (platform_module + routines_module)
| Tool | Module | Status |
|------|--------|--------|
| `criar_rotina` | platform_module | Referenced in features.py platform_ops |
| `listar_rotinas_catalogo` | platform_module + routines_module | Duplicate across 2 modules |
| `listar_rotinas_personalizadas` | routines_module | Referenced in features.py |
| `criar_rotina_personalizada` | routines_module | Referenced in features.py |
| `enviar_rotina_para_aprovacao` | routines_module | Referenced in features.py |
| `ativar_rotina_catalogo` | routines_module | NOT in features.py — dangling |
| `definir_meta` | platform_module | Referenced in features.py |
| `listar_metas` | platform_module | Referenced in features.py |

**Action**: Add all platform/routines tools to ToolRegistry. Fix `listar_rotinas_catalogo` duplication.

### Communication (communication_module)
| Tool | Module | Status |
|------|--------|--------|
| `send_message` | communication_module | In features.py `communication` — just missing ToolRegistry entry |
| `send_rfq_via_channel` | communication_module | In features.py `communication` |
| `parse_incoming_reply` | communication_module | In features.py `communication` |

**Action**: Add these 3 to ToolRegistry. They are D5 tools — implemented and feature-mapped but invisible.

### Monday.com (monday_module)
| Tool | Module | Status |
|------|--------|--------|
| `monday_query` | monday_module | In features.py `monday` |
| `monday_write` | monday_module | In features.py `monday` |
| `monday_brief` | monday_module | In features.py `monday` |

**Action**: Add to ToolRegistry.

### Notion (notion_module)
| Tool | Module | Status |
|------|--------|--------|
| `notion_search` | notion_module | In features.py `notion` |
| `notion_read_page` | notion_module | In features.py `notion` |
| `notion_query_database` | notion_module | In features.py `notion` |
| `notion_list_databases` | notion_module | In features.py `notion` |
| `notion_list_pages` | notion_module | In features.py `notion` |
| `notion_create_page` | notion_module | In features.py `notion` |
| `notion_update_page` | notion_module | In features.py `notion` |
| `notion_append_blocks` | notion_module | In features.py `notion` |
| `notion_delete_block` | notion_module | In features.py `notion` |

**Action**: Add all 9 to ToolRegistry.

### Google Calendar Write
| Tool | Module | Status |
|------|--------|--------|
| `google_calendar_write` | google_module | In features.py `calendar` — missing ToolRegistry |

**Action**: Add to ToolRegistry (exists in google_module alongside query_calendar which IS registered).

### PM Tools (pm_module)
| Tool | Module | Status |
|------|--------|--------|
| `asana_create_task` | pm_module | In features.py `asana_linear` |
| `asana_update_task` | pm_module | In features.py `asana_linear` |
| `asana_search_tasks` | pm_module | In features.py `asana_linear` |
| `asana_get_task_stories` | pm_module | In features.py `asana_linear` |
| `asana_add_task_comment` | pm_module | In features.py `asana_linear` |
| `linear_create_issue` | pm_module | In features.py `asana_linear` |
| `linear_update_issue` | pm_module | In features.py `asana_linear` |
| `linear_list_teams` | pm_module | In features.py `asana_linear` |
| `linear_list_cycles` | pm_module | In features.py `asana_linear` |
| `linear_add_comment` | pm_module | In features.py `asana_linear` |
| `asana_list_projects` | pm_module | NOT in features.py |
| `asana_get_project_tasks` | pm_module | NOT in features.py |
| `linear_list_issues` | pm_module | NOT in features.py |
| `linear_get_project_summary` | pm_module | NOT in features.py |

**Action**: Add the 10 feature-mapped ones to ToolRegistry. Evaluate the 4 extra (read-only, probably useful).

### Slack (slack_module — different from Docker MCP)
| Tool | Module | Status |
|------|--------|--------|
| `slack_list_channels` | slack_module | In features.py `slack` |
| `slack_read_channel` | slack_module | In features.py `slack` |
| `slack_summarize_channel` | slack_module | In features.py `slack` |
| `slack_post_message` | slack_module | In features.py `slack` |
| `slack_get_unread` | slack_module | In features.py `slack` |

**Action**: Add to ToolRegistry. RENAME Docker MCP `slack_read`/`slack_send` to avoid conflict.

### WhatsApp (whatsapp_client_module)
| Tool | Module | Status |
|------|--------|--------|
| `whatsapp_enviar_lote` | whatsapp_client_module | In features.py `crm_avancado` |
| `whatsapp_enviar_mensagem` | whatsapp_client_module | NOT in features.py (probably replaces `send_whatsapp_message`) |
| `whatsapp_status_mensagem` | whatsapp_client_module | NOT in features.py — dangling |

**Action**: `whatsapp_enviar_lote` → add to ToolRegistry. Check if `send_whatsapp_message` in features.py should be renamed to `whatsapp_enviar_mensagem`.

### Web Crawl (web_crawl_module)
| Tool | Module | Status |
|------|--------|--------|
| `crawl_website` | web_crawl_module | NOT in features.py — dangling |
| `extract_company_context` | web_crawl_module | NOT in features.py — dangling |

**Action**: These are probably used by the onboarding/context-gatherer flow. Add to features.py `onboarding` if relevant, then add to ToolRegistry.

### Report (report_module)
| Tool | Module | Status |
|------|--------|--------|
| `list_report_templates` | report_module | NOT in features.py — dangling |
| `generate_report` | report_module | NOT in features.py — dangling |

**Action**: Evaluate usefulness. If active, add to features + ToolRegistry. Otherwise, candidate for removal.

---

## 🟠 Unreachable Tools
In both ToolRegistry and MCP implementation, but **no feature routes them to any agent**.
Agents can't use them — they exist but are invisible at the feature/tier layer.

| Tool | Assessment |
|------|------------|
| `executar_sql_agent` | **DEPRECATED** — replaced by `execute_sql` (D1). Remove from ToolRegistry. |
| `dispatch_rfq_whatsapp` | **SUPERSEDED** — replaced by `send_rfq_via_channel` (D5). rfq_whatsapp_module.py can be removed. |
| `parse_supplier_reply` | **SUPERSEDED** — replaced by `parse_incoming_reply` (D5). |
| `submit_mock_response` | Test/dev tool. Keep in ToolRegistry, add to `compras_ops` or a `dev_tools` feature. |
| `route_to_specialist` | Correct — hardcoded in frontdesk, injected explicitly (per comment in registry). Not a feature tool. |
| `ferramenta_publica_de_teste` | Used via `chat_basico`/`diagnostico` features (both map to frontdesk). **Not actually unreachable** — false positive. |
| `list_google_accounts` | Orphan — listed in GOOGLE_TOOLS but no feature uses it. Evaluate if needed. |
| `read_emails` | In GOOGLE_TOOLS, no feature uses it. Was it replaced? Add to a feature or remove. |
| `monday_brief` | Ghost + unreachable (no ToolRegistry entry). Fix by adding to ToolRegistry + it IS in features. |
| `monday_query` | Same as monday_brief. |
| `monday_write` | Same as monday_brief. |
| `generate_report` | report_module — dangling, no feature. |
| `list_report_templates` | report_module — dangling, no feature. |
| `asana_list_projects` | pm_module extra — not in features. Low priority. |
| `asana_get_project_tasks` | pm_module extra — not in features. |
| `linear_list_issues` | pm_module extra — not in features. |
| `linear_get_project_summary` | pm_module extra — not in features. |
| `ativar_rotina_catalogo` | routines_module — missing from platform_ops feature. Add or remove. |
| `clickup_list_tasks` | pm_module — ClickUp not in features. Leftover? |
| `clickup_get_task_comments` | pm_module — ClickUp not in features. Leftover? |
| `crawl_website` | web_crawl_module — dangling. |
| `extract_company_context` | web_crawl_module — dangling. |
| `whatsapp_enviar_mensagem` | whatsapp_client_module — possible rename of `send_whatsapp_message`. Check. |
| `whatsapp_status_mensagem` | whatsapp_client_module — dangling. |

---

## 🔵 Conflicts / Overlaps

### SQL Duplication
- `executar_sql_agent` (DEPRECATED) + `execute_sql` (current) — both in ToolRegistry and sql_module.py
- **Fix**: Remove `executar_sql_agent` from ToolRegistry + delete from sql_module.py

### RFQ/WhatsApp Legacy vs D5
- `dispatch_rfq_whatsapp` + `parse_supplier_reply` (old, in rfq_whatsapp_module.py)
- `send_rfq_via_channel` + `parse_incoming_reply` (new D5, in communication_module.py)
- **Fix**: Delete rfq_whatsapp_module.py. Remove old tools from ToolRegistry.

### Slack Name Collision
- `slack_read` / `slack_send` in ToolRegistry (Docker MCP stubs, no real impl)
- `slack_list_channels`, `slack_read_channel`, etc. in slack_module.py (real impl)
- **Fix**: Rename Docker MCP entries to `slack_docker_read`/`slack_docker_send` or remove.

### routines: platform_module vs routines_module
- `listar_rotinas_catalogo` appears in BOTH modules
- platform_module has criar_rotina, definir_meta, listar_metas
- routines_module has listar_rotinas_personalizadas, criar_rotina_personalizada, etc.
- **Fix**: Audit which module owns what. Remove duplicate `listar_rotinas_catalogo`.

### `send_whatsapp_message` (features.py) vs `whatsapp_enviar_mensagem` (whatsapp_client_module)
- features.py `crm_avancado` references `send_whatsapp_message` — doesn't exist
- Real tool is `whatsapp_enviar_mensagem` in whatsapp_client_module
- **Fix**: Rename in features.py OR rename the tool.

---

## Recommended Actions by Priority

### P0 — Register existing D5/core tools (no code change, just ToolRegistry entries)
1. Add to ToolRegistry: `send_message`, `send_rfq_via_channel`, `parse_incoming_reply`
2. Add to ToolRegistry: `monday_query`, `monday_write`, `monday_brief`
3. Add to ToolRegistry: `google_calendar_write`
4. Add to ToolRegistry: all 9 notion tools
5. Add to ToolRegistry: all 8 platform/routines tools (criar_rotina, listar_*, definir_meta, etc.)
6. Add to ToolRegistry: 5 slack_module tools (rename Docker MCP slack_* to avoid conflict)
7. Add to ToolRegistry: 10 asana/linear tools from pm_module

### P1 — Remove dead/superseded entries
1. Remove `executar_sql_agent` from ToolRegistry (D1 — superseded by execute_sql)
2. Remove `dispatch_rfq_whatsapp` + `parse_supplier_reply` from ToolRegistry (D5 — superseded)
3. Evaluate removing `rfq_whatsapp_module.py` entirely
4. Remove or rename Docker MCP `slack_read`/`slack_send` (conflict with slack_module)
5. Fix `send_whatsapp_message` → `whatsapp_enviar_mensagem` in features.py `crm_avancado`

### P2 — Cleanup dangling tools
1. `ativar_rotina_catalogo` — add to platform_ops feature or delete
2. `crawl_website` + `extract_company_context` — add to onboarding feature or delete
3. `generate_report` + `list_report_templates` — define a feature or delete
4. `whatsapp_status_mensagem` — add to feature or delete
5. `read_emails` — add to a feature (maybe crm?) or delete
6. `list_google_accounts` — add to document_io or delete
7. ClickUp tools — evaluate if ClickUp is still a target integration

### P3 — Structural fixes
1. Fix `listar_rotinas_catalogo` duplication across platform_module + routines_module
2. Add `submit_mock_response` to a `dev_tools` feature or mark as internal
3. Add extra PM read tools (asana_list_projects, etc.) to asana_linear feature
