# repo-index.md — Planejamento Issue #31 (Eventos de Trigger para Handoffs — T4.3)

> Gerado por factory-planner em 2026-06-19
> Branch: phase-0/issue-31-eventos-de-trigger-para-handoffs

## Arquivos diretamente afetados

| Arquivo | Linhas | Função atual | Ação T4.3 |
|---|---|---|---|
| `services/tool_pool_api/src/tool_pool_api/server/tool_modules/memory_module.py` | 606 | Tools de shared memory (list, link, unlink, get_links) | **Modificar:** Adicionar tool `handoff_trigger_event` + lógica de negócio |
| `services/agent_api/src/agent_api/core/service.py` | 704 | ChatService + AgentService — streaming, detecção de handoff sentinel `__ROUTE_TO_SPECIALIST__` | **Modificar:** Inserir hook pós-handoff que chama `handoff_trigger_event` via fire-and-forget (linha 522, após yield do evento handoff) |
| `supabase/migrations/proposed/<next>_handoff_events_log.sql` | (novo) | Inexistente | **Criar:** Migration com tabela `handoff_events_log` (uuid PK, client_id FK, session_id, source_agent, target_agent, reason, triggered_at, triggered_routines_count) + RLS |
| `docs/llm_wiki/SHARED_MEMORY_DESIGN.md` | 0 (não existe) | Inexistente — referenciado no plano mas nunca criado | **Criar:** Doc completo incluindo seção T4.3 (problema, solução, schema tool, hook, tabela auditoria, watchdog) |
| `services/tool_pool_api/src/tool_pool_api/server/tool_modules/__init__.py` | 332 | Registry de módulos + AVAILABLE_MODULES | **Modificar:** Atualizar `AVAILABLE_MODULES["memory"]["tools"]` para incluir `handoff_trigger_event` |

## Arquivos de contexto (não modificados, mas referenciados)

| Arquivo | Relevância |
|---|---|
| `docs/system_reference/ROUTINES_SYSTEM.md` (seção 3.3, 5, 9) | Define event triggers (`handoff` será novo event_type). Catálogo de 25 rotinas — `handoff_watchdog` será a 26ª. |
| `docs/roadmap/blu-intelligent-memory.md` (Fase 4) | Roadmap da Fase 4 — enriquecimento do grafo com handoffs monitorados |
| `services/agent_api/src/agent_api/core/routines.py` (linhas 1206-1236) | `_fire_on_complete_events` — padrão de chamada a `fire_event_for_client` RPC |
| `services/agent_api/src/agent_api/api/google_calendar_webhook_router.py` (linhas 70-87) | `_fire_event` — padrão alternativo de chamada a `fire_event_for_client` via `get_supabase_client()` |
| `services/agent_api/src/agent_api/core/routine_artifacts.py` (linhas 509-526) | Fire-and-forget best-effort pattern com `fire_event_for_client` + `logger.warning` em falha |
| `supabase/migrations/proposed/20260619000000_shared_business_memory.sql` | Migration base da shared_memory — referência de convenção (BEGIN/COMMIT, comentários, RLS) |
| `supabase/migrations/proposed/20260619000001_shared_memory_links.sql` | Migration de links — referência adicional de convenção |
| `services/tool_pool_api/src/tool_pool_api/__init__.py` | Vazio — sem riscos de conflito |

## Dependências verificadas

| Dependência | Status | Impacto |
|---|---|---|
| `fire_event_for_client` RPC | ✅ Existente e ativo (87 ocorrências no codebase) | T4.3.1 pode chamar diretamente |
| `__ROUTE_TO_SPECIALIST__` sentinel | ✅ Implementado em `service.py:510-516` | T4.3.2 hook point já existe — #25 (T1.3) está completo |
| #30 (T4.2 meta/) | ⏳ Em outra branch — apenas docs | Não bloqueia T4.3 (sem dependência de código) |
| #29 (T4.1 handoffs/) | ⏳ Em outra branch — apenas docs | Não bloqueia T4.3 (sem dependência de código) |
| `get_supabase_client(use_service_role=True)` | ✅ Padrão usado em vários lugares | T4.3.1 tool usa `use_service_role=True` para chamar RPC |

## Estrutura de diretórios relevante

```
repo_platform/
├── docs/
│   ├── llm_wiki/                          ← T4.3.5: criar SHARED_MEMORY_DESIGN.md
│   ├── system_reference/
│   │   └── ROUTINES_SYSTEM.md             ← Referência: eventos + catálogo
│   └── roadmap/
│       └── blu-intelligent-memory.md      ← Referência: Fase 4 design
├── supabase/migrations/proposed/
│   └── <next>_handoff_events_log.sql      ← T4.3.3: NOVA migration
└── services/
    ├── tool_pool_api/src/tool_pool_api/server/tool_modules/
    │   ├── memory_module.py               ← T4.3.1: ADICIONAR tool handoff_trigger_event
    │   └── __init__.py                    ← T4.3.1: atualizar AVAILABLE_MODULES
    └── agent_api/src/agent_api/core/
        └── service.py                     ← T4.3.2: hook pós-handoff
```

## Convenções encontradas

- **Migrations:** Timestamp YYYYMMDDHHMMSS + slug descritivo. `proposed/` = pendente revisão, `applied/` = produção.
- **Tools MCP:** Decorator `@register_module` + função `register_tools(mcp) -> list[str]` + `@mcp.tool(name=...)` + `@mcp_inject_client_id`. Lógica de negócio em função async separada.
- **RPC calls:** `db.rpc("fire_event_for_client", {...}).execute()` dentro de `asyncio.to_thread(lambda: ...)` para não bloquear event loop.
- **Fire-and-forget:** Envolto em try/except com `logger.warning` — falha no evento NUNCA reverte a operação principal.
- **Nomes de tools:** snake_case com prefixo descritivo (`shared_memory_*`, `handoff_*`).
