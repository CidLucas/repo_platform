# resolution.md — Decisões de design resolvidas + Conflitos

> Issue #32 — T4.4: Política de retenção e prune da shared memory
> Planner: factory-planner | Date: 2026-06-19

---

## Decisões revisadas (DD-01 a DD-07)

### DD-01: Soft-delete em 2 fases ✅ APROVADO
Soft-delete (archived=true) → archival 90d → hard-delete físico.
**Racional confirmado:** Alinha com LGPD. Permite restore acidental. Janela de 90d é padrão de mercado para dados de negócio.

### DD-02: 5 TTL tiers ✅ APROVADO (com ajuste)
| Tier | TTL | Uso |
|------|-----|-----|
| curated | ∞ (NULL) | Dados curados manualmente, seed data |
| migration | 90d | Dados migrados de sistemas legados |
| specialist | 30d | Conhecimento gerado por agentes L3 |
| memory_agent_hi | 14d | Fatos de alta relevância do memory agent |
| memory_agent_lo | 7d | Fatos transitórios, observações passageiras |

**Ajuste:** TTL tier é propriedade da COLUNA `ttl_tier`, não do `source`. O source continua sendo a proveniência (quem gerou). O tier determina a política de retenção.

### DD-03: Volume limit 50/entidade ✅ APROVADO (com correção)
Trigger BEFORE INSERT conta `WHERE archived=false AND soft_delete_at IS NULL` para o mesmo (client_id, entity_type, entity_name).

**⚠ CORREÇÃO CRÍTICA:** O plan referencia `source='curated'` como exceção, mas 'curated' NÃO é um valor válido no CHECK constraint de source (só: manual, memory_agent, specialist, migration, system). A exceção deve ser baseada em `ttl_tier='curated'`, não em source.

**Correção proposta:**
```sql
IF NEW.ttl_tier = 'curated' THEN RETURN NEW; END IF;  -- sem limite
```

### DD-04: Routine Engine vs pg_cron ✅ APROVADO (com correção de path)
O Routine Engine NÃO é um serviço separado. Vive em `services/agent_api/src/agent_api/core/routines.py`.

**Correção de path:** T4.4d deve criar a função de prune em:
- `services/agent_api/src/agent_api/core/routine_functions.py` (registrar `prune_shared_memory` como fetch function)
- OU como rotina no catálogo `cross_agent_routines` (INSERT na tabela)
- **NÃO** criar `services/routine_engine/src/routines/prune_shared_memory.py`

**DQ-03 respondida:** O engine atual usa pg_cron para dispatch. Não tem timezone-aware cron nativo — mas 03:00 UTC é trivial de expressar como `0 3 * * *` no pg_cron. Se for usar o Routine Engine, precisa ser como rotina registrada que o dispatcher chama.

### DD-05: Alerta >100 registros ✅ APROVADO
Silencioso para operação normal. Alerta condicional evita fatigue.

### DD-06: Incorporar lifecycle columns na migration base ✅ APROVADO (com ressalva)
A migration `20260619000000` está em `proposed/` (não aplicada). Incorporar lifecycle columns nela é correto.

