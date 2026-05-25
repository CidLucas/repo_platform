# Backlog de Ideias — Blu Platform

Arquivo de captura de ideias para exploração futura. Não são tarefas confirmadas — são direções que valem ser exploradas quando o momento for certo.

Atualizado continuamente durante o desenvolvimento.

---

## Tier Enforcement & Resource Assignment — PRIMEIRA PRIORIDADE FUTURA


## Agente RFQ — Simplificação radical

**Problema:** agente atual está desenhado de forma burocrática (geração de documento PDF/formal), inadequado para PMEs brasileiras.

**Visão correta:** fluxo simples em 3 passos:
1. Recebe uma lista de compras (itens + quantidades)
2. Compara com fornecedores cadastrados e cotas disponíveis
3. Retorna resultado em cards — cotações por fornecedor ou sugestões ranqueadas

**Princípios:**
- Sem geração de documento — se o usuário precisar de um documento formal, usa o agente de documentos
- Output em cards, não em PDF/texto longo
- Leve, rápido, conversacional

**Problema identificado durante testes de routing (Layer 1):**
A atribuição de tools aos agentes está errada. Hoje o tier do cliente filtra tools diretamente
(`TierValidator` em `factory.py`) — mas tools não são a unidade certa de controle.

**Modelo correto (a implementar):**

```
Tier do cliente
  → define quais Features estão habilitadas (ex: "sql_analytics", "crm_advanced", "fiscal")
    → cada Feature seleciona um conjunto de Resources (agents, skills, tools, data sources)
      → esses Resources são atribuídos dinamicamente ao agente no build-time
```

**O que mapear antes de implementar:**
1. Inventário de todos os agents + tools + skills existentes
2. Agrupamento em Features lógicas (ex: Feature "Compras" = ComprasMonitor + supplier-agent + tools de estoque)
3. Mapa Tier → Features habilitadas (FREE / BASIC / SME / PREMIUM / ENTERPRISE)
4. Como o AgentBuilder recebe a lista de resources no build-time (hoje recebe `enabled_tools: list[str]` hard-coded)

**Arquivos centrais para o redesign:**
- `libs/blu_tool_registry/src/blu_tool_registry/tier_validator.py` — lógica atual de tier filtering
- `libs/blu_tool_registry/src/blu_tool_registry/tool_metadata.py` — TierLevel enum
- `services/agent_api/src/agent_api/core/factory.py` — onde tools são filtradas por tier no build
- `libs/blu_agent_framework/src/blu_agent_framework/registry.py` — AgentTypeRegistry com enabled_tools por agente

---

## Arquitetura & Infra

### Shared Memory com pgvector
**Status:** não implementado — `dimension_state` é o substituto atual (1 row por dimensão, upsert simples)

**Ideia original:**
Substituir ou complementar o `dimension_state` com uma tabela `shared_business_memory` que suporte múltiplos blocos por dimensão, com TTL por tipo de bloco e busca semântica via embedding.

Schema proposto:
```sql
CREATE TABLE shared_business_memory (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id       uuid NOT NULL REFERENCES clients(client_id),
  dimension       text NOT NULL,   -- 'compras' | 'financeiro' | 'clientes' | 'agenda' | 'biblioteca' | 'cross'
  block_type      text NOT NULL,   -- 'state' | 'alert' | 'insight' | 'goal' | 'decision'
  summary         text NOT NULL,   -- texto compacto legível por LLM (max ~300 tokens)
  structured_data jsonb,
  source_routine  text,
  valid_until     timestamptz,     -- state: 24h | insights: 7d
  created_at      timestamptz DEFAULT now(),
  embedding       vector(1536)
);
```

Tipos de bloco: `state` (snapshot atual) | `alert` (atenção ativa) | `insight` (padrão observado) | `goal` (meta com progresso) | `decision` (pendente de aprovação).

Função `get_business_memory_snapshot(client_id, max_tokens=1500)`: retorna os blocos mais recentes ordenados por prioridade (alerts → goals → state → insights), respeitando TTL, com teto de ~1500 tokens (~6 blocos de 250 tokens).

**Quando explorar:** quando o `dimension_state` atual começar a ser insuficiente para casos de uso com múltiplos alertas simultâneos ou quando o Synthesis Agent precisar de contexto vetorial.

