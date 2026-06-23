# error-handling-review-f1-5.md — Error Handling Analysis (Fases 1-5)

> **Gerado por:** factory-coder (t_9d2c1caa), 2026-06-23
> **Escopo:** 25 artefatos de Fases 1-5 (21 libs, 2 services, 1 app, 1 package)
> **Fonte:** deep scan + leitura de código de `libs/`, `services/`, `apps/`, `packages/` (src only)
> **Branch:** `feat/b5-error-handling-review-f1-5`
> **Depende de:** `inventory-catalog.md` (T57.1), `error-handling-review.md` (Phase 0 baseline), `resolution.md` (DQ3 tier classification), `patterns-review-f1-5.md`

---

## 1. Executive Summary

| Métrica | Phase 0 (grep) | Phase 1-5 (src deep scan) | Delta |
|----------|:---:|:---:|:---:|
| `except` blocks total (src) | ~1,100+ | ~618 (src only, excl. tests) | — |
| Bare `except:` (sem tipo) | 0 | 0 (190 em .venv de terceiros) | ✅ Confirmado |
| `except Exception:` (broad, src) | ~273+ | **619** (tool_pool_api: 221, agent_api: 94, blu_agent_framework: 64) | ⚠️ Revisado para cima |
| Custom exception hierarchies | 8 libs | **9 artifacts** (8 libs + tool_pool_api RAGClientError) | +1 (tool_pool_api) |
| Retry com backoff | 2 | **3** (MCP + LLM text-to-sql + MCP executor) | +1 (MCP executor) |
| Circuit breaker | 3 | **3** (Langfuse ×2 + routines) | ✅ Confirmado |
| Correlation IDs artifacts | 1 | **6** (blu_agent_framework, blu_supabase_client, blu_models, blu_context_service, blu_hitl_service, blu_experiment_service, agent_api) | +5 |
| str(exc) exposto via HTTPException | 6 locais | **14 locais** (2 agent_api + 12 tool_pool_api) | ⚠️ Revisado para cima |
| print() como logging | ~88 | **39** (src only, 5 artefatos) | Melhor que estimado |
| libs SEM custom exceptions | 12/21 | **12/21** | ✅ Confirmado |
| Services SEM custom exceptions | 2/2 | **2/2** (usam HTTPException direto) | ✅ Confirmado |
| Error Boundaries (TSX) | 0 | **0** | ✅ Confirmado |
| Frontend `catch` sem tipo | ~20 try/catch | **21 `catch (err)`** sem tipo | ✅ |

**Resumo narrativo:** O codebase tem excelente disciplina de bare excepts (zero) e 9 artefatos com hierarchies de exceção próprias. Os problemas sistêmicos concentram-se em **`except Exception` excessivo nos services (619 total, especialmente tool_pool_api com 221)**, **exposição de stack traces via `str(exc)` em 14 endpoints HTTP**, **ausência de retry/circuit breaker para Supabase e Redis (Tier 1)** e **12 libs sem hierarchy de exceções própria**. O correlation ID, embora bem implementado no `blu_agent_framework`, não é propagado para as libs downstream. O frontend não tem Error Boundaries e usa `catch (err)` sem tipagem em 21 locais.

---

## 2. Methodology

### 2.1 Scan Approach (Phase 1-5 vs Phase 0)

| Aspecto | Phase 0 | Phase 1-5 |
|---------|---------|-----------|
| Escopo | grep em todo tree (inclui tests) | grep + leitura de código (src apenas) |
| Profundidade | Contagem de ocorrências | Análise contextual (re-raise vs swallow, fallback, PT-BR) |
| Exclusões | `__pycache__/`, `.venv/`, `node_modules/` | Mesmo + `tests/`, `build/`, `dist/` |
| Ferramentas | grep, rg | grep + read_file + análise manual |
| Artefatos | 25 | 25 (mesmos) |

### 2.2 Dimensions Verified (per error-handling-review.md §DQ)

1. **Exception Hierarchy**: custom exception classes, herança, base comum
2. **Specific vs Broad Except**: bare except, `except Exception`, `except SpecificError`
3. **Retry Policies**: exponential backoff, max_retries, Retry-After header
4. **Circuit Breakers**: cooldown, fail-fast, suspension after N failures
5. **Error Propagation**: re-raise vs swallow, `str(exc)` exposure, stack trace leakage
6. **Logging**: `logger.error`/`logger.exception` vs `print()`, structured JSON, correlation IDs
7. **Frontend**: Error Boundaries, typed catch, `console.log` as error logging

### 2.3 Tier Classification (per resolution.md §DQ3)

| Tier | Criticality | Count | Threshold Adjustment |
|------|-------------|-------|---------------------|
| **Tier 1** | Crítico | 5 (blu_agent_framework, blu_supabase_client, blu_models, blu_context_service, agent_api) | P1 → P0 escalation |
| **Tier 2** | Alto | 5 (tool_pool_api, blu_llm_service, blu_rag_factory, blu_prompt_management, blu_sql_factory) | Standard |
| **Tier 3** | Médio | 4 (blu_auth, blu_hitl_service, blu_data_connectors, blu_db_connector) | Standard |
| **Tier 4** | Baixo | 11 (demais libs + apps/blu_v3 + packages/blu-auth) | Relaxed |

---

## 3. Exception Hierarchy Deep-Dive

### 3.1 Custom Exception Classes — Análise de Qualidade

#### Excelente (hierarchy completa com 4+ subclasses)

