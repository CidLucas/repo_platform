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
