# error-handling-review.md — Error Handling Consistency Review (#57)

> **Gerado por:** factory-coder (t_08221d51), 2026-06-22  
> **Fonte:** grep scan de `libs/`, `services/`, `apps/`, `packages/`  
> **Branch:** `phase-0/issue-57-code-patterns-review`  
> **Depende de:** `inventory-catalog.md` (T57.1), `patterns.md`

---

## 1. Executive Summary

| Métrica | Valor |
|----------|-------|
| `except` blocks total | ~1,100+ |
| Bare `except:` (sem tipo) | **0** ✅ |
| `except Exception:` (broad) | ~273+ (tool_pool_api: 181, agent_api: 92, demais libs: ~300+) |
| Custom exception hierarchies | 8 libs com hierarquias próprias |
| Retry com backoff | 2 implementações (MCP client + LLM service) |
| Circuit breaker | 3 implementações (Langfuse x2 + routines) |
| Correlation IDs | 1 implementação centralizada (blu_agent_framework) |
| Error Boundaries (TSX) | **0** — nenhum encontrado no código do app ❌ |
| User-facing PT-BR errors | Parcial — misto de PT-BR e EN |
| Stack traces expostos a usuários | **Sim** — `str(exc)` em HTTPException responses ⚠️ |
| Structured JSON logging | **0** — logging tradicional com `logger.error/exception` |

---

## 2. Exception Hierarchy

### 2.1 Custom Exception Classes per Service/Lib

| Lib/Service | Base Exception | Subclasses | Herda de | Status |
|-------------|---------------|------------|----------|--------|
| **blu_agent_framework** | `ApprovalError` | — | `RuntimeError` | ✅ |
| | `SkillTurnLimitError` | — | `Exception` | ✅ |
| | `WorkerTurnLimitError` | — | `Exception` | ✅ |
| **blu_auth** | `AuthError` | `MissingCredentialsError`, `InvalidTokenError`, `TokenExpiredError`, `InvalidSignatureError`, `InvalidApiKeyError`, `ClientNotFoundError`, `AuthDisabledError` | `Exception` | ✅ Excelente |
| **blu_data_connectors** | `EcommerceConnectorError` | `RateLimitError`, `AuthenticationError` | `Exception` | ✅ |
| | `AuthenticationError` | *(conta_azul)* | `Exception` | ⚠️ Duplicate class name |
| | `ExecutionError` | — | `Exception` | ✅ |
| **blu_elicitation_service** | `ElicitationError` | `ElicitationValidationError`, `ElicitationTimeoutError`, `ElicitationNotFoundError` | `Exception` | ✅ |
| **blu_prompt_management** | `PromptNotFoundError` | — | `Exception` | ✅ |
| **blu_sql_factory** | `ParseError` | — | `Exception` | ✅ |
| | `ValidationError` | — | *(plain class, not Exception)* | ⚠️ Não herda de Exception |
| **blu_supabase_client** | `AuditError` | — | `RuntimeError` | ✅ |
| **blu_tool_registry** | `ToolRegistryError` | `ToolNotFoundError`, `TierAccessDeniedError`, `DockerMCPConnectionError`, `ToolValidationError` | `Exception` | ✅ |

**Libs SEM custom exceptions:** blu_context_service, blu_db_connector, blu_experiment_service, blu_google_suite_client, blu_hitl_service, blu_landing_intel, blu_llm_service, blu_models, blu_observability_bootstrap, blu_parsers, blu_rag_factory, blu_twilio_client
→ 12 de 21 libs sem hierarchy própria ⚠️

**Services SEM custom exceptions:** agent_api, tool_pool_api — ambos usam `HTTPException` do FastAPI diretamente.

### 2.2 Common Base Class

**Não há uma classe base comum** para todas as exceções do projeto. Cada lib define sua própria hierarchy independente. `blu_auth` é o melhor exemplo com `AuthError` como raiz e 7 subclasses.

**Recomendação:** Criar `blu_core.exceptions.BluError(Exception)` como base comum para todas as exceções do monorepo.

---

## 3. Specific vs Bare Except

### 3.1 Bare `except:` (P0)

**Contagem: 0** ✅ — Nenhum `except:` sem tipo específico encontrado em todo o codebase.

### 3.2 `except Exception:` (Broad catch — P1/P2)

