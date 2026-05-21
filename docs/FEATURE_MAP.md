# Feature Map — Blu Platform

Mapa de Features de produto que intermediam Tier → Recursos (agents + tools).
Gerado em: 2026-05-21 | Validado contra TOOL_INVENTORY.md

Cada Feature representa uma **capacidade de negócio coerente**. O tier do cliente
determina quais Features estão habilitadas. Cada Feature declara quais agents e tools
compõem essa capacidade.

---

## Princípios do mapa

1. Features são capacidades de negócio, não categorias técnicas.
2. Uma tool pode pertencer a múltiplas Features.
3. Um agente pode pertencer a múltiplas Features.
4. O ResourceResolver faz a interseção: tools do agente ∩ tools da Feature ativa.
5. Features são cumulativas — PREMIUM inclui tudo que SME inclui.

---

## Tier → Features (matriz completa)

| Feature | FREE | BASIC | SME | PREMIUM | ENTERPRISE | ADMIN |
|---------|:----:|:-----:|:---:|:-------:|:----------:|:-----:|
| chat_basico | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| diagnostico | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| rag | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| onboarding | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| monitoramento_web | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| sql_analytics | — | — | ✓ | ✓ | ✓ | ✓ |
| platform_ops | — | — | ✓ | ✓ | ✓ | ✓ |
| synthesis | — | — | ✓ | ✓ | ✓ | ✓ |
| compras_basico | — | — | ✓ | ✓ | ✓ | ✓ |
| financeiro | — | — | ✓ | ✓ | ✓ | ✓ |
| agenda_basico | — | — | ✓ | ✓ | ✓ | ✓ |
| documentos | — | — | ✓ | ✓ | ✓ | ✓ |
| ocr_extraction | — | — | ✓ | ✓ | ✓ | ✓ |
| notion | — | — | ✓ | ✓ | ✓ | ✓ |
| monday | — | — | ✓ | ✓ | ✓ | ✓ |
| whatsapp | — | — | ✓ | ✓ | ✓ | ✓ |
| compras_avancado | — | — | — | ✓ | ✓ | ✓ |
| crm_avancado | — | — | — | ✓ | ✓ | ✓ |
| google_integrations | — | — | — | ✓ | ✓ | ✓ |
| estrategia | — | — | — | ✓ | ✓ | ✓ |
| slack | — | — | — | ✓ | ✓ | ✓ |
| asana_linear | — | — | — | ✓ | ✓ | ✓ |
| fiscal | — | — | — | — | ✓ | ✓ |
| docker_mcp | — | — | — | — | ✓ | ✓ |

---

## Definição detalhada de cada Feature

### FREE

#### chat_basico
> Chat com o assistente sem acesso a dados do negócio.
- agents: frontdesk
- tools: ferramenta_publica_de_teste

#### diagnostico
> Ferramenta de diagnóstico e teste do sistema.
- agents: frontdesk
- tools: ferramenta_publica_de_teste

---

### BASIC

#### rag
> Pesquisa na base de conhecimento do cliente (documentos, PDFs, SOPs).
- agents: frontdesk, documentos
- tools: executar_rag_cliente

#### onboarding
> Coleta de contexto inicial, mapeamento de dados, cadastro de configurações.
- agents: context-gatherer
- tools: check_config_completeness, save_config_field, get_agent_requirements, finalize_config,
         peek_csv_columns, list_data_sources, query_data_catalog, suggest_column_mapping,
         update_schema_mapping, get_knowledge_status, update_context_document,
         register_transaction, write_summary_to_kb, executar_rag_cliente

#### monitoramento_web
> Monitoramento de features de produtos, keywords e menções de marca na web.
- agents: frontdesk
- tools: monitor_feature, monitor_keywords, monitor_company

---

### SME

#### sql_analytics
> Consultas SQL sobre dados estruturados do negócio (vendas, estoque, clientes).
- agents: frontdesk, data-analyst, financeiro, compras, agenda, documentos, estrategia
- tools: execute_sql, executar_sql_agent

#### platform_ops
> Criação e gerenciamento de rotinas automatizadas e metas de negócio via linguagem natural.
- agents: platform, context-gatherer
- tools: criar_rotina, listar_rotinas_catalogo, listar_rotinas_personalizadas,
         criar_rotina_personalizada, enviar_rotina_para_aprovacao,
         definir_meta, listar_metas

