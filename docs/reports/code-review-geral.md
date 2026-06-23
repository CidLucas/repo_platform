# Code Review Geral — repo_platform

> **Gerado por:** factory-coder (t_f572c42), 2026-06-22
> **Fonte:** Consolidação de T57.1–T57.7 (inventory, patterns, duplication, performance, security, error handling, test coverage)
> **Branch:** `phase-0/issue-57-code-patterns-review`
> **Escopo:** 25 artefatos (21 libs, 2 services, 1 app, 1 package) — 23 Python, 2 TypeScript/TSX

---

## 1. Executive Summary

O codebase do repo_platform demonstra **excelente disciplina em fundamentos** (zero bare excepts, 0 camelCase em Python, 0 SQL injection, validação de entrada consistente com Pydantic/Zod) mas enfrenta **dívida técnica significativa concentrada em três áreas**: type hints (apenas 35% das funções Python são tipadas), logging inconsistente (88 chamadas de `print()` em código de produção), e ausência de resiliência de rede (sem retry/circuit breaker para Supabase e Redis nos serviços críticos).

**Métricas-chave do review consolidado:**

| Métrica | Valor |
|---|---|
| Artefatos revisados | 25 (21 libs + 2 services + 1 app + 1 package) |
| Dimensões cobertas | 7 padrões + duplicação + performance + 8 security + 11 error handling + test coverage |
| Total de findings únicos | **68** (após cross-referencing e deduplicação) |
| P0 — Imediato | **8** (3 type gaps T1 + 2 print() T1 + 1 stack trace leakage + 1 Supabase sem retry + 1 blu_models sem testes) |
| P1 — Next Sprint | **23** (logging, correlation IDs, rate limiting, CSP, code splitting, broad excepts, circuit breakers, broken tests) |
| P2 — Backlog | **37** (relative imports, any TS, documentation gaps, edge cases, test fixtures duplicadas) |
| Top 3 riscos | 1) 3 libs Tier 1 com <27% type coverage 2) Stack traces expostos via HTTPException 3) blu_models (nó central de 6 dependentes) sem testes |
| Testes executados | 785 (84.2% passing — 661 pass, 113 fail, 11 collection error) |
| Cobertura média | 38% (varia de 0% a 92% entre artefatos testados) |

**Avaliação geral:** O código é funcional e bem estruturado nos níveis de naming e estrutura de pacotes. Os problemas estão principalmente nas camadas de **resiliência operacional** (retry, circuit breaker, correlation IDs, structured logging), **segurança defensiva** (rate limiting, CSP, secrets rotation), e **qualidade de tipos** (65% das funções sem type hints). O custo total estimado de remediação é de aproximadamente **120–160 horas de engenharia**.

---

## 2. Methodology & Tools

### 2.1 Ferramentas por Dimensão

| Task | Ferramentas | Cobertura |
|---|---|---|
| T57.1 — Inventory | `os.walk`, `pyproject.toml` parsing, regex | 25 artefatos catalogados com tiers, deps, entry points |
| T57.2 — Patterns | `scan_all.py` (567 linhas), regex multi-dimensão | 7 dimensões × 25 artefatos (430KB raw JSON) |
| T57.3 — Duplication | `find_dups2.py` (MD5), `deep_analysis.py` (Jaccard), `jscpd` (JS/TS), manual `diff`/`rg` | 3,833 arquivos, 57 grupos MD5, cross-layer |
| T57.4 — Performance | `grep`, `wc -l`, SQL migration analysis, leitura direta de código | 5/5 Tier 1, 2/5 Tier 2, frontend, 35 SQL migrations |
| T57.5 — Security | `grep`/`find`, `npm audit --json`, `uv.lock` analysis, `.secrets.baseline` inspeção | 8 dimensões de segurança × 25 artefatos |
| T57.6 — Error Handling | `grep -rn` multi-pattern, leitura comparativa de código | 11 dimensões × 25 artefatos, matriz 25×11 |
| T57.7 — Test Coverage | `pytest --cov` por artefato, análise de fixtures/mocks/flaky | 15 artefatos com testes, 785 testes executados |

### 2.2 Escopo

- **Libs Python:** 21 (sob `libs/`)
- **Services FastAPI:** 2 (`services/agent_api`, `services/tool_pool_api`)
- **Apps TypeScript/TSX:** 1 (`apps/blu_v3` — React 18 + Vite + Tailwind v3)
- **Packages TypeScript:** 1 (`packages/blu-auth` — shared auth package)
- **Exclusões:** `build/`, `node_modules/`, `dist/`, `__pycache__/`, `.venv/`, `.git/`, `egg-info/`

### 2.3 Tier Classification (per resolution.md §DQ3)

| Tier | Criticality | Count | Escalation Rule |
|---|---|---|---|
| **Tier 1** | Crítico — falha bloqueia operação | 5 libs + 1 service | P1 findings → escalated to P0 |
| **Tier 2** | Alto — falha degrada funcionalidades-chave | 4 libs + 1 service | Standard |
| **Tier 3** | Médio — falha afeta features específicas | 4 libs | Standard |
| **Tier 4** | Baixo — auxiliares, UI, packages | 8 libs + 1 app + 1 package | Relaxed |

---

## 3. Per-Service Checklists

Legenda: ✅ Conforme | ⚠️ Parcial | ❌ Crítico

### 3.1 Tier 1 — Crítico

#### agent_api (Tier 1, Python, FastAPI)

