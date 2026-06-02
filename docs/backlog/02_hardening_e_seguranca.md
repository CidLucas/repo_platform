# Backlog — Hardening Operacional & Segurança

---

## ✅ CONCLUÍDO — P0/P1 Hardening

Reaper pg_cron, asyncio.wait_for, pg_net timeout, heartbeat, recursion_limit, semaphore por cliente — todos implementados.

## ✅ CONCLUÍDO — is_test_account (B1)

Migration `applied/20260525_p7_is_test_account.sql` confirmada no repo.

## ✅ CONCLUÍDO — OpenTelemetry (parcial)

Instrumentação OTEL encontrada em `services/agent_api/src/agent_api/main.py` e testes em `tool_pool_api`.

---

## ⏳ PENDENTE — P2: Claim com worker_id + pod liveness

**Descrição:** Claim resiliente a crashes — gravar `worker_id` no job antes de processar, detectar pods mortos via liveness check.

**Esforço:** 1 dia

---

## ⏳ PENDENTE — P2: Prometheus + Grafana Alerts

**Status:** ❌ Não encontrado no repo.

**Descrição:** Visibilidade operacional — métricas de rotinas, latência, erros por agente.

**Esforço:** 1 dia

---

## ⏳ PENDENTE — P2: Dead Letter Queue (routine_dlq)

**Status:** ❌ Não encontrado no repo.

**Descrição:** Rotinas que falham repetidamente vão para `routine_dlq` para debug pós-falha sem perder o contexto do erro.

**Esforço:** 3h

---

## ⏳ PENDENTE — P3: Priority Queue (event > cron)

**Descrição:** Eventos disparados por usuário têm prioridade sobre rotinas cron — UX mais responsiva.

**Esforço:** 1 dia

---

## ⏳ PENDENTE — P3: OpenTelemetry End-to-End

**Status:** Parcialmente implementado (agent_api + tool_pool_api). Falta tracing distribuído completo entre serviços.

**Esforço:** 2 dias

---

## ⏳ PENDENTE — A3: Polp Webhook Hardening

**Descrição:** Validar HMAC signature no webhook Polp, rate limiting na edge function, idempotency key por event_id.

**Status:** HMAC encontrado em outras edge functions (google-oauth, save-api-token) mas não na função Polp especificamente.

**Esforço:** 3h

---

## ⏳ PENDENTE — B3: Idempotência de Onboarding

**Descrição:** Cliente abandona no meio → volta → comportamento indefinido. Recomendado: idempotent upsert em todos os passos.

**Status:** Upsert encontrado em `routine_artifacts.py` mas não cobrindo o fluxo completo de onboarding.

**Esforço:** 1 dia

---

## ⏳ PENDENTE — E3: Validação End-to-End com Cliente de Teste

**Pré-requisitos:** deploy A4 + criar cliente teste.

**Plano:** `docs/security/test-onboarding-checklist-mai2026.md` + `scripts/e3_smoke.py`.

**Esforço:** 1 dia
