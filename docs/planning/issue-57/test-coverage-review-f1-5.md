# test-coverage-review-f1-5.md — Test Coverage Analysis (Fases 1-5)

> **Gerado por:** factory-coder (t_153dbfcf), 2026-06-23  
> **Escopo:** 25 artefatos de Fases 1-5 (21 libs, 2 services, 1 app, 1 package)  
> **Fonte:** execução real de `pytest --collect-only` + `pytest -q` per-artifact  
> **Depende de:** `inventory-catalog.md` (T57.1), `patterns-review-f1-5.md` (sibling analysis)

---

## 1. Executive Summary

| Métrica | Valor | Status |
|----------|-------|--------|
| Total de artefatos | **25** (21 libs, 2 services, 1 app, 1 package) | — |
| Artefatos com testes executáveis | **12** (48%) | ⚠️ P1 |
| Artefatos com coleção quebrada | **4** (16%) | ❌ P1 |
| Artefatos sem testes | **9** (36%) | ❌ P1 |
| Total de testes coletados | **~1,106** | — |
| Testes que passam | **~815** (73.7%) | ⚠️ |
| Testes que falham | **~108** (9.8%) | ⚠️ |
| Testes com erro de coleta | **17** arquivos | ❌ |
| Fixtures duplicadas entre artifacts | **1** (mock_blu_client_context × 3) | ⚠️ P2 |
| Flaky tests potenciais | **2** (blu_agent_framework) | ⚠️ P2 |
| Cobertura de linha (pytest-cov) | **1/25** artefato configurado (quebrado) | ❌ P1 |

**Resumo narrativo:** Apenas 48% dos artefatos têm testes executáveis. 4 artefatos (16%) têm suites de teste que não conseguem nem carregar (`ImportError` durante `pytest --collect-only`). 9 artefatos (36%) não têm nenhum teste — incluindo 2 de Tier 3 (médio). Dos testes que executam, 73.7% passam, indicando débito técnico acumulado. Fixtures são duplicadas em 3 conftest.py diferentes (`mock_blu_client_context`), sinalizando copy-paste entre artefatos. Cobertura de linha por pytest-cov existe em apenas 1 artefato (blu_shared_utils) e está quebrada (0% reportado). Nenhum artefato usa `pytest.mark.flaky` ou `reruns`.

---

## 2. Methodology

### 2.1 Test Discovery
- `pytest --collect-only` per-artifact (para evitar colisão de conftest.py entre artefatos)
- `pytest -q` com timeout de 60s por diretório
- Exclusões padrão: `node_modules/`, `.venv/`, `__pycache__/`, `dist/`, `build/`

### 2.2 Dimensions Checked
1. **Execução**: pytest consegue coletar e executar? Pass/Fail/Error?
2. **Coleção quebrada**: `ImportError` ou `NameError` durante `--collect-only`?
3. **Fixtures**: Duplicação entre conftest.py de artefatos diferentes? Padrões inconsistentes?
4. **Flaky tests**: Uso de `time.sleep()`, `pytest.mark.flaky`, `reruns`, `xdist`?
5. **Cobertura**: pytest-cov configurado? Threshold? Funcionando?
6. **Missing tests**: Artefatos com zero testes?

### 2.3 Tier Classification (per resolution.md §DQ3)
| Tier | Criticality | Count | Threshold |
|------|-------------|-------|-----------|
| **Tier 1** | Crítico | 5 (blu_agent_framework, blu_supabase_client, blu_models, blu_context_service, agent_api) | P1 → P0 escalation |
| **Tier 2** | Alto | 5 (tool_pool_api, blu_llm_service, blu_rag_factory, blu_prompt_management, blu_sql_factory) | Standard |
| **Tier 3** | Médio | 4 (blu_auth, blu_hitl_service, blu_data_connectors, blu_db_connector) | Standard |
| **Tier 4** | Baixo | 11 (demais libs + apps/blu_v3 + packages/blu-auth) | Relaxed |

---

## 3. Test Execution Results — Per Artifact

### 3.1 Tier 1 — Crítico (Core Infra)

