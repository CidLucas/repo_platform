# CODE MAP — repo_platform

> Mapeamento de arquivos → responsabilidades → documentação relacionada.
> Mantido automaticamente pelo agente de documentação (cron noturno).
> Última atualização: 2026-05-25

---

## Backend — Agent API (`services/agent_api/`)

### Core (`src/agent_api/core/`)

| Arquivo | Responsabilidade | Docs relacionados |
|---|---|---|
| `routines.py` (1.619L) | Engine de execução de rotinas: orquestra steps (skill/function), gerencia state dict, anti-entupimento (semáforo, circuit breaker, heartbeat), reaper de execuções travadas | `docs/routines/rotinas_fluxo_e_dependencias.md`, pitfalls em `repo-platform-context` skill |
| `routine_functions.py` (2.735L) | 11 fetch functions que alimentam as rotinas com dados do DB: `get_finance_indicators`, `get_commercial_indicators`, `get_supply_indicators`, `get_upcoming_meetings`, etc. | `docs/routines/rotinas_fluxo_e_dependencias.md` |
| `routine_artifacts.py` (808L) | Salva outputs das rotinas: insights (`client_insights`), relatórios, whatsapp messages, structured data. Inclui `save_insights()` com mapeamento dimension→room | `docs/routines/rotinas_fluxo_e_dependencias.md` |
| `factory.py` (406L) | Monta grafos LangGraph por tier/cliente. 3 caminhos: frontdesk, standalone agent, worker de rotina. Carrega tools via MCP, aplica tier enforcement | `docs/agent_system_map.md`, `docs/FEATURE_MAP.md` |
| `service.py` (813L) | Camada de serviço de chat: gerencia sessão, contexto, streaming de resposta ao frontend | `docs/agent_system_map.md` |
| `observability.py` (73L) | Configura Langfuse callback handler por invocação (trace_id, session_id, user_id). Fix de traces fragmentados aplicado Mai-2026 | `docs/observability/README.md` |

### API Routers (`src/agent_api/api/`)

| Arquivo | Endpoints principais |
|---|---|
| `agents_router.py` (781L) | CRUD de agentes, standalone agent sessions, catalog |
| `chat_router.py` (235L) | `/v1/chat` — streaming de chat com o atendente |
| `routines_router.py` (196L) | `/v1/internal/routines/run-dispatched` — recebe dispatch do pg_cron |
| `google_calendar_webhook_router.py` (219L) | Recebe webhooks de mudança de calendário Google |
| `schemas.py` (211L) | Pydantic schemas das requests/responses da API |

---

## Backend — Tool Pool API (`services/tool_pool_api/`)

### Tool Modules (`src/tool_pool_api/server/tool_modules/`)

Tools expostas via MCP — chamadas pelos agentes LangGraph.

