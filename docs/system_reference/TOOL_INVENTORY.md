# Tool Inventory — Blu Platform

Auditoria completa de todas as tools registradas e usadas pelos agentes.
Revisado em: 2026-06-02 | Fonte: ToolRegistry (registry.py) + AGENT_SYSTEM.md + SKILLS_SYSTEM.md

> **Nota desta revisão:** corrigidos agentes fantasma (`synthesis`, `supplier-agent`, `scheduler-agent`, `documentos`, `estrategia`), nomenclatura WhatsApp/parse_supplier_reply (decisão D5), e tools ausentes (`execute_sql`, `send_whatsapp_message`, `check_whatsapp_replies`, `send_email`, `google_calendar_write`).

---

## 1. Tools no ToolRegistry

### 1.1 BUILTIN_TOOLS (47 tools)

| Slug | Categoria | Tier Atual | Domínio | Confirmação |
|------|-----------|-----------|---------|-------------|
| `ferramenta_publica_de_teste` | PUBLIC | FREE | infra/teste | — |
| `executar_rag_cliente` | RAG | BASIC | conhecimento | — |
| `execute_sql` | CUSTOM | SME | dados/analytics | ⚠️ ausente na v1 do inventário |
| `monitor_feature` | PUBLIC | BASIC | monitoramento web | — |
| `monitor_keywords` | PUBLIC | BASIC | monitoramento web | — |
| `monitor_company` | PUBLIC | BASIC | monitoramento web | — |
| `check_config_completeness` | PUBLIC | BASIC | onboarding | — |
| `save_config_field` | PUBLIC | BASIC | onboarding | — |
| `get_agent_requirements` | PUBLIC | BASIC | onboarding | — |
| `finalize_config` | PUBLIC | BASIC | onboarding | — |
| `peek_csv_columns` | PUBLIC | BASIC | dados | — |
| `generate_chart_html` | PUBLIC | BASIC | dados/relatórios | chart_module.py |
| `parse_buying_list` | CUSTOM | BASIC | compras/rfq | — |
| `validate_buying_list` | CUSTOM | BASIC | compras/rfq | — |
| `list_suppliers` | CUSTOM | BASIC | compras/rfq | — |
| `dispatch_rfq` | CUSTOM | BASIC | compras/rfq | — |
| `check_rfq_responses` | CUSTOM | BASIC | compras/rfq | — |
| `submit_mock_response` | CUSTOM | BASIC | compras/rfq | — |
| `optimize_allocation` | CUSTOM | BASIC | compras/rfq | — |
| `generate_po_report` | CUSTOM | BASIC | compras/rfq | — |
| `create_purchase_order` | CUSTOM | BASIC | compras/rfq | ✓ HITL |
| `approve_purchase_order` | CUSTOM | BASIC | compras/rfq | ✓ HITL |
| `suggest_counter_offer` | CUSTOM | BASIC | compras/negociação | — |
| `import_buying_list_from_sheets` | CUSTOM | BASIC | compras/google | — |
| `export_po_to_sheets` | CUSTOM | BASIC | compras/google | — |
| `add_supplier` | CUSTOM | BASIC | compras/fornecedores | — |
| `update_supplier` | CUSTOM | BASIC | compras/fornecedores | — |
| `remove_supplier` | CUSTOM | BASIC | compras/fornecedores | — |
| `register_transaction` | CUSTOM | BASIC | financeiro/dados | ✓ HITL |
| `list_data_sources` | CUSTOM | BASIC | dados/contexto | — |
| `query_data_catalog` | CUSTOM | BASIC | dados/contexto | — |
| `suggest_column_mapping` | CUSTOM | BASIC | dados/contexto | — |
| `update_schema_mapping` | CUSTOM | BASIC | dados/contexto | ✓ HITL |
| `get_knowledge_status` | CUSTOM | BASIC | conhecimento | — |
| `update_context_document` | CUSTOM | BASIC | conhecimento | — |
| `dispatch_rfq_whatsapp` | CUSTOM | SME | compras/whatsapp | — |
| `parse_business_reply` | CUSTOM | SME | compras+crm/whatsapp | ⚠️ nome antigo era `parse_supplier_reply` (D5) |
| `extract_document_with_ocr` | RAG | SME | documentos/ocr | — |
| `summarize_document_sections` | RAG | SME | documentos/ocr | — |
| `extract_structured_data` | RAG | SME | documentos/ocr | — |
| `compile_time_series` | RAG | SME | dados/análise | — |
|| `write_summary_to_kb` | RAG | SME | conhecimento | — |
|| `fiscal_preparar_dados_nfe` | CUSTOM | ENTERPRISE | fiscal | ⚠️ declarada em GOOGLE_TOOLS no código — mover para BUILTIN |
|| `fiscal_status_integracao` | CUSTOM | ENTERPRISE | fiscal | ⚠️ declarada em GOOGLE_TOOLS no código — mover para BUILTIN |
|| `shared_memory_list` | CUSTOM | SME | memoria/compartilhada | memory_module.py |
|| `shared_memory_link` | CUSTOM | SME | memoria/compartilhada | memory_module.py |
|| `shared_memory_unlink` | CUSTOM | SME | memoria/compartilhada | memory_module.py |
|| `shared_memory_write` | CUSTOM | SME | memoria/compartilhada | memory_module.py — auto_link: bool = True (T3.4) |
|| `shared_memory_get_links` | CUSTOM | SME | memoria/compartilhada | memory_module.py |
|| `confirm_memory_item` | CUSTOM | SME | memoria/compartilhada | ⚠️ T1.3.5 — a implementar |
| `shared_memory_post_flight` | INTERNAL | — | memoria/post-flight | memory_post_flight.py — não exposta via MCP. Persiste agent_result, agent_metadata, agent_link_pending após execução de agente. |