---

## i18n — App Multi-idioma

**Ideia:** tornar o Blu disponível em múltiplos idiomas (PT-BR, EN, ES como prioridade).

**Abordagem técnica proposta:**
- Todo o código, prompts internos, nomes de tools, descriptions e registry ficam em inglês (já é o padrão definido)
- O conteúdo dos prompts (o que o LLM lê) é internacionalizado
- Adicionar um nó dedicado no LangGraph de resposta: `response_language_node` que detecta o idioma do usuário (via `user_language` no perfil ou detecção automática da mensagem) e formata/traduz a resposta final antes de entregar
- Alternativa mais simples: injetar `user_language` como variável nos prompts e instruir o agente a responder naquele idioma (já fazemos `Responda sempre no idioma do usuário` nos prompts novos)

**Quando explorar:** após estabilização dos agentes principais (Fase 2-3 completas).

---

## Integrações Externas

### NotebookLM — Bases de Conhecimento por Tarefa
**Ideia:** integrar o Hermes/Blu com o NotebookLM para gerar bases de conhecimento especializadas por domínio (ex: base financeira para o FinanceiroMonitor, base de clientes para o CRM Specialist).

Fluxo proposto:
1. Alimentar o NotebookLM com documentos, relatórios e histórico de cada dimensão do negócio do cliente
2. Usar o podcast/summary gerado como contexto enriquecido para os agentes
3. Ou usar o NotebookLM como ferramenta de RAG alternativa ao pgvector para casos de conhecimento mais narrativo

**Quando explorar:** próximo horizonte — útil para onboarding de novos clientes onde a base de documentos é rica.

### GitHub Cloud — Fluxo de Desenvolvimento Automatizado
**Ideia:** integrar o Hermes com o GitHub Cloud (Actions, Issues, PRs) para criar um fluxo de desenvolvimento automatizado:
- Criar issues a partir de conversas de backlog
- Abrir PRs com código gerado via Codex/Claude Code
- Receber notificações de CI/CD e agir sobre falhas
- Vincular tarefas do Linear/Asana a commits e PRs automaticamente

**Quando explorar:** próximo horizonte — desbloquearia um loop completo de desenvolvimento assistido por IA.

---

## Padrões & Convenções

### Prompt Standards (definido em 21/05/2026)
- Nomes de prompts, descriptions, tool names e campos de registry: **inglês**
- Conteúdo dos prompts (o que o LLM lê): **português** (por enquanto — mudará com i18n)
- Prompts existentes NÃO serão migrados em massa — revisão gradual
- Todos os agentes novos seguem o padrão com seções: `<Instructions>`, `<Tool Rules>`, `<Constraints>`, `<Output Format>`

---

*Última atualização: 21/05/2026*

---
## MVP Roadmap — registrado 2026-05-21

### Fase atual (em andamento)
- Estabilizar infra dos agentes: eliminar 500s, routing correto, model names, CancelledError

### Próximas fases (em ordem)

**1. Limpeza de dados**
- Criar função no BD: ao deletar cliente, deletar todos os dados associados (cascade completo)
- Deletar clientes existentes na base e validar que nada fica órfão

**2. Onboarding — ciclo completo (2 clientes)**
- Cliente A: fonte BigQuery
- Cliente B: fonte Google Sheets
- Validar todo o fluxo de entrada de dados para cada fonte

**3. Validação de métricas**
- Pegar todas as métricas elencadas no frontend
- Validar geração correta de cada uma

**4. Integrações**
- Monday
- Slack
- Google Drive, Gmail, Google Agenda
- Open Finance

**5. Mesa de trabalho da Agenda**
- Hoje hardcoded/figurativa
- Tornar dinâmica e funcional

### Pós-MVP (quando produto estiver pronto para receber clientes)
- Otimizar fluxos dos agentes
- Otimizar retrieval (chunking, metadata, estrutura da base)
- Refinamento contínuo de prompts e routing

---
## Pós-MVP — Routing de Agentes (prioridade alta no ciclo de otimização)

