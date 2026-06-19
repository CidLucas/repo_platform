# repo-index.md — Service & Layer Catalog (#57)

> Baseline gerado por factory-planner em 2026-06-19.
> Fonte: scan completo do monorepo (pygount) + docs/system_reference/.

## Stats (source only, excluindo node_modules, .git, build, supabase)

| Métrica | Valor |
|----------|-------|
| Total de arquivos fonte | 3,710 |
| Linhas de código | 426,606 |
| Linhas de comentário | 84,401 |
| Ratio code/comment | 5.1:1 |
| Duplicatas detectadas | 88 arquivos |
| Gerados | 10 arquivos |
| Binários | 31 arquivos |

## Language Breakdown

| Language | Files | Code Lines | % Code | % Files |
|----------|-------|-----------|--------|---------|
| TypeScript | 1,160 | 164,754 | 38.6% | 31.3% |
| TSX | 714 | 100,318 | 23.5% | 19.2% |
| Python | 428 | 59,029 | 13.8% | 11.5% |
| YAML | 123 | 36,710 | 8.6% | 3.3% |
| JSON | 64 | 33,635 | 7.9% | 1.7% |
| XML | 44 | 19,688 | 4.6% | 1.2% |
| SQL | 479 | 4,506 | 1.1% | 12.9% |
| Markdown | 450 | 0 (comment only) | 0% | 12.1% |
| Outros | 248 | 7,966 | 1.9% | 6.7% |

## Layer Map

### L1 — Tools (Tool Pool API)
Repositório: `services/tool_pool_api/`
Language: Python (FastAPI)
Entry points: `src/server.py`, `src/routes/`
Key deps: blu_models, blu_supabase_client, blu_rag_factory, blu_sql_factory, blu_google_suite_client
Reference patterns: TASK_PLAYBOOKS.md §5, TOOL_INVENTORY.md

### L2 — Skills (Agent Framework)
Repositório: `libs/blu_agent_framework/`
Language: Python (LangGraph)
Entry points: `src/blu_agent_framework/graphs/`, `src/blu_agent_framework/routines/`
Key deps: blu_prompt_management, blu_llm_service, blu_context_service, blu_hitl_service
Reference patterns: SKILLS_SYSTEM.md §Skills Catalog, TASK_PLAYBOOKS.md §3

### L3 — Domain Specialists
Repositório: `services/agent_api/`
Language: Python (FastAPI)
Entry points: `src/agent_api/core/`, `src/agent_api/routers/`
Key deps: blu_agent_framework, blu_context_service, blu_supabase_client
Reference patterns: AGENT_SYSTEM.md

### L4 — Frontdesk (Orchestrator)
Repositório: `apps/blu_v3/`
Language: TypeScript/TSX (React 18 + Vite + Tailwind v3)
Entry points: `src/main.tsx`, `src/App.tsx`, `src/components/rooms/`
Key deps: blu-auth (packages), supabase-js
Reference patterns: FRONTEND.md (not found on disk — listed in HERMES.md)

## Library Catalog (libs/) — 23 Libraries