| Dimensão | Status | Finding Principal |
|---|---|---|
| Types | ✅ 81% typed | Best exemplar |
| Naming | ✅ | — |
| Imports | ✅ | — |
| Structure | ⚠️ | `__init__.py` vazio (serviço FastAPI — aceitável) |
| Error Handling | ❌ P0 | `str(exc)` exposto em HTTPException (agents_router:149, chat_router:78, service.py:576,616,672) |
| Logging | ❌ P0 | 32 chamadas de `print()` em produção (T1 escalation) |
| Config | ✅ | Pydantic Settings, env vars |
| Performance | ❌ P0 | N+1 queries em `nodes.py`; schema gap `rfq_requests` |
| Performance | ⚠️ P1 | Sequential awaits (routine_functions.py:1727), HTTP in loop (:1781), monolith 3297 linhas |
| Security | ⚠️ P1 | Sem rate limiting (RATE-01) |
| Security | ⚠️ P2 | CORS localhost regex em produção (CORS-01), dev mode bypass webhook (AUTH-02) |
| Duplication | ⚠️ | config.py boilerplate (DUP-02), mesmo padrão de 7 libs |
| Tests | ❌ P0 | 6% line coverage, 20/26 passando |
| Correlation ID | ❌ | Não gera nem propaga |
| Circuit Breaker | ✅ | Routines: suspensão após 3 falhas |
| Retry | ❌ | Sem retry para Supabase |
| Broad Excepts | ⚠️ P1 | 92 `except Exception:` |
| User-Facing Lang | ⚠️ P2 | Mensagens em inglês (patterns.md exige PT-BR) |

**Score:** ❌ (4 P0) — Tipo: 81% ✅ | Logging: 32 print() ❌ | Stack trace exposure ❌ | Coverage: 6% ❌

#### blu_agent_framework (Tier 1, Python)

| Dimensão | Status | Finding Principal |
|---|---|---|
| Types | ❌ P0 | 27% typed — 240 funções sem tipo |
| Naming | ✅ | — |
| Imports | ✅ | — |
| Structure | ✅ | `__init__.py` com API pública |
| Error Handling | ✅ | Custom exceptions: ApprovalError, SkillTurnLimitError, WorkerTurnLimitError |
| Logging | ⚠️ P1 | 4 `print()` calls |
| Config | ✅ | — |
| Performance | ❌ P0 | N+1 queries em `nodes.py:961-990` (rfq_follow_up_node), N+1 updates `:901-904` (rfq_wait_node) |
| Performance | ⚠️ | Schema gap: `rfq_requests` possivelmente deprecated |
| Duplication | ⚠️ | audit.py duplicado com blu_supabase_client (DUP-01) |
| Tests | ⚠️ P1 | 38% coverage, 198/211 passando, sem conftest.py |
| Correlation ID | ✅ | `generate_correlation_id()` — único artefato com implementação |
| Circuit Breaker | ❌ | Sem (retry substitui para MCP) |
| Retry | ✅ | MCP client: exponential backoff 1s→30s |
| Broad Excepts | ⚠️ P1 | 76 `except Exception:` |

**Score:** ⚠️ (2 P0 type + 2 P0 performance) — Types: 27% ❌ | Correlation ID: ✅ | N+1 queries: ❌

#### blu_supabase_client (Tier 1, Python)

| Dimensão | Status | Finding Principal |
|---|---|---|
| Types | ❌ P0 | 23% typed — 85 funções sem tipo |
| Naming | ✅ | — |
| Imports | ⚠️ | 9 relative imports |
| Structure | ✅ | — |
| Error Handling | ⚠️ | AuditError (custom), mas sem retry para RPC/REST (P0) |
| Performance | — | N/A (client library) |
| Duplication | ⚠️ | audit.py — versão mais completa, consolidar com blu_agent_framework (DUP-01) |
| Tests | ⚠️ P2 | 58% coverage, 50/51 passando, 1 time.sleep (flaky candidate) |
| Circuit Breaker | ❌ P1 | Sem proteção contra cascata de falhas |
| Retry | ❌ P0 | Sem retry para Supabase RPC/REST |
| Broad Excepts | ⚠️ P1 | 21 `except Exception:` |

**Score:** ⚠️ (1 P0 types + 1 P0 retry) — Types: 23% ❌ | Retry: ❌

#### blu_models (Tier 1, Python)

| Dimensão | Status | Finding Principal |
|---|---|---|
| Types | ✅ 84% typed | Best exemplar |
| Naming | ✅ | — |
| Imports | ⚠️ | 42 relative imports (maior contagem — `__init__.py` exports) |
| Structure | ✅ | Pydantic/SQLModel bem estruturados |
| Error Handling | ❌ | Sem custom exception hierarchy |
| Tests | ❌ P0 | **0 testes** — nó central do grafo, 6 dependentes internos |
| Broad Excepts | ✅ | Apenas 2 `except Exception:` |

**Score:** ❌ (1 P0 tests) — Types: 84% ✅ | Tests: 0 ❌ | Dependents: 6 libs em risco

#### blu_context_service (Tier 1, Python)

| Dimensão | Status | Finding Principal |
|---|---|---|
| Types | ❌ P0 | 25% typed — 21 funções sem tipo |
| Naming | ✅ | — |
| Imports | ⚠️ | Import order quebrado (T1) |
| Structure | ✅ | — |
| Error Handling | ❌ | Sem custom exceptions |
| Logging | ✅ | PT-BR logging |
| Performance | ⚠️ P1 | Sequential snapshot: 7+ chamadas Supabase em série (context_service.py:320-730) |
| Duplication | ⚠️ | context_schemas.py tem nome igual a blu_models mas conteúdo diferente |
| Tests | ⚠️ P1 | 23% coverage, 5/12 passando, 6 falham por mudança no schema BluClientContext |
| Circuit Breaker | ❌ P1 | Sem para Redis |
| Retry | ❌ P2 | Sem para Redis |
| Correlation ID | ❌ | — |
| Broad Excepts | ⚠️ P2 | 47 `except Exception:` |

**Score:** ⚠️ (1 P0 types + 1 P1 CB) — Types: 25% ❌ | Redis CB: ❌

### 3.2 Tier 2 — Alto

#### tool_pool_api (Tier 2, Python, FastAPI + MCP)