**Problema atual:** routing baseado em exact match de nuvem de palavras (_PLATFORM_KEYWORDS, _SPECIALIST_ROUTING, _SYNTHESIS_KEYWORDS) — frágil, não generaliza.

**O que precisa:**
- Estratégia mais sofisticada: embedding similarity, classificador leve, ou LLM call dedicado ao routing
- Exemplos que falham hoje: "Ativa o monitor de estoque baixo", "Agenda uma reunião para quinta", "Quais clientes têm maior risco de churn?" — todos caem no frontdesk por não terem exatamente a keyword certa
- Considerar: classificador treinado com exemplos por agente, ou zero-shot com modelo FAST dedicado ao routing intent
- Timing: pós-onboarding, no ciclo de otimização dos agentes

---

## Métricas placeholder/hardcoded no Frontend (levantamento Mai-2026)

### 🔴 CRÍTICO — Dados disponíveis, só falta ligar ao frontend

**BKL-01 — FinanceiroRoom: custo_total e fluxo_caixa não exibidos**
- `get_finance_indicators` já retorna `custo_total`, `burn_rate_mensal`, `cash_flow_30d` (Fase 3)
- Campos ignorados no destructuring — nunca chegam ao JSX
- **Resolvido como quick win (Mai-2026):** campos adicionados ao card principal e analytics expandido

**BKL-02 — HomePage: widget de semanas com `'—'` hardcoded**
- `HomePage.tsx:482–483` — semanas futuras hardcoded com descrição e contagem `'—'`
- Substituir por contagem real de `approval_requests` agrupadas por semana
- Esforço: 2h

**BKL-03 — ComprasRoom: `lead_time_medio_dias` e `otif_perc` sempre `'—'`**
- OTIF requer `promised_delivery_at` em `approval_requests` (não existe)
- Lead time calculável: `AVG(decided_at - created_at)` das aprovações de compra
- Esforço: 3h — migration + atualizar `get_supply_indicators`

**BKL-04 — AdminScreen: "Economia gerada" e "Anomalias" placeholder**
- `AdminScreen.tsx:572–573` — dois cards explicitamente `'—' em breve`
- Anomalias = COUNT de `client_insights` com severity='error' — trivial
- Economia = diferença custo_total atual vs. período anterior (decisão de definição pendente)
- **Anomalias resolvido como quick win (Mai-2026)**

**BKL-05 — ClientesRoom: `crescimento_receita_pct` não exibido**
- `get_commercial_indicators` retorna o campo mas o card não o renderiza
- **Resolvido como quick win (Mai-2026):** badge de variação adicionado ao card de Receita

### 🟡 IMPORTANTE — Dados parcialmente disponíveis

**BKL-06 — FinanceiroRoom: `dso_dias`, `dpo_dias`, `ccc_dias`, `working_capital_ratio` sempre NULL**
- Requerem tabelas de contas a pagar/receber (ausentes no schema)
- Alternativa: `dso` ≈ AVG(dias entre emissão e pagamento) de approval_requests
- Bloqueio real: ausência de `due_date` em transações
- Esforço: 4h para versão aproximada

**BKL-07 — AtividadeScreen: NPS sempre `'—'`**
- `getNpsScore()` chama RPC `analytics_v2.get_nps_score` que não existe no DB
- Criar função que lê de `client_insights` com kpi='nps' ou retorna NULL se sem dados
- Esforço: 2h

**BKL-08 — ComprasRoom: `concentracao_top_perc` calculado mas não exibido**
- `get_supply_indicators` já calcula e retorna o campo
- Frontend não renderiza em nenhum card
- **Resolvido como quick win (Mai-2026):** campo adicionado ao analytics card de Compras

**BKL-09 — EstrategiaRoom: sem KPIs próprios, depende 100% de context_metrics**
- Nenhuma chamada a indicadores estruturados — usa só `getContextMetrics` filtrado por dimension='estrategia'
- Criar `get_strategy_summary()`: crescimento receita YoY, projeção de meta, market share
- Esforço: 5h

### 🟠 MÉDIO — Hardcoded estrutural

