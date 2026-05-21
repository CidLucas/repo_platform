# HERMES.md — Context Map para o Agente

> Lido no início de qualquer sessão de trabalho no repo_platform.
> Atualizar sempre que surgir novo documento relevante ou decisão importante.

---

## O que é o Blu

Escritório virtual com IA para donos de PMEs brasileiras. Não é dashboard nem chatbot — é um time de agentes que trabalha para o dono. Interface em salas. Produto em construção.

Monorepo: `/Users/lucascruz/Documents/GitHub/repo_platform`

---

## Stack

| Camada | Localização | Tech |
|---|---|---|
| Frontend app | `apps/blu_v3/` | React 18 + TS + Vite + Tailwind v3. Porta 5175 |
| Frontend landing | `apps/landing/` | Landing + onboarding wizard |
| Agent API | `services/agent_api/` | FastAPI — orquestra agentes, executa rotinas |
| Tool Pool API | `services/tool_pool_api/` | FastAPI — tools expostas via MCP (SQL, RAG, Google, OCR, RFQ) |
| blu_agent_framework | `libs/blu_agent_framework/` | LangGraph: grafos, skills, agentes, routines engine |
| blu_context_service | `libs/blu_context_service/` | Redis cache + snapshot de memória de negócio |
| blu_prompt_management | `libs/blu_prompt_management/` | Prompts via Langfuse (fallback builtin). type=skill obrigatório. |
| blu_models | `libs/blu_models/` | Pydantic models compartilhados |
| blu_supabase_client | `libs/blu_supabase_client/` | Client Supabase + CRUD compartilhado |
| DB | Supabase (hosted) | PostgreSQL + pgvector + RLS + pg_cron |

DB credentials: haruewffnubdgyofftut (us-west-2). JWT expira ~1h: get_test_token.py.
Ollama Cloud: tag explícita obrigatória (ex: ministral-3:8b).

---

## Arquitetura: Event-Driven + Shared Memory + Swarm (Arquitetura C)

4 camadas progressivas — nenhuma pula uma camada:

```
L4  Orchestrator (User-Facing Agent) — recebe input, classifica, roteia para L3
L3  Domain Specialists (Agent Types) — compras · financeiro · clientes · agenda · docs
L2  Skills — unidades de trabalho (prompt + tools), stateless
L1  Tools (Tool Pool API) — execute_sql · executar_rag · google_calendar · OCR …
```

Agentes são stateless. Toda memória de negócio fica em Supabase.
Agentes NÃO conversam diretamente — escrevem/leem shared memory.

---

## Documentação viva — onde fica o quê

| Arquivo | O que contém |
|---|---|
| `docs/README.md` | Índice de todos os docs ativos |
| `docs/platform_description.md` | Visão geral, stack, arquitetura, estado atual |
| `docs/agent_system_map.md` | Mapa completo: agentes, skills, routines, tools, roadmap |
| `docs/FEATURE_MAP.md` | Tier → Features → Agents + Tools (matriz completa) |
| `docs/TOOL_INVENTORY.md` | Auditoria de todas as 42+ tools registradas por tier/domínio |
| `docs/onboarding-context-map.md` | Fluxo de onboarding, provisionamento de tenant |
| `docs/routines/rotinas_fluxo_e_dependencias.md` | Fluxo técnico de rotinas, step types, catálogo, triggers |
| `docs/blu_app/blu_app concept.md` | Filosofia do produto: salas, HITL, memória, integrações |
| `docs/observability/README.md` | Traces, métricas, Grafana |

### Backlog e ideias futuras

| Arquivo | O que contém |
|---|---|
| `docs/BACKLOG_IDEAS.md` | **Ideias capturadas durante o dev** — não são tarefas confirmadas. Sempre registrar aqui antes de esquecer. |
| `docs/archive/Blu_Routines_MVP_Backlog.md` | Backlog MVP de rotinas — 42 histórias em 7 épicos. Referência principal para o trabalho em rotinas. |
| `docs/archive/Blu_Routines_Skills_Plan.md` | Plano de skills das rotinas (L3 Langfuse prompts) |
| `docs/archive/Blu_Routines.md` | Catálogo original de rotinas v2.1 (26 rotinas com triggers/steps/agentes) |

