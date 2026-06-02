# QA Report — 1.2 end_of_day_digest
**Date:** 2026-06-02 03:50  
**Skill ID:** 1.2  
**Skill:** end_of_day_digest  
**Expected Tool:** execute_sql  
**Expected Agent:** financeiro  
**Tester:** blu-llm-pipeline-tester (cron)

---

## 1. Summary

| Field | Value |
|---|---|
| Pass rate | **0/5** |
| Draft written | NO — root cause is code-level ROUTING_CONFIG, not PROMPT_STATIC |
| Primary root cause | `detect_synthesis_intent` in `service.py` intercepts multi-domain EOD queries and routes to `strategy` agent before frontdesk |
| Secondary root cause | Langfuse loader bug: `'LoadedPrompt' object is not subscriptable` (P1#5) prevents `skill:end_of_day_digest:system` from loading at runtime |
| Tertiary issue | `required_tool_names=[]` in SkillDefinition — skill cannot call `execute_sql` |

---

## 2. Context Service

| Section | Status | Note |
|---|---|---|
| ContextService instantiation | BLOCKED | `ContextService.__init__` requires `cache_service` (RedisService); cannot instantiate outside container |
| Langfuse prompt (`skill:end_of_day_digest:system`) | EXISTS (TEXT type) | Content found; but loader crashes with `'LoadedPrompt' object is not subscriptable` |
| Builtin fallback | EXISTS | `blu_prompt_management.templates` has `SKILL_EOD_DIGEST` builtin |
| `required_tool_names` | `[]` (empty) | `execute_sql` is NOT declared — skill cannot invoke it |

---

## 3. TC Results

| TC | Message | HTTP | Agent | Skill | Tool | Result |
|---|---|---|---|---|---|---|
| TC1 | "Preciso do resumo do final do dia..." | 200 | `strategy` | — | none | ❌ FAIL — wrong agent, error response |
| TC2 | "Me manda o digest de hoje né..." | 200 | `strategy` | — | none | ❌ FAIL — wrong agent, error response |
| TC3 | "Relatório de encerramento do dia..." | 200 | `strategy` | — | none | ❌ FAIL — wrong agent, error response |
| TC4 | "E aí, como foi o dia? Me dá um resumo" | 200 | `frontdesk` | — | none | ❌ FAIL — chit-chat, no routing to financeiro |
| TC5 | "Tudo o que aconteceu hoje no meu negócio..." | 200 | `frontdesk` | — | none | ❌ FAIL — inline SQL fails, no data returned |

**Pass rate: 0/5**

---

## 4. Root Cause Breakdown

| Root Cause | TCs | Description |
|---|---|---|
| `ROUTING_CONFIG` | TC1, TC2, TC3 | `detect_synthesis_intent` in `service.py` intercepts before frontdesk. Queries mentioning "transações+tarefas+pendências" or "desempenho+tarefas+itens" are classified as multi-domain synthesis → routed to `strategy` agent. Strategy agent crashes (Ollama 403 P0 on deepseek-v4-flash for POWERFUL tier) |
| `ROUTING_CONFIG` | TC4 | Informal "como foi o dia" goes to frontdesk; frontdesk answers inline as chit-chat, never invokes `end_of_day_digest` skill or routes to `financeiro` |
| `ROUTING_CONFIG` + `CONTEXT_MISSING` | TC5 | Frontdesk attempts inline SQL for "hoje" but SQL fails (no data for today or GraphRecursionError); returns error message |

**Secondary issues (not root causes for routing):**
- **P1#5 Bug:** `skill:end_of_day_digest:system` in Langfuse is `type=text` (correct) but the loader still throws `'LoadedPrompt' object is not subscriptable` — needs investigation in `loader.py`. This means even if the skill is reached, it runs with empty/builtin prompt.
- **`required_tool_names=[]`:** The SkillDefinition has no tools declared. Even if invoked, the skill cannot call `execute_sql` to fetch today's transactions. This is an **intentional design** (the skill is supposed to receive data as variables from the routine, not query on its own), but it means the skill cannot be meaningfully tested via direct chat — it only makes sense when triggered by the `end_of_day_digest` routine with pre-fetched data.

---

## 5. Prompt Improvements Applied

**Draft written: NO**

Root cause is ROUTING_CONFIG (code), not PROMPT_STATIC. Writing prompt improvements would not fix the interception in `detect_synthesis_intent` or the missing `required_tool_names`.

**What a prompt fix CANNOT solve here:**
- `detect_synthesis_intent` runs BEFORE any LLM call in `service.py` — hardcoded keyword matching
- `required_tool_names=[]` is in `skills.py` (code), not in the Langfuse prompt

---

## 6. Manual Fixes Needed

### P0 — Strategy agent HTTP 500 (Ollama 403)
**File:** `services/agent_api/src/agent_api/core/client.py` (~line 359)  
**Fix:** Replace `OllamaCloudModel.DEEPSEEK_V4_FLASH` → `OllamaCloudModel.QWEN3_5` for ModelTier.POWERFUL  
**Impact:** TC1, TC2, TC3 all crash because `strategy` agent uses POWERFUL tier → 403 → HTTP 500

### P1 — `detect_synthesis_intent` over-intercepts EOD queries
**File:** `services/agent_api/src/agent_api/core/service.py`  
**Issue:** EOD digest queries mentioning multiple concepts ("transações", "tarefas", "pendências") match synthesis detection and are intercepted before frontdesk/financeiro routing  
**Fix:** Add negative pattern for "digest/resumo do dia/encerramento" — should bypass synthesis detection and go to frontdesk → financeiro  
**Severity:** Blocks 3/5 TCs deterministically

### P1 — `required_tool_names=[]` in end_of_day_digest SkillDefinition
**File:** `libs/blu_agent_framework/src/blu_agent_framework/skills.py` line 403  
**Issue:** Skill has no tools, so it can't query transactions. Design intent is "routine-fed data", but testing via chat is impossible without this.  
**Recommendation:** Either add `execute_sql` to `required_tool_names` so skill can work standalone, OR document clearly that this skill is routine-only and should NOT appear in routing tests.

### P1 — Langfuse loader: `'LoadedPrompt' object is not subscriptable`
**File:** `libs/blu_prompt_management/src/blu_prompt_management/loader.py`  
**Issue:** Known P1#5 bug — loader crashes even for TEXT-type prompts. `agents/frontdesk` also affected.  
**Fix:** Add `isinstance(compiled_text, list)` guard per blu-prompt-engineering skill documentation

### P2 — Frontdesk doesn't route "informal EOD" to financeiro/end_of_day_digest
**TC4:** "E aí, como foi o dia? Me dá um resumo rápido" → frontdesk chit-chat  
**Root cause:** Either `routing_hint` for `financeiro` doesn't include EOD patterns, or frontdesk prompt doesn't associate "como foi o dia" with digest skill  
**Action:** After fixing P0+P1, test again and add EOD trigger phrases to frontdesk `routing_hint` if still failing

---

## 7. Re-Run Results (2 Worst TCs)

| TC | 1st Run | Re-Run | Deterministic? |
|---|---|---|---|
| TC1 | HTTP 200, agent=strategy, error response | HTTP 500, no response | Deterministic FAIL (strategy crashes, sometimes harder) |
| TC2 | HTTP 200, agent=strategy, error response | HTTP 200, agent=strategy, error response | Deterministic FAIL |

**Conclusion:** Failures are deterministic. TC1 re-run escalated to HTTP 500 (strategy agent crashed harder on 2nd attempt). Both confirm the strategy agent is broken for POWERFUL-tier model calls.

---

## 8. Next Recommended Actions

1. **[P0 BLOCKER]** Fix Ollama 403 in `client.py` — replace `DEEPSEEK_V4_FLASH` with `QWEN3_5` for POWERFUL tier. Rebuild `blu_agent_api` with `--no-cache`. This unblocks strategy agent and CRM.
2. **[P1]** Fix loader P1#5 bug in `loader.py` — add `isinstance(compiled_text, list)` normalization. This affects ALL prompts across the platform.
3. **[P1]** Add negative synthesis pattern for EOD/digest queries in `service.py::detect_synthesis_intent`.
4. **[P2]** After code fixes, re-test with TC4/TC5 to check frontdesk → financeiro routing for informal EOD queries.
5. **[P2]** Decide: should `end_of_day_digest` skill have `execute_sql` in `required_tool_names`? If yes, add it in `skills.py`.
6. **[INFO]** This skill is inherently "routine-triggered" (data is pre-fetched by the routine's SQL steps and passed as variables). Direct chat testing is not the primary use case — consider marking as `chat_testable=False` in SkillDefinition.
