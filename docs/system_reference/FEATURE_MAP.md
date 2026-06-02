# Feature Map — Blu Platform

Mapa de Features de produto que intermediam Tier → Recursos (agents + skills → tools).
Revisado em: 2026-06-02 | Fonte da verdade: AGENT_SYSTEM.md + SKILLS_SYSTEM.md

**Agentes canônicos (12):** `frontdesk`, `data-entry`, `platform`, `financeiro`, `compras`, `crm`, `agenda`, `data-analyst`, `strategy`, `doc-writer`, `context-gatherer`, `fiscal-agent`

> ⚠️ Versão anterior continha agentes fantasma (`synthesis`, `supplier-agent`, `scheduler-agent`, `documentos`, `estrategia`) que não existem no registry. Todos removidos nesta revisão.

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
- agents: `frontdesk`
- tools: `ferramenta_publica_de_teste`

#### diagnostico
> Ferramenta de diagnóstico e teste do sistema.
- agents: `frontdesk`
- tools: `ferramenta_publica_de_teste`

---

### BASIC

#### rag
> Pesquisa na base de conhecimento do cliente (documentos, PDFs, SOPs).
- agents: `frontdesk`, `context-gatherer`
- skills: `data_access`
- tools: `executar_rag_cliente`, `query_data_catalog`

#### onboarding
> Coleta de contexto inicial, mapeamento de dados, cadastro de configurações.
- agents: `context-gatherer`
- skills: `onboarding`, `knowledge_base_write`
- tools: `check_config_completeness`, `save_config_field`, `get_agent_requirements`, `finalize_config`,
         `peek_csv_columns`, `list_data_sources`, `query_data_catalog`, `suggest_column_mapping`,
         `update_schema_mapping`, `get_knowledge_status`, `update_context_document`,
         `write_summary_to_kb`, `executar_rag_cliente`

> ⚠️ `register_transaction` foi removido do onboarding — escrita de transações é exclusiva do `data-entry`.

#### monitoramento_web
> Monitoramento de features de produtos, keywords e menções de marca na web.
- agents: `frontdesk`
- tools: `monitor_feature`, `monitor_keywords`, `monitor_company`

---

### SME

#### sql_analytics
> Consultas SQL sobre dados estruturados do negócio (vendas, estoque, clientes).
- agents: `frontdesk`, `data-entry`, `data-analyst`, `financeiro`, `compras`, `crm`, `agenda`, `strategy`, `context-gatherer`, `fiscal-agent`
- skills: `sql_analytics`
- tools: `execute_sql`

> ⚠️ `executar_sql_agent` foi removido — absorvido por `execute_sql` (mode=direct|agent) per decisão D1.

#### platform_ops
> Criação e gerenciamento de rotinas automatizadas e metas de negócio via linguagem natural.
- agents: `platform`
- skills: `platform_ops`
- tools: `criar_rotina`, `listar_rotinas_catalogo`, `listar_rotinas_personalizadas`,
         `criar_rotina_personalizada`, `enviar_rotina_para_aprovacao`,
         `definir_meta`, `listar_metas`

> Nota: `context-gatherer` usa `listar_rotinas_catalogo` durante onboarding (contexto de capacidades disponíveis), mas não gerencia rotinas ativamente.

#### synthesis
> Análise cross-dimensional que cruza 2+ domínios do negócio (financeiro × compras × clientes × agenda).
- agents: `strategy`, `data-analyst`
- skills: `insights_synthesis`, `hidden_patterns`, `strategy_analysis`
- tools: `executar_rag_cliente`, `execute_sql`

#### compras_basico
> Análise de padrões de compra, fornecedores e otimização de custos. RFQ básico (sem WhatsApp).
- agents: `compras`
- skills: `sql_analytics`, `data_access`
- tools: `executar_rag_cliente`, `execute_sql`, `list_suppliers`, `dispatch_rfq`, `check_rfq_responses`,
         `parse_buying_list`, `validate_buying_list`, `optimize_allocation`, `generate_po_report`,
         `create_purchase_order`, `approve_purchase_order`, `suggest_counter_offer`,
         `add_supplier`, `update_supplier`, `remove_supplier`,
         `import_buying_list_from_sheets`, `export_po_to_sheets`, `submit_mock_response`

#### financeiro
> Monitor financeiro: fluxo de caixa, receita, despesas, alertas de anomalia.
- agents: `financeiro`, `data-analyst`
- skills: `sql_analytics`, `analytics_charts`, `data_access`
- tools: `executar_rag_cliente`, `execute_sql`, `generate_chart_html`

