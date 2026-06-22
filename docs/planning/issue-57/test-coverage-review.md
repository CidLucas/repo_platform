# Test Coverage & Quality Assessment (#57.7)

> **Gerado por:** factory-tester (t_62e802ed), 2026-06-22
> **Fonte:** Execução `pytest --cov` contra cada lib/service com testes, análise de estrutura, mocks, fixtures e padrões flaky
> **Branch:** `phase-0/issue-57-code-patterns-review`
> **Depende de:** `inventory-catalog.md` (T57.1), `resolution.md` (DQ3 tier classification)

---

## 1. Coverage Summary Table

| Service/Lib | Tier | Framework | # Tests | # Pass | # Fail | # Error | Line Coverage | Branch Coverage | Gap Severity |
|---|---|---|---|---|---|---|---|---|---|
| **agent_api** | T1 | pytest | 26 | 20 | 6 | 0 | 6% | N/A | **P0** |
| blu_agent_framework | T1 | pytest | 211 | 198 | 13 | 0 | 38% | N/A | **P1** |
| blu_supabase_client | T1 | pytest | 51 | 50 | 1 | 0 | 58% | N/A | P2 |
| blu_models | T1 | — | 0 | — | — | — | — | — | **P0 — sem testes** |
| blu_context_service | T1 | pytest | 12 | 5 | 6 | 1 | 23% | N/A | **P1** |
| **tool_pool_api** | T2 | pytest | 7 | 0 | 0 | 7 | N/A | N/A | **P1 — coleção falha** |
| blu_prompt_management | T2 | pytest | 28 | 26 | 2 | 0 | 56% | N/A | P2 |
| blu_llm_service | T2 | pytest | 3 | 0 | 0 | 3 | N/A | N/A | **P1 — coleção falha** |
| blu_rag_factory | T2 | pytest | 52 | 50 | 2 | 0 | 64% | N/A | P2 |
| blu_sql_factory | T3 | pytest | 182 | 137 | 45 | 0 | 59% | N/A | P2 |
| blu_auth | T3 | pytest | 0 | 0 | 0 | 2 | N/A | N/A | **P1 — coleção falha** |
| blu_hitl_service | T3 | — | 0 | — | — | — | — | — | **P0 — sem testes** |
| blu_data_connectors | T3 | — | 0 | — | — | — | — | — | P2 — sem testes |
| blu_db_connector | T3 | pytest | 0 | 0 | 0 | 1 | N/A | N/A | P2 — coleção falha |
| blu_elicitation_service | T4 | pytest | 30 | 30 | 0 | 0 | 72% | N/A | P2 |
| blu_tool_registry | T4 | pytest | 149 | 111 | 38 | 0 | 73% | N/A | P2 |
| blu_twilio_client | T4 | pytest | 31 | 31 | 0 | 0 | 72% | N/A | P2 |
| blu_shared_utils | T4 | pytest | 3 | 3 | 0 | 0 | 92% | N/A | P2 |
| blu_google_suite_client | T4 | — | 0 | — | — | — | — | — | P2 — sem testes |
| blu_landing_intel | T4 | — | 0 | — | — | — | — | — | P2 — sem testes |
| blu_observability_bootstrap | T4 | — | 0 | — | — | — | — | — | P2 — sem testes |
| blu_parsers | T4 | — | 0 | — | — | — | — | — | P2 — sem testes |
| blu_experiment_service | T4 | — | 0 | — | — | — | — | — | P2 — sem testes |
| **blu_v3** (app) | T4 | — | 0 | — | — | — | — | — | P2 — sem testes |
| **blu-auth** (package) | T4 | — | 0 | — | — | — | — | — | P2 — sem testes |

> **Legenda:** T1 = Crítico, T2 = Alto, T3 = Médio, T4 = Baixo (per resolution.md §DQ3)
> **P0** = Imediato, **P1** = Next sprint, **P2** = Backlog
> **Coleção falha** = Testes existem mas não compilam/coletam por import errors ou dependências ausentes

---

## 2. Services/Libs WITHOUT Tests — Flagged

### ⚠ Tier 1 (P0 — CRITICAL)

| Service/Lib | Tier | Why Critical |
|---|---|---|
| **blu_models** | T1 | Nó central do grafo de dependências — 6 libs dependem dele. Sem testes o risco de regressão em schemas Pydantic/SQLModel afeta toda a cadeia. |

### ⚠ Tier 3 (P1 — Next Sprint)

| Service/Lib | Tier | Why |
|---|---|---|
| **blu_hitl_service** | T3 | Gerencia interação humana no loop (HITL). Sem testes não há garantia de que critérios e fluxos de aprovação funcionam. |

