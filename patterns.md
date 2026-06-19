# Design Patterns — Issue #32: Retention & Prune

> Patterns identified in the codebase that inform the retention/prune design.
> Extracted: 2026-06-19

## 1. Routine Function Registration Pattern

**Fonte:** `routine_functions.py:37-56` (`memory.write_dimension_state`)

```python
@register(
    "memory.write_dimension_state",
    description="...",
    inputs=[{"key": "dimension", "type": "str", ...}],
    outputs=[{"key": "memory_written", "type": "bool", ...}],
)
async def _write_dimension_state(inputs: dict, client_id: str) -> dict:
    ...
```

**Aplicação para prune:** Registrar `memory.prune_expired_shared_memory` com o mesmo padrão. Outputs: `{deleted_count, archived_count, pruned_entities}`.

## 2. Supabase Client Access Pattern

**Fonte:** `routine_functions.py:2731` e `memory_module.py:70`

```python
from blu_supabase_client import get_supabase_client
db = get_supabase_client(use_service_role=True)  # rotinas batch
db = await get_supabase_client()                  # tools com user context
```

**Aplicação:** Prune job usa `use_service_role=True` (roda como sistema, sem client_id individual). Precisa iterar por client_id.

## 3. Tool Registration Pattern (MCP)

**Fonte:** `memory_module.py:320-382`

```python
@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    @mcp.tool(name="shared_memory_list", description="...")
    @mcp_inject_client_id
    async def shared_memory_list(ctx, ..., client_id=None) -> dict: ...
```

**Aplicação:** `shared_memory_restore_archived` e `shared_memory_list_archived` seguem o mesmo padrão. Uma função de lógica separada + wrapper MCP com `@mcp_inject_client_id`.

## 4. Entity Validation Pattern

**Fonte:** `memory_module.py:25-44`

```python
_VALID_ENTITY_TYPES = frozenset({"skill", "client", "contact", "supplier", "user"})

def _validate_entity_type(entity_type: str, field_name: str = "entity_type") -> None:
    if entity_type not in _VALID_ENTITY_TYPES:
        raise ValueError(...)
```

**Aplicação:** Volume limit trigger e TTL tiers referenciam entity_type — usar a mesma validação.

## 5. Soft-Delete via Timestamp Pattern (proposto)

**Fonte:** schema de `dimension_state` (valid_until) + design de `expires_at` no roadmap

```sql
-- O roadmap Fase 1.1 já menciona:
-- expires_at para TTL de memórias não confirmadas (default: 14 dias)
-- curated=true zera expires_at
```

**Aplicação:** `archived_at` segue o mesmo padrão de `expires_at`: nullable timestamptz. Soft-delete = SET archived_at = now(). Hard-delete = DELETE WHERE archived_at < now() - INTERVAL '90 days'.

## 6. Unique Constraint + Conflict Pattern

**Fonte:** `memory_module.py:172-181` (duplicate link detection)

```python
except Exception as exc:
    if "duplicate key" in str(exc).lower() or "uq_shared_memory_link" in str(exc).lower():
        raise ValueError("Link already exists: ...")
```

**Aplicação:** Volume limit trigger pode usar ON CONFLICT + subquery para contar registros existentes antes de permitir insert.

## 7. Migration Naming Convention

**Fonte:** `supabase/migrations/proposed/20260619000000_*.sql`

- Timestamp: YYYYMMDDHHMMSS
- Descriptive slug: `shared_business_memory`, `shared_memory_links`
- Proposed/ directory = não aplicado, aguardando revisão
- Applied/ directory = já aplicado em produção

**Aplicação:** Nova migration: `20260620000000_shared_memory_lifecycle.sql`