> ⚠️ `register_transaction` removido — financeiro é read-only. Escrita → `data-entry`.

#### agenda_basico
> Planejamento de agenda, priorização de contatos, follow-up. Sem integrações externas.
- agents: `agenda`
- skills: `sql_analytics`, `data_access`, `meeting_brief`
- tools: `executar_rag_cliente`, `execute_sql`

#### documentos
> Busca e digestão de documentos na base de conhecimento. OCR e extração estruturada.
- agents: `context-gatherer`, `doc-writer`
- skills: `document_curation`, `knowledge_base_write`, `data_access`
- tools: `executar_rag_cliente`, `execute_sql`, `write_summary_to_kb`,
         `extract_document_with_ocr`, `summarize_document_sections`,
         `extract_structured_data`, `compile_time_series`

#### ocr_extraction
> Extração de texto e dados estruturados de PDFs e documentos escaneados.
- agents: `context-gatherer`, `doc-writer`
- skills: `document_curation`
- tools: `extract_document_with_ocr`, `summarize_document_sections`,
         `extract_structured_data`, `compile_time_series`, `write_summary_to_kb`

#### notion
> Leitura e escrita no Notion (páginas, bases de dados).
- agents: `doc-writer`
- skills: `notion`
- tools: `notion_search`, `notion_read_page`, `notion_query_database`, `notion_list_databases`,
         `notion_list_pages`, `notion_create_page`, `notion_update_page`,
         `notion_append_blocks`, `notion_delete_block`

#### monday
> Integração com Monday.com: boards, itens, status, atualizações.
- agents: `agenda`
- skills: `monday`
- tools: `monday_list_boards`, `monday_list_items`, `monday_create_item`,
         `monday_update_item_status`, `monday_get_board_summary`,
         `monday_get_item_updates`, `monday_summarize_board`

#### whatsapp
> Envio e recebimento de mensagens via WhatsApp Business.
- agents: `compras`, `crm`
- skills: `communication`
- tools: `send_whatsapp_message`, `check_whatsapp_replies`, `whatsapp_enviar_lote`

> ⚠️ Inconsistência de nomenclatura: TOOL_INVENTORY usa `whatsapp_enviar_mensagem`, SKILLS_SYSTEM usa `send_whatsapp_message`. A reconciliar no ToolRegistry.

---

### PREMIUM

#### compras_avancado
> RFQ via WhatsApp, parsing de respostas de fornecedor, negociação automatizada.
- agents: `compras`
- skills: `communication`
- tools: `dispatch_rfq_whatsapp`, `parse_supplier_reply`, `send_whatsapp_message`,
         `suggest_counter_offer` (herda tudo de compras_basico)

#### crm_avancado
> Análise de LTV, cohort, churn prediction, segmentação de clientes, campanhas de reengajamento.
- agents: `crm`, `data-analyst`
- skills: `sql_analytics`, `analytics_charts`, `communication`, `data_access`
- tools: `executar_rag_cliente`, `execute_sql`, `send_whatsapp_message`, `whatsapp_enviar_lote`

#### google_integrations
> Google Calendar, Sheets e Docs: leitura, escrita, exportação, criação.
- agents: `agenda`, `doc-writer`, `data-analyst`
- skills: `calendar`, `document_io`
- tools: `query_calendar`, `google_calendar_write`, `import_spreadsheet_schedule`,
         `write_to_sheet`, `read_emails`, `list_google_accounts`,
         `list_spreadsheets`, `export_to_sheet`, `create_spreadsheet_with_data`,
         `google_docs_create`, `google_docs_read`, `google_docs_write`, `google_docs_list`

#### estrategia
> Planejamento estratégico, análise de KPIs, briefs estratégicos, oportunidades de crescimento.
- agents: `strategy`, `data-analyst`
- skills: `insights_synthesis`, `hidden_patterns`, `strategy_analysis`, `competitor_analysis`
- tools: `executar_rag_cliente`, `execute_sql`

#### slack
> Leitura e envio de mensagens no Slack: canais, threads, sumários.
- agents: `crm`, `strategy`
- tools: `slack_list_channels`, `slack_read_channel`, `slack_summarize_channel`,
         `slack_post_message`, `slack_get_unread`

> ⚠️ Tools de Slack ainda não estão no ToolRegistry — ver seção 2.3 do TOOL_INVENTORY.

#### asana_linear
> Gestão de tarefas no Asana e Linear: criar, atualizar, buscar, comentar.
- agents: `crm`
- tools: `asana_create_task`, `asana_update_task`, `asana_search_tasks`,
         `asana_get_task_stories`, `asana_add_task_comment`,
         `linear_create_issue`, `linear_update_issue`, `linear_list_teams`,
         `linear_list_cycles`, `linear_add_comment`

