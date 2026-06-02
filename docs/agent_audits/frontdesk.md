<!-- Last snapshot: 2026-06-02T18:16:59Z | Source: Langfuse v24 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/frontdesk.md -->

<!-- Last snapshot: 2026-06-02T18:01:56Z | Source: Langfuse v24 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/frontdesk.md -->

<!-- Last snapshot: 2026-06-02T17:46:22Z | Source: Langfuse v24 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/frontdesk.md -->

<!-- Last snapshot: 2026-06-02T17:30:49Z | Source: Langfuse v24 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/frontdesk.md -->

<!-- Last snapshot: 2026-06-02T17:15:57Z | Source: Langfuse v24 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/frontdesk.md -->

<!-- Last snapshot: 2026-06-02T17:00:20Z | Source: Langfuse v24 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/frontdesk.md -->

<!-- Last snapshot: 2026-06-02T16:45:06Z | Source: Langfuse v24 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/frontdesk.md -->

<!-- Last snapshot: 2026-06-02T16:29:05Z | Source: Langfuse v24 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/frontdesk.md -->

# Agent Audit: frontdesk
**Date**: 2026-06-02
**Sync Status**: SYNCED (local was v20 PT-BR; updated to v24 EN from Langfuse)
**Overall Score**: 4.5/5

## Current Prompt (from Langfuse production)

```
You are the entry-point assistant of **{{ nome_empresa }}**. Always respond in the user's language.

{% if company_profile %}
## Company Context
{{ company_profile }}
{% endif %}

{% if sql_schema_context %}
## Database Schema
{{ sql_schema_context }}
{% endif %}

{% if available_agents %}
## Available Specialists
{{ available_agents }}
{% endif %}

<Decision Tree>
For each message, walk the steps **in order** and execute the first that applies:
...
(full prompt — see Langfuse agents/frontdesk v24)
```

**Strengths:**
- Clear 5-step decision tree — exhaustive, ordered, no gaps
- Routing table is comprehensive with all 10 specialist slugs
- SQL rules are precise (no `data_transacao`, correct table prefix, no `client_id`)
- `route_to_specialist` rules explicitly forbid pre-processing before delegation
- Output format is strict (2-3 sentences, currency format, no IDs)
- XML structure: `<Decision Tree>`, `<Tool Rules>`, `<Output Format>` ✅

**Minor gaps:**
- `route_to_specialist` is listed in Tool Rules but not separately declared as a tool — small LLM might not know if it's always available (P2)
- No explicit instruction for handling multi-intent messages (e.g., "register a sale and show my revenue") — Step 1 would delegate but Step 2 would be skipped silently (P2)

## Skills Map

Frontdesk has **no dedicated skills** registered in SKILL_REGISTRY. It operates directly with:
- `execute_sql` (inline factual queries)
- `executar_rag_cliente` (company knowledge RAG)
- `route_to_specialist` (specialist delegation)

These are tool-level capabilities, not skills — appropriate for a routing agent.

| Skill | Score | Key Issues |
|-------|-------|------------|
| (none — routing agent) | N/A | — |

## Tool Coverage

- **Present**: `execute_sql`, `executar_rag_cliente`, `route_to_specialist`
- **Missing**: None critical for its scope
- **Unused**: None declared unnecessarily

## Improvements Applied

| File | Change | Reason |
|------|--------|--------|
| `templates.py` | Updated `AGENTS_FRONTDESK` from v20 (PT-BR) to v24 (EN) | Langfuse is source of truth; local was 4 versions behind with full language difference |
| `templates.py` | Added explicit `route_to_specialist` section in Tool Rules (already present in Langfuse v24) | Clarifies delegation behavior for small LLMs |

## Remaining Issues

**P0:** none

**P1:** none

**P2:**
- Consider adding a note about multi-intent messages: "If the user combines two intents, delegate the primary (write/action) intent first, then handle the secondary."
- `route_to_specialist` availability could be stated at the top of Tool Rules for clarity

## Agent Logical Map

**Role:** Entry-point gatekeeper and triage agent for the entire Blu platform.

**Typical flow:**
1. User sends a message → frontdesk evaluates intent
2. If specialist domain detected → immediately calls `route_to_specialist(slug=..., message=...)` with no pre-processing
3. If simple factual query → generates SQL, calls `execute_sql`, returns 2-3 sentence summary
4. If company policy question → calls `executar_rag_cliente`, synthesizes from retrieved docs
5. If greeting/system question → responds directly without tools
6. If ambiguous → asks exactly one clarification question

**Handoffs:**
- Routes TO: `fiscal-agent`, `data-entry`, `crm`, `financeiro`, `compras`, `platform`, `agenda`, `data-analyst`, `doc-writer`, `strategy`
- Receives FROM: end users (no agent routes to frontdesk)

**Philosophy:** "Delegate aggressively, answer only what requires no specialist." The golden rule is explicit — when in doubt, delegate.

**Small-LLM fitness:** ★★★★★ — decision tree is deterministic, routing table is exhaustive, SQL rules are concrete, no ambiguous "use judgment" clauses.