**blu_auth** — Melhor implementação do codebase:
- `AuthError(Exception)` como raiz com `message` + `code`
- 7 subclasses: `MissingCredentialsError`, `InvalidTokenError`, `TokenExpiredError`, `InvalidSignatureError(InvalidTokenError)`, `InvalidApiKeyError`, `ClientNotFoundError`, `AuthDisabledError`
- Cada subclasse tem código de erro único (ex: `MISSING_CREDENTIALS`, `INVALID_SIGNATURE`)
- Nested inheritance: `InvalidSignatureError → InvalidTokenError → AuthError`

**blu_elicitation_service** — Bem estruturada:
- `ElicitationError(Exception)` com `message` + `code`
- 4 subclasses: `ElicitationValidationError`, `ElicitationTimeoutError`, `ElicitationNotFoundError`
- Campos específicos por subclasse (`elicitation_id`, `timeout_seconds`, `session_id`)

**blu_tool_registry** — Clara e funcional:
- `ToolRegistryError(Exception)` como base
- 4 subclasses: `ToolNotFoundError`, `TierAccessDeniedError`, `DockerMCPConnectionError`, `ToolValidationError`
- Cada subclasse com campos contextuais (`tool_name`, `required_tier`, `integration`, `reason`)

**blu_data_connectors** — Bem intencionada mas com duplicação:
- `EcommerceConnectorError(Exception)` como base
- 2 subclasses: `RateLimitError`, `AuthenticationError(EcommerceConnectorError)`
- ⚠️ `AuthenticationError` duplicada: também existe em `accounting/conta_azul_connector.py` herdando de `Exception` diretamente

#### Adequado (1-3 classes, funcional)

| Lib | Classes | Herança | Observação |
|-----|---------|---------|------------|
| **blu_agent_framework** | `ApprovalError(RuntimeError)`, `SkillTurnLimitError(Exception)`, `WorkerTurnLimitError(Exception)` | 3 classes independentes | ⚠️ Sem base comum |
| **blu_supabase_client** | `AuditError(RuntimeError)` | Única | Funcional mas limitada |
| **blu_prompt_management** | `PromptNotFoundError(Exception)` | Única | Suficiente para o escopo |
| **blu_sql_factory** | `ParseError(Exception)`, `ValidationError` (plain class) | ⚠️ `ValidationError` não herda de Exception | P2 |
| **tool_pool_api** | `RAGClientError(Exception)` | Única (em `server/utils/`) | Não cobre API routers |

#### Ausente (12 libs sem hierarchy própria)

`blu_models`, `blu_context_service`, `blu_llm_service`, `blu_rag_factory`, `blu_hitl_service`, `blu_db_connector`, `blu_google_suite_client`, `blu_experiment_service`, `blu_landing_intel`, `blu_observability_bootstrap`, `blu_parsers`, `blu_twilio_client`

### 3.2 Common Base Class — Análise

**Não existe classe base comum** para exceções do monorepo. Cada lib define (ou não) sua própria hierarchy independente. Isto significa:
- Impossível capturar "qualquer erro do projeto" sem `except Exception`
- Sem distinção entre "erro da aplicação" e "erro de sistema/programação"
- Código de integração não pode diferenciar erros de negócio de crashes

**Recomendação arquitetural:** Criar `blu_core.exceptions.BluError(Exception)` como base comum com suporte a `code`, `message`, `correlation_id`.

---

## 4. Specific vs Broad Except — Análise Contextual

### 4.1 Bare `except:` — Confirmado Zero ✅

Zero bare excepts no código fonte. Os 190 hits são todos em `.venv/` (bibliotecas de terceiros: `setuptools`, `pip`, `coverage`, `rich`, `h11`, etc.). **Conformidade exemplar.**

### 4.2 `except Exception:` — Breakdown por Artefato (src only)

| Artefato | Tier | Count | Contexto Predominante | Severidade |
|----------|:----:|:-----:|-----------------------|:----------:|
| **tool_pool_api** | T2 | **221** | Fallback em integrations, inbox dispatch, webhook, reports | ⚠️ P1 |
| **agent_api** | T1 | **94** | Routers, service.py, async generators SSE | ⚠️ P1 (T1 → P0) |
| **blu_agent_framework** | T1 | **64** | Orchestrator, builder, skill factory, checkpointer | ⚠️ P1 (T1 → P0) |
| **blu_context_service** | T1 | **43** | Cache operations, context reads/writes | ⚠️ P1 (T1 → P0) |
| **blu_observability_bootstrap** | T4 | **38** | Langfuse client, ingestion pipelines | P2 |
| **blu_supabase_client** | T1 | **19** | RPC calls, REST operations | ⚠️ P1 (T1 → P0) |
| **blu_sql_factory** | T2 | **16** | SQL parsing, validation, generation | P2 |
| **blu_rag_factory** | T2 | **8** | Document indexing, retrieval | P2 |
| **blu_tool_registry** | T4 | **7** | Tool execution, catalog loading | P2 |
| **blu_prompt_management** | T2 | **7** | Prompt loading, Langfuse fetch | P2 |
| **blu_hitl_service** | T3 | **7** | HITL workflow state transitions | P2 |
| **blu_data_connectors** | T3 | **15** | BigQuery, ecommerce API calls | P2 |
| **blu_auth** | T3 | **13** | JWT decode, secret manager, dependencies | P2 |
| **blu_twilio_client** | T4 | **15** | WhatsApp/SMS send, webhook | P2 |
| **blu_experiment_service** | T4 | **11** | Dataset generation, runner | P2 |
| **blu_db_connector** | T3 | **8** | SQL execution, migrations | P2 |
| **blu_parsers** | T4 | **9** | PDF/Excel parse | P2 |
| **blu_llm_service** | T2 | **3** | LLM call wrapper | P2 |
| **blu_models** | T1 | **2** | Model parsing | ✅ OK |
| **blu_google_suite_client** | T4 | **1** | Google API call | ✅ OK |
| **blu_landing_intel** | T4 | **1** | HTTP fetch | ✅ OK |
| **blu_elicitation_service** | T4 | **0** | — | ✅ Excelente |
| **blu_shared_utils** | T4 | **0** | — | ✅ Excelente |