| Lib/Service | Count | Contexto | Severidade |
|-------------|-------|----------|------------|
| **tool_pool_api** | 181 | Maioria em integrations, inbox dispatch | ⚠️ P1 |
| **agent_api** | 92 | Routers, service.py, routine_artifacts | ⚠️ P1 |
| **blu_agent_framework** | 76 | Orchestrator, builder, checkpointer, routines | ⚠️ P1 |
| **blu_observability_bootstrap** | 54 | Ingestion pipelines, telemetry | P2 |
| **blu_context_service** | 47 | Context reads/writes, cache | P2 |
| **blu_auth** | 42 | JWT decoding, secret manager, dependencies | ⚠️ P1 |
| **blu_sql_factory** | 30 | SQL parsing, validation | P2 |
| **blu_elicitation_service** | 30 | Elicitation manager, API calls | P2 |
| **blu_data_connectors** | 22 | BigQuery, ecommerce API calls | P2 |
| **blu_supabase_client** | 21 | RPC calls, audit logging | ⚠️ P1 |
| **blu_experiment_service** | 16 | Dataset generator, runner | P2 |
| **blu_parsers** | 15 | PDF/Excel parsing | P2 |
| **blu_tool_registry** | 15 | Tool execution, MCP connections | P2 |
| **blu_twilio_client** | 15 | WhatsApp/SMS sending | P2 |
| **blu_rag_factory** | 14 | Document indexing, retrieval | P2 |
| **blu_db_connector** | 12 | SQL execution, migrations | P2 |
| **blu_hitl_service** | 12 | Human-in-the-loop workflows | P2 |
| **blu_llm_service** | 12 | LLM invocation, text-to-sql | P2 |
| **blu_prompt_management** | 11 | Prompt loading, Langfuse client | P2 |
| **blu_google_suite_client** | 8 | Google API calls | P2 |
| **blu_models** | 2 | Model parsing | P2 |
| **blu_landing_intel** | 1 | HTTP fetch | P2 |

**Análise:** Tool_pool_api (181) e agent_api (92) concentram 273 dos broad excepts. Muitos destes são em `except Exception as e:` seguidos de `logger.error/exception` e re-raise — o que é aceitável como barreira de último recurso. Mas 273 broad catches é alto e reduz a capacidade de tratamento diferenciado por tipo de erro.

---

## 4. User-Facing Errors (PT-BR)

### 4.1 Backend (services/)

| Service | Idioma Predominante | Exemplos | Status |
|---------|---------------------|----------|--------|
| **agent_api** | **English** | "Internal processing error", "Database error", "Error loading client context", "Agent not found", "Session not found" | ⚠️ P2 |
| **tool_pool_api** | **English** | "HTTPException status_code=400 detail=str(exc)" | ⚠️ P2 |
| **blu_context_service** | **PT-BR** | "Erro ao SETAR cache para a chave {key}", "Erro ao LER cache da chave {key}" | ✅ |
| **blu_agent_framework** | **PT-BR** | "Erro na conexão MCP (tentativa {n})" | ✅ Parcial |

### 4.2 Frontend (apps/blu_v3/)

| Arquivo | Idioma | Observação |
|---------|--------|------------|
| `useAgentBuilder.ts` | EN | `catch (err)` sem mensagem PT-BR |
| `useKnowledgeBase.ts` | EN | `catch (err)` sem mensagem PT-BR |
| `api/connectors.ts` | EN | `catch (e: unknown)` sem tradução |
| `MonthlyGantt.tsx` | EN | `catch (err)` sem tradução |

**Análise:** O patterns.md especifica "User-facing errors in PT-BR" para o frontend, mas a maioria das mensagens de erro no código está em inglês. As libs internas (blu_context_service, blu_agent_framework) têm alguns erros em PT-BR.

---

## 5. Internal Error / Stack Trace Exposure

### 5.1 `str(exc)` exposto a API consumers