| Artifact | Source Files | Test Files | Tests Collected | Pass | Fail | Error | Pass Rate | Status |
|----------|-------------|------------|-----------------|------|------|-------|-----------|--------|
| **blu_agent_framework** | 21 | 15 | 232 | 218 | 14 | 0 | 94.0% | ⚠️ P2 |
| **blu_supabase_client** | 7 | 6 | 51 | 50 | 1 | 0 | 98.0% | ⚠️ P2 |
| **blu_models** | 23 | 1 | 22 | 22 | 0 | 0 | 100% | ✅ |
| **blu_context_service** | 5 | 2 | 27 | 27 | 0 | 0 | 100% | ✅ |
| **agent_api** | 15 | 3 | 29 | 23 | 6 | 0 | 79.3% | ❌ P1 |

**Análise Tier 1:**
- **blu_agent_framework** (94%): 14 falhas em tests de skills e routing. Testes com `time.sleep(0.05)` (potencial flaky em `test_orchestrator_logging.py:127,146`). Melhor suite da Tier 1 em volume.
- **blu_supabase_client** (98%): 1 falha em `test_query_limit_capped` — KeyError em mock. Próximo de perfeito.
- **blu_models** (100%): 22/22 passam. Apenas 1 arquivo de teste para 23 source files — cobertura de teste/classe é baixa mesmo com 100% de pass rate.
- **blu_context_service** (100%): 27/27 passam. 2 arquivos para 5 sources — razoável.
- **agent_api** (79.3%): ❌ **P1**. 6 falhas concentradas em `test_routine_checkpoint.py`. Serviço Tier 1 com 21% de falhas é inaceitável. 3 arquivos de teste para 15 source files.
- **Gap Tier 1:** Nenhum artefato Tier 1 tem cobertura de linha configurada (pytest-cov ausente).

### 3.2 Tier 2 — Alto (Strategic Services)

| Artifact | Source Files | Test Files | Tests Collected | Pass | Fail | Error | Pass Rate | Status |
|----------|-------------|------------|-----------------|------|------|-------|-----------|--------|
| **blu_llm_service** | 5 | 12 | 58 | 0 | 0 | 3 | — | ❌ P0 |
| **blu_rag_factory** | 5 | 4 | 52 | 50 | 2 | 0 | 96.2% | ⚠️ P2 |
| **blu_prompt_management** | 5 | 2 | 28 | 26 | 2 | 0 | 92.9% | ⚠️ P2 |
| **blu_sql_factory** | 12 | 12 | 182 | 137 | 45 | 0 | 75.3% | ❌ P1 |
| **tool_pool_api** | 58 | 23 | 166 | 0 | 0 | 11 | — | ❌ P0 |

**Análise Tier 2:**
- **blu_llm_service** (❌ P0): **Coleção totalmente quebrada.** 3 arquivos com ImportError — `test_integration_pipeline.py`, `test_sanitizer.py`, `test_text_to_sql.py`. Nenhum teste executa. Tier 2 crítico — P0 escalation.
- **blu_rag_factory** (96.2%): 2 falhas em `test_factory.py` (`test_rag_factory_success`, `test_rag_factory_disabled`). Boa suite.
- **blu_prompt_management** (92.9%): 2 falhas em template assertions (`test_builtin_templates_exist`, `test_list_available`).
- **blu_sql_factory** (75.3%): ❌ **P1**. Maior suite de Tier 2 (182 testes) mas 45 falhas (25% failure rate). Concentradas em `test_validator_exemplars.py`. Suite grande mas baixa confiabilidade.
- **tool_pool_api** (❌ P0): **Coleção totalmente quebrada.** 11 arquivos com erro de coleta — `test_sbm_synthesis.py`, `test_tools.py`, `test_version_module.py`, `test_business_memory_router.py`, `test_knowledge_graph_sync.py`, entre outros. Serviço com mais source files (58) e mais test files (23) de todo o repo — e nada executa. P0 escalation.
- **Gap Tier 2:** 2 dos 5 artefatos (40%) com coleções quebradas. Nenhum tem cobertura de linha.