**BKL-10 — AgendaRoom Gantt: 100% hardcoded com datas de Maio fixas**
- `AgendaRoom.tsx:140–170` — cabeçalho e blocos de tasks string literals com posições em %
- RPC necessário: `{domain, title, start_date, due_date, status}` agregando approval_requests + client_routines (next_run) + Google Calendar
- Parte da **Fase 5** do plano de validação
- Esforço: 8h

**BKL-11 — get_marketing_indicators: função existe mas nunca usada em nenhum room**
- Existe em `pg_proc` e `useAnalytics.ts` mas nenhum room chama
- Integrar ao EstrategiaRoom ou criar MarketingRoom futuro
- Esforço: 3h

### 🔵 BAIXO — Requer dados estruturais ausentes

**BKL-12 — ComprasRoom: `cost_savings_perc` e `ppv` sempre NULL**
- Requerem `preco_referencia` por produto/fornecedor em `dim_inventory`
- Bloqueado por ausência de catálogo de produtos com preços históricos

**BKL-13 — FinanceiroRoom: EBITDA, CAC, inadimplência**
- EBITDA: requer separação OPEX vs. COGS (sem categorização de despesas hoje)
- CAC: sem dados de custo de aquisição
- Inadimplência: sem tabela `contas_receber`
- Bloqueado por dados estruturais ausentes

**BKL-14 — Refresh periódico de Google Sheets como integração**
- `enqueue_incremental_syncs` só cobre BigQuery; Sheets é one-shot no onboarding
- Função separada: verificar `drive_modified_time` como watermark → `upload-drive-source` → `run-csv-etl`
- Parte da **Fase 2** pendente
- Esforço: 4h

**BKL-15 — AdminScreen: "Economia gerada" (definição pendente)**
- Depende de decisão: diferença custo_total atual vs. anterior, ou comparação com valor_referencia em approval_requests

---

## BKL-16 — Produção: Anti-entupimento de processos e hardening operacional

Capturado em: Mai-2026. Motivação: identificamos que execuções de rotinas ficam em `dispatched` indefinidamente quando o agent_api não chega a processar (pg_cron aponta para URL interna, sem timeout, sem watchdog).

### Problema em 3 camadas

**Camada 1 — Pooler / Supabase**
- Connections longas em `transaction mode` travam slot por minutos se a query não tem timeout
- pg_net.http_post sem timeout: request fica pendurada se agent_api estiver lento
- client_routine_executions ficam em `dispatched` para sempre se o consumer morrer

**Camada 2 — Agent API (FastAPI + LangGraph)**
- Agente pode entrar em loop infinito de tool calls sem `max_iterations`
- LLM call sem timeout → request prende worker uvicorn indefinidamente
- Nenhum circuit breaker por cliente: cliente com dados ruins pode prender o worker enquanto outros esperam

**Camada 3 — State machine de rotinas**
- Sem TTL em `client_routine_executions`: `dispatched` nunca vira `failed` automaticamente
- Sem limite de retry: uma rotina quebrada nunca para de tentar
- `claim_routine_executions` sem liveness check: execução claimed por pod morto nunca é liberada

---

### Solução profissional — camada por camada

#### DB / Pooler
1. **Statement timeout global** — `ALTER ROLE service_role SET statement_timeout = '120s'` — qualquer query pesada além de 2min é killed automaticamente
2. **pg_net timeout** — `net.http_post(..., timeout_milliseconds => 30000)` — configurar em `dispatch_routine_executions` para não ficar pendurado aguardando agent_api morto
3. **Stale execution reaper** — pg_cron job `*/5 * * * *` que faz:
   ```sql
   UPDATE client_routine_executions
   SET status = 'failed', error = 'timeout: no heartbeat for 10min'
   WHERE status = 'dispatched'
     AND dispatched_at < now() - interval '10 minutes';
   ```
4. **Índice parcial** em `client_routine_executions(status, dispatched_at) WHERE status = 'dispatched'` para o reaper ser rápido
5. **Lock advisor por cliente** — `pg_try_advisory_xact_lock(hashtext(client_id))` no início do claim para evitar double-claim entre pods

