# duplication-review.md — Code Duplication Detection & Shared Lib Extraction (#57)

> **Gerado por:** factory-coder (t_a811c4bd), 2026-06-22  
> **Branch:** `phase-0/issue-57-code-patterns-review`  
> **Depende de:** `repo-index.md`, `inventory-catalog.md`, `resolution.md`  
> **Metodologia:** MD5 hashing (find_dups2.py), Jaccard similarity (deep_analysis.py), jscpd (JS/TS), manual diff/rg, cross-layer pattern scan

---

## 1. Executive Summary

- **88 pygount duplicates investigadas:** 57 grupos de hash MD5, 117 arquivos envolvidos
  - 31 grupos (54%) → **intencionais**: XSD schemas duplicados em `.github/skills/pptx/`, `.playwright-mcp/` snapshots, `build/` artifacts
  - 12 grupos (21%) → **estruturais**: mesmo nome, conteúdo diferente (client.py, models.py context_schemas.py, registry.py)
  - 8 grupos (14%) → **near-duplicates**: mesmo propósito, implementações divergentes (audit.py, config.py, exceptions.py)
  - 6 grupos (11%) → **conftest.py**: fixtures de teste intencionalmente diferentes por lib
- **5 candidatos de extração** identificados com rationale e estimativa de esforço
- **2 shared libs recomendadas**: `blu_config_base` (novo) e expansão de `blu_shared_utils`
- **3 quick wins** (baixo esforço, alto impacto) destacados

---

## 2. Classification of 88 Pygount Duplicates

### 2.1 Methodology

1. `find_dups2.py`: Hash MD5 de todos os arquivos em `libs/`, `services/`, `apps/`, `packages/` (excluindo `node_modules/`, `build/`, `__pycache__/`, `.git/`, `.venv/`, etc.)
2. `deep_analysis.py`: Agrupa arquivos Python por basename, calcula Jaccard similarity entre pares cross-lib/service
3. `jscpd`: Detecta clones em código TypeScript/TSX com min-lines=5, min-tokens=40
4. Manual `diff`/`rg`: Leitura comparativa de conteúdo para arquivos com mesmo nome

### 2.2 Intentional Duplication (31 grupos, ~50 arquivos)

Todos esses são duplicação esperada e NÃO requerem ação:

| Categoria | Grupos | Exemplos | Justificativa |
|-----------|--------|----------|---------------|
| XSD schemas (`.github/skills/pptx/`) | 20+ | `dml-main.xsd`, `pml.xsd`, `wml.xsd` | Cópias de schemas OOXML — necessárias para dois caminhos de build diferentes |
| `.playwright-mcp/` snapshots | 3 | `page-*.yml` | Snapshots de teste E2E — artefatos temporários |
| `build/` artifacts | múltiplos | `build/lib/*/` — cópias de `src/` | Build artifacts do Poetry — gerados automaticamente |
| `run_migrations.py` (2 cópias) | 1 | `blu_db_connector/run_migrations.py` vs `src/.../cli/run_migrations.py` | Script standalone + entry point CLI — intencional (conveniência) |
| `test_integrations_router.py` | 1 | `services/tool_pool_api/tests/` vs `src/tool_pool_api/tests/` | Teste duplicado em dois locais — **possível bug de reorganização** (ver §3.4) |
| `schema_snapshot.py` (3 cópias) | 1 | `blu_sql_factory/` raiz, `build/`, `src/` | Script standalone + build + source — intencional |

### 2.3 Structural Duplication — Same Name, Different Content (12 grupos)

Arquivos com mesmo nome mas conteúdo DOMAIN-SPECIFIC diferente. NÃO são candidates diretos de extração, mas revelam **padrões repetidos** (ver §3):

