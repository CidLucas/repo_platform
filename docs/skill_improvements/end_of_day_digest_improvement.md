# Skill Improvement Report: end_of_day_digest
**Date:** 2026-05-29T22:24:07Z
**Round:** 1

## What Changed

### Before (template in templates.py)
- Written in **Portuguese** — violates the ENGLISH-only prompt rule.
- No explicit trigger condition defined.
- No architecture description — unclear input/output contract.
- No pitfalls section.
- No output format specification (just vague "max 150 words").
- Variables (`tarefas_concluidas`, `itens_abertos`, `kpis_do_dia`) existed but weren't documented with Jinja guards in the instructions.
- No anti-hallucination constraint (LLM could invent tasks).

### After (published to Langfuse)
- Written entirely in **English** (prompt content), with PT-BR mandated only for user-facing output.
- Clear **Trigger** sentence.
- Explicit **Architecture** block: input variables → synthesis → output.
- **Tool Rules** section clarifying: no external tools, max_turns=2, single-pass generation.
- **Constraints** section with Jinja guard examples and explicit anti-hallucination rules.
- **Output Format** with exact emoji/structure spec so the LLM produces consistent digests.
- **Pitfalls** section covering: empty-variable hallucination, lazy score defaults, section bloat.

### Patterns borrowed from:
- `project-planning-framework` (Hermes local skill): trigger sentence pattern, numbered steps in tool rules.
- `notion` skill (Hermes local): variable-guard documentation pattern, fallback behavior specification.
- Hermes skill best practices: Trigger / Architecture / Tool Rules / Constraints / Output Format / Pitfalls structure.

---

## SkillDefinition Suggestions (not auto-applied)

- **description:** Suggest expanding to: `"Synthesize the day's completed tasks, open items, and KPI data into a structured, motivational end-of-day digest. Activated by the EOD routine or on-demand by the business owner."` — adds more context for frontdesk routing.
- **required_tool_names:** Currently `[]` — correct. No tools needed for pure narrative generation. Consider adding a `get_day_summary` tool in the future if day data is fetched dynamically rather than injected.
- **max_turns:** `2` is appropriate for a single-pass generation skill. No change needed.
- **tags:** Current tags `["routines", "digest", "narrative", "eod"]` are good. Consider adding `"daily"` for disambiguation from `weekly_summary`.

---

## New Skills Suggested

| Name | Description | Domain Tag | Agent |
|------|-------------|------------|-------|
| `standup_brief` | Generate a concise morning standup summary from overnight events, blockers, and today's priorities — complements EOD digest | `routines` | morning/routines agent |
| `personal_wins_tracker` | Accumulate and periodically surface notable business wins for morale and investor reporting | `routines` | digest/narrative agent |
| `eod_slack_post` | Format and post the EOD digest directly to a configured Slack channel | `communication` | notification agent |

---

## New Tools Suggested

| Name | Description | Skills that would use it |
|------|-------------|--------------------------|
| `get_day_activity_summary` | Fetches completed CRM tasks, calendar events, and closed tickets from the day via API aggregation | `end_of_day_digest`, `morning_plan`, `weekly_summary` |
| `score_day` | Calculates an objective 1–10 day score from KPIs (tasks closed / goal, revenue / target, etc.) | `end_of_day_digest`, `weekly_summary` |
| `post_to_channel` | Posts a formatted message to Slack, Teams, or WhatsApp Business given a channel ID | `end_of_day_digest`, `collection_messages`, `followup_draft` |

---

## Langfuse Prompt Published

- **Prompt name:** `skill:end_of_day_digest:system`
- **Labels:** `["production"]`
- **Tags:** `["skill", "end_of_day_digest", "blu", "auto-improved"]`
- **Langfuse ID:** `96c31daa-abc0-433e-a0f6-29dfdb834a18`
- **Status:** ✅ Published (HTTP 201)