| Lib | Language | Purpose | Key Files | Deps |
|-----|----------|---------|-----------|------|
| blu_agent_framework | Python | LangGraph agent graphs, skills, routines engine | graphs/, routines/ | blu_prompt_management, blu_llm_service |
| blu_auth | Python/TS | Authentication & authorization | src/ | blu_supabase_client |
| blu_context_service | Python | Redis cache + business memory snapshots | src/ | redis, blu_models |
| blu_data_connectors | Python | BigQuery, CSV, Sheets connectors | src/ | blu_supabase_client |
| blu_db_connector | Python | Database abstraction layer | src/ | blu_supabase_client |
| blu_elicitation_service | Python | User elicitation/conversation service | src/ | blu_llm_service |
| blu_experiment_service | Python | A/B testing & experiments | src/ | blu_supabase_client |
| blu_google_suite_client | Python | Google Calendar, Gmail, Drive client | src/ | google-api-python-client |
| blu_hitl_service | Python | Human-in-the-loop (Redis sorted sets) | src/ | redis |
| blu_landing_intel | Python | Website intelligence (CNPJ extraction) | src/ | crawl4ai |
| blu_llm_service | Python | LLM client abstraction (Ollama, Langfuse) | src/ | langfuse, ollama |
| blu_models | Python | Pydantic shared models | src/models/ | pydantic |
| blu_observability_bootstrap | Python | OpenTelemetry tracing setup | src/ | opentelemetry |
| blu_parsers | Python | Document parsing (PDF, CSV, etc.) | src/ | pymupdf, pandas |
| blu_prompt_management | Python | Langfuse prompt management | src/ | langfuse |
| blu_rag_factory | Python | RAG pipeline (embeddings, vector search) | src/ | cohere, pgvector |
| blu_shared_utils | Python | Shared utility functions | src/ | — |
| blu_sql_factory | Python | Dynamic SQL generation | src/ | blu_supabase_client |
| blu_supabase_client | Python | Supabase CRUD client | src/ | supabase-py |
| blu_tool_registry | Python | Tool registration & discovery | src/ | — |
| blu_twilio_client | Python | WhatsApp/Twilio integration | src/ | twilio |

## Services Catalog

| Service | Language | Framework | Port | Entry Points |
|---------|----------|-----------|------|-------------|
| agent_api | Python | FastAPI | — | `src/agent_api/main.py`, `src/agent_api/routers/` |
| tool_pool_api | Python | FastAPI | — | `src/server.py`, `src/routes/` |

## Apps Catalog

| App | Language | Framework | Port | Entry Points |
|-----|----------|-----------|------|-------------|
| blu_v3 | TypeScript/TSX | React 18 + Vite + Tailwind v3 | 5175 | `src/main.tsx`, `src/App.tsx` |
| landing | — | — | — | (not present in current checkout) |

## Packages Catalog

| Package | Language | Purpose |
|---------|----------|---------|
| blu-auth | TypeScript | Shared auth package for frontend |

## Known Pattern Files (existing)

| File | Location | Status |
|------|----------|--------|
| AGENT_SYSTEM.md | docs/system_reference/ | ✅ Presente |
| SKILLS_SYSTEM.md | docs/system_reference/ | ✅ Presente |
| ROUTINES_SYSTEM.md | docs/system_reference/ | ✅ Presente |
| TOOL_INVENTORY.md | docs/system_reference/ | ✅ Presente |
| TASK_PLAYBOOKS.md | docs/system_reference/ | ✅ Presente |
| FEATURE_MAP.md | docs/system_reference/ | ✅ Presente |
| CODE_MAP.md | docs/system_reference/ | ❌ Ausente (listado em HERMES.md) |
| FRONTEND.md | docs/system_reference/ | ❌ Ausente (listado em HERMES.md) |
| DATABASE_SCHEMA.md | docs/system_reference/ | ❌ Ausente (listado em HERMES.md) |
| patterns.md | docs/ | ❌ Ausente |
| SHARED_MEMORY_DESIGN.md | docs/ | ❌ Ausente |
| hidden_patterns_improvement.md | docs/skill_improvements/ | ✅ Presente |

## Dependency Status (Phases #17–#37)

### Completed
- #17 pre-flight: foundations + integration (tests blocked)
- #18 post-flight: implementado
- #19 handoff hooks: implementado
- #20 integrity validation: implementado
- #21 routine engine checkpoint: implementado
- #22 snapshot templates: implementado

### In Progress (planning)
- #23 context_report_monthly: intake only
- #24 post-ETL snapshot: intake only
- #25 vector store pipeline: plan done, implementation parcial (3 tasks blocked)
- #26 shared_memory_search: plan done
- #27 shared_memory_graph: plan done

### Phase 4 (planning ready)
- #29 weekly synthesis SBM→LightRAG: ready
- #30 diretório meta/: ready
- #31 knowledge_graph_summary: running (planner)
- #32 retention policy: running (intake)

> **Conclusão:** Fases 1-3 substancialmente completas. Este code review (#57) é planejado agora para execução quando #17-#37 estiverem done. Risco R3 mitigado: este é apenas o plano; execução aguarda sinal.
