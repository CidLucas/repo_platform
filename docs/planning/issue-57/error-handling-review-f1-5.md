# error-handling-review-f1-5.md — Error Handling Analysis (Fases 1-5)

> **Gerado por:** factory-coder (t_9d2c1caa), 2026-06-23  
> **Escopo:** 25 artefatos de Fases 1-5 (21 libs, 2 services, 1 app, 1 package)  
> **Fonte:** scan automatizado de todos os arquivos Python (excluindo `test/`, `.venv/`, `__pycache__/`)  
> **Depende de:** `inventory-catalog.md` (T57.1), `error-handling-review.md` (original), `resolution.md`

---

## 1. Executive Summary

| Métrica | Valor | Status |
|----------|-------|--------|
| Total de artefatos escaneados | **25** (21 libs, 2 services, 1 app, 1 package) | — |
| Total de blocos `except` | **932** | — |
| `except:` bare (sem tipo) | **0** | ✅ |
| `except Exception:` (broad) | **625** (67.1%) | ❌ P0 |
| `except <SpecificError>:` | **307** (32.9%) | ⚠️ P1 |
| Artefatos com custom exceptions | **9** de 25 (36%) | ⚠️ P1 |
| Total de classes de exceção custom | **14** | — |
| Base class comum | **Nenhuma** | ⚠️ P1 |
| Retry com backoff (tenacity/backoff) | **0** — biblioteca não usada | ❌ P1 |
| Circuit breaker implementado | **2** (langfuse + routines) | ⚠️ P2 |
| `print()` em código-fonte | **144** chamadas | ⚠️ P2 |
| `logger.*` chamadas | **1,822** chamadas | ✅ |
| `logger.exception()` (com traceback) | **131** chamadas | ✅ |
| `logger.error()` | **283** chamadas | ✅ |
| Structured JSON logging | **0** — apenas formatador Grafana | ⚠️ P2 |
| Error swallowing (`except: pass`) | **0** | ✅ |
| Error swallowing (`except: return None`) | **0** | ✅ |
| `raise ... from exc` (chain preservation) | **Parcial** — 4 artefatos usam | ⚠️ P2 |
| Artefatos P0 (Tier 1 com >50% broad) | **5** de 5 (100%) | ❌ P0 |
| Artefatos P1 (crítico Tier 2+) | **4** | ❌ P1 |
| Artefatos sem nenhum `except` | **1** (blu_shared_utils) | ✅ |
| Artefatos sem Python | **1** (blu_v3 — frontend TSX) | ✅ |

**Resumo narrativo:** O codebase tem **zero bare excepts**, zero error swallowing, e usa `logger.exception()` adequadamente em 131 pontos — pontos fortes. No entanto, **67% dos 932 blocos except são broad (`except Exception`)**, 16 dos 25 artefatos não têm hierarchy de exceções customizada, **nenhum artefato usa biblioteca de retry** (tenacity/backoff), e os circuit breakers são implementações ad-hoc duplicadas entre `blu_observability_bootstrap` e `blu_prompt_management`. Tier 1 inteiro está em P0: todos os 5 artefatos críticos têm >75% de broad excepts. `blu_auth` e `blu_elicitation_service` são os melhores exemplos de tratamento de erro específico (39% e 0% broad, respectivamente, com hierarchies de exceção bem definidas).

---

## 2. Methodology

### 2.1 Scanning Approach
- Scanner Python percorreu todos os arquivos `.py` nos 25 artefatos (excluindo `test/`, `tests/`, `.venv/`, `__pycache__/`, `node_modules/`, `dist/`, `build/`)
- Regex matching para: `except <tipo>`, classes de exceção custom, `print(`, `logger.`, `raise`, padrões de retry/circuit breaker
- Verificações manuais complementares via `grep` para: retry decorators, circuit breaker implementations, error swallowing, `raise from`, structured logging

### 2.2 Dimensions Checked
1. **Broad vs Specific**: Proporção de `except Exception` vs `except <SpecificError>`
2. **Custom Exception Hierarchy**: Classes de exceção por artefato, herança, base comum
3. **Retry/Circuit Breaker**: Uso de tenacity/backoff, implementações ad-hoc de retry/circuit breaker
4. **Logging**: `print()` vs `logger.*`, `logger.exception()` vs `logger.error()`, structured logging
5. **Error Propagation**: `raise from exc` (chain preservation), re-raise vs swallow
6. **Bare Excepts**: `except:` sem tipo (SystemExit/KeyboardInterrupt risk)

