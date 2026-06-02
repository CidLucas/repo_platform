# Sistema de Rotinas — Referência Técnica

> Documento de referência estrutural. Descreve o funcionamento completo do
> pipeline de rotinas: onde as definições vivem, como são disparadas, como
> executam, onde armazenam outputs e como notificam.
> Não inclui backlog de issues — para isso ver BACKLOG_IDEAS.md.

---

## 1. Visão geral

Rotinas são fluxos automatizados multi-step que rodam em nome de um cliente.
Cada rotina tem uma definição de catálogo (o quê fazer) e uma assinatura por
cliente (quando rodar, com quais configs e para qual canal notificar).

O pipeline completo é:

```
Trigger (cron / numeric / event / manual)
  → dispatch_execution (insere row em client_routine_executions com status=dispatched)
  → pg_cron @ cada minuto → dispatch_routine_executions() [SQL]
      → POST /v1/internal/routines/run-dispatched  [pg_net]
          → check_and_enqueue_triggers()           [Python – avalia novos triggers]
          → claim_dispatched_batch()               [SQL – SELECT ... FOR UPDATE SKIP LOCKED]
          → run_dispatched_executions()            [Python – asyncio.gather por execução]
              → _run_single_execution()            [semáforo + heartbeat + timeout 120s]
                  → _execute_one()                 [engine de steps]
                      step loop: function | skill | llm | artifact | approval
                  → _notify_client()               [app / whatsapp / email]
```

---

## 2. Tabelas de dados

### 2.1 cross_agent_routines — catálogo de rotinas

Definições centrais compartilhadas por todos os clientes.

| Coluna           | Tipo      | Descrição                                                    |
|------------------|-----------|--------------------------------------------------------------|
| id               | text (PK) | Slug da rotina (ex: `financeiro_monitor`)                    |
| name             | text      | Nome legível                                                 |
| steps            | jsonb     | Array de steps (ver seção 4)                                 |
| trigger_type     | text      | `manual` \| `cron` \| `numeric` \| `event`                  |
| trigger_config   | jsonb     | Config do trigger (expression, metric, threshold, etc.)      |
| config_schema    | jsonb     | Array de campos configuráveis por cliente (com defaults)     |
| room             | text      | Sala da interface associada                                  |
| visibility       | text      | `user` \| `internal`                                         |

### 2.2 client_routines — assinaturas por cliente

Cada linha representa um cliente inscrito em uma rotina do catálogo.

| Coluna               | Tipo      | Descrição                                                      |
|----------------------|-----------|----------------------------------------------------------------|
| id                   | uuid (PK) | PK da assinatura                                               |
| client_id            | uuid      | FK → clientes_blu                                              |
| routine_id           | text      | FK → cross_agent_routines.id (ou UUID para rotinas customizadas) |
| active               | bool      | Se a assinatura está ativa                                     |
| status               | text      | `active` \| `suspended` (circuit breaker)                     |
| trigger_type         | text      | Pode sobrescrever o trigger do catálogo                        |
| trigger_config       | jsonb     | Config de trigger por cliente (ex: expression cron customizada)|
| config               | jsonb     | Overrides de config_schema (ex: dias_inactive, threshold)      |
| notify_channel       | text      | `app` \| `whatsapp` \| `email`                                |
| last_run_at          | timestamptz | Timestamp da última execução; usado pelo cron poller        |
| consecutive_failures | int       | Contagem para circuit breaker                                  |
| steps                | jsonb     | Steps customizados (se vazio, usa os do catálogo)              |
| source               | text      | `catalog` \| `ai` (rotinas criadas pela IA)                   |
| created_by_ai        | bool      | Se foi criada autonomamente pela IA                            |

### 2.3 client_routine_executions — log de execuções

Cada linha é uma execução individual de uma rotina para um cliente.

