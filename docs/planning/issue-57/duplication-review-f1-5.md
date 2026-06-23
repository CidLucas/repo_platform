# duplication-review-f1-5.md — Cross-Phase Code Duplication Analysis (Fases 1-5)

> **Gerado por:** factory-coder (t_fcff5835), 2026-06-23
> **Escopo:** 25 artefatos de Fases 1-5 (21 libs, 2 services, 1 app, 1 package)
> **Fonte:** análise manual + grep/rg + diff + inspeção de código-fonte
> **Branch:** `feat/b2-duplication-analysis-f1-5`
> **Depende de:** `duplication-review.md` (t_a811c4bd), `patterns-review-f1-5.md` (t_b99bd5a4), `inventory-catalog.md` (t_13beaba9)
> **Anti-Goals:** NÃO modificar código fonte — análise apenas. NÃO escrever testes.

---

## 1. Executive Summary

|| Métrica | Valor |
||----------|-------|
|| Total de artefatos analisados | **25** (21 libs, 2 services, 1 app, 1 package) |
|| Fases cobertas | Fase 1 (Fundação), Fase 2 (Memory Agent), Fase 3 (Documentos/RAG), Fase 4 (Enriquecimento), Fase 5 (Transparência/UI) |
|| Duplicações intra-fase identificadas | **4** (3 críticas em memory_module.py) |
|| Duplicações cross-fase identificadas | **8** (4 herdadas de duplication-review.md + 4 novas) |
|| Candidatos de extração priorizados | **6** (3 quick wins + 3 médio prazo) |
|| Duplicação 100% (byte-identical) | **2 funções** em memory_module.py (_validate_snapshot_frontmatter, _validate_snapshot_body) |
|| Duplicação 80%+ (near-duplicate) | **2 funções** (_validate_entity_type ↔ _validate_meta_entity_type) |

**Resumo narrativo:** A análise cross-fase revela que a maior concentração de duplicação está na Fase 1 (Fundação da Memória), particularmente no módulo `memory_module.py` (3.669 linhas), que contém **2 funções 100% duplicadas** (definidas em dois locais diferentes do mesmo arquivo) e **2 funções 80% similares** com propósitos quase idênticos. Cross-fase, a duplicação se concentra em: (a) boilerplate de configuração (`config.py` × 7 artefatos entre Fases 1-4), (b) infraestrutura de auditoria (`audit.py` — Fase 1 `blu_agent_framework` vs Fase 1 `blu_supabase_client`), (c) padrão de exceções (`exceptions.py` — Fase 1 `blu_auth` vs Fase 2 `blu_elicitation` vs Fase 3 `blu_tool_registry`). O frontend (Fase 5) tem baixa duplicação com o backend, exceto no padrão de handlers de API.

---

## 2. Methodology

### 2.1 Análise Intra-Fase
- **Inspeção manual** de funções duplicadas dentro do mesmo arquivo (Python: `grep -n "^def "` + diff)
- **Análise de similaridade** entre funções com nomes semelhantes (ex: `_validate_entity_type` vs `_validate_meta_entity_type`)
- **Mapeamento de boilerplate** por artefato (padrões de import, logging, error handling)

### 2.2 Análise Cross-Fase
- **Mapeamento fase→artefato** baseado em `docs/roadmap/blu-intelligent-memory.md`
- **Comparação de padrões estruturais** entre módulos de fases diferentes
- **Revalidação** dos 8 clusters DUP-01 a DUP-08 do `duplication-review.md` original
- **Busca de novos padrões** não cobertos pela análise anterior (focando em tool_modules)

### 2.3 Ferramentas Utilizadas
| Ferramenta | Propósito | Cobertura |
|------------|-----------|-----------|
| `grep -n "^def "` | Identificar funções duplicadas no mesmo arquivo | memory_module.py (3.669L) |
| `diff` manual | Comparar conteúdo de funções near-duplicate | 4 pares de funções |
| `grep -rn` | Buscar padrões cross-module (get_supabase_client, db.rpc, json.loads) | 35 tool_modules |
| `duplication-review.md` | Baseline de 88 pygount duplicates | 25 artefatos |

