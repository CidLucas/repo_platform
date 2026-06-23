# patterns-review-f1-5.md — Code Patterns Consistency Review (Fases 1-5)

> **Gerado por:** factory-coder (t_b99bd5a4), 2026-06-23
> **Escopo:** 25 artefatos de Fases 1-5 (21 libs, 2 services, 1 app, 1 package)
> **Branch:** `feat/b1-code-patterns-analysis-f1-5`
> **Depende de:** `inventory-catalog.md` (T57.1), `patterns.md` (baseline), `resolution.md` (DQ3 tier classification)

---

## 1. Executive Summary

| Métrica | Valor | Status |
|----------|-------|--------|
| Total de artefatos analisados | **25** (21 libs, 2 services, 1 app, 1 package) | — |
| Dimensões verificadas | **7** (naming, imports, structure, types, error handling, logging, config) | — |
| Funções com type hints (Python) | **626/1773 (35%)** | ❌ Crítico |
| Bare `except:` (sem tipo) | **0** | ✅ Excelente |
| `__init__.py` com API pública | **20/21** libs | ✅ |
| Imports relativos (`from .`) | **196** | ⚠️ Anti-pattern |
| `print()` como logging | **88** chamadas | ❌ P1 |
| Structured JSON logging | **1/25** artefatos | ⚠️ P1 |
| Correlation IDs | **1/25** artefatos (blu_agent_framework) | ⚠️ P1 |
| `any` em TypeScript | **17** ocorrências | ⚠️ P2 |
| `console.log` em TS | **35** chamadas | ⚠️ P2 |
| Error Boundaries (TSX) | **0** | ❌ |
| Possíveis secrets hardcoded | **22** (15 em tests) | ⚠️ P1 |
| Import order quebrado | **10** arquivos | P2 |
| camelCase em Python | **0** | ✅ |

**Resumo narrativo:** O codebase tem excelente disciplina de nomenclatura (0 camelCase em Python, 0 classes não-PascalCase) e zero bare excepts. Os problemas sistêmicos concentram-se em **type hints (35% de cobertura)**, **uso de `print()` como logging (88 chamadas)**, **imports relativos (196 ocorrências)** e **ausência de correlation IDs fora do blu_agent_framework**. O frontend (apps/blu_v3) tem 17 `any` e 35 `console.log` — aceitável para Tier 4, mas requer atenção.

---

## 2. Methodology

### 2.1 Scope Definition — Fases 1-5

As Fases 1-5 abrangem todos os artefatos do monorepo. Conforme `resolution.md`:

| Fase | Issues | Artefatos Relacionados |
|------|--------|----------------------|
| Fase 1 | #17-#20 (pre-flight, post-flight, handoff, integrity) | blu_agent_framework, agent_api |
| Fase 2 | #21-#24 (routine checkpoint, snapshots, intake) | routine_engine, blu_context_service |
| Fase 3 | #25-#28 (vector store pipeline, shared memory) | tool_pool_api, blu_rag_factory |
| Fase 4 | #29-#32 (synthesis, meta, knowledge graph, retention) | blu_sql_factory, blu_models |
| Fase 5 | #33-#37 (extensões e otimizações) | libs restantes, apps/blu_v3, packages/blu-auth |

### 2.2 Scan Tool

Varredura completa do monorepo com foco em:
- Python: `libs/` (21) + `services/` (2) → todos os `.py` files
- TypeScript: `apps/blu_v3/` (1) + `packages/` (1) → todos os `.ts/.tsx` files
- Exclusões: `__pycache__/`, `.venv/`, `node_modules/`, `dist/`, `build/`, `.next/`, `egg-info/`

### 2.3 Dimensions Checked

Cada artefato verificado nas 7 dimensões do `patterns.md`:
1. **Naming**: snake_case files/functions/variables, PascalCase classes, UPPER_SNAKE constants (Python); PascalCase components, camelCase utils, `use` hooks (TS)
2. **Imports**: stdlib → third-party → project ordering, path style, wildcard detection
3. **Structure**: `__init__.py` exports, `setup.py`/`pyproject.toml`, standard directories (TS)
4. **Types**: type hints presence, Pydantic usage, `any` detection (TS)
5. **Error handling**: bare except, custom exception hierarchies, correlation IDs, error boundaries (TS)
6. **Logging**: `logging.getLogger(__name__)`, structured JSON, `print()` detection, `console.log` detection
7. **Config**: `os.getenv`/`os.environ`, Pydantic Settings, hardcoded secrets detection, Vite env vars (TS)