| Dimensão | Status | Finding Principal |
|---|---|---|
| Types | ✅ 76% typed | Bom |
| Naming | ✅ | — |
| Imports | ⚠️ | Import order quebrado (2 arquivos), 42 relative imports |
| Structure | ⚠️ | `__init__.py` vazio |
| Error Handling | ❌ P1 | 181 `except Exception:`, `str(exc)` em HTTPException (:450) |
| Logging | ⚠️ P1 | 18 `print()` calls |
| Config | ✅ | — |
| Duplication | ⚠️ | config.py boilerplate (DUP-02), Redis setup reinventado (Cross-01), test_integrations_router.py ×2 (DUP-07) |
| Security | ⚠️ P1 | Shared bearer token em inbox_dispatch (AUTH-01); sem rate limiting (RATE-01) |
| Security | ⚠️ P2 | Shared static tokens sem rotação (SEC-02) |
| Performance | — | Análise delegada a scan de patterns globais |
| Tests | ❌ P1 | Coleção falha (7 arquivos, 0 executados) — dep `FileTreeStore` quebrada, 4 arquivos sem asserts |
| Correlation ID | ❌ | — |
| Circuit Breaker | ❌ | — |
| Retry | ❌ | — |

**Score:** ⚠️ (2 P1) — Tests: coleção falha ❌ | Broad excepts: 181 ❌

#### blu_llm_service (Tier 2, Python)

| Dimensão | Status | Finding Principal |
|---|---|---|
| Types | ❌ | 16% typed — 71 funções sem tipo |
| Imports | ⚠️ | Import order quebrado |
| Error Handling | ❌ | Sem custom exceptions |
| Circuit Breaker | ❌ P1 | Sem para LLM APIs |
| Retry | ✅ | Text-to-sql: max_retries=3, exponential backoff |
| Retry | ❌ | Outros paths LLM sem retry |
| Tests | ❌ P1 | Coleção falha (5 arquivos) — imports quebrados (`BluClientContext`, `sanitize_observation`) |

**Score:** ⚠️ (1 P1 types + 1 P1 CB + 1 P1 tests)

#### blu_rag_factory (Tier 2, Python)

| Dimensão | Status | Finding Principal |
|---|---|---|
| Types | ⚠️ | 32% typed |
| Error Handling | ❌ | Sem custom exceptions |
| Tests | ⚠️ P2 | 64% coverage, 50/52 passando |
| Broad Excepts | ⚠️ | 14 `except Exception:` |

**Score:** ⚠️ — Types: 32% ⚠️ | Coverage: 64% ✅

#### blu_prompt_management (Tier 2, Python)

| Dimensão | Status | Finding Principal |
|---|---|---|
| Types | ⚠️ | 22% typed |
| Error Handling | ✅ | PromptNotFoundError |
| Circuit Breaker | ✅ | Langfuse: cooldown 60s |
| Tests | ⚠️ P2 | 56% coverage, 26/28 passando |

**Score:** ⚠️ — Types: 22% ⚠️ | CB: ✅ | Coverage: 56%

#### blu_sql_factory (Tier 2, Python)

| Dimensão | Status | Finding Principal |
|---|---|---|
| Types | ❌ | 26% typed — 224 funções sem tipo |
| Imports | ⚠️ | 13 relative imports |
| Error Handling | ⚠️ | ParseError ✅, mas ValidationError não herda de Exception |
| Logging | ⚠️ P1 | 14 `print()` calls |
| Performance | ⚠️ | DUP-08: schema_snapshot.py ×3 (intencional) |
| Duplication | ⚠️ | DUP-04: ValidationTimer duplicado com LLMCallTimer |
| Tests | ⚠️ P2 | 59% coverage, 137/182 passando, 45 falhas |
| Broad Excepts | ⚠️ | 30 `except Exception:` |

**Score:** ⚠️ — Types: 26% ❌ | Tests: 45 falhas ⚠️

### 3.3 Tier 3 — Médio

#### blu_auth (Tier 3, Python)

| Dimensão | Status | Finding Principal |
|---|---|---|
| Types | ⚠️ | 38% typed |
| Error Handling | ✅ Excelente | AuthError + 7 subclasses — melhor hierarchy do codebase |
| Imports | ⚠️ | Import order quebrado, 10 relative imports |
| Duplication | ⚠️ | config.py boilerplate (DUP-02), exceptions.py (DUP-03) |
| Tests | ❌ P1 | Coleção falha (3 arquivos) — imports quebrados (`AuthRequest`, `FileTreeStore`) |
| Broad Excepts | ⚠️ | 42 `except Exception:` |

**Score:** ⚠️ — Exception hierarchy: ✅ | Tests: coleção falha ❌

#### blu_hitl_service (Tier 3, Python)

| Dimensão | Status | Finding Principal |
|---|---|---|
| Types | ⚠️ | 31% typed |
| Error Handling | ❌ | Sem custom exceptions |
| Tests | ❌ P0 | 0 testes — HITL sem cobertura |
| Broad Excepts | ⚠️ | 12 `except Exception:` |

**Score:** ❌ (1 P0 tests) — Tests: 0 ❌

#### blu_data_connectors (Tier 3, Python)

| Dimensão | Status | Finding Principal |
|---|---|---|
| Types | ⚠️ | 58% typed |
| Error Handling | ✅ | EcommerceConnectorError, RateLimitError, AuthenticationError |
| Error Handling | ⚠️ P2 | Nome duplicado: `AuthenticationError` em 2 namespaces |
| Retry | ⚠️ | RateLimitError com Retry-After header |

**Score:** ⚠️ — Types: 58% ✅ | Nome duplicado: P2

#### blu_db_connector (Tier 3, Python)

| Dimensão | Status | Finding Principal |
|---|---|---|
| Types | ⚠️ | 35% typed |
| Imports | ⚠️ | Import order quebrado |
| Error Handling | ❌ | Sem custom exceptions |
| Logging | ⚠️ P1 | 19 `print()` calls |
| Duplication | ⚠️ | run_migrations.py ×2 (intencional) |
| Tests | ⚠️ P2 | Coleção falha (1 arquivo) — imports quebrados (`TierCliente`, `TipoCliente`) |
| Broad Excepts | ⚠️ | 12 `except Exception:` |

**Score:** ⚠️ — Types: 35% ⚠️ | Tests: coleção falha P2

### 3.4 Tier 4 — Baixo