### 2.3 Tier Classification (per resolution.md §DQ3)
| Tier | Criticality | Count | Threshold |
|------|-------------|-------|-----------|
| **Tier 1** | Crítico | 5 (agent_api, blu_agent_framework, blu_supabase_client, blu_models, blu_context_service) | P1 → P0 escalation |
| **Tier 2** | Alto | 5 (tool_pool_api, blu_llm_service, blu_rag_factory, blu_prompt_management, blu_sql_factory) | Standard |
| **Tier 3** | Médio | 4 (blu_auth, blu_hitl_service, blu_data_connectors, blu_db_connector) | Standard |
| **Tier 4** | Baixo | 11 (demais libs + routine_engine + apps/blu_v3) | Relaxed |

---

## 3. Per-Artifact Error Handling Profile

### 3.1 Tier 1 — Crítico (Core Infra)

| Artifact | Files | Lines | Total Excepts | Broad Excepts | Specific Excepts | Custom Exceptions | Retry Hits | Print/Log | Status |
|----------|-------|-------|---------------|---------------|-------------------|--------------------|------------|-----------|--------|
| **agent_api** | 23 | 9,844 | 123 | 98 (79%) | 25 | — | 12 | 50/238 | ❌ P0 |
| **blu_agent_framework** | 25 | 8,985 | 72 | 64 (88%) | 8 | ApprovalError, SkillTurnLimitError, WorkerTurnLimitError | 23 | 4/163 | ❌ P0 |
| **blu_supabase_client** | 8 | 1,683 | 21 | 19 (90%) | 2 | AuditError | 18 | 0/49 | ❌ P0 |
| **blu_models** | 25 | 4,169 | 2 | 2 (100%) | 0 | — | 1 | 0/0 | ❌ P0 |
| **blu_context_service** | 6 | 2,052 | 49 | 43 (87%) | 6 | — | 0 | 0/84 | ❌ P0 |

**Análise Tier 1:**
- **agent_api** (❌ P0): 79% broad excepts. 50 chamadas `print()` (vs 238 `logger`), concentradas em `run_routine.py` (32 prints), `_debug_patch.py`, `_debug_patch2.py`. Top broad-except files: `routine_functions.py` (22), `routines.py` (20), `service.py` (13), `agents_router.py` (11), `routine_artifacts.py` (11). **Sem custom exceptions** — usa `HTTPException` do FastAPI diretamente. Circuit breaker implementado em `routines.py` (P1 feature com `_CIRCUIT_BREAKER_MAX_FAILURES = 3`). Retry keyword hits são apenas comentários/documentação, não implementações reais.
- **blu_agent_framework** (❌ P0): 88% broad excepts. Melhor que agent_api em organização: tem 3 custom exceptions (`ApprovalError(RuntimeError)`, `SkillTurnLimitError`, `WorkerTurnLimitError`) e logging consistente (163 `logger` vs 4 `print`). **Ponto forte:** `raise ... from exc` usado em `approval.py` (3 ocorrências). **Ponto fraco:** `SkillTurnLimitError` e `WorkerTurnLimitError` herdam de `Exception` genérico, não de base comum.
- **blu_supabase_client** (❌ P0): 90% broad excepts. Apenas 2 specific excepts entre 21. Tem `AuditError(RuntimeError)` como única custom exception. `logger` consistente (49 chamadas), zero `print`.
- **blu_models** (❌ P0): Apenas 2 except blocks — ambos broad. Sem custom exceptions. Sem logging (0 `logger`, 0 `print`). Impacto baixo (poucos excepts), mas como Tier 1, escalado a P0.
- **blu_context_service** (❌ P0): 87% broad excepts (43 de 49). **Sem custom exceptions.** 84 chamadas `logger`, zero `print`. Top broad-except file: `context_service.py` (36 broad excepts). Usa `raise ... from exc` em `context_service.py:935`.

**Gap Tier 1 comum:** Nenhum artefato Tier 1 tem hierarchy de exceção com base comum. `blu_agent_framework` é o único com múltiplas classes de exceção. Nenhum usa tenacity/backoff para retry.

### 3.2 Tier 2 — Alto (Strategic Services)