| Coluna          | Tipo      | Descrição                                                          |
|-----------------|-----------|--------------------------------------------------------------------|
| id              | uuid (PK) | ID da execução                                                     |
| client_id       | uuid      | FK → clientes_blu                                                  |
| routine_id      | text      | ID da rotina                                                       |
| triggered_by    | text      | `cron` \| `numeric` \| `event` \| `manual`                        |
| trigger_data    | jsonb     | Dados do trigger (ex: metric, current_value, drop_pct)             |
| status          | text      | `pending` → `dispatched` → `executing` → `completed` \| `failed` \| `awaiting_approval` |
| dispatched_at   | timestamptz | Quando foi enfileirado                                           |
| heartbeat_at    | timestamptz | Atualizado a cada 20s para evitar que o reaper mate a execução  |
| result_text     | text      | Output final consolidado (uma linha por step)                      |
| result_metadata | jsonb     | Estado intermediário checkpointado após cada step                  |
| completed_at    | timestamptz | Quando finalizou                                                 |
| worker_slug     | text      | Último skill/agente que produziu output                            |
| failure_count   | int       | Falhas desta execução (não confundir com consecutive_failures)     |

### 2.4 dimension_state — outputs de análise por dimensão

Armazena o resultado estruturado de rotinas de monitor que escrevem análises.

| Coluna      | Tipo      | Descrição                                           |
|-------------|-----------|-----------------------------------------------------|
| id          | uuid (PK) |                                                     |
| client_id   | uuid      |                                                     |
| dimension   | text      | Nome da dimensão (ex: `financeiro`, `clientes`)     |
| summary     | text      | Texto narrativo do output                           |
| structured  | jsonb     | Dados estruturados extraídos                        |
| valid_until | timestamptz | TTL da análise                                   |
| updated_at  | timestamptz | Última atualização                               |

---

## 3. Triggers

O sistema suporta 4 tipos de trigger. A avaliação de cron e numeric ocorre
dentro de `check_and_enqueue_triggers()`, chamado a cada tick do dispatcher.

### 3.1 cron (agendado)

- `trigger_config.expression` — expressão cron (ex: `0 9 * * 1`)
- O poller lê `last_run_at` da assinatura do cliente e usa `croniter` para
  calcular o próximo disparo
- Primeira ativação: `last_run_at` é nulo → stampa `now()` e pula, o próximo
  intervalo regular dispara normalmente (evita disparo imediato ao ativar)
- O cliente pode sobrescrever a expression em `client_routines.trigger_config`

### 3.2 numeric (monitoramento de métrica)

- `trigger_config.metric` — chave em `_NUMERIC_METRIC_REGISTRY`
- `trigger_config.threshold` — fração do baseline que dispara (ex: `0.85` = queda > 15%)
- `trigger_config.window_months` — janela de comparação histórica (padrão: 1)
- `trigger_config.cooldown_hours` — mínimo entre disparos (padrão: 24h)
- O cliente pode sobrescrever `threshold` e `window_months` via `config`
- Métricas registradas em `_NUMERIC_METRIC_REGISTRY` (validado Jun/2026):
  - `revenue` / `faturamento` — faturamento mensal via RPC `get_revenue_monthly_rate`
  - `new_clients_monthly_rate` — novos clientes via RPC `get_new_clients_monthly_rate`
  - `ticket_medio` — ticket médio via RPC `get_ticket_medio_monthly_rate`
  - `churn_rate` — taxa de churn via RPC `get_churn_rate_monthly`
  - `pedidos_count` — volume de pedidos via RPC `get_pedidos_monthly_rate`
- Lógica: dispara quando `current < threshold * baseline`
  (para churn use `threshold > 1` para detectar spike)
- ⚠️ Rotinas do catálogo que referenciam métricas fora do registry (ex: `cash_flow_alert`
  usa `saldo_conta_corrente`) são silenciadas pelo poller — não disparam. A métrica
  deve existir em `_NUMERIC_METRIC_REGISTRY` e o catálogo em `list_numeric_metrics()`
  deve estar em sync.

### 3.3 event (evento de plataforma)

- Disparado via `enqueue_routine_event()` em Python ou via RPC SQL
  `dispatch_routine_event(routine_id, client_id, trigger_data)`
- Eventos suportados: `ingestion_completed`, `onboarding_completed`,
  `monthly_close`, `new_integration`, `document_created`
- Cooldown configurável via `trigger_config.cooldown_hours`
- Encadear rotinas: ao final dos steps, `on_complete.fire_event` dispara outro evento
  via RPC `fire_event_for_client`

### 3.4 manual

