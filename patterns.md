# Padrões Arquiteturais — Issue #18: Post-flight Shared Memory (T1.2)

> Planejamento factory-planner, branch `phase-0/issue-18-sm-postflight`
> Gerado: 2026-06-19 | Fase 1, T1.2

## 1. Padrões a seguir (existentes no codebase)

### P1 — Módulo de Tool com `@register_module`

**Local**: `services/tool_pool_api/src/tool_pool_api/server/tool_modules/memory_module.py`

Cada módulo exporta uma função `register_tools(mcp: FastMCP) -> list[str]` decorada com `@register_module`. A função registra tools MCP e retorna a lista de nomes registrados. O `__init__.py` importa o módulo e chama cada `register_fn`.

**Template para `memory_post_flight.py`**:
```python
class AvailableTools(BaseModel):
    tier: str = "BASIC"
    enabled_tool_names: list[str] = Field(default_factory=list)
    # ... campos existentes

    # NOVO (T4.3a):
    knowledge_graph_summary: KnowledgeGraphSummary | None = None
```

**Convenção:** Campos novos são opcionais (`| None = None`) para retrocompatibilidade. Version via campo `version: int` no sub-modelo (DD-04).

---

## Pattern 2: Módulo de tool interna via FastMCP + register_module

**Onde:** Todos os módulos em `tool_modules/` (ex: `memory_module.py`, `context_module.py`)
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
from . import register_module

@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    @mcp.tool(name="update_knowledge_graph_summary")
    async def update_knowledge_graph_summary(client_id: str, summary: dict) -> bool:
        ...
    return ["update_knowledge_graph_summary"]
```

**Convenção:** Função `register_tools(mcp)` registrada via decorator `@register_module`. Import no `__init__.py` (`register_all_tools`). Registro no `AVAILABLE_MODULES` com metadados. Tools internas (não-MCP) usam mesmo padrão mas não são expostas no MCP externo — chamadas diretas via client.

---

## Pattern 3: Context Service com Redis cache + clear_context_cache

**Onde:** `context_service.py`

```python
CACHE_TTL_SECONDS = 300
async def clear_context_cache(self, client_id: UUID) -> None:
    cache_key = self._get_cache_key(client_id)
    await asyncio.to_thread(self.cache.delete, cache_key)
```

**Convenção:** Após atualizar `clientes_blu.available_tools`, invalidar cache via `clear_context_cache(client_id)`. Próximo `get_client_context()` recarrega do Supabase. TTL 5 minutos como fallback.

---

## Pattern 4: Domain projection com _DOMAIN_SECTIONS

**Onde:** `context_service.py` — `get_domain_projection()`

```python
_DOMAIN_SECTIONS: dict[str, frozenset[str]] = {
    "analytics": frozenset({"data_schema", "available_tools", "company_profile"}),
    "rag":      frozenset({"company_profile", "policies", "brand_voice"}),
    # ...
}
```

**⚠️ DISCREPÂNCIA:** O plano intake afirma que `available_tools` está nos domínios `rag`, `documents`, `knowledge` — mas o código atual **não** inclui `available_tools` nesses domínios. APENAS `analytics`, `data`, `sql`, `config`, `settings` têm `available_tools`.

**Ação T4.3c:** Decidir se deve adicionar `available_tools` a `rag`/`documents`/`knowledge` OU documentar que specialists nesses domínios acessam via `get_knowledge_graph_summary()` helper separado.

---

## Pattern 5: Upsert JSONB com merge parcial

**Onde:** `memory_module.py` — `shared_memory_upsert`, `context_module.py`

```python
# Ler existente
existing = supabase.table("clientes_blu").select("available_tools").eq("client_id", cid).single().execute()
tools = existing.data.get("available_tools") or {}
# Merge parcial
tools["knowledge_graph_summary"] = summary_dict
# Escrever
supabase.table("clientes_blu").update({"available_tools": tools}).eq("client_id", cid).execute()
```

**Convenção:** Ler → merge (preservar campos existentes) → escrever. Nunca overwrite cego. Usar optimistic locking via `version` quando possível (R2).

---

## Pattern 6: Testes unitários com mock Supabase

**Onde:** `services/tool_pool_api/tests/unit/test_tools.py`

```python
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.mark.asyncio
async def test_my_function():
    mock_db = MagicMock()
    with patch("modulo.get_supabase_client", return_value=mock_db):
        result = await minha_funcao(client_id, summary)
        assert result is True
```

**Convenção:** AsyncMock para métodos async do Supabase. MagicMock para client. Patch nos imports de módulo (não de biblioteca).

---

## Pattern 7: Structured logging para auditoria

**Onde:** `context_module.py`, `memory_module.py`

```python
logger.info(f"knowledge_graph_summary updated for {client_id}: {total_entities} entities, {total_documents} docs, last_sync={last_sync}")
```

**Convenção:** Log INFO com client_id + métricas chave. Não logar corpo completo (PII). Structured = key=value no formato.

---

## Resumo

| # | Pattern | Arquivo referência |
|---|---------|-------------------|
| 1 | Schema Pydantic opcional + versionado | `context_schemas.py` |
| 2 | Módulo tool via @register_module | `memory_module.py` |
| 3 | Cache Redis + clear_context_cache | `context_service.py` |
| 4 | Domain projection _DOMAIN_SECTIONS | `context_service.py` |
| 5 | Upsert JSONB merge parcial | `memory_module.py` |
| 6 | Testes mock Supabase | `test_tools.py` |
| 7 | Structured logging | `context_module.py` |

**Total: 7 patterns mapeados.**
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
