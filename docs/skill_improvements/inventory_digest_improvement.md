# Skill Improvement Report: inventory_digest
**Date:** 2026-05-30T07:00:00
**Round:** 1

## What Changed

### Before (fallback template — Portuguese, minimal structure)
- Single-language PT-BR prompt with basic instructions
- No trigger condition definition
- No explicit output format (just "max 300 words with 3 sections")
- No pitfalls or constraint section
- No traffic-light consistency rule
- Variables listed inline without Jinja guards
- No mention of what data sources NOT to fabricate

### After (Langfuse v2 — English, full anatomy)
- Added explicit **Trigger** section: one-sentence routing condition
- Added **Architecture** block clarifying the no-tool / context-injection pattern
- Added **Tool Rules** with numbered steps mapping each variable to its purpose
- Added **Constraints** block: max_turns, no-tool-calls rule, no-threshold-elicitation rule, Jinja guards mandate
- Added detailed **Output Format** with exact section headers, emoji markers, conditional rendering instructions per section
- Added **Pitfalls** section covering 6 known LLM failure modes (generic output, threshold elicitation, ignoring cost anomalies, hallucinating suppliers, traffic light inconsistency, turn waste)
- All content written in English (per platform convention for new prompts)

### Patterns Borrowed From
- `~/.hermes/skills/software-development/blu-skills-development/SKILL.md` — L3 routine skill anatomy, Jinja guard mandate, no-tool pattern, max_turns=2-3 for narrative skills
- `~/.hermes/skills/software-development/blu-prompt-engineering/SKILL.md` — Rich agent prompt anatomy (XML sections), confirmation-gate pattern, output format declaration style, pitfalls structure

## SkillDefinition Suggestions (not auto-applied)

- **description**: Current is good. Could add "Emits 🟢/🟡/🔴 overall status and up to 3 prioritised actions." for richer planner context.
- **required_tool_names**: `[]` is correct — this is a routine narrative skill; context is injected by routine engine. No change needed.
- **max_turns**: `3` is appropriate for narrative generation. Could reduce to `2` given the skill should produce final output in turn 1. Recommend keeping `3` for buffer.
- **tags**: Current tags `["routines", "procurement", "monitor", "report", "alert"]` are all in English ✅. Suggest adding `"narrative"` to align with other routine skill tags pattern. Consider renaming `"monitor"` to `"digest"` since the skill produces a digest artifact, not a live monitor.

## New Skills Suggested

| Name | Description | Domain Tag | Agent |
|------|-------------|------------|-------|
| `reorder_suggestion` | Generate automated reorder suggestions based on stock levels, lead times, and historical consumption — outputs a ranked list of purchase orders to place | `procurement` | compras / procurement agent |
| `supplier_scorecard` | Produce a period-based supplier performance scorecard: on-time delivery rate, price variance, quality incidents | `procurement` | compras / procurement agent |
| `stock_movement_digest` | Summarise stock movements (entries, exits, adjustments) for a period — complements inventory_digest with flow analysis instead of snapshot | `procurement` | compras / procurement agent |

## New Tools Suggested

| Name | Description | Skills that would use it |
|------|-------------|--------------------------|
| `get_inventory_alerts` | Fetch items below `estoque_minimo` from the DB, with current qty and supplier info | `inventory_digest`, `reorder_suggestion` |
| `get_open_purchase_orders` | Query open/pending POs with supplier, expected delivery date, and delay flag | `inventory_digest`, `supplier_scorecard` |
| `get_cost_anomalies` | Detect items where latest unit cost deviates >10% from 3-month moving average | `inventory_digest`, `supplier_scorecard` |
| `dispatch_rfq_whatsapp` | Send Request for Quotation via WhatsApp to a supplier contact (already listed in confirmation-gate tools list — confirm it's wired to procurement agent) | `reorder_suggestion`, `fornecedores` |

## Langfuse Prompt Published
- Prompt name: `skill:inventory_digest:system`
- Labels: `["production"]`
- Version: 2 (updated from v1)
- Status: ✅ Published