| Artifact | Files | Lines | Total Excepts | Broad Excepts | Specific Excepts | Custom Exceptions | Retry Hits | Print/Log | Status |
|----------|-------|-------|---------------|---------------|-------------------|--------------------|------------|-----------|--------|
| **tool_pool_api** | 67 | 27,227 | 383 | 222 (57%) | 161 | RAGClientError | 4 | 26/559 | ⚠️ P2 |
| **blu_llm_service** | 6 | 1,853 | 11 | 3 (27%) | 8 | — | 24 | 0/36 | ⚠️ P2 |
| **blu_rag_factory** | 6 | 1,332 | 12 | 8 (66%) | 4 | — | 0 | 0/63 | ⚠️ P2 |
| **blu_prompt_management** | 6 | 5,825 | 11 | 7 (63%) | 4 | PromptNotFoundError | 14 | 0/32 | ⚠️ P2 |
| **blu_sql_factory** | 18 | 5,373 | 25 | 19 (76%) | 6 | ParseError | 2 | 14/97 | ⚠️ P2 |

**Análise Tier 2:**
- **tool_pool_api** (⚠️ P2): Maior codebase (67 files, 27K lines, 383 excepts). 57% broad — **melhor proporção entre os artefatos grandes**. 161 specific excepts é o maior número absoluto. Usa `ToolError` extensivamente em `platform_module.py`, `pm_module.py`, `rfq_module.py`. Apenas 1 custom exception (`RAGClientError`). 26 `print()` vs 559 `logger` — bem estruturado.
- **blu_llm_service** (⚠️ P2): **Melhor artefato Tier 2 em especificidade** — apenas 27% broad. Zero `print`, 36 `logger`. **Sem custom exceptions**.
- **blu_rag_factory** (⚠️ P2): 66% broad. Zero `print`, 63 `logger`. Sem custom exceptions.
- **blu_prompt_management** (⚠️ P2): 63% broad. **Circuit breaker implementado para Langfuse** (`loader.py:77`). `PromptNotFoundError(Exception)` como custom exception. Zero `print`, 32 `logger`.
- **blu_sql_factory** (⚠️ P2): 76% broad. 14 `print()` (scripts CLI). `ParseError(Exception)` como custom exception. 97 `logger`.

### 3.3 Tier 3 — Médio (Feature Support)

| Artifact | Files | Lines | Total Excepts | Broad Excepts | Specific Excepts | Custom Exceptions | Retry Hits | Print/Log | Status |
|----------|-------|-------|---------------|---------------|-------------------|--------------------|------------|-----------|--------|
| **blu_auth** | 24 | 1,291 | 33 | 13 (39%) | 20 | AuthError | 0 | 0/44 | ✅ |
| **blu_hitl_service** | 4 | 1,135 | 12 | 7 (58%) | 5 | — | 0 | 0/20 | ⚠️ P2 |
| **blu_data_connectors** | 13 | 1,799 | 21 | 15 (71%) | 6 | AuthenticationError, EcommerceConnectorError, ExecutionError | 2 | 0/45 | ⚠️ P2 |
| **blu_db_connector** | 9 | 817 | 12 | 8 (66%) | 4 | — | 0 | 19/30 | ⚠️ P2 |

**Análise Tier 3:**
- **blu_auth** (✅): **Melhor artefato do codebase em error handling.** Apenas 39% broad excepts. Hierarchy de exceção exemplar: `AuthError(Exception)` com 7 subclasses documentadas em `core/exceptions.py`. Zero `print`, 44 `logger`. **Modelo a ser seguido.**
- **blu_hitl_service** (⚠️ P2): 58% broad. Sem custom exceptions. Zero `print`, 20 `logger`.
- **blu_data_connectors** (⚠️ P2): 71% broad. 3 custom exceptions. `raise ... from e` em `factory.py:85`. Zero `print`, 45 `logger`.
- **blu_db_connector** (⚠️ P2): 66% broad. 19 `print()` em scripts CLI. `raise ... from e` em `operations.py:190`. Sem custom exceptions.

### 3.4 Tier 4 — Baixo (Support)

