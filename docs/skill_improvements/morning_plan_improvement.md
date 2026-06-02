# Skill Improvement Report: morning_plan
**Date:** 2026-05-29T22:10:00
**Round:** 1

## What Changed

### Before (v1 — fallback template in templates.py)
- Written entirely in **Portuguese** (the system prompt itself was PT-BR), which conflicts with the "prompt in English" policy.
- No formal `## Trigger` block — the use-case was implicit.
- Instructions were embedded as an inline numbered list without clear section labels.
- No explicit pitfall section or constraint block.
- Word limit mentioned only at the end of the template (200 words).
- No guard described for completely empty context (all Jinja vars blank).
- No explicit language enforcement instruction for the LLM.

### After (v2 — Langfuse production)
- Prompt now fully in **English** following platform policy.
- Structured with canonical sections: `Trigger`, `Architecture`, `Tool Rules`, `Constraints`, `Output Format`, `Pitfalls`.
- `Trigger` clearly states routing condition (morning_sync routine OR explicit user request).
- `Architecture` documents the no-tool-call pattern (pure synthesis from pre-fetched context).
- `Tool Rules` explicitly lists the 3 rules (no tools, handle empty context, single response).
- `Constraints` formalises max_turns with `{{max_turns}}`, enforces PT-BR output, and mandates Jinja guards.
- `Output Format` specifies exact emoji-labelled sections with clear omission rules (Alertas section omitted when empty).
- `Pitfalls` added 5 known failure modes: empty context hallucination, over-verbosity, missing urgency ranking, wrong language default, and section bleed.

### Patterns borrowed from
- **Hermes productivity/project-planning-framework skill**: trigger-condition one-liner, structured output with labelled sections.
- **Hermes google-workspace skill**: explicit guard-and-fallback pattern for missing context variables.
- **Hermes docs pattern analysis**: Trigger → Architecture → Tool Rules → Constraints → Output Format → Pitfalls canonical structure.

---

## SkillDefinition Suggestions (not auto-applied)

- **description**: Current description is good but could emphasise the "no-tool synthesis" nature more clearly for planner routing. Suggested: _"Pure synthesis skill: generates a prioritised daily plan narrative from pre-fetched KPIs, calendar agenda, pending approvals, and integration alerts injected by the morning_sync routine engine. No tool calls."_
- **required_tool_names**: `[]` is correct — this skill intentionally makes no tool calls.
- **max_turns**: `2` is appropriate for a single-shot synthesis skill. Could be reduced to `1` if the routine engine never expects back-and-forth (marginal gain in latency/cost).
- **tags**: Current tags `["routines", "morning", "planning", "narrative"]` are good English tags. Consider adding `"briefing"` for better frontdesk routing on user queries like "give me my briefing".

---

## New Skills Suggested

| Name | Description | Domain Tag | Agent |
|------|-------------|------------|-------|
| `daily_priorities_update` | Allows the user to interactively adjust the day's priorities mid-day (re-rank, add, remove items) after morning_plan is delivered. | `planning` | frontdesk / morning_sync |
| `kpi_alert_triage` | When integration alerts arrive outside the morning window, quickly triages severity and recommends immediate action vs. defer. | `monitoring` | monitor_agent |
| `agenda_conflict_detector` | Scans the calendar context for scheduling conflicts, back-to-back meetings, or missing prep blocks and flags them. | `agenda` | morning_sync / agenda_agent |

---

## New Tools Suggested

| Name | Description | Skills that would use it |
|------|-------------|--------------------------|
| `get_morning_context` | Fetches and bundles KPIs, calendar events, pending approvals, and integration alerts into a single structured payload for injection into morning_plan. | `morning_plan`, `daily_priorities_update` |
| `urgency_scorer` | Scores a list of pending items by impact × urgency using a lightweight heuristic model, returning a ranked list. | `morning_plan`, `kpi_alert_triage`, `end_of_day_digest` |

---

## Langfuse Prompt Published
- **Prompt name:** `skill:morning_plan:system`
- **Version:** 2
- **Labels:** `["production"]`
- **Tags:** `["skill", "morning_plan", "blu", "auto-improved"]`
- **Status:** ✅ Published (HTTP 201)