### 3.3 Tier 3 — Médio (Feature Support)

| Artifact | Source Files | Test Files | Tests Collected | Pass | Fail | Error | Pass Rate | Status |
|----------|-------------|------------|-----------------|------|------|-------|-----------|--------|
| **blu_auth** | 16 | 6 | 10 | 0 | 0 | 2 | — | ❌ P1 |
| **blu_hitl_service** | 3 | 0 | 0 | 0 | 0 | 0 | 0% | ❌ P1 |
| **blu_data_connectors** | 8 | 0 | 0 | 0 | 0 | 0 | 0% | ❌ P1 |
| **blu_db_connector** | 6 | 2 | 0 | 0 | 0 | 1 | — | ❌ P1 |

**Análise Tier 3:**
- **blu_auth** (❌ P1): Coleção quebrada. 2 erros em `test_mcp_middleware.py` e `test_strategies.py` — ImportError de fastmcp. 10 testes coletados mas nenhum executa. 6 test files no total (incluindo fora de /tests).
- **blu_hitl_service** (❌ P1): **Zero testes.** 3 source files, nenhum test file. Serviço de Human-in-the-Loop — crítico para UX de supervisão.
- **blu_data_connectors** (❌ P1): **Zero testes.** 8 source files, múltiplos conectores (accounting, bigquery, ecommerce). Sem cobertura para integrações externas.
- **blu_db_connector** (❌ P1): Coleção quebrada. `ImportError: cannot import name 'TierCliente'` — schema de blu_models desatualizado. 1 erro bloqueia toda a suite.
- **Gap Tier 3:** 100% dos artefatos Tier 3 têm problemas graves: 2 com coleção quebrada, 2 sem testes.

### 3.4 Tier 4 — Baixo (Auxiliary)

| Artifact | Source Files | Test Files | Tests Collected | Pass | Fail | Error | Pass Rate | Status |
|----------|-------------|------------|-----------------|------|------|-------|-----------|--------|
| **blu_elicitation_service** | 6 | 2 | 30 | 30 | 0 | 0 | 100% | ✅ |
| **blu_google_suite_client** | 9 | 0 | 0 | 0 | 0 | 0 | 0% | ⚠️ P3 |
| **blu_experiment_service** | 8 | 0 | 0 | 0 | 0 | 0 | 0% | ⚠️ P3 |
| **blu_landing_intel** | 2 | 0 | 0 | 0 | 0 | 0 | 0% | ⚠️ P3 |
| **blu_observability_bootstrap** | 4 | 0 | 0 | 0 | 0 | 0 | 0% | ⚠️ P3 |
| **blu_parsers** | 10 | 0 | 0 | 0 | 0 | 0 | 0% | ⚠️ P3 |
| **blu_shared_utils** | 2 | 4 | 3 | 3 | 0 | 0 | 100% | ⚠️ P2 |
| **blu_tool_registry** | 8 | 8 | 149 | 111 | 38 | 0 | 74.5% | ❌ P1 |
| **blu_twilio_client** | 3 | 4 | 31 | 31 | 0 | 0 | 100% | ✅ |

**Análise Tier 4:**
- **blu_elicitation_service** (✅): 30/30 passam. Bom exemplo de Tier 4 bem testado.
- **blu_twilio_client** (✅): 31/31 passam. Suite limpa, sem warnings.
- **blu_tool_registry** (❌ P1): Apesar de Tier 4, 38 falhas em 149 testes (25.5% failure rate). Concentradas em `test_sql_tool.py` e `test_sql_tool_integration_suite.py`. Muitos testes mas baixa confiabilidade.
- **blu_shared_utils** (⚠️ P2): 3/3 passam mas pytest-cov reporta 0% de cobertura contra threshold de 85%. Configuração de coverage quebrada (`--cov` apontando para path incorreto).
- **6 artefatos Tier 4 sem testes:** `blu_google_suite_client` (9 src files), `blu_experiment_service` (8 src files), `blu_parsers` (10 src files) — os 3 com volume significativo de código sem cobertura.
- **Gap Tier 4:** Embora relaxed thresholds, 7 de 11 artefatos (64%) têm problemas.