- Inserção direta de row em `client_routine_executions` com `status=dispatched`
  (via painel, chat ou `run_routine.py`)
- Não passa pelo poller de triggers

---

## 4. Definição de steps (jsonb)

Cada step é um objeto no array `steps` da rotina. Campos comuns:

| Campo          | Descrição                                                           |
|----------------|---------------------------------------------------------------------|
| id             | Identificador único do step (string)                               |
| step           | Número ordinal (usado no HITL resume)                              |
| type           | `function` \| `skill` \| `llm` \| `artifact` \| `approval`        |
| inputs         | Dict com valores ou templates `{{chave}}`                           |
| outputs        | Schema de saída esperada (dict nome→tipo)                           |
| on_failure     | `continue` (padrão) \| `halt`                                      |
| parallel_group | Se presente, steps com o mesmo grupo rodam em paralelo             |
| on_complete    | `{fire_event: "event_type", payload: {}}` para encadear eventos    |

### 4.1 type: function

Chamada determinística sem LLM. Registrada em `routine_functions._REGISTRY`.

```json
{
  "id": "buscar_clientes",
  "type": "function",
  "function": "analytics.query_inactive_clients",
  "inputs": { "days_inactive": "{{days_inactive}}", "limit": 100 }
}
```

Namespace de funções disponíveis: `analytics.*`, `storage.*`, `finance.*`, etc.

### 4.2 type: skill

Executa uma `SkillDefinition` do `SKILL_REGISTRY` via `SkillFactory`.
Fallback para `_invoke_worker` (agente slug) se não encontrar no registry.

```json
{
  "id": "analisar",
  "type": "skill",
  "skill_slug": "finance_monitor_report",
  "task_template": "Analise o fluxo de caixa: {{resumo_financeiro}}",
  "outputs": { "summary": "string", "alertas": "list" }
}
```

Se `outputs` está definido, o engine injeta instrução de JSON structured output
no final da task e tenta extrair via `_extract_json_from_text`.

⚠️ As skills dos 4 monitores (`agenda_monitor_report`, `clients_monitor_report`,
`inventory_digest`, `finance_monitor_report`) não estão no SKILL_REGISTRY (Jun/2026).
O engine faz fallback para `_invoke_worker` e recebe erro `Unknown worker`, retornando
`summary=""`. O step `write_memory` subsequente falha pq `summary` é required. Ver
issue no BACKLOG_IDEAS.md.

### 4.3 type: llm

Chamada direta a LLM via prompt Langfuse. Sem agente, sem tools.

```json
{
  "id": "gerar_briefing",
  "type": "llm",
  "prompt_name": "blu/daily_briefing_v1",
  "model_tier": "fast",
  "outputs": { "briefing": "string" }
}
```

Variáveis do state são injetadas no prompt via `prompt_obj.compile(**ctx)`.

### 4.4 type: artifact

Side effects: email, alert, WhatsApp, documento. Com dedupe automático.

```json
{
  "id": "enviar_email",
  "type": "artifact",
  "artifact_type": "email",
  "function": "channels.send_email_batch",
  "inputs": { "recipients": "{{lista_clientes}}", "body": "{{summary}}" }
}
```

Funções de artifact disponíveis:
- `channels.send_email_batch` — e-mail em lote
- `channels.send_email` — e-mail único
- `channels.send_whatsapp` — WhatsApp
- `channels.create_alert` — alerta in-app
- `channels.request_approval` — HITL approval gate
- `storage.save_context_document` — salva documento

Dedupe: funções side-effectful criam um claim em `artifact_delivery_claims`
antes de executar. Reexecuções do mesmo step são silenciadas.

### 4.5 type: approval (HITL)

Pausa a execução, cria row em `approval_requests`. Quando aprovada,
o trigger `trg_redispatch_after_approval` reinsere a execução a partir do
step seguinte (`result_metadata._resume_from_step`).

---

## 5. Engine de execução — estado compartilhado

O estado (`state dict`) é inicializado com:

```
trigger_data            ← dados do evento/trigger
client_id               ← UUID do cliente
routine_name            ← nome da rotina
exec_id                 ← UUID da execução
nome_empresa            ← da tabela clientes_blu
website_url             ← de company_profile JSONB
schema_defaults         ← defaults do config_schema da rotina
client_config           ← overrides do cliente (wins sobre schema_defaults)
tier                    ← tier do cliente (sempre wins sobre client_config)
```

