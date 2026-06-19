# Repo Index — Issue #32: Política de Retenção e Prune

> Catalog of all files relevant to the retention/prune policy design.
> Generated: 2026-06-19 by factory-planner (t_ac9a439c)

## Architecture Layers (top → bottom)

```
docs/
├── llm_wiki/SHARED_MEMORY_DESIGN.md   ⬜ NÃO EXISTE (target para T4.4)
├── roadmap/blu-intelligent-memory.md   ✅ Lido — Fase 2.5 define prune diário
└── system_reference/TOOL_INVENTORY.md  ✅ Lido — tools SBM registradas

supabase/migrations/
├── proposed/20260619000000_shared_business_memory.sql     ⚠️ PROPOSED (não applied)
├── proposed/20260619000001_shared_memory_links.sql        ⚠️ PROPOSED
└── proposed/20260620000000_shared_memory_lifecycle.sql    ⬜ A CRIAR

services/
├── agent_api/src/agent_api/core/routine_functions.py      ✅ Lido — memory.write_dimension_state
└── tool_pool_api/src/tool_pool_api/server/tool_modules/
    └── memory_module.py                                    ✅ Lido — tools SBM existentes
```

## Files Detailed

### 1. Migration Base: 20260619000000_shared_business_memory.sql
**Status:** proposed/ (NOT applied — tabela não existe em produção)
**Schema atual:** id, client_id, entity_type, entity_name, key, value, source, confidence, metadata, created_at, updated_at
**Faltando:** expires_at, curated, archived_at
**Implicação:** Como a migration ainda não foi aplicada, podemos adicionar as colunas lifecycle DIRETAMENTE na migration base em vez de criar ALTER TABLE separado. Simplifica o deploy.

### 2. Migration Links: 20260619000001_shared_memory_links.sql
**Status:** proposed/ (NOT applied)
**FKs relevantes:** source_memory_id / target_memory_id → ON DELETE SET NULL
**Implicação:** Hard-delete de registros SBM não quebra integridade referencial. Links ficam órfãos (NULL) e podem ser limpados depois. R3 é risco baixo.

### 3. routine_functions.py
**Função existente:** `memory.write_dimension_state` — escreve em `dimension_state`, NÃO em shared_business_memory.
**Padrão de registro:** @register("namespace.function_name") com inputs/outputs declarativos.
**Padrão de acesso DB:** `get_supabase_client(use_service_role=True)` → `db.table().rpc()` ou `.upsert()`
**Função a criar:** `memory.prune_expired_shared_memory`

### 4. memory_module.py (tool_pool_api)
**Tools existentes:** shared_memory_list, shared_memory_link, shared_memory_unlink, shared_memory_get_links
**Padrão:** @register_module → register_tools(mcp) → @mcp.tool + @mcp_inject_client_id
**Tools a criar:** shared_memory_restore_archived, shared_memory_list_archived (se soft-delete)
**Validação:** _VALID_ENTITY_TYPES = frozenset({"skill", "client", "contact", "supplier", "user"})

### 5. TOOL_INVENTORY.md
**Tools SBM listadas:** shared_memory_list, shared_memory_link, shared_memory_unlink, shared_memory_get_links
**Categoria:** CUSTOM / SME / memoria/compartilhada
**Observação:** shared_memory_read e shared_memory_write NÃO aparecem no inventário atual (referenciadas em issues mas não registradas).

### 6. blu-intelligent-memory.md (Roadmap)
**Fase 2.5 — Expiração automática:** "Job periódico (diário, 03h) que deleta registros com expires_at < now() e curated=false. Simples, via Supabase cron ou rotina do Routine Engine."
**Fase 4 — Enriquecimento do Grafo:** SBM → LightRAG semanal. Depende de curated=true.

## Dependências Cruzadas
```
#37 (backup) ──▶ #32 (prune) ──▶ #35 (versionamento)
    02:00           03:00           04:00
```
