# resolution.md — Conflict Detection & Design Decisions (#57)

> Resolução de conflitos e decisões de design para o code review #57.
> Gerado por factory-planner, 2026-06-19.

## 1. Conflict Detection

### 1.1 Dependency Status (R3)

**Risco:** Review depende de #17-#37 completos.

**Status das dependências:**

| Phase | Issues | Status | Blocking? |
|-------|--------|--------|-----------|
| Fase 1 | #17-#20 | Implementado (pre/post-flight, handoff, integrity) | Não |
| Fase 2 | #21-#24 | Implementado (routine checkpoint, snapshots, intake #23-#24) | Não |
| Fase 3 | #25-#28 | Parcial (vector store pipeline — 3 tasks blocked, plan done) | Não-bloqueante |
| Fase 4 | #29-#32 | Planning (3 planners active, 1 intake active) | Não-bloqueante |

**Resolução:** Este é o **planejamento** (#57), não a execução. O plano está documentado e as tasks de execução serão criadas com `parents` linkados ao completion signal de #17-#37. O risco R3 é mitigado por design: as tasks filhas só promovem a `ready` quando as dependências estiverem `done`.

### 1.2 Missing Reference Docs

**Conflito:** HERMES.md lista `CODE_MAP.md`, `FRONTEND.md`, `DATABASE_SCHEMA.md`, `DATABASE_FUNCTIONS_MAP.md`, `PRODUCT_CONCEPT.md`, `MONDAY_API_REFERENCE.md`, `ONBOARDING.md`, `ONBOARDING_CONTEXT_MAP.md`, `TOOL_REGISTRY_REPORT.md` em `docs/system_reference/` — mas apenas 7 arquivos existem no disco.

**Resolução:** Esses docs ausentes são gaps de documentação, não do code review. O review deve:
- Anotar a ausência como um finding P2 (documentation gap)
- Usar o que existe (AGENT_SYSTEM, SKILLS_SYSTEM, ROUTINES_SYSTEM, TOOL_INVENTORY, TASK_PLAYBOOKS, FEATURE_MAP) como baseline
- Não tentar preencher esses gaps durante o review (fora de escopo)

### 1.3 88 Duplicate Files (pygount)

**Conflito:** pygount detectou 88 arquivos com conteúdo idêntico.

**Resolução:** T57.3 (code duplication) deve investigar esses 88 casos especificamente:
- Verificar se são duplicação intencional (ex: stubs, fixtures, templates) ou acidental
- Identificar candidatos a extração para shared libs
- Priorizar por frequência de duplicação e impacto de manutenção

## 2. Design Questions (resolved)

### DQ1: Incluir build/ e node_modules/?

**Resposta:** ❌ Excluir. Foco em source code apenas. build/, node_modules/, dist/, __pycache__/, .next/ já foram excluídos do scan.

### DQ2: Timeline de remediação

**Resposta:** Default adotado:
- **P0** = Imediato (security, data loss, blocking bugs)
- **P1** = Next sprint (performance, maintainability, tech debt crítico)
- **P2** = Backlog (style, minor inconsistency, nice-to-have)

### DQ3: Serviços/libs prioritários

**Resposta:** Weighted by criticality:
- **Tier 1 (crítico):** agent_api, blu_agent_framework, blu_supabase_client, blu_models, blu_context_service
- **Tier 2 (alto):** tool_pool_api, blu_prompt_management, blu_llm_service, blu_rag_factory
- **Tier 3 (médio):** blu_auth, blu_hitl_service, blu_data_connectors, blu_sql_factory
- **Tier 4 (baixo):** Demais libs, apps/blu_v3 (frontend), packages/

Tier 1 services get stricter thresholds: P1 findings in Tier 1 are escalated to P0.

## 3. Task Decomposition Rationale

As 8 subtarefas do plan.json (T57.1–T57.8) foram decompostas seguindo a estrutura:

```
T57.1 (inventory) — 1 task factory-coder — base para todas as demais
    ↓
T57.2–T57.7 (6 revisões paralelas) — 6 tasks factory-coder — independentes entre si
    ↓
T57.8 (consolidation) — 1 task factory-coder — depende de T57.1+T57.2+T57.3+T57.4+T57.5+T57.6+T57.7
```

**Paralelismo:** T57.2 a T57.7 podem rodar em paralelo após T57.1 completar.
**Fan-in:** T57.8 consolida todas as 7 tasks anteriores.

## 4. Artifacts Generated

| Artifact | Path | Purpose |
|----------|------|---------|
| repo-index.md | `docs/planning/issue-57/repo-index.md` | Service catalog, language breakdown, dependency status |
| patterns.md | `docs/planning/issue-57/patterns.md` | Expected code conventions (Python, TS, SQL, cross-cutting) |
| resolution.md | `docs/planning/issue-57/resolution.md` | Conflict detection, design decisions, decomposition rationale |

## 5. Risk Mitigation Summary

| Risk | Mitigation | Status |
|------|-----------|--------|
| R1: Codebase size | Automated tooling (grep, linters, jscpd) + sampling | Accepted — tasks use tooling |
| R2: Intentional deviations | Flag as "review needed", not "violation" | Built into review template |
| R3: Dependency on #17-#37 | Parent links gating execution | Implemented |
| R4: Mixed ecosystems | Standardized finding schema | Schema defined in T57.8 spec |
