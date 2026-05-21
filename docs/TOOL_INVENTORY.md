# Tool Inventory — Blu Platform

Auditoria completa de todas as tools registradas e usadas pelos agentes.
Gerado em: 2026-05-21 | Fonte: ToolRegistry (registry.py) + AgentTypeRegistry (registry.py)

---

## 1. Tools no ToolRegistry

### 1.1 BUILTIN_TOOLS (42 tools)

| Slug | Categoria | Tier Atual | Domínio | Confirmação |
|------|-----------|-----------|---------|-------------|
| ferramenta_publica_de_teste | PUBLIC | FREE | infra/teste | — |
| executar_rag_cliente | RAG | BASIC | conhecimento | — |
| monitor_feature | PUBLIC | BASIC | monitoramento web | — |
| monitor_keywords | PUBLIC | BASIC | monitoramento web | — |
| monitor_company | PUBLIC | BASIC | monitoramento web | — |
| check_config_completeness | PUBLIC | BASIC | onboarding | — |
| save_config_field | PUBLIC | BASIC | onboarding | — |
| get_agent_requirements | PUBLIC | BASIC | onboarding | — |
| finalize_config | PUBLIC | BASIC | onboarding | — |
| peek_csv_columns | PUBLIC | BASIC | dados | — |
| parse_buying_list | CUSTOM | BASIC | compras/rfq | — |
| validate_buying_list | CUSTOM | BASIC | compras/rfq | — |
| list_suppliers | CUSTOM | BASIC | compras/rfq | — |
| dispatch_rfq | CUSTOM | BASIC | compras/rfq | — |
| check_rfq_responses | CUSTOM | BASIC | compras/rfq | — |
| submit_mock_response | CUSTOM | BASIC | compras/rfq | — |
| optimize_allocation | CUSTOM | BASIC | compras/rfq | — |
| generate_po_report | CUSTOM | BASIC | compras/rfq | — |
| create_purchase_order | CUSTOM | BASIC | compras/rfq | ✓ HITL |
| approve_purchase_order | CUSTOM | BASIC | compras/rfq | ✓ HITL |
| suggest_counter_offer | CUSTOM | BASIC | compras/negociação | — |
| import_buying_list_from_sheets | CUSTOM | BASIC | compras/google | — |
| export_po_to_sheets | CUSTOM | BASIC | compras/google | — |
| add_supplier | CUSTOM | BASIC | compras/fornecedores | — |
| update_supplier | CUSTOM | BASIC | compras/fornecedores | — |
| remove_supplier | CUSTOM | BASIC | compras/fornecedores | — |
| register_transaction | CUSTOM | BASIC | financeiro/dados | ✓ HITL |
| list_data_sources | CUSTOM | BASIC | dados/contexto | — |
| query_data_catalog | CUSTOM | BASIC | dados/contexto | — |
| suggest_column_mapping | CUSTOM | BASIC | dados/contexto | — |
| update_schema_mapping | CUSTOM | BASIC | dados/contexto | ✓ HITL |
| get_knowledge_status | CUSTOM | BASIC | conhecimento | — |
| update_context_document | CUSTOM | BASIC | conhecimento | — |
| dispatch_rfq_whatsapp | CUSTOM | SME | compras/whatsapp | — |
| parse_supplier_reply | CUSTOM | SME | compras/whatsapp | — |
| extract_document_with_ocr | RAG | SME | documentos/ocr | — |
| summarize_document_sections | RAG | SME | documentos/ocr | — |
| extract_structured_data | RAG | SME | documentos/ocr | — |
| compile_time_series | RAG | SME | dados/análise | — |
| write_summary_to_kb | RAG | SME | conhecimento | — |
| fiscal_preparar_dados_nfe | CUSTOM | BASIC | fiscal | — |
| fiscal_status_integracao | CUSTOM | BASIC | fiscal | — |

> Nota: fiscal_preparar_dados_nfe e fiscal_status_integracao estão declaradas dentro
> de GOOGLE_TOOLS no código mas são categoria CUSTOM — provavelmente erro de localização.

### 1.2 GOOGLE_TOOLS (12 tools)

| Slug | Tier Atual | Domínio |
|------|-----------|---------|
| write_to_sheet | PREMIUM | google/sheets |
| read_emails | PREMIUM | google/gmail |
| query_calendar | PREMIUM | google/calendar |
| list_google_accounts | PREMIUM | google/oauth |
| list_spreadsheets | PREMIUM | google/sheets |
| export_to_sheet | PREMIUM | google/sheets |
| create_spreadsheet_with_data | PREMIUM | google/sheets |
| google_docs_create | PREMIUM | google/docs |
| google_docs_read | PREMIUM | google/docs |
| google_docs_write | PREMIUM | google/docs |
| google_docs_list | PREMIUM | google/docs |
| import_spreadsheet_schedule | PREMIUM | google/sheets/agenda |

### 1.3 DOCKER_MCP_TOOLS (9 tools)

