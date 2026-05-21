# Routines — Fluxo e Dependências

> Última atualização: 2026-05-21
> Catálogo: 21 rotinas ativas, todas com `llm_count = 0`

---

## 1. Visão Geral do Fluxo

```
pg_cron (1x/min)
  → dispatch_routine_executions() [RPC Supabase]
    → HTTP POST agent_api /internal/routines/run
      → _execute_routine_steps()
        → step: function  → routine_functions.py
        → step: skill     → SKILL_REGISTRY._execute_skill_step()
        → step: artifact  → routine_artifacts.py
        → step: approval  → approval_requests (pausa até HITL)
```

---

## 2. Tabelas Envolvidas

| Tabela | Papel |
|---|---|
| `cross_agent_routines` | Catálogo global: definição de rotinas, steps, trigger, room, config_schema |
| `client_routines` | Inscrições de clientes em rotinas do catálogo + config personalizada |
| `client_routine_executions` | Histórico de execuções: status, started_at, completed_at, output |
| `approval_requests` | Pausas HITL geradas por steps do tipo `approval` |
| `notifications` | Alertas entregues via steps do tipo `artifact` → `send_notification` |
| `client_insights` | Insights gerados por steps de análise |
| `dimension_state` | Estado compacto por sala, escrito pelos Room Monitors ao final de cada rotina |

---

## 3. Tipos de Step

### `function`
Função Python determinística, sem LLM. Registrada em `routine_functions.py`.
- Exemplos: `fetch_overdue_receivables`, `compute_cash_position`, `list_upcoming_meetings`
- Não consome tokens. Resultado vai para o contexto do próximo step.

### `skill`
Executa uma skill do `SKILL_REGISTRY`. Usa LLM. O step config deve ter `skill_slug`.
- Todo step `type=skill` no catálogo — nunca `type=llm`
- Inputs explicitamente declarados no `@register(inputs=[...])`
- Exemplos de skills vinculadas: `morning_plan`, `reconciliation_report`, `collection_messages`

### `artifact`
Entrega artefato para o usuário. Registrado em `routine_artifacts.py`.
- `channels.create_alert` — cria card de alerta na UI (com `execution_id` e `routine_id` no payload)
- `channels.send_notification` — cria registro em `notifications`
- Não usa LLM.

### `approval`
Cria um `approval_request` e suspende a execução da rotina. A rotina só continua quando o usuário aprova.
- `status = 'pending'` → usuário age → `status = 'approved'` | `'rejected'` | `'edited'`
- Campos: `action_type`, `title`, `insight_text`, `body`, `priority`, `assigned_role`

---

## 4. Triggers de Disparo

| Tipo | Como funciona |
|---|---|
| `cron` | `trigger_config.cron_expr` — schedule no formato `MIN HOUR DOM MONTH DOW` (5 campos, pg_cron) |
| `event` | Gatilho por evento de negócio (ex: pagamento aprovado, cliente inativou) |
| `manual` | Disparado pelo usuário via chat ou UI |
| `chain` | Disparado ao final de outra rotina |

O dispatcher roda a cada minuto. Só dispara rotinas cujo `next_run_at <= now()` e `status = 'active'`.

---

## 5. Catálogo de Rotinas (21 rotinas ativas)

| Slug | Sala | Skill L3 | Frequência |
|---|---|---|---|
| `morning_plan` | Home | `morning_plan` | Diária 07h |
| `end_of_day_digest` | Home | `end_of_day_digest` | Diária 18h |
| `weekly_summary` | Financeiro | `weekly_summary` | Semanal (seg) |
| `reconciliation_report` | Financeiro | `reconciliation_report` | Mensal |
| `collection_messages` | Clientes | `collection_messages` | Semanal |
| `followup_draft` | Clientes | `followup_draft` | Semanal |
| `reactivation_proposal` | Clientes | `reactivation_proposal` | Mensal |
| `satisfaction_survey` | Clientes | `satisfaction_survey` | Mensal |
| `meeting_brief` | Agenda | `meeting_brief` | Antes de reuniões |
| `hidden_patterns` | Estratégia | `hidden_patterns` | Semanal |
| `competitor_analysis` | Estratégia | `competitor_analysis` | Mensal |
| *(+ 10 rotinas builtin/system)* | — | — | — |

---

## 6. Visibilidade de Rotinas no Frontend

Cada rotina tem um campo `visibility`:
- `builtin` — visível e sempre ativa, não pode ser desativada pelo usuário
- `optional` — visível, o usuário pode ativar/desativar na Config da sala
- `hidden` — não aparece na UI (rotinas internas de sistema)

Config de rotinas vive na aba **Config** de cada sala (`RoutineConfigSection.tsx`). A tira inferior de cada sala exibe rotinas atualmente em execução.

---

## 7. Schedule Builder (Frontend)

`RoutineConfigSection.tsx` suporta schedules:
- `daily` — hora fixa (campo hour)
- `weekly` — dia da semana + hora
- `monthly` — dia do mês (limitado a 28 para evitar problemas em meses curtos) + hora

Gera cron no formato `MIN HOUR DOM MONTH DOW` para persistir em `client_routines.trigger_config`.

---

## 8. Dependências Técnicas

| Componente | Arquivo |
|---|---|
| Engine principal | `services/agent_api/src/agent_api/core/routines.py` |
| Funções determinísticas | `services/agent_api/src/agent_api/core/routine_functions.py` |
| Artefatos de entrega | `services/agent_api/src/agent_api/core/routine_artifacts.py` |
| Skill execution | `libs/blu_agent_framework/src/blu_agent_framework/skills.py` |
| Context injection | `libs/blu_context_service/src/blu_context_service/context_service.py` |
| Migrations relevantes | `supabase/migrations/20260520000300_routines_schema_additions.sql` |
| | `supabase/migrations/20260520000500_new_routines_seed.sql` |
| | `supabase/migrations/20260521000100_routines_llm_to_skill.sql` |
