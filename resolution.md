# Resolution — T4.2: Diretório meta/ para dados operacionais

> Issue: [#30](https://github.com/CidLucas/repo_platform/issues/30)
> Branch: phase-0/issue-30-meta-dir
> Gerado: 2026-06-19 | factory-planner
> Base: plan.json (intake) + repo-scan + LLM-wiki

---

## Design Decisions Resolvidas (6)

### DD-01 — Coluna `path` na tabela existente vs. tabela separada
**Decisão:** Coluna `path` opcional (nullable text) na tabela `shared_business_memory`.
**Rationale:** Mantém tudo em uma tabela para queries unificadas. NULL path = entity-scoped memory (modelo atual). Non-NULL path = operational data (meta/). Mais simples que gerenciar duas tabelas com schemas quase idênticos.
**Consequências:** Migration precisa lidar com rows existentes (NULL path). UNIQUE constraint precisa ser recriada com `COALESCE(path, '')`.

### DD-02 — Path validation: prefixo `meta/` automático
**Decisão:** Tools prefixam `meta/` automaticamente. Agente nunca passa o prefixo — apenas o sub-path significativo (ex: `"financeiro/receita_bruta"`).
**Rationale:** Previne prefixos inconsistentes. Simplifica prompts dos agentes. Garante que dados operacionais fiquem sempre sob `meta/`.
**Consequências:** `_validate_meta_path()` sempre adiciona `meta/`. CHECK constraint no SQL aceita qualquer path válido (não apenas `meta/`), pois a validação de prefixo é application-level.

### DD-03 — Ferramentas específicas vs. generalizar tools existentes
**Decisão:** Criar 4 novas tools (`meta_read`, `meta_write`, `meta_delete`, `meta_list`) em vez de adicionar parâmetro `path` nas tools `shared_memory_*`.
**Rationale:** Separação clara de responsabilidades. Tools `shared_memory_*` (T0.4/T0.5) operam no modelo plano (entity_type, entity_name, key). Tools `meta_*` (T4.2) operam no namespace hierárquico `meta/`. Ambas compartilham a mesma tabela física.
**Consequências:** 8 tools totais no módulo memory (4 existentes + 4 novas). Mantém retrocompatibilidade.

### DD-04 — Path como namespace adicional, não como substituição de entity
**Decisão:** Toda entrada meta mantém `entity_type` e `entity_name` (default: `"client"` + primeiro match). `path` é namespace adicional, não substituto.
**Rationale:** Consistência com o schema existente. RLS policies já usam `client_id`. Entity permite escopo multi-tenant dentro do mesmo path.
**Consequências:** Meta tools aceitam `entity_type`/`entity_name` opcionais com defaults.

### DD-05 — `meta_delete` recursivo com flag explícita
**Decisão:** `meta_delete` suporta deleção recursiva de subtree, mas apenas com `recursive=True` explícito.
**Rationale:** Previne deleção acidental de subtrees. Agente deve opt-in explicitamente.
**Consequências:** Comportamento padrão (`recursive=False`) deleta apenas entrada exata por `(path, key)`.

### DD-06 — `meta_list` com navegação estilo diretório
**Decisão:** `meta_list` retorna tanto `entries` (chaves no path atual) quanto `sub_paths` (subdiretórios com contagem), similar a `ls` mostrando arquivos e diretórios.
**Rationale:** Permite navegação progressiva — agente vê estrutura antes de descer. Evita queries massivas.
**Consequências:** Query SQL usa `LIKE 'prefix%'` com pós-processamento para separar entries diretas de sub-paths.

---

## Conflitos Detectados (4)

### CF-01 — UNIQUE constraint change em tabela com dados
**Conflito:** A constraint `uq_shared_memory_entry` atual é `UNIQUE (client_id, entity_type, entity_name, key)`. A nova constraint precisa ser `UNIQUE (client_id, entity_type, entity_name, COALESCE(path, ''), key)`.
**Resolução:** Migration em 3 passos: (1) `DROP CONSTRAINT IF EXISTS uq_shared_memory_entry`, (2) `ALTER TABLE ADD COLUMN path`, (3) `CREATE UNIQUE INDEX uq_shared_memory_entry ON ... (client_id, entity_type, entity_name, COALESCE(path, ''), key)`. Usar `CREATE UNIQUE INDEX` em vez de `ADD CONSTRAINT UNIQUE` para suportar `COALESCE` na expressão.
**Severidade:** Média — requer testar em staging antes de aplicar em produção.

### CF-02 — SHARED_MEMORY_DESIGN.md é referência fantasma
**Conflito:** `memory_module.py:9` e `plan.json` referenciam `docs/llm_wiki/SHARED_MEMORY_DESIGN.md` que **não existe**. O diretório `docs/llm_wiki/` existe mas o arquivo nunca foi criado.
**Resolução:** A subtarefa T4.2.4 deve **criar** o arquivo (não apenas adicionar seção). O draft `SHARED_MEMORY_DESIGN_T4.2_draft.md` fornece conteúdo inicial para a seção T4.2. Estrutura sugerida: seções T0.x (fase 0 — completada), T4.1 (handoffs), **T4.2 (meta/)**, T4.3 (eventos), T4.4 (retenção).
**Severidade:** Baixa — T4.2.4 já contempla criação da seção.

### CF-03 — Branch `phase-0/issue-30-meta-dir` contém artifacts de #32
**Conflito:** O commit HEAD (`5fd1a577`) contém artifacts de planejamento da issue #32 (retenção/prune), não da #30. O commit original do intake (`66374067`) está acessível via git history.
**Resolução:** Fazer reset para o commit do intake (`66374067`) antes de commitar os artifacts de T4.2. Preserva o histórico original.
**Severidade:** Alta — deve ser corrigido neste planejamento.

### CF-04 — Migração `20260619000002` disponível mas naming consistente
**Conflito:** O slot `20260619000002` está livre na sequência de migrações. Nenhum conflito de numeração.
**Resolução:** Usar `20260619000002_shared_memory_path.sql` como nome da migration.
**Severidade:** Nenhuma — slot disponível.

---

## Unidades de Entrega (3)

| Unidade | Subtarefas | Descrição | Depende de |
|---------|-----------|-----------|------------|
| **DU-1: Schema** | T4.2.1 | Migration SQL — coluna path + constraints + índices | Nenhum |
| **DU-2: Tools** | T4.2.2, T4.2.3 | 4 tools meta_* + registro no __init__.py | DU-1 |
| **DU-3: Docs** | T4.2.4, T4.2.5 | SHARED_MEMORY_DESIGN.md (seção T4.2) + TOOL_INVENTORY.md | DU-2 |

**Ordem de implementação:** DU-1 → DU-2 → DU-3. DU-2.4 pode rodar em paralelo com DU-2.2/DU-2.3 após DU-2.2 concluir (pois precisa das assinaturas exatas das tools).

---

## Questões em Aberto (4)

### QA-01 — `shared_memory_list` deve ignorar entradas com path?
**Contexto:** A tool `shared_memory_list` atual agrupa por `entity_type`/`entity_name`. Entradas com `path` populado (Meta/) podem poluir essa listagem.
**Recomendação:** Adicionar filtro `.is_("path", None)` na query de `shared_memory_list` para que ela só retorne entradas entity-scoped. Entradas meta/ são acessíveis apenas via `meta_list`.
**Decisão pendente:** Humano deve confirmar se prefere separação estrita ou se `shared_memory_list` deve mostrar tudo.

### QA-02 — Nomes das tools: `meta_*` vs `shared_memory_meta_*`?
**Contexto:** As tools existentes usam prefixo `shared_memory_`. As novas tools T4.2 usam prefixo `meta_`.
**Recomendação:** Manter `meta_read`, `meta_write`, `meta_delete`, `meta_list` — mais curtos, mais fáceis para agentes, e semanticamente distintos de `shared_memory_*`.
**Decisão pendente:** Humano deve confirmar convenção de nomenclatura.

### QA-03 — `meta_list` deve suportar `recursive=True`?
**Contexto:** O design draft T4.2 especifica `meta_list` com `recursive` como parâmetro opcional. A DD-06 define navegação estilo diretório (não recursiva por padrão).
**Recomendação:** Implementar `recursive=True` como opção para agentes que precisam de dump completo. Default `False` para navegação progressiva.
**Decisão pendente:** Incluir `recursive` na v1 ou deixar para iteração futura?

### QA-04 — `meta_write` deve usar UPSERT ou INSERT-only?
**Contexto:** O design draft especifica "Idempotent — upserts on (client_id, entity_type, entity_name, path, key)".
**Recomendação:** UPSERT é o correto — permite que agentes escrevam sem verificar existência prévia. Mantém semântica de idempotência.
**Decisão:** UPSERT com `on_conflict="client_id,entity_type,entity_name,COALESCE(path,''),key"`.

---

## Handoff para factory-coder

### Sequência de implementação

```
T4.2.1 (Migration SQL)
  └─► T4.2.2 (Core logic — 4 _meta_*_logic functions)
        ├─► T4.2.3 (Registration — decorators + __init__.py)
        └─► T4.2.4 (Documentation — SHARED_MEMORY_DESIGN.md)
              └─► T4.2.5 (Tool inventory — TOOL_INVENTORY.md)
```

### Pontos de atenção para o coder

1. **UNIQUE constraint com COALESCE:** PostgreSQL trata NULLs como distintos em UNIQUE. Usar `CREATE UNIQUE INDEX ... ON (client_id, entity_type, entity_name, COALESCE(path, ''), key)` — não `ADD CONSTRAINT UNIQUE`.
2. **Path sempre prefixado:** `_validate_meta_path()` automaticamente adiciona `meta/`. O agente NUNCA passa o prefixo.
3. **`meta_list` com sub_paths:** Query SQL faz `LIKE 'prefix%'`, depois pós-processa para separar entries diretas (path == prefix) de sub-paths (path like prefix/...).
4. **SHARED_MEMORY_DESIGN.md NÃO EXISTE:** Precisa ser criado do zero. O draft `SHARED_MEMORY_DESIGN_T4.2_draft.md` serve de base.
5. **Branch precisa ser resetada:** HEAD atual tem artifacts de #32. Resetar para `66374067` antes de commitar.
