# Resolution — Issue #31 / T4.3 (knowledge_graph_summary update)

> Gerado por factory-planner em 2026-06-19

## 1. Design Decisions (validadas/refinadas do intake)

### DD-01: Schema em AvailableTools ✅ CONFIRMADA
Adicionar `knowledge_graph_summary: KnowledgeGraphSummary | None = None` ao `AvailableTools` (linha 278 de context_schemas.py). Retrocompatível (campo opcional).

### DD-02: Versionamento do summary ✅ CONFIRMADA
`KnowledgeGraphSummary.version: int = 1`. Campo no próprio summary (não no AvailableTools). Permite migração futura de formato.

### DD-03: Módulo knowledge_graph_sync.py ✅ CONFIRMADA — refino
- Internal tool via `@register_module` (padrão do codebase).
- Função: `update_knowledge_graph_summary(client_id: UUID, summary: dict) -> bool`.
- Registrada no `AVAILABLE_MODULES` como "knowledge_graph" e importada em `register_all_tools`.
- NÃO exposta como MCP tool (chamada interna pelo job T4.1).

### DD-04: Payload structure ✅ CONFIRMADA
```python
class EntitySummary(BaseModel):
    name: str
    type: str
    degree: int

class KnowledgeGraphSummary(BaseModel):
    total_documents: int = 0
    total_entities: int = 0
    top_entities: list[EntitySummary] = Field(default_factory=list, max_length=10)
    last_sync: str | None = None  # ISO timestamp
    version: int = 1
```

### DD-05: Upsert JSONB em clientes_blu.available_tools ✅ CONFIRMADA
Ler → merge (preservar tier, enabled_tool_names, etc.) → escrever. Cache invalidado após.

### DD-06: Cache invalidation ✅ CONFIRMADA
`clear_context_cache(client_id)` após upsert.

---

## 2. Discrepância encontrada: _DOMAIN_SECTIONS

**O plano intake afirma:** "available_tools já é incluído nas seções permitidas para domínios 'analytics', 'data', 'sql', 'rag', 'documents', 'knowledge', 'config', 'settings'"

**Realidade (código em context_service.py:30-43):**
- `rag`, `documents`, `knowledge` **NÃO** incluem `available_tools`.
- Apenas `analytics`, `data`, `sql`, `config`, `settings` incluem.

**Decisão planner:** T4.3c deve:
1. Adicionar `available_tools` a `rag` e `documents` (domínios que usarão `knowledge_graph_summary`)
2. Manter `knowledge` como está (focado em company_profile/policies/brand_voice)
3. OU: Manter domain projection inalterado e expor `get_knowledge_graph_summary()` como helper separado

**Recomendação:** Opção 3 (helper separado) — evita mudança de comportamento em _DOMAIN_SECTIONS que afeta outras sections do available_tools. O `get_knowledge_graph_summary()` é um accessor específico, não uma mudança no projection.

---

## 3. Conflicts Analysis

| Issue relacionada | Branch | Arquivos em conflito | Severidade |
|---|---|---|---|
| #29 (handoffs dir) | `phase-4/issue-29-dir-handoffs-estruturado` | Nenhum | ✅ Clean |
| #30 (meta/ dir) | `phase-4/issue-30-diretorio-meta-dados-operacionais` | Nenhum | ✅ Clean |
| #32 (retenção/prune) | `phase-0/issue-32-politica-de-retencao-e-prune` | Nenhum | ✅ Clean |

**Conclusão:** Zero conflitos de arquivo com branches relacionadas. T4.3 pode prosseguir sem coordenação.

---

## 4. Risks & Mitigations (validados)

| ID | Risco | Mitigação | Status |
|----|-------|-----------|--------|
| R1 | LightRAG não existe → summary fica None | Campo opcional (DD-02). Fallback: "grafo não disponível" | ✅ Mitigado |
| R2 | Race condition no JSONB | version field (optimistic locking). Single-writer (cron semanal T4.1) | ✅ Mitigado |
| R3 | RLS leak entre tenants | RLS client_id no ContextService. Testar em integração | ⚠️ Precisa teste |
| R4 | Schema evolution | version field no summary. Migração on-read | ✅ Mitigado |

---

## 5. Pipeline de Delivery (sequenciamento)

```
T4.3a (schema) ──┬──> T4.3b (sync module) ──┬──> T4.3c (context helper) ──> T4.3e (testes)
                 │                           │
                 └──> (paralelo com T4.3b)   └──> T4.3d (docstring/integration point)
```

**Tasks para factory-coder (sequenciais com paralelismo):**

| Order | Card | Depende de | Estimativa |
|-------|------|------------|------------|
| 1 | T4.3a: Schema KnowledgeGraphSummary + AvailableTools | — | Pequeno (1 arquivo, ~40 linhas) |
| 2 | T4.3b: Módulo knowledge_graph_sync.py | T4.3a | Médio (2 arquivos, ~120 linhas) |
| 3 | T4.3c: Context Service helper + domain review | T4.3a, T4.3b | Pequeno (1 arquivo, ~40 linhas) |
| 4 | T4.3d: Docstring com payload exemplo T4.1 | T4.3b | Trivial (docstring, ~15 linhas) |
| 5 | T4.3e: Testes unitários (3 arquivos) | T4.3a, T4.3b, T4.3c | Médio (3 arquivos, ~200 linhas) |

**Otimização:** T4.3c e T4.3d podem rodar em paralelo após T4.3b.

---

## 6. Questões abertas (do intake)

| ID | Questão | Status após scan |
|----|---------|-----------------|
| DQ1 | Métricas de qualidade no summary? | **Adiado** — adicionar quando T4.1 existir e gerar dados reais |
| DQ2 | Quais specialists recebem o summary? | **Respondido**: `rag`, `documents` via helper `get_knowledge_graph_summary()`. Outros sob demanda. |
| DQ3 | Stale detection (`stale_after_hours`)? | **Adiado** — adicionar `stale_after_hours` ao schema na V2 quando T4.1 rodar periodicamente |

---

## 7. Decisões de implementação (planner)

1. **Helper separado, não domain projection** — `get_knowledge_graph_summary(client_id)` é adicionado ao ContextService como accessor tipado. `_DOMAIN_SECTIONS` não é alterado (evita side effects em outras sections do `available_tools`).

2. **1 card monolítico por subtarefa** — 5 cards para factory-coder, sequenciados com paralelismo T4.3c ∥ T4.3d.

3. **Testes em 3 arquivos separados** — cada lib/service com seus próprios testes. Mock Supabase (padrão do codebase).

4. **knowledge_graph_sync como internal tool** — registrada no AVAILABLE_MODULES mas NÃO exposta via MCP (chamada direta pelo job T4.1).

5. **Structure logging obrigatório** — `logger.info(f"knowledge_graph_summary updated: client={client_id}, entities={n}, docs={m}, sync={ts}")`.

---

## 8. Branch & Commit

- Branch: `phase-0/issue-31-eventos-trigger-handoffs`
- Próximo passo: factory-coder implementa T4.3a (schema) → T4.3b (sync) → T4.3c+T4.3d (paralelo) → T4.3e (testes)