| Artifact | Files | Lines | Total Excepts | Broad Excepts | Specific Excepts | Custom Exceptions | Retry Hits | Print/Log | Status |
|----------|-------|-------|---------------|---------------|-------------------|--------------------|------------|-----------|--------|
| **blu_elicitation_service** | 7 | 1,343 | 12 | 0 (0%) | 12 | ElicitationError | 0 | 0/6 | ✅ |
| **blu_experiment_service** | 9 | 2,535 | 14 | 11 (78%) | 3 | — | 1 | 1/90 | ⚠️ P2 |
| **blu_google_suite_client** | 14 | 698 | 8 | 1 (12%) | 7 | — | 0 | 0/0 | ✅ |
| **blu_landing_intel** | 3 | 195 | 1 | 1 (100%) | 0 | — | 0 | 0/0 | ❌ P1 |
| **blu_observability_bootstrap** | 5 | 1,648 | 52 | 38 (73%) | 14 | — | 4 | 0/87 | ⚠️ P2 |
| **blu_parsers** | 13 | 1,243 | 15 | 9 (60%) | 6 | — | 0 | 0/50 | ⚠️ P2 |
| **blu_shared_utils** | 2 | 66 | 0 | 0 | 0 | — | 0 | 0/0 | ✅ |
| **blu_tool_registry** | 10 | 4,039 | 8 | 7 (87%) | 1 | ToolRegistryError | 0 | 0/33 | ❌ P1 |
| **blu_twilio_client** | 4 | 799 | 15 | 15 (100%) | 0 | — | 0 | 0/34 | ❌ P1 |
| **routine_engine** | 6 | 1,417 | 20 | 15 (75%) | 5 | — | 7 | 30/62 | ⚠️ P2 |
| **blu_v3** | 0 | 0 | 0 | 0 | 0 | — | 0 | 0/0 | ✅ |

---

## 4. Cross-Cutting Findings

### 4.1 Custom Exception Hierarchy
**14 custom exception classes** em **9 artefatos**. **16 artefatos sem custom exceptions** — incluindo 3 Tier 1 (agent_api, blu_models, blu_context_service).

**Finding P1 — Sem base class comum:** Não existe `BluError(Exception)` como raiz para todas as exceções do monorepo.

### 4.2 Retry & Circuit Breaker
**Retry library: NÃO UTILIZADA** (❌ P1). Zero imports de `tenacity` ou `backoff` em código fonte.

**Circuit breaker: 2 implementações ad-hoc** (⚠️ P2):
1. Langfuse circuit breaker duplicado em `blu_observability_bootstrap` e `blu_prompt_management`
2. Routine circuit breaker em `agent_api/routines.py` (implementação correta)

### 4.3 Logging
- 1,822 `logger.*` vs 144 `print()` (92.7% logger) ✅
- 131 `logger.exception()` (traceback logging) ✅
- Zero structured JSON logging (⚠️ P2)
- `routine_engine`: 30 prints (preocupante para serviço)

### 4.4 Error Propagation
- `raise ... from exc`: apenas ~6 usos em 932 except blocks (⚠️ P2)
- Zero error swallowing ✅
- Re-raise pattern comum com `logger.exception()`

### 4.5 Bare Excepts
**0 bare excepts** ✅ — excelente.

---

## 5. Findings by Severity

### P0 — Imediato
| ID | Artefato | Finding |
|----|----------|---------|
| EH-P0-01 | agent_api | 79% broad excepts, Tier 1, sem custom exceptions |
| EH-P0-02 | blu_agent_framework | 88% broad excepts, orquestrador mascara falhas críticas |
| EH-P0-03 | blu_supabase_client | 90% broad excepts, falhas de DB indiferenciadas |
| EH-P0-04 | blu_context_service | 87% broad excepts, dependency de todos os agents |
| EH-P0-05 | blu_models | 100% broad, Tier 1 sem tratamento específico |

### P1 — Próximo Sprint
| ID | Artefato | Finding |
|----|----------|---------|
| EH-P1-01 | Global | Zero uso de retry library (tenacity/backoff) |
| EH-P1-02 | Global | 16/25 artefatos sem custom exceptions |
| EH-P1-03 | Global | Sem base class comum (BluError) |
| EH-P1-04 | tool_pool_api | 222 broad excepts (maior número absoluto) |
| EH-P1-05 | blu_twilio_client | 100% broad excepts |
| EH-P1-06 | blu_tool_registry | ToolRegistryError definida mas subutilizada |
| EH-P1-07 | routine_engine | 75% broad + 30 print() |
| EH-P1-08 | blu_landing_intel | 100% broad |

### P2 — Backlog
| ID | Artefato | Finding |
|----|----------|---------|
| EH-P2-01 | blu_observability_bootstrap + blu_prompt_management | Circuit breaker Langfuse duplicado |
| EH-P2-02 | Global | raise from exc em apenas ~6 pontos |
| EH-P2-03 | Global | Zero structured JSON logging |
| EH-P2-04 | blu_auth | secret_manager raise Exception sem from e |
| EH-P2-05 | blu_sql_factory | ValidationError não herda de Exception |
| EH-P2-06 | blu_data_connectors | AuthenticationError duplicada |
| EH-P2-07 | blu_experiment_service | 1 print() em cli.py |

