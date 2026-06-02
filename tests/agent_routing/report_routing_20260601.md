# Routing Test Report — 2026-06-01

## Resultado Geral

| Métrica | Valor |
|---|---|
| Total de TCs | 50 |
| ✅ Pass | 21 (42%) |
| ⚠️ Wrong agent | 27 (54%) |
| ❌ HTTP error | 2 (4%) |
| Latência média | ~19.7s |

## Por Layer

| Layer | Pass | Wrong | Error | Total |
|---|---|---|---|---|
| L1 — Routing Coverage | 9 | 9 | 2 | 20 |
| L2 — Edge Cases | 2 | 8 | 0 | 10 |
| L3 — Tool Invocation | 5 | 5 | 0 | 10 |
| L4 — Graceful Failure | 5 | 5 | 0 | 10 |

---

## Falhas por Padrão (Root Cause)

### 🔴 P0 — `synthesis` nunca alcançado (6 misses → frontdesk)

TCs: #04, #05, #06, #21, #22, #45

Todas as queries de síntese estratégica caem no `frontdesk`. O `detect_synthesis_intent()` não está ativando — keywords como `"custo"`, `"investimento"`, `"afetando minha capacidade"`, `"o que está acontecendo"` não estão matchando.

**Fix:** Auditar `_SYNTHESIS_KEYWORDS` e `_SLUG_ALIASES` em `common_module.py`. Possível que `synthesis` esteja mapeado para outro slug ou a checagem de 2 dimensões não está funcionando.

---

### 🔴 P0 — `crm` nunca alcançado (5 misses: 4× frontdesk, 1× agenda)

TCs: #15, #16, #26, #35, #40

Keywords como `"clientes em risco"`, `"ltv"`, `"cohort"`, `"clientes inativos"`, `"slack"` não estão roteando para `crm`.

**Fix:** Verificar se `crm` está em `_SLUG_ALIASES` com mapeamento correto. Possível conflito com `detect_specialist_intent()` não registrando `crm` como opção válida.

---

### 🔴 P0 — `fiscal-agent` roteando para `context-gatherer` (2× TCs #11, #41)

Keywords `"nota fiscal"` estão sendo interceptadas pelo `context-gatherer` antes do `detect_specialist_intent()`. Provavelmente `_SLUG_ALIASES` mapeia `"nota fiscal"` → `context-gatherer` (legado).

**Fix:** Remapear no `_SLUG_ALIASES`: `"nota fiscal"` → `"fiscal-agent"`.

---

### 🟠 P1 — `platform` parcialmente quebrado (5 misses: 3× frontdesk, 2× agenda)

TCs: #25, #33, #34, #43, #49

- `"Quais rotinas"` → `agenda` (keyword "rotinas" colide com agenda?)
- `"Quais são minhas metas"` → `frontdesk`
- `"Cria uma rotina"` (bare) → `frontdesk` (keyword só matchou quando mais específico)
- `"Agenda uma reunião e define uma meta"` → `agenda` (agenda ganha no primeiro match)

**Fix:** `detect_platform_intent()` deve checar antes de `detect_scheduler_intent()`. Verificar se "rotinas" e "metas" estão nas keywords de `platform`.

---

### 🟠 P1 — `compras` (supplier) parcialmente quebrado (3× frontdesk)

TCs: #24, #28, #31

- `"cotação e verificar agenda do fornecedor"` → `frontdesk` (deveria ser compras pelo primeiro match)
- `"fornecedor"` sozinho → `frontdesk`
- `"Lista os fornecedores"` → `frontdesk`

**Fix:** `"fornecedor"` deve ser keyword de `compras`. Verificar se está mapeado.

---

### 🟡 P2 — `estrategia` não alcançado (2× frontdesk)

TCs: #17, #27

- `"foco estratégico"` → `frontdesk`
- `"Planejamento para o próximo mês"` → `frontdesk` (nota do TEST_PLAN: `"planejamento"` é synthesis keyword, não estrategia)

**Fix:** Adicionar `"foco estratégico"`, `"planejamento para"` ao routing de `estrategia`.

---

### 🟡 P2 — `agenda` não alcançado em 2 casos

TCs: #30, #47

- `"prazo da entrega"` → `frontdesk` (keyword "prazo" não mapeada?)
- `"99h"` (horário inválido) → `frontdesk` (deveria chegar ao agenda que rejeita)

---

### ⚫ HTTP 0 — Timeouts em #02 e #18

- `"Ativa o monitor de estoque baixo"` → timeout
- `"Monta um plano trimestral para crescimento"` → timeout

Latência média de ~20s indica que alguns agentes (especialmente `estrategia`, `synthesis`) estão usando modelo POWERFUL (possivelmente deepseek-v4-flash) que retorna 403 → timeout. Ver bug documentado em `systemic-bugs-20260529.md`.

---

## Casos que Passaram ✅

L1: #01, #03, #07, #08, #09, #10, #13, #19, #20  
L2: #23, #29  
L3: #32, #36, #37, #38, #39  
L4: #42, #44, #46, #48, #50  

Roteamento estável: `frontdesk` (fallback SQL/RAG), `agenda` (scheduler), `compras` (cotação keyword), `doc-writer` (SOP keyword).

---

## Matriz de Confusão

| Expected | Got | Count |
|---|---|---|
| synthesis | frontdesk | 6× |
| crm | frontdesk | 4× |
| compras | frontdesk | 3× |
| platform | frontdesk | 3× |
| fiscal-agent | context-gatherer | 2× |
| platform | agenda | 2× |
| agenda | frontdesk | 2× |
| estrategia | frontdesk | 2× |
| crm | agenda | 1× |
| doc-writer | strategy | 1× |
| fiscal-agent | frontdesk | 1× |

> `frontdesk` absorvendo 25 das 27 falhas — é o dreno padrão quando keywords não matcham.

---

## Ações Recomendadas (Prioridade)

| Pri | Fix | Arquivo | Impacto |
|---|---|---|---|
| P0 | Remapear `"nota fiscal"` → `fiscal-agent` em `_SLUG_ALIASES` | `common_module.py` | +2 TCs |
| P0 | Auditar `detect_synthesis_intent()` — keywords não matchando | `service.py` | +6 TCs |
| P0 | Auditar `crm` em `_SLUG_ALIASES` e `detect_specialist_intent()` | `common_module.py` | +5 TCs |
| P0 | Rebuild após fix de deepseek-v4-flash 403 (ver bug 20260529) | `client.py` | +2 TCs (timeouts) |
| P1 | Garantir `platform` checked antes de `agenda` no pipeline | `service.py` | +2 TCs |
| P1 | Adicionar `"fornecedor"`, `"lista fornecedores"` às keywords de `compras` | `service.py` | +2 TCs |
| P2 | Adicionar `"foco estratégico"`, `"planejamento para"` às keywords de `estrategia` | `service.py` | +2 TCs |

**Potencial após fixes P0:** 21 → ~36 pass (72%)  
**Potencial após P0+P1+P2:** ~42 pass (84%)

---

*Gerado por Hermes em 2026-06-01. Traces Langfuse: tag `routing-test`, session prefix `test-20260601`.*