### Tier 4 (P2 — Backlog)

Serviços/libs de suporte sem testes: blu_data_connectors, blu_google_suite_client, blu_landing_intel, blu_observability_bootstrap, blu_parsers, blu_experiment_service, blu_v3 (frontend), blu-auth (package).

---

## 3. Services/Libs with Tests But Broken Collection

These have test files on disk that fail to collect (import errors / missing dependencies):

| Service/Lib | Tier | Test Files | Root Cause |
|---|---|---|---|
| **tool_pool_api** | T2 | 7 files | `fastmcp` depende de `key_value.aio.stores.filetree.FileTreeStore` — breaking dep version mismatch. 2 integração + 2 unit + 3 flat tests todos falham. |
| **blu_llm_service** | T2 | 5 files | `test_text_to_sql.py` importa `blu_models.context.BluClientContext` que não existe. `test_sanitizer.py` importa `sanitize_observation` ausente de `client.py`. |
| **blu_auth** | T3 | 3 files | `test_strategies.py` importa `AuthRequest` de `blu_auth.core.models` — classe removida. `test_mcp_middleware.py` falha por dependência `FileTreeStore`. |
| **blu_db_connector** | T3 | 1 file | `test_operations.py` importa `TierCliente, TipoCliente` de `blu_models.cliente_blu` — nomes não existem no modelo atual. |

---

## 4. Quality Assessment

### 4.1 Test Organization

**Boa prática (src ↔ tests mirror):**
- `blu_auth`: `src/blu_auth/core/models.py` → `tests/test_strategies.py` ✅
- `blu_sql_factory`: `src/blu_sql_factory/allowlist.py` → `tests/test_allowlist.py` ✅
- `tool_pool_api`: `src/tool_pool_api/server/mcp_server.py` → `tests/unit/test_tools.py` ✅

**Problemas:** 
- `tool_pool_api` tem testes híbridos: 4 em `tests/` e 3 em `src/tool_pool_api/tests/` — duplicação de diretório de teste dentro do source tree
- `blu_llm_service`: 5 tests files todos flat em `tests/`, nenhum subdiretório unit/integration
- `blu_agent_framework`: 1 flat + 7 em `tests/unit/` — estrutura mista

### 4.2 Fixture Reusability

| Lib | conftest.py | Fixture Quality |
|---|---|---|
| blu_auth | ✅ `tests/conftest.py` | Config de contexto compartilhada |
| blu_context_service | ✅ `tests/conftest.py` | Mock de SupabaseService, fixtures de contexto |
| blu_db_connector | ✅ `tests/conftest.py` | Fixture de engine SQLAlchemy |
| blu_rag_factory | ✅ `tests/conftest.py` | Mock de LLM, configs |
| blu_sql_factory | ✅ `tests/conftest.py` | Fixtures de validator, schema snapshot |
| blu_supabase_client | ✅ `tests/conftest.py` | Mock client Supabase |
| blu_twilio_client | ✅ `tests/conftest.py` | Mock Twilio client |
| tool_pool_api | ✅ `tests/conftest.py` + `tests/unit/conftest.py` | Hierarquia de fixtures |
| blu_agent_framework | ❌ | Nenhum conftest — fixtures duplicadas entre test_agent_framework.py e tests/unit/ |

**Achado:** `blu_agent_framework` (T1, 211 testes, 8 test files) não tem conftest.py. Fixtures de LLM mock, checkpointer e agent config são redefinidas em cada test file — indicador de duplicação.

### 4.3 Mock Quality (Sampled)

**Bons mocks (exercitam superfície de integração):**
- `blu_supabase_client/tests/test_postgrest_executor.py` — mocka a camada HTTP do Supabase, com time.sleep (flaky candidate)
- `blu_rag_factory/tests/unit/test_factory.py` — mocka LLM response, exercita fallback paths
- `blu_tool_registry/tests/test_registry.py` — mocka validação de tools, cobre erros e edge cases
- `blu_context_service/tests/unit/test_context_service.py` — mocka Supabase e Redis, testa cache hit/miss

**Mocks abaixo do ideal:**
- `blu_agent_framework/tests/test_agent_framework.py` — ~198 testes passando, mas mocks são excessivamente simplificados (monkeypatch de funções internas em vez de mock de interface). Testes frágeis a refatorações internas.
- `blu_llm_service/tests/test_client.py` — mocka httpx.Client diretamente sem usar responses library — frágil

### 4.4 Integration vs Unit Balance

