# Blu Routines — MVP Backlog
> Gerado em: 2026-05-20  
> Âncora: análise do repo + catálogo v2.1 (26 rotinas)  
> Convenção de status: 🟢 existe | 🟡 existe parcialmente | 🔴 falta

---

## 0. Contexto: o que já existe

### Infraestrutura de execução (✅ sólida)
| Componente | Status | Arquivo |
|---|---|---|
| Engine de execução (step types: function/skill/artifact/approval) | 🟢 | `routines.py` |
| Registro de funções determinísticas | 🟢 | `routine_functions.py` |
| Artefatos de entrega (push_card, send_notification) | 🟢 | `routine_artifacts.py` |
| Avaliação de triggers | 🟢 | `routine_triggers.py` |
| pg_cron (minutely sweep) | 🟢 | `cron.job` — `dispatch_routine_executions` + `process_pending` |
| Tabelas: `cross_agent_routines`, `client_routines`, `client_routine_executions` | 🟢 | migrations |
| HITL / approval_requests + Redis queue | 🟢 | `blu_hitl_service` |
| Config UI (toggle, cron picker, config_schema pills) | 🟢 | `RoutineConfigSection.tsx` |
| 10 rotinas seedadas | 🟢 | `20260511000200_routines_seed_and_cron.sql` |

### Fetch functions existentes em `routine_functions.py`
| Função | O que busca |
|---|---|
| `get_kpi_snapshots` | KPIs financeiros/operacionais via `v_resumo_dashboard` |
| `get_pending_approvals` | Aprovações pendentes do cliente |
| `get_overdue_approvals` | Aprovações vencidas |
| `get_daily_activity` | Atividade do dia (sessões, ingestions) |
| `get_weekly_activity` | Atividade semanal |
| `get_calendar_events` | Google Calendar via OAuth |
| `get_upcoming_deadlines` | Deadlines combinando agenda + aprovações |
| `check_integration_health` | Saúde das conexões (erros de sync) |
| `gather_client_context` | Contexto completo do cliente (masterprompt + KPIs) |
| `get_masterprompt` | Prompt mestre do cliente |
| `query_inactive_clients` | Clientes inativos (uso interno) |

### Analytics disponíveis (analytics_v2)
- Tabelas fato: `fato_transacoes`, `fato_compras`
- Dims: `dim_clientes`, `dim_fornecedores`, `dim_inventory`, `dim_datas`
- Views prontas: `v_resumo_dashboard`, `v_series_temporal`, `v_ultimos_pedidos`, `v_distribuicao_regional`
- Jobs: `reg_jobs` (ETL status)

### Fonte Financeira (Polp)
- `polp_accounts` — saldos bancários e cartão de crédito
- `polp_transactions` — transações com paymentData, receiver, payer
- `polp-cnpj-enrich` — edge function para enriquecimento CNPJ
- **Faltam fetch functions** que leem Polp diretamente nas rotinas

---

## 1. Gaps a corrigir (todos os 6, priorizados)

### GAP-1 · Per-tenant cron dispatcher
**O que é:** `dispatch_routine_executions()` enfileira rotinas tipo `cron` mas não avalia `trigger_config.expression` por cliente — dispara todas no mesmo horário UTC.

**O que já temos:** `analytics_v2.reg_jobs` cron (job_id 2) varre e processa por cliente. Esse padrão é o modelo.

**Fix:**
```sql
-- migration: per_tenant_cron_dispatcher.sql
-- Modificar dispatch_routine_executions() para:
-- 1. Ler client_routines WHERE trigger_type IN ('cron','schedule') AND active = true
-- 2. Para cada row, avaliar se NOW() satisfaz trigger_config.expression (usando pg_cron.schedule_matches ou cálculo manual)
-- 3. Só enqueue se should_run_now = true E last_run_at < início do intervalo atual
```
- **Esforço:** M (1 migration + testes)
- **Dependências:** nenhuma
- **Prioridade:** 🔴 P0 — bloqueia todas as rotinas com horário por usuário

---

### GAP-2 · on_complete event fire no engine
**O que é:** engine não chama `fire_event_for_client` ao completar um step/rotina — morning chain funciona como 3 crons independentes, não cadeia real.

**Fix:** ~20 linhas em `routines.py`:
```python
# Em _execute_routine_execution(), após status = 'completed':
if step.get("on_complete", {}).get("fire_event"):
    await fire_event_for_client(
        client_id=client_id,
        event_type=step["on_complete"]["fire_event"],
        payload=context
    )
```
- **Esforço:** S
- **Prioridade:** 🔴 P0 — habilita cadeias (Morning → Briefing → etc.)

