# repo-index.md — Planning artifacts for Issue #32 (T4.4)

> Generated: 2026-06-19 | Planner: factory-planner | Branch: phase-0/issue-32-politica-de-retencao-e-prune

## Arquivos relevantes escaneados

| Arquivo | Papel | Status |
|---------|-------|--------|
| `docs/llm_wiki/INTAKE_PLAN_32_politica_de_retencao_e_prune.json` | Plano de intake (7 subtarefas, 7 DDs) | Referência |
| `docs/llm_wiki/SHARED_MEMORY_DESIGN.md` | Design doc da shared memory (T2.2, T4.4 referencia) | Lido até T2.2; T4.4 não detalhado |
| `docs/llm_wiki/TOOL_INVENTORY.md` | Catálogo de 69 tools — shared_memory_* parcialmente listado | DQ-04: NÃO é YAML |
| `supabase/migrations/proposed/20260619000000_shared_business_memory.sql` | Migration base da tabela (NÃO aplicada) | Em proposed/ ⚠ |
| `supabase/migrations/proposed/20260619000001_shared_memory_links.sql` | Migration links table (NÃO aplicada) | Em proposed/ |
| `supabase/migrations/proposed/20260619000002_shared_memory_integrity.sql` | Trigger validação (NÃO aplicada) | Em proposed/ |
| `supabase/migrations/proposed/20260619000003_routine_checkpoint_rpc.sql` | ALTER entity_type + RPC checkpoint (NÃO aplicada) | Modifica base migration ⚠ |
| `services/tool_pool_api/src/tool_pool_api/server/tool_modules/memory_module.py` | 1262 linhas — 7 tools shared_memory_* registradas | CORE — T4.4c edita aqui |
| `services/agent_api/src/agent_api/core/routines.py` | Engine de rotinas (funções + artifact steps) | T4.4d usa ⚠ (não é serviço separado) |
| `services/agent_api/src/agent_api/api/routines_router.py` | API de rotinas — execução e catálogo | T4.4d refere indiretamente |

## Arquivos que NÃO existem (referenciados pelo plan)

| Referência no Plan | Realidade |
|-------------------|-----------|
| `configs/tool_inventory.yaml` | **Não existe.** O registry é código Python (registry.py) e a wiki é `TOOL_INVENTORY.md` |
| `services/routine_engine/src/routines/prune_shared_memory.py` | **Não existe.** O engine está em `agent_api/core/routines.py`. Não há subdiretório `services/routine_engine/` |

## Related issues scan

| Issue | Título | Estado | Conflito com #32 |
|-------|--------|--------|-----------------|
| #21 | Routine checkpoint em shared memory | CLOSED (migration em proposed/) | `entity_type` CHECK ALTER — ver resolution.md |
| #26 | shared_memory_search (T3.2) | Plan em andamento | Edita memory_module.py — merge conflict risk |
| #29 | Diretório handoffs/ (T4.1) | Plan em andamento | Baixo — handoffs separado de prune |
| #30 | Diretório meta/ (T4.2) | Plan em andamento | Edita memory_module.py — ALTA sobreposição |
| #31 | Eventos trigger handoffs (T4.3) | Plan em andamento | Médio — mesmo domínio Fase 4 |
| #33 | Página visualização memória (F5) | Backlog | Depende de T4.4 (status archived) |
| #34 | Permissões escrita SBM (F5) | Backlog | Depende de ttl_tier para regras |