| Artefato | Lang | Types | Tests | Destaques |
|---|---|---|---|---|
| blu_elicitation_service | Python | 20% typed | 72% cov, 30/30 pass ✅ | Custom exceptions ✅ |
| blu_experiment_service | Python | 52% typed | 0 tests P2 | trace_id nos logs ✅ |
| blu_google_suite_client | Python | 69% typed ✅ | 0 tests P2 | Boa estrutura de submódulos |
| blu_landing_intel | Python | 20% typed | 0 tests P2 | — |
| blu_observability_bootstrap | Python | **100% typed** ✅ | 0 tests P2 | Structured JSON logging ✅, Circuit breaker Langfuse ✅ — referência |
| blu_parsers | Python | 38% typed | 0 tests P2 | — |
| blu_shared_utils | Python | 0% typed | 92% cov, 3/3 pass ✅ | Sem `__init__.py` P2 |
| blu_tool_registry | Python | 17% typed | 73% cov, 111/149 pass | Custom exceptions ✅, 38 falhas por enum mismatch |
| blu_twilio_client | Python | 9% typed | 72% cov, 31/31 pass ✅ | — |
| apps/blu_v3 | TS/TSX | 17 `any` P2 | 0 tests P2 | Sem code splitting P1, sem CSP P1, sem Error Boundaries P1, sem image optimization P2, 35 console.log P2 |
| packages/blu-auth | TS | 0 `any` ✅ | 0 tests P2 | npm audit: 2 high vulns |

---

## 4. Cross-Cutting Themes

### 4.1 Type Hints — 65% das funções Python sem tipo

**Métrica global:** 626/1773 funções tipadas (35%). Este é o maior gap de qualidade do codebase.

**Tier 1 críticos (<30%):**
- blu_agent_framework: 27% (240 funções sem tipo)
- blu_context_service: 25% (21 funções sem tipo)
- blu_supabase_client: 23% (85 funções sem tipo)

**Tier 2 baixos (<35%):**
- blu_llm_service: 16% (71 funções sem tipo)
- blu_prompt_management: 22% (49 funções sem tipo)
- blu_sql_factory: 26% (224 funções sem tipo)

**Best exemplars:** agent_api (81%), blu_models (84%), blu_observability_bootstrap (100% — única lib 100% tipada).

**Systemic issue:** A cultura de type hints não foi adotada consistentemente. As novas libs (agent_api: 81%) mostram que é possível — as libs legacy precisam de catch-up.

### 4.2 Logging Inconsistente — 88 print() em Produção

**Artefatos com print() como logging:**

| Artefato | Tier | Chamadas | Severidade |
|---|---|---|---|
| agent_api | T1 | 32 | P0 (T1 escalation) |
| blu_db_connector | T3 | 19 | P1 |
| tool_pool_api | T2 | 18 | P1 |
| blu_sql_factory | T2 | 14 | P1 |
| blu_agent_framework | T1 | 4 | P1 |
| blu_experiment_service | T4 | 1 | P2 |

**Apenas 1/25 artefatos** (blu_observability_bootstrap) implementa structured JSON logging, contrariando patterns.md.

### 4.3 Correlation IDs — Isolados no blu_agent_framework

O `blu_agent_framework/orchestrator` gera e usa correlation IDs (`generate_correlation_id()` — 12-char hex), mas:

- **Nenhum middleware HTTP** injeta `X-Correlation-Id` nas requests
- **agent_api e tool_pool_api** não propagam o ID para as libs downstream
- **24/25 artefatos** não incluem correlation_id em logs
- **Frontend** não envia request ID nos headers

### 4.4 Resiliência de Rede — Ausente nos Serviços Críticos

| Serviço Externo | Retry | Circuit Breaker | Impacto |
|---|---|---|---|
| **Supabase** (RPC/REST) | ❌ | ❌ | P0 — banco principal sem resiliência |
| **Redis** | ❌ | ❌ | P1 — cache sem proteção contra degradação |
| **LLM APIs** | ⚠️ (text-to-sql only) | ❌ | P1 — timeouts em cadeia |
| Google APIs | ❌ | ❌ | P2 |
| BigQuery | ❌ | ❌ | P2 |
| Twilio | ❌ | ❌ | P2 |
| Langfuse | ❌ | ✅ (2 impl) | ✅ |
| MCP (external) | ✅ (exponential backoff) | ❌ | ✅ |

### 4.5 Duplicação Cross-Cutting

**Padrão repetido mais impactante:** config.py com pydantic-settings boilerplate aparece em **7 artefatos** (5 libs + 2 services), com ~15 linhas idênticas cada (DUP-02). Extrair para `blu_config_base` economizaria ~80 linhas e padronizaria `env_file`, `extra="ignore"`.

**Padrão de exceções repetido:** 3 libs (blu_auth, blu_elicitation_service, blu_tool_registry) implementam `BaseException(message, code)` independentemente (DUP-03).

**Frontend:** Rotinas TSX compartilham UI blocks sem componente extraído (RoutineConfigSection ↔ RoutinesPanel).

### 4.6 Test Gaps Sistêmicos

| Categoria | Count |
|---|---|
| Artefatos sem testes | 10 (incluindo blu_models T1) |
| Artefatos com coleção quebrada | 4 (tool_pool_api, blu_llm_service, blu_auth, blu_db_connector) |
| Artefatos com cobertura <30% | 5 (agent_api 6%, blu_context_service 23%, blu_agent_framework 38%, etc.) |
| Testes sem asserts | 4 arquivos (tool_pool_api) |
| Flaky candidates (time.sleep) | 2 (blu_agent_framework, blu_supabase_client) |

### 4.7 Stack Trace Exposure — Padrão Cross-Service

`str(exc)` é embutido em `HTTPException.detail` ou SSE events em **6 locais** nos dois services:

| Arquivo | Linha | Severidade |
|---|---|---|
| agent_api/api/agents_router.py | 149 | P0 |
| agent_api/core/service.py | 576, 616, 672 | P0 |
| agent_api/api/chat_router.py | 78 | P0 |
| tool_pool_api/api/integrations_router.py | 450 | P1 |