| Slug | Tier Atual | Integração | Confirmação |
|------|-----------|-----------|-------------|
| github_read | ENTERPRISE | github | — |
| github_write | ENTERPRISE | github | ✓ HITL |
| slack_read | ENTERPRISE | slack | — |
| slack_send | ENTERPRISE | slack | ✓ HITL |
| stripe_read | ENTERPRISE | stripe | — |
| stripe_charge | ENTERPRISE | stripe | ✓ HITL |
| postgres_query | ENTERPRISE | postgres | — |
| jira_read | ENTERPRISE | jira | — |
| jira_write | ENTERPRISE | jira | ✓ HITL |

**Total no ToolRegistry: 63 tools** (42 builtin + 12 google + 9 docker_mcp)

---

## 2. Tools nos Agentes mas FORA do ToolRegistry

Estas tools são referenciadas em `AgentTypeConfig.enabled_tools` mas retornam
`None` em `ToolRegistry.get_tool()`. O filtro do factory deixa passar todas elas
(branch `is None` na condição) — ou seja, chegam ao MCP sem validação de tier.

### 2.1 Tools de Plataforma (Routines + Goals)

| Slug | Agente(s) que usa | Domínio | Tier correto |
|------|--------------------|---------|-------------|
| criar_rotina | platform | plataforma | SME |
| listar_rotinas_catalogo | platform, context-gatherer | plataforma | SME |
| listar_rotinas_personalizadas | context-gatherer | plataforma | SME |
| criar_rotina_personalizada | context-gatherer | plataforma | SME |
| enviar_rotina_para_aprovacao | context-gatherer | plataforma | SME |
| definir_meta | platform | plataforma | SME |
| listar_metas | platform | plataforma | SME |

### 2.2 Tools de WhatsApp

| Slug | Agente(s) que usa | Domínio | Tier correto |
|------|--------------------|---------|-------------|
| whatsapp_enviar_mensagem | crm, supplier-agent | comunicação | SME |
| whatsapp_enviar_lote | crm | comunicação/crm | SME |

### 2.3 Tools de Slack

| Slug | Agente(s) que usa | Domínio | Tier correto |
|------|--------------------|---------|-------------|
| slack_list_channels | crm, synthesis | comunicação | PREMIUM |
| slack_read_channel | crm | comunicação | PREMIUM |
| slack_summarize_channel | crm, synthesis | comunicação | PREMIUM |
| slack_post_message | crm | comunicação | PREMIUM |
| slack_get_unread | synthesis | comunicação | PREMIUM |

### 2.4 Tools de Asana

| Slug | Agente(s) que usa | Domínio | Tier correto |
|------|--------------------|---------|-------------|
| asana_get_task_stories | crm | agenda/projetos | PREMIUM |
| asana_add_task_comment | crm | agenda/projetos | PREMIUM |
| asana_create_task | scheduler-agent | agenda/projetos | PREMIUM |
| asana_update_task | scheduler-agent | agenda/projetos | PREMIUM |
| asana_search_tasks | scheduler-agent, synthesis | agenda/projetos | PREMIUM |

### 2.5 Tools de Linear

| Slug | Agente(s) que usa | Domínio | Tier correto |
|------|--------------------|---------|-------------|
| linear_add_comment | crm | agenda/projetos | PREMIUM |
| linear_create_issue | scheduler-agent | agenda/projetos | PREMIUM |
| linear_update_issue | scheduler-agent | agenda/projetos | PREMIUM |
| linear_list_teams | scheduler-agent | agenda/projetos | PREMIUM |
| linear_list_cycles | scheduler-agent, synthesis | agenda/projetos | PREMIUM |

### 2.6 Tools de Monday

| Slug | Agente(s) que usa | Domínio | Tier correto |
|------|--------------------|---------|-------------|
| monday_list_boards | scheduler-agent | agenda/monday | SME |
| monday_list_items | scheduler-agent | agenda/monday | SME |
| monday_create_item | scheduler-agent | agenda/monday | SME |
| monday_update_item_status | scheduler-agent | agenda/monday | SME |
| monday_get_board_summary | scheduler-agent | agenda/monday | SME |
| monday_get_item_updates | scheduler-agent | agenda/monday | SME |
| monday_summarize_board | scheduler-agent | agenda/monday | SME |

### 2.7 Tools de Notion

| Slug | Agente(s) que usa | Domínio | Tier correto |
|------|--------------------|---------|-------------|
| notion_search | synthesis, doc-writer | conhecimento | SME |
| notion_read_page | synthesis, doc-writer | conhecimento | SME |
| notion_query_database | synthesis, doc-writer | conhecimento | SME |
| notion_list_databases | synthesis, doc-writer | conhecimento | SME |
| notion_list_pages | doc-writer | conhecimento | SME |
| notion_create_page | doc-writer | conhecimento | SME |
| notion_update_page | doc-writer | conhecimento | SME |
| notion_append_blocks | doc-writer | conhecimento | SME |
| notion_delete_block | doc-writer | conhecimento | SME |

**Total fora do ToolRegistry: 39 tools**
— Todas chegam ao MCP sem validação de tier pelo factory.

---

## 3. Enabled_tools por Agente (mapa completo)