---

### GAP-3 · Google Calendar webhook receiver
**O que é:** pull de agenda já existe (`_get_calendar_events` via OAuth). Falta endpoint push para receber notificações de mudança do Google.

**Padrão de referência:** OAuth já implementado em `agents_router.py` (`PATCH /sessions/{id}/google`) e `context_service.get_integration_tokens`. Usar o mesmo padrão.

**Fix:**
```
POST /webhooks/google-calendar   # novo endpoint em agent_api
→ valida X-Goog-Channel-Token
→ chama fire_event_for_client(event_type='calendar_changed', ...)
→ Supabase trigger enfileira rotinas com trigger_type='event' e event='calendar_changed'
```
- **Esforço:** M
- **Prioridade:** 🟡 P1 (necessário para Prep Reunião automática)

---

### GAP-4 · Evento sale_approved no trigger SQL
**O que é:** quando `approval_requests` muda status para `approved` e `action_type` é venda, nenhum evento é disparado.

**Como config é setada:** em `RoutineConfigSection.tsx`, trigger_type=`event` com `event_name` no `trigger_config`. O campo `trigger_condition` em `cross_agent_routines` filtra o tipo de evento.

**Fix:** 1 migration — trigger AFTER UPDATE em `approval_requests`:
```sql
CREATE OR REPLACE FUNCTION public.on_approval_completed() RETURNS TRIGGER AS $$
BEGIN
  IF NEW.status = 'approved' AND NEW.action_type IN ('sale','venda','pedido') THEN
    PERFORM public.fire_event_for_client(
      NEW.client_id, 'sale_approved',
      jsonb_build_object('approval_id', NEW.id, 'payload', NEW.payload)
    );
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```
- **Esforço:** S
- **Prioridade:** 🟡 P1

---

### GAP-5 · Fetch functions faltando para as 26 rotinas
**O que falta** (baseado no catálogo + funções existentes):

| Função nova | Fonte de dados | Rotinas que usam |
|---|---|---|
| `get_cash_position` | `polp_accounts` (Polp) | Alerta de Fluxo, Conciliação |
| `get_recent_transactions` | `polp_transactions` (Polp) | Conciliação, Cobrança |
| `get_overdue_customers` | `dim_clientes` + `fato_transacoes` | Cobrança, Inadimplência |
| `get_supplier_orders` | `fato_compras` + `dim_fornecedores` | Gestão Fornecedores, Compras |
| `get_inventory_alerts` | `dim_inventory` | Nível de Estoque |
| `get_sales_performance` | `v_resumo_dashboard` + `v_series_temporal` | Follow-up Vendas, Análise |
| `get_client_pipeline` | `dim_clientes` (CRM data) | Reativação, Pipeline |
| `get_nps_data` | `analytics_v2` NPS table (se existir) | Pesquisa Satisfação |
| `get_competitor_data` | externo (search tool) | Análise Concorrência |

- **Esforço:** L (cada função ~40-80 linhas, 9 funções)
- **Prioridade:** 🟡 P1 — implementar por ordem das rotinas no MVP

---

### GAP-6 · LLM Skills (9 rotinas precisam de narrativa)
**O que é:** rotinas que precisam de linguagem natural gerada por LLM, não só dados.

| Skill slug | Rotina | O que gera |
|---|---|---|
| `morning_plan_skill` | Plano do Dia | resumo priorizando agenda + pendências |
| `daily_digest_skill` | Digest Diário | narrativa sobre atividade do dia |
| `weekly_summary_skill` | Resumo Semanal | análise de performance da semana |
| `collection_message_skill` | Mensagem de Cobrança | texto personalizado por cliente |
| `followup_draft_skill` | Follow-up Vendas | email/msg de follow-up |
| `reactivation_skill` | Reativação de Clientes | proposta de reativação |
| `meeting_prep_skill` | Prep Reunião | briefing do participante |
| `hidden_patterns_skill` | Padrões Escondidos | análise narrativa de anomalias |
| `competitor_analysis_skill` | Análise Concorrência | relatório competitivo |

- **Esforço:** L (skills via `blu-skills-development`, 1 Langfuse prompt cada)
- **Prioridade:** 🟡 P1-P2 conforme rotina

---

## 2. Classificação das 26 rotinas

### Sistema (roda para todos, sem opt-out)
> pg_cron global — não depende de `client_routines` do usuário