| Módulo | LOC | Ferramentas principais |
|---|---|---|
| `sql_module.py` | 1.029 | `execute_sql`, `get_schema` — executa SQL seguro contra analytics_v2 |
| `context_module.py` | 1.052 | `get_business_context`, `save_insight`, `get_inventory_alerts`, `get_meetings`, `_derive_entry_type` |
| `google_module.py` | 802 | `get_calendar_events`, `send_gmail`, `create_calendar_event`, OAuth refresh |
| `monday_module.py` | 744 | `get_monday_boards`, `create_monday_item`, `update_monday_item` — two-phase fetch para evitar complexity limit |
| `notion_module.py` | 824 | `search_notion`, `get_notion_page`, `create_notion_page` |
| `slack_module.py` | 959 | `send_slack_message`, `get_slack_channels`, `post_slack_file` |
| `rfq_module.py` | 2.031 | Fluxo completo de RFQ (cotação): pesquisa fornecedores, gera solicitação, acompanha resposta |
| `rfq_whatsapp_module.py` | 398 | Envio de RFQ via WhatsApp (Twilio) |
| `pm_module.py` | 1.331 | Gestão de projetos: tarefas, sprints, aprovações |
| `document_intelligence_module.py` | 571 | Análise de documentos (NF, contratos, PDFs) |
| `ocr_extraction_module.py` | 420 | Extração de texto via OCR |
| `rag_module.py` | 167 | `search_documents` — busca vetorial na knowledge base |
| `report_module.py` | 570 | Geração de relatórios estruturados |
| `web_crawl_module.py` | 227 | Crawl de páginas (análise de concorrentes, via crawl4ai) |
| `web_monitor_module.py` | 142 | Monitoramento de mudanças em páginas web |
| `fiscal_module.py` | 112 | Consultas fiscais (CNPJ, NF-e) |
| `consumer_inbox_module.py` | 318 | Inbox de mensagens do consumidor |
| `platform_module.py` | 427 | Tools de plataforma: tenant config, feature flags |
| `routines_module.py` | 398 | Tools de gerenciamento de rotinas expostas ao agente |
| `prompt_module.py` | 247 | Busca e renderização de prompts via Langfuse |
| `config_helper_module.py` | 454 | Helpers de configuração de agentes/skills |
| `whatsapp_client_module.py` | 253 | Client WhatsApp via Twilio |
| `structured_data_formatter.py` | 293 | Formata dados estruturados para output do agente |
| `report_format_adapters.py` | 195 | Adapta formato de relatórios por destino (chat, PDF, etc.) |
| `report_templates.py` | 187 | Templates de relatórios |
| `common_module.py` | 62 | Utilitários compartilhados entre módulos |

### API Routers (`src/tool_pool_api/api/`)

| Arquivo | Endpoints principais |
|---|---|
| `admin_router.py` (667L) | Gestão de clientes, offboarding, configs de tenant |
| `integrations_router.py` (576L) | CRUD de `integration_tokens` (Slack, Monday, Notion, Google) |
| `polp_webhook_router.py` (267L) | Recebe webhooks Polp (open finance) |
| `twilio_webhook_router.py` (331L) | Recebe webhooks Twilio (WhatsApp) |
| `reports_router.py` (282L) | Geração e entrega de relatórios |
| `ingest_router.py` (126L) | Endpoints de ingestão de dados |
| `inbox_dispatch_router.py` (136L) | Dispatch de mensagens de inbox |

---

## Libs Python (`libs/`)

| Lib | LOC | Responsabilidade |
|---|---|---|
| `blu_agent_framework` | ~6.750 | LangGraph: grafos, builder de agentes, skill_factory, checkpointer Redis, registry, orchestrator, approval flow |
| `blu_prompt_management` | ~4.483 | Carrega prompts do Langfuse (type=skill obrigatório), fallback em `templates.py`. `get_builtin_template()` para L3 |
| `blu_tool_registry` | ~3.079 | Registry de tools por tier/feature, ResourceResolver (interseção tier × features) |
| `blu_models` | ~4.044 | Pydantic models compartilhados entre services e libs |
| `blu_context_service` | ~1.578 | Redis cache + snapshot de memória de negócio do cliente |
| `blu_llm_service` | ~1.753 | Wrapper de chamadas LLM (Ollama Cloud, OpenAI), logging, correlation IDs |
| `blu_rag_factory` | ~1.332 | Pipeline RAG: embedding, indexação, hybrid search (pgvector) |
| `blu_hitl_service` | ~1.135 | Human-in-the-loop: Redis sorted sets, filas de aprovação |
| `blu_supabase_client` | — | Client Supabase + CRUD compartilhado. `db_engine.py` expõe `get_pooler_engine()` e `get_direct_engine()` |
| `blu_auth` | — | JWT decoder, MCP middleware, estratégias de auth |
| `blu_shared_utils` | — | Data transformers, text utils |
| `blu_sql_factory` | — | SQL seguro: allowlist, schema snapshot, exemplar validator, Text-to-SQL |
| `blu_parsers` | — | Parsers de documentos (NF-e, etc.) |
| `blu_google_suite_client` | — | Client Google (Sheets, Drive, Calendar) |
| `blu_twilio_client` | — | Client Twilio (WhatsApp, SMS) |
| `blu_data_connectors` | — | Conectores de fontes de dados externas |
| `blu_db_connector` | — | Connector de DB (pool, migrations helper) |
| `blu_landing_intel` | — | Inteligência de landing (website intel do onboarding) |
| `blu_elicitation_service` | — | Elicitação de dados estruturados do usuário |
| `blu_experiment_service` | — | A/B experiments, feature flags experimentais |
| `blu_observability_bootstrap` | — | Setup de OTEL/Grafana no boot dos services |