---

## Estado atual do desenvolvimento (atualizar sempre)

### Infraestrutura de rotinas — o que existe
- Engine de execução: `services/agent_api/src/agent_api/core/routines.py`
- Fetch functions: `routine_functions.py` (11 funções existentes)
- Artefatos: `routine_artifacts.py` | Triggers: `routine_triggers.py`
- pg_cron: sweep 1x/min, 3 jobs ativos (dispatch, process, monthly_close)
- 10 rotinas seedadas em `cross_agent_routines`
- HITL: `libs/blu_hitl_service/` — Redis sorted sets
- Config UI: `RoutineConfigSection.tsx` — toggle, cron picker, config_schema pills

### Gaps ainda abertos (MVP de rotinas)
| ID | O que falta | Prio |
|---|---|---|
| INF-01 | Per-tenant cron dispatcher (avaliar trigger_config.expression por cliente) | P0 |
| INF-02 | on_complete event hook no engine (~20 linhas em routines.py) | P0 |
| INF-03 | Evento sale_approved (trigger AFTER UPDATE em approval_requests) | P1 |
| INF-04 | Pluggy/Polp webhook receiver + merchant logo_url | P1 |
| INF-05 | Google Calendar webhook receiver (padrão OAuth já existente) | P1 |
| INF-06 | Migration: nps_score em dim_clientes + estoque_minimo em dim_inventory | P1 |
| INF-07 | SchemaField tipo dict no front (para config de concorrentes) | P2 |

### Fetch functions faltando para as rotinas MVP
get_cash_position, get_recent_transactions, evaluate_cash_alert,
get_overdue_customers, get_client_pipeline, get_inventory_alerts,
get_supplier_orders, get_sales_performance, get_upcoming_meetings,
get_meeting_participant_context, crawl_competitor_pages, get_nps_data

### Skills L3 faltando (Langfuse prompts, aguardam definição de agentes)
morning_plan, daily_digest, weekly_summary, collection_message,
followup_draft, reactivation_proposal, meeting_brief,
hidden_patterns, competitor_analysis, satisfaction_survey

---

## Decisões de arquitetura firmadas

- Agentes NÃO divididos por domínio. Divisão pendente (mapear skills primeiro).
- Prompts: sempre type=skill (nunca type=llm). Langfuse + fallback em templates.py.
- Análise de Concorrência: usa crawl4ai já presente no repo.
- NPS: campo em dim_clientes (nps_score, nps_data_coletada, nps_detalhes), não tabela separada.
- Polp webhook: incluir imagens de log (merchant logo_url) da API.
- Built-in routines: config de hora (diárias), dia da semana (semanais), dia do mês (mensais).
- Agente RFQ: redesenho radical — fluxo em 3 passos, sem geração de PDF. Output em cards.
- Tier enforcement: tier controla Features, não tools diretamente. ResourceResolver faz interseção.
- "revisar" = cleanup ativo (remove dead code, duplicação, centraliza lógica). Não é relatório.

---

## Convenções do repo

- Docs em inglês; seções de decisão/filosofia podem ser PT-BR.
- Sempre auditar DB live antes de qualquer migration.
- Docker --no-cache quando patches não chegam ao container.
- Hermes skills do Blu: `blu-skills-development`, `blu-workflow-design`, `blu-prompt-engineering`.
- Long planning artifacts: entregar no chat, não em arquivo (para evitar stalls de write_file).

---

## Próximos passos pendentes (última discussão)

1. Definir divisão de agentes (APÓS mapear skills L3 para entender quantos precisam)
2. Implementar EPIC-0 Infra (INF-01 e INF-02 primeiro — P0)
3. Morning Chain (EPIC-1) como primeiro validador end-to-end
4. Tier Enforcement & Resource Assignment redesign (PRIMEIRA PRIORIDADE FUTURA — ver BACKLOG_IDEAS.md)