| Rotina | Trigger | Já seedada |
|---|---|---|
| morning_sync | cron 07:00 BRL | ✅ |
| daily_briefing | cron 07:30 BRL | ✅ |
| pending_decisions_review | cron 08:00 BRL | ✅ |
| daily_insights | cron 06:00 | ✅ |
| context_report_monthly | cron 1º do mês | ✅ |
| context_report_post_ingestion | event: ingestion_completed | ✅ |
| onboarding_complete | event: onboarding_completed | ✅ |

### Built-in (ativadas por padrão, usuário pode desligar/configurar horário)
> `client_routines.source = 'catalog'` + toggle no UI

| Rotina | Trigger | Config disponível |
|---|---|---|
| Plano do Dia | cron (hora config) | hora de execução |
| Digest Diário | cron 18:00 | hora |
| Radar de Prazos | cron 09:00 | dias da semana |
| Resumo Semanal | cron sex 17:00 | dia + hora |
| Alerta de Fluxo de Caixa | numeric: saldo < limiar | limiar (R$) |
| Cobrança de Inadimplentes | cron (semanal) | freq + dias de atraso mínimo |
| Nível de Estoque Crítico | numeric: estoque < mínimo | threshold por produto |
| Gestão de Fornecedores | event: compra_aprovada | — |

### Opcionais (desligadas por padrão, usuário ativa)
> `client_routines.active = false` por padrão no seed

| Rotina | Trigger | Quem ativa |
|---|---|---|
| Follow-up de Vendas | event: sale_approved | cliente (vendas ativas) |
| Reativação de Clientes | cron mensal | cliente |
| Prep Reunião | event: calendar_changed | cliente (requer Google) |
| Pesquisa de Satisfação | event: pedido_entregue | cliente |
| Relatório de Conciliação | cron mensal | financeiro |
| Análise de Concorrência | cron (config) | estratégia |
| Padrões Escondidos | cron semanal | analítico |
| Pipeline de Clientes | cron diário | CRM |
| Relatório de Compras | cron semanal | compras |
| Análise de Campanhas | event: campanha_finalizada | marketing |

---

## 3. Backlog MVP — Épicos e histórias

### EPIC-0 · Infraestrutura crítica
> Pré-requisito para qualquer rotina funcionar corretamente por usuário

| ID | História | Esforço | Prio |
|---|---|---|---|
| INF-01 | Per-tenant cron dispatcher: `dispatch_routine_executions()` avalia `trigger_config.expression` por cliente e compara com `last_run_at` | M | P0 |
| INF-02 | on_complete event hook no engine: após step completo, `fire_event_for_client` se `step.on_complete.fire_event` definido | S | P0 |
| INF-03 | Evento `sale_approved`: trigger AFTER UPDATE em `approval_requests` para `action_type IN ('sale','venda')` | S | P1 |
| INF-04 | Google Calendar webhook receiver: `POST /webhooks/google-calendar` → `fire_event_for_client('calendar_changed')` | M | P1 |

---

### EPIC-1 · Morning Chain (Gerente de Rotinas)
> morning_sync → daily_briefing → pending_decisions_review como cadeia real

| ID | História | Esforço | Deps |
|---|---|---|---|
| MC-01 | Seed correto: morning_sync com `on_complete.fire_event: morning_ready` em steps | S | INF-02 |
| MC-02 | daily_briefing como evento `morning_ready` (muda de cron para event) | S | MC-01 |
| MC-03 | Fetch function `get_daily_schedule`: combina `get_calendar_events` + `get_upcoming_deadlines` + `get_pending_approvals` em 1 call | S | — |
| MC-04 | Skill `morning_plan_skill`: Langfuse prompt que recebe `{kpis, agenda, pendencias}` e gera plano narrativo do dia | M | MC-03 |
| MC-05 | Artefato: card "Plano do Dia" no AgentOpsRoom com sumário + lista de pendências clicáveis | M | MC-04 |

---

### EPIC-2 · Financeiro (Fluxo de Caixa + Conciliação)

| ID | História | Esforço | Deps |
|---|---|---|---|
| FIN-01 | Fetch function `get_cash_position`: lê `polp_accounts` (saldo atual, limite crédito, disponível) por `client_id` | M | — |
| FIN-02 | Fetch function `get_recent_transactions`: lê `polp_transactions` últimos N dias, agrupa por categoria | M | — |
| FIN-03 | Rotina "Alerta de Fluxo": trigger `numeric` (saldo < `config.threshold`), roda `get_cash_position`, dispara card de alerta | M | FIN-01, INF-01 |
| FIN-04 | Skill `monthly_reconciliation_skill`: recebe transações + KPIs e gera narrativa de conciliação | M | FIN-02 |
| FIN-05 | Rotina "Relatório de Conciliação": cron mensal, steps: `get_cash_position` → `get_recent_transactions` → skill → PDF card | L | FIN-01..04 |

