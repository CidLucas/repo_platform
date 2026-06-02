<!-- Last snapshot: 2026-06-02T18:16:53Z | Source: Langfuse v4 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/agenda.md -->

<!-- Last snapshot: 2026-06-02T18:01:49Z | Source: Langfuse v4 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/agenda.md -->

<!-- Last snapshot: 2026-06-02T17:46:15Z | Source: Langfuse v4 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/agenda.md -->

# Agent Audit: agenda
**Date**: 2026-06-02
**Sync Status**: IN_SYNC (agent prompt) + SYNCED (3 skill templates updated)
**Overall Score**: 4/5

## Current Prompt (from Langfuse production, v4)
```
You are the **Agenda Specialist** of **{{ nome_empresa }}** — responsible for calendar management, meeting scheduling, and task tracking via Monday.com. Always respond in the user's language.

{{ company_profile }}

<Instructions>
- Manage the full scheduling cycle: create, edit, and cancel events in Google Calendar.
- Query Monday.com boards to surface tasks, deadlines, and project statuses.
- Update Monday.com items: statuses, dates, and assignees.
- Prepare meeting briefs with relevant context before scheduled meetings.
- Always confirm time, date, and participants before creating an event.
- Detect calendar conflicts and proactively suggest alternative slots.
- Use execute_sql (read-only) for data-backed scheduling insights — e.g., busiest days, meeting frequency trends.
</Instructions>

<Tool Rules>
`query_calendar`: use to read existing events, check availability, and detect conflicts before proposing new slots. Always call before creating an event.

`google_calendar_write`: use ONLY after explicit user confirmation. Required fields: title, start_datetime, end_datetime. Attendees are optional.

`import_spreadsheet_schedule`: use when the user wants to bulk-import events from a spreadsheet. Confirm source and column mapping before executing.

`monday_list_boards`: use to discover available boards before querying items. Call first if the board name is unknown.

`monday_list_items`: use to retrieve tasks and their current status from a known board.

`monday_create_item`: use to create a new task or deliverable. Always confirm name, board, and due date with the user before executing.

`monday_update_item_status`: use to mark progress on an existing item. Requires explicit instruction from the user.

`monday_get_board_summary`: use to give the user an overview of a board's progress (counts by status).

`monday_get_item_updates`: use to fetch the activity log or comments on a specific item.

`monday_summarize_board`: use to generate a narrative summary of board activity for briefing purposes.

`execute_sql`: use (read-only) for scheduling analytics — e.g., meeting frequency trends, team workload distribution. Always prefix tables with `analytics_v2.`. Never INSERT/UPDATE/DELETE.

`meeting_brief`: use to compile participant context and relevant background before a meeting. No external writes.
</Tool Rules>

<Constraints>
- Do not analyze financial or customer data — redirect to the appropriate specialist.
- Always confirm before creating or canceling any calendar event or Monday item.
- Maximum 5 turns per scheduling task.
- Do not reference tool names directly in user-facing messages.
</Constraints>
```

## Skills Map
| Skill | Score | Key Issues |
|-------|-------|------------|
| `calendar` | 4/5 | Local template was stale (PT-BR vs Langfuse EN with tool parameter docs). **Synced.** |
| `meeting_brief` | 3/5 | Local template was minimal PT-BR, Langfuse v2 adds pitfall guards & explicit anti-hallucination rules. **Synced.** |
| `agenda_monitor_report` | 3/5 | Local template was a bare 10-line PT-BR prompt; Langfuse v3 is a full structured spec with pitfalls and output format. **Synced.** |
| `agenda_ops` | 2/5 | Exists locally only — no Langfuse production prompt found (404). `required_tool_names=[]` needs populate. |

## Tool Coverage
- **Present (agent prompt)**: `query_calendar`, `google_calendar_write`, `import_spreadsheet_schedule`, `monday_list_boards`, `monday_list_items`, `monday_create_item`, `monday_update_item_status`, `monday_get_board_summary`, `monday_get_item_updates`, `monday_summarize_board`, `execute_sql`, `meeting_brief`
- **Missing from skills.py `required_tool_names`**: `agenda_monitor_report` and `meeting_brief` skills have `required_tool_names=[]` — acceptable since they are synthesis-only (no live tool calls). `calendar` skill correctly lists `query_calendar`, `google_calendar_write`, `import_spreadsheet_schedule`.
- **Unused**: `execute_sql` is referenced in agent prompt but not tied to any explicit skill; covered implicitly by `sql_analytics` transversal skill if registered.

## Improvements Applied
| File | Change | Reason |
|------|--------|--------|
| `templates.py` | Updated `SKILL_AGENDA_MONITOR_REPORT` content | Synced to Langfuse v3: structured spec with pitfall guards, explicit output format, anti-hallucination rules |
| `templates.py` | Updated `SKILL_MEETING_BRIEF` content | Synced to Langfuse v2: added pitfall section, explicit hallucination guards, `company_profile` optional variable |
| `templates.py` | Updated `SKILL_CALENDAR` content | Synced to Langfuse v1: added tool parameter signatures, São Paulo timezone default, workflow steps |

## Remaining Issues
**P0:** none

**P1:**
- `agenda_ops` skill has no Langfuse production prompt (404). Should either be published to Langfuse or removed if superseded by `calendar` + `sql_analytics` combo.
- `agenda_monitor_report` and `meeting_brief` skills have `required_tool_names=[]` — acceptable for routine/synthesis skills but should be documented explicitly with a comment in skills.py to avoid future confusion.

**P2:**
- Agent prompt could benefit from a `<Handoffs>` section listing which agents to redirect to for financial (financeiro), customer (crm) and procurement (compras) queries.
- `execute_sql` in agent prompt references `analytics_v2.` prefix but no explicit sql_analytics skill is mapped for this agent — worth registering.

## Agent Logical Map
The **Agenda Specialist** operates as the scheduling hub of the Blu platform. Its typical flow:

1. **Intent detection**: User asks about calendar, meetings, tasks, or Monday.com boards.
2. **Read-first pattern**: Always calls `query_calendar` before any write to detect conflicts.
3. **Confirmation gate**: Explicitly confirms event details with user before executing any write (google_calendar_write, monday_create_item).
4. **Monday.com path**: If task/project related, discovers boards via `monday_list_boards`, queries items, then updates or creates items only on explicit instruction.
5. **Meeting brief path**: For pre-meeting prep, compiles participant context + history via `meeting_brief` skill (synthesis only, no writes).
6. **Analytics path**: For scheduling trends/analytics, uses `execute_sql` (read-only, `analytics_v2.` prefix).

**Routine integrations:**
- `agenda_monitor` routine → triggers `agenda_monitor_report` skill → returns PT-BR health snapshot.
- `meeting_brief` can be triggered by scheduled routines or direct user requests.

**Handoffs:**
- Financial data queries → `financeiro` agent
- Customer/CRM data → `crm` agent
- Procurement tasks → `compras` agent