### blu_agent_framework — Detalhe dos arquivos principais

| Arquivo | LOC | Responsabilidade |
|---|---|---|
| `builder.py` | 1.356 | Monta o grafo LangGraph completo: nodes, edges, tools, checkpointer |
| `nodes.py` | 1.009 | Nós do grafo: reasoning, tool_call, approval_gate, output |
| `orchestrator.py` | 678 | L4 orchestrator: classifica intent, roteia para specialist |
| `registry.py` | 616 | Registry de agentes e skills disponíveis |
| `checkpointer.py` | 558 | Persistência de estado do grafo no Redis |
| `skills.py` | 377 | Definição e carregamento de skills L2 |
| `skill_factory.py` | 271 | Executa uma skill: carrega prompt, monta tools, invoca LLM |
| `routing.py` | 260 | Lógica de routing entre agentes |
| `mcp_client.py` | 341 | Client MCP para conectar ao Tool Pool API |
| `approval.py` | 414 | Fluxo de aprovação HITL |
| `state.py` | 349 | Definição do AgentState (LangGraph) |
| `routines/context_report.py` | — | Geração de relatório de contexto do cliente |

---

## Supabase

### Edge Functions (`supabase/functions/`)

| Função | Responsabilidade |
|---|---|
| `onboarding-bootstrap` | Provisiona tenant: cria client_routines, semeia configurações |
| `onboarding-website-intel` | Extrai inteligência do site da empresa (CNPJ, ramo, contexto) |
| `onboarding-capture-drive-token` | Captura e salva token OAuth Google Drive (Fernet encrypt) |
| `google-oauth-start` / `google-oauth-callback` | Fluxo OAuth Google server-side |
| `get-agenda-events` | Busca eventos Google Calendar + Monday + Notion em paralelo, retorna array unificado |
| `get-monday-subitems` | Lazy fetch de subitems Monday por item_id (evita complexity limit) |
| `google-calendar-events` | Busca eventos de calendário Google para um cliente |
| `save-api-token` | Salva token de API (Slack, Monday, Notion) com validação prévia do provider |
| `polp-connect` | Inicia conexão Polp (open finance), retorna URL de autenticação |
| `polp-webhook` | Recebe eventos Polp em tempo real |
| `polp-sync` | Sync manual de contas + transações Polp |
| `run-csv-etl` | ETL de CSV do cliente → staging → fato_transacoes |
| `run-sync-etl` | Sync incremental de dados externos → fato_transacoes |
| `discover-bigquery-columns` | Detecta colunas de tabela BigQuery do cliente |
| `match-columns` | Mapeia colunas do cliente para colunas canônicas Blu (column_mapping) |
| `process-document` | Processa documento (OCR, extração de dados) |
| `search-documents` | Busca vetorial na knowledge base |
| `upload-csv-source` | Upload de CSV como fonte de dados |
| `upload-drive-source` | Upload de Google Drive como fonte de dados |
| `generate-context-report` | Gera relatório de contexto do cliente |
| `website-context-builder` | Constrói contexto a partir do site da empresa |
| `routine-builder` | Cria/edita rotinas via linguagem natural |
| `_shared` | Helpers compartilhados: `requireAuth`, `resolveClientId`, `fernetEncrypt` |

### DB — Schemas e tabelas principais