---

### EPIC-3 · Clientes (Cobrança + Follow-up)

| ID | História | Esforço | Deps |
|---|---|---|---|
| CLI-01 | Fetch function `get_overdue_customers`: lê `dim_clientes` + `fato_transacoes` com filtro de dias de atraso | M | — |
| CLI-02 | Skill `collection_message_skill`: gera mensagem de cobrança personalizada por cliente (tom + valor + prazo) | M | — |
| CLI-03 | Rotina "Cobrança de Inadimplentes": cron config, steps: `get_overdue_customers` → skill → approval (HITL) → send | M | CLI-01, CLI-02 |
| CLI-04 | Fetch function `get_client_pipeline`: lê dim_clientes com status CRM, última compra, frequência | M | — |
| CLI-05 | Skill `followup_draft_skill`: gera follow-up pós-venda (email/WhatsApp) contextualizado | M | INF-03 |
| CLI-06 | Rotina "Follow-up de Vendas": event `sale_approved`, steps: fetch cliente → skill → approval → send | M | CLI-04..05, INF-03 |

---

### EPIC-4 · Operações (Estoque + Fornecedores)

| ID | História | Esforço | Deps |
|---|---|---|---|
| OPS-01 | Fetch function `get_inventory_alerts`: lê `dim_inventory` com threshold de estoque mínimo por produto | M | — |
| OPS-02 | Rotina "Nível de Estoque Crítico": trigger numeric, steps: `get_inventory_alerts` → card de alerta com lista de SKUs | S | OPS-01, INF-01 |
| OPS-03 | Fetch function `get_supplier_orders`: lê `fato_compras` + `dim_fornecedores`, status de entregas | M | — |
| OPS-04 | Rotina "Gestão de Fornecedores": event `compra_aprovada`, steps: fetch pedidos → card resumo de fornecedor | S | OPS-03 |

---

### EPIC-5 · Estratégia (Padrões + Concorrência)

| ID | História | Esforço | Deps |
|---|---|---|---|
| EST-01 | Fetch function `get_sales_performance`: lê `v_series_temporal` + `v_resumo_dashboard` com comparativo período | M | — |
| EST-02 | Skill `hidden_patterns_skill`: analisa `v_series_temporal` em busca de anomalias e gera narrativa | L | EST-01 |
| EST-03 | Rotina "Padrões Escondidos": cron semanal, steps: fetch → skill → card no EstrategiaRoom | M | EST-01..02 |
| EST-04 | Skill `competitor_analysis_skill`: usa search tool + contexto do cliente para relatório competitivo | L | — |
| EST-05 | Rotina "Análise de Concorrência": cron config, steps: skill → card no EstrategiaRoom | M | EST-04 |

---

### EPIC-6 · Agenda e Reuniões

| ID | História | Esforço | Deps |
|---|---|---|---|
| AGD-01 | Google Calendar webhook endpoint + registro do watch channel por cliente | M | INF-04 |
| AGD-02 | Skill `meeting_prep_skill`: busca participante (dim_clientes ou externo), gera briefing | M | — |
| AGD-03 | Rotina "Prep Reunião": event `calendar_changed`, steps: `get_calendar_events` → `meeting_prep_skill` → card | M | AGD-01..02 |

---

## 4. Roadmap MVP — ordem de execução

```
Semana 1-2: EPIC-0 (INF-01, INF-02, INF-03)
Semana 2-3: EPIC-1 completo (Morning Chain funcional)
Semana 3-4: EPIC-2 FIN-01..03 (Alerta de Fluxo rodando)
Semana 4-5: EPIC-3 CLI-01..03 (Cobrança rodando)
Semana 5-6: EPIC-3 CLI-04..06 + EPIC-4 OPS-01..02
Semana 6-7: EPIC-4 OPS-03..04 + EPIC-6 AGD-01..03
Semana 7-8: EPIC-5 + FIN-04..05 + polish geral
```

---

## 5. Decisões abertas

1. **Agentes** — divisão ainda não definida. Não usar split por domínio. Discutir separadamente.
2. **Polp saldo em tempo real** — `polp_accounts.updated_at` é suficiente para MVP ou precisamos de webhook Polp também?
3. **NPS** — `analytics_v2` tem tabela de NPS? Confirmar antes de EPIC-3 CLI completo.
4. **Reativação** — Skill de reativação (CLI-07) — pós-MVP por complexidade de personalização.
5. **Análise de Concorrência** — qual search tool usar? WebSearch? Perplexity? Definir antes de EST-04.