---

## 3. Phase-to-Artifact Mapping

Baseado no roadmap `blu-intelligent-memory.md` e na estrutura real do código:

| Fase | Nome | Artefatos Primários | Artefatos de Suporte |
|------|------|--------------------|-----------------------|
| **Fase 1** | Fundação da Memória | `memory_module.py`, `memory_pre_flight.py`, `memory_post_flight.py`, `context_module.py`, `platform_module.py` | `blu_agent_framework`, `blu_supabase_client`, `blu_models`, `blu_context_service`, `blu_db_connector` |
| **Fase 2** | Memory Agent | `routines_module.py`, `onboarding_shared_memory_hook.py`, `handoff_hook.py` | `blu_hitl_service`, `blu_elicitation_service` |
| **Fase 3** | LightRAG — Documentos | `rag_module.py`, `document_intelligence_module.py`, `ocr_extraction_module.py`, `web_crawl_module.py` | `blu_rag_factory`, `blu_parsers`, `blu_prompt_management`, `blu_llm_service` |
| **Fase 4** | Enriquecimento do Grafo | `sbm_to_lightrag_synthesis.py`, `knowledge_graph_sync.py`, `version_module.py` | `blu_sql_factory` |
| **Fase 5** | Transparência e Controle | `apps/blu_v3/` (UI), `packages/blu-auth/` (auth React) | `report_module.py`, `chart_module.py` |
| **Cross-cutting** | Infra compartilhada | — | `blu_auth`, `blu_tool_registry`, `blu_observability_bootstrap`, `blu_data_connectors`, `blu_google_suite_client`, `blu_shared_utils`, `blu_twilio_client`, `blu_experiment_service`, `blu_landing_intel` |

---

## 4. Intra-Phase Duplication

### 4.1 Fase 1 — memory_module.py: Funções 100% Duplicadas (CRÍTICO)

O arquivo `memory_module.py` (3.669 linhas, o maior do codebase) contém **duas funções definidas redundantemente em dois locais diferentes**:

#### DUP-F1-01: `_validate_snapshot_frontmatter` — 100% Duplicate

| Campo | Valor |
|-------|-------|
| **Localizações** | Linha 319 e Linha 529 |
| **Similaridade** | **100%** — byte-identical (72 linhas cada) |
| **Propósito** | Validar frontmatter de snapshots (entity_type='snapshot') |
| **Impacto** | 72 linhas duplicadas. Alteração requer update em 2 lugares. |
| **Causa provável** | Copy-paste durante desenvolvimento de Fase 2 (snapshot validation foi movida mas a cópia original não foi removida) |
| **Recomendação** | Remover a duplicata (linhas 529-610) e unificar as chamadas para usar apenas a definição na linha 319. **Quick Win — esforço: ~15min** |

#### DUP-F1-02: `_validate_snapshot_body` — 100% Duplicate

| Campo | Valor |
|-------|-------|
| **Localizações** | Linha 402 e Linha 612 |
| **Similaridade** | **100%** — byte-identical (~120 linhas cada) |
| **Propósito** | Validar body de snapshots |
| **Impacto** | ~120 linhas duplicadas. |
| **Recomendação** | Remover a duplicata (linhas 612-730) e unificar as chamadas. **Quick Win — esforço: ~15min** |

#### DUP-F1-03: `_validate_entity_type` ↔ `_validate_meta_entity_type` — 80% Similar

| Campo | Valor |
|-------|-------|
| **Localizações** | `_validate_entity_type` (linha 263), `_validate_meta_entity_type` (linha 2063) |
| **Similaridade** | **80%** — mesma assinatura, mesma lógica, constantes diferentes |
| **Diferença** | `_VALID_ENTITY_TYPES` vs `_VALID_META_ENTITY_TYPES` |
| **Linhas** | 7 linhas cada (14 total, ~5 duplicadas) |
| **Recomendação** | Extrair função base `_validate_entity_type_in(entity_type, valid_set, field_name)` que aceita o set de tipos válidos como parâmetro. As duas funções wrapper mantêm a API atual. **Quick Win — esforço: ~30min** |