### 1.2 GOOGLE_TOOLS (13 tools)

| Slug | Tier Atual | Domínio |
|------|-----------|---------|
| `write_to_sheet` | PREMIUM | google/sheets |
| `read_emails` | PREMIUM | google/gmail |
| `query_calendar` | PREMIUM | google/calendar |
| `google_calendar_write` | PREMIUM | google/calendar | ⚠️ usada na skill `calendar` mas ausente na v1 do inventário |
| `list_google_accounts` | PREMIUM | google/oauth |
| `list_spreadsheets` | PREMIUM | google/sheets |
| `export_to_sheet` | PREMIUM | google/sheets |
| `create_spreadsheet_with_data` | PREMIUM | google/sheets |
| `import_spreadsheet_schedule` | PREMIUM | google/sheets/agenda |
| `google_docs_create` | PREMIUM | google/docs |
| `google_docs_read` | PREMIUM | google/docs |
| `google_docs_write` | PREMIUM | google/docs |
| `google_docs_list` | PREMIUM | google/docs |

### 1.3 DOCKER_MCP_TOOLS (9 tools)

| Slug | Tier Atual | Integração | Confirmação |
|------|-----------|-----------|-------------|
| `github_read` | ENTERPRISE | github | — |
| `github_write` | ENTERPRISE | github | ✓ HITL |
| `slack_read` | ENTERPRISE | slack | — |
| `slack_send` | ENTERPRISE | slack | ✓ HITL |
| `stripe_read` | ENTERPRISE | stripe | — |
| `stripe_charge` | ENTERPRISE | stripe | ✓ HITL |
| `postgres_query` | ENTERPRISE | postgres | — |
| `jira_read` | ENTERPRISE | jira | — |
| `jira_write` | ENTERPRISE | jira | ✓ HITL |

**Total no ToolRegistry: 70 tools** (48 builtin + 13 google + 9 docker_mcp)

---

## 2. Tools referenciadas em Skills mas FORA do ToolRegistry

Estas tools aparecem em `required_tool_names` nas skill definitions mas não têm entrada no ToolRegistry. Precisam ser registradas.

### 2.1 Tools de Comunicação (skill: `communication`)