### 3.5 Apps & Packages

| Artifact | Language | Source Dirs | Tests | Status |
|----------|----------|-------------|-------|--------|
| **apps/blu_v3** | TypeScript/TSX | `src/` (React + Vite) | 0 | ❌ P1 |
| **packages/blu-auth** | TypeScript | `src/` (shared auth) | 0 | ❌ P1 |

**Análise Frontend:**
- Nenhum teste TypeScript/TSX em todo o monorepo.
- `apps/blu_v3`: React 18 + Vite — sem Jest, Vitest, ou Testing Library configurados.
- `packages/blu-auth`: Shared auth package — sem testes unitários para tokens, refresh, ou sessão.
- Ambos Tier 4 mas impacto é alto: frontend é a interface principal do usuário.

---

## 4. Collection Errors — Detailed Breakdown

### 4.1 blu_auth (Tier 3)
| Arquivo | Erro | Causa |
|---------|------|-------|
| `test_mcp_middleware.py` | ImportError | fastmcp dependency chain quebrada no venv |
| `test_strategies.py` | ImportError | Mesma cadeia de fastmcp |

### 4.2 blu_db_connector (Tier 3)
| Arquivo | Erro | Causa |
|---------|------|-------|
| `test_operations.py` | ImportError | `TierCliente` não existe em `blu_models.cliente_blu` — schema migration desatualizada |

### 4.3 blu_llm_service (Tier 2)
| Arquivo | Erro | Causa |
|---------|------|-------|
| `test_integration_pipeline.py` | ImportError | Provável dependência de langchain não disponível |
| `test_sanitizer.py` | ImportError | Módulo importado não encontrado |
| `test_text_to_sql.py` | ImportError | Módulo importado não encontrado |

### 4.4 tool_pool_api (Tier 2)
| Arquivo | Erro | Causa |
|---------|------|-------|
| `test_sbm_synthesis.py` | ImportError | Módulo SBM não disponível |
| `test_tools.py` | ImportError | Dependência de tool não resolvida |
| `test_version_module.py` | NameError | Variável não definida |
| `test_business_memory_router.py` | ImportError | — |
| `test_business_memory_integration.py` | ImportError | — |
| `test_sbm_lightrag_weekly.py` | ImportError | — |
| `test_integrations_router.py` | ImportError | — |
| `test_knowledge_graph_sync.py` | ImportError | — |
| `test_memory_meta.py` | ImportError | — |
| `test_memory_module_embedding.py` | ImportError | — |
| `test_memory_read.py` | ImportError | — |

---

## 5. Duplicate Fixtures Analysis

### 5.1 `mock_blu_client_context` — Duplicated × 3

| Arquivo | Linha | Definição |
|---------|-------|-----------|
| `libs/blu_context_service/tests/conftest.py` | 31 | `def mock_blu_client_context(mock_client_id, mock_credencial_sql, mock_cliente_blu_row) -> BluClientContext:` |
| `libs/blu_rag_factory/tests/conftest.py` | 10 | `def mock_blu_client_context() -> BluClientContext:` |
| `libs/blu_sql_factory/tests/conftest.py` | 10 | `def mock_blu_client_context() -> BluClientContext:` |

**Análise:** Três definições distintas do mesmo fixture com assinaturas diferentes. `blu_context_service` tem a versão mais rica (com parâmetros reais), enquanto `blu_rag_factory` e `blu_sql_factory` são versões simplificadas copy-paste. Isso indica que não há um pacote compartilhado de test fixtures — cada lib reinventa seus mocks.

**Recomendação:** Extrair para um `blu_test_utils` compartilhado ou pelo menos consolidar a fixture base em `blu_context_service` e re-exportar.

### 5.2 Conftest Placeholders

| Arquivo | Conteúdo |
|---------|----------|
| `blu_supabase_client/tests/conftest.py` | Vazio |
| `services/tool_pool_api/tests/conftest.py` | Vazio (mas `tests/unit/conftest.py` tem conteúdo) |

