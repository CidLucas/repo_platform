# Patterns — Issue #31 / T4.3 (knowledge_graph_summary update)

> Gerado por factory-planner em 2026-06-19

## Pattern 1: Pydantic Schema com campo opcional versionado

**Onde:** `context_schemas.py` — todo modelo de context section

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
