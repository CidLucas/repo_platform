# Resolution — Issue #24: Hook pós-ETL Onboarding Snapshot Inicial

> Branch: `phase-2/issue-24-post-etl-onboarding-snapshot`
> Fase 2, T2.4
> Gerado: 2026-06-19

## Resumo Executivo

Planejamento do hook pós-ETL para gerar 4 snapshots iniciais (financeiro, clientes, agenda, compras) na `shared_business_memory` após primeiro ETL de onboarding concluir. **1 conflito crítico encontrado** (C1) que bloqueia o início da implementação.

---

## Conflitos Detectados

### C1 🔴 CRÍTICO — CHECK constraint collision entre #22 e #21

**Arquivos:** `20260619000003_snapshot_templates.sql` (#22) e `20260619000003_routine_checkpoint_rpc.sql` (#21)

**Descrição:** Ambos fazem `DROP CONSTRAINT IF EXISTS shared_business_memory_entity_type_check` + recriação com seus próprios tipos. Nenhum inclui os tipos do outro.

| Migração | Issue | Tipos adicionados |
|----------|-------|-------------------|
| `snapshot_templates.sql` | #22 | `'snapshot'` |
| `routine_checkpoint_rpc.sql` | #21 | `'agent_result', 'agent_metadata', 'routine'` |

**Impacto:** A segunda migração a rodar destrói os tipos da primeira. Se `snapshot_templates` rodar depois, `entity_type='routine'` falha no CHECK. Se `routine_checkpoint` rodar depois, `entity_type='snapshot'` falha no CHECK.

**Resolução:** 
1. Criar migração unificada `20260619000003_entity_types_consolidated.sql` que aplica o UNION de todos os tipos: `'skill', 'client', 'contact', 'supplier', 'user', 'snapshot', 'agent_result', 'agent_metadata', 'routine'`
2. Remover as seções de CHECK constraint de ambos os arquivos originais (manter apenas suas outras operações)
3. Aplicar na ordem: unificada → snapshot_templates (sem CHECK) → routine_checkpoint_rpc (sem CHECK)

**Responsável:** T2.4.1 (aplicar migrações) — deve ser a primeira subtarefa executada.

---

### C2 🟡 WARNING — Branch inicialmente divergente

**Descrição:** A branch `phase-2/issue-24-post-etl-onboarding-snapshot` existia mas o workspace estava em `phase-0/issue-17-sm-preflight`.

**Resolução:** Aplicado `git checkout --force`. Branch correta está ativa. Sem consequências para o planejamento.

---

### C3 🟡 WARNING — 15 RPCs de referência não implementadas

**Descrição:** Nenhuma das queries listadas em `_SNAPSHOT_DIMENSION_FIELDS` (`get_cash_position`, `get_recent_transactions`, etc.) existe como função SQL.

**Resolução:** T2.4.4 cobre a criação de todas as RPCs faltantes. Se dados não existirem (cliente novo), retornar `[]` ou `{}` vazio — snapshots aceitam indicadores parciais (risco R1 mitigado).

---

### C4 ℹ️ INFO — `onboarding_complete` routine não gera snapshots

**Descrição:** A rotina existente tem 5 passos (build_context, save_context_map, upsert_clientes_blu_context, upsert_client_goals, init_home_state) mas nenhum gera snapshots.

**Impacto:** Nenhum. O hook pós-ETL opera em trigger separado sobre `reg_jobs`, não na rotina `onboarding_complete`. São pipelines independentes.

---

## Design Decisions (do plan.json)

| ID | Decisão | Status |
|----|---------|--------|
| DD1 | Hook via trigger AFTER UPDATE em `analytics_v2.reg_jobs` quando status → 'completed' pela primeira vez para client_id | ✅ Mantida |
| DD2 | Geração delegada a `analytics_v2.generate_onboarding_snapshots(p_client_id)` usando `_SNAPSHOT_DIMENSION_FIELDS` | ✅ Mantida |
| DD3 | Snapshots em `public.shared_business_memory` com `entity_type='snapshot'`, `entity_name='{dimensao}:{periodo}'` | ⚠️ Depende de C1 resolvido |
| DD4 | Períodos iniciais: financeiro=semanal, clientes=diario, agenda=mensal, compras=semanal | ✅ Mantida |
| DD5 | Frontmatter: `gerado_por='onboarding_etl_hook'`, `versao=1`, `template_version=1`, `confianca=0.85` | ✅ Mantida |

---

## Decomposição em Subtarefas

| ID | Título | Dependências | Assignee sugerido | Bloqueadores |
|----|--------|-------------|-------------------|-------------|
| T2.4.1 | Aplicar migrações de templates de snapshot (prereq #22) | — | factory-coder | C1 (CHECK merge) |
| T2.4.2 | Criar função SQL `generate_onboarding_snapshots` | T2.4.1 | factory-coder | — |
| T2.4.3 | Criar trigger pós-ETL em `reg_jobs` | T2.4.2 | factory-coder | — |
| T2.4.4 | Adicionar RPCs faltantes para queries de referência | T2.4.1 | factory-coder | 15 RPCs a criar |
| T2.4.5 | Teste de integração end-to-end | T2.4.3, T2.4.4 | factory-tester | — |
| T2.4.6 | Documentação e seed de snapshots | T2.4.5 | factory-coder | — |

---

## Pré-requisitos Verificados

| Prereq | Status | Notas |
|--------|--------|-------|
| `_SNAPSHOT_DIMENSION_FIELDS` em context_schemas.py | ✅ Completo | 4 dimensões, 21 indicadores, 15 queries ref |
| Validação de snapshot em memory_module.py | ✅ Completo | `_validate_snapshot_frontmatter()` + `_validate_snapshot_body()` |
| Tabela `shared_business_memory` | ✅ Migração proposta | `20260619000000_shared_business_memory.sql` |
| Trigger de integridade | ✅ Migração proposta | `20260619000002_shared_memory_integrity.sql` |
| `reg_jobs` com coluna `status` | ✅ Existe na baseline | `archive/20260430000000_baseline.sql` |
| Pipeline ETL com `apply_staging_to_facts` | ✅ Migração proposta | `20260526060000_unified_ingest_staging_and_apply.sql` |
| `entity_type='snapshot'` no CHECK | ⚠️ C1 | Depende de merge com #21 |
| RPCs de referência | ❌ Nenhuma existe | T2.4.4 cobre |

---

## Riscos e Mitigações

| Risco | Severidade | Mitigação | Responsável |
|-------|-----------|-----------|-------------|
| R1: Snapshots vazios para cliente sem dados | 🟡 MÉDIO | Snapshots aceitam indicadores opcionais; apenas 4 financeiro + 2 clientes são required | T2.4.2 |
| R2: Trigger dispara em retry de job | 🟡 MÉDIO | Verificar existência prévia de snapshots para client_id (idempotência) | T2.4.3 |
| R3: Conflito de migrações #22 vs #21 | 🔴 ALTO | Migração unificada de entity_types (C1) | T2.4.1 |

---

## Próximos Passos (pós-aprovação humana)

1. Criar task `t_{id}` para T2.4.1 (factory-coder): resolver C1 + aplicar migrações
2. Criar task `t_{id}` para T2.4.2 (factory-coder): `generate_onboarding_snapshots`
3. Criar task `t_{id}` para T2.4.3 (factory-coder): trigger pós-ETL
4. Criar task `t_{id}` para T2.4.4 (factory-coder): 15 RPCs de referência
5. Criar task `t_{id}` para T2.4.5 (factory-tester): teste end-to-end
6. Criar task `t_{id}` para T2.4.6 (factory-coder): docs + seed

Dependências: T2.4.2 depende de T2.4.1. T2.4.3 depende de T2.4.2. T2.4.4 é independente de T2.4.2/T2.4.3 (paralelo com T2.4.1). T2.4.5 depende de T2.4.3 + T2.4.4. T2.4.6 depende de T2.4.5.
