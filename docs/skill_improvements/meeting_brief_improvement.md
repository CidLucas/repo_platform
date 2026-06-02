# Skill Improvement Report: meeting_brief
**Date:** 2026-05-29T23:44:55Z
**Round:** 1

## What Changed

### Before (templates.py fallback)
- Written entirely in Portuguese (`Você é o assistente de reuniões da...`)
- No explicit Trigger section — purpose was implicit
- No Constraints block — no hallucination guard, no word-limit enforcement
- No Pitfalls section
- Optional variables injected directly into the prompt body without explicit "not provided" fallback instructions
- No guidance on what to output when context is missing (LLM would fabricate)
- Architecture was implicit (no description of flow)
- Section headers were in Portuguese inside the system prompt

### After (new Langfuse prompt)
- Full English system prompt following the canonical Hermes skill structure
- Explicit **Trigger** sentence for frontdesk routing clarity
- **Architecture** block explaining the synthesis-only flow (no external tools)
- **Tool Rules** with numbered steps, making it clear no tool calls are needed and exactly what inputs map to what outputs
- **Constraints** block with hard word limit (450 words), explicit hallucination guard ("NEVER invent participant details"), and Jinja guards for all optional vars
- **Output Format** specifies exact 4-section structure with tone and language (PT-BR for user output)
- **Pitfalls** section covering: hallucination risk, section inflation, agenda ordering, missing metadata edge case, language mixing, and large participant count handling

### Patterns borrowed from
- `teams-meeting-pipeline` Hermes skill: trigger sentence pattern, decision-tree for missing data, explicit pitfall blocks with named failure modes
- Hermes skill structure standard: Trigger / Architecture / Tool Rules / Constraints / Output Format / Pitfalls
- Hermes docs skill patterns: numbered tool steps, constraint bullets with "NEVER" prefix, explicit output format specification

---

## SkillDefinition Suggestions (not auto-applied)

- **description:** Current is good. Could be slightly more specific: `"Produce a pre-meeting briefing document with participant profiles, business history, risks, and a prioritized agenda. Activates on any meeting prep or briefing request."`
- **required_tool_names:** Currently `[]` — correct, this skill is synthesis-only. No changes needed.
- **max_turns:** `3` is appropriate for a single-shot synthesis skill. Could be reduced to `2` (one user turn + one briefing response), but `3` gives buffer for clarifying the meeting context. Keep as is.
- **tags:** Current: `["routines", "agenda", "scheduling", "meeting", "briefing"]` — solid. Consider adding `"preparation"` for broader routing coverage. All tags are already in English ✅

---

## New Skills Suggested

| Name | Description | Domain Tag | Agent |
|------|-------------|------------|-------|
| `post_meeting_summary` | Generate a structured post-meeting summary with action items, decisions made, and next steps from raw notes or transcript | `meeting`, `productivity` | frontdesk / scheduled |
| `meeting_conflict_detector` | Scan the calendar for scheduling conflicts, double-bookings, or travel-time violations and suggest resolutions | `agenda`, `scheduling` | agenda agent |
| `participant_profile_builder` | Given a name or email, pull CRM + LinkedIn context to build a participant profile for briefings | `crm`, `meeting`, `research` | meeting_brief pre-step |

---

## New Tools Suggested

| Name | Description | Skills that would use it |
|------|-------------|--------------------------|
| `get_calendar_event_details` | Fetch full metadata for a calendar event (participants, location, agenda items, attachments) from Google Calendar / Outlook | `meeting_brief`, `post_meeting_summary`, `agenda` |
| `lookup_contact_history` | Given a contact name/email, return past interactions, deal history, and open tasks from CRM | `meeting_brief`, `collection_messages`, `followup_draft` |
| `fetch_meeting_transcript` | Pull transcript or recording from Teams/Meet for a given meeting ID | `post_meeting_summary`, `weekly_summary` |

---

## Langfuse Prompt Published

- **Prompt name:** `skill:meeting_brief:system`
- **Labels:** `["production"]`
- **Tags:** `["skill", "meeting_brief", "blu", "auto-improved"]`
- **Langfuse ID:** `1bff50ac-5ff8-453d-a399-4d0d88678220`
- **Status:** ✅ Published (HTTP 201)