| Schema | Tabelas principais |
|---|---|
| `public` | `clientes_blu` (+ `active_clientes_blu` view), `client_routines`, `cross_agent_routines`, `approval_requests`, `app_config`, `integration_tokens`, `integration_configs` |
| `analytics_v2` | `fato_transacoes` (PK: transacao_id+client_id), `dim_inventory` (coluna: `nome`), `dim_clientes`, `dim_fornecedores`, `client_insights` (campo: `room`), `reg_jobs` |
| `polp_*` | `polp_integrations`, `polp_accounts`, `polp_transactions`, `polp_bills` |

**entry_type canônicos:** `revenue | purchase | expense | banking`
**client_insights.room slugs:** `financeiro | clientes | compras | agenda | estrategia | home`

> 82 migrations em `supabase/migrations/`. Sem Alembic — aplicar via `psql -f arquivo.sql`.

---

## Frontend (`apps/blu_v3/`)

### Rooms (`src/pages/app/`)

| Room | LOC | Domínio |
|---|---|---|
| `AdminScreen.tsx` | 1.319 | Config de tenant, integrações, tokens |
| `FinanceiroRoom.tsx` | 908 | KPIs financeiros, fluxo de caixa, receita, custo |
| `HomePage.tsx` | 583 | Dashboard principal, resumo multi-domínio |
| `BibliotecaRoom.tsx` | 579 | Knowledge base, documentos |
| `ClientesRoom.tsx` | 572 | CRM, pipeline, inadimplência, NPS |
| `DocumentosRoom.tsx` | 526 | Upload e análise de documentos |
| `EstrategiaRoom.tsx` | 496 | Planejamento, análise competitiva |
| `AgentOpsRoom.tsx` | 471 | Operações de agentes, monitoring |
| `AgendaRoom.tsx` | 406 | Gantt dinâmico (rotinas + aprovações + eventos externos) |
| `ComprasRoom.tsx` | 400 | Inventory, fornecedores, RFQ |
| `AgentesScreen.tsx` | 374 | Catálogo e config de agentes |
| `AtividadeScreen.tsx` | 204 | Feed de atividade recente |

### API layer (`src/api/`)

Cada arquivo mapeia para um domínio — chamam edge functions Supabase ou o Agent API direto.

### Hooks (`src/hooks/`)

| Hook | Responsabilidade |
|---|---|
| `useAtendenteChat.ts` | Streaming de chat com o agente |
| `useAnalytics.ts` | Queries de KPIs e métricas |
| `useApprovals.ts` | Fila de aprovações HITL |
| `useAgents.ts` | Catálogo de agentes disponíveis |
| `useAuth.ts` | Auth state, JWT, client_id |
| `useNotifications.ts` | Notificações em tempo real |
| `useConnectorStatus.ts` | Status de integrações conectadas |

---

## Docs (`docs/`)

| Arquivo | O que contém |
|---|---|
| `HERMES.md` | Context map principal: stack, estado atual, gaps, decisões, próximos passos |
| `agent_system_map.md` | Mapa completo de agentes, skills, routines, tools, roadmap |
| `FEATURE_MAP.md` | Tier → Features → Agents + Tools (matriz completa) |
| `TOOL_INVENTORY.md` | Auditoria das 42+ tools por tier/domínio |
| `platform_description.md` | Visão geral do produto, arquitetura |
| `onboarding-context-map.md` | Fluxo de onboarding, provisionamento de tenant |
| `routines/rotinas_fluxo_e_dependencias.md` | Fluxo técnico de rotinas, step types, catálogo, triggers |
| `BACKLOG_IDEAS.md` | Ideias capturadas durante o dev |
| `archive/Blu_Routines_MVP_Backlog.md` | 42 histórias em 7 épicos — backlog MVP de rotinas |
| `CODE_MAP.md` | Este arquivo |
| `TASK_PLAYBOOKS.md` | Receitas passo a passo por tipo de tarefa |
| `CHANGELOG.md` | Log de mudanças diário em linguagem humana |
