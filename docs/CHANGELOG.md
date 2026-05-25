# CHANGELOG — repo_platform

> Log de mudanças em linguagem humana — não é git log, é "o que isso significa para quem vai usar amanhã".
> Mantido automaticamente pelo agente de documentação (cron noturno).
> Última atualização: 2026-05-25

---

## 2026-05-25 — Baseline (primeira geração automática)

*Snapshot inicial do estado do projeto. Próximas entradas serão geradas nightly a partir de commits do dia.*

**Estado geral:**
- ✅ Infraestrutura de rotinas completa (engine, pg_cron, anti-entupimento, circuit breaker)
- ✅ Pipeline de dados unificado em `fato_transacoes` (Polp + CSV + BigQuery)
- ✅ Gantt dinâmico com fontes externas (Google Calendar, Monday, Notion)
- ✅ 25 edge functions deployadas
- ✅ 82 migrations aplicadas
- ✅ 10 rotinas no catálogo (`cross_agent_routines`)
- ⚠️ Rotinas ainda sem dispatch automático funcional ponta-a-ponta (URL do agent_api precisa ser pública)
- ⚠️ `client_insights` vazia — `daily_insights` routine nunca rodou em produção

---

## 2026-05-21 — Cleanup de infra + HERMES.md expandido

**Commits:** `8a309dcd`, `2b7bc821`, `2579b15d`

**O que mudou:**
- Alembic removido do projeto — migrações agora são 100% psql direto em `supabase/migrations/`
- `scripts/README.md` criado — documenta todos os scripts utilitários (audit, seed, bq_export, etc.)
- `HERMES.md` expandido com: recursos de design em `open-design/skills/`, política de sessão do agente, links de READMEs por subsistema
- Validação da Layer 1 de agentes concluída (infra de comunicação entre agentes via shared memory)

**Impacto para devs:**
- Para rodar migrations: `psql "postgresql://..." -f supabase/migrations/ARQUIVO.sql` — não existe mais script Alembic
- Para criar migration nova: arquivo com naming `YYYYMMDDHHMMSS_descricao.sql` em `supabase/migrations/`

---

## 2026-05-20 — Observability + LLM Parser + RAG hardening

**Commits:** `80049d42`, `20b2b449`, `4dd8230f`, `402ddbfb`

**O que mudou:**

**Observability (BL-006):**
- Novo wrapper de logging de chamadas LLM em `blu_llm_service` com correlation IDs
- Cada chamada LLM agora tem `trace_id` único, `session_id`, `user_id` passados ao Langfuse
- Fix de traces fragmentados: `get_langfuse_config()` cria handler por invocação (não singleton)

**LLM JSON Parser (BL-001):**
- `parse_first_json()` substituiu `_parse_json()` — tolerante a output malformado do LLM
- O orchestrator agora não quebra quando o LLM retorna texto extra antes do JSON
- Antes: qualquer JSON fora do formato esperado → exception. Agora: tenta extrair o primeiro JSON válido

**RAG hardening:**
- Cleanup de `hybrid_match_docs` — async ingest mais robusto
- Menos chance de documentos ficarem "presos" durante indexação

**Impacto para devs:**
- Se debugar traces no Langfuse: agora estão agrupados por `trace_id` — não mais fragmentados
- `blu_agent_framework`: lifecycle, normalização e testes melhorados (BL-002 a BL-005, BL-007)

---

## 2026-05-19 — Checkpoint cards respondendo

**Commit:** `32694a5b`

Cards de aprovação HITL respondendo corretamente no frontend. Fluxo de aprovação funcionando.

---

## 2026-05-13 — Skills refactor + merge agent-api

**Commit:** `3bb21d5c`

- Refactor do sistema de skills: separação mais clara entre L2 (skills) e L3 (prompts Langfuse)
- Merge da branch agent-api: consolidação do serviço de agentes

---

## Histórico de mudanças de arquitetura (Mai-2026)

*Decisões grandes que afetam o projeto inteiro — ver HERMES.md para detalhes completos.*

| Data | Decisão |
|---|---|
| 21-Mai | `fato_compras` dropada — tudo em `fato_transacoes` com `entry_type` |
| 21-Mai | `entry_type` derivado automaticamente: `revenue\|purchase\|expense\|banking` |
| 22-Mai | `client_insights.dimension` renomeada para `room` |
| 22-Mai | `onboarding_bootstrap_tx` corrigido para setar `active=true` nas rotinas |
| 22-Mai | Anti-entupimento implementado: semáforo por cliente, circuit breaker, heartbeat, reaper |
| 22-Mai | Langfuse traces: handler por invocação com `trace_id` fixo (não mais singleton fragmentado) |
| 21-Mai | Polp ETL completo: `sync_polp_transactions` → `fato_transacoes` |
| 21-Mai | Gantt com fontes externas: edge function `get-agenda-events` |
| 21-Mai | Soft delete de clientes: `soft_delete_client()` + pg_cron de purge noturno |
| 21-Mai | Separação de connection strings: pooler (6543) para API, direct (5432) para bulk |