A cada step, outputs são merged no state (`state[k] = v`).
Templates `{{chave}}` em inputs/task_template são resolvidos contra o state
antes do step executar. Valores nulos/listas vazias/dicts vazios viram `""`.

⚠️ Atenção ao mismatch de chaves: se um step de skill retorna `{"summary": "..."}` mas
o step seguinte usa `{{memory_summary}}`, o placeholder não resolve e a string literal
`{{memory_summary}}` chega ao banco. A chave usada no template deve bater exatamente com
a chave do `outputs` do step anterior.

⚠️ Config schema e defaults: valores do `config_schema` com `default` são injetados no
state inicial como `schema_defaults`. Se o cliente não tiver override em `client_routines.config`
E o step usa `{{threshold_caixa}}` diretamente nos inputs, o valor vem do schema_defaults.
Se `schema_defaults` não inclui a chave (bug de schema), o placeholder não resolve e funções
numéricas que esperam float recebem a string `{{threshold_caixa}}` e crasham.

O state é checkpointado em `result_metadata` após cada batch de steps,
permitindo resume após aprovação HITL.

---

## 6. Concorrência e resiliência

### 6.1 Claim atômico (SKIP LOCKED)

`claim_routine_executions(batch_size)` faz UPDATE com `FOR UPDATE SKIP LOCKED`,
garantindo que múltiplos workers não peguem a mesma execução.

### 6.2 Guard de in-flight

`_dispatch_execution_sync` verifica se já existe execução em `pending |
dispatched | executing` para o mesmo `client_id + routine_id` antes de inserir.
Isso evita disparos duplicados mesmo que o poller rode duas vezes.

### 6.3 Semáforo por cliente

Cada client_id tem um `asyncio.Semaphore(4)` — no máximo 4 execuções paralelas
por cliente dentro do mesmo processo worker.

### 6.4 Heartbeat

Thread daemon (`threading.Thread`) pulsa `heartbeat_at` a cada 20s fora do
event loop. Isso evita que o reaper marque como morta uma execução bloqueada
em chamada síncrona que teria congelado um heartbeat baseado em `asyncio.sleep`.

### 6.5 Timeout global

Cada execução tem timeout de 120s (`_ROUTINE_EXECUTION_TIMEOUT_S`).
Timeout → status `failed` + contagem no circuit breaker.

### 6.6 Circuit breaker

`record_routine_failure(client_id, routine_id, max_failures=3)` via RPC.
Após 3 falhas consecutivas → status da assinatura vira `suspended`.
`reset_routine_failures` é chamado após sucesso.

---

## 7. Notificação ao cliente

Após `status=completed`, `_notify_client()` lê `notify_channel` da assinatura:

| Canal     | Mecanismo                                         |
|-----------|---------------------------------------------------|
| `app`     | Nenhuma ação extra — notificação in-app gerada separadamente |
| `whatsapp`| `TwilioClient.send_whatsapp(phone_e164, message)` |
| `email`   | `_deliver_email(email, subject, body, client_id)` |

A mensagem sempre inclui: nome da rotina + primeira linha do result_text +
link para app.blu.com.br.

---

## 8. Dispatcher SQL → HTTP

A ponte entre o banco e o Python é:

```
pg_cron (a cada minuto)
  → SELECT cron.schedule('dispatch-routines', '* * * * *',
        'SELECT public.dispatch_routine_executions()')
  → dispatch_routine_executions() [SQL]
      → lê app_config: agent_api_core_url + agent_api_routine_dispatch_token
      → net.http_post(url || '/internal/routines/run-dispatched',
                      Authorization: Bearer <token>,
                      timeout: 30s)
```

O endpoint retorna 202 imediatamente e processa em `BackgroundTask` para não
bloquear o timeout de 30s do pg_net.

Token: env `ROUTINE_DISPATCH_TOKEN` + `app_config.agent_api_routine_dispatch_token`.
URL:   env ou `app_config.agent_api_core_url`.

---

## 9. Catálogo de rotinas (cross_agent_routines atuais)

25 rotinas no catálogo (Jun/2026):