| Slug | Skill | Tier correto | Observação |
|------|-------|-------------|------------|
| `send_whatsapp_message` | `communication` | SME | ⚠️ TOOL_INVENTORY v1 usava `whatsapp_enviar_mensagem` — reconciliar |
| `check_whatsapp_replies` | `communication` | SME | Ausente completamente |
| `send_email` | `communication` | SME | Ausente completamente |

### 2.2 Tools de Plataforma (skill: `platform_ops`)

| Slug | Agente(s) que usa | Tier correto |
|------|-------------------|-------------|
| `criar_rotina` | `platform` | SME |
| `listar_rotinas_catalogo` | `platform`, `context-gatherer` | SME |
| `listar_rotinas_personalizadas` | `context-gatherer` | SME |
| `criar_rotina_personalizada` | `context-gatherer` | SME |
| `enviar_rotina_para_aprovacao` | `context-gatherer` | SME |
| `definir_meta` | `platform` | SME |
| `listar_metas` | `platform` | SME |

### 2.3 Tools de Slack (feature: `slack` — PREMIUM)

| Slug | Agente(s) que usa | Tier correto |
|------|-------------------|-------------|
| `slack_list_channels` | `crm`, `strategy` | PREMIUM |
| `slack_read_channel` | `crm` | PREMIUM |
| `slack_summarize_channel` | `crm`, `strategy` | PREMIUM |
| `slack_post_message` | `crm` | PREMIUM |
| `slack_get_unread` | `strategy` | PREMIUM |

### 2.4 Tools de Asana (feature: `asana_linear` — PREMIUM)

| Slug | Agente(s) que usa | Tier correto |
|------|-------------------|-------------|
| `asana_get_task_stories` | `crm` | PREMIUM |
| `asana_add_task_comment` | `crm` | PREMIUM |
| `asana_create_task` | `crm` | PREMIUM |
| `asana_update_task` | `crm` | PREMIUM |
| `asana_search_tasks` | `crm`, `strategy` | PREMIUM |

> ⚠️ Na v1 estas tools estavam atribuídas ao `scheduler-agent` (agente fantasma). Movidas para `crm` e `strategy`. Confirmar se faz sentido ou se haverá um agente dedicado.

### 2.5 Tools de Linear (feature: `asana_linear` — PREMIUM)

| Slug | Agente(s) que usa | Tier correto |
|------|-------------------|-------------|
| `linear_add_comment` | `crm` | PREMIUM |
| `linear_create_issue` | `crm` | PREMIUM |
| `linear_update_issue` | `crm` | PREMIUM |
| `linear_list_teams` | `crm` | PREMIUM |
| `linear_list_cycles` | `crm`, `strategy` | PREMIUM |

### 2.6 Tools de Monday (skill: `monday` — SME)

| Slug | Agente(s) que usa | Tier correto |
|------|-------------------|-------------|
| `monday_list_boards` | `agenda` | SME |
| `monday_list_items` | `agenda` | SME |
| `monday_create_item` | `agenda` | SME |
| `monday_update_item_status` | `agenda` | SME |
| `monday_get_board_summary` | `agenda` | SME |
| `monday_get_item_updates` | `agenda` | SME |
| `monday_summarize_board` | `agenda` | SME |

> ⚠️ Na v1 atribuídas ao `scheduler-agent` (agente fantasma). Movidas para `agenda`.

### 2.7 Tools de Notion (skill: `notion` — SME)

| Slug | Agente(s) que usa | Tier correto |
|------|-------------------|-------------|
| `notion_search` | `doc-writer` | SME |
| `notion_read_page` | `doc-writer` | SME |
| `notion_query_database` | `doc-writer` | SME |
| `notion_list_databases` | `doc-writer` | SME |
| `notion_list_pages` | `doc-writer` | SME |
| `notion_create_page` | `doc-writer` | SME |
| `notion_update_page` | `doc-writer` | SME |
| `notion_append_blocks` | `doc-writer` | SME |
| `notion_delete_block` | `doc-writer` | SME |

> ⚠️ Na v1 atribuídas a `synthesis` e `doc-writer`. `synthesis` era agente fantasma — movidas para `doc-writer` apenas.