### 4.3 Análise Qualitativa dos Broad Excepts

#### Padrão "Fallback Degradado" (aceitável)
```python
# blu_context_service/tool_cache.py — fallback com logger.warning
except Exception as e:
    logger.warning(f"Tool cache store error: {e}")
    return fallback_value  # operação continua degradada
```
Este padrão é aceitável pois (a) loga o erro, (b) retorna fallback, (c) não quebra a operação principal.

#### Padrão "Log e Re-raise" (aceitável como barreira)
```python
# blu_agent_framework/builder.py — barreira de último recurso
except Exception as e:
    logger.exception("Unexpected error in skill execution")
    raise  # re-raise para handler superior
```
Aceitável como barreira de último recurso, desde que haja tratamento específico nos níveis abaixo.

#### Padrão "str(exc) Exposto" (CRÍTICO)
```python
# agent_api/api/agents_router.py:149
except Exception as exc:
    logger.error("Error creating session: %s", exc)
    raise HTTPException(status_code=500, detail=str(exc))  # ❌ P0
```
Expõe mensagens internas de erro para API consumers. Ver §7 para análise completa.

#### Padrão "Swallow Silencioso" (PREOCUPANTE)
```python
# agent_api/core/service.py — SSE generator
except Exception:
    pass  # continua o loop, erro ignorado
```
Embora raro, alguns blocos swallow errors silenciosamente dentro de generators SSE.

---

## 5. Retry Policies — Deep-Dive

### 5.1 Implementações Existentes

#### blu_agent_framework MCP Client — Exponential Backoff (✅ Funcional)
```python
# mcp_client.py:157-221
backoff = 1
max_retries = 5
for attempt in range(max_retries):
    try:
        # connect via streamablehttp_client
        return
    except asyncio.CancelledError:
        if attempt < max_retries - 1:
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)
        else:
            raise  # esgota tentativas
    except Exception as e:
        logger.error(f"Erro na conexão MCP (tentativa {attempt + 1}): {e}")
        if attempt < max_retries - 1:
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)
```
- **Estratégia:** 1s → 2s → 4s → 8s → 16s (cap 30s)
- **Max retries:** 5
- **Tratamento:** CancelledError tratado separadamente de Exception genérica
- **PT-BR:** Mensagens de log em português ✅

#### blu_llm_service Text-to-SQL — Configurável (✅ Excelente)
```python
# text_to_sql_config.py:66-90 (Pydantic Settings)
max_retries: int = 3
initial_retry_delay_ms: int = 1000
max_retry_delay_ms: int = 8000
retry_multiplier: float = 2.0
```
- **Estratégia:** 1s → 2s → 4s → 8s (cap 8s)
- **Max retries:** 3 (validado: 0-10)
- **Configurável via Pydantic Settings** — gold standard

#### blu_agent_framework MCP Executor — Parameterizado (✅)
```python
# mcp_executor.py:49-54
max_retries: int = 3
```
- **Estratégia:** Reconnect-and-retry no executor de ferramentas MCP
- **Max retries:** 3 (configurável)

#### blu_data_connectors RateLimitError — Condicional (✅)
- Implementa `RateLimitError(EcommerceConnectorError)` com suporte a `Retry-After` header
- Não é retry automático — depende do caller verificar o header

### 5.2 Matriz de Retry — Onde Falta

| Serviço | Artefato | Tier | Tem Retry? | Risco |
|---------|----------|:----:|:----------:|-------|
| Supabase RPC | blu_supabase_client | T1 | ❌ | **P0** — perda de dados em operações críticas |
| Supabase REST | blu_supabase_client | T1 | ❌ | **P0** — queries falham sem retry |
| Redis | blu_context_service | T1 | ❌ | **P1** — cache miss cascateia em Supabase |
| LLM (geral) | blu_llm_service | T2 | ⚠️ só text-to-sql | P1 — outros paths sem retry |
| Google APIs | blu_google_suite_client | T4 | ❌ | P2 |
| BigQuery | blu_data_connectors | T3 | ❌ | P2 |
| Twilio | blu_twilio_client | T4 | ❌ | P2 |
| MCP (external) | blu_agent_framework | T1 | ✅ (5 retries) | — |

---

## 6. Circuit Breakers — Deep-Dive

### 6.1 Implementações Existentes

#### blu_observability_bootstrap Langfuse — Cooldown (✅)
```python
# langfuse.py:431-465
_cooldown_until: float = 0.0
_COOLDOWN_SECONDS: float = 300.0  # 5 minutos

def _ensure_client(self):
    if time.time() < self._cooldown_until:
        return None  # circuit open
    # ... init client ...

def _trigger_cooldown(self):
    self._cooldown_until = time.time() + self._COOLDOWN_SECONDS
```
- **Mecanismo:** Cooldown de 5min após falha de conexão
- **Smart:** distingue erros de rede (502/503) de erros de negócio (404)
- **Fallback:** operação continua sem Langfuse (telemetria degradada)