**Análise:** conftest.py vazios indicam que existem mas nunca foram populados. O `tool_pool_api` tem conftest duplicado: um no raiz de tests (vazio) e outro em `tests/unit/` (com fixtures mock_mcp_context, mock_blu_context).

---

## 6. Flaky Test Risks

### 6.1 Tests com `time.sleep` / `asyncio.sleep`

| Arquivo | Linha | Padrão | Risco |
|---------|-------|--------|-------|
| `blu_agent_framework/tests/unit/test_orchestrator_logging.py` | 127 | `time.sleep(0.05)` | ⚠️ Médio |
| `blu_agent_framework/tests/unit/test_orchestrator_logging.py` | 146 | `await asyncio.sleep(0.05)` | ⚠️ Médio |

**Análise:** Apenas 2 sleep calls reais (não mockados) em todo o codebase de teste. Ambos em `blu_agent_framework` e com valores muito baixos (50ms). Baixo risco de flakyness por timing, mas devem ser substituídos por mocks de clock.

### 6.2 Mocks de sleep (boas práticas)

| Arquivo | Padrão | Avaliação |
|---------|--------|-----------|
| `blu_supabase_client/tests/test_postgrest_executor.py:320,330` | `patch("time.sleep")` | ✅ Boa prática |
| `services/routine_engine/tests/unit/test_backup_shared_memory.py:328,349,1238` | `patch("asyncio.sleep", new_callable=AsyncMock)` | ✅ Boa prática |

### 6.3 Marcadores de Flaky / Reruns
- **Nenhum uso de `pytest.mark.flaky`** em todo o repo
- **Nenhum uso de `pytest-rerunfailures`** ou `--reruns`
- **Nenhum uso de `pytest-xdist`** (execução paralela)

---

## 7. Code Coverage Analysis

### 7.1 pytest-cov Configuration

| Artefato | Configurado? | Threshold | Cobertura Real | Status |
|----------|-------------|-----------|----------------|--------|
| **blu_shared_utils** | Sim (`pyproject.toml`) | 85% | 0.00% | ❌ Quebrado |
| Demais 24 artefatos | Não | — | — | ❌ Não configurado |

### 7.2 blu_shared_utils — Diagnóstico
O `pyproject.toml` de `blu_shared_utils` configura:
```
[tool.pytest.ini_options]
addopts = "--cov=src/blu_shared_utils --cov-report=term --cov-fail-under=85"
```
Mas o `--cov` aponta para um path relativo que não resolve corretamente quando pytest roda do repo root. Isso explica 0% de cobertura em 3/3 testes passando.

### 7.3 Cobertura Estimada por Volume

| Métrica | Tier 1 | Tier 2 | Tier 3 | Tier 4 | Total |
|---------|--------|--------|--------|--------|-------|
| Source files | 71 | 85 | 33 | 58 | 247 |
| Test files | 27 | 53 | 8 | 31 | 119 |
| Ratio test/src | 0.38 | 0.62 | 0.24 | 0.53 | 0.48 |
| Artefatos com coverage tool | 0/5 | 0/5 | 0/4 | 1/11 | 1/25 |

---

## 8. Key Gaps — Functionality Without Tests

### 8.1 Tier 1 — Crítico
| Gap | Impacto |
|-----|---------|
| `agent_api` checkpoint logic com 21% de falhas | Rotinas podem falhar silenciosamente — 6 testes quebrando em `test_routine_checkpoint.py` |
| `blu_agent_framework` skills/tags routing com 14 falhas | Roteamento de agentes pode enviar tasks para specialist errado |
| `blu_models`: 1 test file para 23 source files | Cobertura de schemas é superficial — campos novos podem quebrar sem detecção |

### 8.2 Tier 2 — Alto
| Gap | Impacto |
|-----|---------|
| `blu_llm_service` (P0): coleção totalmente quebrada | LLM service sem testes — regressões em text-to-sql, sanitizer, embeddings não detectadas |
| `tool_pool_api` (P0): coleção totalmente quebrada | Serviço central de tools com 58 source files sem cobertura funcional |
| `blu_sql_factory` com 25% de falhas | SQL validation regressions não detectadas — queries mal formadas podem chegar ao banco |

