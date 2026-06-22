# inventory-catalog.md — Baseline Service & Library Catalog (#57)

> **Gerado por:** factory-coder (t_13beaba9), 2026-06-22  
> **Fonte:** scan automatizado de `libs/`, `services/`, `apps/`, `packages/`  
> **Branch:** `phase-0/issue-57-code-patterns-review`  
> **Depende de:** `patterns.md`, `resolution.md`, `repo-index.md`

---

## 1. Summary

| Métrica | Valor |
|----------|-------|
| Total de artefatos catalogados | **25** (21 libs, 2 services, 1 app, 1 package) |
| Libs Python | 21 |
| Services Python (FastAPI) | 2 |
| Apps TypeScript/TSX | 1 |
| Packages TypeScript | 1 |
| Diretórios vazios | 0 |
| Libs com `__init__.py` | 20/21 (blu_shared_utils sem entry points explícitos) |

---

## 2. Tier Classification (per resolution.md §DQ3)

| Tier | Criticality | Items | Threshold Adjustment |
|------|-------------|-------|---------------------|
| **Tier 1** (crítico) | Core infra — falha bloqueia toda operação | 5 libs + 1 service | P1 findings → escalated to P0 |
| **Tier 2** (alto) | Serviços estratégicos — falha degrada funcionalidades-chave | 4 libs + 1 service | Standard thresholds |
| **Tier 3** (médio) | Suporte — falha afeta features específicas | 4 libs | Standard thresholds |
| **Tier 4** (baixo) | Auxiliares, UI, packages | 8 libs + 1 app + 1 package | Relaxed thresholds |

---

## 3. Library Catalog — Tier 1 (Crítico)

| Lib | Language | Key Entry Points | External Deps | Internal Deps |
|-----|----------|-----------------|---------------|---------------|
| **blu_agent_framework** | Python | `src/blu_agent_framework/__init__.py`, `routines/__init__.py` | langgraph, langchain-core, pydantic, redis, httpx, jinja2, anyio, mcp, langchain-mcp-adapters | — |
| **blu_supabase_client** | Python | `src/blu_supabase_client/__init__.py` | supabase, python-dotenv, pydantic | — |
| **blu_models** | Python | `src/blu_models/__init__.py`, `ingestion/__init__.py` | sqlmodel, pydantic, psycopg2-binary | — |
| **blu_context_service** | Python | `src/blu_context_service/__init__.py` | redis | blu_models, blu_supabase_client |

## 4. Library Catalog — Tier 2 (Alto)

| Lib | Language | Key Entry Points | External Deps | Internal Deps |
|-----|----------|-----------------|---------------|---------------|
| **blu_llm_service** | Python | `src/blu_llm_service/__init__.py` | langchain-core/community/ollama, langfuse, requests, pydantic-settings, langchain-openai/anthropic/google-genai, huggingface-hub | — |
| **blu_rag_factory** | Python | `src/blu_rag_factory/__init__.py` | langchain-core, httpx | blu_llm_service, blu_context_service, blu_models, blu_prompt_management |
| **blu_prompt_management** | Python | `src/blu_prompt_management/__init__.py` | pydantic, jinja2, fastmcp | blu_models, blu_db_connector, blu_sql_factory |
| **blu_sql_factory** | Python | `src/blu_sql_factory/__init__.py`, `config/__init__.py` | langchain-core/community, sqlalchemy, sqlglot | blu_llm_service, blu_context_service, blu_models, blu_supabase_client |

## 5. Library Catalog — Tier 3 (Médio)