**Total fora do ToolRegistry: 42 tools**

---

## 3. Enabled_tools por Agente (mapa completo — agentes canônicos)

| Agente | Skills | Tools no Registry | Tools FORA do Registry | Total |
|--------|--------|:-----------------:|:----------------------:|:-----:|
| `frontdesk` | `data_access`, `sql_analytics` | `executar_rag_cliente`, `execute_sql`, `query_data_catalog`, `ferramenta_publica_de_teste`, `monitor_feature`, `monitor_keywords`, `monitor_company` | — | 7 |
| `data-entry` | `ledger`, `data_access`, `csv_analytics`, `sql_analytics` | `register_transaction`, `execute_sql`, `executar_rag_cliente`, `query_data_catalog`, `peek_csv_columns` | — | 5 |
| `platform` | `platform_ops`, `data_access` | `executar_rag_cliente`, `query_data_catalog` | `criar_rotina`, `listar_rotinas_catalogo`, `definir_meta`, `listar_metas` | 6 |
| `financeiro` | `data_access`, `sql_analytics`, `analytics_charts`, `csv_analytics` | `executar_rag_cliente`, `execute_sql`, `query_data_catalog`, `generate_chart_html`, `peek_csv_columns` | — | 5 |
| `compras` | `compras_ops`, `data_access`, `sql_analytics`, `communication` | `executar_rag_cliente`, `execute_sql`, `query_data_catalog`, `list_suppliers`, `dispatch_rfq`, `check_rfq_responses`, `parse_buying_list`, `validate_buying_list`, `optimize_allocation`, `generate_po_report`, `create_purchase_order`, `approve_purchase_order`, `suggest_counter_offer`, `add_supplier`, `update_supplier`, `remove_supplier`, `import_buying_list_from_sheets`, `export_po_to_sheets`, `dispatch_rfq_whatsapp`, `parse_business_reply` | `send_whatsapp_message`, `check_whatsapp_replies`, `send_email` | 23 |
| `crm` | `crm_ops`, `data_access`, `sql_analytics`, `communication`, `analytics_charts` | `executar_rag_cliente`, `execute_sql`, `query_data_catalog`, `generate_chart_html`, `parse_business_reply` | `send_whatsapp_message`, `check_whatsapp_replies`, `send_email`, `whatsapp_enviar_lote`, `slack_list_channels`, `slack_read_channel`, `slack_summarize_channel`, `slack_post_message`, `asana_get_task_stories`, `asana_add_task_comment`, `asana_create_task`, `asana_update_task`, `asana_search_tasks`, `linear_add_comment`, `linear_create_issue`, `linear_update_issue`, `linear_list_teams`, `linear_list_cycles` | 23 |
| `agenda` | `agenda_ops`, `sql_analytics`, `monday`, `calendar`, `meeting_brief` | `executar_rag_cliente`, `execute_sql`, `query_calendar`, `google_calendar_write`, `import_spreadsheet_schedule` | `monday_list_boards`, `monday_list_items`, `monday_create_item`, `monday_update_item_status`, `monday_get_board_summary`, `monday_get_item_updates`, `monday_summarize_board` | 12 |
| `data-analyst` | `data_access`, `sql_analytics`, `analytics_charts`, `csv_analytics`, `document_io` | `executar_rag_cliente`, `execute_sql`, `query_data_catalog`, `generate_chart_html`, `peek_csv_columns`, `google_docs_create`, `google_docs_read`, `google_docs_write`, `google_docs_list`, `write_to_sheet`, `list_spreadsheets`, `export_to_sheet`, `create_spreadsheet_with_data` | — | 13 |
| `strategy` | `data_access`, `sql_analytics`, `analytics_charts`, `insights_synthesis`, `hidden_patterns` | `executar_rag_cliente`, `execute_sql`, `query_data_catalog`, `generate_chart_html` | `slack_list_channels`, `slack_summarize_channel`, `slack_get_unread`, `asana_search_tasks`, `linear_list_cycles` | 9 |
| `doc-writer` | `data_access`, `knowledge_base_write`, `document_io`, `document_curation`, `notion` | `executar_rag_cliente`, `query_data_catalog`, `write_summary_to_kb`, `get_knowledge_status`, `update_context_document`, `extract_document_with_ocr`, `summarize_document_sections`, `extract_structured_data`, `compile_time_series`, `google_docs_create`, `google_docs_read`, `google_docs_write`, `google_docs_list` | `notion_search`, `notion_read_page`, `notion_query_database`, `notion_list_databases`, `notion_list_pages`, `notion_create_page`, `notion_update_page`, `notion_append_blocks`, `notion_delete_block` | 22 |
| `context-gatherer` | `data_access`, `sql_analytics`, `knowledge_base_write`, `onboarding`, `document_curation` | `executar_rag_cliente`, `execute_sql`, `query_data_catalog`, `write_summary_to_kb`, `get_knowledge_status`, `update_context_document`, `check_config_completeness`, `save_config_field`, `get_agent_requirements`, `finalize_config`, `list_data_sources`, `suggest_column_mapping`, `update_schema_mapping`, `peek_csv_columns`, `extract_document_with_ocr`, `summarize_document_sections`, `extract_structured_data`, `compile_time_series` | `listar_rotinas_catalogo`, `listar_rotinas_personalizadas`, `criar_rotina_personalizada`, `enviar_rotina_para_aprovacao` | 22 |
| `fiscal-agent` | `fiscal`, `data_access`, `sql_analytics` | `executar_rag_cliente`, `execute_sql`, `query_data_catalog`, `fiscal_preparar_dados_nfe`, `fiscal_status_integracao` | — | 5 |

