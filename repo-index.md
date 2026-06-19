# Repo Index — T4.2: Diretório meta/ para dados operacionais

> Issue: [#30](https://github.com/CidLucas/repo_platform/issues/30)
> Branch: phase-0/issue-30-meta-dir
> Gerado: 2026-06-19 | factory-planner

## Arquivos a Modificar (5)

### 1. `supabase/migrations/proposed/20260619000002_shared_memory_path.sql` [NOVO]
**Tipo:** Migration SQL
**Subtarefa:** T4.2.1
**Papel:** Adiciona coluna `path` à tabela `shared_business_memory`, recria UNIQUE constraint com COALESCE(path, ''), adiciona CHECK constraint de validação, cria índice `idx_sbm_path` para queries por path prefix.

### 2. `services/tool_pool_api/src/tool_pool_api/server/tool_modules/memory_module.py` [MODIFICAR]
**Tipo:** Código Python (606 linhas atuais)
**Subtarefas:** T4.2.2, T4.2.3
**Papel:** Adicionar 4 funções `_logic` (meta_read, meta_write, meta_delete, meta_list) + 4 wrappers MCP com `@mcp.tool` e `@mcp_inject_client_id` decorators. Registrar no `register_tools()`.
**Padrões existentes:** `@register_module` decorator, `_logic` functions, `_TABLE`/`_LINKS_TABLE` constants, `_validate_entity_type()`, `get_supabase_client()`.
**Ferramentas existentes (4):** shared_memory_list, shared_memory_link, shared_memory_unlink, shared_memory_get_links.

### 3. `services/tool_pool_api/src/tool_pool_api/server/tool_modules/__init__.py` [MODIFICAR]
**Tipo:** Código Python (332 linhas)
**Subtarefa:** T4.2.3
**Papel:** Atualizar `AVAILABLE_MODULES["memory"]["tools"]` — adicionar `meta_read`, `meta_write`, `meta_delete`, `meta_list`.
**Entrada atual (linhas 322–331):**
```python
"memory": {
    "description": "Shared Business Memory — entity listing, knowledge retrieval, and semantic linking",
    "tools": [
        "shared_memory_list",
        "shared_memory_link",
        "shared_memory_unlink",
        "shared_memory_get_links",
    ],
    "requires_auth": True,
},
```

### 4. `docs/llm_wiki/SHARED_MEMORY_DESIGN.md` [CRIAR seção T4.2]
**Tipo:** Documentação (LLM wiki)
**Subtarefa:** T4.2.4
**Papel:** Documentar T4.2 — problem statement, schema com coluna path, tool interface (4 tools), design decisions, exemplos de uso.
**Status atual:** ARQUIVO NÃO EXISTE — referência fantasma. `memory_module.py:9` referencia `"Design doc: docs/llm_wiki/SHARED_MEMORY_DESIGN.md (Fase 0 / T0.4)"` mas o arquivo nunca foi criado.
**Draft existente:** `docs/llm_wiki/SHARED_MEMORY_DESIGN_T4.2_draft.md` (233 linhas) — conteúdo de referência para T4.2.

### 5. `docs/system_reference/TOOL_INVENTORY.md` [MODIFICAR]
**Tipo:** Documentação (inventário de tools)
**Subtarefa:** T4.2.5
**Papel:** Adicionar 4 entries na seção 1.1 BUILTIN_TOOLS: `meta_read`, `meta_write`, `meta_delete`, `meta_list` como CUSTOM/SME em `memoria/compartilhada`.
**Entradas atuais (linhas 60–63):** shared_memory_list, shared_memory_link, shared_memory_unlink, shared_memory_get_links.

## Arquivos de Referência (não modificar)

| Arquivo | Papel |
|---------|-------|
| `supabase/migrations/proposed/20260619000000_shared_business_memory.sql` | Schema base — tabela `shared_business_memory` (111 linhas). Define a estrutura atual sem `path`. |
| `supabase/migrations/proposed/20260619000001_shared_memory_links.sql` | Tabela de links entre entidades. Independente de `path`. |
| `docs/llm_wiki/SHARED_MEMORY_DESIGN_T4.2_draft.md` | Draft de design para T4.2 (233 linhas) — especificação completa da feature. |
| `docs/roadmap/blu-intelligent-memory.md` | Roadmap original (Fase 4 = Graph Enrichment, diferente da Fase 4 atual). |
| `plan.json` | Intake plan com 5 subtarefas, 4 design decisions, 3 riscos, 4 design questions. |

## Dependências

```
T4.2.1 (Migration) → T4.2.2 (Core logic) → T4.2.3 (Registration)
                                           → T4.2.4 (Documentation)
                        T4.2.3 (Registration) → T4.2.5 (Tool inventory)
```

## Migrations Existentes (evitar conflito de numeração)

| Migration | Status |
|-----------|--------|
| `20260619000000_shared_business_memory.sql` | proposed — tabela base |
| `20260619000001_shared_memory_links.sql` | proposed — links table |
| `20260619000002` | **disponível** — T4.2 usará este número |