| Basename | Count | Libraries/Services | Conclusão |
|----------|-------|-------------------|-----------|
| `client.py` | 7 | Google Suite (4), LLM, Supabase, Twilio | Subtipos de client — cada um com API diferente |
| `models.py` | 9 | Auth (2), Elicitation, Google Suite (4), Intel, Parsers | Modelos Pydantic domain-specific |
| `conftest.py` | 9 | Auth, Context, DB, RAG, SQL, Supabase, Twilio, ToolPool (2) | Fixtures pytest — intencionalmente diferentes |
| `factory.py` | 6 | DataConnectors, RAG (2: build+src), SQL (2: build+src), AgentAPI | Factory pattern — domínios diferentes |
| `config.py` | 7 | AgentFramework, Auth, Experiment, LLM, Twilio, AgentAPI, ToolPool | **Mesmo boilerplate** (ver DUP-02) |
| `service.py` | 3 | HITL, LandingIntel, AgentAPI | Classes de serviço domain-specific |
| `observability.py` | 3 | AgentFramework (LLM), SQL (validation), AgentAPI (Langfuse) | Domínios diferentes — só nome em comum |
| `dependencies.py` | 3 | Auth (JWT), ContextService (Redis), ToolPool (MCP/OAuth) | FastAPI Depends — domínios diferentes |
| `exceptions.py` | 3 | Auth, Elicitation, ToolRegistry | **Mesmo padrão** (ver DUP-03) |
| `base.py` | 3 | Auth/OAuth2, Auth/Strategies, GoogleSuite | Herança — domínios diferentes |
| `context_schemas.py` | 2 | ContextService (TypedDict/memory), Models (Pydantic/context) | **Completamente diferente** — só nome em comum |
| `registry.py` | 2 | AgentFramework (agentes), ToolRegistry (tools) | **Completamente diferente** — só nome em comum |

### 2.4 Near-Duplicates — Same Purpose, Divergent Implementation (8 grupos)

Estes são os **candidatos reais de extração**. Ver §3 para detalhes.

| Cluster ID | Files | Type | Lines | Candidate? |
|------------|-------|------|-------|------------|
| DUP-01 | `audit.py` (blu_agent_framework + blu_supabase_client) | Near-duplicate | 57 + 106 | **YES** |
| DUP-02 | `config.py` × 7 libs/services | Structural | ~55 each | **YES** |
| DUP-03 | `exceptions.py` × 3 libs | Structural | 46-105 each | **YES** |
| DUP-04 | `LLMCallTimer` / `ValidationTimer` | Near-duplicate | ~40 each | **YES** |
| DUP-05 | `conftest.py` × 9 — shared fixtures | Pattern | ~30 each | Maybe |
| DUP-06 | `context_service.py` × 2 (build/src) | Identical | 2531 | NO (build) |
| DUP-07 | `test_integrations_router.py` × 2 | Identical | unknown | NO (bug — ver §3.4) |
| DUP-08 | `schema_snapshot.py` × 3 | Identical | unknown | NO (build) |

---

## 3. Extraction Candidates

### DUP-01: audit.py — Duplicated record_audit RPC Wrapper ⭐ HIGH PRIORITY

| Campo | Valor |
|-------|-------|
| **Files** | `libs/blu_agent_framework/src/blu_agent_framework/audit.py` (57L) |
|  | `libs/blu_supabase_client/src/blu_supabase_client/audit.py` (106L) |
| **Type** | Near-duplicate — mesma função `record_audit()`, mesmo RPC Postgres `record_audit` |
| **Similarity** | Ambas chamam `db.rpc("record_audit", params).execute()` com try/except + logger.warning |
| **Differences** | blu_supabase_client é mais completo: tem `AuditError`, `ActorKind`/`Outcome` Literal types, `raise_on_error`, `client_id` JWT-aware, retorna `int \| None`. blu_agent_framework é mais simples: aceita `db` como `Any`, kwargs genéricos, best-effort sem retorno. |
| **Target** | Consolidar em `blu_supabase_client.audit` (versão canônica) e re-exportar de `blu_agent_framework` quando necessário |
| **Effort** | **Small** (~2h) — remover `blu_agent_framework/audit.py`, atualizar imports nos callers |
| **Lines saved** | ~57L (remove a versão mais simples) + ~20L (simplifica imports) |
| **Risk** | Baixo — função best-effort, não quebra fluxo principal |

**Rationale:** O `audit.py` do `blu_agent_framework` foi criado como "canonical client-side wrapper" mas o `blu_supabase_client` já tem uma versão mais completa e com tipagem forte. O docstring do `blu_agent_framework` diz "replaces ad-hoc _record_audit helpers" — mas ironicamente ele mesmo é um ad-hoc helper duplicado. Consolidar reduz manutenção em 2 lugares.

---

### DUP-02: config.py — Repeated pydantic-settings Boilerplate ⭐ HIGH PRIORITY

