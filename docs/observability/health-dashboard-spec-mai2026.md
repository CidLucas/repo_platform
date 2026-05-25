# Dashboard Health — Pre-Onboarding (Mai/2026)

Especificação do dashboard de saúde operacional para acompanhar a fase de onboarding
de clientes do Blu. Não é dashboard de negócio — é **painel SRE / operador**.

## Audiência
- Lucas (engenharia) durante fase de validação 72h por cliente teste
- Operador de plantão após primeiros 5 clientes em prod

## Stack alvo
- **Backend de telemetria**: OTLP → Grafana Cloud (`OTEL_EXPORTER_OTLP_ENDPOINT` já
  configurado em `docker-compose.prod.yml`, atualmente sem dashboards organizados).
- **Fonte adicional**: Supabase (Postgres) via plugin `grafana-postgresql-datasource`
  apontando para `SUPABASE_DB_URL` (read-only role recomendado — *follow-up*).
- **Logs**: stdout dos containers Cloud Run → Cloud Logging → painel Loki/Grafana
  (`logName=projects/.../atendente-core` e `tool-pool-api`).

## Painéis (linha de prioridade)

### 1. Rotinas suspensas (CRITICAL)
**Pergunta**: alguma rotina foi suspensa por circuit breaker e ainda não foi
revisada?

```sql
-- Datasource: Supabase Postgres
SELECT
  cr.client_id,
  c.empresa_nome,
  cr.routine_id,
  cr.name,
  cr.consecutive_failures,
  cr.last_run_at,
  cr.status
FROM client_routines cr
JOIN clientes_blu c USING (client_id)
WHERE cr.status = 'suspended'
ORDER BY cr.last_run_at DESC NULLS LAST;
```

- **Visualização**: Table
- **Alerta**: count > 0 por > 15 min → Slack `#blu-alerts` (severity=high)
- **Limiar**: `consecutive_failures >= 3` (default `record_routine_failure`)

### 2. Falhas de execução por hora
**Pergunta**: temos um spike de falhas?

```sql
SELECT
  date_trunc('hour', completed_at) AS bucket,
  count(*) FILTER (WHERE status='failed')   AS failed,
  count(*) FILTER (WHERE status='completed') AS completed,
  count(*) FILTER (WHERE status='failed')::float / NULLIF(count(*),0) AS failure_rate
FROM client_routine_executions
WHERE completed_at > now() - interval '24h'
GROUP BY 1
ORDER BY 1;
```

- **Visualização**: Time series (bars empilhadas) + linha de `failure_rate`
- **Alerta**: `failure_rate > 0.2` em janela de 1h E `failed > 5` → Slack high
- **Por que ambos os limiares**: evitar alerta em horas de baixa atividade.

### 3. Heartbeat staleness (workers travados)
**Pergunta**: algum worker pegou execução, não finalizou e parou de bater
heartbeat?

```sql
SELECT
  worker_slug,
  client_id,
  routine_id,
  dispatched_at,
  heartbeat_at,
  EXTRACT(EPOCH FROM (now() - heartbeat_at))::int AS heartbeat_age_s
FROM client_routine_executions
WHERE status = 'dispatched'
  AND heartbeat_at IS NOT NULL
  AND now() - heartbeat_at > interval '5 minutes'
ORDER BY heartbeat_age_s DESC;
```

- **Visualização**: Table com cor por idade (verde <2min, amarelo <5min, vermelho >5min)
- **Alerta**: > 0 rows por > 10 min → Slack high (worker travado é incidente)
- **Index existente**: `idx_routine_exec_heartbeat` já cobre essa query.

### 4. Execuções stuck em `pending` / `dispatched`
**Pergunta**: o dispatcher está consumindo a fila?

```sql
SELECT status, count(*) AS qtd, min(created_at) AS oldest, max(created_at) AS newest
FROM client_routine_executions
WHERE status IN ('pending','dispatched')
  AND created_at > now() - interval '24h'
GROUP BY status;
```