---

## 4. Anomalias e Inconsistências

### A. execute_sql ausente da v1 do inventário
Tool mais usada do sistema (11 agentes, 8+ skills) não estava listada em BUILTIN_TOOLS. Adicionada nesta revisão com `tier_required=SME`.

### B. Tier BASIC em quase todos os agentes
Todos os 12 agentes têm `tier_required=TierLevel.BASIC`. Proposta de correção no FEATURE_MAP.md.

### C. 42 tools fora do ToolRegistry passam sem validação de tier
O filtro: `(meta := ToolRegistry.get_tool(t)) is None or meta.is_accessible_by_tier(tier)` — quando `meta` é None, a condição é True e a tool passa sem validação. **Risco de segurança:** cliente BASIC pode invocar tools PREMIUM se souber o slug.

### D. Nomenclatura inconsistente de WhatsApp
- `whatsapp_enviar_mensagem` (TOOL_INVENTORY v1, registry.py)
- `send_whatsapp_message` (SKILLS_SYSTEM, skill `communication`)
- `whatsapp_enviar_lote` (ambos, ok)
Um destes nomes está errado. Reconciliar com o código da tool real.

### E. parse_supplier_reply vs parse_business_reply
Decisão D5 renomeou `parse_supplier_reply` → `parse_business_reply` (escopo mais amplo, cobre clientes e fornecedores). TOOL_INVENTORY v1 ainda usava o nome antigo. Corrigido nesta revisão.

### F. fiscal tools em GOOGLE_TOOLS
`fiscal_preparar_dados_nfe` e `fiscal_status_integracao` estão declaradas dentro de GOOGLE_TOOLS no código mas são categoria CUSTOM. Mover para BUILTIN_TOOLS. Tier corrigido para ENTERPRISE (era BASIC).

### G. ENTERPRISE tem os mesmos included_tools que PREMIUM no TierValidator
`TierValidator.TIER_DEFINITIONS["ENTERPRISE"]["included_tools"]` é idêntico ao PREMIUM. Docker MCP tools estão em `DOCKER_MCP_TOOLS` mas não em `included_tools`.

### H. TierValidator.features[] é dead code
A chave `features` existe em todos os TIER_DEFINITIONS mas nunca é lida — o FeatureRegistry proposto aproveitará esse campo.

### I. google_calendar_write ausente da v1 do inventário
Usada pela skill `calendar` mas não listada em GOOGLE_TOOLS. Adicionada nesta revisão.