---

## 6. Positive Findings

| ID | Finding |
|----|---------|
| ✅ | Zero bare excepts em 25 artefatos |
| ✅ | Zero error swallowing |
| ✅ | 131 logger.exception() calls — tracebacks preservados |
| ✅ | blu_auth: modelo de hierarchy (AuthError + 7 subclasses, 39% broad) |
| ✅ | blu_elicitation_service: 0% broad, todas capturas específicas |
| ✅ | blu_llm_service: 27% broad — melhor Tier 2 |
| ✅ | logger domina print: 1,822 vs 144 (92.7%) |
| ✅ | Circuit breaker routines.py: implementação correta |

---

## 7. Recommendations

### Immediate (P0)
1. Substituir `except Exception` por exceções específicas nos 5 artefatos Tier 1
2. Criar custom exceptions: `AgentAPIError`, `ContextServiceError`, `SupabaseClientError`, `ModelError`
3. blu_context_service: separar cache miss de DB failure

### Next Sprint (P1)
4. Adotar `tenacity` como biblioteca padrão de retry
5. Criar `blu_core.exceptions.BluError(Exception)` como base comum
6. Criar custom exceptions para os 16 artefatos sem hierarchy
7. blu_twilio_client: `TwilioError` com subclasses
8. blu_tool_registry: usar hierarchy já definida

### Backlog (P2)
9. Extrair circuit breaker Langfuse para shared lib
10. Adotar `raise ... from exc` consistentemente
11. Migrar routine_engine de print() para logger
12. Adotar structlog para JSON logging
13. blu_sql_factory: ValidationError herdar de Exception

---

## 8. Artifact Checklist

| # | Artifact | Tier | Excepts | Broad% | Custom Exc | Status |
|---|----------|------|---------|--------|------------|--------|
| 1 | agent_api | 1 | 123 | 79% | ❌ | ❌ P0 |
| 2 | blu_agent_framework | 1 | 72 | 88% | ✅ | ❌ P0 |
| 3 | blu_supabase_client | 1 | 21 | 90% | ✅ | ❌ P0 |
| 4 | blu_models | 1 | 2 | 100% | ❌ | ❌ P0 |
| 5 | blu_context_service | 1 | 49 | 87% | ❌ | ❌ P0 |
| 6 | tool_pool_api | 2 | 383 | 57% | ✅ | ⚠️ P2 |
| 7 | blu_llm_service | 2 | 11 | 27% | ❌ | ⚠️ P2 |
| 8 | blu_rag_factory | 2 | 12 | 66% | ❌ | ⚠️ P2 |
| 9 | blu_prompt_management | 2 | 11 | 63% | ✅ | ⚠️ P2 |
| 10 | blu_sql_factory | 2 | 25 | 76% | ✅ | ⚠️ P2 |
| 11 | blu_auth | 3 | 33 | 39% | ✅ | ✅ |
| 12 | blu_hitl_service | 3 | 12 | 58% | ❌ | ⚠️ P2 |
| 13 | blu_data_connectors | 3 | 21 | 71% | ✅ | ⚠️ P2 |
| 14 | blu_db_connector | 3 | 12 | 66% | ❌ | ⚠️ P2 |
| 15 | blu_elicitation_service | 4 | 12 | 0% | ✅ | ✅ |
| 16 | blu_experiment_service | 4 | 14 | 78% | ❌ | ⚠️ P2 |
| 17 | blu_google_suite_client | 4 | 8 | 12% | ❌ | ✅ |
| 18 | blu_landing_intel | 4 | 1 | 100% | ❌ | ❌ P1 |
| 19 | blu_observability_bootstrap | 4 | 52 | 73% | ❌ | ⚠️ P2 |
| 20 | blu_parsers | 4 | 15 | 60% | ❌ | ⚠️ P2 |
| 21 | blu_shared_utils | 4 | 0 | — | ❌ | ✅ |
| 22 | blu_tool_registry | 4 | 8 | 87% | ✅ | ❌ P1 |
| 23 | blu_twilio_client | 4 | 15 | 100% | ❌ | ❌ P1 |
| 24 | routine_engine | 4 | 20 | 75% | ❌ | ⚠️ P2 |
| 25 | blu_v3 | 4 | 0 | — | ❌ | ✅ |

---

*Fim do relatório. Artefato salvo como docs/planning/issue-57/error-handling-review-f1-5.md.*