- **Visualização**: Stat (one number per status) + Stat com idade do mais velho
- **Alerta**: oldest `pending` > 5 min → medium; > 15 min → high.

### 5. Tokens OAuth expirados ou prestes a expirar
**Pergunta**: integrações que vão começar a falhar em breve?

```sql
-- assumindo refresh_token presente => podemos refrescar; sem refresh => morto
SELECT
  it.provider,
  count(*) FILTER (WHERE it.refresh_token_encrypted IS NULL OR it.refresh_token_encrypted = '') AS no_refresh,
  count(*) FILTER (WHERE it.access_token_encrypted IS NULL OR it.access_token_encrypted = '')  AS no_access,
  count(*) AS total
FROM integration_tokens it
JOIN clientes_blu c USING (client_id)
WHERE c.is_test_account = false
GROUP BY 1
ORDER BY 1;
```

- **Visualização**: Table
- **Alerta**: `no_refresh > 0` → medium (cliente precisa re-autenticar)
- **Follow-up**: adicionar `expires_at` em `integration_tokens` para alerta
  proativo (atualmente derivamos da resposta do refresh — sem coluna pública).

### 6. Notificações de alerta por tipo (últimas 24h)
**Pergunta**: o que está acontecendo com os clientes?

```sql
SELECT
  type,
  urgency_level,
  count(*) AS qtd
FROM notifications
WHERE created_at > now() - interval '24h'
  AND type IN ('routine_suspended','integration_failed','approval_pending')
GROUP BY 1,2
ORDER BY 3 DESC;
```

- **Visualização**: Bar chart
- **Sem alerta** — observabilidade.

### 7. Latência p50/p95 de execução
**Pergunta**: rotinas estão ficando mais lentas?

```sql
SELECT
  date_trunc('hour', completed_at) AS bucket,
  percentile_cont(0.50) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (completed_at - dispatched_at))) AS p50,
  percentile_cont(0.95) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (completed_at - dispatched_at))) AS p95
FROM client_routine_executions
WHERE status = 'completed'
  AND completed_at > now() - interval '24h'
  AND dispatched_at IS NOT NULL
GROUP BY 1
ORDER BY 1;
```

- **Visualização**: Time series 2 linhas (p50, p95)
- **Alerta**: p95 > 60s sustentado por 30min → medium.

### 8. Aprovações HITL pendentes (Sprint 4 — placeholder)
```sql
SELECT count(*) FROM client_routine_executions WHERE status='awaiting_approval';
```
- **Visualização**: Stat
- **Alerta**: > 0 por > 24h → medium (cliente esqueceu).

## Variáveis de dashboard
- `$client_id` (multi-select, populado de `clientes_blu` com `is_test_account = false`)
- `$time_range` (template padrão Grafana)
- `$severity` (filtro de notifications: `low/normal/high`)

## Alertas — destinos
- Slack `#blu-alerts` (criar webhook → secret `SLACK_ALERTS_WEBHOOK_URL` no
  Vault) — *follow-up*: webhook ainda não provisionado
- Telegram bot do Lucas para severidade `high` apenas (durante validação 72h)

## Follow-ups não bloqueadores
1. Adicionar `expires_at` em `integration_tokens` para alerta proativo
2. Criar role read-only no Postgres para Grafana (não usar service_role)
3. Provisionar Slack webhook e gravar no Vault como `slack_alerts`
4. Considerar Grafana On-Call para escalation depois do MVP de onboarding
5. Exportar este dashboard como JSON sob `infra/grafana/dashboards/health.json`
   e versionar — provisioning via API (não manualmente no UI)

## Anti-objetivos (NÃO incluir agora)
- Métricas de negócio (MRR, churn, NPS) — fica em outro dashboard
- Métricas de LLM cost (tokens, $) — fica em dashboard separado de FinOps
- Tracing distribuído (spans) — já há OTEL exportando; dashboard de traces vem
  em sprint posterior quando volume justificar
