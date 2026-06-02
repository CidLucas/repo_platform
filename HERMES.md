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

### ⭐ System Reference — consultar SEMPRE primeiro

> **Pasta:** `docs/system_reference/` — fonte de verdade única do sistema de agentes.
> Agentes devem sempre procurar aqui antes de qualquer decisão sobre capacidades, skills e rotinas.

| Arquivo | O que contém |
|---|---|
| **`docs/system_reference/AGENT_SYSTEM.md`** | **12 agentes: papéis, hierarquia, roteamento, decisões de arquitetura** |
| **`docs/system_reference/SKILLS_SYSTEM.md`** | **Catálogo completo de skills: tools, agentes consumidores, governance** |
| `docs/system_reference/FEATURE_MAP.md` | Tier → Features → Agents + Tools (matriz completa) |
| `docs/system_reference/TOOL_INVENTORY.md` | Auditoria de todas as tools registradas por tier/domínio |
| `docs/system_reference/ROUTINES_SYSTEM.md` | Fluxo técnico de rotinas: pg_cron → steps (function/skill/artifact/approval) |
| `docs/system_reference/TASK_PLAYBOOKS.md` | Receitas de dev: como adicionar rotina, skill, tool, integração |

### Referências complementares

| Arquivo | O que contém |
|---|---|
| `docs/README.md` | Índice de todos os docs ativos |
| `docs/onboarding-context-map.md` | Fluxo de onboarding, provisionamento de tenant |
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
- **agenda → scheduler-agent** (2026-05-29): o agente `agenda` planejado em `agents_and_skills.md` (22/05) nunca foi criado. Suas responsabilidades foram absorvidas pelo `scheduler-agent` (slug diferente, mesmo papel: calendário, follow-ups, disponibilidade, reuniões). A skill `agenda` existe (slug: agenda, prompt: skill:agenda:system) e fica em `scheduler-agent.skill_slugs`. Não criar slug `agenda` como agente separado.
- **Binding agente↔skill via skill_slugs** (2026-05-29): o plano original usava tag-intersection (gerava over-match — context-gatherer e platform pegavam todas as 16 L3 skills via tag `routines`). Migrado para `skill_slugs=[ ]` explícito no registry. Não regredir para tag-intersection.
- **context-gatherer usa fragments, não prompt_name** (2026-05-29): prompt montado dinamicamente a partir de 6 fragments Langfuse (`fragment/context-gatherer-base`, `fragment/transaction-extraction-rules`, `fragment/schema-mapping-workflow`, `fragment/routine-definition-workflow`, `fragment/knowledge-curation-workflow`, `fragment/confirmation-patterns`). Não existe `agents/context-gatherer` no Langfuse.

## Política de sessão (agente)

Ao **encerrar cada sessão** de trabalho no repo:
1. Atualizar a seção "Estado atual do desenvolvimento" e "Gaps abertos" neste arquivo se algo mudou.
2. Atualizar o README da pasta/lib que foi tocada nessa sessão.
3. Registrar ideias futuras em `docs/BACKLOG_IDEAS.md` antes de fechar.

Não reescrever o HERMES.md inteiro — atualizar apenas as seções dinâmicas (estado, gaps, próximos passos).

---

## Recursos de design (open-design/)

Pasta local com skills de design HTML/CSS — não commitada (`.gitignore`).
Caminho: `open-design/skills/`

Skills úteis disponíveis:
- `html-ppt/` — apresentações HTML interativas (35+ temas, 20+ animações, layouts)
- `web-prototype/` — protótipos web, wireframes, landing pages SaaS
- `mobile-app/` / `mobile-onboarding/` — simulações de UI mobile
- `dashboard/` — dashboards HTML com charts
- `hyperframes/` — vídeos/frames animados com paletas e transições
- `kami-landing/` / `kami-deck/` — landing pages e decks com sistema próprio
- `invoice/` / `finance-report/` — documentos financeiros HTML
- `wireframe-sketch/` — wireframes rápidos
- `simple-deck/`, `replit-deck/`, `guizang-ppt/` — decks alternativos

Para qualquer tarefa de interface/design/apresentação: verificar `open-design/skills/` antes de criar do zero.

---

## Scripts utilitários

Documentados em `scripts/README.md`. Scripts ativos:

| Script | Propósito |
|---|---|
| `audit_langfuse_prompts.py` | Auditoria de prompts no Langfuse |
| `create_analytics_prompts.py` | Setup de prompts de analytics |
| `create_rfq_prompts.py` | Setup de prompts de RFQ |
| `seed_google_oauth_vault.py` | Seed de credenciais OAuth Google |
| `seed_platform_knowledge.py` | Seed de knowledge base |
| `seed_test_suppliers.py` | Seed de fornecedores de teste |
| `bq_export.py` | Export BigQuery |
| `check_analytics_views.sh` | Verificação de views analytics |
| `generate_agent_docs.py` | Geração de docs de agentes |

> Migrações de schema ficam em `supabase/migrations/` — Alembic foi removido.