**⚠ RESSALVA:** A migration `20260619000003` (issue #21) faz ALTER TABLE para expandir entity_type. Se incorporarmos tudo na base, precisamos também incluir os entity_types expandidos (agent_result, agent_metadata, routine) na base migration. Caso contrário, o ALTER da #21 vai conflitar.

**Recomendação:** Consolidar `20260619000000` + `20260619000003` + lifecycle columns em uma única migration, ou coordenar com o owner da #21.

### DD-07: Backup race condition ✅ APROVADO
Prune (03:00) verifica checkpoint de backup (02:00) antes de executar. Janela de 1h é adequada.

---

## Conflitos detectados (4)

### CONFLICT-01: 'curated' como source vs ttl_tier 🔴 CRÍTICO
**Onde:** Plan.intake.json DD-03, T4.4c  
**Problema:** O plan trata 'curated' como valor de `source`, mas o CHECK constraint da migration só permite: manual, memory_agent, specialist, migration, system. 'curated' não existe como source.  
**Resolução:** Usar `ttl_tier` (nova coluna) como discriminante, não `source`. Adicionar 'curated' ao CHECK de source é uma alternativa, mas semanticamente errado — curated é política de retenção, não proveniência do dado.

### CONFLICT-02: memory_module.py — 3 plans editam o mesmo arquivo 🟡 ALTO
**Arquivo:** `services/tool_pool_api/.../memory_module.py` (1262 linhas)  
**Plans concorrentes:**
- #26 (T3.2): adiciona `shared_memory_search` + expande `_VALID_ENTITY_TYPES`
- #30 (T4.2): adiciona helpers `upsert_synthesis_output()`, `upsert_dedup_mapping()`, etc.
- #32 (T4.4c): adiciona parâmetro `ttl_tier` em upsert/write

**Mitigação:** Ordenar implementação: #32 depende de #26 para _VALID_ENTITY_TYPES expandido. #30 e #32 editam funções DIFERENTES do módulo — conflito gerenciável se ordem for respeitada.

### CONFLICT-03: Migration cascade — entity_type CHECK 🟡 MÉDIO
**Problema:** 3 migrations em proposed/ tocam a mesma tabela:
1. `20260619000000` — CREATE TABLE (entity_type base)
2. `20260619000003` — ALTER TABLE entity_type (expande)
3. T4.4a — ALTER TABLE lifecycle columns

Se as migrations são aplicadas em ordem numérica, o ALTER da #21 quebra se a tabela for recriada com schema diferente.

**Resolução:** Consolidar tudo em uma única migration antes de promover para applied/. Alternativa: aplicar 00000 → 00003 → T4.4a em sequência (ALTERs compatíveis).

### CONFLICT-04: TOOL_INVENTORY — YAML não existe 🟢 BAIXO
**Problema:** Plan referencia `configs/tool_inventory.yaml` — arquivo não existe.  
**Realidade:** O registry de tools é código Python. A wiki `TOOL_INVENTORY.md` é documentação.  
**Resolução:** T4.4e deve atualizar o `TOOL_INVENTORY.md` (adicionar shared_memory_read/write que faltam) E verificar se o registry Python está completo. NÃO criar `configs/tool_inventory.yaml`.

---

## Design Questions respondidas

| DQ | Pergunta | Resposta |
|----|----------|----------|
| DQ-01 | Volume limit 50 configurável por tenant? | **Não agora.** 50 é conservador. Monitorar rejeições (R-01). Adicionar config per-tenant é over-engineering no MVP. |
| DQ-02 | 90 dias archival suficiente? | **Sim para MVP.** LGPD não exige retenção específica para dados de negócio. 90d é janela de segurança razoável para restore acidental. |
| DQ-03 | Routine Engine suporta 03:00 UTC? | **Via pg_cron sim.** O engine atual não tem cron próprio — usa pg_cron para dispatch. Expressão `0 3 * * *` resolve. |
| DQ-04 | TOOL_INVENTORY location? | **`docs/llm_wiki/TOOL_INVENTORY.md`** (wiki). O registry Python real está em `tool_modules/registry.py`. NÃO criar YAML. |

---

## 3 Delivery Units (ordem de implementação)

### DU-1: Foundation (T4.4a + T4.4b)
- Migration consolidada: lifecycle columns + volume limit trigger
- Depende de: NADA (migrations ainda em proposed/)
- Bloqueia: TUDO abaixo

### DU-2: Core Logic (T4.4c + T4.4d)
- memory_module.py: adicionar ttl_tier parameter
- Routine function: prune_shared_memory registrada
- Depende de: DU-1 (colunas existem), #26 (entity_types)
- Bloqueia: DU-3

### DU-3: Registry + Tests (T4.4e + T4.4f)
- TOOL_INVENTORY.md atualizado
- Testes unitários + integração
- Depende de: DU-2 (lógica implementada)

---

## Recomendação final

**APROVAR com as correções acima.**
O plano é sólido mas precisa de 3 ajustes antes da implementação:
1. Corrigir 'curated' → usar `ttl_tier`, não `source` (CONFLICT-01)
2. Corrigir paths do Routine Engine (CONFLICT-03, DQ-03)
3. Corrigir target do TOOL_INVENTORY (CONFLICT-04)