| Arquivo | Linha | Contexto | Severidade |
|---------|-------|----------|------------|
| `agent_api/api/agents_router.py` | 149 | `HTTPException(status=500, detail=str(exc))` | ⚠️ P1 |
| `agent_api/core/service.py` | 576 | SSE yield `{'event': 'error', 'data': {'message': str(exc)}}` | ⚠️ P1 |
| `agent_api/core/service.py` | 616, 672 | Async gen yield error with str(exc) | ⚠️ P1 |
| `agent_api/api/chat_router.py` | 78 | `HTTPException(status=401, detail=str(exc))` | ⚠️ P1 |
| `tool_pool_api/api/integrations_router.py` | 450 | `HTTPException(status=400, detail=str(exc))` | ⚠️ P1 |
| `agent_api/api/google_calendar_webhook_router.py` | 193 | `HTTPException(status=502, detail=f"Google API error: {exc}")` | P2 |

### 5.2 `traceback.format_exc` controlado

| Arquivo | Linha | Contexto | Status |
|---------|-------|----------|--------|
| `agent_api/core/routines.py` | 1099-1100 | `traceback.format_exc(limit=3)` — limitado a 3 frames | ✅ Bom |

### 5.3 `str(exc)` em dados internos (não exposto ao usuário)

Múltiplos arquivos capturam `str(exc)` para logging ou payloads internos (`skill_factory.py`, `builder.py`, `orchestrator.py`, `routine_artifacts.py`). Isto é aceitável pois os dados não são expostos ao usuário final diretamente.

**Análise:** O principal problema é `str(exc)` sendo embutido em `HTTPException.detail` — expõe mensagens de erro internas para API consumers. Deveria usar mensagens genéricas amigáveis e logar o detalhe internamente.

---

## 6. Logging with Context

### 6.1 Structured Logging (JSON)

**Status: ❌ Ausente.** Nenhuma lib ou service usa `python-json-logger`, `structlog`, ou `JsonFormatter`. O logging é feito com `logging.getLogger(__name__)` padrão e `logger.error()` / `logger.exception()`.

`blu_observability_bootstrap` depende de `opentelemetry-api/sdk` para distributed tracing, mas o output dos logs ainda é texto plano (não JSON estruturado).

### 6.2 Contexto em Logs (client_id, correlation_id)

| Lib/Service | client_id presente? | correlation_id presente? | Observação |
|-------------|---------------------|--------------------------|------------|
| **blu_agent_framework** | ✅ Sim (approval, audit) | ✅ Sim (orchestrator, observability) | `generate_correlation_id()` — 12-char hex |
| **blu_context_service** | ⚠️ Parcial | ❌ | Logs só mencionam a key, sem client_id |
| **blu_auth** | ✅ Sim (dependencies) | ❌ | client_id nos logs de erro |
| **agent_api** | ✅ Sim (routines) | ❌ | client_id nos logs de rotina |
| **tool_pool_api** | ❌ | ❌ | Sem structured context nos logs |
| **demais libs** | ❌ | ❌ | Sem client_id ou correlation_id nos logs |

### 6.3 Severity Level Appropriateness

| Contexto | Nível usado | Adequado? |
|-----------|-------------|-----------|
| Falha de LLM call | `logger.error` / `logger.exception` | ✅ |
| MCP connection failure | `logger.error` | ✅ |
| Skill turn limit | `logger.error` | ⚠️ Deveria ser `warning` — é condição esperada |
| Tool execution failure | `logger.exception` | ✅ |
| Context report failure | `logger.exception` | ✅ |

---

## 7. Retry Policies

### 7.1 Implementações Encontradas

| Lib | Arquivo | Mecanismo | Config | Status |
|-----|---------|-----------|--------|--------|
| **blu_agent_framework** | `mcp_client.py` | Exponential backoff: 1s → 2s → 4s → ... capping at 30s | Hardcoded | ✅ Funcional |
| **blu_llm_service** | `text_to_sql_config.py` | `max_retries=3`, exponential backoff: 1s → 2s → 4s → 8s | Configurável via `TextToSQLConfig` | ✅ Excelente |
| **blu_data_connectors** | `ecommerce_base_connector.py` | `RateLimitError` com `Retry-After` header | Condicional ao header | ✅ |

### 7.2 Matriz de Presença de Retry