### 4.8 Frontend — 3 Gaps Estruturais

1. **Zero Error Boundaries** — qualquer exceção não tratada quebra a UI inteira (P1)
2. **Sem code splitting** — bundle monolítico sem React.lazy/Suspense (P1)
3. **Sem CSP headers** — exposto a XSS via inline scripts (P1)

### 4.9 Relative Imports — Spec vs Realidade

196 imports relativos (`from .module import`) — a maioria em `__init__.py` como padrão Python idiomático. O patterns.md prescreve full paths (`from libs.X.src.X import`). **Recomendação:** Revisar patterns.md para aceitar relative imports, mantendo full-path apenas para imports cross-lib. Esta é uma divergência intencional válida (resolution.md R2).

---

## 5. Prioritized Findings

### 5.1 P0 — Imediato (segurança, perda de dados, bloqueio operacional)

| # | ID | Dimensão | Artefato | Descrição | Arquivo:Linha |
|---|---|---|---|---|---|
| 1 | TYPE-T1-01 | Types | blu_agent_framework (T1) | 27% typed — 240 funções sem type hints | `src/blu_agent_framework/` |
| 2 | TYPE-T1-02 | Types | blu_context_service (T1) | 25% typed — 21 funções sem tipo | `src/blu_context_service/` |
| 3 | TYPE-T1-03 | Types | blu_supabase_client (T1) | 23% typed — 85 funções sem tipo | `src/blu_supabase_client/` |
| 4 | LOG-T1-01 | Logging | agent_api (T1) | 32 chamadas de `print()` em produção (T1 escalation) | `run_routine.py` e scripts |
| 5 | ERR-P0-01 | Error Handling | agent_api (T1) | `str(exc)` exposto via HTTPException.detail | `api/agents_router.py:149`, `api/chat_router.py:78`, `core/service.py:576,616,672` |
| 6 | ERR-P0-02 | Error Handling | blu_supabase_client (T1) | Sem retry para Supabase RPC/REST — risco de perda de dados | `client.py` |
| 7 | PERF-P0-01 | Performance | blu_agent_framework (T1) | N+1 queries: 2N round-trips DB por follow-up | `nodes.py:961-990` |
| 8 | PERF-P0-02 | Performance | blu_agent_framework (T1) | N+1 updates: batch update virou N queries individuais | `nodes.py:901-904` |
| 9 | PERF-P0-03 | Performance | blu_agent_framework (T1) | Schema gap: `rfq_requests` referenciada mas pode não existir no DB de produção | `nodes.py` (geral) |
| 10 | TEST-P0-01 | Tests | blu_models (T1) | **0 testes** — nó central do grafo, 6 dependentes | `libs/blu_models/` |
| 11 | TEST-P0-02 | Tests | agent_api (T1) | 6% line coverage — serviço T1 com 26 testes apenas | `services/agent_api/` |

**Nota:** Findings 7, 8, 9 são do performance review e requerem verificação imediata no DB de produção e correção de queries.

### 5.2 P1 — Next Sprint (performance, maintainability, tech-debt crítico)

| # | ID | Dimensão | Descrição |
|---|---|---|---|
| 1 | CORR-P1-01 | Error Handling | Correlation IDs não propagados — impossível rastrear requests ponta-a-ponta |
| 2 | LOG-P1-01 | Logging | Structured JSON logging ausente em 24/25 artefatos |
| 3 | LOG-P1-02 | Logging | Substituir `print()` por `logging` em blu_db_connector (19), tool_pool_api (18), blu_sql_factory (14) |
| 4 | SEC-P1-01 | Security | Rate limiting ausente em agent_api (T1) — RATE-01 |
| 5 | SEC-P1-02 | Security | CSP headers ausentes no frontend — CSP-01 |
| 6 | SEC-P1-03 | Security | Shared bearer token sem escopo em inbox_dispatch — AUTH-01 |
| 7 | SEC-P1-04 | Security | xlsx Prototype Pollution/ReDoS sem fix — DEP-01 |
| 8 | PERF-P1-01 | Performance | Sequential awaits em routine_functions.py:1727 (3 queries Supabase em série) |
| 9 | PERF-P1-02 | Performance | HTTP em loop sem paralelismo — routine_functions.py:1781 |
| 10 | PERF-P1-03 | Performance | Sequential snapshot — 7+ chamadas Supabase em série (context_service.py:320) |
| 11 | PERF-P1-04 | Performance | Sem code splitting no frontend — React.lazy/Suspense ausente |
| 12 | PERF-P1-05 | Performance | Monolith: routine_functions.py com 3297 linhas |
| 13 | ERR-P1-01 | Error Handling | Zero Error Boundaries no frontend React |
| 14 | ERR-P1-02 | Error Handling | 273+ `except Exception:` broad catches nos services |
| 15 | ERR-P1-03 | Error Handling | Sem circuit breaker para Supabase (blu_supabase_client) |
| 16 | ERR-P1-04 | Error Handling | Sem circuit breaker para Redis (blu_context_service) |
| 17 | ERR-P1-05 | Error Handling | Sem circuit breaker para LLM APIs (blu_llm_service) |
| 18 | ERR-P1-06 | Error Handling | 12 libs sem hierarchy de exceções própria |
| 19 | TYPE-P1-01 | Types | Adicionar type hints a Tier 2: blu_llm_service (71), blu_sql_factory (224), blu_prompt_management (49) |
| 20 | TEST-P1-01 | Tests | Corrigir coleção de testes: tool_pool_api (7 arquivos), blu_llm_service (5), blu_auth (3), blu_db_connector (1) |
| 21 | TEST-P1-02 | Tests | Criar testes para blu_hitl_service (T3, 0 testes) |
| 22 | DUP-P1-01 | Duplication | Audit.py duplicado — consolidar em blu_supabase_client (DUP-01) |
| 23 | DUP-P1-02 | Duplication | config.py boilerplate em 7 artefatos — extrair blu_config_base (DUP-02) |

### 5.3 P2 — Backlog (estilo, documentação, melhorias incrementais)