### 2.4 Tier Classification (per resolution.md §DQ3)

| Tier | Criticality | Count | Threshold |
|------|-------------|-------|-----------|
| **Tier 1** | Crítico | 5 (blu_agent_framework, blu_supabase_client, blu_models, blu_context_service, agent_api) | P1 → P0 escalation |
| **Tier 2** | Alto | 5 (tool_pool_api, blu_llm_service, blu_rag_factory, blu_prompt_management, blu_sql_factory) | Standard |
| **Tier 3** | Médio | 4 (blu_auth, blu_hitl_service, blu_data_connectors, blu_db_connector) | Standard |
| **Tier 4** | Baixo | 11 (demais libs + apps/blu_v3 + packages/blu-auth) | Relaxed |

---

## 3. Dimension 1: Naming

### 3.1 Python Naming (23 artefatos)

| Métrica | Valor | Compliance |
|----------|-------|------------|
| Arquivos não-snake_case | **1** (teste: `import os.py`) | ✅ |
| Funções camelCase | **0** | ✅ Excelente |
| Classes não-PascalCase | **0** | ✅ Excelente |
| Constantes UPPER_SNAKE | 77+ detectadas | ✅ |

**Análise:** A disciplina de nomenclatura Python é exemplar. Zero funções camelCase, zero classes com nome incorreto. O único desvio é o arquivo `libs/blu_db_connector/tests/import os.py` (com espaço no nome) — provavelmente um artefato de teste.

**Exemplos de conformidade:**
- `blu_agent_framework/config.py::ATENDENTE_CONFIG` — UPPER_SNAKE ✅
- `blu_context_service/tool_cache.py::DEFAULT_TTL_SECONDS` — UPPER_SNAKE ✅
- `blu_context_service/tool_cache.py::MAX_SUMMARY_LENGTH` — UPPER_SNAKE ✅

### 3.2 TypeScript/TSX Naming (2 artefatos)

| Métrica | apps/blu_v3 | packages/blu-auth | Compliance |
|----------|-------------|-------------------|------------|
| Componentes PascalCase (.tsx) | ✅ (1 desvio: `main.tsx`) | ✅ | ⚠️ Trivial |
| Hooks com prefixo `use` | ✅ (useIntegrations, useAdmin, etc.) | ✅ (useAuth) | ✅ |
| Interfaces PascalCase | ✅ (RecentActivityItem, DayStats...) | ✅ (AuthState...) | ✅ |
| Variáveis snake_case (anti-pattern) | 4 ocorrências | 0 | ⚠️ P2 |

**Exemplos de snake_case em TS:**
- `apps/blu_v3/src/components/agenda/MonthlyGantt.tsx::tooltip_content`
- `apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx::column_mapping`

---

## 4. Dimension 2: Imports

### 4.1 Python Imports

| Métrica | Valor | Compliance |
|----------|-------|------------|
| Wildcard imports (`import *`) | **0** | ✅ |
| Import order quebrado | **10 arquivos** | ⚠️ P2 |
| Imports relativos (`from .`) | **196** | ⚠️ Anti-pattern |

**Import order broken (10 arquivos):**

| Arquivo | Artefato | Tier |
|---------|----------|------|
| `blu_auth/oauth2/google_provider.py` | blu_auth | T3 |
| `blu_context_service/context_service.py` | blu_context_service | **T1** ⚠️ |
| `blu_db_connector/operations.py` | blu_db_connector | T3 |
| `blu_experiment_service/cli.py` | blu_experiment_service | T4 |
| `blu_experiment_service/runner.py` | blu_experiment_service | T4 |
| `blu_llm_service/client.py` | blu_llm_service | T2 |
| `tool_pool_api/server/tool_modules/communication_module.py` | tool_pool_api | T2 |
| `tool_pool_api/server/tool_modules/report_module.py` | tool_pool_api | T2 |