| Lib | Language | Key Entry Points | External Deps | Internal Deps |
|-----|----------|-----------------|---------------|---------------|
| **blu_auth** | Python | `src/blu_auth/__init__.py`, `adapters/`, `core/`, `dependencies/`, `fastapi/` | pyjwt, pydantic, pydantic-settings, cryptography, google-auth-oauthlib, google-auth, google-cloud-secret-manager, fastapi | — |
| **blu_hitl_service** | Python | `src/blu_hitl_service/__init__.py` | redis, pydantic | blu_models |
| **blu_data_connectors** | Python | `src/blu_data_connectors/__init__.py`, `accounting/`, `base/`, `bigquery/`, `ecommerce/` | httpx, numpy, pandas, pyarrow, google-cloud-bigquery, google-auth, db-dtypes | — |
| **blu_db_connector** | Python | `src/__init__.py`, `src/blu_db_connector/__init__.py` | sqlalchemy, alembic, psycopg2-binary, pyjwt, python-dotenv, sqlmodel, pandas | — |

## 6. Library Catalog — Tier 4 (Baixo)

| Lib | Language | Key Entry Points | External Deps | Internal Deps |
|-----|----------|-----------------|---------------|---------------|
| **blu_google_suite_client** | Python | `src/.../__init__.py`, `calendar/`, `docs/`, `gmail/`, `sheets/` | google-api-python-client, google-auth, google-auth-httplib2, google-auth-oauthlib, pydantic, httpx | — |
| **blu_elicitation_service** | Python | `src/blu_elicitation_service/__init__.py` | pydantic, redis | blu_models |
| **blu_experiment_service** | Python | `src/blu_experiment_service/__init__.py` | httpx, pydantic, pydantic-settings, pyyaml, sqlmodel, asyncpg, langfuse, greenlet | blu-models, blu-db-connector |
| **blu_landing_intel** | Python | `src/blu_landing_intel/__init__.py` | httpx | — |
| **blu_observability_bootstrap** | Python | `src/blu_observability_bootstrap/__init__.py` | opentelemetry-api/sdk, opentelemetry-instrumentation-fastapi, opentelemetry-exporter-otlp, python-json-logger, langfuse, langchain-core, fastapi | — |
| **blu_parsers** | Python | `src/blu_parsers/__init__.py`, `chunker/`, `parsers/` | pypdf, pandas, docling | — |
| **blu_shared_utils** | Python | *(sem __init__.py próprio)* | pandas | blu_models |
| **blu_tool_registry** | Python | `src/blu_tool_registry/__init__.py`, `tools/__init__.py` | pydantic | — |
| **blu_twilio_client** | Python | `src/blu_twilio_client/__init__.py` | twilio, pydantic, pydantic-settings | — |

## 7. Services Catalog

| Service | Language | Framework | Entry Points | Key External Deps | Internal Deps (count) |
|---------|----------|-----------|-------------|-------------------|----------------------|
| **agent_api** (Tier 1) | Python | FastAPI | `src/agent_api/main.py`, `api/`, `core/` | fastapi, uvicorn, redis, langfuse, langgraph, langgraph-checkpoint-redis, croniter, httpx, anyio | 16 libs: blu-auth, blu-models, blu-agent-framework, blu-prompt-management, blu-llm-service, blu-tool-registry, blu-context-service, blu-db-connector, blu-supabase-client, blu-google-suite-client, blu-parsers, blu-rag-factory, blu-hitl-service, blu-elicitation-service, blu-sql-factory, blu-observability-bootstrap |
| **tool_pool_api** (Tier 2) | Python | FastAPI + MCP | `src/tool_pool_api/main.py`, `api/`, `core/`, `server/` | fastapi, uvicorn, fastmcp, redis, langfuse, duckdb, reportlab, openpyxl, crawl4ai | 16 libs: blu-models, blu-db-connector, blu-context-service, blu-auth, blu-observability-bootstrap, blu-llm-service, blu-rag-factory, blu-sql-factory, blu-tool-registry, blu-prompt-management, blu-google-suite-client, blu-parsers, blu-elicitation-service, blu-agent-framework, blu-supabase-client, blu-twilio-client |

## 8. Apps & Packages Catalog

