# QA Report — 2.3 platform_ops (criar_rotina)
**Date:** 2026-06-02 08:51  
**Tester:** blu-llm-pipeline-tester (cron)  
**Skill tested:** `platform_ops` | Expected tool: `criar_rotina`  
**Expected agent:** `platform`

---

## 1. Summary

| Metric | Value |
|---|---|
| Pass rate | 0/5 (0%) |
| Correct routing | 3/5 (TC2, TC4, TC5 → `platform`) |
| Tool called | 0/5 |
| Draft prompt written | YES — `skill:plataforma:system` v1 (label=production) |
| Context issues | `skill:plataforma:system` absent from Langfuse (404) → empty system prompt |

**Root cause summary:** Two distinct failure modes.  
1. **TC1, TC3**: Pre-frontdesk keyword routing in `service.py` intercepts messages containing "relatório"/"resumo"/"automático" and routes to `agenda` — platform agent never sees these messages.  
2. **TC2, TC4, TC5**: Correct routing to `platform`, but `skill:plataforma:system` was missing from Langfuse → agent ran with empty system prompt → no tool calls, just elicitation prose.

---

## 2. Context Service

| Section | Status |
|---|---|
| `company_profile` | Unable to verify (ContextService requires RedisService, cannot instantiate outside Docker) |
| `brand_voice` | Unable to verify |
| `team_structure` | Unable to verify |
| `policies` | Unable to verify |
| `data_schema` | Unable to verify |
| `available_tools` | Unable to verify |
| `default_system_prompt` override | Unknown — could not access ContextService |
| `enabled_tool_names` | N/A |

**Note:** `skill:plataforma:system` prompt key was confirmed absent from Langfuse (HTTP 404). Builtin fallback is disabled in the loader. This is the primary failure for TC2/TC4/TC5.

---

## 3. TC Results Table

| TC | Message | Expected Agent | Actual Agent | Tool Called | Status | Root Cause |
|---|---|---|---|---|---|---|
| TC1 | "Quero ativar o relatório diário de vendas para receber toda manhã." | platform | **agenda** | none | ❌ FAIL | ROUTING_CONFIG |
| TC2 | "me ajuda a configurar uma rotina automática pra mandar o resumo financeiro todo dia" | platform | platform | none | ❌ FAIL | LANGFUSE_404 |
| TC3 | "Preciso que o Blu me envie automaticamente um resumo do estoque toda segunda-feira às 8h." | platform | **agenda** | none | ❌ FAIL | ROUTING_CONFIG |
| TC4 | "ativa as rotinas de acompanhamento do negócio pra mim" | platform | platform | none | ❌ FAIL | LANGFUSE_404 |
| TC5 | "Gostaria de configurar um alerta automático quando meu estoque estiver baixo." | platform | platform | none | ❌ FAIL | LANGFUSE_404 |

---

## 4. Root Cause Breakdown

| Root Cause | Count | TCs | Description |
|---|---|---|---|
| `ROUTING_CONFIG` | 2 | TC1, TC3 | Keywords "relatório"/"resumo"+"estoque" trigger pre-frontdesk routing to `agenda` in `service.py::detect_specialist_intent` |
| `LANGFUSE_404` | 3 | TC2, TC4, TC5 | `skill:plataforma:system` missing from Langfuse → loader returns empty system prompt → agent skips tool calls |

### ROUTING_CONFIG detail
`service.py` routing cascade intercepts before frontdesk:
- "relatório diário de vendas" → triggers scheduler/agenda keyword match
- "resumo do estoque toda segunda-feira" → triggers scheduler/agenda keyword match
- These messages never reach the frontdesk or the platform agent

**Root cause = code bug in `service.py`/`detect_specialist_intent`** — prompt fix won't solve it.

### LANGFUSE_404 detail
- `skill:plataforma:system` was NOT in Langfuse (confirmed via HTTP audit)
- The prompt DID exist as builtin `SKILL_PLATAFORMA` in `templates.py`, but the builtin fallback is disabled in the loader
- **FIX APPLIED:** Published `skill:plataforma:system` v1 to Langfuse with label `production` (2026-06-02)

---

## 5. Prompt Improvements Applied

### Created from scratch: `skill:plataforma:system` v1

**Before:** Not present in Langfuse (404). Builtin `SKILL_PLATAFORMA` in templates.py but unreachable due to loader behavior.

**After:** Published exact content of `SKILL_PLATAFORMA` builtin to Langfuse v1 with label `production`.

Key sections:
```
## Tool Rules
1. listar_rotinas_catalogo — Call FIRST before any routine creation
2. criar_rotina — Call ONLY after explicit user confirmation
3. definir_meta — Call ONLY after explicit user confirmation
...

## Constraints
- NEVER create routines or goals without explicit user confirmation
- NEVER skip listing existing items before creating

## Output Format
- Present the plan in 2–3 plain-language lines
- Ask: "Confirma a criação?" — wait for confirmation
```

**No additional modifications made** — the builtin prompt was already well-structured with XML-style sections, tool rules, constraints, and confirmation gates.

---

## 6. Manual Fixes Needed (Code)

### P0 — Routing keyword conflict in `service.py`

**File:** `services/agent_api/src/agent_api/core/service.py`  
**Function:** `detect_specialist_intent()` (pre-frontdesk routing cascade)

**Problem:** Keywords like "relatório", "resumo", "agenda", "semana" inside scheduling contexts are being matched for `agenda` agent before the frontdesk can evaluate platform-routing intent.

**Investigation needed:**  
1. Inspect `_TAG_MAP`/`_DOMAIN_RULES` in `nodes.py` for keywords that overlap platform vs agenda domains
2. Check `detect_specialist_intent` logic for "relatório" → scheduler match
3. Possible fix: add negative lookahead for "rotina" / "automatizar" keywords to exclude from agenda routing OR add platform as higher-priority rule

**This is not a prompt fix** — messages never reach the platform prompt.

### P1 — Keyword gaps in `_SLUG_ALIASES` or routing

Ensure keywords like "ativar rotina", "configurar rotina automática", "relatório automático" resolve to `platform` in `_SLUG_ALIASES` and not to `agenda`.

---

## 7. Re-Run Results

| TC | 1st Run Agent | Re-Run Agent | Consistent? |
|---|---|---|---|
| TC1 | agenda | agenda | ✅ Deterministic |
| TC3 | agenda | agenda | ✅ Deterministic |

Both re-runs confirm the routing failure is deterministic (not flaky). Root cause is pre-frontdesk routing, not LLM variability.

---

## 8. Next Recommended Actions

1. **[P0 — Code]** Investigate `service.py::detect_specialist_intent` — fix keyword routing so "relatório automático", "resumo + estoque" don't trigger `agenda`. Platform routines involve scheduling language, so some overlap is expected; add disambiguation.
2. **[P0 — Validate]** Restart `blu_agent_api` container to pick up newly published `skill:plataforma:system` prompt, then re-run TC2/TC4/TC5 to verify tool calls now happen.
3. **[P1 — Code]** Check `_SLUG_ALIASES` in `common_module.py` — add "relatório automático" / "automação de relatório" → "platform" aliases.
4. **[P1 — Monitor]** After code fix, confirm `criar_rotina` tool is called AND confirmation gate is respected (HITL pattern).
5. **[P2 — Prompt]** After routing is fixed, evaluate whether `skill:plataforma:system` v1 triggers proper elicitation sequence before tool calls.
6. **Continue to 2.4** (`platform_ops / definir_meta`) after resolving the routing P0.