| Serviço de Rede | Lib/Service | Tem Retry? |
|-----------------|-------------|------------|
| Supabase RPC | blu_supabase_client | ❌ P1 |
| Supabase REST | blu_supabase_client | ❌ P1 |
| Redis | blu_context_service | ❌ P2 |
| LLM (LangChain) | blu_llm_service | ✅ (text-to-sql) / ❌ (outros paths) |
| Google APIs | blu_google_suite_client | ❌ P2 |
| BigQuery | blu_data_connectors | ❌ P2 |
| Twilio | blu_twilio_client | ❌ P2 |
| Langfuse | blu_observability_bootstrap | ❌ (usa circuit breaker no lugar) |
| MCP (external) | blu_agent_framework | ✅ (exponential backoff) |

---

## 8. Circuit Breakers

### 8.1 Implementações Encontradas

| Sistema | Arquivo | Mecanismo | Cooldown | Status |
|---------|---------|-----------|----------|--------|
| **Langfuse (observability)** | `blu_observability_bootstrap/langfuse.py` | Cooldown após falha de conexão | 300s (5min) | ✅ Funcional |
| **Langfuse (prompts)** | `blu_prompt_management/loader.py` | Cooldown após falha/timeout | 60s (1min) | ✅ Funcional |
| **Routines (agent_api)** | `agent_api/core/routines.py` | Suspensão após 3 falhas consecutivas | Permanente até reset manual | ✅ Funcional |

### 8.2 Matriz de Circuit Breaker

| Serviço Externo | Lib/Service | Tem Circuit Breaker? |
|-----------------|-------------|---------------------|
| Supabase | blu_supabase_client | ❌ P1 |
| Redis | blu_context_service | ❌ P1 |
| LLM APIs | blu_llm_service | ❌ P1 |
| Google APIs | blu_google_suite_client | ❌ P2 |
| Langfuse | blu_observability_bootstrap | ✅ |
| Langfuse | blu_prompt_management | ✅ |
| Twilio | blu_twilio_client | ❌ P2 |
| MCP (external) | blu_agent_framework | ❌ (retry substitui) |

---

## 9. Error Boundaries (Frontend)

### 9.1 React Error Boundaries

**Status: ❌ Ausente.** Nenhum `ErrorBoundary` component, `componentDidCatch`, ou `error-boundary` encontrado no código fonte de `apps/blu_v3/` ou `packages/blu-auth/`.

As únicas ocorrências estão em `node_modules/@remix-run/router` (biblioteca de terceiros).

### 9.2 Try/Catch no Frontend

| Arquivo | Quantidade | Comentário |
|---------|------------|------------|
| `hooks/useAgentBuilder.ts` | 10+ try/catch | Sem Error Boundary como fallback |
| `hooks/useKnowledgeBase.ts` | 5+ try/catch | Sem Error Boundary |
| `api/connectors.ts` | 1 try/catch | Sem Error Boundary |
| `api/atendente.ts` | 1 try/catch | Sem Error Boundary |
| `MonthlyGantt.tsx` | 1 try/catch | Sem Error Boundary |

**Análise:** O patterns.md especifica "Error boundaries at room level". Nenhuma implementação encontrada. Um erro não tratado em qualquer componente pode quebrar toda a UI.

---

## 10. Correlation IDs

### 10.1 Implementação Central

| Função | Local | Descrição |
|--------|-------|-----------|
| `generate_correlation_id()` | `blu_agent_framework/utils/observability.py:37` | Gera ID hexadecimal de 12 caracteres |
| `log_parse_failure()` | `blu_agent_framework/utils/observability.py:44` | Log com correlation_id |
| `log_missing_tool()` | `blu_agent_framework/utils/observability.py:78` | Log com correlation_id |
| `log_missing_skill()` | `blu_agent_framework/utils/observability.py:108` | Log com correlation_id |

### 10.2 Fluxo do Correlation ID

```
┌─────────────────────────────────────────────────────────────────┐
│  Request Entry Point (agent_api / tool_pool_api)                │
│  ❌ NÃO gera correlation_id — não existe middleware de tracing  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  blu_agent_framework.orchestrator                               │
│  ✅ cid = generate_correlation_id()  (parse_intent, decompose,  │
│     plan, execute_step, synthesize)                             │
│  ✅ Inclui cid nos logs de erro: logger.error("... %s", cid)   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Demais libs (blu_supabase_client, blu_llm_service, etc.)       │
│  ❌ Não recebem nem propagam correlation_id                     │
└─────────────────────────────────────────────────────────────────┘
```

### 10.3 Status por Camada