| Lib | Unit | Integration | Flat | Ratio (I:U) |
|---|---|---|---|---|
| blu_agent_framework | 7 | 0 | 1 | 0:7 |
| blu_rag_factory | 4 | 0 | 0 | 0:4 |
| agent_api | 2 | 0 | 0 | 0:2 |
| tool_pool_api | 2 | 2 | 3 | 1:1 |
| Demais | 0 | 0 | flat | N/A |

**Achado:** Nenhum teste de integração real na maioria das libs. `tool_pool_api` tem 2 testes de integração mas ambos sem asserts (ver §4.5). Os testes de integração em `services/agent_api/tests/unit/` são na verdade unitários com mock.

### 4.5 Tests Without Assertions

| Test File | Asserts | Issue |
|---|---|---|
| `tool_pool_api/src/tool_pool_api/tests/test_e2e_helper.py` | 0 | Arquivo importa módulos mas nunca testa nada |
| `tool_pool_api/tests/integration/test_mcp_auth_flow.py` | 0 | Setup de servidor MCP mas sem validações |
| `tool_pool_api/tests/integration/test_tool_pool.py` | 0 | Esqueleto de teste vazio |
| `tool_pool_api/tests/unit/test_tools.py` | 1 | Apenas 1 assert para múltiplos cenários |

### 4.6 Test File Organization — Source Mirror Analysis

| Lib | Source Files | Test Files | Coverage of Source? |
|---|---|---|---|
| blu_agent_framework | 20 src files | 8 test files | Somente 1 test file flat cobre todos os src (test_agent_framework.py). Testes unitários adicionais em `tests/unit/`. |
| blu_sql_factory | 14 src files | 6 test files | ✅ Boa cobertura: allowlist, validator, exemplar, e2e |
| blu_tool_registry | 10 src files | 4 test files | ✅ Boa cobertura: registry, sql_tool, feature_registry |
| blu_auth | 24 src files | 3 test files | Cobertura insuficiente — 24 arquivos de código para 3 arquivos de teste |
| blu_llm_service | 6 src files | 5 test files | Cobertura adequada mas todos quebrados (coleção falha) |

---

## 5. Flaky Test Candidates

| Test File | Pattern | Risk |
|---|---|---|
| `blu_agent_framework/tests/unit/test_orchestrator_logging.py` | `time.sleep` presente | **Alto** — sleep é o padrão mais comum de flaky test; dependente de timing |
| `blu_supabase_client/tests/test_postgrest_executor.py` | `time.sleep` presente | **Alto** — rede/threading mockado incorretamente |

**Padrões adicionais observados:**
- `blu_tool_registry/tests/test_sql_tool_integration_suite.py`: 38 testes falham — vários por erro de validação de enum (espera `VALIDATION_ERROR`, recebe `validation_failed`). Não é flaky, mas indica que o código foi alterado sem atualizar os testes.
- `blu_context_service/tests/unit/test_context_service.py`: 6 de 12 testes falham por alteração no schema `BluClientContext` (11 erros de validação Pydantic). Testes não acompanharam mudanças no modelo.

---

## 6. Top 5 Test Gaps with Recommendations

### Gap 1 (P0): blu_models — Sem Testes

**Severidade:** CRÍTICO — 6 dependentes internos, sem nenhum teste.

**Recomendação:**
Criar testes unitários para todos os modelos Pydantic/SQLModel:

```python
# tests/test_models.py
from blu_models.cliente_blu import ClienteBlu, TierCliente, TipoCliente
from blu_models.context import BluClientContext
from blu_models.hitl import HitlCriterion, HitlConfig

def test_cliente_blu_defaults():
    """Verificar defaults e campos obrigatórios."""
    c = ClienteBlu(nome="Teste", email="teste@exemplo.com")
    assert c.tier == TierCliente.BASIC  # default esperado
    assert c.ativo is True

def test_blu_client_context_validation():
    """Validar schemas de contexto com dados reais."""
    ctx = BluClientContext(
        client_id="uuid-aqui",
        nome_empresa="Empresa X",
        brand_voice="profissional",
        # ... campos obrigatórios
    )
    assert ctx.client_id is not None
    assert ctx.nome_empresa == "Empresa X"
```

### Gap 2 (P1): agent_api — 6% Line Coverage

**Severidade:** ALTO — serviço T1 com apenas 6% de cobertura.

**Recomendação:**
Adicionar testes unitários para os 4 routers principais (agents_router, chat_router, routines_router) e para o core:

