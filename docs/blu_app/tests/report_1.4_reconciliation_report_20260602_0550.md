# QA Report — 1.4 reconciliation_report

**Date:** 2026-06-02 05:50  
**Skill ID:** 1.4  
**Skill Name:** reconciliation_report  
**Expected Tool:** execute_sql (via financeiro agent)  
**Expected Agent:** financeiro  
**Tester:** blu-llm-pipeline-tester (automated cron)  

---

## 1. Summary

| Field | Value |
|---|---|
| Skill tested | 1.4 reconciliation_report |
| Pass rate | 0/5 |
| Draft prompt written | YES — `agents/frontdesk` v22 |
| Context issues | ContextService not instantiable outside Docker (requires cache_service arg) |
| Primary root cause | ROUTING_CONFIG (missing reconciliation keywords in frontdesk routing table) |
| Secondary finding | reconciliation_report is a routine-only skill (pure generation, no tool calls) — not in financeiro.skill_slugs by design |

---

## 2. Context Service Assessment

| Section | Status | Notes |
|---|---|---|
| company_profile | UNKNOWN | ContextService requires cache_service arg — not directly inspectable outside container |
| brand_voice | UNKNOWN | Same |
| team_structure | UNKNOWN | Same |
| policies | UNKNOWN | Same |
| data_schema | UNKNOWN | Same |
| available_tools | UNKNOWN | Same |
| enabled_tool_names | N/A | reconciliation_report has `required_tool_names=[]` — pure generation |
| default_system_prompt override | NOT CHECKED | DOCKER EXEC approach not used (ContextService init fails outside container without Redis) |

**Note:** `ContextService.__init__()` requires `cache_service` (RedisService) as positional arg. Script to inspect context outside container fails. Per pitfall docs: infer from API responses.

**Inferred from responses:** The financeiro agent has SQL access and was tried inline by frontdesk (TC3/TC4 produced partial SQL query attempts). Client `6446d4fa` likely has minimal/no fato_transacoes data for test account.

---

## 3. Prompt Status (Step 3a)

| Prompt Key | Status |
|---|---|
| `skill:reconciliation_report:system` | EXISTS — type=text, production label. Pure generation prompt (no tool calls). |
| `agents/frontdesk` | EXISTS — type=chat (causing `'LoadedPrompt' object is not subscriptable` in loader). Content readable directly via SDK. |
| `agents/financeiro` | EXISTS — same type=chat loader issue. |

**⚠️ Loader Bug Present:** All three prompts return `'LoadedPrompt' object is not subscriptable` when loaded via `PromptLoader.load()`. This matches the known pitfall: prompts created as `type=chat` in Langfuse cause `compiled_text` to be a list instead of str. The `loader.py` fix (concatenate list to str) may not be deployed in the current container.

---

## 4. Skill Definition Analysis

```
reconciliation_report:
  required_tool_names: []    # PURE GENERATION — no execute_sql called
  prompt_name: skill:reconciliation_report:system
  tags: [routines, finance, reconciliation, narrative]
```

**This skill is designed to be invoked by routines**, with financial context pre-injected as Jinja2 variables (`saldo_inicio`, `saldo_fim`, `mes_referencia`, etc.). It is NOT meant for interactive chat routing via `execute_sql`.

The skill_priority.md lists expected_tool as `execute_sql`, but the Langfuse prompt explicitly states: *"This skill operates as a pure generation skill — no tool calls are required."*

**Expected behavior for chat queries about reconciliation:** route to `financeiro` agent (which has SQL access) → financeiro runs execute_sql → produces narrative.

---

## 5. TC Results Table

| TC | Input | HTTP | Agent | Tool Called | Pass/Fail | Root Cause |
|---|---|---|---|---|---|---|
| TC1 | Relatório de conciliação financeira do mês passado (formal) | 200 | frontdesk | none | ❌ FAIL | ROUTING_CONFIG |
| TC2 | Fecha o mês pra mim — resumo entrou/saiu (informal) | 200 | frontdesk | none | ❌ FAIL | ROUTING_CONFIG |
| TC3 | Conciliação de caixa de maio, fornecedores e discrepâncias | 200 | frontdesk | none | ❌ FAIL | ROUTING_CONFIG |
| TC4 | Meu caixa está batendo? Conciliar transações (diagnóstica) | 200 | frontdesk | none | ❌ FAIL | ROUTING_CONFIG |
| TC5 | Execute conciliação mensal: categorias, outliers, top pagamentos | 200 | frontdesk | none | ❌ FAIL | ROUTING_CONFIG |