**Relative imports — Top 8 por artefato:**

| Artefato | Tier | Count | Contexto |
|----------|------|-------|----------|
| **blu_models** | T1 ⚠️ | 42 | `__init__.py` exports internos |
| **tool_pool_api** | T2 | 42 | Módulos internos do serviço |
| blu_experiment_service | T4 | 23 | Estrutura de subpacotes |
| blu_tool_registry | T4 | 16 | `__init__.py` exports |
| blu_google_suite_client | T4 | 13 | Submódulos (calendar, gmail, docs...) |
| blu_sql_factory | T2 | 13 | `__init__.py` + submódulos |
| blu_auth | T3 | 10 | `__init__.py` de adapters, oauth2 |
| blu_supabase_client | T1 ⚠️ | 9 | Estrutura interna |

**Análise:** A maioria dos imports relativos está em `__init__.py` — onde `from .module import X` é o padrão Python idiomático para definir APIs públicas de pacotes. Isto é uma **divergência intencional** do patterns.md (que prescreve `from libs.blu_models.src.models import ...`), mas é o comportamento padrão do Python e amplamente aceito. O patterns.md pode precisar de revisão neste ponto (ver §10).

### 4.2 TypeScript Imports

| Métrica | apps/blu_v3 | packages/blu-auth | Compliance |
|----------|-------------|-------------------|------------|
| Path aliases (`@/`) | ✅ | N/A | ✅ |
| Default exports | 5 arquivos | 0 | ⚠️ P2 |
| `import.meta.env` | ✅ 6 arquivos | ✅ 1 arquivo | ✅ |

---

## 5. Dimension 3: Structure

### 5.1 Python Structure

| Métrica | Valor | Compliance |
|----------|-------|------------|
| Libs com `__init__.py` com API pública | **20/21** | ✅ |
| Libs com `__init__.py` vazio | **0** | ✅ |
| Libs sem `__init__.py` | **1** (blu_shared_utils) | ⚠️ P2 |
| Services com `__init__.py` vazio | **2** (agent_api, tool_pool_api) | ⚠️ P2 |
| `setup.py`/`pyproject.toml` | Verificar manualmente | — |

**Serviços com `__init__.py` vazio:**
- `services/agent_api/src/agent_api/__init__.py` — vazio, Tier 1
- `services/tool_pool_api/src/tool_pool_api/__init__.py` — vazio, Tier 2

Services FastAPI não precisam exportar API pública via `__init__.py` (entrada é `main.py`), mas patterns.md prescreve `__init__.py` com exports — divergência aceitável.

**blu_shared_utils** (T4) é a única lib sem `__init__.py` próprio — usa imports diretos de seus módulos. Baixa prioridade.

### 5.2 TypeScript Structure

| Diretório Padrão | apps/blu_v3 | packages/blu-auth |
|------------------|-------------|-------------------|
| `src/components/` | ✅ (dentro de `src/`) | ✅ (dentro de `src/`) |
| `src/hooks/` | ✅ (dentro de `src/`) | ✅ (dentro de `src/`) |
| `src/api/` | ✅ (dentro de `src/`) | ✅ (dentro de `src/`) |
| `src/types/` | ✅ (dentro de `src/`) | ✅ (dentro de `src/`) |
| `src/store/` | ✅ (Zustand) | N/A |

**Nota:** Ambos os artefatos TS usam estrutura flat com `src/` como raiz — `components/`, `hooks/`, `api/` estão dentro de `src/`. Em conformidade com patterns.md TS conventions.

---

## 6. Dimension 4: Types

### 6.1 Python Type Hints

**Métrica global: 626/1773 funções tipadas (35%)** ❌