| Name | Category | Language | Framework | Entry Points | Key External Deps |
|------|----------|----------|-----------|-------------|-------------------|
| **blu_v3** | apps | TypeScript/TSX | React 18 + Vite + Tailwind v3 | `src/main.tsx`, `src/App.tsx` | react, react-dom, react-router-dom, @supabase/supabase-js, @tanstack/react-query, zustand, xlsx, @phosphor-icons/react |
| **blu-auth** | packages | TypeScript | Shared auth package | `src/index.ts` | react, @supabase/supabase-js |

---

## 9. Language Breakdown

| Language | Count | % |
|----------|-------|---|
| Python | 23 (21 libs + 2 services) | 92% |
| TypeScript/TSX | 2 (1 app + 1 package) | 8% |

**Nota:** SQL não aparece como linguagem primária de nenhum artefato — migrations estão em `supabase/migrations/` (fora do escopo deste scan que foca em `libs/`, `services/`, `apps/`, `packages/`).

---

## 10. Cross-Service Dependency Graph

```
                    ┌─────────────────────────────────────────────┐
                    │              blu_models (T1)                 │
                    │         (shared Pydantic models)             │
                    └──────┬──────────┬──────────┬────────────────┘
                           │          │          │
              ┌────────────┼──────────┼──────────┼────────────────┐
              ▼            ▼          ▼          ▼                 ▼
    blu_context_service  blu_hitl  blu_elicitation  blu_shared_utils  blu_experiment
         (T1)            (T3)      (T4)             (T4)              (T4)
              │                          
    ┌─────────┼─────────┐               
    ▼         ▼         ▼               
blu_supabase  blu_prompt_mgmt (T2)──────► blu_db_connector (T3)
(T1)              │                            │
                  ▼                            ▼
            blu_sql_factory (T3)──────► blu_llm_service (T2)
                  │                            │
                  └────────────┬───────────────┘
                               ▼
                        blu_rag_factory (T2)

    ┌──────────────────────────────────────────────────────────┐
    │                    SERVICES                               │
    │  agent_api (T1) ──► 16 internal libs (via pyproject.toml) │
    │  tool_pool_api (T2) ──► 16 internal libs                  │
    └──────────────────────────────────────────────────────────┘

    ┌──────────────────────────────────────────────────────────┐
    │                    FRONTEND                               │
    │  blu_v3 (T4) ──► packages/blu-auth (T4)                  │
    └──────────────────────────────────────────────────────────┘
```

**Legenda:** T1=Crítico, T2=Alto, T3=Médio, T4=Baixo

**Observações sobre o grafo:**
- `blu_models` (T1) é o nó mais referenciado — 6 libs dependem diretamente dele
- `blu_supabase_client` (T1) é dependency de `blu_context_service` (T1) e `blu_sql_factory` (T3)
- `blu_agent_framework` (T1) não aparece como dependência interna de nenhuma lib — é consumido apenas pelos services
- Os services (`agent_api`, `tool_pool_api`) são os integradores finais — cada um referencia 16 libs internas
- 9 libs não têm dependências internas (standalone): blu_agent_framework, blu_supabase_client, blu_models, blu_llm_service, blu_auth, blu_data_connectors, blu_google_suite_client, blu_landing_intel, blu_observability_bootstrap, blu_parsers, blu_tool_registry, blu_twilio_client

---

## 11. Reference Documentation Matrix

### 11.1 Present in `docs/system_reference/`

| Document | Status | Covers |
|----------|--------|--------|
| AGENT_SYSTEM.md | ✅ Presente | 12 agentes: papéis, hierarquia, roteamento, arquitetura |
| SKILLS_SYSTEM.md | ✅ Presente | Catálogo de skills: tools, agentes, governance |
| ROUTINES_SYSTEM.md | ✅ Presente | Fluxo de rotinas: pg_cron → steps |
| TOOL_INVENTORY.md | ✅ Presente | Auditoria de tools por tier/domínio |
| TASK_PLAYBOOKS.md | ✅ Presente | Receitas: adicionar rotina, skill, tool, integração |
| FEATURE_MAP.md | ✅ Presente | Tier → Features → Agents + Tools |
| README.md | ✅ Presente | Visão geral do diretório |