#### Agent API
1. **`max_iterations` no LangGraph** — toda invocação de grafo com `recursion_limit=25` (LangGraph default é 25, mas verificar se está sendo passado)
2. **LLM timeout** — `httpx.Timeout(30.0)` no client do model provider, não depender do timeout do provider
3. **Task timeout por request** — `asyncio.wait_for(run_agent(...), timeout=90)` no router; retornar 408 para o chamador, marcar execution como `failed`
4. **Semaphore por cliente** — `asyncio.Semaphore(2)` por `client_id` para evitar que um cliente mal-comportado ocupe todos os workers
5. **Heartbeat de execução** — agente faz UPDATE em `client_routine_executions.heartbeat_at = now()` a cada step do grafo; reaper usa `heartbeat_at` em vez de `dispatched_at`
6. **Circuit breaker por rotina** — após N falhas consecutivas na mesma `routine_id` + `client_id`, marcar `status='suspended'` e alertar via notificação

#### State machine de rotinas
1. **Status explícito `suspended`** — além de `active/failed/completed`: indica que a rotina parou de tentar por excesso de falhas (requer intervenção manual ou reset automático)
2. **`max_retries` em `cross_agent_routines.trigger_config`** — ex: `{"max_retries": 3, "backoff": "exponential"}` — engine respeita e incrementa `retry_count` em `client_routines`
3. **`execution_timeout_s` por rotina** — field em `cross_agent_routines` que o dispatcher passa no header; agent_api usa como `asyncio.wait_for` timeout
4. **Claim com worker_id** — `claimed_by uuid DEFAULT NULL` em `client_routine_executions` — ao claim, setar `claimed_by = pod_id`; reaper ignora execuções com `claimed_by` de pod vivo (via tabela `agent_pods` com heartbeat)

#### Observability (pré-requisito para tudo acima)
1. **Prometheus metrics no FastAPI** — `starlette-exporter` ou `prometheus-fastapi-instrumentator`: latência p99, taxa de erro, fila de execuções, workers ativos
2. **Alertas Grafana** — rotina em `dispatched` há mais de 10min → alert; error rate > 5% → alert; pool de conexões > 80% → alert
3. **Tracing distributed** — OpenTelemetry + Langfuse já parcialmente configurado; adicionar `trace_id` em `client_routine_executions` para correlacionar log do DB com log do agente
4. **Dead Letter Queue** — execuções que falharam 3x vão para tabela `routine_dlq` com payload completo para debug manual

#### Infra / deploy
1. **Readiness probe no agent_api** — `/health` já existe; configurar no Cloud Run/k8s para não rotear para pod não-pronto
2. **Graceful shutdown** — `SIGTERM` handler que para de aceitar novos claims mas termina execuções em andamento (máx 30s), depois `sys.exit(0)`
3. **Horizontal scaling com claim atomico** — múltiplos pods competem pelo mesmo `claim_routine_executions()` via `SELECT ... FOR UPDATE SKIP LOCKED` (verificar se já está assim)
4. **Separação de filas por prioridade** — rotinas `trigger_type=event` (ex: onboarding_complete) têm prioridade sobre `trigger_type=cron`; implementar com `priority int` na fila de claim

### Ordem de implementação sugerida (quando for hardening)

| Prio | Item | Impacto | Esforço |
|---|---|---|---|
| P0 | Stale execution reaper (pg_cron 5min) | Para entupimento imediato | 1h |
| P0 | `asyncio.wait_for` timeout no router | Para travamento de workers | 1h |
| P0 | `pg_net timeout_milliseconds` no dispatch | Para pg_cron sem resposta | 30min |
| P1 | Heartbeat de execução | Reaper mais preciso | 3h |
| P1 | `max_iterations` explícito no LangGraph | Evita loop infinito | 30min |
| P1 | Circuit breaker por rotina (N falhas → suspended) | Evita retry storm | 4h |
| P1 | Semaphore por cliente no agent_api | Fair use entre clientes | 2h |
| P2 | Claim com worker_id + pod liveness | Claim resiliente a crashes | 1 dia |
| P2 | Prometheus + Grafana alerts | Visibilidade operacional | 1 dia |
| P2 | Dead Letter Queue | Debug pós-falha | 3h |
| P3 | Priority queue (event > cron) | UX mais responsiva | 1 dia |
| P3 | OpenTelemetry end-to-end | Tracing distribuído completo | 2 dias |
- Esforço: 2h após definição