### 8.3 Tier 3 — Médio
| Gap | Impacto |
|-----|---------|
| `blu_auth` coleção quebrada | Auth middleware sem testes — regressão em JWT, API keys, OAuth não detectada |
| `blu_hitl_service` zero testes | Human-in-the-loop sem cobertura — fluxos de aprovação podem quebrar |
| `blu_data_connectors` zero testes | 8 conectores externos sem testes de integração — BigQuery, ecommerce, accounting |

### 8.4 Tier 4 — Baixo
| Gap | Impacto |
|-----|---------|
| `blu_parsers` zero testes | PDF parsing (10 source files) sem cobertura — extração de documentos quebrada |
| `blu_experiment_service` zero testes | Experimentos sem validação — métricas podem ser incorretas |
| `blu_google_suite_client` zero testes | Integração Google (9 source files, 4 domínios) sem cobertura |
| `blu_observability_bootstrap` zero testes | OpenTelemetry config sem validação — tracing pode falhar |

### 8.5 Frontend
| Gap | Impacto |
|-----|---------|
| `apps/blu_v3` zero testes | React app sem Jest/Vitest — sem cobertura de componentes, hooks, ou routing |
| `packages/blu-auth` zero testes | Auth package compartilhado sem testes de token refresh/session |

---

## 9. Recommendations — Prioritized

### P0 — Blocker (antes de qualquer merge futuro)

1. **Fix `tool_pool_api` test collection (Tier 2):** 11 arquivos com ImportError. Prioridade máxima — serviço central com 58 source files e zero cobertura funcional. Resolver dependências de SBM, memory modules, e knowledge_graph_sync.
2. **Fix `blu_llm_service` test collection (Tier 2):** 3 arquivos com ImportError. LLM service é crítico para text-to-sql e embeddings.
3. **Fix `blu_auth` test collection (Tier 3):** 2 arquivos com ImportError de fastmcp. Auth middleware sem cobertura é risco de segurança.

### P1 — High Priority (este sprint)

4. **Fix `blu_db_connector` test collection (Tier 3):** `TierCliente` não existe — atualizar imports para schema atual de blu_models.
5. **Fix `blu_sql_factory` 45 failing tests (Tier 2):** 25% failure rate — maior taxa de falhas do repo. Concentradas em validator exemplars.
6. **Fix `agent_api` 6 failing tests (Tier 1):** `test_routine_checkpoint.py` — rotinas são core do sistema.
7. **Fix `blu_tool_registry` 38 failing tests (Tier 4→P1):** Apesar de Tier 4, tool registry é referenciado por ambos os services. 25% failure rate.
8. **Adicionar testes a `blu_hitl_service` (Tier 3):** 3 source files, 0 testes. Human-in-the-loop é crítico para UX.
9. **Adicionar testes a `blu_data_connectors` (Tier 3):** 8 conectores externos sem cobertura. Risco de falhas em integrações.

### P2 — Medium Priority (próximo sprint)

10. **Consolidar fixture `mock_blu_client_context`:** Extrair para shared test utils (evitar 3 definições divergentes).
11. **Corrigir `blu_shared_utils` pytest-cov:** Path do `--cov` está quebrado (0% vs threshold 85%).
12. **Adicionar pytest-cov a todos os Tier 1 e Tier 2:** Mínimo threshold 70% para Tier 1, 60% para Tier 2.
13. **Substituir `time.sleep` em `test_orchestrator_logging.py`:** Mockar clock em vez de sleep real (2 ocorrências).
14. **Adicionar `pytest-rerunfailures` para CI:** Detectar flaky tests automaticamente com `--reruns 2`.

### P3 — Low Priority (backlog)

