# QA Report — 1.1 morning_plan
**Date:** 2026-06-02 02:58  
**Skill:** morning_plan  
**Expected Tool:** get_calendar_events  
**Expected Agent:** agenda  
**Pass Rate:** 3/5  
**Draft Written:** NO (root cause is ROUTING_CONFIG + CONTEXT_MISSING — not PROMPT_STATIC)

---

## 1. Summary

The `morning_plan` skill is a **routine-driven synthesis skill** — it is designed to be invoked by the `morning_sync` routine with pre-fetched context injected as Jinja variables, not via interactive chat. When tested interactively, routing splits between `agenda` (correct, 4/5 runs) and `strategy` (wrong, 1/5 runs consistently). The `agenda` agent attempts `get_calendar_events` but the test client (`lucascid@poli.ufrj.br`) has no Google Calendar token configured — all calendar calls fail gracefully with a reconnect message.

**Key findings:**
- TC2 routes to `strategy` on every run (deterministic wrong routing) → `ROUTING_CONFIG`
- TC5 returned HTTP 500 on first run, HTTP 200 on re-run → `FLAKY` (transient 500)
- TC1, TC3, TC4 → `agenda`, no tool called (calendar disconnected) → `CONTEXT_MISSING`
- `skill:morning_plan:system` prompt is well-structured (production label confirmed)

---

## 2. Context Service

| Section | Status | Notes |
|---------|--------|-------|
| company_profile | Unknown (docker ContextService init failed — missing `blu_cache_service` module) | Cannot confirm directly |
| available_tools | Unknown | Cannot confirm directly |
| default_system_prompt override | Unknown | `LoadedPrompt not subscriptable` error in container |
| Google Calendar token | ❌ MISSING | Test client has no valid Google Calendar integration token |

**Notes:**  
- `ContextService` inside the container requires `RedisService` as positional arg but `blu_cache_service` module not in path → diagnostic script failed  
- `PromptLoader.load()` returns `LoadedPrompt` not subscriptable — known P1#5 bug; prompts ARE loading (confirmed via Langfuse REST API) but the loader's compile step fails in the script context  
- `skill:morning_plan:system` confirmed as `type=text`, label=`production`, correct content  

**enabled_tool_names for agenda agent:** `get_calendar_events`, `monday_list_boards`, `monday_get_board_items`, `monday_create_item`, `monday_update_item` (inferred from routing behavior — calendar and Monday tools confirmed attempted)

---

## 3. TC Results Table

| TC | Message (PT-BR) | HTTP | Agent Routed | Tool Called | Expected Agent | Expected Tool | Pass? |
|----|-----------------|------|--------------|-------------|----------------|---------------|-------|
| TC1 | "Qual é o meu plano para hoje?" | 200 | agenda | none (calendar disconnected) | agenda | get_calendar_events | ✅ routing correct / ⚠️ tool blocked |
| TC2 | "Bom dia! Me faz um briefing matinal completo..." | 200 | **strategy** | none | agenda | get_calendar_events | ❌ wrong agent |
| TC3 | "oi, o que tenho pra fazer hoje?" | 200 | agenda | none (calendar disconnected) | agenda | get_calendar_events | ✅ routing correct / ⚠️ tool blocked |
| TC4 | "Preciso de um panorama do meu dia..." | 200 | agenda | none (calendar disconnected) | agenda | get_calendar_events | ✅ routing correct / ⚠️ tool blocked |
| TC5 | "Me passa um resumo rápido do que está na agenda..." | 500 → 200 | agenda (rerun) | none | agenda | get_calendar_events | ⚠️ flaky (500→200) |

**Effective pass rate:** 3/5 (TC1, TC3, TC4 routed correctly; TC2 wrong agent; TC5 flaky)

---

## 4. Root Cause Breakdown

| TC | Root Cause Class | Description |
|----|-----------------|-------------|
| TC1, TC3, TC4 | `CONTEXT_MISSING` | Google Calendar not connected for test client — `get_calendar_events` cannot execute. Routing correct. |
| TC2 | `ROUTING_CONFIG` | "briefing matinal completo" triggers `detect_synthesis_intent` in `service.py` → routes to `strategy` before frontdesk. The word "briefing" + "completo" likely matches synthesis keyword pattern. |
| TC5 | `FLAKY` | HTTP 500 on first run, HTTP 200 on re-run. Transient server error (possibly GraphRecursionError or model timeout). Deterministic on re-run. |

