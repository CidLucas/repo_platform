# E3 — Validação 72h cliente de teste interno

**Sprint 5.** Objetivo: rodar onboarding completo num cliente `is_test_account=true`,
observar 72h de operação real, validar que todas as 25 rotinas
ativam pelo menos uma vez, dedupe funciona, TTL funciona, sem regressão de RLS.

## Pré-requisitos

- [ ] Push pendente feito (commits 6c434f65, 992af40e, sprint4)
- [ ] A4 backend deployado em Cloud Run (depende do push acima)
- [ ] Langfuse keys rotacionadas
- [ ] Identificar/criar conta de teste (hoje: 0 `is_test_account=true` na base)

## Checklist de onboarding (Dia 0)

### 1. Criar cliente teste
```sql
-- Marcar cliente existente OU inserir novo
UPDATE clientes_blu
SET is_test_account = true
WHERE client_id = '<uuid>';

-- ou novo:
INSERT INTO clientes_blu (..., is_test_account) VALUES (..., true);
```

### 2. Conectar integrações na ordem
1. Google Workspace (Gmail + Calendar + Drive)
2. WhatsApp Business (via Polp se voltar; senão skip)
3. Monday/Pipefy (CRM)
4. BigQuery (analytics)
5. Sheets export (relatórios)

### 3. Ativar rotinas builtin
Deve ser automático via `client_routines` triggers. Conferir:
```sql
SELECT routine_id, status FROM client_routines
WHERE client_id='<uuid>' ORDER BY routine_id;
-- Esperado: 8 builtin como 'active'
```

### 4. Disparar `onboarding_complete` manualmente
```sql
INSERT INTO client_routine_executions (client_id, routine_id, triggered_by, trigger_data)
VALUES ('<uuid>', 'onboarding_complete', 'manual_e3_smoke', '{}');
```

## Janela de observação 72h

### Dia 1 — Smoke imediato (+2h após onboarding)
- [ ] `client_routine_executions` tem ≥3 rows do cliente teste
- [ ] `artifact_log` ≥1 row (esperado de `onboarding_complete` → `storage.save_context_document`)
- [ ] Nenhuma execução `status='failed'` por erro de schema/RLS
- [ ] `notifications` chegou pelo menos 1 (in_app)

### Dia 2 — Cobertura amplia (+24h)
- [ ] Rotinas cron diárias dispararam: `morning_sync`, `daily_briefing`, `daily_insights`,
      `end_of_day_digest`, `agenda_monitor`, `financeiro_monitor`, `clientes_monitor`,
      `compras_monitor`, `deadline_radar`, `pending_decisions_review`
- [ ] Fail rate cliente teste < 20% (baseline prod hoje: 35% — investigar gap)
- [ ] Nenhum approval_request expirou prematuramente (D1)
- [ ] Nenhum artefato duplicado (D2) — checar `SELECT execution_id, step_id, count(*) FROM artifact_log GROUP BY 1,2 HAVING count(*)>1` deve voltar 0

### Dia 3 — Lifecycle completo (+72h)
- [ ] `weekly_summary` disparou (se cron semanal coincidir)
- [ ] Algum approval_request pendente do dia 1 expirou via TTL → notification `approval_expired`
- [ ] Circuit breaker (P8): nenhuma rotina foi suspensa indevidamente
- [ ] Logs sem stack traces não-investigados (rever últimas 72h)
- [ ] Compras: `dim_inventory.nome` populando OK (sem regressão schema-Mai)

## Script de smoke + monitor

Ver `scripts/e3_smoke.py` — roda batch de queries SQL e produz relatório executivo.

## Critérios de sucesso (para abrir onboarding público)

1. ≥20/25 rotinas dispararam pelo menos 1x sem erro
2. Fail rate cliente teste ≤ 15%
3. 0 vazamentos RLS (cliente teste não vê dados de outro client_id)
4. 0 artefatos duplicados em `artifact_log`
5. TTL funcionou em ≥1 caso real
6. P8 (suspended alert): se algum failure_count chegou a 5+, notification urgency=high foi criada

## Pós-E3

Se 5/6 critérios → onboarding GA aprovado. Documentar em
`docs/security/test-onboarding-log-mai2026.md` com timeline de eventos.
Se <5/6 → iterar Sprint 6 (correções).