#### blu_prompt_management Langfuse — Cooldown (✅)
```python
# loader.py:77-79
_langfuse_cooldown_until: float = 0.0
_LANGFUSE_COOLDOWN_SECONDS: float = 60.0  # 1 minuto
```
- **Mecanismo:** Cooldown de 1min (mais agressivo que observability)
- **Timeout-aware:** também ativa circuit breaker em timeouts

#### agent_api Routines — Suspensão (✅)
```python
# routines.py:57,239 — P1 circuit breaker
# 3 falhas consecutivas → status "suspended"
# Requer reset manual para reativar
```
- **Mecanismo:** Suspensão permanente após 3 falhas consecutivas
- **Granularidade:** per-rotina, per-client
- **Logging:** `[CircuitBreaker] routine %s client %s SUSPENDED after repeated failures`

### 6.2 Matriz de Circuit Breaker — Onde Falta

| Serviço | Artefato | Tier | Tem CB? | Risco |
|---------|----------|:----:|:-------:|-------|
| Supabase | blu_supabase_client | T1 | ❌ | **P0** — sem proteção contra cascata de falhas |
| Redis | blu_context_service | T1 | ❌ | **P1** — falha de cache causa degradação sem limite |
| LLM APIs | blu_llm_service | T2 | ❌ | **P1** — timeouts em cadeia |
| Google APIs | blu_google_suite_client | T4 | ❌ | P2 |
| Langfuse | blu_observability_bootstrap | T4 | ✅ (300s) | — |
| Langfuse | blu_prompt_management | T2 | ✅ (60s) | — |
| Twilio | blu_twilio_client | T4 | ❌ | P2 |
| MCP | blu_agent_framework | T1 | ❌ (retry substitui) | — |

---

## 7. str(exc) Exposure — Stack Trace Leakage (P0)

### 7.1 Locais de Exposição (src only, 14 locais)

#### agent_api (2 locais)

| Arquivo | Linha | Contexto |
|---------|:-----:|----------|
| `agents_router.py` | 149 | `HTTPException(status=500, detail=str(exc))` |
| `chat_router.py` | 78 | `HTTPException(status=401, detail=str(exc))` |
| `service.py` | 683 | SSE yield `{'event': 'error', 'data': {'message': str(exc)}}` |
| `service.py` | 737, 793 | `yield {"event": "error", "message": str(exc)}` |

#### tool_pool_api (12 locais)

| Arquivo | Linhas | Contexto |
|---------|:------:|----------|
| `integrations_router.py` | 450, 499, 523, 546, 568 | `HTTPException(status=4xx/5xx, detail=str(exc))` |
| `reports_router.py` | 119, 146, 188, 203, 230, 252, 278 | `HTTPException(status=4xx/5xx, detail=str(exc))` |

### 7.2 Padrão Problemático

```python
# Exemplo canônico do problema
except Exception as exc:
    logger.error("Error creating session: %s", exc)
    raise HTTPException(status_code=500, detail=str(exc))
```

**Problemas:**
1. `str(exc)` expõe mensagens internas (nomes de tabela, queries, stack traces)
2. API consumers recebem detalhes de infraestrutura (ex: "relation 'agent_sessions' does not exist")
3. Potencial vazamento de informação em auditoria de segurança

**Solução recomendada:**
```python
except Exception as exc:
    error_id = generate_correlation_id()
    logger.error("[%s] Error creating session: %s", error_id, exc, exc_info=True)
    raise HTTPException(status_code=500, detail=f"Internal error. Reference: {error_id}")
```

### 7.3 str(exc) em Contextos Internos (NÃO expostos)

Múltiplos arquivos capturam `str(exc)` para logging ou payloads internos (`skill_factory.py`, `builder.py`, `orchestrator.py`, `routine_artifacts.py`). Isto é aceitável pois os dados não são expostos ao usuário final — apenas ao sistema de logging.

---

## 8. Error Propagation — Análise de Fluxo

### 8.1 Re-raise vs Swallow

**Re-raise (bom):** A maioria dos blocos `except Exception` faz `raise` (re-raise) ou `logger.exception()` + `raise HTTPException`. Isto garante que erros não são silenciosamente ignorados.

**Swallow controlado (aceitável):** `blu_context_service/tool_cache.py` captura `Exception`, loga warning e retorna fallback (`None`, `[]`, `0`). Isto é aceitável pois o cache é uma camada de otimização — falha não deve quebrar a operação principal.

**Swallow problemático:** Alguns generators SSE em `agent_api/core/service.py` capturam `Exception` sem re-raise, potencialmente mascarando erros em streaming.

### 8.2 Error Propagation Cross-Lib

```
┌──────────────────────────────────────────────────────────────────┐
│  API Layer (agent_api / tool_pool_api)                           │
│  ❌ Usa HTTPException genérico com str(exc)                      │
│  ❌ Não distingue erros de negócio vs sistema                    │
└────────────────────────┬─────────────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────────────┐
│  Orchestrator (blu_agent_framework)                              │
│  ✅ SkillTurnLimitError, WorkerTurnLimitError, ApprovalError     │
│  ⚠️ Mas também usa except Exception como barreira               │
└────────────────────────┬─────────────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────────────┐
│  Libs downstream (supabase, llm, context, etc.)                  │
│  ❌ 12/21 libs sem exceções próprias                             │
│  ❌ Erros propagados como Exception genérica                     │
│  ❌ Impossível handler superior distinguir tipo de erro          │
└──────────────────────────────────────────────────────────────────┘
```

