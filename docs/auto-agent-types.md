# Auto-generated agent types
_Generated from `blu_agent_framework.registry.AgentTypeRegistry`._

## `agenda` — Scheduling Specialist

- **description**: Scheduling and follow-up planning specialist. Creates structured follow-up schedules, prioritises client contacts, and recommends engagement timing. Used in routines for weekly follow-up reminders.
- **tier_required**: `BASIC`
- **max_turns**: 5  **on_max_turns**: `return_partial`
- **enabled_tools**: `executar_rag_cliente`, `execute_sql`
- **prompt_name**: `agents/frontdesk`
- **routing_hint**: Follow-up scheduling, client contact prioritisation, calendar planning.

## `compras` — Procurement Specialist

- **description**: Procurement and supplier analysis specialist. Analyses purchase patterns, identifies supplier risks, and recommends cost optimisation strategies. Used in routines for monthly procurement reviews.
- **tier_required**: `BASIC`
- **max_turns**: 5  **on_max_turns**: `return_partial`
- **enabled_tools**: `executar_rag_cliente`, `execute_sql`
- **prompt_name**: `agents/frontdesk`
- **routing_hint**: Procurement analysis, supplier reviews, purchasing cost optimisation.

## `context-gatherer` — Context Agent

- **description**: Structured data gathering and mapping specialist. Registers transactions from natural language, creates automation routine definitions, maps spreadsheet columns to database fields, and curates the knowledge base. Use when the user wants to record data, set up automations, or organise their information landscape.
- **tier_required**: `BASIC`
- **max_turns**: 6  **on_max_turns**: `return_partial`
- **enabled_tools**: `listar_rotinas_catalogo`, `listar_rotinas_personalizadas`, `criar_rotina_personalizada`, `enviar_rotina_para_aprovacao`, `write_summary_to_kb`, `executar_rag_cliente`, `register_transaction`, `list_data_sources`, `query_data_catalog`, `suggest_column_mapping`, `update_schema_mapping`, `get_knowledge_status`, `update_context_document`
- **fragments**: fragment/context-gatherer-base, fragment/transaction-extraction-rules, fragment/schema-mapping-workflow, fragment/routine-definition-workflow, fragment/knowledge-curation-workflow, fragment/confirmation-patterns
- **routing_hint**: Recording sales, purchases, expenses, or events. Setting up automations or routines. Mapping data sources or spreadsheet columns. Organising documents, tagging knowledge base files, cleaning up duplicates. Anything that prepares data for other skills to use.

## `crm` — CRM Specialist

- **description**: Client relationship and communication specialist. Writes personalised outreach emails, analyses client segments, and recommends engagement strategies. Used in routines for reengagement campaigns and follow-ups.
- **tier_required**: `BASIC`
- **max_turns**: 5  **on_max_turns**: `return_partial`
- **enabled_tools**: `executar_rag_cliente`, `execute_sql`
- **prompt_name**: `agents/frontdesk`
- **routing_hint**: Writing client emails, personalised outreach, CRM campaigns.

## `documentos` — Documents Specialist

- **description**: Knowledge base and document analysis specialist. Searches and summarises stored documents, identifies knowledge gaps, and produces weekly digests. Used in routines for knowledge base maintenance.
- **tier_required**: `BASIC`
- **max_turns**: 5  **on_max_turns**: `return_partial`
- **enabled_tools**: `executar_rag_cliente`, `execute_sql`
- **prompt_name**: `agents/frontdesk`
- **routing_hint**: Document search, knowledge base digests, content gap analysis.

## `estrategia` — Strategy Specialist

- **description**: Business strategy and performance analysis specialist. Analyses KPIs, identifies growth opportunities, and writes strategic briefs. Used in routines for monthly reviews and low-acquisition alerts.
- **tier_required**: `BASIC`
- **max_turns**: 5  **on_max_turns**: `return_partial`
- **enabled_tools**: `executar_rag_cliente`, `execute_sql`
- **prompt_name**: `agents/frontdesk`
- **routing_hint**: Strategic analysis, business performance reviews, growth recommendations.

## `financeiro` — Financial Specialist

- **description**: Financial health and reporting specialist. Analyses revenue trends, ticket averages, and cash flow indicators. Used in routines for weekly financial snapshots and alerts.
- **tier_required**: `BASIC`
- **max_turns**: 5  **on_max_turns**: `return_partial`
- **enabled_tools**: `executar_rag_cliente`, `execute_sql`
- **prompt_name**: `agents/frontdesk`
- **routing_hint**: Financial reports, revenue analysis, cash flow monitoring.

## `frontdesk` — Frontdesk

- **description**: Entry point specialist. Handles simple RAG and SQL queries directly. Routes complex or multi-domain tasks to the appropriate specialist via handoff tool. Use as the first point of contact for all user requests.
- **tier_required**: `BASIC`
- **max_turns**: 10  **on_max_turns**: `return_partial`
- **enabled_tools**: `executar_rag_cliente`, `execute_sql`, `ferramenta_publica_de_teste`
- **prompt_name**: `agents/frontdesk`
- **routing_hint**: Entry point. Simple knowledge questions, basic data queries.

