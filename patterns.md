# Design Patterns — T4.2: Diretório meta/

> Extraídos do codebase para guiar a implementação das 4 novas tools meta_*.
> Issue: [#30](https://github.com/CidLucas/repo_platform/issues/30)

## P1 — Tool Registration via `@register_module`

**Fonte:** `memory_module.py`, `__init__.py`

Toda tool segue o ciclo de registro em 2 camadas:

```python
# memory_module.py
@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    registered_tools: list[str] = []
    # ... define tools ...
    registered_tools.append("tool_name")
    return registered_tools

# __init__.py
AVAILABLE_MODULES["memory"]["tools"] = [
    "shared_memory_list",
    # ... novas tools ...
]
```

**Aplicação para T4.2:** As 4 novas tools (meta_read, meta_write, meta_delete, meta_list) seguem este padrão. Devem ser adicionadas tanto no `register_tools()` quanto no `AVAILABLE_MODULES`.

---

## P2 — Logic Function + MCP Wrapper Separation

**Fonte:** `memory_module.py` (funções `_shared_memory_*_logic`)

Separação estrita entre lógica de negócio (async, testável, sem dependências MCP) e wrapper MCP (decorators, logging, tratamento de erro):

```python
# Logic function — testável, sem MCP
async def _shared_memory_list_logic(
    client_id: str,
    entity_type: str | None = None,
) -> dict:
    db = await get_supabase_client()
    result = await db.schema("public").table(_TABLE).select(...).eq(...).execute()
    return {"entities": [...]}

# MCP wrapper — decorators, logging, error handling
@mcp.tool(name="shared_memory_list", description="...")
@mcp_inject_client_id
async def shared_memory_list(
    ctx: Context,
    entity_type: str | None = None,
    client_id: str | None = None,
) -> dict:
    if not client_id:
        raise ToolError("client_id is required")
    try:
        return await _shared_memory_list_logic(client_id=client_id, entity_type=entity_type)
    except ValueError as exc:
        raise ToolError(str(exc))
```

**Aplicação para T4.2:** Cada meta tool terá `_meta_{verb}_logic` + wrapper `meta_{verb}` seguindo exatamente este template.

---

## P3 — Parameter Order Convention (MCP tools)

**Fonte:** Todas as tools em `memory_module.py`

Ordem fixa de parâmetros:

```
ctx: Context          # primeiro — sempre
<business params>     # meio — type hints, defaults
client_id: str | None # ÚLTIMO — injetado por @mcp_inject_client_id
```

**Aplicação para T4.2:** As meta tools seguem esta convenção:

```python
async def meta_write(
    ctx: Context,
    path: str,           # business param
    key: str,
    value: Any,
    entity_type: str = "client",
    entity_name: str | None = None,
    source: str = "specialist",
    confidence: float = 1.0,
    client_id: str | None = None,  # ÚLTIMO
) -> dict:
```

---

## P4 — Entity Validation Pattern

**Fonte:** `memory_module.py` (`_validate_entity_type`, `_VALID_ENTITY_TYPES`)

```python
_VALID_ENTITY_TYPES: frozenset[str] = frozenset({
    "skill", "client", "contact", "supplier", "user"
})

def _validate_entity_type(entity_type: str, field_name: str = "entity_type") -> None:
    if entity_type not in _VALID_ENTITY_TYPES:
        raise ValueError(
            f"Invalid {field_name} '{entity_type}'. Must be one of: {sorted(_VALID_ENTITY_TYPES)}"
        )
```

**Aplicação para T4.2:** Meta tools reusam `_validate_entity_type()`. Adicionalmente, criam `_validate_meta_path()` para validar o formato do path.

---

## P5 — Path Validation Pattern (NOVO para T4.2)

```python
_META_PREFIX = "meta/"

def _validate_meta_path(path: str) -> tuple[str, str]:
    """Valida e normaliza path. Retorna (full_path, clean_path)."""
    path = path.strip().strip("/").lower()
    if not path:
        raise ValueError("Path is required for meta tools")
    full_path = f"{_META_PREFIX}{path}"
    if not re.match(r'^[a-z][a-z0-9_/-]*$', full_path):
        raise ValueError(f"Invalid meta path: {path}")
    if len(full_path) > 512:
        raise ValueError(f"Path too long (max 512 chars): {len(full_path)}")
    return full_path, path
```

---

## P6 — Supabase Query Patterns

**Fonte:** `memory_module.py`

| Operação | Padrão |
|----------|--------|
| SELECT | `db.schema("public").table(_TABLE).select("cols").eq("client_id", cid).execute()` |
| SELECT com filtro composto | `.eq(...).eq(...).order(...)` encadeado |
| INSERT | `db.schema(...).table(...).insert(payload).execute()` |
| UPSERT | `db.schema(...).table(...).upsert(payload, on_conflict="cols").execute()` |
| DELETE | `db.schema(...).table(...).delete().eq("id", id).eq("client_id", cid).execute()` |
| Path prefix query | `db.schema(...).table(_TABLE).select(...).eq("client_id", cid).like("path", f"{prefix}%").execute()` |

**Aplicação para T4.2:**
- `meta_read` → SELECT com `.eq("path", full_path).eq("key", key).maybe_single()`
- `meta_write` → UPSERT com `on_conflict="client_id,entity_type,entity_name,COALESCE(path,''),key"`
- `meta_delete` → DELETE com `.eq("path", full_path).eq("key", key)` (exato) OU `.like("path", f"{full_path}/%")` (recursivo)
- `meta_list` → SELECT com `.like("path", f"{full_path}%")` para prefix matching

---

## P7 — Migration Pattern (DDL seguro)

**Fonte:** `20260619000000_shared_business_memory.sql`

Toda migration:
1. `BEGIN;`
2. Operações dentro de `IF NOT EXISTS` / `DROP IF EXISTS`
3. Índices, triggers, RLS policies, comments
4. `COMMIT;`

**Aplicação para T4.2.1:** A migration `20260619000002_shared_memory_path.sql` segue este padrão, com cuidado extra para DROP + recriação da UNIQUE constraint.

---

## Resumo

| Padrão | Onde se aplica | Subtarefa |
|--------|---------------|-----------|
| P1 — @register_module | __init__.py, memory_module.py | T4.2.3 |
| P2 — Logic + MCP wrapper | memory_module.py | T4.2.2, T4.2.3 |
| P3 — Parameter order | memory_module.py | T4.2.2 |
| P4 — Entity validation | memory_module.py (reuso) | T4.2.2 |
| P5 — Path validation | memory_module.py (novo) | T4.2.2 |
| P6 — Supabase queries | memory_module.py | T4.2.2 |
| P7 — Migration DDL | migration SQL | T4.2.1 |