| Camada | correlation_id? | Observação |
|--------|-----------------|------------|
| API Gateway / Entry | ❌ | Sem middleware de tracing |
| Orchestrator (agent_framework) | ✅ | Gera e usa nos logs |
| Skill execution | ❌ | correlation_id não propagado |
| Tool execution | ❌ | correlation_id não propagado |
| External calls (Supabase, LLM, etc.) | ❌ | correlation_id não propagado |
| Frontend (blu_v3) | ❌ | Sem request ID nos headers |

**Análise:** A infraestrutura de correlation ID existe (`generate_correlation_id`, funções de log), mas seu uso é limitado ao `blu_agent_framework/orchestrator`. Não há middleware HTTP que injete correlation ID nas requests, e as libs downstream não propagam o ID.

---

## 11. Findings by Priority

### 11.1 P0 — Crítico (ação imediata)

| # | Finding | Local | Detalhe |
|---|---------|-------|---------|
| P0-1 | **Stack traces expostos via HTTPException** | `agent_api/api/agents_router.py:149`, `agent_api/api/chat_router.py:78`, `agent_api/core/service.py:576,616,672`, `tool_pool_api/api/integrations_router.py:450` | `str(exc)` embutido em `detail` de HTTPException expõe erros internos a API consumers |
| P0-2 | **Sem retry para Supabase RPC/REST** | `blu_supabase_client/` | Falhas de rede no Supabase não têm retry — risco de perda de dados em operações críticas |

### 11.2 P1 — Alto (próxima sprint)

| # | Finding | Local | Detalhe |
|---|---------|-------|---------|
| P1-1 | **Sem Error Boundaries no frontend** | `apps/blu_v3/` | Patterns.md exige Error Boundaries "at room level" — nenhum implementado |
| P1-2 | **273+ `except Exception:` nos services** | `tool_pool_api` (181), `agent_api` (92) | Broad catches excessivos; deveriam ser específicos por tipo de erro |
| P1-3 | **Sem circuit breaker para Supabase** | `blu_supabase_client/` | Sem proteção contra cascata de falhas no banco principal |
| P1-4 | **Sem circuit breaker para Redis** | `blu_context_service/` | Sem proteção contra falhas de cache causando degradação |
| P1-5 | **Sem circuit breaker para LLM APIs** | `blu_llm_service/` | Falhas repetidas em APIs externas podem causar timeouts em cadeia |
| P1-6 | **Correlation ID não propagado** | Todas as libs downstream do orchestrator | Impossível rastrear request ponta-a-ponta |
| P1-7 | **12 libs sem hierarchy de exceções própria** | 12/21 libs | Usam `except Exception` sem tipos customizados |

### 11.3 P2 — Médio (backlog)

| # | Finding | Local | Detalhe |
|---|---------|-------|---------|
| P2-1 | **Logging não estruturado** | Todo o codebase | Sem JSON logging — difícil indexar/alertar em produção |
| P2-2 | **Mensagens de erro em inglês (não PT-BR)** | `agent_api`, `tool_pool_api`, `blu_v3` | Patterns.md exige PT-BR para user-facing errors |
| P2-3 | **Sem retry para Google APIs** | `blu_google_suite_client/` | Sem retry em chamadas Google Calendar/Gmail/Sheets |
| P2-4 | **Sem retry para BigQuery** | `blu_data_connectors/` | Sem retry em queries custosas |
| P2-5 | **Sem retry para Twilio** | `blu_twilio_client/` | Sem retry em envio de WhatsApp/SMS |
| P2-6 | **`ValidationError` não herda de Exception** | `blu_sql_factory/checks.py:24` | Dificulta captura uniforme |
| P2-7 | **Nome de classe duplicado: `AuthenticationError`** | `blu_data_connectors/accounting/` + `base/ecommerce_base_connector.py` | Duas classes com mesmo nome em namespaces diferentes |
| P2-8 | **client_id ausente em logs de várias libs** | Maioria das libs Tier 3/4 | Logs sem contexto de tenant |
| P2-9 | **SkillTurnLimitError logged como error** | `blu_agent_framework/builder.py:856` | Deveria ser `warning` — é condição esperada |

---

## 12. Per-Service Dimension Matrix

Legenda: ✅ Conforme | ⚠️ Parcial/Ausente | ❌ Crítico