| # | ID | Dimensão | Descrição |
|---|---|---|---|
| 1 | IMP-P2-01 | Imports | 196 relative imports — spec conflict com patterns.md |
| 2 | IMP-P2-02 | Imports | 10 arquivos com import order quebrado |
| 3 | TS-P2-01 | TypeScript | 17 `any` em apps/blu_v3 |
| 4 | TS-P2-02 | TypeScript | 35 `console.log` em produção |
| 5 | TS-P2-03 | TypeScript | 4 variáveis snake_case em TS (anti-pattern) |
| 6 | TS-P2-04 | TypeScript | 5 default exports (anti-pattern TS moderno) |
| 7 | STR-P2-01 | Structure | blu_shared_utils sem `__init__.py` |
| 8 | STR-P2-02 | Structure | Services com `__init__.py` vazio |
| 9 | DOC-P2-01 | Documentation | 9 documentos listados em HERMES.md ausentes (CODE_MAP.md, FRONTEND.md, DATABASE_SCHEMA.md, etc.) |
| 10 | DOC-P2-02 | Documentation | SHARED_MEMORY_DESIGN.md referenciado mas não existe |
| 11 | SEC-P2-01 | Security | .secrets.baseline gitignored (SEC-01) |
| 12 | SEC-P2-02 | Security | Shared static tokens sem rotação (SEC-02) |
| 13 | SEC-P2-03 | Security | CORS localhost regex permissivo em produção (CORS-01) |
| 14 | SEC-P2-04 | Security | Dev mode bypass webhook validation (AUTH-02) |
| 15 | SEC-P2-05 | Security | pip-audit não integrado ao CI (DEP-02) |
| 16 | SEC-P2-06 | Security | npm audit: 3 high vulns em blu_v3 (vite, ws, react-router têm fix), 2 high em blu-auth |
| 17 | ERR-P2-01 | Error Handling | Mensagens de erro em inglês (patterns.md exige PT-BR) |
| 18 | ERR-P2-02 | Error Handling | Sem retry para Google APIs, BigQuery, Twilio |
| 19 | ERR-P2-03 | Error Handling | `ValidationError` (blu_sql_factory) não herda de Exception |
| 20 | ERR-P2-04 | Error Handling | `AuthenticationError` duplicado em 2 namespaces |
| 21 | ERR-P2-05 | Error Handling | SkillTurnLimitError logged como `error` (deveria ser `warning`) |
| 22 | PERF-P2-01 | Performance | Missing index: `agent_catalog_id` em `agent_sessions` |
| 23 | PERF-P2-02 | Performance | Sem otimização de imagens no frontend |
| 24 | TEST-P2-01 | Tests | Edge cases faltantes nas libs com cobertura >50% |
| 25 | TEST-P2-02 | Tests | Adicionar conftest.py a blu_agent_framework (T1, 211 testes, fixtures duplicadas) |
| 26 | TEST-P2-03 | Tests | Eliminar time.sleep dos testes (2 candidatos flaky) |
| 27 | TEST-P2-04 | Tests | Remover test files vazios/sem assert em tool_pool_api (4 arquivos) |
| 28 | DUP-P2-01 | Duplication | Extrair BluError base class para blu_shared_utils (DUP-03) |
| 29 | DUP-P2-02 | Duplication | Extrair BluTimer context manager (DUP-04) |
| 30 | DUP-P2-03 | Duplication | Extrair shared TSX routine components (JS-01) |
| 31 | DUP-P2-04 | Duplication | Extrair shared API handler factory (JS-02) |
| 32 | DUP-P2-05 | Duplication | Remover test_integrations_router.py obsoleto (DUP-07) |
| 33 | DUP-P2-06 | Duplication | tool_pool_api usar blu_context_service Redis deps em vez de reinventar (Cross-01) |

---

## 6. Remediation Suggestions with Examples

### 6.1 P0 — Stack Trace Leakage Fix

**Problema (agent_api/api/agents_router.py:149):**
```python
# ANTES — expõe detalhes internos
except Exception as exc:
    raise HTTPException(status_code=500, detail=str(exc))
```

**Solução:**
```python
# DEPOIS — mensagem genérica, detalhe logado
except Exception as exc:
    logger.exception("Erro interno ao processar requisição de agentes", extra={"error": str(exc)})
    raise HTTPException(status_code=500, detail="Erro interno do servidor. Tente novamente.")
```

**Esforço:** Small (~1h) — 6 locais afetados.

### 6.2 P0 — N+1 Queries Batch Fix

**Problema (blu_agent_framework/nodes.py:961-990):**
```python
# ANTES — 2N queries DB
for rfq_id in follow_up_ids:
    rfq_result = db.table("rfq_requests").select(...).eq("id", rfq_id).maybe_single().execute()
    # ...
    db.table("rfq_requests").update({"follow_up_count": follow_ups}).eq("id", rfq_id).execute()
```

**Solução:**
```python
# DEPOIS — 1 query batch + 1 batch update
rfqs_result = db.table("rfq_requests").select(
    "id,supplier_id,follow_up_count,deadline,communication_channel,supplier_roster(name,contact_phone,contact_email)"
).in_("id", follow_up_ids).execute()

for rfq in (rfqs_result.data or []):
    # processa em memória...

db.table("rfq_requests").update(
    {"follow_up_count": db.raw("follow_up_count + 1")}
).in_("id", reminded_ids).execute()
```

**Esforço:** Small (~1.5h) — 2 funções afetadas.

### 6.3 P0 — N+1 Update Fix (1 linha)

**Problema (blu_agent_framework/nodes.py:901-904):**
```python
# ANTES
if expired:
    for rfq_id in expired:
        db.table("rfq_requests").update({"status": "expired"}).eq("id", rfq_id).execute()
```

**Solução (1 linha muda tudo):**
```python
# DEPOIS
if expired:
    db.table("rfq_requests").update({"status": "expired"}).in_("id", expired).execute()
```

**Esforço:** Trivial (~5min).

### 6.4 P1 — Rate Limiting com slowapi

**Problema:** Nenhum rate limiting em agent_api (T1).