| id                           | trigger_type | Descrição                                    |
|------------------------------|--------------|----------------------------------------------|
| agenda_monitor               | cron         | Monitor de Agenda Diário (05:30)             |
| cash_flow_alert              | numeric      | Alerta de Fluxo de Caixa                     |
| client_reactivation          | cron         | Reativação de Clientes (dia 15)              |
| clientes_monitor             | cron         | Monitor de Clientes Diário (06:30)           |
| collection_overdue           | cron         | Cobrança de Inadimplentes (seg 09h)          |
| competitor_analysis          | cron         | Análise de Concorrência (dia 1 mensal)       |
| compras_monitor              | cron         | Monitor de Compras Diário (07h)              |
| context_report_monthly       | cron         | Relatório de Contexto Mensal (dia 1 03h)     |
| context_report_post_ingestion| event        | Relatório de Contexto Pós-Ingestão           |
| daily_briefing               | event        | Plano do Dia (evento morning_ready)          |
| daily_insights               | cron         | Insights Diários (06h)                       |
| deadline_radar               | cron         | Radar de Prazos (12h)                        |
| end_of_day_digest            | cron         | Digest do Fim de Dia (21h)                   |
| financeiro_monitor           | cron         | Monitor Financeiro Diário (06h)              |
| hidden_patterns              | cron         | Padrões Escondidos (dom 08h)                 |
| inventory_alert              | cron         | Nível de Estoque Crítico (seg-sex 08h)       |
| meeting_prep                 | event        | Prep Reunião (evento calendar_changed)       |
| monthly_reconciliation       | cron         | Relatório de Conciliação Mensal (dia 5 08h)  |
| morning_sync                 | cron         | Sincronização da Manhã (10h)                 |
| onboarding_complete          | event        | Mapa de Contexto Onboarding                  |
| pending_decisions_review     | cron         | Revisão de Decisões Pendentes (11h)          |
| sales_followup               | event        | Follow-up de Vendas (evento sale_approved)   |
| satisfaction_survey          | event        | Pesquisa de Satisfação (evento pedido_entregue)|
| supplier_management          | event        | Gestão de Fornecedores (evento compra_aprovada)|
| weekly_summary               | cron         | Resumo Semanal (sex 20h)                     |

Config padrão e config_schema específicos de cada rotina vivem nas rows de
`cross_agent_routines`. Overrides por cliente ficam em `client_routines.config`.

---

## 10. SKILL_REGISTRY — skills usadas em steps de rotina

Skills de rotina são `SkillDefinition` com tag `l3` registradas em
`blu_agent_framework/skills.py → SKILL_REGISTRY`. Steps do tipo `skill`
referenciam o `name` da SkillDefinition via `skill_slug`.

O execution engine usa `SkillFactory.run(skill_name, parent_state)` diretamente,
sem passar pelo grafo do orchestrator. Fallback para `_invoke_worker` (agent
slug) quando o skill_slug não existe no SKILL_REGISTRY.

---

## 11. Rotinas customizadas (client_routines sem catálogo)

Quando `routine_id` é um UUID, a rotina é buscada em `client_routines` em vez
de `cross_agent_routines`. São rotinas criadas autonomamente pela IA ou pelo
usuário no builder. Steps e config ficam inteiramente em `client_routines`.

---

## 12. Como testar localmente

```bash
cd services/agent_api

# Executar uma rotina de catálogo manualmente para um client_id de teste
python run_routine.py <routine_id> <client_id>

# Exemplos:
python run_routine.py financeiro_monitor fa707dd2-2d9f-4b10-92a6-f6e641d0a5cb
python run_routine.py clientes_monitor   fa707dd2-2d9f-4b10-92a6-f6e641d0a5cb
python run_routine.py agenda_monitor     fa707dd2-2d9f-4b10-92a6-f6e641d0a5cb
python run_routine.py compras_monitor    fa707dd2-2d9f-4b10-92a6-f6e641d0a5cb
```

Se libs internas estiverem desatualizadas:
```bash
pip install -e libs/blu_tool_registry
pip install -e libs/blu_agent_framework
```

Para verificar o catálogo de primitivos disponíveis (functions, artifacts, skills):
```
GET /v1/routines/catalog   (requer agent_api rodando)
```