#### synthesis
> Análise cross-dimensional que cruza 2+ domínios do negócio (financeiro × compras, clientes × agenda).
- agents: synthesis, data-analyst
- tools: executar_rag_cliente, execute_sql

#### compras_basico
> Análise de padrões de compra, fornecedores e otimização de custos. RFQ básico (sem WhatsApp).
- agents: compras, supplier-agent
- tools: executar_rag_cliente, execute_sql, list_suppliers, dispatch_rfq, check_rfq_responses,
         parse_buying_list, validate_buying_list, optimize_allocation, generate_po_report,
         create_purchase_order, approve_purchase_order, suggest_counter_offer,
         add_supplier, update_supplier, remove_supplier,
         import_buying_list_from_sheets, export_po_to_sheets, submit_mock_response

#### financeiro
> Monitor financeiro: fluxo de caixa, receita, despesas, alertas de anomalia.
- agents: financeiro, data-analyst
- tools: executar_rag_cliente, execute_sql, register_transaction

#### agenda_basico
> Planejamento de agenda, priorização de contatos, follow-up. Sem integrações externas.
- agents: agenda
- tools: executar_rag_cliente, execute_sql

#### documentos
> Busca e digestão de documentos na base de conhecimento. OCR e extração estruturada.
- agents: documentos, context-gatherer
- tools: executar_rag_cliente, execute_sql, write_summary_to_kb,
         extract_document_with_ocr, summarize_document_sections,
         extract_structured_data, compile_time_series

#### ocr_extraction
> Extração de texto e dados estruturados de PDFs e documentos escaneados.
- agents: documentos, doc-writer
- tools: extract_document_with_ocr, summarize_document_sections,
         extract_structured_data, compile_time_series, write_summary_to_kb

#### notion
> Leitura e escrita no Notion (páginas, bases de dados).
- agents: synthesis, doc-writer
- tools: notion_search, notion_read_page, notion_query_database, notion_list_databases,
         notion_list_pages, notion_create_page, notion_update_page,
         notion_append_blocks, notion_delete_block

#### monday
> Integração com Monday.com: boards, itens, status, atualizações.
- agents: scheduler-agent
- tools: monday_list_boards, monday_list_items, monday_create_item,
         monday_update_item_status, monday_get_board_summary,
         monday_get_item_updates, monday_summarize_board

#### whatsapp
> Envio de mensagens via WhatsApp Business (unitário e em lote).
> SME: apenas supplier-agent (RFQ). crm acessa WhatsApp via crm_avancado (PREMIUM).
- agents: supplier-agent
- tools: whatsapp_enviar_mensagem, whatsapp_enviar_lote

---

### PREMIUM

#### compras_avancado
> RFQ via WhatsApp, parsing de respostas de fornecedor, negociação automatizada.
- agents: supplier-agent, compras
- tools: dispatch_rfq_whatsapp, parse_supplier_reply, whatsapp_enviar_mensagem,
         suggest_counter_offer (herda tudo de compras_basico)

#### crm_avancado
> Análise de LTV, cohort, churn prediction, segmentação de clientes, campanhas de reengajamento.
- agents: crm, data-analyst
- tools: executar_rag_cliente, execute_sql, whatsapp_enviar_mensagem, whatsapp_enviar_lote

#### google_integrations
> Google Calendar, Sheets e Docs: leitura, escrita, exportação, criação.
- agents: scheduler-agent, doc-writer, agenda
- tools: query_calendar, write_to_sheet, read_emails, list_google_accounts,
         list_spreadsheets, export_to_sheet, create_spreadsheet_with_data,
         google_docs_create, google_docs_read, google_docs_write, google_docs_list,
         import_spreadsheet_schedule

#### estrategia
> Planejamento estratégico, análise de KPIs, briefs estratégicos, oportunidades de crescimento.
- agents: estrategia, synthesis, data-analyst
- tools: executar_rag_cliente, execute_sql, notion_search, notion_read_page

#### slack
> Leitura e envio de mensagens no Slack: canais, threads, sumários.
- agents: crm, synthesis
- tools: slack_list_channels, slack_read_channel, slack_summarize_channel,
         slack_post_message, slack_get_unread

#### asana_linear
> Gestão de tarefas no Asana e Linear: criar, atualizar, buscar, comentar.
- agents: scheduler-agent, crm
- tools: asana_create_task, asana_update_task, asana_search_tasks,
         asana_get_task_stories, asana_add_task_comment,
         linear_create_issue, linear_update_issue, linear_list_teams,
         linear_list_cycles, linear_add_comment

