# Resolution — T4.2: Diretório meta/ para dados operacionais

> Issue: [#30](https://github.com/CidLucas/repo_platform/issues/30)
> Branch: phase-0/issue-30-meta-dir
> Gerado: 2026-06-19 | factory-planner
> Base: plan.json (intake) + repo-scan + LLM-wiki

---

## Design Decisions Resolvidas (6)

### DD-01 — Coluna `path` na tabela existente vs. tabela separada
**Decisão:** Coluna `path` opcional (nullable text) na tabela `shared_business_memory`.
**Rationale:** Mantém tudo em uma tabela para queries unificadas. NULL path = entity-scoped memory. Non-NULL path = operational data. Mais simples que duas tabelas.

### DD-02 — Path validation: prefixo `meta/` automático
**Decisão:** Tools prefixam `meta/` automaticamente. Agente nunca passa o prefixo.
**Rationale:** Previne prefixos inconsistentes. Simplifica prompts dos agentes.

### DD-03 — Ferramentas específicas vs. generalizar tools existentes
**Decisão:** 4 novas tools (`meta_read`, `meta_write`, `meta_delete`, `meta_list`) em vez de modificar `shared_memory_*`.
**Rationale:** Separação clara de responsabilidades. Retrocompatibilidade total.

### DD-04 — Path como namespace adicional, não substituição de entity
**Decisão:** Toda entrada meta mantém `entity_type` e `entity_name` (default: `"client"`).
**Rationale:** Consistência com schema existente. RLS policies já usam `client_id`.

### DD-05 — `meta_delete` recursivo com flag explícita
**Decisão:** `meta_delete` suporta deleção recursiva mas apenas com `recursive=True` explícito.
**Rationale:** Previne deleção acidental de subtrees.

### DD-06 — `meta_list` com navegação estilo diretório
**Decisão:** Retorna `entries` (chaves no path atual) + `sub_paths` (subdiretórios com contagem).
**Rationale:** Navegação progressiva. Evita queries massivas.

---

## Conflitos Detectados (4)

### CF-01 — UNIQUE constraint change em tabela com dados
**Resolução:** Migration em 3 passos: DROP constraint → ADD COLUMN path → CREATE UNIQUE INDEX com COALESCE.
**Severidade:** Média.

### CF-02 — SHARED_MEMORY_DESIGN.md é referência fantasma
**Resolução:** T4.2.4 deve CRIAR o arquivo (não apenas adicionar seção). Draft existente fornece conteúdo base.
**Severidade:** Baixa.

### CF-03 — Branch contém artifacts de #32
**Resolução:** Reset para commit do intake (`66374067`) já executado. Branch agora contém apenas arquivos do intake + artifacts T4.2.
**Severidade:** Alta — resolvido.

### CF-04 — Migração `20260619000002` disponível
**Resolução:** Usar `20260619000002_shared_memory_path.sql`. Slot livre.
**Severidade:** Nenhuma.

---

## Unidades de Entrega (3)

| Unidade | Subtarefas | Descrição |
|---------|-----------|-----------|
| **DU-1: Schema** | T4.2.1 | Migration SQL — coluna path + constraints + índices |
| **DU-2: Tools** | T4.2.2, T4.2.3 | 4 tools meta_* + registro em __init__.py |
| **DU-3: Docs** | T4.2.4, T4.2.5 | SHARED_MEMORY_DESIGN.md + TOOL_INVENTORY.md |

**Ordem:** DU-1 → DU-2 → DU-3 (DU-2.4 pode rodar em paralelo com DU-2.2/2.3).

---

## Questões em Aberto (4)

### QA-01 — `shared_memory_list` deve ignorar entradas com path?
**Recomendação:** Adicionar filtro `.is_("path", None)` em shared_memory_list para separar entity-scoped de meta/.
**Pendente:** Confirmação humana.

### QA-02 — Nomes das tools: `meta_*` vs `shared_memory_meta_*`?
**Recomendação:** Manter `meta_read`, `meta_write`, `meta_delete`, `meta_list` — mais curtos e semanticamente distintos.
**Pendente:** Confirmação humana.

### QA-03 — `meta_list` deve suportar `recursive=True`?
**Recomendação:** Implementar como opção. Default `False`.
**Pendente:** Incluir na v1 ou iterar depois?

### QA-04 — `meta_write`: UPSERT ou INSERT-only?
**Recomendação:** UPSERT — idempotente por natureza. `on_conflict="client_id,entity_type,entity_name,COALESCE(path,''),key"`.

---

## Handoff para factory-coder

### Sequência
```
T4.2.1 (Migration) → T4.2.2 (Core logic) → T4.2.3 (Registration)
                                           → T4.2.4 (Documentation)
                        T4.2.3 → T4.2.5 (Tool inventory)
```

### Pontos críticos
1. UNIQUE constraint usa `CREATE UNIQUE INDEX` com `COALESCE(path, '')` — NÃO `ADD CONSTRAINT UNIQUE`
2. `_validate_meta_path()` sempre adiciona prefixo `meta/`
3. `meta_list` usa `LIKE 'prefix%'` + pós-processamento para sub_paths
4. SHARED_MEMORY_DESIGN.md precisa ser CRIADO do zero
5. Branch resetada para intake commit `66374067`
