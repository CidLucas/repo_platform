# Repo Index — Issue #31 / T4.3 (knowledge_graph_summary update)

> Gerado por factory-planner em 2026-06-19
> Branch: `phase-0/issue-31-eventos-trigger-handoffs`

## Arquivos a modificar (5)

| # | Arquivo | Ação | Subtarefa |
|---|---------|------|-----------|
| 1 | `libs/blu_models/src/blu_models/context_schemas.py` | Adicionar classes `KnowledgeGraphSummary` + `EntitySummary`; campo `knowledge_graph_summary` em `AvailableTools` | T4.3a |
| 2 | `services/tool_pool_api/src/tool_pool_api/server/tool_modules/knowledge_graph_sync.py` | NOVO — módulo com `update_knowledge_graph_summary()` | T4.3b, T4.3d |
| 3 | `services/tool_pool_api/src/tool_pool_api/server/tool_modules/__init__.py` | Registrar `knowledge_graph_sync` no `AVAILABLE_MODULES` + import no `register_all_tools` | T4.3b |
| 4 | `libs/blu_context_service/src/blu_context_service/context_service.py` | Adicionar `get_knowledge_graph_summary()` helper; **revisar** `_DOMAIN_SECTIONS` (rag/documents/knowledge não incluem `available_tools`) | T4.3c |

## Arquivos de teste a criar (3)

| # | Arquivo | Subtarefa |
|---|---------|-----------|
| 5 | `libs/blu_models/tests/unit/test_context_schemas.py` | T4.3e |
| 6 | `services/tool_pool_api/tests/unit/test_knowledge_graph_sync.py` | T4.3e |
| 7 | `libs/blu_context_service/tests/unit/test_knowledge_graph_summary.py` | T4.3e |

## Arquivos de contexto (read-only, 3)

| # | Arquivo | Propósito |
|---|---------|-----------|
| 8 | `libs/blu_models/src/blu_models/blu_client_context.py` | Modelo `BluClientContext` — consumidor do `available_tools` |
| 9 | `docs/llm_wiki/SHARED_MEMORY_DESIGN.md` | Especificação T4.3 original |
| 10 | `docs/system_reference/AGENT_SYSTEM.md` | Domínios de specialists, routing |

## Dependências externas (próximas fases)

| Dependência | Status | Bloqueia? |
|-------------|--------|-----------|
| T4.1 (enrichment job SBM→LightRAG) | Não implementado | Não — campo opcional (None até T4.1 existir) |
| T4.2 (deduplication) | Não implementado | Não — usa `total_entities` do summary, não escreve |
| LightRAG (Fase 3) | Não implementado | Não — summary fica None/empty até disponível |
| T3.1 (LightRAG spike) | Desconhecido (não verificado) | Não — T4.3 é preparatório |

## Total: 7 arquivos (4 modify + 3 new test files)
# Repo Index — Issue #18: Post-flight Shared Memory (T1.2)

> Planejamento factory-planner, branch `phase-0/issue-18-sm-postflight`
> Gerado: 2026-06-19 | Fase 1, T1.2

## 1. Arquivos relevantes para implementação

### 1.1 Shared Memory — Infraestrutura existente (Fase 0)

| Arquivo | Descrição | Relevância p/ T1.2 |
|---------|-----------|---------------------|
| `services/tool_pool_api/src/tool_pool_api/server/tool_modules/memory_module.py` | Tools L1: `shared_memory_list`, `shared_memory_link`, `shared_memory_unlink`, `shared_memory_get_links` | **ALTA** — Padrão de módulo a seguir. `_VALID_ENTITY_TYPES` precisa ser expandido. Funções `_*_logic` separadas das tools MCP. |
| `services/tool_pool_api/src/tool_pool_api/server/tool_modules/__init__.py` | Registro de módulos (`@register_module`). Importa `memory_module`. | **ALTA** — Precisará importar novo `memory_post_flight`. `AVAILABLE_MODULES["memory"]` precisa de atualização. |
| `supabase/migrations/proposed/20260619000000_shared_business_memory.sql` | Tabela `shared_business_memory` com CHECK constraint em `entity_type` | **ALTA** — Migration T1.2a precisa ALTER TABLE para adicionar novos entity_types. |
| `supabase/migrations/proposed/20260619000001_shared_memory_links.sql` | Tabela `shared_memory_links` | **BAIXA** — Links existentes, sem mudança necessária. `agent_link_pending` vai em tabela separada ou campo `source='agent_pending'`. |

### 1.2 Agent API — Hook point

| Arquivo | Descrição | Relevância p/ T1.2 |
|---------|-----------|---------------------|
| `services/agent_api/src/agent_api/core/service.py` | `ChatService` com `process_message()` e `process_message_stream()`. `AgentService.stream_agent_response()`. | **CRÍTICO** — Hook post-flight será inserido após `graph.ainvoke()` (sync) e após stream final (async). Infra de fire-and-forget já existe: `_fire_and_forget()`, `_background_tasks: set`. |
| `services/agent_api/src/agent_api/core/factory.py` | `BuiltAgent`, `get_factory()`, `get_context_service()` | **MÉDIA** — Referenciado em service.py, sem mudanças diretas. |
| `libs/blu_agent_framework/state.py` | `AgentState` e `create_initial_state()` | **BAIXA** — Estado do grafo, sem mudanças. |