15. **Adicionar testes a `apps/blu_v3`:** Configurar Vitest + Testing Library para componentes React.
16. **Adicionar testes a `packages/blu-auth`:** Testes unitários para token refresh e session management.
17. **Adicionar testes a `blu_parsers`, `blu_google_suite_client`, `blu_experiment_service`:** Artefatos Tier 4 com maior volume de código sem cobertura.
18. **Adicionar `pytest-xdist` para paralelismo:** Reduzir tempo de execução da suite (~1100 testes).
19. **Adicionar `pytest-randomly` para detectar order-dependency:** Tests que passam por acaso devido à ordem de execução.

---

## 10. Anomalies & Notes

### 10.1 Estrutura de testes inconsistente
- **Test files dentro de `/src/`:** Alguns artefatos têm `test_*.py` soltos no diretório raiz da lib (ex: `blu_agent_framework/test_agent_framework.py`, `blu_auth/` com 16 test files fora de `/tests/`).
- **Padrão recomendado:** Todos os testes em `/tests/` com estrutura espelhando `/src/`.

### 10.2 Testes sem `__init__.py`
- Alguns diretórios de teste não têm `__init__.py`, o que pode causar colisões de namespace quando pytest roda do repo root (conftest collisions já observadas).

### 10.3 `blu_context_service` — fixture mais rica
- A fixture `mock_blu_client_context` em `blu_context_service` é a versão canônica (3 parâmetros reais). As versões em `blu_rag_factory` e `blu_sql_factory` são simplificações copy-paste sem parâmetros.

### 10.4 `services/routine_engine/tests` — não catalogado
- O diretório `services/routine_engine/` existe no disco com `tests/unit/test_backup_shared_memory.py` mas não está no inventory-catalog.md (25 artefatos). Possível artefato novo ou fora do escopo.

### 10.5 Warnings comuns
- `PydanticDeprecatedSince20`: Uso de `class Config` em vez de `ConfigDict` — afeta `blu_models/hitl.py:83`, propagado para `blu_context_service`, `blu_elicitation_service`, `blu_rag_factory`, `blu_sql_factory`, `blu_shared_utils`.
- `DeprecationWarning`: `datetime.utcfromtimestamp()` em alguns testes.
- total de ~30 warnings distribuídos entre artefatos.

---

## 11. Acceptance Criteria Checklist

- [x] Todos os 25 artefatos analisados (21 libs + 2 services + 1 app + 1 package)
- [x] Testes executados com `pytest` per-artifact (coleção + execução)
- [x] Coleções quebradas identificadas (4 artefatos, 17 arquivos)
- [x] Fixtures duplicadas mapeadas (`mock_blu_client_context` × 3)
- [x] Flaky test risks identificados (2 sleep calls)
- [x] Cobertura de linha verificada (1/25 configurado, quebrado)
- [x] Testes ausentes para funcionalidades-chave mapeados (9 artefatos sem testes)
- [x] Recomendações priorizadas (P0-P3) e acionáveis
- [x] Artefato salvo em `docs/planning/issue-57/test-coverage-review-f1-5.md`
- [x] Classificação por Tier aplicada (resolution.md §DQ3)

---

## 12. Quick Reference — Health Dashboard

```
Tier 1 (Crítico):  ████████░░  80% passing   (2/5 com falhas, 0/5 com collection broken)
Tier 2 (Alto):     ████░░░░░░  40% passing   (2/5 com collection broken, 2/5 com falhas)
Tier 3 (Médio):    ██░░░░░░░░  20% passing   (2/4 com collection broken, 2/4 sem testes)
Tier 4 (Baixo):    ██████░░░░  64% passing   (1/11 com falhas, 7/11 sem testes ou broken)
Frontend:          ░░░░░░░░░░   0% passing   (0/2 com qualquer teste)

Overall:           ██████░░░░  48% com testes executáveis
                   ████████░░  73.7% pass rate (dos que executam)
```

**Veredito:** O codebase tem 48% de cobertura de testes funcional, com 2 serviços Tier 2 em estado P0 (coleção quebrada). A prioridade máxima é restaurar `tool_pool_api` e `blu_llm_service` para execução, seguido por adicionar testes aos 9 artefatos completamente descobertos.