```python
# Proposta de refactor:
def _validate_entity_type_in(entity_type: str, valid_set: set, field_name: str = "entity_type") -> None:
    if entity_type not in valid_set:
        raise ValueError(
            f"Invalid {field_name} '{entity_type}'. "
            f"Must be one of: {sorted(valid_set)}"
        )

def _validate_entity_type(entity_type: str, field_name: str = "entity_type") -> None:
    _validate_entity_type_in(entity_type, _VALID_ENTITY_TYPES, field_name)

def _validate_meta_entity_type(entity_type: str, field_name: str = "entity_type") -> None:
    _validate_entity_type_in(entity_type, _VALID_META_ENTITY_TYPES, field_name)
```

---

### 4.2 Fase 1 — Padrão de Upsert Repetido (memory_module.py)

#### DUP-F1-04: `_shared_memory_upsert_logic` ↔ `_shared_memory_meta_upsert_logic` — 60% Similar

| Campo | Valor |
|-------|-------|
| **Localizações** | `_shared_memory_upsert_logic` (linha 935), `_shared_memory_meta_upsert_logic` (linha 2072) |
| **Similaridade** | **60%** — mesmo fluxo: validate → normalize → db.upsert com ON CONFLICT |
| **Diferenças** | Tabelas diferentes (`shared_business_memory` vs `shared_business_memory_meta`), campos diferentes no payload |
| **Linhas** | ~120 linhas cada (~70 duplicadas estruturalmente) |
| **Recomendação** | Extrair helper `_build_upsert_payload(client_id, entity_type, entity_name, key, ...)` e `_execute_upsert(db, table, payload, conflict_columns)`. **Médio prazo — esforço: ~2h** |

---

## 5. Cross-Phase Duplication

### 5.1 Fase 1 ↔ Fase 1: audit.py (DUP-01 herdado)

| Campo | Valor |
|-------|-------|
| **Arquivos** | `libs/blu_agent_framework/src/blu_agent_framework/audit.py` (56L) |
|  | `libs/blu_supabase_client/src/blu_supabase_client/audit.py` (106L) |
| **Tipo** | Near-duplicate — mesma função `record_audit()`, mesmo RPC |
| **Fases** | Ambas Fase 1 (infra core) |
| **Recomendação** | Consolidar em `blu_supabase_client.audit` (versão canônica). Remover `blu_agent_framework/audit.py`. |
| **Status** | Já documentado em duplication-review.md §DUP-01. Esforço: ~2h. |

### 5.2 Fase 1-4: config.py Boilerplate (DUP-02 herdado)

| Campo | Valor |
|-------|-------|
| **Arquivos** | 7 `config.py`: `blu_agent_framework` (F1), `blu_auth` (F1), `blu_experiment_service` (F1), `blu_llm_service` (F3), `blu_twilio_client` (F1), `agent_api` (F1-5), `tool_pool_api` (F1-5) |
| **Padrão** | `BaseSettings` + `@lru_cache get_x_settings()` — idêntico em 7 lugares |
| **Linhas duplicadas** | ~15L boilerplate × 7 = ~105L |
| **Fases impactadas** | Fase 1 (4), Fase 3 (1), Fase 1-5 (2 services) |
| **Recomendação** | Criar `blu_config_base` com `BluBaseSettings` + `get_cached_settings()` factory |
| **Status** | Já documentado em duplication-review.md §DUP-02. Esforço: ~4h. |

### 5.3 Fase 1 ↔ Fase 2 ↔ Fase 3: exceptions.py (DUP-03 herdado)

