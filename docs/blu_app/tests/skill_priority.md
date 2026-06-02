# Skill Priority Map

## Phase 0 — Core Routing

| ID | Skill | Expected Tool | Agent Slug |
|---|---|---|---|
| 0.1 | frontdesk | route_to_specialist | frontdesk |
| 0.2 | sql_analytics | execute_sql | frontdesk/data-analyst |
| 0.3 | rag_search | executar_rag_cliente | frontdesk |

## Phase 1 — Scheduled Reports

| ID | Skill | Expected Tool | Agent Slug |
|---|---|---|---|
| 1.1 | morning_plan | get_calendar_events | agenda |
| 1.2 | end_of_day_digest | execute_sql | financeiro |
| 1.3 | weekly_summary | execute_sql | financeiro |
| 1.4 | reconciliation_report | execute_sql | financeiro |

## Phase 2 — Write Ops

| ID | Skill | Expected Tool | Agent Slug |
|---|---|---|---|
| 2.1 | ledger | register_transaction | data-entry |
| 2.2 | fornecedores | add_supplier | compras |
| 2.3 | platform_ops | criar_rotina | platform |
| 2.4 | platform_ops | definir_meta | platform |
| 2.5 | hitl_approval | hitl_approval | data-entry |

## Phase 3 — CRM + Compras + Financeiro Analytics

| ID | Skill | Expected Tool | Agent Slug |
|---|---|---|---|
| 3.1 | crm_ops | get_client_insights | crm |
| 3.2 | crm_ops | whatsapp_enviar_mensagem | crm |
| 3.3 | compras_ops | dispatch_rfq | compras |
| 3.4 | financeiro_ops | execute_sql | financeiro |

## Phase 4 — Integrations

| ID | Skill | Expected Tool | Agent Slug |
|---|---|---|---|
| 4.1 | monday | monday_create_item | agenda |
| 4.2 | monday | monday_list_boards | agenda |
| 4.3 | monday | monday_update_item | agenda |
| 4.4 | monday | monday_get_board_items | agenda |
| 4.5 | calendar | get_calendar_events | agenda |
| 4.6 | calendar | create_calendar_event | agenda |
| 4.7 | meeting_brief | get_calendar_events | agenda |
| 4.8 | google_docs | google_docs_list | doc-writer |
| 4.9 | google_docs | google_docs_read | doc-writer |
| 4.10 | google_workspace | google_docs_create | doc-writer |
| 4.11 | google_workspace | google_docs_write | doc-writer |
| 4.12 | google_workspace | create_spreadsheet_with_data | doc-writer |

## Phase 5 — Cross-Domain Synthesis

| ID | Skill | Expected Tool | Agent Slug |
|---|---|---|---|
| 5.1 | insights_synthesis | execute_sql | strategy |
| 5.2 | hidden_patterns | execute_sql | data-analyst |
| 5.3 | competitor_analysis | executar_rag_cliente | strategy |