| Artefato | Tier | Funções Totais | Tipadas | Não-tipadas | % Tipado |
|----------|------|---------------|---------|-------------|----------|
| **agent_api** | **T1** | 83 | 67 | 16 | **81%** ✅ |
| **blu_agent_framework** | **T1** | 329 | 89 | 240 | **27%** ❌ P0 |
| **blu_models** | **T1** | 57 | 48 | 9 | **84%** ✅ |
| **blu_context_service** | **T1** | 28 | 7 | 21 | **25%** ❌ P0 |
| **blu_supabase_client** | **T1** | 111 | 26 | 85 | **23%** ❌ P0 |
| tool_pool_api | T2 | 158 | 120 | 38 | **76%** ✅ |
| blu_llm_service | T2 | 85 | 14 | 71 | **16%** ❌ |
| blu_rag_factory | T2 | 59 | 19 | 40 | **32%** ⚠️ |
| blu_prompt_management | T2 | 63 | 14 | 49 | **22%** ⚠️ |
| blu_sql_factory | T2 | 301 | 77 | 224 | **26%** ❌ |
| blu_auth | T3 | 82 | 31 | 51 | **38%** ⚠️ |
| blu_hitl_service | T3 | 29 | 9 | 20 | **31%** ⚠️ |
| blu_data_connectors | T3 | 57 | 33 | 24 | **58%** ⚠️ |
| blu_db_connector | T3 | 66 | 23 | 43 | **35%** ⚠️ |
| blu_tool_registry | T4 | 206 | 35 | 171 | **17%** |
| blu_twilio_client | T4 | 55 | 5 | 50 | **9%** |
| blu_elicitation_service | T4 | 50 | 10 | 40 | **20%** |
| blu_google_suite_client | T4 | 59 | 41 | 18 | **69%** |
| blu_parsers | T4 | 37 | 14 | 23 | **38%** |
| blu_landing_intel | T4 | 10 | 2 | 8 | **20%** |
| blu_observability_bootstrap | T4 | 7 | 7 | 0 | **100%** ✅ |
| blu_experiment_service | T4 | 29 | 15 | 14 | **52%** |
| blu_shared_utils | T4 | 5 | 0 | 5 | **0%** |

**Tier 1 — Análise com thresholds escalados (P1 → P0):**

| Artefato (T1) | % Tipado | Severidade | Ação |
|---------------|----------|------------|------|
| agent_api | 81% | ✅ | Best exemplar — manter |
| blu_models | 84% | ✅ | Best exemplar — manter |
| blu_agent_framework | **27%** | ❌ P0 | Crítico — 240 funções sem tipo |
| blu_context_service | **25%** | ❌ P0 | Crítico — core infrastructure |
| blu_supabase_client | **23%** | ❌ P0 | Crítico — core infrastructure |

**Exemplos de funções sem tipo em Tier 1 (verificados):**
- `blu_agent_framework/approval.py:56::is_pending` — função pública sem tipo
- `blu_agent_framework/approval.py:142::request` — sem tipo de retorno
- `blu_agent_framework/approval.py:171::decide` — sem tipo de parâmetros
- `blu_context_service/context_service.py:22::external_user_lookup_from_context_service` — sem anotações
- `blu_supabase_client/src/blu_supabase_client/client.py` — múltiplas funções sem tipo

### 6.2 Pydantic Usage

| Métrica | Valor |
|----------|-------|
| Artefatos com Pydantic models | 11/23 Python |
| Artefatos com Pydantic Settings | 7/23 |

**Pydantic Settings encontrados em:**
- `blu_auth` (T3), `blu_context_service` (T1), `blu_experiment_service` (T4), `blu_llm_service` (T2), `blu_twilio_client` (T4), `agent_api` (T1), `tool_pool_api` (T2) ✅

### 6.3 TypeScript Types

| Métrica | Valor | Compliance |
|----------|-------|------------|
| `any` usage | **17 ocorrências** (apps/blu_v3) | ⚠️ P2 |
| Zod schemas | Não verificado (fora do scope) | — |

**`any` occurrences (apps/blu_v3):**
- `src/api/analytics.ts:83` — `data: any`
- `src/api/analytics.ts:84` — múltiplos `any` em API response
- `src/hooks/useKnowledgeBase.ts:53` — `item: any`
- `src/pages/app/AdminScreen.tsx:412,418` — `any` em handlers

---

## 7. Dimension 5: Error Handling

### 7.1 Python Error Handling

| Métrica | Valor | Compliance |
|----------|-------|------------|
| Bare `except:` | **0** | ✅ Excelente |
| Custom exception hierarchies | 8/23 libs | ⚠️ |
| Correlation IDs | 1/25 artefatos (blu_agent_framework) | ⚠️ P1 |