---

### ENTERPRISE

#### fiscal
> Emissão de NF-e / NFS-e, validação de dados fiscais, integração SEFAZ (stub — parceiro externo).
- agents: fiscal-agent
- tools: fiscal_preparar_dados_nfe, fiscal_status_integracao, executar_rag_cliente, execute_sql

#### docker_mcp
> Integrações Docker MCP: GitHub, Slack (ENTERPRISE), Stripe, PostgreSQL externo, Jira.
- agents: frontdesk (qualquer agente com acesso)
- tools: github_read, github_write, slack_read, slack_send,
         stripe_read, stripe_charge, postgres_query, jira_read, jira_write

---

## Mapa Agente → Features que o habilitam

| Agente | Features |
|--------|---------|
| frontdesk | chat_basico, diagnostico, rag, monitoramento_web, sql_analytics |
| context-gatherer | onboarding, platform_ops, documentos |
| synthesis | synthesis, estrategia, slack (PREMIUM) |
| data-analyst | sql_analytics, synthesis, financeiro, compras_basico, crm_avancado, estrategia |
| platform | platform_ops |
| crm | crm_avancado, whatsapp, slack (PREMIUM), asana_linear (PREMIUM) |
| financeiro | financeiro, sql_analytics |
| compras | compras_basico, compras_avancado (PREMIUM), sql_analytics |
| agenda | agenda_basico, google_integrations (PREMIUM) |
| documentos | rag, documentos, ocr_extraction, notion (SME) |
| estrategia | estrategia (PREMIUM) |
| supplier-agent | compras_basico, compras_avancado (PREMIUM), whatsapp |
| scheduler-agent | agenda_basico, monday, google_integrations (PREMIUM), asana_linear (PREMIUM) |
| doc-writer | documentos, ocr_extraction, notion (SME), google_integrations (PREMIUM) |
| fiscal-agent | fiscal (ENTERPRISE) |

---

## Mudanças de tier_required nos Agentes (vs. estado atual)

Todos os agentes hoje têm `tier_required=TierLevel.BASIC`. Proposta correta:

| Agente | Tier Atual | Tier Correto | Motivo |
|--------|-----------|-------------|--------|
| frontdesk | BASIC | BASIC | OK — entry point universal |
| context-gatherer | BASIC | BASIC | OK — onboarding é universal |
| synthesis | BASIC | SME | Requer SQL + dados estruturados |
| data-analyst | BASIC | SME | Requer SQL analytics |
| platform | BASIC | SME | Requer criar_rotina / definir_meta |
| crm | BASIC | PREMIUM | Requer WhatsApp + Slack + Asana |
| financeiro | BASIC | SME | Requer SQL analytics |
| compras | BASIC | SME | Requer SQL analytics |
| agenda | BASIC | SME | Minimal (sql), mas serve com SME |
| documentos | BASIC | SME | OCR requer SME tier |
| estrategia | BASIC | PREMIUM | Planejamento estratégico = premium feature |
| supplier-agent | BASIC | SME | dispatch_rfq_whatsapp requer SME |
| scheduler-agent | BASIC | SME | Monday requer SME |
| doc-writer | BASIC | SME | Notion + Google Docs requer SME+ |
| fiscal-agent | BASIC | ENTERPRISE | Integração SEFAZ = enterprise only |

---

## Ações de correção antes da implementação

1. Registrar no ToolRegistry as 39 tools fora do registro (plataforma, WhatsApp,
   Slack, Asana, Linear, Monday, Notion) com tier_required correto.
   → Arquivo: `libs/blu_tool_registry/src/blu_tool_registry/registry.py`

2. Mover fiscal_preparar_dados_nfe e fiscal_status_integracao de GOOGLE_TOOLS para BUILTIN_TOOLS.

3. Adicionar tools específicas de domínio nos agentes Monitor (compras, financeiro, agenda, documentos)
   que hoje têm apenas executar_rag + execute_sql.
   → compras: list_suppliers, dispatch_rfq (compras_basico)
   → financeiro: register_transaction
   → agenda: agendar_consulta (se existir)
   → documentos: extract_document_with_ocr, summarize_document_sections

4. Atualizar `tier_required` nos AgentTypeConfig conforme tabela acima.
