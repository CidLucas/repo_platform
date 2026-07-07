# Fix: MV refresh no run-csv-etl + job queue periódico

## Contexto

O `run-csv-etl` edge function (supabase/functions/run-csv-etl/index.ts) faz inline ETL inserindo em fato_transacoes, depois DELETA o staging e chama `sincronizar_csv_cliente` RPC. A RPC tenta ler do staging (já deletado), falha, e o `REFRESH MATERIALIZED VIEW` dentro dela nunca roda.

O frontend lê métricas de `analytics_v2.v_resumo_dashboard` (wrap da `mv_resumo_dashboard`) e `v_series_temporal`. Sem refresh das MVs, as métricas (receita_total, ticket_medio, total_pedidos, etc.) ficam zeradas mesmo com dados na fato_transacoes.

## Mudanças

### 1. run-csv-etl/index.ts — Fix imediato

Após o inline ETL (insert em dim_clientes + fato_transacoes), **antes** da limpeza do staging (linha ~347), adicionar:

```typescript
// ── Refresh MVs ──────────────────────────────────────────────────────
try {
  await svc.rpc('refresh_client_dashboards', { p_client_id: client_id });
  console.log(`[run-csv-etl] ${requestId} MVs refreshed for client=${client_id}`);
} catch (refreshErr) {
  console.warn(`[run-csv-etl] ${requestId} MV refresh failed (non-fatal):`, refreshErr);
}
```

Isso garante que as MVs sejam sempre atualizadas independente do sincronizar_csv_cliente.

### 2. sincronizar_csv_cliente — Job queue em vez de refresh inline

No arquivo `supabase/migrations/proposed/20260527000000_fix_date_parse_datetime_format.sql`, a função `sincronizar_csv_cliente` faz REFRESH MATERIALIZED VIEW nas linhas 340-343. Substituir esse refresh inline por um INSERT em `analytics_v2.reg_jobs` com `job_type = 'refresh_dashboards'`.

**ANTES (linhas 340-343):**
```sql
  -- Refresh MVs
  REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_resumo_dashboard;
  REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_series_temporal;
```

**DEPOIS:**
```sql
  -- Enqueue dashboard refresh job (dispatcher process_pending_jobs faz o refresh)
  INSERT INTO analytics_v2.reg_jobs (client_id, job_type, status, input_params, progress_pct, created_at, updated_at)
  VALUES (v_client_id, 'refresh_dashboards', 'pending', '{}'::jsonb, 0, now(), now())
  ON CONFLICT DO NOTHING;
```

Isso transforma o refresh num job que o dispatcher existente (`process_pending_jobs`, chamado por pg_cron) processa de forma assíncrona.

**Importante:** A função atual está no migration PROPOSED (`proposed/20260527000000`). A versão que está deployed pode ser diferente — verificar qual é a versão ativa no banco (a migration `20260527000000_fix_date_parse_datetime_format.sql` também existe em `proposed/`). Se a versão deployed for a de `proposed/`, editar esse arquivo. Senão, verificar qual migration aplicou a versão atual.

### 3. (Opcional) Garantir que dispatcher esteja rodando

Verificar se `process_pending_jobs` está agendado no pg_cron. A migration `20260625_p14_inline_refresh_dashboards_in_dispatcher.sql` já implementa o dispatcher inline. Se não houver um cron job de scheduling, adicionar:

```sql
SELECT cron.schedule(
  'process-pending-jobs',
  '* * * * *',  -- a cada minuto
  'SELECT analytics_v2.process_pending_jobs();'
);
```

## Verificação

1. Rodar `run-csv-etl` para um cliente de teste
2. Verificar `analytics_v2.reg_jobs` — deve ter um job `refresh_dashboards` criado
3. Aguardar o dispatcher rodar (ou chamar manualmente `SELECT analytics_v2.process_pending_jobs();`)
4. Verificar `analytics_v2.mv_resumo_dashboard` — dados devem aparecer
5. Frontend deve mostrar métricas corretas
