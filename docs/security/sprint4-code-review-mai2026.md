# Pre-Onboarding Hardening — Code Review (Sprints 1-4)

**Data:** 2026-05-25. **Reviewer:** Hermes (segunda passagem).

## Status geral

| Sprint | Fase | Status | Comentário |
|---|---|---|---|
| 1 | A — Security P0..P7 | ✅ aplicado em prod | RLS + secdef + force RLS + is_test_account |
| 2 | B — Backend hardening | ✅ código pronto | A4 deploy bloqueado por push pendente |
| 3 | C — Observability + P8 | ✅ aplicado | dashboard spec + logging audit |
| 4 | D+E1 | ✅ aplicado | TTL + dedupe + inventory |
| 5 | E3 | ⏳ próximo | validação 72h cliente teste |

## Achados desta revisão

### 🟢 Sprint 4 — saúde geral
- 15 migrations P0..P10 em `applied/` (estado prod = estado git).
- 10 pg_cron jobs ativos, incluindo `expire_pending_approvals_10min` (rodou 21:10:00 succeeded).
- `approval_requests`: 61 pending todas com `expires_at` populado (100% coverage). 7 approved sem TTL (esperado).
- `artifact_log`: 0 rows (correto — nenhum email/whatsapp ainda foi disparado em prod).
- `client_routines`: 17 active / 7 inactive / 0 suspended.

### 🔴 BUG ENCONTRADO E CORRIGIDO — D2 silenciosamente off

**Sintoma:** o wire-up do dedupe checava `step.get("artifact_type") in {"email","whatsapp","document"}`,
mas **20 das 21 rotinas com artifact step em prod NÃO populam `artifact_type`** — só usam
`function: channels.create_alert` (ou similar). Resultado: dedupe nunca dispararia para
nenhuma rotina existente quando o catálogo crescer com `send_email_batch` etc.

**Fix:** inferir tipo pelo `fn_name` (mais robusto). Agora:

```python
_SIDE_EFFECTFUL_FNS = {
    "channels.send_email": "email",
    "channels.send_email_batch": "email",
    "channels.send_whatsapp": "whatsapp",
    "storage.save_context_document": "document",
}
if fn_name in _SIDE_EFFECTFUL_FNS:
    claim_id = await claim_artifact(...)
```

Hoje 1 rotina em prod (`onboarding_complete` → `storage.save_context_document`) já se
beneficia. Cobertura aumenta automaticamente conforme novas rotinas usem email/whatsapp.

### 🟡 Pontos de atenção (não-bloqueadores)

1. **`channels.create_alert` NÃO está dedupado** (decisão consciente — alert tem
   dedupe próprio via `execution_id` no payload, e re-alertar é geralmente
   benigno). Validar na E3 que não há spam.

2. **`approved` sem `expires_at`** (7 rows) — backfill P9 só cobriu pending. OK,
   approved já é estado terminal.

3. **artifact_dedupe.py usa `"now()"` como string** no `update()`. O cliente
   Supabase pode interpretar como literal. Validar na E3 que `sent_at` é
   preenchido (alternativa: `datetime.now(UTC).isoformat()`).

4. **Push pendente:** dois commits locais (`6c434f65`, `992af40e`) + um novo
   da Sprint 4. Sem isso, A4 não vai para produção (Cloud Run não rebuilda).

5. **A4 código pronto mas não deployado** — depende do push acima.

6. **Langfuse keys** ainda expostas no git history (rotacionar via console).

## Métricas de superfície (referência para E3)

```
Tabelas com RLS habilitado (sensitive):  100%
Tabelas com RLS forçado:                  Sim (P3)
pg_cron jobs ativos:                      10
client_routines.active:                   17
approval_requests pendentes:              61 (todas com TTL)
artifact_log rows:                        0 (baseline)
client_routine_executions últimas 24h:    [medir em E3]
```

## Próximo: Sprint 5 / E3

Ver `docs/security/test-onboarding-checklist-mai2026.md` (criado em seguida).