---

## 9. Logging & Observability

### 9.1 Structured Logging (JSON)

**Status: ❌ Ausente.** Nenhuma lib ou service usa `python-json-logger`, `structlog`, ou `JsonFormatter`. O logging é feito com `logging.getLogger(__name__)` padrão.

`blu_observability_bootstrap` depende de `opentelemetry-api/sdk` para distributed tracing, mas o output dos logs ainda é texto plano.

### 9.2 logger.error / logger.exception por Artefato (src only)

| Artefato | Tier | `logger.error` | `logger.exception` | Total | Avaliação |
|----------|:----:|:--------------:|:------------------:|:-----:|-----------|
| tool_pool_api | T2 | 85 | 84 | 169 | ⚠️ Alto — 169 chamadas, muitas em broad excepts |
| agent_api | T1 | 10 | 22 | 32 | ✅ Adequado |
| blu_agent_framework | T1 | 21 | 10 | 31 | ✅ Adequado |
| blu_supabase_client | T1 | 18 | 0 | 18 | ⚠️ usa `logger.warning` para falhas de rede |
| blu_twilio_client | T4 | 17 | 0 | 17 | ✅ |
| blu_context_service | T1 | 14 | 0 | 14 | ✅ (usa `logger.warning` para cache misses) |
| blu_sql_factory | T2 | 14 | 4 | 18 | ✅ |
| blu_experiment_service | T4 | 12 | 0 | 12 | ✅ |
| blu_auth | T3 | 11 | 0 | 11 | ✅ |
| blu_data_connectors | T3 | 11 | 0 | 11 | ✅ |
| blu_parsers | T4 | 7 | 0 | 7 | ✅ |
| blu_rag_factory | T2 | 5 | 2 | 7 | ✅ |
| blu_hitl_service | T3 | 5 | 0 | 5 | ✅ |
| blu_tool_registry | T4 | 5 | 2 | 7 | ✅ |
| blu_db_connector | T3 | 5 | 0 | 5 | ✅ |
| blu_llm_service | T2 | 1 | 1 | 2 | ✅ |
| blu_prompt_management | T2 | 1 | 0 | 1 | ✅ |
| blu_elicitation_service | T4 | 1 | 0 | 1 | ✅ |
| blu_observability_bootstrap | T4 | 1 | 0 | 1 | ✅ |
| blu_models | T1 | 0 | 0 | 0 | N/A (data layer) |
| blu_google_suite_client | T4 | 0 | 0 | 0 | ⚠️ sem logging de erro |
| blu_landing_intel | T4 | 0 | 0 | 0 | ⚠️ sem logging de erro |
| blu_shared_utils | T4 | 0 | 0 | 0 | N/A |

### 9.3 print() como Logging (src only)

| Artefato | print() calls | Arquivos | Severidade |
|----------|:------------:|----------|:----------:|
| **tool_pool_api** | 18 | MCP server, report modules | ⚠️ P1 |
| **blu_db_connector** | 14 | Operations, CLI | ⚠️ P2 |
| **blu_agent_framework** | 4 | Debug/demo files | P2 |
| **blu_sql_factory** | 2 | allowlist_validator.py | P2 |
| **blu_experiment_service** | 1 | CLI | P2 |

**Total: 39 chamadas de `print()` em 5 artefatos** (Phase 0 estimava ~88, mas incluía tests). O número é menor que o estimado, mas ainda preocupante em `tool_pool_api` (18) e `blu_db_connector` (14).

### 9.4 Correlation ID — Propagação por Artefato

| Artefato | Correlation ID? | Tipo | Observação |
|----------|:--------------:|------|------------|
| **blu_agent_framework** | ✅ 19 refs | `generate_correlation_id()` | Gera e usa nos logs do orchestrator |
| **blu_hitl_service** | ✅ 13 refs | `request_id` | Propaga em workflows HITL |
| **blu_experiment_service** | ✅ 7 refs | `trace_id` | Integração com Langfuse tracing |
| **agent_api** | ✅ 6 refs | `request_id` | Em endpoints específicos |
| **blu_models** | ✅ 4 refs | `trace_id` | Em modelos de audit |
| **blu_supabase_client** | ✅ 3 refs | `trace_id` | Em `record_audit()` |
| **blu_observability_bootstrap** | ✅ 2 refs | `trace_id` | Em spans de tracing |
| **blu_context_service** | ✅ 1 ref | `request_id` | Isolado |
| **demais 15 artefatos** | ❌ 0 | — | Sem correlation ID |

**Análise:** Correlation ID existe e funciona onde implementado, mas o coverage é baixo — apenas 8/23 artefatos Python têm qualquer referência. Nenhum middleware HTTP injeta `X-Correlation-Id` automaticamente.

---

## 10. Frontend Error Handling (apps/blu_v3 + packages/blu-auth)

### 10.1 Error Boundaries

**Status: ❌ Inexistente.** Zero `ErrorBoundary` components, `componentDidCatch`, ou wrappers de erro no código fonte.

Os únicos Error Boundaries estão em `node_modules/@remix-run/router` (biblioteca de terceiros).