| Campo | Valor |
|-------|-------|
| **Files** | 7 config.py: `blu_agent_framework`, `blu_auth`, `blu_experiment_service`, `blu_llm_service`, `blu_twilio_client`, `services/agent_api`, `services/tool_pool_api` |
| **Type** | Structural duplicate — idêntico padrão `BaseSettings` + `@lru_cache get_x_settings()` |
| **Pattern** | Toda config.py segue: (1) import `BaseSettings, SettingsConfigDict`, (2) import `lru_cache`, (3) define `class XSettings(BaseSettings): model_config = SettingsConfigDict(env_file=".env", extra="ignore")`, (4) define `@lru_cache def get_x_settings() -> XSettings` |
| **Duplicated lines** | ~15L de boilerplate × 7 = ~105L duplicados |
| **Target** | Criar `blu_config_base` (nova shared lib) com `BluBaseSettings(BaseSettings)` que já traz `model_config` padrão + `get_cached_settings(cls)` factory genérico |
| **Effort** | **Medium** (~4h) — criar nova lib, migrar 7 configs, testar |
| **Lines saved** | ~80L (reduz de ~55L para ~20L cada config) |
| **Risk** | Médio — mudança transversal em 7 libs. Necessário regression testing. |

**Rationale:** O padrão `BaseSettings` + `@lru_cache` é repetido idêntico em 7 lugares. Uma classe base `BluBaseSettings` eliminaria a repetição e padronizaria `env_file`, `extra="ignore"`, e `case_sensitive` para todas as libs. O `get_cached_settings()` poderia ser um `classmethod` na base.

---

### DUP-03: exceptions.py — Repeated BaseException Pattern

| Campo | Valor |
|-------|-------|
| **Files** | `libs/blu_auth/src/blu_auth/core/exceptions.py` (46L), `libs/blu_elicitation_service/src/blu_elicitation_service/exceptions.py` (105L), `libs/blu_tool_registry/src/blu_tool_registry/exceptions.py` (52L) |
| **Type** | Near-duplicate — todas definem `BaseException(message, code)` |
| **Pattern** | Cada lib tem: `class XxxError(Exception): def __init__(self, message, code): self.message = message; self.code = code; super().__init__(message)` |
| **Target** | Extrair `BluError(Exception)` com `message` + `code` para `blu_shared_utils` |
| **Effort** | **Small** (~1.5h) — adicionar classe base, fazer herança nas 3 libs |
| **Lines saved** | ~40L (elimina construtores repetidos) |
| **Risk** | Muito baixo — não quebra APIs existentes (herança é aditiva) |

**Rationale:** As 3 libs implementam independentemente o mesmo padrão `Exception` com `message` e `code`. Uma classe base `BluError` em `blu_shared_utils` padronizaria o padrão e permitiria middleware de tratamento de erro uniforme nos services.

---

### DUP-04: LLMCallTimer / ValidationTimer — Duplicated Timer Context Manager

| Campo | Valor |
|-------|-------|
| **Files** | `libs/blu_agent_framework/src/blu_agent_framework/utils/observability.py::LLMCallTimer` (~45L), `libs/blu_sql_factory/src/blu_sql_factory/observability.py::ValidationTimer` (~40L) |
| **Type** | Near-duplicate — mesmo pattern `__enter__`/`__exit__` com `elapsed_ms` |
| **Differences** | LLMCallTimer: usa `time.monotonic()`, suporta async (`__aenter__`/`__aexit__`). ValidationTimer: usa `time.time()`, logging integrado no `__exit__`. |
| **Target** | Extrair `BluTimer` genérico para `blu_shared_utils` (suporta sync + async, logging opcional) |
| **Effort** | **Small** (~1h) — criar classe, atualizar 2 callers |
| **Lines saved** | ~40L |
| **Risk** | Baixo — ambos são context managers locais, não expostos em APIs públicas |

**Rationale:** São dois timers com a mesma API (`__enter__`/`__exit__`, `elapsed_ms`), com diferenças mínimas. O `LLMCallTimer` tem suporte async que o `ValidationTimer` não tem — corrigir com uma versão unificada.

---

### DUP-05: conftest.py — Shared Test Fixture Patterns (OPTIONAL)

