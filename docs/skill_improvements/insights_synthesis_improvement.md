# Skill Improvement Report: insights_synthesis
**Date:** 2026-05-30T07:15:00
**Round:** 1

## What Changed

### Before (fallback template — Portuguese, minimal)
```
Você é o analista estratégico da **{{ nome_empresa }}**.
Sua tarefa: sintetizar os insights do dia{% if periodo %} ({{ periodo }}){% endif %} em uma narrativa estratégica unificada.

{% if resumo_financeiro %}## Financeiro\n{{ resumo_financeiro }}{% endif %}
{% if resumo_clientes %}## Clientes\n{{ resumo_clientes }}{% endif %}
{% if resumo_compras %}## Compras\n{{ resumo_compras }}{% endif %}
{% if resumo_agenda %}## Agenda\n{{ resumo_agenda }}{% endif %}
```

**Problems identified:**
- No Trigger section — LLM had no anchor for when/why this skill is activated
- No Architecture description — no explicit note that this skill calls zero tools
- No Tool Rules — no numbered workflow steps for synthesis
- No Constraints — LLM could hallucinate metrics, omit sections, or drift language
- No Output Format — structure was implicit (just section headers, no narrative shape)
- No Pitfalls — known risks (hallucination, all-empty summaries, generic narrative) unmitigated
- Written in Portuguese — violates "prompts must be in English" standard
- `max_turns` variable not included in the prompt

### After (published to Langfuse — English, structured)
- **Trigger**: explicit one-sentence routing condition
- **Architecture**: ASCII flow diagram showing no tool calls, context injected upstream
- **Tool Rules**: numbered synthesis steps; lists all injected Jinja variables
- **Constraints**: max_turns enforced; hallucination prohibition; all-empty guard; language lock
- **Output Format**: exact PT-BR markdown template with emoji headers, section guards, prioritised action list
- **Pitfalls**: 7 named failure modes with explicit mitigations

### Patterns borrowed from
- `~/.hermes/skills/software-development/blu-skills-development/SKILL.md` — Hermes Skill Anatomy (Trigger → Architecture → Tool Rules → Constraints → Output Format → Pitfalls)
- `~/.hermes/skills/software-development/blu-prompt-engineering/SKILL.md` — Rich Agent Prompt Anatomy, Jinja guard patterns, optional variables pattern, confirmation-gating (n/a here but cross-domain signal section inspired by it)
- Hermes skill standard: one-sentence trigger, numbered tool steps, hard constraint bullets, exact output format declaration

## SkillDefinition Suggestions (not auto-applied)

- **description**: Current: *"Synthesise cross-domain insights from finance, clients, procurement, and agenda data into a unified strategic narrative. Used by daily_insights routine."* → Suggested: *"Synthesise cross-domain insights from finance, clients, procurement, and agenda summaries into a prioritised strategic narrative with action items. Activated by daily_insights routine."* (adds "prioritised" and "action items" to improve planner selection precision)
- **required_tool_names**: Current: `[]` → Keep as `[]`. Context is injected by the routine engine — no tools needed. ✅ Correct.
- **max_turns**: Current: `4` → Consider lowering to `2`. This is a pure LLM synthesis step (no tool calls, no retries needed). `max_turns=2` is the standard for narrative-only routine skills (see `morning_plan`). `4` is overly generous and may allow unnecessary LLM loops.
- **tags**: Current: `["routines", "synthesis", "strategy", "analysis", "narrative"]` → Suggested: `["routines", "synthesis", "strategy", "analysis", "narrative", "insights"]`. Add `"insights"` for better routing via `classify_skill_intent_node` (especially if an `insights` or `synthesis` agent is added). All tags are already in English ✅.

## New Skills Suggested

| Name | Description | Domain Tag | Agent |
|------|-------------|------------|-------|
| `weekly_insights_synthesis` | Same as `insights_synthesis` but oriented to 7-day windows; includes week-over-week delta highlighting for finance and client metrics | `synthesis` | synthesis agent |
| `risk_alert_synthesis` | Scans cross-domain summaries specifically for compound risk signals (e.g. revenue drop + churn + supplier delay) and emits a short alert narrative with severity level | `synthesis` | synthesis agent |
| `okr_progress_synthesis` | Synthesises progress toward company OKRs/goals from finance, client, and task data; maps each key result to a RAG status (🟢/🟡/🔴) | `strategy` | strategy agent |

## New Tools Suggested

| Name | Description | Skills that would use it |
|------|-------------|--------------------------|
| `get_cross_domain_summary` | Fetches pre-computed domain summaries (finance, clients, procurement, agenda) from the routine engine state store for a given `client_id` and `period`. Eliminates reliance on upstream injection when used interactively. | `insights_synthesis`, `weekly_insights_synthesis`, `risk_alert_synthesis` |
| `rank_action_items` | Takes a list of potential action items and returns a prioritised ranking based on urgency, business impact, and domain (uses a lightweight LLM classifier). | `insights_synthesis`, `okr_progress_synthesis` |

## Langfuse Prompt Published
- Prompt name: `skill:insights_synthesis:system`
- Labels: `["production", "latest"]`
- Version: 1
- Status: ✅ Published