**Solução:**
```python
# main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

# chat_router.py
from slowapi import Limiter
from fastapi import Request

@router.post("/v1/chat")
@limiter.limit("10/minute", key_func=lambda r: r.state.client_id)
async def chat(request: Request, body: ChatRequest):
    ...
```

**Esforço:** Medium (~3h) — middleware + configuração + testes.

### 6.5 P1 — Sequential Awaits → asyncio.gather

**Problema (routine_functions.py:1727-1773):**
```python
# ANTES — 3 queries independentes em série
acct_resp = await asyncio.to_thread(supabase.table("polp_accounts").select("*").eq("client_id", cid).execute)
bills_resp = await asyncio.to_thread(supabase.table("polp_bills").select("*").eq("client_id", cid).execute)
intg_resp = await asyncio.to_thread(supabase.table("polp_integrations").select("*").eq("client_id", cid).execute)
```

**Solução:**
```python
# DEPOIS — 3 queries em paralelo
acct_fn = lambda: supabase.table("polp_accounts").select("*").eq("client_id", cid).execute()
bills_fn = lambda: supabase.table("polp_bills").select("*").eq("client_id", cid).execute()
intg_fn = lambda: supabase.table("polp_integrations").select("*").eq("client_id", cid).execute()

acct_resp, bills_resp, intg_resp = await asyncio.gather(
    asyncio.to_thread(acct_fn),
    asyncio.to_thread(bills_fn),
    asyncio.to_thread(intg_fn),
)
```

**Esforço:** Small (~1h) — 2 funções afetadas.

### 6.6 P1 — HTTP Loop Batch com Semaphore

**Problema (routine_functions.py:1781-1815):**
```python
# ANTES — N integrações × P páginas em série
for intg_id in integration_ids:
    page = 1
    while True:
        r = await http.get(f"{polp_base}/integrations/{intg_id}/recurrings", ...)
```

**Solução:**
```python
# DEPOIS — paralelo com limite de concorrência
sem = asyncio.Semaphore(5)

async def fetch_integration(intg_id):
    async with sem:
        async with httpx.AsyncClient(timeout=15.0) as http:
            page = 1
            while True:
                r = await http.get(f"{polp_base}/integrations/{intg_id}/recurrings", headers=polp_headers, params={"page": page})
                # ... pagination ...

recurrings_results = await asyncio.gather(*[fetch_integration(iid) for iid in integration_ids])
```

**Esforço:** Small (~1.5h).

### 6.7 P1 — Code Splitting com React.lazy

**Problema:** Frontend sem code splitting — bundle monolítico.

**Solução:**
```tsx
// App.tsx
import React, { Suspense } from "react";

const BibliotecaRoom = React.lazy(() => import("./pages/app/BibliotecaRoom"));
const DocumentosRoom = React.lazy(() => import("./pages/app/DocumentosRoom"));
const OnboardingApp = React.lazy(() => import("./pages/onboarding/OnboardingApp"));

function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Routes>
        <Route path="/biblioteca" element={<BibliotecaRoom />} />
        <Route path="/documentos" element={<DocumentosRoom />} />
        <Route path="/onboarding" element={<OnboardingApp />} />
      </Routes>
    </Suspense>
  );
}
```

**Esforço:** Medium (~3h) — refatorar router + adicionar Suspense boundaries.

### 6.8 Quick Wins (<1h each)

| # | Ação | Esforço | Impacto |
|---|---|---|---|
| QW-1 | N+1 update fix (1 linha — nodes.py:901) | 5 min | Elimina N queries desnecessárias |
| QW-2 | Consolidar audit.py (remover duplicata em blu_agent_framework) | 2h | Elimina duplicação T1 |
| QW-3 | Extrair BluError base class para blu_shared_utils | 1.5h | Padroniza exceptions em 3 libs |
| QW-4 | Extrair BluTimer context manager | 1h | Unifica timers em 2 libs |
| QW-5 | `npm audit fix` em blu_v3 e blu-auth | 30 min | Corrige 5 high vulns (vite, ws, react-router) |
| QW-6 | Adicionar `loading="lazy"` em `<img>` tags no frontend | 30 min | Melhora LCP |

---

## 7. Effort Estimates & Sequencing

### 7.1 Total Estimated Remediation Effort

| Prioridade | Findings | Esforço Estimado |
|---|---|---|
| P0 — Imediato | 11 findings | **20–30 horas** |
| P1 — Next Sprint | 23 findings | **55–75 horas** |
| P2 — Backlog | 34 findings | **45–60 horas** |
| **Total** | **68 findings** | **120–165 horas** |

### 7.2 Suggested Sequencing

**Fase 1 — P0 Imediato (Sprint atual):**

| Ordem | Ação | Esforço | Dependências |
|---|---|---|---|
| 1 | Verificar `rfq_requests` no DB de produção (PERF-P0-03) | 30 min | Acesso Supabase prod |
| 2 | N+1 update fix — nodes.py:901 (PERF-P0-02) | 5 min | — |
| 3 | N+1 query fix — nodes.py:961 (PERF-P0-01) | 1.5h | — |
| 4 | Stack trace leakage fix — 6 locais (ERR-P0-01) | 1h | — |
| 5 | Substituir print() por logging em agent_api (LOG-T1-01) | 2h | — |
| 6 | Adicionar retry com backoff ao blu_supabase_client (ERR-P0-02) | 3h | — |
| 7 | Criar testes para blu_models (TEST-P0-01) | 4h | Entender schemas |
| 8 | Subir cobertura do agent_api para >40% (TEST-P0-02) | 6h | — |
| 9 | Adicionar type hints a blu_supabase_client funções públicas (TYPE-T1-03) | 3h | — |

**Fase 2 — P1 Next Sprint:**