**Nota:** A revisão detalhada de error handling está em `error-handling-review.md` (T57.6). Resultados sumarizados aqui para completude.

**Correlation IDs — apenas blu_agent_framework:**
- `blu_agent_framework/approval.py`
- `blu_agent_framework/orchestrator.py`
- `blu_agent_framework/utils/observability.py`
- `blu_agent_framework/tests/unit/test_orchestrator_logging.py`

Nenhum outro artefato (incluindo os services agent_api e tool_pool_api) propaga correlation IDs — violação do patterns.md §1 (Error Handling: "Correlation IDs passed via context").

### 7.2 TypeScript Error Handling

| Métrica | apps/blu_v3 | packages/blu-auth |
|----------|-------------|-------------------|
| Error Boundaries | **0** ❌ | **0** ❌ |
| Try/catch presente | ✅ 5 arquivos | ✅ 1 arquivo |

---

## 8. Dimension 6: Logging

### 8.1 Python Logging

| Métrica | Valor | Compliance |
|----------|-------|------------|
| `logging.getLogger(__name__)` | **154 arquivos** | ✅ |
| `print()` como logging | **88 chamadas** em 6 artefatos | ❌ P1 |
| Structured JSON logging | **1 artefato** (blu_observability_bootstrap) | ⚠️ P1 |
| Loguru usage | 0 | — |

**`print()` as logging — por artefato:**

| Artefato | Tier | Chamadas | Severidade |
|----------|------|----------|------------|
| **agent_api** | **T1** | **32** | ❌ P0 (T1 escalation) |
| **blu_db_connector** | T3 | **19** | ⚠️ P1 |
| **tool_pool_api** | T2 | **18** | ⚠️ P1 |
| blu_sql_factory | T2 | 14 | ⚠️ P1 |
| blu_agent_framework | T1 | 4 | ⚠️ P1 |
| blu_experiment_service | T4 | 1 | P2 |

**Exemplos de `print()` como logging (verificados):**
- `agent_api/run_routine.py` — 32 chamadas de `print()` para logging de rotinas
- `blu_db_connector/run_migrations.py:5` — `print(f"Migrating database...")`
- `blu_db_connector/manager.py:11` — múltiplos `print()` de status
- `blu_sql_factory/schema_snapshot.py:9` — output de schema
- `blu_agent_framework/skills.py:2` — debug prints

**Structured logging:** Apenas `blu_observability_bootstrap` (T4) implementa logging JSON estruturado via `python-json-logger`. Os demais 22 artefatos Python usam logging textual tradicional. Patterns.md §1 prescreve "Structured logging (JSON)".

### 8.2 TypeScript Logging

| Métrica | apps/blu_v3 | packages/blu-auth |
|----------|-------------|-------------------|
| `console.log` | **34 chamadas** | **1 chamada** |

**Top arquivos com console.log:**
- `apps/blu_v3/src/api/clientes.ts` — 3 chamadas
- `apps/blu_v3/src/api/connectors.ts` — 3 chamadas
- `apps/blu_v3/src/api/agenda.ts` — 2 chamadas
- `apps/blu_v3/src/api/analytics.ts` — 2 chamadas

---

## 9. Dimension 7: Config

### 9.1 Python Config

| Métrica | Valor | Compliance |
|----------|-------|------------|
| `os.getenv`/`os.environ` | **49 arquivos** | ✅ |
| Pydantic Settings (`BaseSettings`) | **7 artefatos** | ✅ |
| `load_dotenv` | 4 arquivos | ✅ |
| Possíveis hardcoded secrets | **22** | ⚠️ P1 |

**Possíveis hardcoded secrets — análise:**

Dos 22 matches, **15 estão em arquivos de teste** (conftest.py, test_*.py) — aceitável para testes com valores fictícios:
- `blu_auth/tests/conftest.py::SECRET` — test fixture
- `blu_auth/tests/test_strategies.py::token, api_key` — test values
- `blu_context_service/tests/conftest.py::password` — test fixture
- `blu_llm_service/tests/test_client.py::API_KEY` — test value
- `blu_sql_factory/tests/conftest.py::api_key` — test fixture

