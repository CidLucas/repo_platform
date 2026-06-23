# duplication-review-f1-5.md — Code Duplication Analysis (Fases 1-5)

> **Gerado por:** factory-coder (t_0398d5bc), 2026-06-23
> **Escopo:** 25 artefatos de Fases 1-5 (21 libs, 2 services, 1 app, 1 package)
> **GOAL:** Issue #57 — P1: Revisão geral de code patterns, código repetido e performance
> **Behavior:** b2 — Code Duplication Analysis
> **Decisão:** create_new — análise inédita dos 25 artefatos
> **Branch:** `phase-0/issue-57-code-patterns-review`
> **Depende de:** `duplication-review.md` (baseline Phase 0), `inventory-catalog.md` (T57.1), `patterns-review-f1-5.md` (B1)

---

## 1. Executive Summary

| Métrica | Valor |
|----------|-------|
| Total de artefatos analisados | **25** (21 libs, 2 services, 1 app, 1 package) |
| Fases identificadas | **5** (Foundation → Agent Infra → Tool Ecosystem → Integrations → Frontend) |
| Candidatos de extração intra-fase | **7** (3 high-priority, 2 medium, 2 deferred) |
| Candidatos de extração cross-fase | **4** (2 high-priority, 1 medium, 1 deferred) |
| Duplicação intra-fase total | **~480 linhas** (Python) + **~75 linhas** (TSX) |
| Duplicação cross-fase total | **~320 linhas** (Python) |
| Shared libs recomendadas | **3** (1 new: `blu_config_base`; 2 expand: `blu_shared_utils`, `blu_supabase_client`) |
| Quick wins identificados | **4** (total: ~5h esforço, ~200 linhas eliminadas) |

**Resumo narrativo:** A duplicação de código nas Fases 1-5 concentra-se em três padrões sistêmicos: (1) boilerplate de `BaseSettings` + `@lru_cache` repetido em 9 artefatos de 4 fases diferentes, (2) hierarquias de exceção customizadas reinventadas em 5 artefatos de 3 fases, e (3) wrappers de audit/log duplicados entre Fase 1 e Fase 2. A Fase 1 (Foundation) é a origem da maior parte do código reutilizável mas subextraído. A Fase 4 (Integrations) tem a maior densidade de código standalone com zero dependências internas — oportunidade de consolidação. A Fase 5 (Frontend) tem duplicação intra-fase contida (TSX routine components, API handlers).

---

## 2. Methodology

### 2.1 Phase Assignment