### 10.2 try/catch Análise

| Arquivo | try/catch | catch tipado? | console.error? | Mensagem PT-BR? |
|---------|:---------:|:------------:|:--------------:|:---------------:|
| `hooks/useAgentBuilder.ts` | 10+ | ❌ `catch (err)` | ✅ | ❌ EN |
| `hooks/useKnowledgeBase.ts` | 5+ | ❌ `catch (err)` | ✅ | ❌ EN |
| `hooks/useStandaloneAgent.ts` | 5+ | ❌ `catch (err)` | ✅ | ❌ EN |
| `api/connectors.ts` | 1 | ✅ `catch (e: unknown)` | ❌ | ❌ EN |
| `api/atendente.ts` | 1 | ❌ | ❌ | ❌ EN |
| `MonthlyGantt.tsx` | 1 | ❌ `catch (err)` | ❌ | ❌ EN |
| `CollapsiblePanel.tsx` | 2 | ❌ | ❌ | ❌ EN |
| `AppShell.tsx` | 2 | ✅ (1 tipado, 1 bare) | ❌ | ❌ EN |

**Total: 21 `catch (err)` sem tipo explícito** — `err` é implicitamente `any`.

### 10.3 console.log/error/warn

**34 chamadas** de `console.log`/`console.error`/`console.warn` no frontend (src apenas).

### 10.4 `any` TypeScript

**4 ocorrências** de `: any` no código fonte — aceitável para Tier 4.

### 10.5 User-Facing Error Messages

**Idioma:** Todas as mensagens de erro no frontend estão em **inglês** (ex: `'Failed to load catalog'`, `'Failed to load tools'`). O `patterns.md` especifica "User-facing errors in PT-BR" para o frontend, mas zero mensagens seguem esta diretriz.

---

## 11. Error Handling no TypeScript (packages/blu-auth)

O package `blu-auth` (TypeScript) não tem:
- Custom error classes
- Error boundaries
- Tipagem em catch blocks
- Mensagens PT-BR

Escopo limitado (auth context provider) — Tier 4, aceitável.

---

## 12. Findings by Priority

### 12.1 P0 — Crítico (ação imediata)

| # | Finding | Artefatos | Detalhe |
|---|---------|-----------|---------|
| **P0-1** | **str(exc) exposto via HTTPException (14 endpoints)** | agent_api (4), tool_pool_api (10) | `detail=str(exc)` expõe mensagens internas a API consumers |
| **P0-2** | **Sem retry para Supabase (Tier 1)** | blu_supabase_client | RPC/REST sem retry — perda de dados em falhas de rede |
| **P0-3** | **Sem circuit breaker para Supabase (Tier 1)** | blu_supabase_client | Sem proteção contra cascata de falhas no banco principal |
| **P0-4** | **Broad except nos 4 Tier 1 + agent_api (239 blocos)** | blu_agent_framework, blu_supabase_client, blu_context_service, agent_api | P1 escalado a P0 por tier |

### 12.2 P1 — Alto (próxima sprint)

| # | Finding | Artefatos | Detalhe |
|---|---------|-----------|---------|
| **P1-1** | **Zero Error Boundaries no frontend** | apps/blu_v3, packages/blu-auth | patterns.md exige "at room level" |
| **P1-2** | **Sem retry para Redis (Tier 1)** | blu_context_service | Cache miss cascateia em Supabase |
| **P1-3** | **Sem circuit breaker para Redis (Tier 1)** | blu_context_service | Degradação sem limite |
| **P1-4** | **Sem circuit breaker para LLM APIs** | blu_llm_service | Timeouts em cadeia |
| **P1-5** | **Correlation ID não propagado para 15/23 artefatos** | Maioria das libs | Impossível tracing ponta-a-ponta |
| **P1-6** | **12/21 libs sem hierarchy de exceções** | 12 libs Python | `except Exception` sem alternativa |
| **P1-7** | **tool_pool_api: 221 broad excepts + 18 print()** | tool_pool_api | Maior concentração de más práticas |
| **P1-8** | **Sem middleware HTTP de tracing** | agent_api, tool_pool_api | Correlation ID não injetado automaticamente |

### 12.3 P2 — Médio (backlog)

| # | Finding | Artefatos | Detalhe |
|---|---------|-----------|---------|
| **P2-1** | **Logging não estruturado (JSON)** | Todo codebase | Sem JSON logging — difícil indexar/alertar |
| **P2-2** | **Mensagens de erro em inglês (frontend + services)** | agent_api, tool_pool_api, apps/blu_v3 | patterns.md exige PT-BR |
| **P2-3** | **Sem retry para Google APIs** | blu_google_suite_client | Google Calendar/Gmail/Sheets sem retry |
| **P2-4** | **Sem retry para BigQuery** | blu_data_connectors | Queries custosas sem retry |
| **P2-5** | **Sem retry para Twilio** | blu_twilio_client | WhatsApp/SMS sem retry |
| **P2-6** | **ValidationError não herda Exception** | blu_sql_factory | `class ValidationError:` sem herança |
| **P2-7** | **AuthenticationError duplicado** | blu_data_connectors | Duas classes com mesmo nome em namespaces diferentes |
| **P2-8** | **Sem logging de erro** | blu_google_suite_client, blu_landing_intel | Zero `logger.error` — erros silenciosos |
| **P2-9** | **21 `catch (err)` sem tipo no frontend** | apps/blu_v3 | `err` implicitamente `any` |
| **P2-10** | **34 console.log no frontend** | apps/blu_v3 | Deveria usar sistema de logging/telemetria |
| **P2-11** | **Sem custom exceptions nos 2 services** | agent_api, tool_pool_api | Usam HTTPException diretamente |
| **P2-12** | **5 artefatos com print() como logging** | tool_pool_api (18), blu_db_connector (14), blu_agent_framework (4), blu_sql_factory (2), blu_experiment_service (1) | Total: 39 chamadas |