| Service/Lib (Tier) | Exc. Hierarchy | Bare Except | Broad Except | User-Facing PT-BR | Stack Trace Exp. | Structured Logging | Context Logging | Retry | Circuit Breaker | Error Boundary | Correlation ID |
|-----|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| **agent_api (T1)** | ❌ | ✅ | ⚠️ (92) | ❌ EN | ❌ str(exc) | ❌ | ✅ client_id | ❌ | ✅ routines | N/A | ❌ |
| **tool_pool_api (T2)** | ❌ | ✅ | ❌ (181) | ❌ EN | ❌ str(exc) | ❌ | ❌ | ❌ | ❌ | N/A | ❌ |
| **blu_agent_framework (T1)** | ✅ | ✅ | ⚠️ (76) | ⚠️ Misto | ✅ | ❌ | ✅ cid+client | ✅ MCP | ❌ | N/A | ✅ Generator |
| **blu_auth (T3)** | ✅ Excelente | ✅ | ⚠️ (42) | N/A (internal) | ✅ | ❌ | ✅ client_id | ❌ | ❌ | N/A | ❌ |
| **blu_supabase_client (T1)** | ✅ | ✅ | ⚠️ (21) | N/A | ✅ | ❌ | ❌ | ❌ P0 | ❌ P1 | N/A | ❌ |
| **blu_context_service (T1)** | ❌ | ✅ | ⚠️ (47) | ✅ PT-BR | ✅ | ❌ | ❌ | ❌ | ❌ P1 | N/A | ❌ |
| **blu_llm_service (T2)** | ❌ | ✅ | ⚠️ (12) | N/A | ✅ | ❌ | ❌ | ✅ text-to-sql | ❌ P1 | N/A | ❌ |
| **blu_models (T1)** | ❌ | ✅ | ✅ (2) | N/A | ✅ | ❌ | ❌ | N/A | N/A | N/A | ❌ |
| **blu_rag_factory (T2)** | ❌ | ✅ | ⚠️ (14) | N/A | ✅ | ❌ | ❌ | ❌ | ❌ | N/A | ❌ |
| **blu_prompt_management (T2)** | ✅ | ✅ | ⚠️ (11) | N/A | ✅ | ❌ | ❌ | ❌ | ✅ Langfuse | N/A | ❌ |
| **blu_sql_factory (T2)** | ⚠️ | ✅ | ⚠️ (30) | N/A | ✅ | ❌ | ❌ | ❌ | ❌ | N/A | ❌ |
| **blu_db_connector (T3)** | ❌ | ✅ | ⚠️ (12) | N/A | ✅ | ❌ | ❌ | ❌ | ❌ | N/A | ❌ |
| **blu_data_connectors (T3)** | ✅ | ✅ | ⚠️ (22) | N/A | ✅ | ❌ | ❌ | ⚠️ RateLimit | ❌ | N/A | ❌ |
| **blu_hitl_service (T3)** | ❌ | ✅ | ⚠️ (12) | N/A | ✅ | ❌ | ❌ | ❌ | ❌ | N/A | ❌ |
| **blu_elicitation_service (T4)** | ✅ | ✅ | ⚠️ (30) | N/A | ✅ | ❌ | ❌ | ❌ | ❌ | N/A | ❌ |
| **blu_experiment_service (T4)** | ❌ | ✅ | ⚠️ (16) | N/A | ✅ | ❌ | ❌ | ❌ | ❌ | N/A | ✅ trace_id |
| **blu_google_suite_client (T4)** | ❌ | ✅ | ⚠️ (8) | N/A | ✅ | ❌ | ❌ | ❌ | ❌ | N/A | ❌ |
| **blu_landing_intel (T4)** | ❌ | ✅ | ✅ (1) | N/A | ✅ | ❌ | ❌ | ❌ | ❌ | N/A | ❌ |
| **blu_observability_bootstrap (T4)** | ❌ | ✅ | ⚠️ (54) | N/A | ✅ | ❌ | ❌ | ❌ | ✅ Langfuse | N/A | ❌ |
| **blu_parsers (T4)** | ❌ | ✅ | ⚠️ (15) | N/A | ✅ | ❌ | ❌ | ❌ | ❌ | N/A | ❌ |
| **blu_tool_registry (T4)** | ✅ | ✅ | ⚠️ (15) | N/A | ✅ | ❌ | ❌ | ❌ | ❌ | N/A | ❌ |
| **blu_twilio_client (T4)** | ❌ | ✅ | ⚠️ (15) | N/A | ✅ | ❌ | ❌ | ❌ | ❌ | N/A | ❌ |
| **apps/blu_v3 (T4)** | N/A | N/A | N/A | ❌ EN | N/A | N/A | N/A | ❌ | N/A | ❌ P1 | ❌ |
| **packages/blu-auth (T4)** | N/A | N/A | N/A | ❌ EN | N/A | N/A | N/A | ❌ | N/A | ❌ | ❌ |