**Observed behavior:** All 5 TCs stayed at frontdesk. TC1, TC2, TC5 hit SQL recursion loop ("dificuldade ao processar SQL após múltiplas tentativas"). TC3, TC4 attempted inline SQL with no data found (client lacks fato_transacoes rows).

---

## 6. Root Cause Breakdown

| Root Cause | TCs | Description |
|---|---|---|
| ROUTING_CONFIG | TC1–TC5 (100%) | Frontdesk routing table missing "conciliação", "reconciliação", "fechamento de mês", "anomalias" keywords for `financeiro` slug. |
| CONTEXT_MISSING (data) | TC3, TC4 (partial) | Test client lacks fato_transacoes data — even correct routing would produce empty results. |

**Systemic issue also detected:**
- `PromptLoader.load()` fails with `'LoadedPrompt' object is not subscriptable` for ALL prompts checked. This indicates the `type=chat` prompt fix is not deployed in the current container, or all 3 prompts were created as chat type.

---

## 7. Prompt Improvements Applied

### agents/frontdesk — routing table fix

**Before (v21):**
```
| Fluxo de caixa, DRE, análise financeira com projeção, relatório de lucro | `financeiro` |
```

**After (v22, draft):**
```
| Fluxo de caixa, DRE, análise financeira com projeção, relatório de lucro, conciliação financeira, reconciliação de caixa, fechamento de mês, anomalias nas despesas, relatório de conciliação | `financeiro` |
```

**Draft key:** `agents/frontdesk`  
**Version:** v22  
**Label:** draft (promote to production manually in Langfuse UI)  
**Impact:** Routes reconciliation/conciliation queries to `financeiro` agent.

---

## 8. Manual Fixes Needed

### P1 — Promote frontdesk v22 to production
After reviewing, promote `agents/frontdesk` v22 in Langfuse UI: Prompts → agents/frontdesk → v22 → Add label "production".

### P1 — Fix PromptLoader for type=chat prompts (or recreate as type=text)
All 3 prompts tested fail with `'LoadedPrompt' object is not subscriptable`. Check `loader.py` in the container for the list-concatenation fix. If not applied, deploy the fix or recreate prompts as `type=text`.

Diagnostic:
```bash
docker exec blu_agent_api python3 -c "
from blu_prompt_management.loader import PromptLoader
import asyncio
async def t():
    l = PromptLoader()
    r = await l.load('agents/frontdesk')
    print(type(r), r[:100])
asyncio.run(t())
"
```

### P2 — Populate test client data
Client `6446d4fa` (skill priority test client) appears to have no `fato_transacoes` data. Even after routing fix, reconciliation queries will return "no data". Run data ingestion for this client.

### P3 — Update skill_priority.md expected_tool
The priority map shows `execute_sql` as expected tool for `reconciliation_report`. The actual prompt is pure generation — correct expected_tool should be `N/A (routine-only)` or `execute_sql via financeiro`. Update the table for accuracy.

---

## 9. Re-run Results (2 Worst TCs)

| TC | First Run | Re-run | Deterministic? |
|---|---|---|---|
| TC1 | frontdesk, SQL loop error | frontdesk, SQL loop error | ✅ Yes — deterministic failure |
| TC5 | frontdesk, SQL loop error | frontdesk, SQL loop error | ✅ Yes — deterministic failure |

**Conclusion:** Failures are deterministic, not flaky. Routing fix (v22 draft) must be promoted to production before re-testing.

---

## 10. Next Recommended Actions

1. **Promote `agents/frontdesk` v22 to production** — resolves routing for all reconciliation queries
2. **Investigate PromptLoader `type=chat` bug** — affects multiple skills, blocking prompt introspection
3. **Populate fato_transacoes data for test client** — needed for meaningful reconciliation results after routing fix
4. **Next QA item:** 2.1 ledger (register_transaction → data-entry)