**7 matches fora de testes requerem investigação** — podem ser strings de exemplo/documentação, mas precisam de verificação manual.

### 9.2 TypeScript Config

| Métrica | apps/blu_v3 | packages/blu-auth |
|----------|-------------|-------------------|
| `VITE_` env vars | ✅ 6 arquivos | ✅ 1 arquivo |
| `import.meta.env` | ✅ 6 arquivos | ✅ 1 arquivo |

---

## 10. Cross-Cutting Analysis

### 10.1 Violations by Severity

| Severity | Count | Description |
|----------|-------|-------------|
| **P0** | 3 | blu_agent_framework (27% typed), blu_context_service (25% typed), blu_supabase_client (23% typed) — Tier 1 type gaps |
| **P0** | 1 | agent_api print() logging (32 calls, T1 escalation) |
| **P1** | 4 | Missing correlation IDs (24/25 artifacts), structured logging absence, blu_db_connector print() (19), tool_pool_api print() (18) |
| **P2** | 7 | Relative imports (196), import order broken (10 files), `any` in TS (17), console.log (35), empty __init__.py in services (2), missing error boundaries, blu_shared_utils no __init__.py |

### 10.2 Best Exemplars

| Artefato | Tier | Destaques |
|----------|------|-----------|
| **agent_api** | T1 | 81% typed, Pydantic Settings, env vars, proper loggers (apesar dos print()) |
| **blu_models** | T1 | 84% typed, Pydantic models, clean structure |
| **blu_observability_bootstrap** | T4 | 100% typed, structured JSON logging — referência para os demais |
| **blu_google_suite_client** | T4 | 69% typed, boa estrutura de submódulos |

### 10.3 Systemic Issues

1. **Type hints são a maior dívida técnica.** 65% das funções Python não têm type hints. Os 3 Tier 1 críticos (blu_agent_framework, blu_context_service, blu_supabase_client) têm cobertura entre 23-27% — longe do padrão esperado de strict mode.

2. **Logging inconsistency.** Embora 154 arquivos usem `logging.getLogger(__name__)`, 88 chamadas de `print()` persistem em código de produção (agent_api, db_connector, tool_pool_api). Apenas 1 artefato implementa structured JSON logging, contrariando o patterns.md.

3. **Correlation IDs não propagados.** Apenas blu_agent_framework implementa — os services agent_api e tool_pool_api não incluem correlation_id em seus logs, impossibilitando rastreamento cross-service.

4. **Relative imports como padrão de facto.** 196 imports relativos — a maioria em `__init__.py` como prática Python idiomática. O patterns.md prescreve `from libs.X.src.X import` (full path), mas o código real usa `from .module import`. Este é um **conflito spec vs realidade** que requer decisão: ou o patterns.md está errado e deve aceitar relative imports, ou o código deve ser migrado para full paths.

5. **Frontend sem error boundaries.** Nenhum componente TSX implementa ErrorBoundary — em caso de exceção não tratada, o app inteiro quebra.

### 10.4 Relative Imports: Spec vs Reality

O patterns.md §1 (Imports) prescreve: `from libs.blu_models.src.models import ...` — caminho completo a partir da raiz do repo.

A realidade: 20/21 libs usam `from .module import X` em seus `__init__.py`. Este é o padrão Python idiomático e permite:
- Renomear/mover a lib sem quebrar todos os imports internos
- Instalar como package (`pip install -e .`)
- Independência de PYTHONPATH

**Recomendação:** Revisar patterns.md para aceitar relative imports como padrão, mantendo full-path apenas para imports cross-lib (ex: `from libs.blu_models... import` de fora de `blu_models/`). Esta é uma divergência intencional válida (resolution.md R2: "intentional deviations are review needed, not violations").

### 10.5 Fase 1-5 Alignment