| Campo | Valor |
|-------|-------|
| **Arquivos** | `blu_auth/core/exceptions.py` (46L, F1), `blu_elicitation_service/exceptions.py` (105L, F2), `blu_tool_registry/exceptions.py` (52L, F3) |
| **Padrão** | `class XxxError(Exception): def __init__(self, message, code)` — mesmo construtor |
| **Recomendação** | Extrair `BluError(Exception)` com `message` + `code` para `blu_shared_utils` |
| **Status** | Já documentado em duplication-review.md §DUP-03. Esforço: ~1.5h. |

### 5.4 Fase 1 ↔ Fase 3: Timer Context Managers (DUP-04 herdado)

| Campo | Valor |
|-------|-------|
| **Arquivos** | `blu_agent_framework/utils/observability.py::LLMCallTimer` (165L, F1) |
|  | `blu_sql_factory/observability.py::ValidationTimer` (233L, F3) |
| **Padrão** | `__enter__`/`__exit__` com `elapsed_ms` |
| **Recomendação** | Extrair `BluTimer` genérico (sync + async) para `blu_shared_utils` |
| **Status** | Já documentado em duplication-review.md §DUP-04. Esforço: ~1h. |

### 5.5 Fase 1 ↔ Fase 3: Padrão de Query Supabase (NOVO)

| Campo | Valor |
|-------|-------|
| **Arquivos** | `memory_module.py` (F1), `context_module.py` (F1), `rag_module.py` (F3), `sbm_to_lightrag_synthesis.py` (F4) |
| **Padrão** | `db = await get_supabase_client()` + `.schema("public").table(...)` + `.select(...).eq(...).execute()` |
| **Similaridade** | Padrão estrutural — mesma sequência de chamadas, mesmos padrões de filtro |
| **Linhas envolvidas** | ~200 ocorrências de `db.table(...)` em 35 tool_modules |
| **Recomendação** | Criar helper `SupabaseQueryBuilder` em `blu_supabase_client` com métodos: `select_by_client()`, `upsert_with_conflict()`, `update_by_id()`. Reduz boilerplate e padroniza tratamento de erros. **Médio prazo — esforço: ~3h** |

```python
# Exemplo do padrão repetido:
# Em memory_module.py, context_module.py, rag_module.py, sbm_to_lightrag_synthesis.py, ...

db = await get_supabase_client()
result = await (
    db.schema("public")
    .table("shared_business_memory")
    .select("*")
    .eq("client_id", client_id)
    .eq("entity_type", entity_type)
    .execute()
)
```

### 5.6 Fase 1-5: `logging.getLogger(__name__)` — 35 Repetições (NOVO)

| Campo | Valor |
|-------|-------|
| **Arquivos** | Todos os 35 tool_modules + `__init__.py` |
| **Padrão** | `logger = logging.getLogger(__name__)` no topo de cada módulo |
| **Linhas** | 35 linhas idênticas |
| **Severidade** | Baixa — idiomático Python, esperado |
| **Recomendação** | NÃO EXTRAIR. Padrão idiomático aceitável. Manter como está. |
| **Rationale** | `logging.getLogger(__name__)` por módulo é o padrão Python recomendado. Cada módulo deve ter seu próprio logger para filtragem granular. |

### 5.7 Fase 1 ↔ Fase 2: Padrão de Payload de Memória (NOVO)

| Campo | Valor |
|-------|-------|
| **Arquivos** | `memory_module.py::_shared_memory_upsert_logic` (F1), `memory_post_flight.py::_shared_memory_post_flight_logic` (F2) |
| **Padrão** | Construção de `payload` dict com `client_id`, `entity_type`, `entity_name`, `key`, `body`, `source`, `confidence` |
| **Similaridade** | 50% — mesmo schema de campos, validações similares |
| **Impacto** | Se o schema muda, ambos os locais precisam ser atualizados |
| **Recomendação** | Extrair `build_memory_payload()` helper usado por ambos. **Médio prazo — esforço: ~1h** |

### 5.8 Fase 5 ↔ Backend: API Handler Pattern (NOVO)

