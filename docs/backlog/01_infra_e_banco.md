# Backlog — Infra & Banco de Dados

---

## ✅ CONCLUÍDO — Tenant Deletion Assíncrono (Wipe Worker)

**Problema:** DELETE direto trava PgBouncer por ~6min em tenants com 180k+ rows.

**Status:** ✅ Implementado — migrations `applied/20260525_p11_tenant_wipe_worker.sql` e `p11_fix_tenant_wipe_tick_ambiguity.sql` confirmados no repo.

**Pendente (decisão):** Hard-delete vs anonimização LGPD — definir política antes de novo cliente churn.

---

## ⏳ PENDENTE — Pool de Conexões para Produção (B2)

**Status:** `pool_size` atual é 5 (padrão) e 2 (session mode). Meta era aumentar para 6/max_overflow=3.

**Ação:** Ajustar `libs/blu_supabase_client/src/blu_supabase_client/db_engine.py` + validar limite da instância Supabase.

**Esforço:** 2h

---

## ⏳ PENDENTE — Shared Business Memory com pgvector

**Status:** ❌ Não implementado. `dimension_state` ainda é o substituto.

Schema proposto (tabela `shared_business_memory`): campos `entity_type`, `entity_name`, `key`, `body`, `embedding vector(1536)`, `source`, `curated`, `confidence`, `expires_at`.

**Quando explorar:** quando `dimension_state` for insuficiente para múltiplos alertas simultâneos ou quando Memory Agent precisar de contexto vetorial (ver PRD Blu Intelligent Memory).

---

## ⏳ PENDENTE — Pipeline de Ingestão Multilíngue

**Problema:** `match-columns` usa aliases hardcoded PT/EN. Qualquer novo idioma exige patch manual.

**Solução recomendada:** Híbrido LLM (cobertura multilíngue) + fallback aliases hardcoded (determinismo). Confidence score decide.

**Pré-requisito:** decidir contrato canonical (PT ou EN).

**Impacto:** `match-columns`, `upload-csv-source`, `etl-bigquery-ingest`, `apply_staging_to_facts`.

**Esforço:** 3-4 dias
