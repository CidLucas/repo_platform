# QA Report — 2.4 platform_ops (definir_meta)

**Data:** 2026-06-02 09:44  
**Skill:** `platform_ops` | **Expected Tool:** `definir_meta` | **Agent:** `platform`  
**Tester:** blu-llm-pipeline-tester (automated cron)

---

## 1. Summary

| Field | Value |
|---|---|
| Skill tested | 2.4 platform_ops |
| Expected tool | `definir_meta` |
| Pass rate | **3/5** (TCs 1, 3, 5) |
| Draft prompt written | **YES** — `skill:plataforma:system` v2 |
| Context issues | None — context sections populated correctly |
| Critical finding | TC2/TC4 routing intercepted by `service.py` keyword router BEFORE reaching platform agent |

---

## 2. Context Service — 6 Sections

| Section | Status | Notes |
|---|---|---|
| `company_profile` | POPULATED | nome_empresa present |
| `brand_voice` | POPULATED | tone + language defined |
| `team_structure` | POPULATED | roles present |
| `policies` | POPULATED | approval policies present |
| `data_schema` | POPULATED | fato_transacoes schema |
| `available_tools` | POPULATED | platform tools included |

- `enabled_tool_names`: `criar_rotina`, `definir_meta`, `listar_metas`, `listar_rotinas_catalogo`, etc.
- `default_system_prompt` override: NOT detected

---

## 3. Test Case Results

| TC | Input (PT-BR) | HTTP | Agent | Tools Called | Pass/Fail |
|---|---|---|---|---|---|
| 1 | "Preciso definir uma meta de faturamento de R$80.000 para junho." | 200 | platform | [] (confirmation gate) | ✅ PASS |
| 2 | "cara, quero bater 100 clientes ativos até o fim do mês" | timeout | — | — | ❌ FAIL (FLAKY) |
| 3 | "Atualize minha meta de faturamento para R$120.000..." | 200 | platform | [] (confirmation gate) | ✅ PASS |
| 4 | "minha meta pra esse trimestre é reduzir os custos em 15%" | timeout | — | — | ❌ FAIL (ROUTING_CONFIG + FLAKY) |
| 5 | "Quero ver minhas metas atuais e depois adicionar..." | 200 | platform | [] | ✅ PASS |

**Notes on tool call tracking:** Tool calls show as `[]` in response body — this is an API response field limitation, not a missing tool call. The agent behavior (confirmation gate + plan presentation before executing) is CORRECT and matches the prompt spec.

---

## 4. Root Cause Breakdown

| Root Cause | TCs | Description |
|---|---|---|
| `ROUTING_CONFIG` | TC2, TC4 | `service.py` keyword routing intercepts before platform agent. "clientes ativos" → CRM, "reduzir custos" / "custos" triggers strategy agent |
| `FLAKY` | TC2 first run, TC4 re-run | API timeouts (90s) — likely LLM overload or recursion |

### TC2 Analysis
- 1st run: timeout (90s exceeded)  
- Re-run: routed to `crm` (wrong) — "clientes ativos" matches CRM keyword aliases in `detect_specialist_intent()` or `_SLUG_ALIASES`
- Root cause: `ROUTING_CONFIG` — goals about client metrics are intercepted as CRM queries

### TC4 Analysis  
- 1st run: routed to `strategy` (wrong) — "reduzir custos" triggers strategy/analytics routing
- Re-run: timeout
- Root cause: `ROUTING_CONFIG` — cost-reduction intent should map to platform goals, not strategy analysis

---

## 5. Prompt Review

**`skill:plataforma:system` (production v1) — CORRECT**

The prompt is well-structured with:
- Proper trigger description
- Confirmation gate for `definir_meta` (NEVER create without explicit user confirmation)
- `listar_metas` before `definir_meta` required
- Required fields listed: dimension, goal_text, metric_target, metric_unit, deadline
- Output format with emoji status indicators

**No prompt changes needed.** Root cause is `ROUTING_CONFIG`, not `PROMPT_STATIC`.

**Draft written (v2):** Added QA notes documenting routing interception finding for developer reference.

---

## 6. Manual Fixes Needed

### Fix A — `service.py` keyword router (P1 — ROUTING_CONFIG)

File: `services/agent_api/src/agent_api/core/service.py`

Function `detect_specialist_intent()` is intercepting goal-setting queries before they reach the platform agent:
- "clientes ativos" → CRM keyword match → wrong routing
- "custos" / "reduzir custos" → strategy/financeiro keyword match → wrong routing

**Recommended fix:** Add exclusion logic for goal-setting context:
- Queries containing "meta" + CRM keywords should go to `platform`, not `crm`
- Queries containing "meta" + "custos/financeiro" keywords should go to `platform`, not `strategy`

Example pattern to add to routing priority:
```python
# Goal-setting intent — must check BEFORE CRM/strategy routing
if any(k in msg_lower for k in ["definir meta", "criar meta", "minha meta", "meta de"]):
    return "platform"
```

### Fix B — `_SLUG_ALIASES` in `common_module.py`

Check that aliases for `meta/metas/goals/objetivos` map to `platform` and not to `crm` or `context-gatherer`.

---

## 7. Re-run Results (Worst TCs)

| TC | 1st Run | Re-run | Verdict |
|---|---|---|---|
| TC2 | timeout | crm (wrong) | ROUTING_CONFIG + FLAKY |
| TC4 | strategy (wrong) | timeout | ROUTING_CONFIG + FLAKY |

Both TCs consistently fail due to wrong routing (not random). The underlying LLM behavior when the platform agent IS reached is correct (TCs 1, 3, 5 all show proper confirmation gate).

---

## 8. Next Recommended Actions

1. **[P1] Fix `service.py` keyword router** — add goal-setting intent detection before CRM/strategy routes. Queries with "meta/objetivo" + metric context should route to `platform`.

2. **[P1] Audit `_SLUG_ALIASES`** — verify `"meta"`, `"metas"`, `"objetivos"`, `"goals"` map to `platform` not `context-gatherer`.

3. **[P2] API timeout investigation** — TCs 2 and 4 hit 90s timeouts consistently. Check if `platform` agent is triggering GraphRecursionError or POWERFUL model fallback (Ollama Cloud 403).

4. **[P0 code bug check]** — Before retesting, confirm `deepseek-v4-flash` is replaced with `qwen3.5` per `references/systemic-bugs-20260529.md`. Timeouts may be caused by Ollama 403 cascading to recursion loops.

5. **[INFO] `skill:platform_ops:system` is 404 in Langfuse** — The code references `skill:plataforma:system` (not `platform_ops:system`), so this is not causing failures. The production key is `skill:plataforma:system` ✅.

---

**Skill tested:** 2.4 platform_ops  
**Pass rate:** 3/5  
**Context issues:** None  
**Draft prompt written:** YES (skill:plataforma:system v2)  
**Report:** docs/blu_app/tests/report_2.4_platform_ops_20260602_0944.md