| Campo | Valor |
|-------|-------|
| **Arquivos** | `apps/blu_v3/src/api/agenda.ts` ↔ `apps/blu_v3/src/api/estrategia.ts` (TS, F5) |
| **Padrão** | `createPaginatedHandler()` e `createMutationHandler()` factories — 25 linhas duplicadas |
| **Similaridade** | 70% — mesma estrutura de fetch com auth header e error handling |
| **Recomendação** | Extrair `createApiHandler()` factory compartilhada. **Baixo esforço — ~30min** |
| **Status** | Parcialmente coberto em duplication-review.md §5.2 (JS/TS) |

---

## 6. Extraction Candidates — Prioritized by Phase

### 6.1 Quick Wins (Fase 1 — memory_module.py)

| # | ID | Ação | Linhas Salvas | Esforço | Fase |
|---|----|------|--------------|---------|------|
| QW-F1-01 | DUP-F1-01 | Remover `_validate_snapshot_frontmatter` duplicata (linha 529) | 72L | ~15min | F1 |
| QW-F1-02 | DUP-F1-02 | Remover `_validate_snapshot_body` duplicata (linha 612) | 120L | ~15min | F1 |
| QW-F1-03 | DUP-F1-03 | Unificar `_validate_entity_type` + `_validate_meta_entity_type` | 5L | ~30min | F1 |

**Total Quick Wins:** ~197 linhas eliminadas em ~1h.

### 6.2 Medium-Term — Cross-Phase

| # | ID | Ação | Linhas Salvas | Esforço | Fases Impactadas |
|---|----|------|--------------|---------|-------------------|
| MT-01 | DUP-01 | Consolidar audit.py | 57L | ~2h | F1 (2 libs) |
| MT-02 | DUP-02 | Extrair blu_config_base | 80L | ~4h | F1, F3, F1-5 |
| MT-03 | DUP-03 | Extrair BluError base class | 40L | ~1.5h | F1, F2, F3 |
| MT-04 | DUP-04 | Extrair BluTimer | 40L | ~1h | F1, F3 |
| MT-05 | DUP-F1-04 | Unificar upsert logic helpers | 70L | ~2h | F1 |
| MT-06 | DUP-F5-01 | Extrair SupabaseQueryBuilder | ~80L | ~3h | F1, F3, F4 |

**Total Medium-Term:** ~367 linhas salvas em ~13.5h.

### 6.3 Deferred (Backlog)

| # | ID | Ação | Linhas Salvas | Esforço | Rationale |
|---|----|------|--------------|---------|-----------|
| DF-01 | DUP-05 | Extrair shared test fixtures | ~150L | ~6h | 9 libs — fazer incrementalmente |
| DF-02 | DUP-F5-02 | Extrair `createApiHandler()` factory (TS) | 25L | ~30min | Baixo impacto, Fase 5 apenas |
| DF-03 | DUP-F1-05 | Extrair `build_memory_payload()` helper | ~30L | ~1h | Depende de DUP-F1-04 |

---

## 7. New Shared Libraries Recommended

### 7.1 `blu_config_base` (NEW — proposed in duplication-review.md)

**Fases impactadas:** F1 (4 libs), F3 (1 lib), F1-5 (2 services)

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

### 7.2 `blu_shared_utils` — Expand Scope

**Adições propostas:**

| Módulo | Origem | Descrição | Fases |
|--------|--------|-----------|-------|
| `blu_error.py` | DUP-03 | `BluError(Exception)` com `message` + `code` | F1, F2, F3 |
| `blu_timer.py` | DUP-04 | `BluTimer` context manager (sync + async) | F1, F3 |
| `blu_validators.py` | DUP-F1-03 | `validate_in_set()` helper genérico | F1 |
| `blu_audit.py` | DUP-01 | Re-export de `blu_supabase_client.audit.record_audit()` | F1 |

---

## 8. Cross-Phase Impact Matrix