### 1.3 Supabase Client

| Arquivo | Descrição | Relevância p/ T1.2 |
|---------|-----------|---------------------|
| `libs/blu_supabase_client/` | `get_supabase_client()` → AsyncSupabaseClient | **ALTA** — Módulo `memory_post_flight.py` usará o mesmo client. Padrão: `db.table("shared_business_memory").upsert(...).execute()`. |

### 1.4 Documentação e Inventário

| Arquivo | Descrição | Relevância p/ T1.2 |
|---------|-----------|---------------------|
| `docs/system_reference/TOOL_INVENTORY.md` | Catálogo completo de tools (240 linhas) | **ALTA** — T1.2f adicionará `shared_memory_post_flight` como CUSTOM/INTERNAL. |
| `docs/roadmap/blu-intelligent-memory.md` | Roadmap Fase 1–5 da memória inteligente | **MÉDIA** — Contexto de design. SHARED_MEMORY_DESIGN.md derivará daqui. |
| `docs/llm_wiki/` | (diretório não existe ainda) | **NOVO** — T1.2d criará `SHARED_MEMORY_DESIGN.md` neste path. |

### 1.5 Testes

| Arquivo | Descrição | Relevância p/ T1.2 |
|---------|-----------|---------------------|
| `services/tool_pool_api/tests/` | Testes existentes: unitários e integração. Sem testes de memory ainda. | **ALTA** — T1.2e criará `test_memory_post_flight.py`. Padrão de teste a seguir: `test_integration/test_tool_pool.py`. |

## 2. Padrões de código descobertos

### 2.1 Módulo de Tool (`memory_module.py`)

```python
@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    registered_tools: list[str] = []

    @mcp.tool(name="shared_memory_list", description="...")
    @mcp_inject_client_id
    async def shared_memory_list(ctx, ..., client_id=None) -> dict:
        if not client_id: raise ToolError(...)
        return await _shared_memory_list_logic(client_id=client_id, ...)

    registered_tools.append("shared_memory_list")
    return registered_tools
```

**Padrão**: `@register_module` + `@mcp.tool` + `@mcp_inject_client_id` + `_*_logic()` separada.

### 2.2 Fire-and-forget (`service.py`)

```python
_background_tasks: set = set()

def _fire_and_forget(coro) -> None:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
```

### 2.3 Supabase queries (`memory_module.py`)

```python
db = await get_supabase_client()
result = await db.schema("public").table("shared_business_memory")
    .select(...).eq("client_id", client_id).execute()
```

### 2.4 Import pattern (`__init__.py`)

Módulos importados explicitamente: `from . import memory_module` → trigger `@register_module`.

## 3. Conflitos detectados

| ID | Conflito | Impacto | Resolução |
|----|----------|---------|-----------|
| C1 | `_VALID_ENTITY_TYPES` em `memory_module.py` é `frozenset`. Adicionar `agent_result`, `agent_metadata`, `agent_link_pending` requer modificar este módulo também. | **MÉDIO** — Validation em `shared_memory_link/unlink` usa este set. Se não expandir, links de/para `agent_result` falhariam. | Expandir `_VALID_ENTITY_TYPES` para incluir os novos tipos OU manter o post-flight independente (não expõe agent types via link). Recomendação: DD-06 diz que post-flight é internal — não precisa de link validation nos novos tipos. Manter separado. |
| C2 | CHECK constraint no SQL é rígido. ALTER TABLE necessário antes de inserir com novos entity_types. | **ALTO** — Sem migration, upsert falha. | Migration T1.2a é pré-requisito de deploy. Ordem: migration → deploy module → hook. |
| C3 | `memory_module.py` referencia `docs/llm_wiki/SHARED_MEMORY_DESIGN.md` (linha 9), mas arquivo não existe. | **BAIXO** — Link quebrado em docstring. | T1.2d criará o arquivo. Atualizar referência no memory_module.py se necessário. |
| C4 | `_fire_and_forget` em `service.py` é síncrono (não async). Hook post-flight precisará ser async para acessar Supabase. | **BAIXO** — `asyncio.create_task()` aceita corotina. | OK — `_fire_and_forget(shared_memory_post_flight(...))` funciona. |
| C5 | `AgentService.stream_agent_response()` não tem infra de `_background_tasks`. | **MÉDIO** — Se hook também deve rodar para standalone agents, precisa adicionar tracking. | Escopo T1.2 cobre apenas ChatService (frontdesk + specialist handoff). AgentService fica para iteração futura. |
| C6 | `docs/llm_wiki/` diretório não existe. | **BAIXO** | T1.2d criará o diretório e o arquivo. |

## 4. Dependências entre subtarefas

```
T1.2a (migration SQL)  ─── independente (DDL apenas)
T1.2b (memory_post_flight.py) ─── depende de T1.2a (valida entity_types no CHECK)
T1.2c (hook service.py) ─── depende de T1.2b (importa módulo)
T1.2d (documentação) ─── independente (pode rodar em paralelo)
T1.2e (testes) ─── depende de T1.2b (testa o módulo)
T1.2f (TOOL_INVENTORY) ─── depende de T1.2b (lista a tool)
```

**Recomendação de paralelismo**: T1.2a + T1.2d podem rodar em paralelo. Depois T1.2b → T1.2c e T1.2e + T1.2f em paralelo.