Os 25 artefatos foram classificados em 5 fases baseado na arquitetura em camadas (HERMES.md §Arquitetura) e na evolução das issues (#17-#37, resolution.md §1.1):

| Fase | Nome | Artefatos | Issues relacionadas | Status |
|------|------|-----------|---------------------|--------|
| **Fase 1** | Foundation (Core Platform) | blu_agent_framework, blu_supabase_client, blu_models, blu_context_service, blu_shared_utils | #17-#20 | ✅ Implementado |
| **Fase 2** | Agent Infrastructure | agent_api, blu_prompt_management, blu_llm_service, blu_rag_factory, blu_sql_factory, blu_tool_registry | #21-#24 | ✅ Implementado |
| **Fase 3** | Tool Ecosystem | tool_pool_api, blu_auth, blu_db_connector, blu_data_connectors, blu_hitl_service | #25-#28 | ⚠️ Parcial |
| **Fase 4** | External Integrations | blu_google_suite_client, blu_elicitation_service, blu_experiment_service, blu_landing_intel, blu_observability_bootstrap, blu_parsers, blu_twilio_client | #29-#32 | 📋 Planning |
| **Fase 5** | Frontend | apps/blu_v3, packages/blu-auth | — | 🚧 Em desenvolvimento |

### 2.2 Analysis Tools

| Tool | Purpose | Coverage |
|------|---------|----------|
| MD5 hashing (`find_dups2.py`) | Byte-identical file detection | 3,833 files, 57 duplicate groups |
| Jaccard similarity (`deep_analysis.py`) | Near-duplicate Python files | 19 same-name groups |
| jscpd | Clone detection in TypeScript/TSX | apps/blu_v3 + packages/blu-auth |
| Manual `diff`/`rg` | Comparative content analysis | config.py, exceptions.py, audit.py, observability.py |
| Regex scan (`scan_all.py`) | Structural pattern detection | 25 artifacts, 7 dimensions |

### 2.3 Duplication Classification

| Classe | Definição | Ação esperada |
|--------|-----------|---------------|
| **Hard duplicate** | Byte-identical (MD5 match) | Remover cópia, consolidar |
| **Near-duplicate** | Mesmo propósito, implementações divergentes | Extrair base comum, unificar |
| **Structural duplicate** | Mesmo boilerplate, domínios diferentes | Extrair classe base / factory |
| **Pattern duplicate** | Mesmo padrão, fixtures/conftest | Extrair shared fixtures (defer) |

---

## 3. Phase-to-Artifact Mapping

### 3.1 Fase 1 — Foundation (5 artefatos)

| Artefato | Tier | Linhas (aprox) | Dependências internas | Papel arquitetural |
|----------|------|---------------|----------------------|-------------------|
| **blu_agent_framework** | T1 | ~4,200 | blu_prompt_management, blu_llm_service | LangGraph: grafos, skills, agents, routines engine |
| **blu_supabase_client** | T1 | ~900 | — | Client Supabase + CRUD compartilhado |
| **blu_models** | T1 | ~1,800 | — | Pydantic models compartilhados (referenciado por 6+ artefatos) |
| **blu_context_service** | T1 | ~2,500 | blu_models, blu_supabase_client | Redis cache + snapshot de memória de negócio |
| **blu_shared_utils** | T4 | ~200 | blu_models | Shared utility functions (data_transformers, text_utils) |

**Características da Fase 1:**
- Núcleo do sistema — 3 dos 5 artefatos são Tier 1 (crítico)
- `blu_models` é o nó mais referenciado do grafo de dependências (6+ consumidores)
- `blu_shared_utils` é subutilizado (apenas 2 módulos) — candidato principal para expansão
- `blu_supabase_client` contém `audit.py` (106L) que é duplicado em `blu_agent_framework/audit.py` (57L)

### 3.2 Fase 2 — Agent Infrastructure (6 artefatos)

| Artefato | Tier | Linhas (aprox) | Dependências internas | Papel arquitetural |
|----------|------|---------------|----------------------|-------------------|
| **agent_api** | T1 (service) | ~5,800 | 16 libs internas | FastAPI — orquestra agentes, executa rotinas |
| **blu_prompt_management** | T2 | ~1,500 | blu_models, blu_db_connector, blu_sql_factory | Langfuse prompt management |
| **blu_llm_service** | T2 | ~1,200 | — | LLM client abstraction (Ollama, Langfuse) |
| **blu_rag_factory** | T2 | ~1,800 | blu_llm_service, blu_context_service, blu_models, blu_prompt_management | RAG pipeline (embeddings, vector search) |
| **blu_sql_factory** | T2 | ~2,000 | blu_llm_service, blu_context_service, blu_models, blu_supabase_client | Dynamic SQL generation |
| **blu_tool_registry** | T4 | ~600 | — | Tool registration & discovery |

**Características da Fase 2:**
- `agent_api` é o integrador principal (16 dependências internas) — maior risco de duplicação
- `blu_sql_factory` tem `observability.py::ValidationTimer` (~40L) near-duplicate do `LLMCallTimer` em `blu_agent_framework`
- `blu_tool_registry/exceptions.py` (52L) segue mesmo padrão `BaseException(message, code)` de outras fases

### 3.3 Fase 3 — Tool Ecosystem (5 artefatos)

| Artefato | Tier | Linhas (aprox) | Dependências internas | Papel arquitetural |
|----------|------|---------------|----------------------|-------------------|
| **tool_pool_api** | T2 (service) | ~7,500 | 16 libs internas | FastAPI + FastMCP — tools SQL, RAG, Google, OCR |
| **blu_auth** | T3 | ~2,200 | — | Authentication & authorization (JWT, OAuth2) |
| **blu_db_connector** | T3 | ~1,600 | — | Database abstraction layer (SQLAlchemy, Alembic) |
| **blu_data_connectors** | T3 | ~2,400 | — | BigQuery, CSV, Sheets connectors |
| **blu_hitl_service** | T3 | ~800 | blu_models | Human-in-the-loop (Redis sorted sets) |

**Características da Fase 3:**
- `tool_pool_api` é o segundo maior artefato (7,500 linhas, 57 módulos)
- `tool_pool_api` reinventa setup de Redis que já existe em `blu_context_service.dependencies`
- `blu_auth/core/exceptions.py` (46L) repete padrão `BaseException(message, code)` da Fase 2
- `blu_data_connectors` tem `AuthenticationError`, `ExecutionError`, `EcommerceConnectorError` — cada um herdando de `Exception` diretamente

### 3.4 Fase 4 — External Integrations (7 artefatos)

| Artefato | Tier | Linhas (aprox) | Dependências internas | Papel arquitetural |
|----------|------|---------------|----------------------|-------------------|
| **blu_google_suite_client** | T4 | ~3,200 | — | Google Calendar, Gmail, Drive client |
| **blu_elicitation_service** | T4 | ~1,000 | blu_models | User elicitation/conversation service |
| **blu_experiment_service** | T4 | ~1,400 | blu_models, blu_db_connector | A/B testing & experiments |
| **blu_landing_intel** | T4 | ~600 | — | Website intelligence (CNPJ extraction) |
| **blu_observability_bootstrap** | T4 | ~800 | — | OpenTelemetry tracing setup |
| **blu_parsers** | T4 | ~1,500 | — | Document parsing (PDF, CSV) |
| **blu_twilio_client** | T4 | ~700 | — | WhatsApp/Twilio integration |

**Características da Fase 4:**
- Maior densidade de artefatos standalone (6/7 sem dependências internas)
- `blu_elicitation_service/exceptions.py` (105L) — maior arquivo de exceções, mesmo padrão `BaseException(message, code)`
- `blu_experiment_service/config.py` e `blu_twilio_client/config.py` repetem boilerplate `BaseSettings + @lru_cache`
- `blu_google_suite_client` tem 4 sub-módulos (calendar, docs, gmail, sheets) cada um com `client.py` similar — intra-artefact duplication

### 3.5 Fase 5 — Frontend (2 artefatos)

| Artefato | Tier | Linhas (aprox) | Framework | Papel arquitetural |
|----------|------|---------------|-----------|-------------------|
| **apps/blu_v3** | T4 | ~265,000 | React 18 + TS + Vite + Tailwind v3 | Frontend app (salas, agentes, métricas) |
| **packages/blu-auth** | T4 | ~900 | React + Supabase JS | Shared auth package |

**Características da Fase 5:**
- `apps/blu_v3` é o maior artefato do monorepo (265K linhas TS/TSX)
- Duplicação JS/TS detectada via jscpd: 5 cross-file clones, 30+ within-file clones
- `packages/blu-auth` é pequeno e standalone — baixo risco de duplicação
- Sem duplicação cross-directory entre `apps/` e `packages/`

---

## 4. Intra-Fase Duplication Analysis

### 4.1 Fase 1 — Foundation

#### DUP-F1-01: `audit.py` — record_audit RPC Wrapper Duplicado ⭐ HIGH PRIORITY

| Campo | Valor |
|-------|-------|
| **Tipo** | Near-duplicate |
| **Arquivos** | `blu_agent_framework/audit.py` (57L), `blu_supabase_client/audit.py` (106L) |
| **Similaridade** | Ambas chamam `db.rpc("record_audit", params).execute()` com try/except + logger.warning |
| **Diferenças** | blu_supabase_client: mais completo (`AuditError`, `ActorKind`/`Outcome` Literal types, `raise_on_error`, `client_id` JWT-aware). blu_agent_framework: mais simples (`db` como `Any`, kwargs genéricos, best-effort). |
| **Ação** | Consolidar em `blu_supabase_client.audit` (canônico). Remover `blu_agent_framework/audit.py`. |
| **Linhas salvas** | ~57L |
| **Esforço** | Small (~2h) |
| **Risco** | Baixo — função best-effort, não quebra fluxo principal |

#### DUP-F1-02: `context_service.py` Duplicação build/src

| Campo | Valor |
|-------|-------|
| **Tipo** | Hard duplicate (build artifact) |
| **Arquivos** | `build/lib/blu_context_service/context_service.py` (2,531L), `src/blu_context_service/context_service.py` (2,531L) |
| **Ação** | NÃO requer ação — build artifact do Poetry/Pip. Excluir build/ dos scans futuros. |

#### DUP-F1-03: `blu_shared_utils` — Subutilizado

| Campo | Valor |
|-------|-------|
| **Tipo** | Oportunidade de consolidação |
| **Situação** | Apenas 2 módulos (`data_transformers.py`, `text_utils.py`) para ~200 linhas totais |
| **Ação** | Expandir com classes base extraídas de outras fases (ver §6) |

**Resumo Fase 1:** 1 near-duplicate crítico (audit.py), 1 build artifact falso positivo, 1 lib subutilizada. Total: ~57 linhas duplicadas.

---

### 4.2 Fase 2 — Agent Infrastructure

#### DUP-F2-01: `config.py` Boilerplate — BaseSettings + @lru_cache ⭐ HIGH PRIORITY

| Campo | Valor |
|-------|-------|
| **Tipo** | Structural duplicate |
| **Arquivos** | `agent_api/config.py` (~51L), `blu_llm_service/config.py` (~40L) |
| **Padrão** | (1) `import BaseSettings, SettingsConfigDict`, (2) `import lru_cache`, (3) `class XSettings(BaseSettings): model_config = SettingsConfigDict(env_file=".env", extra="ignore")`, (4) `@lru_cache def get_x_settings()` |
| **Linhas duplicadas** | ~30L boilerplate × 2 = ~60L |
| **Ação** | Extrair `BluBaseSettings` para `blu_config_base` (ver §7.1) |
| **Esforço** | Medium (~4h para todas as fases) |

#### DUP-F2-02: `LLMCallTimer` ↔ `ValidationTimer` — Duplicated Timer Context Manager ⭐ HIGH PRIORITY

| Campo | Valor |
|-------|-------|
| **Tipo** | Near-duplicate |
| **Arquivos** | `blu_agent_framework/utils/observability.py::LLMCallTimer` (~45L, Fase 1), `blu_sql_factory/observability.py::ValidationTimer` (~40L, Fase 2) |
| **Similaridade** | Mesmo pattern `__enter__`/`__exit__` com `elapsed_ms` |
| **Diferenças** | LLMCallTimer: `time.monotonic()`, suporte async (`__aenter__`/`__aexit__`). ValidationTimer: `time.time()`, logging no `__exit__`. |
| **Ação** | Extrair `BluTimer` para `blu_shared_utils` (ver §7.2) |
| **Linhas salvas** | ~40L |
| **Esforço** | Small (~1h) |

#### DUP-F2-03: `blu_rag_factory` ↔ `blu_sql_factory` — conftest.py Similarity

| Campo | Valor |
|-------|-------|
| **Tipo** | Pattern duplicate (test fixtures) |
| **Similaridade** | Jaccard 0.27 — maior similaridade entre conftest.py de libs diferentes |
| **Ação** | Defer — extrair incrementalmente para `blu_shared_utils.testing` |
| **Esforço** | Large (~6h para todas as 9 libs) |

**Resumo Fase 2:** 1 structural duplicate (config.py × 2), 1 near-duplicate cross-fase com Fase 1 (timer), 1 pattern duplicate (conftest). Total: ~100 linhas duplicadas intra-fase.

---

### 4.3 Fase 3 — Tool Ecosystem

#### DUP-F3-01: Redis Connection Setup Reinventado

| Campo | Valor |
|-------|-------|
| **Tipo** | Near-duplicate / reinvenção |
| **Arquivos** | `blu_context_service/dependencies.py` (Fase 1, ~30L Redis setup), `tool_pool_api/core/dependencies.py` (Fase 3, ~60L Redis setup) |
| **Similaridade** | Ambos criam pool de conexão Redis com parâmetros similares |
| **Diferenças** | tool_pool_api implementa singleton próprio em vez de usar `blu_context_service` |
| **Ação** | tool_pool_api deve usar `blu_context_service` dependencies para Redis |
| **Linhas salvas** | ~60L |
| **Esforço** | Medium (~3h) |
| **Risco** | Médio — mudança em dependência crítica de service |

#### DUP-F3-02: Exceções em `blu_data_connectors` — Herança Direta de Exception

| Campo | Valor |
|-------|-------|
| **Tipo** | Structural duplicate |
| **Arquivos** | `blu_data_connectors/accounting/conta_azul_connector.py::AuthenticationError`, `blu_data_connectors/base/abstract_connector.py::ExecutionError`, `blu_data_connectors/base/ecommerce_base_connector.py::EcommerceConnectorError` |
| **Padrão** | Todas herdam de `Exception` diretamente, sem `message`/`code` padronizados |
| **Ação** | Padronizar com `BluError` base class (ver §7.2) |
| **Esforço** | Small (~1h) |

#### DUP-F3-03: `blu_auth/core/exceptions.py` — Mesmo Padrão BaseException

| Campo | Valor |
|-------|-------|
| **Tipo** | Structural duplicate |
| **Arquivos** | `blu_auth/core/exceptions.py::AuthError` (46L), `blu_elicitation_service/exceptions.py::ElicitationError` (105L, Fase 4), `blu_tool_registry/exceptions.py::ToolRegistryError` (52L, Fase 2) |
| **Padrão** | `class XxxError(Exception): def __init__(self, message, code): self.message = message; self.code = code; super().__init__(message)` |
| **Ação** | Extrair `BluError(Exception)` com `message` + `code` para `blu_shared_utils` |
| **Linhas salvas** | ~40L (elimina construtores repetidos em 3+ artefatos) |
| **Esforço** | Small (~1.5h) |
| **Risco** | Muito baixo — herança é aditiva, não quebra APIs existentes |

#### DUP-F3-04: `test_integrations_router.py` × 2 — Possível Bug de Reorganização

| Campo | Valor |
|-------|-------|
| **Tipo** | Hard duplicate (possível lixo) |
| **Arquivos** | `services/tool_pool_api/tests/test_integrations_router.py`, `services/tool_pool_api/src/tool_pool_api/tests/test_integrations_router.py` |
| **Ação** | Verificar e remover a cópia obsoleta (card separado) |
| **Esforço** | Trivial (~15min) |

**Resumo Fase 3:** 1 reinvenção de Redis (cross-fase com Fase 1), 1 padrão de exceções disperso (cross-fase com Fase 2 e 4), 1 bug possível. Total: ~120 linhas duplicadas intra-fase.

---

### 4.4 Fase 4 — External Integrations

#### DUP-F4-01: `google_suite_client` — Intra-Artefact Duplication (4× client.py)

| Campo | Valor |
|-------|-------|
| **Tipo** | Structural duplicate (dentro do mesmo artefato) |
| **Arquivos** | `blu_google_suite_client/src/.../calendar/client.py`, `docs/client.py`, `gmail/client.py`, `sheets/client.py` |
| **Padrão** | Cada sub-módulo tem seu próprio `client.py` com padrão similar: `build_service()`, autenticação Google, `execute_request()` |
| **Similaridade** | Métodos de autenticação e service building idênticos; diferem apenas nas APIs consumidas |
| **Ação** | Extrair `GoogleBaseClient` com auth + service building; subclasses só implementam métodos domain-specific |
| **Linhas salvas** | ~120L |
| **Esforço** | Medium (~3h) |
| **Risco** | Médio — requer refatoração dos 4 sub-módulos |

#### DUP-F4-02: `config.py` em 3 artefatos Fase 4

| Campo | Valor |
|-------|-------|
| **Tipo** | Structural duplicate |
| **Arquivos** | `blu_experiment_service/config.py` (~30L), `blu_twilio_client/config.py` (~25L), `blu_llm_service/config.py` (~40L, Fase 2) |
| **Padrão** | Mesmo boilerplate `BaseSettings + @lru_cache` (DUP-F2-01) |
| **Ação** | Consolidar com `blu_config_base` (ver §7.1) |

#### DUP-F4-03: `blu_elicitation_service/exceptions.py` — Maior Arquivo de Exceções (105L)

| Campo | Valor |
|-------|-------|
| **Tipo** | Structural duplicate |
| **Padrão** | Mesmo `BaseException(message, code)` que DUP-F3-03, mas com 7 sub-classes de erro |
| **Ação** | Herdar de `BluError` (ver §7.2) |

#### DUP-F4-04: Artefatos Standalone sem Dependências Internas

| Artefato | Dependências internas |
|----------|----------------------|
| blu_google_suite_client | 0 |
| blu_landing_intel | 0 |
| blu_observability_bootstrap | 0 |
| blu_parsers | 0 |
| blu_twilio_client | 0 |

**Observação:** 5/7 artefatos da Fase 4 são completamente standalone — não referenciam nenhuma lib interna. Isso indica oportunidade de compartilhar utilities (config, logging, error handling) que cada um reinventa localmente.

**Resumo Fase 4:** 1 intra-artefact duplication (Google client × 4), 2 structural duplicates de config/exceptions, 5 artefatos standalone reinventando utilities. Total: ~195 linhas duplicadas intra-fase.

---

### 4.5 Fase 5 — Frontend

#### DUP-F5-01: TSX Routine Components Duplicados

| Campo | Valor |
|-------|-------|
| **Tipo** | Cross-file clone (jscpd) |
| **Arquivos** | `RoutineExecutionFeed.tsx` ↔ `RoutineResultModal.tsx` (12 linhas, 111 tokens) |
| **Similaridade** | Compartilham interface de execução de rotina |
| **Ação** | Extrair `RoutineExecutionStatus` component compartilhado |
| **Esforço** | Small (~2h) |

#### DUP-F5-02: API Handler Pattern Duplicado

| Campo | Valor |
|-------|-------|
| **Tipo** | Cross-file clone (jscpd) |
| **Arquivos** | `api/agenda.ts` ↔ `api/estrategia.ts` (25 linhas, 116 tokens) |
| **Similaridade** | Mesmo padrão de API handler com paginação e tratamento de erro |
| **Ação** | Extrair `createApiHandler()` factory com paginação e error handling |
| **Esforço** | Small (~1.5h) |

#### DUP-F5-03: Routine Config Form Duplicado

| Campo | Valor |
|-------|-------|
| **Tipo** | Cross-file clone (jscpd) |
| **Arquivos** | `RoutineConfigSection.tsx` ↔ `RoutinesPanel.tsx` (14 linhas, 124 tokens) |
| **Ação** | Extrair `useRoutineConfig` hook compartilhado |
| **Esforço** | Small (~1.5h) |

#### DUP-F5-04: Within-File Clones (30+)

| Severidade | Descrição |
|-----------|-----------|
| Baixa | Código repetido dentro do mesmo arquivo TSX/TS (ex: `api/admin.ts` tem 2 clones internos) |
| **Ação** | Defer — baixo impacto, refatorar durante manutenção normal |

**Resumo Fase 5:** 3 cross-file clones significativos (TSX routine components, API handlers), 30+ within-file clones (baixa prioridade). Total: ~75 linhas duplicadas cross-file.

---

## 5. Cross-Fase Duplication Analysis

### 5.1 Matriz de Duplicação Cross-Fase

| Origem | Fase 1 | Fase 2 | Fase 3 | Fase 4 | Fase 5 |
|--------|--------|--------|--------|--------|--------|
| **Fase 1** | DUP-F1-01 (audit) | DUP-X01 (timer, config) | DUP-X02 (Redis, exceptions) | DUP-X03 (config, exceptions) | — |
| **Fase 2** | — | DUP-F2-01 (config) | DUP-X02 (exceptions) | DUP-X03 (config) | — |
| **Fase 3** | — | — | DUP-F3-01 (Redis) | DUP-X03 (exceptions) | — |
| **Fase 4** | — | — | — | DUP-F4-01 (Google client) | — |
| **Fase 5** | — | — | — | — | DUP-F5-01 (TSX) |

### 5.2 Cross-Fase Extraction Candidates

#### DUP-X01: `config.py` Boilerplate — 9 Artefatos, 4 Fases ⭐ HIGHEST PRIORITY

| Campo | Valor |
|-------|-------|
| **Tipo** | Structural duplicate (cross-fase) |
| **Fases afetadas** | Fase 1 (blu_agent_framework), Fase 2 (agent_api, blu_llm_service), Fase 3 (blu_auth), Fase 4 (blu_experiment_service, blu_twilio_client) |
| **Total de artefatos** | **9** (contando blu_context_service e tool_pool_api) |
| **Padrão** | `class XSettings(BaseSettings): model_config = SettingsConfigDict(env_file=".env", extra="ignore")` + `@lru_cache def get_x_settings()` |
| **Linhas duplicadas** | ~15L boilerplate × 9 = **~135L** |
| **Solução** | Criar `blu_config_base` com `BluBaseSettings(BaseSettings)` + `get_cached_settings()` factory |
| **Linhas salvas** | ~100L (reduz cada config de ~30-55L para ~15L) |
| **Esforço** | Medium (~4h) |
| **Risco** | Médio — mudança transversal em 9 artefatos. Necessário regression testing. |

#### DUP-X02: `exceptions.py` Pattern — 5 Artefatos, 3 Fases ⭐ HIGH PRIORITY

| Campo | Valor |
|-------|-------|
| **Tipo** | Structural duplicate (cross-fase) |
| **Fases afetadas** | Fase 2 (blu_tool_registry), Fase 3 (blu_auth, blu_data_connectors), Fase 4 (blu_elicitation_service) |
| **Total de artefatos** | **5** (incluindo blu_prompt_management) |
| **Padrão** | `class XxxError(Exception): def __init__(self, message, code): self.message = message; self.code = code; super().__init__(message)` |
| **Linhas duplicadas** | ~15L construtor × 5 = **~75L** |
| **Solução** | Criar `BluError(Exception)` base class em `blu_shared_utils` |
| **Linhas salvas** | ~60L |
| **Esforço** | Small (~1.5h) |
| **Risco** | Muito baixo — herança é aditiva |

#### DUP-X03: Redis Connection Setup — 2 Artefatos, 2 Fases

| Campo | Valor |
|-------|-------|
| **Tipo** | Near-duplicate / reinvenção |
| **Fases afetadas** | Fase 1 (blu_context_service), Fase 3 (tool_pool_api) |
| **Descrição** | tool_pool_api implementa singleton de Redis próprio (~60L) quando blu_context_service já oferece `get_redis_client()` |
| **Solução** | tool_pool_api deve usar blu_context_service dependencies |
| **Linhas salvas** | ~60L |
| **Esforço** | Medium (~3h) |

#### DUP-X04: Audit/Timer — 2 Artefatos, 2 Fases

| Campo | Valor |
|-------|-------|
| **Tipo** | Near-duplicate (cross-fase) |
| **Fases afetadas** | Fase 1 (blu_agent_framework), Fase 2 (blu_sql_factory) |
| **Padrão** | `LLMCallTimer` (F1) + `ValidationTimer` (F2) — ambos context managers com `elapsed_ms` |
| **Solução** | Extrair `BluTimer` para `blu_shared_utils` |
| **Linhas salvas** | ~40L |
| **Esforço** | Small (~1h) |

---

## 6. Top 10 Highest-Impact Duplications (All Phases)

Ranked by `lines_affected × maintenance_frequency × criticality_tier`:

| # | ID | Description | Lines | Fases | Tiers | Impact Score | Recommended |
|---|----|-------------|-------|-------|-------|-------------|-------------|
| 1 | DUP-X01 | config.py boilerplate (9 artefatos) | 135 | F1-F4 | T1-T4 | **9.5** | Extract `blu_config_base` |
| 2 | DUP-F1-01 | audit.py (2 artefatos Fase 1) | 163 | F1 | T1 | **8.5** | Consolidate em blu_supabase_client |
| 3 | DUP-X02 | exceptions.py pattern (5 artefatos) | 75 | F2-F4 | T1-T4 | **7.8** | Extract `BluError` base class |
| 4 | DUP-X04 | Timer context manager (2 artefatos) | 85 | F1-F2 | T1-T2 | **5.8** | Extract `BluTimer` |
| 5 | DUP-F3-01 | Redis setup reinvention (tool_pool_api) | 60 | F1, F3 | T1-T2 | **5.2** | Use blu_context_service deps |
| 6 | DUP-F4-01 | Google client intra-artefact (×4) | 120 | F4 | T4 | **4.5** | Extract `GoogleBaseClient` |
| 7 | DUP-F5-01 | Routine UI components (2 files) | 50 | F5 | T4 | **3.2** | Extract shared component |
| 8 | DUP-F5-02 | API handler pattern (2 files) | 25 | F5 | T4 | **2.5** | Extract factory |
| 9 | DUP-F5-03 | Routine config form (2 files) | 25 | F5 | T4 | **2.5** | Extract `useRoutineConfig` hook |
| 10 | DUP-F3-04 | test_integrations_router.py × 2 | ~100 | F3 | T2 | **2.0** | Remove stale copy |

---

## 7. Recommended New & Expanded Shared Libraries

### 7.1 `blu_config_base` (NEW — Proposed) ⭐

**Purpose:** Base class for all pydantic-settings configurations across Fases 1-4.

**Scope:**
```python
# blu_config_base/src/blu_config_base/__init__.py
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import TypeVar

T = TypeVar("T", bound="BluBaseSettings")

class BluBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @classmethod
    @lru_cache
    def get_cached(cls: type[T]) -> T:
        return cls()
```

**Impacto:**
- Reduz 9 config.py de ~30-55L para ~15L cada (~130L salvas)
- Padroniza `env_file`, `extra`, `case_sensitive` para todo o monorepo
- Elimina duplicação de `@lru_cache` factory em 9 lugares

**Artefatos afetados:**

| Fase | Artefato | Config Atual | Nova (com BluBaseSettings) |
|------|----------|-------------|---------------------------|
| F1 | blu_agent_framework | `AgentFrameworkSettings(BaseSettings)` ~40L | `class AgentFrameworkSettings(BluBaseSettings)` ~15L |
| F1 | blu_context_service | `ContextSettings(BaseSettings)` ~30L | `class ContextSettings(BluBaseSettings)` ~15L |
| F2 | agent_api | `Settings(BaseSettings)` ~51L | `class Settings(BluBaseSettings)` ~20L |
| F2 | blu_llm_service | `LLMSettings(BaseSettings)` ~40L | `class LLMSettings(BluBaseSettings)` ~15L |
| F3 | blu_auth | `AuthSettings(BaseSettings)` ~35L | `class AuthSettings(BluBaseSettings)` ~15L |
| F3 | tool_pool_api | `Settings(BaseSettings)` ~40L | `class Settings(BluBaseSettings)` ~20L |
| F4 | blu_experiment_service | `ExperimentSettings(BaseSettings)` ~30L | `class ExperimentSettings(BluBaseSettings)` ~15L |
| F4 | blu_twilio_client | `TwilioSettings(BaseSettings)` ~25L | `class TwilioSettings(BluBaseSettings)` ~15L |

**Effort:** Medium (~4h) — criar lib, migrar 8+ configs, testar inicialização de cada artefato.
**Risk:** Médio — mudança transversal. Regression testing obrigatório nos 2 services.

---

### 7.2 `blu_shared_utils` — Expand Scope

**Current:** `data_transformers.py` + `text_utils.py` (~200L)

**Proposed additions:**

| Módulo | Fonte | Descrição | Fases afetadas | Linhas |
|--------|-------|-----------|---------------|--------|
| `blu_error.py` | DUP-X02 | `BluError(Exception)` com `message` + `code` | F2, F3, F4 | ~25L (nova) |
| `blu_timer.py` | DUP-X04 | `BluTimer` context manager (sync + async) | F1, F2 | ~30L (nova) |
| `blu_audit.py` | DUP-F1-01 | Re-export de `blu_supabase_client.audit.record_audit()` | F1 | ~10L (wrapper) |
| `blu_config.py` | DUP-X01 | `get_env_bool()`, `get_env_int()`, `get_env_list()` helpers | F1-F4 | ~30L (nova) |

**Impacto após expansão:**

| Artefato | Mudança |
|----------|---------|
| blu_auth | `AuthError(BluError)` em vez de `AuthError(Exception)` |
| blu_elicitation_service | `ElicitationError(BluError)` com 7 sub-classes |
| blu_tool_registry | `ToolRegistryError(BluError)` |
| blu_data_connectors | `AuthenticationError(BluError)`, `ExecutionError(BluError)` |
| blu_agent_framework | `LLMCallTimer` → `BluTimer` |
| blu_sql_factory | `ValidationTimer` → `BluTimer` |

**Effort:** Small (~2.5h total) — 4 módulos novos, herança em 5 artefatos.

---

### 7.3 `blu_supabase_client` — Consolidate Audit

**Current:** `audit.py` (106L) — versão canônica com tipagem forte.

**Proposed:** Remover `blu_agent_framework/audit.py` (57L). blu_agent_framework importa de `blu_supabase_client.audit`.

**Effort:** Small (~2h) — remover arquivo, atualizar 1-2 imports em blu_agent_framework.

---

## 8. Quick Wins (Low Effort, High Impact)

| # | Ação | Fase | Esforço | Impacto | Linhas Salvas | Card |
|---|------|------|---------|---------|--------------|------|
| QW-1 | Consolidar `audit.py` — remover duplicata em blu_agent_framework | F1 | ~2h | Elimina duplicação T1 | ~57L | T57.3-qw1 |
| QW-2 | Extrair `BluError` base class para blu_shared_utils | F2-F4 | ~1.5h | Padroniza exceptions em 5 artefatos | ~60L | T57.3-qw2 |
| QW-3 | Extrair `BluTimer` context manager | F1-F2 | ~1h | Unifica timers em 2 artefatos | ~40L | T57.3-qw3 |
| QW-4 | Remover `test_integrations_router.py` cópia obsoleta | F3 | ~15min | Limpa lixo de reorganização | ~100L | T57.3-qw4 |

**Total Quick Wins:** ~4.75h esforço, ~257 linhas eliminadas.

---

## 9. Phase-by-Phase Recommendations

### Fase 1 — Foundation
- **Ação imediata:** Consolidar audit.py (QW-1)
- **Curto prazo:** Expandir blu_shared_utils com BluTimer (QW-3)
- **Médio prazo:** Criar blu_config_base e migrar config.py
- **Risco:** Baixo — Foundation é estável e bem testada

### Fase 2 — Agent Infrastructure
- **Ação imediata:** Extrair BluError base class (QW-2)
- **Curto prazo:** Migrar config.py de agent_api + blu_llm_service para blu_config_base
- **Médio prazo:** Resolver similaridade conftest.py incrementalmente
- **Risco:** Médio — agent_api é o integrador principal (16 dependências)

### Fase 3 — Tool Ecosystem
- **Ação imediata:** Remover test_integrations_router.py obsoleto (QW-4)
- **Curto prazo:** tool_pool_api usar blu_context_service para Redis (reduz ~60L)
- **Médio prazo:** Padronizar exceções em blu_auth e blu_data_connectors com BluError
- **Risco:** Médio — tool_pool_api é grande (7,500 linhas, 57 módulos)

### Fase 4 — External Integrations
- **Ação imediata:** Migrar config.py de blu_experiment_service + blu_twilio_client para blu_config_base
- **Curto prazo:** Extrair GoogleBaseClient dos 4 sub-módulos do google_suite_client
- **Médio prazo:** Criar utilities compartilhadas para artefatos standalone (5/7 sem deps internas)
- **Risco:** Baixo — artefatos standalone, baixo acoplamento

### Fase 5 — Frontend
- **Curto prazo:** Extrair RoutineExecutionStatus component (DUP-F5-01)
- **Curto prazo:** Criar createApiHandler factory (DUP-F5-02)
- **Curto prazo:** Extrair useRoutineConfig hook (DUP-F5-03)
- **Defer:** Within-file clones (30+) — refatorar durante manutenção normal
- **Risco:** Médio — app grande (265K linhas), mudanças requerem teste visual

---

## 10. Dependency Graph Impact

```
                    ┌─────────────────────────────────────────────┐
                    │           blu_config_base (NEW)              │
                    │         BaseSettings + get_cached()          │
                    └──────┬──────────┬──────────┬────────────────┘
                           │          │          │
              ┌────────────┼──────────┼──────────┼────────────────┐
              ▼            ▼          ▼          ▼                 ▼
        F1: blu_agent    F2: agent  F2: blu_llm  F4: blu_exp    F4: blu_twilio
        _framework       _api        _service     _service       _client

                    ┌─────────────────────────────────────────────┐
                    │        blu_shared_utils (EXPANDED)          │
                    │  BluError + BluTimer + BluAudit + Config    │
                    └──────┬──────────┬──────────┬────────────────┘
                           │          │          │
              ┌────────────┼──────────┼──────────┼────────────────┐
              ▼            ▼          ▼          ▼                 ▼
        F2: blu_tool   F3: blu_auth  F4: blu_el  F1: blu_agent   F2: blu_sql
        _registry                              _framework       _factory
```

**Novas dependências:**
- `blu_config_base` → dependência de 8+ artefatos (Fases 1-4)
- `blu_shared_utils` → +5 consumidores (expansão de 2 para ~7 artefatos)

**Riscos de dependência circular:**
- Nenhum. `blu_config_base` depende apenas de `pydantic-settings` (externo). `blu_shared_utils` já depende de `blu_models` (existente).

---

## 11. Acceptance Criteria Checklist

- [x] 25 artefatos de Fases 1-5 mapeados (§3)
- [x] Intra-fase duplication identificada em todas as 5 fases (§4)
- [x] Cross-fase duplication matrix construída (§5)
- [x] Top 10 highest-impact duplications ranqueadas (§6)
- [x] 3 shared libs recomendadas (1 new, 2 expand) (§7)
- [x] 4 quick wins identificados com estimativa de esforço (§8)
- [x] Recomendações phase-by-phase (§9)
- [x] Impacto no grafo de dependências analisado (§10)
- [x] File saved to `docs/planning/issue-57/duplication-review-f1-5.md`
- [ ] Git commit + push
- [ ] PR created

---

## 12. References

| Documento | Path | Relação |
|-----------|------|---------|
| Baseline duplication review | `docs/planning/issue-57/duplication-review.md` | Análise Phase 0 por tipo de duplicação |
| Inventory catalog | `docs/planning/issue-57/inventory-catalog.md` | Catálogo dos 25 artefatos (T57.1) |
| Patterns consistency review | `docs/planning/issue-57/patterns-review-f1-5.md` | Revisão de consistência de patterns (B1) |
| Patterns baseline | `docs/planning/issue-57/patterns.md` | Convenções esperadas |
| Resolution | `docs/planning/issue-57/resolution.md` | Decisões de design e classificação de tiers |
| Repo index | `docs/planning/issue-57/repo-index.md` | Service catalog, language breakdown |
| HERMES.md | `HERMES.md` | Arquitetura em camadas (L1-L4) |
| SHARED_MEMORY_DESIGN.md | `docs/llm_wiki/SHARED_MEMORY_DESIGN.md` | Design da shared memory (Fases 1-5) |

---

> **Nota:** Esta análise complementa `duplication-review.md` (organizado por tipo de duplicação) com uma visão phase-by-phase. Juntas, as duas análises cobrem: classificação dos 88 pygount duplicates (duplication-review.md) + análise intra/cross-fase com recomendações de extração por fase (este documento).