| Agente | Tools no Registry | Tools FORA do Registry | Total |
|--------|:-----------------:|:----------------------:|:-----:|
| frontdesk | executar_rag_cliente, execute_sql, ferramenta_publica_de_teste | — | 3 |
| context-gatherer | write_summary_to_kb, executar_rag_cliente, register_transaction, list_data_sources, query_data_catalog, suggest_column_mapping, update_schema_mapping, get_knowledge_status, update_context_document | listar_rotinas_catalogo, listar_rotinas_personalizadas, criar_rotina_personalizada, enviar_rotina_para_aprovacao | 13 |
| crm | executar_rag_cliente, execute_sql | whatsapp_enviar_mensagem, whatsapp_enviar_lote, slack_list_channels, slack_read_channel, slack_summarize_channel, slack_post_message, asana_get_task_stories, asana_add_task_comment, linear_add_comment | 11 |
| estrategia | executar_rag_cliente, execute_sql | — | 2 |
| compras | executar_rag_cliente, execute_sql | — | 2 |
| financeiro | executar_rag_cliente, execute_sql | — | 2 |
| agenda | executar_rag_cliente, execute_sql | — | 2 |
| documentos | executar_rag_cliente, execute_sql | — | 2 |
| synthesis | executar_rag_cliente, execute_sql | slack_summarize_channel, slack_list_channels, notion_search, notion_read_page, notion_query_database, notion_list_databases, slack_get_unread, asana_search_tasks, linear_list_cycles | 11 |
| data-analyst | executar_rag_cliente, execute_sql | — | 2 |
| platform | executar_rag_cliente | criar_rotina, listar_rotinas_catalogo, definir_meta, listar_metas | 5 |
| supplier-agent | list_suppliers, executar_rag_cliente, execute_sql | dispatch_rfq_whatsapp*, parse_supplier_reply*, whatsapp_enviar_mensagem | 6 |
| scheduler-agent | query_calendar, executar_rag_cliente, execute_sql | monday_list_boards, monday_list_items, monday_create_item, monday_update_item_status, monday_get_board_summary, monday_get_item_updates, monday_summarize_board, asana_create_task, asana_update_task, asana_search_tasks, linear_create_issue, linear_update_issue, linear_list_teams, linear_list_cycles | 17 |
| doc-writer | executar_rag_cliente, execute_sql, google_docs_create, google_docs_write, google_docs_read | notion_list_pages, notion_read_page, notion_search, notion_create_page, notion_update_page, notion_append_blocks, notion_delete_block, notion_query_database, notion_list_databases | 14 |
| fiscal-agent | executar_rag_cliente, execute_sql, fiscal_preparar_dados_nfe, fiscal_status_integracao | — | 4 |

> * dispatch_rfq_whatsapp e parse_supplier_reply têm tier_required=SME no ToolRegistry
>   mas chegam ao supplier-agent mesmo em clientes BASIC porque o agente tem tier_required=BASIC.

---

## 4. Anomalias e Inconsistências Encontradas

### A. Tier BASIC em quase tudo

Todos os 15 agentes têm `tier_required=TierLevel.BASIC`. Isso não reflete a complexidade
real das capacidades — o synthesis agent, strategic-planner e crm specialist deveriam
exigir pelo menos SME ou PREMIUM.

### B. Tools SME chegando a clientes BASIC via supplier-agent

`dispatch_rfq_whatsapp` e `parse_supplier_reply` têm `tier_required=SME` no ToolRegistry,
mas o `supplier-agent` tem `tier_required=BASIC`. O filtro do factory usa `is_accessible_by_tier`,
então BASIC vai falhar na hora de usar essas tools — mas o agente é montado e o erro só
acontece em runtime quando a tool é invocada.

### C. 39 tools fora do ToolRegistry passam sem validação

O filtro: `(meta := ToolRegistry.get_tool(t)) is None or meta.is_accessible_by_tier(tier)`
— quando `meta` é None (tool não registrada), a condição é True e a tool passa.
Isso significa que todas as 39 tools não-registradas chegam ao agente independente do tier.

### D. ENTERPRISE tem os mesmos included_tools que PREMIUM no TierValidator

`TierValidator.TIER_DEFINITIONS["ENTERPRISE"]["included_tools"]` é idêntico ao PREMIUM.
Docker MCP tools (github, slack, stripe) estão em DOCKER_MCP_TOOLS mas não em included_tools.

### E. fiscal_preparar_dados_nfe e fiscal_status_integracao em GOOGLE_TOOLS

Declaradas dentro da seção GOOGLE_TOOLS do ToolRegistry mas categoria é CUSTOM e não
têm nada a ver com Google. Localização incorreta — possível erro copy-paste.

### F. compras, financeiro, agenda, documentos têm apenas executar_rag + execute_sql

Quatro agentes Monitor têm apenas 2 tools declaradas, apesar de serem especializados.
Isso significa que, na prática, funcionam como um frontdesk com prompt diferente —
não têm acesso a tools específicas do seu domínio (ex: compras não tem list_suppliers).

### G. TierValidator.features[] é dead code

A chave `features` existe em todos os TIER_DEFINITIONS mas nunca é lida em nenhum
arquivo do codebase — o FeatureRegistry proposto aproveitará esse campo.
