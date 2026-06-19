# Padrões Arquiteturais — Issue #18: Post-flight Shared Memory (T1.2)

> Planejamento factory-planner, branch `phase-0/issue-18-sm-postflight`
> Gerado: 2026-06-19 | Fase 1, T1.2

## 1. Padrões a seguir (existentes no codebase)

### P1 — Módulo de Tool com `@register_module`

**Local**: `services/tool_pool_api/src/tool_pool_api/server/tool_modules/memory_module.py`

Cada módulo exporta uma função `register_tools(mcp: FastMCP) -> list[str]` decorada com `@register_module`. A função registra tools MCP e retorna a lista de nomes registrados. O `__init__.py` importa o módulo e chama cada `register_fn`.

**Template para `memory_post_flight.py`**:
```python
@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    registered_tools: list[str] = []
    
    # Tool interna: NÃO exposta via @mcp.tool — apenas lógica interna
    # A função _shared_memory_post_flight_logic é chamada pelo hook no service.py
    
    logger.info("[PostFlight Module] Internal tool ready (not exposed via MCP).")
    return registered_tools  # lista vazia = internal only
```

**Variação para DD-06 (internal tool)**: Módulo registra mas retorna `[]` — sem tools MCP expostas. A lógica é importada diretamente pelo hook em service.py.

### P2 — Separação lógica ↔ tool MCP

Toda tool MCP delega para uma função `_*_logic()` async pura, sem dependência de `Context` ou `FastMCP`. Isso permite testar a lógica isoladamente e reusar de outros contextos (como o hook em service.py).

**Template**:
```python
async def _shared_memory_post_flight_logic(
    client_id: str,
    agent_slug: str,
    session_id: str,
    agent_result: dict | None = None,
    agent_metadata: dict | None = None,
    suggested_links: list[dict] | None = None,
) -> dict:
    """Insere/upsert resultados do agente na shared_business_memory."""
    ...
```

### P3 — Fire-and-forget assíncrono

**Local**: `services/agent_api/src/agent_api/core/service.py` (linhas 37, 162-165)

```python
_background_tasks: set = set()

def _fire_and_forget(coro) -> None:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
```

**Uso no hook**:
```python
_fire_and_forget(
    _shared_memory_post_flight_logic(
        client_id=client_id,
        agent_slug=_selected_agent,
        session_id=session_id,
        agent_result={...},
        agent_metadata={...},
    )
)
```

### P4 — Supabase client assíncrono

**Local**: `memory_module.py` (via `blu_supabase_client`)

```python
db = await get_supabase_client()
result = await db.schema("public").table("shared_business_memory")
    .upsert(payload, on_conflict="client_id,entity_type,entity_name,key")
    .execute()
```

A constraint `uq_shared_memory_entry UNIQUE (client_id, entity_type, entity_name, key)` permite upsert nativo.

### P5 — Extração de tool_calls do AIMessage

**Local**: `service.py` — o LangGraph expõe `AIMessage.tool_calls` como lista de dicts com `name` e `args`. O hook extrai apenas `name` (DD-03: `tool_usage:<name>`) sem payloads sensíveis.

```python
if isinstance(last_msg, AIMessage):
    tool_names = [tc.get("name") for tc in getattr(last_msg, "tool_calls", []) or []]
```

### P6 — Naming convention com prefixos semânticos (DD-03)

Keys salvas na shared_business_memory seguem convenção:

| Prefixo | Significado | Exemplo |
|---------|-------------|---------|
| `decision:` | Decisão tomada pelo agente | `decision:priorizar_fornecedor_x` |
| `finding:` | Descoberta/informação extraída | `finding:cliente_atrasado_3_meses` |
| `summary:` | Resumo do que foi feito | `summary:analise_financeira_q1` |
| `tool_usage:` | Ferramenta utilizada (apenas nome) | `tool_usage:execute_sql` |

`entity_name` segue `<agent_slug>:<session_id[:8]>` para resultados e `<agent_slug>` para metadados.

### P7 — Noise suppression (DD-04)

Apenas o **último estado significativo** é salvo. Estados intermediários do LangGraph são descartados. O hook extrai:
- Último `AIMessage.content` como `agent_result`
- `tool_calls` do AIMessage (apenas nomes)
- `session_id` + `agent_slug` + `elapsed` como `agent_metadata`

Estados intermediários (nós do grafo, elicitation, tool outputs) NÃO são persistidos.

## 2. Decisões de design confirmadas

| ID | Decisão | Status | Implicação |
|----|---------|--------|------------|
| DD-01 | Módulo separado `memory_post_flight.py` | ✅ Confirmado | Segue padrão `memory_module.py`. Arquivo em `tool_modules/`. |
| DD-02 | 3 novos entity_types | ✅ Confirmado | Migration SQL necessária. `_VALID_ENTITY_TYPES` pode ou não ser expandido (ver C1). |
| DD-03 | Prefixos semânticos em keys | ✅ Confirmado | Validação opcional no módulo (warning, não erro). |
| DD-04 | Noise suppression | ✅ Confirmado | Hook extrai APENAS estado final. Upsert substitui entradas anteriores. |
| DD-05 | Fire-and-forget async | ✅ Confirmado | Infra `_background_tasks` já existe. |
| DD-06 | Internal tool (não MCP) | ✅ Confirmado | `@register_module` retorna `[]` vazio. Lógica chamada direto pelo hook. |

## 3. Design questions respondidas

| ID | Pergunta | Resposta do planner |
|----|----------|---------------------|
| DQ1 | Síncrono vs fire-and-forget? | **Fire-and-forget assíncrono**. Padrão `_background_tasks` já existe em service.py. Post-flight não deve bloquear o usuário. |
| DQ2 | Onde extrair agent_result? | **Último AIMessage** da resposta (`.content`). Se for frontdesk → specialist, o último AIMessage é o do specialist (já substituído no estado). |
| DQ3 | tool_usage: nomes ou payloads? | **Apenas nomes**. Payloads podem conter dados sensíveis (PII, queries SQL, etc.). |
| DQ4 | agent_link_pending: automático ou aprovação? | **Automático com source='agent_pending'**. Links criados como `agent_link_pending` ficam na tabela `shared_memory_links` com `source='agent_pending'` para validação posterior por rotina T4.4. |

## 4. Anti-padrões a evitar

- ❌ Bloquear o fluxo principal: post-flight NUNCA deve fazer `await` no caminho crítico.
- ❌ Salvar estados intermediários: apenas último estado significativo.
- ❌ Expor post-flight como tool MCP: apenas hook interno.
- ❌ Hardcodar entity_types no hook: usar constantes do módulo.
- ❌ Silenciar erros completamente: log warning se post-flight falhar.