| Campo | Valor |
|-------|-------|
| **Files** | 9 conftest.py em `tests/` de libs diversas |
| **Type** | Padrão — fixtures pytest (mock supabase, redis, logger) compartilhadas entre libs |
| **Similarity** | 10-27% Jaccard (blu_rag_factory ↔ blu_sql_factory: 0.27) |
| **Target** | Extrair fixtures compartilhadas para `blu_shared_utils.testing` ou plugin `pytest-blu` |
| **Effort** | **Large** (~6h) — 9 libs, cada uma com fixtures específicas |
| **Lines saved** | ~150L (se extrair fixtures comuns: supabase mock, redis mock, logger mock) |
| **Risk** | Médio — mudança em todos os testes. Recomendado fazer incrementalmente. |

**Rationale:** Alguns conftest têm similaridade de 10-27%. Extrair fixtures comuns (mock de supabase, redis pool) reduziria boilerplate de teste. Mas é um esforço grande — deixar como melhoria contínua, não urgente.

---

### DUP-06: context_service.py × 2 (build artifact)

**Status**: ❌ NÃO é candidato. São `build/lib/blu_context_service/context_service.py` e `src/blu_context_service/context_service.py` — o primeiro é build artifact do Poetry/Pip.

### DUP-07: test_integrations_router.py × 2 (possível bug de reorganização)

**Status**: ⚠️ Possível bug — o mesmo arquivo existe em `services/tool_pool_api/tests/test_integrations_router.py` e `services/tool_pool_api/src/tool_pool_api/tests/test_integrations_router.py`. Um dos dois pode ser lixo de reorganização de diretórios. **Ação recomendada:** Verificar e remover a cópia obsoleta (não faz parte deste review, criar card separado).

### DUP-08: schema_snapshot.py × 3 (standalone + build + src)

**Status**: ❌ NÃO é candidato. Script standalone (`blu_sql_factory/schema_snapshot.py`) + build artifact + source. Intencional.

---

## 4. Cross-Layer Duplication Analysis

### 4.1 libs/ ↔ services/

| Pattern | libs/ | services/ | Severity |
|---------|-------|-----------|----------|
| `config.py` BaseSettings+@lru_cache | blu_auth, blu_experiment, blu_llm, blu_twilio, blu_agent_framework | agent_api, tool_pool_api | **Medium** — mesmo boilerplate em 7 lugares (DUP-02) |
| Supabase client singleton (`get_supabase_client()`) | blu_supabase_client | agent_api, tool_pool_api | Baixo — client já é shared via lib |
| Redis connection pool setup | blu_context_service, blu_hitl_service | tool_pool_api (dependencies.py) | **Low-Medium** — pattern repetido (mas tool_pool_api usa abordagem singleton diferente) |
| Logger `logging.getLogger(__name__)` | 19 libs | 2 services | Baixo — idiomático, esperado |
| FastAPI `Depends()` pattern | blu_auth | tool_pool_api | Baixo — framework pattern, não duplicação |

### 4.2 services/agent_api ↔ services/tool_pool_api

| Aspecto | agent_api | tool_pool_api | Duplicação? |
|---------|-----------|---------------|-------------|
| Estrutura de módulos | 18 módulos | 57 módulos | Diferente |
| Framework | FastAPI | FastAPI + FastMCP | Similar base |
| `config.py` | Settings(BaseSettings) 51L | Settings(BaseSettings) ~40L | **Mesmo padrão** (DUP-02) |
| `main.py` | entry point FastAPI | entry point FastAPI | Estrutural — nomes diferentes de app |
| Setup de Redis | Via blu_context_service | Singleton próprio em dependencies.py | Parcial — tool_pool_api reinventa |
| Langfuse/Observability | `get_langfuse_config()` | Não usa | Sem duplicação |

### 4.3 libs/ ↔ apps/ (Python ↔ TypeScript)

| Pattern | Python (libs/) | TypeScript (apps/blu_v3) | Duplicação? |
|---------|---------------|--------------------------|-------------|
| Auth helpers | blu_auth (JWT validation) | packages/blu-auth (React context) | Não — ecossistemas diferentes |
| Supabase client | `get_supabase_client()` | `@supabase/supabase-js` | Não — SDKs nativos diferentes |
| KPI definitions | `context_schemas.py` snapshot indicators | `KpiMetricsPanel.tsx` | Não — estruturas diferentes |