> ⚠️ Asana/Linear ainda não estão no ToolRegistry. Anteriormente atribuídos a `scheduler-agent` (agente fantasma) — movidos para `crm`.

---

### ENTERPRISE

#### fiscal
> Emissão de NF-e / NFS-e, validação de dados fiscais, integração SEFAZ (stub — parceiro externo).
- agents: `fiscal-agent`
- skills: `fiscal`
- tools: `fiscal_preparar_dados_nfe`, `fiscal_status_integracao`, `executar_rag_cliente`, `execute_sql`

#### docker_mcp
> Integrações Docker MCP: GitHub, Slack (ENTERPRISE), Stripe, PostgreSQL externo, Jira.
- agents: `frontdesk` (qualquer agente com acesso)
- tools: `github_read`, `github_write`, `slack_read`, `slack_send`,
         `stripe_read`, `stripe_charge`, `postgres_query`, `jira_read`, `jira_write`

---

## Mapa Agente → Features que o habilitam

| Agente | Features |
|--------|---------|
| `frontdesk` | chat_basico, diagnostico, rag, monitoramento_web, sql_analytics |
| `context-gatherer` | onboarding, rag, documentos, ocr_extraction |
| `data-entry` | sql_analytics (read para verificação antes de escrever) |
| `platform` | platform_ops |
| `financeiro` | financeiro, sql_analytics |
| `compras` | compras_basico, compras_avancado (PREMIUM), whatsapp, sql_analytics |
| `crm` | crm_avancado, whatsapp, slack (PREMIUM), asana_linear (PREMIUM) |
| `agenda` | agenda_basico, monday, google_integrations (PREMIUM) |
| `data-analyst` | sql_analytics, synthesis, financeiro, crm_avancado, estrategia, google_integrations |
| `strategy` | synthesis, estrategia, slack (PREMIUM) |
| `doc-writer` | documentos, ocr_extraction, notion, google_integrations (PREMIUM) |
| `fiscal-agent` | fiscal (ENTERPRISE) |

---

## Mudanças de tier_required propostas (vs. estado atual)

Todos os agentes hoje têm `tier_required=TierLevel.BASIC`. Proposta:

| Agente | Tier Atual | Tier Correto | Motivo |
|--------|-----------|-------------|--------|
| `frontdesk` | BASIC | BASIC | OK — entry point universal |
| `context-gatherer` | BASIC | BASIC | OK — onboarding é universal |
| `data-entry` | BASIC | BASIC | OK — escrita de dados = capacidade básica |
| `platform` | BASIC | SME | Requer criar_rotina / definir_meta |
| `financeiro` | BASIC | SME | Requer SQL analytics |
| `compras` | BASIC | SME | Requer SQL analytics + tools de compras |
| `crm` | BASIC | PREMIUM | Requer WhatsApp + Slack + Asana |
| `agenda` | BASIC | SME | Requer Monday + SQL |
| `data-analyst` | BASIC | SME | Requer SQL analytics + charts |
| `strategy` | BASIC | PREMIUM | Análise cross-domain = premium feature |
| `doc-writer` | BASIC | SME | Notion + Google Docs requer SME+ |
| `fiscal-agent` | BASIC | ENTERPRISE | Integração SEFAZ = enterprise only |

---

## Ações de correção pendentes

1. **Registrar no ToolRegistry** as tools fora do registro (plataforma, WhatsApp, Slack, Asana, Linear, Monday, Notion) com `tier_required` correto.
   → `libs/blu_tool_registry/src/blu_tool_registry/registry.py`

2. **Reconciliar nomenclatura de WhatsApp**: `whatsapp_enviar_mensagem` (TOOL_INVENTORY) vs `send_whatsapp_message` (SKILLS_SYSTEM/communication).

3. **Registrar tools ausentes**: `check_whatsapp_replies`, `send_email`, `google_calendar_write` — usadas em skills mas não no ToolRegistry.

4. **Registrar `execute_sql`** como BUILTIN_TOOL — usada por todos os agentes mas ausente da seção 1.1 do TOOL_INVENTORY.

5. **Mover fiscal tools** de GOOGLE_TOOLS para BUILTIN_TOOLS no ToolRegistry (são CUSTOM, não Google).

6. **Atualizar `tier_required`** nos AgentTypeConfig conforme tabela acima.

7. **Definir destino de Asana/Linear**: anteriormente em `scheduler-agent` (agente fantasma). Agora em `crm` — confirmar se faz sentido ou criar o `scheduler-agent` de fato.