```python
# tests/unit/test_chat_router.py
import pytest
from httpx import AsyncClient
from agent_api.main import app

@pytest.fixture
def client():
    return AsyncClient(app=app, base_url="http://test")

@pytest.mark.asyncio
async def test_chat_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

### Gap 3 (P1): Testes de Integração Ausentes para Serviços T1/T2

**Severidade:** ALTO — agent_api e tool_pool_api não têm testes de integração que validem o pipeline completo (HTTP → core → DB → response).

**Recomendação:**
Criar 1 teste de integração por rota principal no agent_api usando TestClient do FastAPI. Para tool_pool_api, corrigir primeiro a dependência fastmcp/key_value.

### Gap 4 (P1): blu_hitl_service — Sem Testes

**Severidade:** ALTO — serviço de interação humana (HITL) sem nenhuma cobertura.

**Recomendação:**
Testar os critérios de aprovação/rejeição e o fluxo de timeout:

```python
# tests/test_hitl_service.py
from blu_hitl_service import HitlProcessor
from blu_models.hitl import HitlCriterion

def test_hitl_criterion_timeout():
    """Critério com timeout deve falhar após expiração."""
    criterion = HitlCriterion(
        id="c1",
        description="Approve?",
        timeout_seconds=0,  # expira imediatamente
    )
    result = HitlProcessor.evaluate(criterion)
    assert result.status == "timeout"
    assert not result.approved
```

### Gap 5 (P2): Testes de Edge Cases Faltantes nas Libs com Cobertura

**Severidade:** MÉDIO — libs com cobertura >50% (blu_tool_registry 73%, blu_twilio_client 72%) ainda carecem de testes para:

- Inputs vazios/null
- Valores limite (boundary)
- Erros de conexão/IO
- Payloads malformados

**Exemplo (blu_twilio_client):**

```python
def test_send_message_empty_recipient():
    """Envio sem destinatário deve levantar erro."""
    client = TwilioClient()
    with pytest.raises(ValueError, match="recipient"):
        client.send_message(to="", body="Hello")

def test_send_message_timeout():
    """Timeout de rede deve ser tratado graciosamente."""
    client = TwilioClient(timeout=0.001)
    result = client.send_message(to="+551199999999", body="Test")
    assert result.status == "error"
    assert "timeout" in result.error.lower()
```

---

## 7. Summary Statistics

| Métrica | Valor |
|---|---|
| Total de artefatos no catálogo | 25 (21 libs + 2 services + 1 app + 1 package) |
| Artefatos COM testes | 15 (13 libs + 2 services) |
| Artefatos SEM testes | 10 |
| Artefatos com testes executáveis | 12 |
| Artefatos com coleção falha (broken) | 4 (tool_pool_api, blu_llm_service, blu_auth, blu_db_connector) |
| Artefatos com 0 testes no disco | 9 (blu_models, blu_hitl_service, blu_data_connectors, blu_google_suite_client, blu_landing_intel, blu_observability_bootstrap, blu_parsers, blu_experiment_service, blu_v3, blu-auth) |
| Total de testes executados | 785 |
| Testes passando | 661 (84.2%) |
| Testes falhando | 113 (14.4%) |
| Testes com erro de coleção | 11 |
| Total de conftest.py | 10 |
| Flaky candidates (time.sleep) | 2 |

### Gaps por Severidade:

| Severidade | Count | Items |
|---|---|---|
| **P0** (imediato) | 2 | blu_models sem testes, agent_api com 6% cobertura |
| **P1** (next sprint) | 5 | tool_pool_api, blu_llm_service, blu_auth coleção falha; blu_hitl_service sem testes; agent_api sem testes de integração |
| **P2** (backlog) | 10+ | Libs T4 sem testes, edge cases faltantes, fixtures duplicadas |

---

## 8. Recommendations Summary

1. **P0 — Criar testes para blu_models** — nó central do grafo, 0% cobertura
2. **P1 — Corrigir coleção de testes quebrados** (tool_pool_api, blu_llm_service, blu_auth) — testes existem mas não rodam
3. **P1 — Subir cobertura do agent_api** de 6% para >40% — serviço T1 crítico
4. **P1 — Criar testes para blu_hitl_service** — HITL sem testes é risco operacional
5. **P2 — Adicionar conftest.py a blu_agent_framework** — T1 com 211 testes mas fixtures duplicadas
6. **P2 — Eliminar time.sleep dos testes** — 2 candidatos flaky identificados
7. **P2 — Remover test files vazios/sem assert** em tool_pool_api (4 arquivos)
8. **P2 — Adicionar edge cases** (empty, null, timeout, boundary) nas libs com cobertura >50%