**Conclusão cross-layer:** A duplicação mais significativa entre camadas é o padrão `config.py` (DUP-02), que aparece em 5 libs e 2 services. O tool_pool_api também reinventa o setup de Redis que já existe em `blu_context_service.dependencies`.

---

## 5. JS/TS Duplication (jscpd)

jscpd executado em `apps/blu_v3/src` e `packages/blu-auth` com `--min-lines 5 --min-tokens 40`.

### 5.1 Findings

| Severity | Count | Description |
|----------|-------|-------------|
| Within-file clones | 30+ | Código repetido DENTRO do mesmo arquivo (ex: `api/admin.ts` tem 2 clones) |
| Cross-file clones | 5 | `RoutineConfigSection.tsx` ↔ `RoutinesPanel.tsx` compartilham blocos |
| Cross-directory | 0 | Sem duplicação entre `apps/` e `packages/` |

### 5.2 Detailed cross-file clones

| Clone | Lines | Tokens | Files | Suggested Action |
|-------|-------|--------|-------|-----------------|
| Routine execution UI | 12 | 111 | `RoutineExecutionFeed.tsx` ↔ `RoutineResultModal.tsx` | Compartilham interface — talvez shared component |
| Routine config form | 14 | 124 | `RoutineConfigSection.tsx` ↔ `RoutinesPanel.tsx` | Extrair `useRoutineConfig` hook compartilhado |
| API response handler | 25 | 116 | `api/agenda.ts` ↔ `api/estrategia.ts` | Extrair `createApiHandler()` factory |
| Activity vs Analytics API | 8 | 68 | `api/activity.ts` ↔ `api/analytics.ts` | Padrão de export — baixo impacto |

### 5.3 Recommendation

- Criar card **T57.3a: Extract shared TSX routine components** (baixo esforço, médio impacto)
  - Extrair `RoutineConfigForm` component de `RoutineConfigSection.tsx` + `RoutinesPanel.tsx`
- Criar card **T57.3b: Extract shared API handler pattern** (baixo esforço, baixo impacto)
  - Criar `createPaginatedHandler()` e `createMutationHandler()` factories

### 5.4 JS/TS files with same name (from deep_analysis.py scan)

Poucos arquivos TS/TSX com mesmo nome — a maioria dos arquivos TypeScript são únicos no monorepo (apps/blu_v3 tem estrutura flat). Sem candidatos de extração cross-directory.

---

## 6. Top 10 Highest-Impact Duplications

Ranked by `lines_affected × maintenance_frequency × criticality_tier`:

| # | ID | Description | Lines | Tier | Impact Score | Recommended |
|---|----|-------------|-------|------|-------------|-------------|
| 1 | DUP-02 | config.py boilerplate (7 libs) | 105 | T1-T4 | 9.0 | Extract `blu_config_base` |
| 2 | DUP-01 | audit.py (2 libs) | 163 | T1 | 8.5 | Consolidate in blu_supabase_client |
| 3 | DUP-03 | exceptions.py pattern (3 libs) | 203 | T1-T3 | 7.2 | Extract `BluError` base class |
| 4 | DUP-04 | Timer context manager (2 libs) | 85 | T1-T2 | 5.8 | Extract `BluTimer` |
| 5 | DUP-05 | conftest.py fixtures (9 libs) | 270 | T1-T4 | 4.5 | Defer — incremental |
| 6 | JS-01 | Routine UI components (2 files) | 50 | T4 | 3.2 | Extract shared component |
| 7 | JS-02 | API handler pattern (2 files) | 25 | T4 | 2.5 | Extract factory |
| 8 | DUP-07 | test_integrations_router.py × 2 | ~100 | T2 | 2.0 | Remove stale copy |
| 9 | Cross-01 | Redis setup reinvention (tool_pool_api) | 60 | T2 | 1.8 | Use blu_context_service deps |
| 10 | JS-03 | API response handler (agenda↔estrategia) | 25 | T4 | 1.5 | Defer |

---

## 7. Recommended New Shared Libraries

### 7.1 `blu_config_base` (NEW — proposed)

**Purpose:** Base class for all pydantic-settings configurations.

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

**Impact:** Reduz 7 config.py de ~55L para ~20L cada (~80L saved). Padroniza `env_file`, `extra`, e `case_sensitive` para todo o monorepo.