---

## 13. Per-Service Dimension Matrix (Fases 1-5)

Legenda: ✅ Conforme | ⚠️ Parcial | ❌ Crítico/Ausente

| Artefato (Tier) | Exc. Hierarchy | Bare Except | Broad Except | str(exc) Exp. | Retry | Circuit Brk | Struct. Log | Corr. ID | Error Bound. | User PT-BR |
|---|---|---|---|---|---|---|---|---|---|---|
| **agent_api (T1)** | ❌ | ✅ | ⚠️ (94) | ❌ (4 locais) | ❌ | ✅ routines | ❌ | ✅ (6) | N/A | ❌ EN |
| **blu_agent_framework (T1)** | ✅ | ✅ | ⚠️ (64) | ✅ | ✅ MCP | ❌ | ❌ | ✅ (19) | N/A | ⚠️ Misto |
| **blu_supabase_client (T1)** | ✅ AuditError | ✅ | ⚠️ (19) | ✅ | ❌ P0 | ❌ P0 | ❌ | ✅ (3) | N/A | N/A |
| **blu_context_service (T1)** | ❌ | ✅ | ⚠️ (43) | ✅ | ❌ P1 | ❌ P1 | ❌ | ⚠️ (1) | N/A | ✅ PT-BR |
| **blu_models (T1)** | ❌ | ✅ | ✅ (2) | ✅ | N/A | N/A | ❌ | ✅ (4) | N/A | N/A |
| **tool_pool_api (T2)** | ⚠️ RAGClientError | ✅ | ❌ (221) | ❌ (10 locais) | ❌ | ❌ | ❌ | ❌ | N/A | ❌ EN |
| **blu_llm_service (T2)** | ❌ | ✅ | ✅ (3) | ✅ | ✅ text-to-sql | ❌ P1 | ❌ | ❌ | N/A | N/A |
| **blu_rag_factory (T2)** | ❌ | ✅ | ⚠️ (8) | ✅ | ❌ | ❌ | ❌ | ❌ | N/A | N/A |
| **blu_prompt_management (T2)** | ✅ | ✅ | ⚠️ (7) | ✅ | ❌ | ✅ Langfuse | ❌ | ❌ | N/A | N/A |
| **blu_sql_factory (T2)** | ⚠️ (ValidationError) | ✅ | ⚠️ (16) | ✅ | ❌ | ❌ | ❌ | ❌ | N/A | N/A |
| **blu_auth (T3)** | ✅ Excelente | ✅ | ⚠️ (13) | ✅ | ❌ | ❌ | ❌ | ❌ | N/A | N/A |
| **blu_hitl_service (T3)** | ❌ | ✅ | ⚠️ (7) | ✅ | ❌ | ❌ | ❌ | ✅ (13) | N/A | N/A |
| **blu_data_connectors (T3)** | ✅ | ✅ | ⚠️ (15) | ✅ | ✅ RateLimit | ❌ | ❌ | ❌ | N/A | N/A |
| **blu_db_connector (T3)** | ❌ | ✅ | ⚠️ (8) | ✅ | ❌ | ❌ | ❌ | ❌ | N/A | N/A |
| **blu_elicitation_service (T4)** | ✅ | ✅ | ✅ (0) | ✅ | ❌ | ❌ | ❌ | ❌ | N/A | N/A |
| **blu_experiment_service (T4)** | ❌ | ✅ | ⚠️ (11) | ✅ | ❌ | ❌ | ❌ | ✅ (7) | N/A | N/A |
| **blu_google_suite_client (T4)** | ❌ | ✅ | ✅ (1) | ✅ | ❌ | ❌ | ❌ | ❌ | N/A | N/A |
| **blu_landing_intel (T4)** | ❌ | ✅ | ✅ (1) | ✅ | ❌ | ❌ | ❌ | ❌ | N/A | N/A |
| **blu_observability_bootstrap (T4)** | ❌ | ✅ | ⚠️ (38) | ✅ | ❌ | ✅ Langfuse | ❌ | ✅ (2) | N/A | N/A |
| **blu_parsers (T4)** | ❌ | ✅ | ⚠️ (9) | ✅ | ❌ | ❌ | ❌ | ❌ | N/A | N/A |
| **blu_shared_utils (T4)** | ❌ | ✅ | ✅ (0) | ✅ | ❌ | ❌ | ❌ | ❌ | N/A | N/A |
| **blu_tool_registry (T4)** | ✅ | ✅ | ⚠️ (7) | ✅ | ❌ | ❌ | ❌ | ❌ | N/A | N/A |
| **blu_twilio_client (T4)** | ❌ | ✅ | ⚠️ (15) | ✅ | ❌ | ❌ | ❌ | ❌ | N/A | N/A |
| **apps/blu_v3 (T4)** | N/A | N/A | N/A | N/A | ❌ | N/A | N/A | ❌ | ❌ P1 | ❌ EN |
| **packages/blu-auth (T4)** | N/A | N/A | N/A | N/A | ❌ | N/A | N/A | ❌ | ❌ | ❌ EN |