### 11.2 Listed in HERMES.md but MISSING (P2 documentation gaps)

| Document | Priority | Domain |
|----------|----------|--------|
| CODE_MAP.md | P2 | Mapa de navegação do monorepo |
| FRONTEND.md | P2 | Design system, componentes, UI patterns |
| DATABASE_SCHEMA.md | P2 | Schema Supabase: tabelas, colunas, RLS |
| DATABASE_FUNCTIONS_MAP.md | P2 | Funções DB por domínio |
| PRODUCT_CONCEPT.md | P2 | Visão de produto, filosofia |
| MONDAY_API_REFERENCE.md | P2 | Referência da API Monday |
| ONBOARDING.md | P2 | Fluxo de onboarding |
| ONBOARDING_CONTEXT_MAP.md | P2 | Mapa de contexto onboarding |
| TOOL_REGISTRY_REPORT.md | P2 | Relatório de registry de tools |

### 11.3 Referenced in task spec but NOT FOUND

| Document | Status |
|----------|--------|
| SHARED_MEMORY_DESIGN.md | ❌ Ausente — não listado em HERMES.md, não existe no disco |

### 11.4 Present in `docs/planning/issue-57/` (this review)

| Document | Status | Purpose |
|----------|--------|---------|
| patterns.md | ✅ Presente | Baseline de convenções esperadas |
| resolution.md | ✅ Presente | Design decisions, tier classification |
| repo-index.md | ✅ Presente | Scan inicial (pygount stats) |
| inventory-catalog.md | ✅ **Este arquivo** | Catálogo completo com deps e grafo |

---

## 12. Notes & Observations

### 12.1 Discrepância na contagem de libs
O task spec menciona "23 libs", mas o scan em disco encontrou **21 libs** sob `libs/`. O `repo-index.md` também lista 21 na tabela (embora o título diga "23 Libraries"). Diferença de 2 — possivelmente libs planejadas mas ainda não criadas, ou removidas após o spec inicial.

### 12.2 blu_shared_utils — sem entry points
`blu_shared_utils` é o único diretório em `libs/` sem entry points explícitos (sem `__init__.py` no raiz do src). O código está em `src/blu_shared_utils/` com módulos individuais (`data_transformers.py`, etc.), mas o scan não encontrou `__init__.py` no caminho esperado.

### 12.3 Poetry naming convention
As dependências internas nos `pyproject.toml` usam nomes com hífen (`blu-agent-framework`, `blu-supabase-client`), enquanto os diretórios usam underscore (`blu_agent_framework`, `blu_supabase_client`). O mapeamento é consistente: `blu-models` ↔ `blu_models`, etc.

### 12.4 services/agent_api — Dockerfile presente
Diferente das libs, `services/agent_api/` inclui `Dockerfile`, `poetry.lock` e `run_routine.py` — indicando que é deployável como serviço standalone.

### 12.5 Monorepo poetry — sem root workspace
O root `pyproject.toml` existe mas as libs individuais têm seus próprios `pyproject.toml` com dependências internas referenciadas por `{path = "../../libs/...", develop = true}`. Não usa poetry workspaces — cada lib/service é um projeto poetry independente.

---

## 13. Acceptance Criteria Checklist

- [x] All 21 libs, 2 services, 1 app, 1 package cataloged (25 total)
- [x] Tier classification applied per resolution.md §2 DQ3
- [x] Entry points documented for each artifact
- [x] Key external dependencies extracted from pyproject.toml / package.json
- [x] Internal cross-dependencies mapped (via pyproject.toml path refs)
- [x] Missing reference docs flagged (9 absent from HERMES.md list)
- [x] File saved to `docs/planning/issue-57/inventory-catalog.md`
- [ ] Git commit + push to branch `phase-0/issue-57-code-patterns-review`

**Nota:** Discrepância "23 libs" vs "21 libs" documentada em §12.1. O repo-index.md (planner) também lista 21 libs na tabela — apesar do cabeçalho dizer "23 Libraries".