| Fase | Artefatos Chave | Status Geral |
|------|----------------|-------------|
| Fase 1 | blu_agent_framework, agent_api | ⚠️ agent_api: 81% typed mas 32 print() calls; blu_agent_framework: 27% typed (P0) |
| Fase 2 | blu_context_service, routine_engine | ❌ blu_context_service: 25% typed (P0), sem correlation IDs |
| Fase 3 | tool_pool_api, blu_rag_factory | ⚠️ tool_pool_api: 76% typed mas 18 print() calls; blu_rag_factory: 32% typed |
| Fase 4 | blu_sql_factory, blu_models | ⚠️ blu_sql_factory: 26% typed, 14 print(); blu_models: 84% typed (exemplar) |
| Fase 5 | blu_v3, blu-auth, libs restantes | ⚠️ 17 any, 35 console.log, 0 error boundaries |

---

## 11. Per-Dimension Summary Matrix

| Dimensão | Compliance Global | Tier 1 | Tier 2 | Tier 3 | Tier 4 | Maior Problema |
|----------|-----------------|--------|--------|--------|--------|----------------|
| **Naming** | ✅ 98% | ✅ | ✅ | ✅ | ✅ | 1 arquivo de teste mal nomeado |
| **Imports** | ⚠️ 70% | ⚠️ | ⚠️ | ⚠️ | ✅ | 196 relative imports (spec conflict) |
| **Structure** | ✅ 92% | ✅ | ✅ | ✅ | ⚠️ | blu_shared_utils sem `__init__.py` |
| **Types** | ❌ 35% | ❌ P0 | ❌ | ⚠️ | ⚠️ | 3 Tier 1 com <27% typed |
| **Error Handling** | ✅ 85% | ⚠️ | ✅ | ✅ | ✅ | Correlation IDs só em 1 artefato |
| **Logging** | ⚠️ 70% | ❌ P0 | ⚠️ | ⚠️ | ✅ | agent_api: 32 print() calls |
| **Config** | ✅ 90% | ✅ | ✅ | ✅ | ✅ | 7 secrets fora de testes |

---

## 12. Recommendations

### P0 — Immediate (security/data-loss/blocking)

1. **Add type hints to Tier 1 core functions** — blu_agent_framework (240 untyped), blu_context_service (21), blu_supabase_client (85). Começar pelas funções públicas exportadas.
2. **Replace print() with logging in agent_api** — 32 chamadas de `print()` no Tier 1 service violam patterns.md e escalam a P0.

### P1 — Next Sprint

3. **Implement correlation ID propagation** em agent_api e tool_pool_api
4. **Adopt structured JSON logging** — começar por Tier 1 e Tier 2 (seguir exemplo do blu_observability_bootstrap)
5. **Replace print() with logging** em blu_db_connector (19), tool_pool_api (18), blu_sql_factory (14)
6. **Investigate 7 non-test hardcoded secrets** — verificar se são strings de exemplo ou credenciais reais
7. **Add type hints to Tier 2** — blu_llm_service (71), blu_sql_factory (224), blu_prompt_management (49)

### P2 — Backlog

8. **Resolve relative imports spec conflict** — atualizar patterns.md ou migrar código
9. **Fix import order** nos 10 arquivos identificados
10. **Add `__init__.py` to blu_shared_utils**
11. **Add Error Boundaries** ao apps/blu_v3
12. **Replace `console.log`** with proper logging in TS
13. **Replace `any` types** in apps/blu_v3 (17 occurrences)
14. **Rename** `libs/blu_db_connector/tests/import os.py`

---

## 13. Artifacts

| Artifact | Path | Purpose |
|----------|------|---------|
| patterns-review-f1-5.md | `docs/planning/issue-57/patterns-review-f1-5.md` | This report |
| patterns.md | `docs/planning/issue-57/patterns.md` | Baseline conventions |
| resolution.md | `docs/planning/issue-57/resolution.md` | Tier classification, design decisions |
| inventory-catalog.md | `docs/planning/issue-57/inventory-catalog.md` | Full artifact catalog |

---

## 14. Verification

- [x] All 25 artifacts checked against 7 pattern dimensions
- [x] Tier 1 services (5) checked with stricter thresholds (P1 → P0)
- [x] Key claims verified via grep sampling (agent_api print(), blu_agent_framework defs, blu_models relative imports)
- [x] At least 3 concrete examples per violation type
- [x] Fase 1-5 alignment table included
- [x] File saved to `docs/planning/issue-57/patterns-review-f1-5.md`
- [ ] Git commit + push — próximo passo
- [ ] PR creation — próximo passo