---

## 13. Bare Except Count per Service

| Lib/Service | Count |
|-------------|-------|
| (todos) | **0** total — nenhum `except:` sem tipo |

---

## 14. Retry / Circuit Breaker Presence Matrix

| Serviço Externo | Supabase | Redis | LLM APIs | Google APIs | BigQuery | Langfuse | Twilio | MCP |
|-----------------|:--------:|:-----:|:--------:|:-----------:|:--------:|:--------:|:------:|:---:|
| **Retry** | ❌ | ❌ | ✅ (text-to-sql) | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Circuit Breaker** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (2 impl) | ❌ | ❌ |

---

## 15. Notes & Observations

### 15.1 Positive Findings
- **Zero bare `except:`** — toda captura tem tipo específico ou `Exception` (broad, mas não bare)
- **blu_auth exception hierarchy** é a melhor implementação: 7 subclasses específicas com herança clara
- **blu_tool_registry** tem hierarchy própria com 4 subclasses bem definidas
- **Circuit breakers** existentes (Langfuse, routines) são bem implementados
- **Correlation ID** infrastructure existe e funciona corretamente onde é usada
- **blu_llm_service text-to-sql** tem retry configurável exemplar

### 15.2 Critical Gaps
- **Stack trace leakage** via `str(exc)` em HTTPException — expõe detalhes de infraestrutura
- **Zero Error Boundaries** no frontend React — qualquer erro não tratado quebra a UI inteira
- **Supabase sem retry/circuit breaker** — banco principal sem resiliência de rede

### 15.3 Recomendações de Arquitetura
1. **Criar `blu_core.exceptions.BluError`** como classe base para todas as exceções do monorepo
2. **Middleware de tracing HTTP** que injeta `X-Correlation-Id` em todas as requests
3. **Error Boundary wrapper** em `apps/blu_v3/src/components/` para cada seção principal
4. **Retry decorator reutilizável** para chamadas de rede (Supabase, Redis, APIs externas)
5. **Circuit breaker padrão** em `blu_supabase_client` e `blu_llm_service`

---

## 16. Language Summary

| Linguagem | Artefatos | Excepts | Exception Hierarchy | Error Boundaries | User-Facing Lang |
|-----------|-----------|---------|---------------------|-----------------|------------------|
| Python | 23 (21 libs + 2 services) | ~1,100+ | 8 libs com custom | N/A | Misto PT-BR/EN |
| TypeScript/TSX | 2 (1 app + 1 package) | ~20 try/catch | 0 | 0 | Principalmente EN |

---

## 17. Verification Commands Used

```bash
# Exception handling
grep -rn "except" libs/ services/ apps/ packages/ --include="*.py" --include="*.tsx" --include="*.ts" | grep -v node_modules

# Custom exception classes
grep -rn "class \w*Error\|class \w*Exception" libs/ services/ --include="*.py"

# Traceback exposure
grep -rn "traceback.format_exc\|str(exc)" libs/ services/ --include="*.py"

# Correlation / trace IDs
grep -rni "correlation_id\|request_id\|trace_id" libs/ services/ --include="*.py"

# Retry patterns
grep -rn "retry\|Retry\|backoff\|Backoff" libs/ services/ --include="*.py"

# Circuit breakers
grep -rni "circuit.breaker\|CircuitBreaker\|cooldown" libs/ services/ --include="*.py"

# Error boundaries (TSX)
grep -rn "ErrorBoundary\|error.boundary" apps/ packages/ --include="*.tsx" --include="*.ts" | grep -v node_modules

# Logging errors
grep -rn "logger\.\(error\|exception\|critical\)(" libs/ services/ --include="*.py"
```