| Ordem | Ação | Esforço | Dependências |
|---|---|---|---|
| 10 | Rate limiting em agent_api com slowapi (SEC-P1-01) | 3h | — |
| 11 | CSP headers no frontend (SEC-P1-02) | 2h | — |
| 12 | Code splitting com React.lazy (PERF-P1-04) | 3h | — |
| 13 | Sequential awaits → asyncio.gather (PERF-P1-01) | 1h | — |
| 14 | HTTP loop batch com Semaphore (PERF-P1-02) | 1.5h | — |
| 15 | Sequential snapshot → asyncio.gather (PERF-P1-03) | 2h | — |
| 16 | Error Boundaries no frontend (ERR-P1-01) | 2h | 12 (code splitting) |
| 17 | Circuit breaker para Supabase (ERR-P1-03) | 3h | 6 (retry Supabase) |
| 18 | Circuit breaker para Redis (ERR-P1-04) | 2h | — |
| 19 | Circuit breaker para LLM APIs (ERR-P1-05) | 2h | — |
| 20 | Consolidar audit.py (DUP-P1-01) | 2h | — |
| 21 | Extrair blu_config_base (DUP-P1-02) | 4h | — |
| 22 | Corrigir coleção de testes quebrados (TEST-P1-01) | 6h | Entender APIs |
| 23 | Criar testes para blu_hitl_service (TEST-P1-02) | 3h | — |
| 24 | Correlation ID middleware HTTP (CORR-P1-01) | 4h | — |
| 25 | Adicionar type hints a blu_agent_framework funções públicas (TYPE-T1-01) | 6h | — |
| 26 | Adicionar type hints a blu_context_service (TYPE-T1-02) | 2h | — |
| 27 | Substituir print() por logging em db_connector, tool_pool, sql_factory (LOG-P1-02) | 2h | — |

**Fase 3 — P2 Backlog (contínuo):**
Executar incrementalmente conforme capacidade. Priorizar: npm audit fix (QW-5), BluError extraction (DUP-P2-01), documentation gaps (DOC-P2-01), e eliminação de any/console.log no frontend (TS-P2-01, TS-P2-02).

### 7.3 Dependencies Between Remediations

```
retry Supabase (ERR-P0-02)
    └─► circuit breaker Supabase (ERR-P1-03)

code splitting frontend (PERF-P1-04)
    └─► Error Boundaries frontend (ERR-P1-01)

blu_config_base extraction (DUP-P1-02)
    └─► migrar 7 artefatos para usar base class

correlation ID middleware HTTP (CORR-P1-01)
    └─► propagar para libs downstream (P2)

type hints Tier 1 (TYPE-T1-01,02,03)
    └─► type hints Tier 2 (TYPE-P1-01)
```

### 7.4 Follow-up Issues Sugeridos

| Issue | Descrição | Assignee |
|---|---|---|
| T57.8-p0-01 | Fix N+1 queries + schema gap em nodes.py | factory-coder |
| T57.8-p0-02 | Fix stack trace leakage nos services | factory-coder |
| T57.8-p0-03 | Adicionar retry/circuit breaker ao blu_supabase_client | factory-coder |
| T57.8-p0-04 | Substituir print() por logging em agent_api | factory-coder |
| T57.8-p1-01 | Implementar rate limiting em agent_api e tool_pool_api | factory-coder |
| T57.8-p1-02 | Adicionar CSP + Error Boundaries + code splitting ao frontend | factory-coder |
| T57.8-p1-03 | Extrair blu_config_base shared lib | factory-coder |
| T57.8-p1-04 | Corrigir coleção de testes quebrados (4 artefatos) | factory-tester |
| T57.8-p1-05 | Criar testes para blu_models + blu_hitl_service | factory-tester |
| T57.8-p2-01 | Resolver 196 relative imports — spec vs realidade | factory-coder |
| T57.8-p2-02 | Criar 9 documentos system_reference faltantes | factory-coder |

---

## Appendix A: Input Files

| Arquivo | Task | Linhas | Status |
|---|---|---|---|
| `docs/planning/issue-57/inventory-catalog.md` | T57.1 | 225 | ✅ |
| `docs/planning/issue-57/patterns-review.md` | T57.2 | 462 | ✅ |
| `docs/planning/issue-57/duplication-review.md` | T57.3 | 369 | ✅ |
| `docs/planning/issue-57/performance-review.md` | T57.4 | 263 | ✅ |
| `docs/planning/issue-57/security-review.md` | T57.5 | 347 | ✅ |
| `docs/planning/issue-57/error-handling-review.md` | T57.6 | 448 | ✅ |
| `docs/planning/issue-57/test-coverage-review.md` | T57.7 | 319 | ✅ |

## Appendix B: Tier → Escalation Reference

| Tier | Artefatos | Regra P1→P0 |
|---|---|---|
| T1 | agent_api, blu_agent_framework, blu_supabase_client, blu_models, blu_context_service | P1 findings escalam para P0 |
| T2 | tool_pool_api, blu_llm_service, blu_rag_factory, blu_prompt_management, blu_sql_factory | Standard |
| T3 | blu_auth, blu_hitl_service, blu_data_connectors, blu_db_connector | Standard |
| T4 | 8 libs + apps/blu_v3 + packages/blu-auth | Relaxed |

## Appendix C: Key Metrics Dashboard

```
Type Coverage:    ████████░░░░░░░░░░░░ 35% (626/1773 funções)
Bare Excepts:     ████████████████████ 0   ✅
Broad Excepts:    ████████████████████ 273+ ⚠️
Test Pass Rate:   █████████████████░░░ 84.2% (661/785)
Test Coverage:    ███████░░░░░░░░░░░░░ 38% (média)
Correlation IDs:  █░░░░░░░░░░░░░░░░░░░ 1/25 artefatos
Structured JSON:  █░░░░░░░░░░░░░░░░░░░ 1/25 artefatos
Rate Limiting:    ░░░░░░░░░░░░░░░░░░░░ 0/2 services
CSP Headers:      ░░░░░░░░░░░░░░░░░░░░ 0
Error Boundaries: ░░░░░░░░░░░░░░░░░░░░ 0
Print() as Log:   ██████████░░░░░░░░░░ 88 chamadas
```

---

*Consolidado em 2026-06-22 por factory-coder (t_f572c42). Baseado em 7 relatórios de code review (T57.1–T57.7), 25 artefatos, 68 findings únicos.*