---

## READMEs de referência por subsistema

| README | O que cobre |
|---|---|
| `scripts/README.md` | Scripts utilitários: seeding, Langfuse, analytics, docs |
| `docs/README.md` | Índice de toda documentação viva |
| `docs/observability/README.md` | Traces, métricas, Grafana |

---



- Docs em inglês; seções de decisão/filosofia podem ser PT-BR.
- Sempre auditar DB live antes de qualquer migration.
- Docker --no-cache quando patches não chegam ao container.
- Hermes skills do Blu: `blu-skills-development`, `blu-workflow-design`, `blu-prompt-engineering`.
- Long planning artifacts: entregar no chat, não em arquivo (para evitar stalls de write_file).

---

## Plano de validação da plataforma (sessões 20/21-Mai-2026)

### Fase 1 — CASCADE DELETE + limpeza de dados ✅ COMPLETA
- FK cascade em bigquery_foreign_tables e standalone_agent_sessions corrigidas
- Trigger trg_drop_bigquery_fdw_server remove FDW server ao deletar cliente
- enqueue_incremental_syncs() + pg_cron 02:00/14:00 UTC
- run_etl_job() classifica tipo_transacao (cascata: mapeamento → CPF/CNPJ → join dimensional)
- 5 migrations aplicadas: 20260521001000 a 20260521001400

### Fase 2 — Onboarding ✅ PARCIALMENTE COMPLETA
- Campo CPF/CNPJ adicionado: useOnboardingDraft, StepInfo, mappers.ts, index.ts, RPC bootstrap
- O onboarding blu_v3 estava ~95% funcional — mapeado e documentado

Ainda falta (Fase 2):
- Validação ponta-a-ponta com BigQuery real e Google Sheets (manual, a fazer)
- Refresh periódico de Google Sheets (drive_modified_time como watermark)
- onboarding-website-intel retornar CNPJ

### Fase 3 — KPI functions por tipo_transacao ✅ COMPLETA (21-Mai-2026)
- get_finance_indicators: receita_liquida (vendas), custo_total (compras), margem_bruta, burn_rate, cash_flow_30d
- get_commercial_indicators: filtrado por tipo_transacao='venda', inclui churn_60d, séries mensais, clientes novos/recorrentes
- get_supply_indicators: spend_periodo filtrado por tipo_transacao='compra'
- get_kpi_mtd_comparison(): nova função — 4 KPIs MTD vs. mês anterior (receita, custo, margem, fluxo_caixa)
- Migration: 20260521002000_kpi_functions_tipo_transacao.sql

Ainda falta (Fase 3):
- Conectar get_kpi_mtd_comparison ao frontend (cards de KPI do painel principal)
- Implementar ebitda, cac, inadimplencia (requerem dados adicionais)

### Fase 4 — Integrações ✅ PARCIALMENTE COMPLETA (21-Mai-2026)

Implementado:
- Wiring Slack/Monday: edge function `save-api-token` (deployed) + UI modal com input de token + admin.ts sintetiza integration_tokens como 'connected'. Backend (slack_module, monday_module) já lia integration_tokens — agora o ciclo está fechado.

Ainda falta:
- Refresh periódico Google Sheets como integração (não one-shot)
- Teste ponta-a-ponta: agente executando comando real via Slack/Monday token salvo

### Open Finance (Polp) — ✅ JÁ IMPLEMENTADO (não é pós-MVP)

A integração Polp é completa e rica, não é "do zero / pós-MVP" como estava documentado erroneamente.

O que existe hoje:
- `polp-connect` — edge function que inicia a conexão via Polp API, retorna `url_to_authenticate`
- `polp-webhook` — recebe eventos em tempo real: `integrations.updated`, `accounts.updated`, `accounts.synchronized`, `transactions.created/updated/deleted`, `bills.created/updated`
- `polp-sync` — sync manual: contas + transações + faturas de cartão (CREDIT accounts)
- 4 tabelas: `polp_integrations`, `polp_accounts`, `polp_transactions`, `polp_bills`
- `polp_bills` contém vencimento, valor total, pagamento mínimo, parcelamentos — ou seja, **contas a pagar via cartão já existem**
- `polp_transactions` contém description, amount, type, category, merchant, payment_data — base para fluxo de caixa real

O que ainda falta na Polp:
- ETL que lê `polp_transactions` e insere em `fato_transacoes` (para unificar com dados de CSV/BigQuery no mesmo pipeline de KPIs)
- Métricas de fluxo de caixa bancário usando `polp_accounts.balance` diretamente (sem ETL)
- `merchant logo_url` no webhook (INF-04) — cosmético

### Fase 5 — Agenda dinâmica ✅ COMPLETA (21-Mai-2026)

- `public.get_unified_tasks(p_client_id)` — UNION ALL de approval_requests (pending) + client_routines (is_active + next_run_at), domain inferido por nome/agent_slug
- `fetchUnifiedTasks()` + `UnifiedTask` interface em agenda.ts
- Gantt substituído: janela de 4 semanas a partir da segunda-feira atual, barras posicionadas por start_date/due_date, linha "hoje" dinâmica, cores por domínio, fallback "sem tarefas" por linha

