# patterns.md — Design Patterns extraídos do código

> Issue #32 — T4.4: Política de retenção e prune da shared memory
> Planner: factory-planner | Date: 2026-06-19

---

## Pattern 1: MCP Tool Registration (memory_module.py)

**Estrutura:**
```python
@mcp.tool(name="shared_memory_xxx", description="...")
@mcp_inject_client_id
async def shared_memory_xxx(ctx, ..., client_id=None) -> dict:
    # validação no tool-level
    # delega para _shared_memory_xxx_logic()
```

**Como T4.4c deve seguir:** Adicionar parâmetro `ttl_tier: str | None = None` a:
- `shared_memory_upsert` (linha ~862)
- `shared_memory_write` (linha ~946)
- Respectivas `_xxx_logic()` functions

**Pitfall:** Cada tool tem validação duplicada — não consolidar em helper único.

---

## Pattern 2: Migration em proposed/ — cascata de ALTER

**Estado atual:**
```
20260619000000: CREATE TABLE + entity_type IN (skill, client, contact, supplier, user)
20260619000003: ALTER TABLE → entity_type IN (... + agent_result, agent_metadata, routine)
```

**Problema:** Se T4.4a incorpora lifecycle columns na migration base, o ALTER da #21 quebra (a constraint já foi redefinida). Ou a nova migration base precisa incluir agent_result/agent_metadata/routine desde o início.

**Padrão correto:** Consolidar todas as pending changes na migration base antes de promover para applied/.

---

## Pattern 3: Soft-delete em 2 fases (proposto)

```
INSERT → archived=false, soft_delete_at=now()+TTL, hard_delete_at=soft_delete_at+90d
  ↓ (TTL expira)
soft-delete: UPDATE archived=true WHERE soft_delete_at <= now()
  ↓ (90 dias após soft-delete)
hard-delete: DELETE WHERE hard_delete_at <= now()
  ↓
Registro removido fisicamente
```

**Referência no código:** Nenhuma — não implementado. Pattern extraído do plan.intake.json.

---

## Pattern 4: Volume limit com trigger BEFORE INSERT

```sql
CREATE TRIGGER trg_sbm_volume_limit
BEFORE INSERT ON shared_business_memory
FOR EACH ROW
EXECUTE FUNCTION check_volume_limit();
```

A função conta `SELECT count(*) WHERE client_id=NEW.client_id AND entity_type=NEW.entity_type AND entity_name=NEW.entity_name AND archived=false AND soft_delete_at IS NULL`.

**Exceção:** Se `NEW.source='curated'` — mas **'curated' não existe no CHECK constraint atual.** Ver resolution.md.

---

## Pattern 5: Routine Engine (agent_api, não serviço separado)

O engine de rotinas vive em `services/agent_api/src/agent_api/core/routines.py`, NÃO em `services/routine_engine/`.

**Entry points:**
- `routine_functions.py` — funções registradas (get_cash_position, etc.)
- `routine_artifacts.py` — artifact steps
- `routine_triggers.py` — triggers (pg_cron → dispatch)
- `routines_router.py` — API endpoints

**T4.4d precisa:** Registrar `prune_shared_memory` como routine function em `routine_functions.py`, ou como step na tabela `cross_agent_routines`. NÃO criar diretório `services/routine_engine/`.

---

## Pattern 6: Source validation — gap entre plan e schema

| Source value | Na migration CHECK? | No plan T4.4c? |
|-------------|---------------------|-----------------|
| manual | ✅ | Default (manual) |
| memory_agent | ✅ | Default (memory_agent_lo) |
| specialist | ✅ | Default (specialist) |
| migration | ✅ | Default (migration) |
| system | ✅ | — |
| **curated** | ❌ NÃO EXISTE | Referenciado como tier e como source |

**Correção necessária:** Adicionar 'curated' ao CHECK constraint de source, OU usar `ttl_tier` como o discriminante (recomendado: tier, não source).

---

## Pattern 7: Checklist migration — RLS preservado

Toda migration que toca `shared_business_memory` deve:
1. Preservar RLS policies existentes
2. Não dropar índices sem recriar
3. Usar SECURITY DEFINER para funções que bypass RLS (service_role)
4. Incluir comentários em português (padrão do projeto)
5. Rodar em transação (BEGIN/COMMIT)

**T4.4a precisa garantir:** Adicionar colunas sem quebrar o RLS `client_own_shared_memory`. Índices parciais WHERE archived=true não devem conflitar com RLS.
