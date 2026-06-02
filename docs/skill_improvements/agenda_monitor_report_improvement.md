# Skill Improvement Report: agenda_monitor_report
**Date:** 2026-05-30T01:15:00
**Round:** 1

## What Changed

### Before (v1 — Portuguese, minimal structure)
- Written entirely in Portuguese (violates English-prompt convention)
- No explicit Trigger section — unclear when frontdesk routes here
- No Architecture section
- No Tool Rules — didn't state that no tools are needed (routine skill pattern)
- Constraints: implicit only (word limit)
- Output Format: vague ("relatório conciso") with no emoji/structure template
- No Pitfalls section
- Missing Jinja guards on optional variables (partial — some guards existed but not all)
- No explicit "traffic light" guidance beyond emoji mention

### After (v2 — English, full Hermes anatomy)
- Full English content following `# Skill / ## Trigger / ## Architecture / ## Tool Rules / ## Constraints / ## Output Format / ## Pitfalls` structure
- **Trigger**: explicit one-sentence activation condition tied to `agenda_monitor` routine
- **Architecture**: ASCII flow showing context injection → no-tool → narrative output
- **Tool Rules**: explicitly states NO tool calls; numbered steps for LLM execution
- **Constraints**: hard caps on turns ({{max_turns}}), action count (3 max), hallucination prevention, Jinja guards documented
- **Output Format**: concrete PT-BR message template with emoji structure, section guards, 300-word cap
- **Pitfalls**: 6 documented failure modes covering empty-variable hallucination, traffic-light inflation, date format pass-through, and turn-budget misuse

### Patterns borrowed from:
- `~/.hermes/skills/software-development/blu-skills-development/SKILL.md` — L3 routine skill pattern (no tool calls, `required_tool_names=[]`, Jinja guards for all optional vars)
- `~/.hermes/skills/software-development/blu-prompt-engineering/SKILL.md` — Rich Agent Prompt Anatomy (XML-tagged sections, confirmation gates, Output Format with concrete templates)
- Hermes skill anatomy: Trigger → Architecture → Tool Rules → Constraints → Output Format → Pitfalls

---

## SkillDefinition Suggestions (not auto-applied)

- **description**: Current is adequate but could be more routing-precise:
  > *Suggested:* `"Generate a scheduled agenda health snapshot (overdue follow-ups, upcoming meetings, contact gaps, priority actions) for the agenda_monitor routine. Read-only — no tool calls, context injected by routine engine."`
- **required_tool_names**: `[]` is correct — this is a pure narrative skill. No changes needed.
- **max_turns**: `3` is acceptable but `2` would be more appropriate — with no tools and all context pre-injected, 1 LLM turn should always suffice. Reducing to `2` adds a safety margin without over-allocating.
  > *Suggested:* `max_turns=2`
- **tags**: Current tags `["routines", "agenda", "scheduling", "monitor", "report", "alert"]` are good English tags. One improvement: ensure `"agenda"` tag is present so the agent with domain tag `"agenda"` can match this skill via tag intersection.
  > *Verified:* `"agenda"` tag is already present. ✅

---

## New Skills Suggested

| Name | Description | Domain Tag | Agent |
|------|-------------|------------|-------|
| `agenda_conflict_detector` | Detect scheduling conflicts in upcoming calendar (double-bookings, back-to-back meetings with travel time, overlapping priorities) and suggest resolution | `agenda` | agenda |
| `followup_priority_ranker` | Rank overdue follow-ups by business impact (deal size × days overdue × client tier) and suggest optimal contact order | `agenda` | crm / agenda |
| `meeting_prep_brief` | Generate a pre-meeting brief with client history, recent interactions, open action items, and suggested talking points | `agenda` | agenda |

---

## New Tools Suggested

| Name | Description | Skills that would use it |
|------|-------------|--------------------------|
| `get_agenda_snapshot` | Fetch upcoming meetings, overdue follow-ups, and client contact gaps from calendar + CRM integrations in a single structured call | `agenda_monitor_report`, `meeting_prep_brief`, `agenda_conflict_detector` |
| `get_followup_list` | Query CRM/task system for overdue follow-ups filtered by client tier, days overdue, and deal stage | `followup_priority_ranker`, `collection_messages`, `agenda_monitor_report` |
| `calendar_conflict_check` | Given a list of calendar events, detect scheduling conflicts and return structured conflict report | `agenda_conflict_detector` |

---

## Langfuse Prompt Published
- **Prompt name:** `skill:agenda_monitor_report:system`
- **Version:** 2
- **Labels:** `["production"]`
- **Tags:** `["skill", "agenda_monitor_report", "blu", "auto-improved"]`
- **Status:** ✅ Published