### Open Finance (Polp) ETL ✅ COMPLETO (21-Mai-2026)

- `analytics_v2.sync_polp_transactions(p_client_id)` — upsert polp_transactions → fato_transacoes; CREDIT='venda', DEBIT='compra', tipo_lancamento='bancario'
- `analytics_v2.enqueue_polp_sync()` — loop sobre todos clientes com polp_integrations ativo
- pg_cron 'polp_sync_to_fato_6h' a cada 6h — 137 linhas sincronizadas no primeiro run
- ON CONFLICT preserva tipo_transacao e categoria já classificados (não sobrescreve)

### Gantt com fontes externas ✅ COMPLETO (21-Mai-2026)

- Edge function `get-agenda-events` (deployed, 133kB) — Google Calendar + Monday + Notion em paralelo via Promise.allSettled
- Token único lookup em integration_tokens WHERE provider IN ('google','monday','notion')
- `inferDomain()` classifica eventos por palavras-chave — mesmo vocabulário do Gantt
- Fix provider mismatch: AdminScreen.tsx usava 'ic-monday'/'ic-notion' → corrigido para 'monday'/'notion'
- frontend: fetchExternalAgendaEvents() + 7ª query no AgendaRoom + merge com unifiedTasks por domínio

### Fixes pós-validação (22-Mai-2026)

- `get_unified_tasks`: corrigida ambiguidade `title` (alias ar.title), `is_active`→`active`, `next_run_at` removido, JOIN cross_agent_routines para nome do catálogo — migration 20260522000100
- `onboarding_bootstrap_tx`: ON CONFLICT em client_routines agora reseta `active=true, status='active'` — rotinas nunca ficam presas como inactive após re-onboarding — migration 20260522000300
- AgendaRoom CTAs: consultam useIntegrations, mostram "✓" quando conectado, onClick usa goWithTab('admin','Admin','integracoes') em vez de window.location.href
- AdminScreen: lê initialTab da store no mount para abrir tab correta
- Rotinas do cliente de teste reativadas manualmente + onboarding_complete re-disparado (migration 20260522000200)

---

## Audit de validação — 21-Mai-2026

### DB ✅ PASS total
- 5 migrations aplicadas (20260521191013 a 20260521192850)
- FKs: bigquery_foreign_tables CASCADE, standalone_agent_sessions SET NULL ✅
- Trigger trg_drop_bigquery_fdw_server ✅
- 8 pg_cron jobs ativos (enqueue_incremental_syncs_12h, polp_sync_to_fato_6h + 6 existentes)
- 31 funções em analytics_v2 ✅
- get_unified_tasks + onboarding_bootstrap_tx em public ✅
- clientes_blu.cpf_cnpj column ✅
- fato_transacoes bancario: 102 compras + 35 vendas (Polp ETL ok)
- integration_tokens: 1 token Google presente

### Pontos de atenção (não bloqueadores)
- fato_transacoes: 60.552 rows com tipo_lancamento/tipo_transacao NULL — são registros históricos de CSV/BQ sem CPF/CNPJ correspondente nos dims. Normal para dados de teste sem dimensões populadas.
- polp_integrations: 7/9 OUTDATED, 1 UPDATING, 1 UPDATED — sync em andamento, não stalled. Polp marca OUTDATED automaticamente quando detecta novos dados disponíveis.
- pg_cron duplicado: dispatch_routine_executions e dispatch_routine_executions_to_agent chamam a mesma função — inofensivo mas vale limpar depois.

### Frontend ✅ PASS total
- AgendaRoom.tsx: 7 queries, Gantt dinâmico, externalEvents merged ✅
- agenda.ts: UnifiedTask, AgendaExternalEvent, fetchUnifiedTasks, fetchExternalAgendaEvents ✅
- AdminScreen.tsx: provider 'monday'/'notion' corretos, save-api-token wired ✅
- FinanceiroRoom: cash_flow_30d, custo_total ✅
- ClientesRoom: crescimento_receita_perc ✅
- ComprasRoom: concentracao_top_perc ✅

### Edge functions (22 total) ✅
get-agenda-events, save-api-token, google-calendar-events, polp-*, onboarding-*, run-*-etl, process-document, search-documents, upload-*, discover-bigquery-columns, match-columns, generate-context-report, website-context-builder, routine-builder

---

## Próximos passos pendentes

1. Onboarding de clientes de teste + validação ponta-a-ponta (BigQuery real, Sheets, Polp)
2. Revisão front/UX após feedback de uso real
3. Refresh periódico Google Sheets (drive_file_id → re-download → run-csv-etl)
4. Métricas diretas de saldo bancário: polp_accounts.balance como KPI de caixa em tempo real
5. Limpar pg_cron duplicado: dispatch_routine_executions_to_agent