| Duplicação | Fase 1 | Fase 2 | Fase 3 | Fase 4 | Fase 5 | Severidade |
|------------|--------|--------|--------|--------|--------|------------|
| DUP-F1-01/02 (snapshot validators 100%) | ❌ | — | — | — | — | P0 (crítico — bug latente) |
| DUP-F1-03 (entity validators 80%) | ⚠️ | — | — | — | — | P1 |
| DUP-01 (audit.py) | ❌ | — | — | — | — | P0 |
| DUP-02 (config.py × 7) | ❌ | — | ❌ | — | ⚠️ | P0 |
| DUP-03 (exceptions.py × 3) | ❌ | ❌ | ❌ | — | — | P1 |
| DUP-04 (timer × 2) | ❌ | — | ❌ | — | — | P1 |
| DUP-F1-04 (upsert pattern) | ⚠️ | — | — | — | — | P2 |
| DUP-F5-01 (Supabase query pattern) | ⚠️ | — | ⚠️ | ⚠️ | — | P2 |
| DUP-F1-05 (memory payload) | ⚠️ | ⚠️ | — | — | — | P2 |
| DUP-F5-02 (API handler TS) | — | — | — | — | ⚠️ | P2 |

---

## 9. Acceptance Criteria Checklist

- [x] 25 artefatos de Fases 1-5 analisados
- [x] Duplicação intra-fase identificada (F1: 4 findings)
- [x] Duplicação cross-fase identificada (8 findings)
- [x] Mapeamento fase→artefato documentado (§3)
- [x] Candidatos de extração priorizados (§6)
- [x] Quick wins identificados (3 itens, ~1h)
- [x] Recomendações de shared libraries (§7)
- [x] Cross-phase impact matrix (§8)
- [x] File saved to `docs/planning/issue-57/duplication-review-f1-5.md`
- [ ] Git commit + push

---

## 10. Notas Metodológicas

1. **A análise é complementar ao `duplication-review.md` original** — este relatório foca na perspectiva de fases, enquanto o anterior foca na classificação técnica dos 88 pygount duplicates.

2. **Intra-fase F1 foi a mais detalhada** porque `memory_module.py` (3.669L) é o maior arquivo do codebase e concentra a maior densidade de duplicação.

3. **Fases 2-4 têm menos duplicação intra-fase** porque são módulos menores e mais focados.

4. **Fase 5 (TypeScript) tem baixa duplicação** com o backend Python — ecossistemas diferentes, baixa prioridade de extração cross-language.

5. **A duplicação de `_validate_snapshot_frontmatter`/`_validate_snapshot_body` é particularmente perigosa**: se alguém corrigir um bug na definição da linha 319 mas esquecer da linha 529, o bug persiste em metade dos call sites. Isto é um **bug latente** que justifica prioridade P0.

---

## 11. Action Items Summary

| Priority | ID | Action | Effort | Phase | Assignee |
|----------|----|--------|--------|-------|----------|
| 🔴 P0 | DUP-F1-01 | Remove duplicate _validate_snapshot_frontmatter (line 529) | 15min | F1 | factory-coder |
| 🔴 P0 | DUP-F1-02 | Remove duplicate _validate_snapshot_body (line 612) | 15min | F1 | factory-coder |
| 🔴 P0 | DUP-01 | Consolidate audit.py | 2h | F1 | factory-coder |
| 🔴 P0 | DUP-02 | Extract blu_config_base | 4h | F1-4 | factory-coder |
| 🟡 P1 | DUP-F1-03 | Unify entity_type validators | 30min | F1 | factory-coder |
| 🟡 P1 | DUP-03 | Extract BluError base class | 1.5h | F1-3 | factory-coder |
| 🟡 P1 | DUP-04 | Extract BluTimer | 1h | F1, F3 | factory-coder |
| 🟢 P2 | DUP-F1-04 | Unify upsert logic helpers | 2h | F1 | factory-coder |
| 🟢 P2 | DUP-F5-01 | Extract SupabaseQueryBuilder | 3h | F1, F3, F4 | factory-coder |
| 🟢 P2 | DUP-F1-05 | Extract build_memory_payload() | 1h | F1-2 | factory-coder |
| 🟢 P2 | DUP-F5-02 | Extract createApiHandler() factory (TS) | 30min | F5 | factory-coder |

---
