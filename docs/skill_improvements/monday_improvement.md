# Skill Improvement Report: monday
**Date:** 2026-05-30T08:00:00
**Round:** 1

## What Changed

### Before
- Prompt written entirely in Portuguese (violates ENGLISH-prompt rule)
- No explicit `## Trigger` section — activation conditions buried in instructions
- No `## Architecture` overview
- No `## Pitfalls` section
- Numbered instruction steps existed but lacked tool-routing decision logic (narrative vs metrics distinction)
- No Jinja guard for `company_profile`
- `nome_empresa` referenced but `max_turns` not included as a variable
- Output format described inline, not in a dedicated section

### After
- Full structured prompt in ENGLISH following the canonical 6-section schema
- Explicit **Trigger** (one-sentence routing condition)
- **Architecture** block shows the data-flow at a glance
- **Tool Rules** numbered 1–7 with explicit decision branches (narrative vs metrics, include_updates flag)
- Required fields listed per tool for fast LLM lookup
- **Constraints** section includes `{{max_turns}}` variable and Jinja guard `{% if company_profile %}`
- **Output Format** section with explicit table structure and confirmation templates
- **Pitfalls** section with 6 known failure modes (board name ambiguity, skipped confirmation gate, over-fetching, stale board_id, include_updates performance, board-specific status values)

### Patterns borrowed from
- Hermes productivity skill patterns (trigger sentence, architecture block, pitfalls section)
- Existing scheduler agent template in `templates.py` (confirmation gate patterns, tool routing logic)
- Prior skills in this round (reconciliation_report, sql_analytics) for output format table structure

---

## SkillDefinition Suggestions (not auto-applied)

- **description**: Current description is good but could mention "project management" more explicitly for routing. Suggested: `"Manage Monday.com boards: query and create items, update statuses, retrieve updates, and generate board summaries and briefings for project management."`
- **required_tool_names**: All 7 tools look appropriate. Consider adding a future `monday_search_items` tool (by keyword/assignee) — currently missing, forces users to list all items.
- **max_turns**: 5 is appropriate. Board resolution + read op = 2 turns; write ops with confirmation = 3 turns. No change needed.
- **tags**: Current tags `["monday", "tasks", "project-management"]` are valid English. Consider adding `"boards"` for more precise routing when multiple project-management tools exist.

---

## New Skills Suggested

| Name | Description | Domain Tag | Agent |
|------|-------------|------------|-------|
| `asana` | Manage Asana projects and tasks: list projects, create/update tasks, check team workload, set deadlines and assignees | `project-management` | scheduler_agent / frontdesk |
| `linear` | Manage Linear issues, cycles (sprints), and team backlogs: create issues, update status, list cycles, check team capacity | `project-management` | scheduler_agent / frontdesk |
| `project_status_rollup` | Cross-tool project status rollup: aggregates Monday, Asana, and Linear into a unified project dashboard | `project-management` | analytics_agent |

---

## New Tools Suggested

| Name | Description | Skills that would use it |
|------|-------------|--------------------------|
| `monday_search_items` | Search Monday.com items by keyword, assignee, or status across all boards | `monday` |
| `monday_move_item` | Move an item from one group/board to another | `monday` |
| `monday_add_update` | Post a comment/update on a Monday.com item | `monday` |
| `cross_pm_status` | Query status across Monday + Asana + Linear simultaneously and return unified JSON | `monday`, `asana`, `linear`, `project_status_rollup` |

---

## Langfuse Prompt Published
- Prompt name: `skill:monday:system`
- Labels: `["production"]`
- Version: 7
- Status: SUCCESS (HTTP 201)