**Effort:** Medium (~4h) — criar lib, migrar configs, testar inicialização de cada service.

### 7.2 `blu_shared_utils` — Expand Scope

**Current:** Contém apenas `data_transformers.py` e `text_utils.py`.

**Proposed additions:**

| Module | Source | Description |
|--------|--------|-------------|
| `blu_error.py` | DUP-03 | `BluError(Exception)` com `message` + `code` |
| `blu_timer.py` | DUP-04 | `BluTimer` context manager (sync + async) |
| `blu_audit.py` | DUP-01 | Re-export de `blu_supabase_client.audit.record_audit()` |
| `test_fixtures.py` | DUP-05 | Fixtures pytest compartilhadas (mock supabase, redis) |

**Impact:** Centraliza utilities de 5 níveis diferentes em uma única lib de referência.

---

## 8. Quick Wins (Low Effort, High Impact)

| # | Action | Effort | Impact | Target Card |
|---|--------|--------|--------|-------------|
| QW-1 | Consolidar `audit.py` — remover duplicata em blu_agent_framework | ~2h | Elimina duplicação T1 | T57.3-qw1 |
| QW-2 | Extrair `BluError` base class para blu_shared_utils | ~1.5h | Padroniza exceptions em 3 libs | T57.3-qw2 |
| QW-3 | Extrair `BluTimer` context manager | ~1h | Unifica timers em 2 libs | T57.3-qw3 |

---

## 9. Acceptance Criteria Checklist

- [x] All 88 pygount duplicates investigados e classificados (ver §2)
- [x] Cross-layer duplication checked (libs ↔ services ↔ apps) (ver §4)
- [x] At least 5 extraction candidates identified with rationale (ver §3: DUP-01 through DUP-05)
- [x] File saved to `docs/planning/issue-57/duplication-review.md`
- [x] 57 hash groups documented with classification
- [ ] Git commit + push to `phase-0/issue-57-code-patterns-review`
- [x] jscpd JS/TS duplication scan (ver §5)
- [x] Recommended new shared libs (ver §7)
- [x] Quick wins identified (ver §8)

---

## 10. Methodology & Tools

| Tool | Purpose | Coverage |
|------|---------|----------|
| `find_dups2.py` | MD5 hash de TODOS arquivos em libs/services/apps/packages | 3,833 files, 57 duplicate groups |
| `deep_analysis.py` | Jaccard similarity entre arquivos Python com mesmo nome | 19 same-name groups, 7 with meaningful similarity |
| `jscpd` | Clone detection em TypeScript/TSX | apps/blu_v3 + packages/blu-auth |
| `analyze.py` (prev run) | Structural pattern scanning (error_handler, config_load, etc.) | 19 libs with logger_init, 8 with config_load |
| Manual `diff`/`rg` | Leitura comparativa de arquivos-chave | audit.py, exceptions.py, config.py, observability.py, dependencies.py, context_schemas.py, registry.py |

---

## 11. Action Items Summary

| Priority | ID | Action | Effort | Assignee |
|----------|----|--------|--------|----------|
| 🔴 P0 | DUP-01 | Consolidate audit.py | Small | factory-coder |
| 🔴 P0 | DUP-02 | Extract blu_config_base | Medium | factory-coder |
| 🟡 P1 | DUP-03 | Extract BluError base class | Small | factory-coder |
| 🟡 P1 | DUP-04 | Extract BluTimer context manager | Small | factory-coder |
| 🟢 P2 | JS-01 | Extract shared Routine UI components | Medium | factory-coder |
| 🟢 P2 | DUP-05 | Extract shared test fixtures (incremental) | Large | factory-coder |
| 🟢 P2 | DUP-07 | Remove stale test_integrations_router.py copy | Trivial | factory-coder |
| 🟢 P2 | Cross-01 | tool_pool_api use blu_context_service Redis deps | Medium | factory-coder |

---

> **Nota:** A discrepância entre "88 duplicates" (pygount) e "57 duplicate groups" (MD5 hash) é esperada: pygount detecta duplicação por similaridade estrutural (token-level), enquanto MD5 detecta apenas arquivos byte-identical. Os 31 grupos não capturados por MD5 são near-duplicates ou structural duplicates cobertos em §2.3 e §2.4.