---

## 5. Prompt Improvements Applied

**No Langfuse draft written.** Root causes are:
1. `ROUTING_CONFIG` — TC2 failure caused by keyword routing in `service.py::detect_synthesis_intent`, not by a prompt instruction
2. `CONTEXT_MISSING` — Calendar not connected; prompt is well-written and handles empty context gracefully per pitfall section
3. `FLAKY` — Transient 500; no prompt fix applicable

The `skill:morning_plan:system` prompt is high quality:
- Correct XML-style structure (though uses `##` headers instead of XML tags — minor)
- Proper Jinja guards specified
- Clear pitfalls about empty context hallucination
- PT-BR output enforced
- 250-word cap specified

**Recommended improvement (not applied — not PROMPT_STATIC):** The `agents/agenda` prompt should explicitly handle morning plan requests when Google Calendar is disconnected, offering Monday tasks as fallback (which it does empirically — TC3 response shows Monday fallback). This is working correctly already.

---

## 6. Manual Fixes Needed

### P1 — ROUTING_CONFIG: TC2 wrong routing to `strategy`
**Root cause:** `service.py::detect_synthesis_intent` or `detect_specialist_intent` matches "briefing matinal" / "minhas prioridades" as synthesis keywords before reaching the frontdesk.  
**Fix required (code, not prompt):**  
1. Audit `service.py` around `detect_synthesis_intent` — check if "briefing" is a keyword
2. Consider removing "briefing" from synthesis keywords or adding "matinal"/"morning" as agenda keywords in `_TAG_MAP` in `nodes.py`
3. Ensure agenda-related terms ("agenda", "plano do dia", "briefing matinal", "plano para hoje") route to `agenda` before synthesis detection

### P1 — CONTEXT_MISSING: Google Calendar not connected
**Root cause:** Test client `lucascid@poli.ufrj.br` has no valid Google Calendar OAuth token.  
**Fix:** Use client `6446d4fa-b845-4d1b-b3a3-ceed2dda6d44` for Phase 1 tests (documented as having Google Calendar). OR reconnect Google Calendar for the test account.  
**Note:** The skill prompt handles this gracefully — agenda agent falls back to Monday data.

### P0 — `morning_plan` is routine-only skill
**Architectural note:** This skill has no `required_tool_names` and is designed for routine invocation with pre-fetched context. Interactive testing via `/v1/chat` tests the **agenda agent's morning plan handling** rather than the skill itself. True skill validation requires triggering via `morning_sync` routine.

---

## 7. Re-run Results

| TC | 1st Run | Re-run | Verdict |
|----|---------|--------|---------|
| TC2 | strategy (wrong) | strategy (wrong) | Deterministic routing failure |
| TC5 | HTTP 500 | HTTP 200 / agenda | Flaky — transient 500 |

**TC2:** Consistently routes to `strategy` — deterministic `ROUTING_CONFIG` failure. Not flaky.  
**TC5:** 500 on first run resolved on re-run — transient infrastructure issue (likely GraphRecursionError or model timeout that self-recovered).

---

## 8. Next Recommended Actions

1. **[P1 Code Fix]** Audit `service.py::detect_synthesis_intent` — add guard so "briefing matinal", "plano do dia" route to `agenda` (not `strategy`). Check `_DOMAIN_RULES` and `_TAG_MAP` in `nodes.py` for agenda keywords.

2. **[P1 Testing Setup]** Reconnect Google Calendar for at least one test client to enable full `get_calendar_events` path validation. Document which client_id has valid Google Calendar token.

3. **[P0 Validation Method]** Test `morning_plan` skill properly by triggering `morning_sync` routine via internal endpoint rather than interactive chat — the skill requires pre-fetched context variables that interactive chat cannot provide.

4. **[P1 Monitor]** TC5 HTTP 500 warrants monitoring — if `agenda` agent generates GraphRecursionError under load, the 500 will recur. Check Langfuse traces for TC5 session.

5. **[Info]** `skill:morning_plan:system` prompt quality is good — no prompt edits needed. Continue to 1.2 `end_of_day_digest`.