---

## 14. Recommendations by Priority

### 14.1 Imediato (P0)

1. **Substituir `str(exc)` em todos os HTTPException** — 14 endpoints em agent_api e tool_pool_api
   - Template: `HTTPException(status=500, detail=f"Internal error. Reference: {correlation_id}")`
   - Logar detalhe completo via `logger.exception()`

2. **Adicionar retry com exponential backoff ao blu_supabase_client**
   - 3 retries com 1s → 2s → 4s para operações RPC e REST
   - `AuditError` já existe — estender para `SupabaseTimeoutError`, `SupabaseConnectionError`

3. **Adicionar circuit breaker ao blu_supabase_client**
   - Cooldown de 60s após 3 falhas consecutivas
   - Reutilizar padrão do `blu_observability_bootstrap/langfuse.py`

### 14.2 Curto Prazo (P1)

4. **Criar Error Boundary no frontend**
   - `apps/blu_v3/src/components/ErrorBoundary.tsx`
   - Envolver seções principais: agent builder, knowledge base, chat

5. **Adicionar retry + circuit breaker ao blu_context_service (Redis)**
   - Retry: 2 tentativas com 100ms → 200ms
   - Circuit breaker: cooldown de 30s

6. **Criar middleware HTTP de tracing**
   - Injetar `X-Correlation-Id` em todas as requests
   - Propagar para libs downstream via context var

7. **Criar `blu_core.exceptions.BluError`** como classe base comum
   - Campos: `message`, `code`, `correlation_id`
   - Migrar 8 hierarchies existentes para herdar de `BluError`

### 14.3 Backlog (P2)

8. **Migrar para structured JSON logging** — `python-json-logger` + `JsonFormatter`
9. **Traduzir user-facing errors para PT-BR** — agent_api, tool_pool_api, apps/blu_v3
10. **Adicionar retry para Google APIs, BigQuery, Twilio**
11. **Corrigir `ValidationError` do blu_sql_factory** — herdar de `Exception`
12. **Unificar `AuthenticationError` duplicado** no blu_data_connectors
13. **Tipar `catch (err)` no frontend** — substituir por `catch (err: unknown)`
14. **Substituir `print()` por `logger.info()`** nos 5 artefatos (39 chamadas)

---

## 15. Positive Findings

- ✅ **Zero bare `except:`** — disciplina exemplar em todo o codebase
- ✅ **blu_auth exception hierarchy** — gold standard: 7 subclasses com `code` único e nested inheritance
- ✅ **blu_elicitation_service** — hierarchy limpa com campos contextuais por subclasse
- ✅ **blu_tool_registry** — hierarchy funcional com 4 subclasses bem definidas
- ✅ **blu_llm_service text-to-sql retry** — configurável via Pydantic Settings, validado
- ✅ **Circuit breakers existentes** (Langfuse ×2, routines) bem implementados
- ✅ **Correlation ID infrastructure** existe e funciona onde implementada
- ✅ **blu_agent_framework MCP client** — retry com exponential backoff e logging PT-BR
- ✅ **blu_supabase_client audit** — `raise_on_error` flag controla propagação sem quebrar operação
- ✅ **blu_context_service/tool_cache** — fallback pattern bem implementado

---

## 16. Verification Commands Used

```bash
# except Exception (src only, per artifact)
grep -rn "except Exception" {dir}/src --include="*.py" | wc -l

# Bare except (excl .venv)
grep -rn "^[[:space:]]*except[[:space:]]*:" libs/ services/ --include="*.py" | grep -v .venv

# Custom exception classes
grep -rn "^class \w*\(.*Error\|Exception\|Fault\)" libs/ services/ --include="*.py" | grep -v .venv

# str(exc) in HTTPException
grep -rn "HTTPException.*str(exc)" libs/ services/ --include="*.py" | grep -v .venv

# Retry/backoff patterns
grep -rn "retry\|Retry\|backoff\|max_retries" {dir}/src --include="*.py"

# Circuit breaker patterns
grep -rni "circuit.breaker\|CircuitBreaker\|cooldown\|SUSPENDED" libs/ services/ --include="*.py" | grep -v .venv

# Correlation / trace IDs
grep -rni "correlation_id\|request_id\|trace_id" {dir}/src --include="*.py"

# logger.error/exception counts
grep -rn "logger\.error\|logger\.exception" {dir}/src --include="*.py" | wc -l

# print() as logging
grep -rn "^[[:space:]]*print(" {dir}/src --include="*.py" | wc -l

# Frontend error handling
grep -rn "catch (" apps/blu_v3/src --include="*.ts" --include="*.tsx" | grep -v node_modules
grep -rn "ErrorBoundary\|error.boundary" apps/ packages/ --include="*.tsx" --include="*.ts" | grep -v node_modules
```

---

## 17. Language Summary

| Linguagem | Artefatos | Excepts (src) | Exc. Hierarchies | Retry Impl | Circuit Breaker | Error Boundaries | User-Facing Lang |
|-----------|-----------|:------------:|:----------------:|:----------:|:---------------:|:----------------:|:----------------:|
| Python | 23 (21 libs + 2 services) | ~618 | 9 (8 libs + 1 service) | 3 | 3 | N/A | Misto PT-BR/EN |
| TypeScript/TSX | 2 (1 app + 1 package) | ~21 try/catch | 0 | 0 | 0 | 0 | EN |

