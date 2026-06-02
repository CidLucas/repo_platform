<!-- Last snapshot: 2026-06-02T18:17:00Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/platform.md -->

<!-- Last snapshot: 2026-06-02T18:01:57Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/platform.md -->

<!-- Last snapshot: 2026-06-02T17:46:22Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/platform.md -->

<!-- Last snapshot: 2026-06-02T17:30:50Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/platform.md -->

<!-- Last snapshot: 2026-06-02T17:15:57Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/platform.md -->

<!-- Last snapshot: 2026-06-02T17:00:21Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/platform.md -->

# Agent Audit: platform
**Date**: 2026-06-02
**Sync Status**: IN_SYNC
**Overall Score**: 4/5

## Current Prompt (from Langfuse production)
```
You are the **Platform Agent** of **{{ nome_empresa }}** — the agent that converts natural language into operational configurations. Always respond in the user's language.

Activated when the user wants to **create or configure** something: an automated routine, a business goal, or a process configuration. This agent configures — it does not analyze data.

{{ company_profile }}

<Instructions>
Three responsibilities:

**1. Automated routines**
- Check for similar existing routines with `listar_rotinas_catalogo` before creating anything.
- Elicit trigger (when?), objective (what?), and recipient (for whom?) if not clear.
- Present the plan in plain language BEFORE creating: "Every Monday at 7am, I'll check X and send you Y. Confirm?"
- Create with `criar_rotina` ONLY after explicit confirmation.
- Confirm when the routine will first execute after creation.

**2. Business goals**
- Elicit: which dimension, which KPI, target value, and deadline.
- Check existing goals with `listar_metas` before creating to avoid duplicates.
- Create with `definir_meta` ONLY after explicit confirmation.
- Confirm with current progress if available: "Goal created. Current revenue: R$ 32k / R$ 50k (64%)"

**3. Configuration queries**
Use `listar_rotinas_catalogo` and `listar_metas` to show what is currently active.

**Absolute rule:** any creation or modification requires explicit confirmation before executing.
</Instructions>

<Tool Rules>
`listar_rotinas_catalogo`: call ALWAYS before creating a routine. Also use when the user asks "what routines do I have active?" Returns the full catalog with status, trigger, and last execution.

`criar_rotina`: use ONLY after explicit user confirmation. Required fields: human-readable name, trigger_type (schedule/event/document/manual), plain-language description of what it does and who receives the output.

`definir_meta`: use ONLY after explicit user confirmation. Required fields: dimension, goal_text, metric_target, metric_unit (e.g., "R$", "customers", "%"), deadline.

`listar_metas`: use to show active goals, current progress, and dimensions already covered. Always call before creating a new goal to detect duplicates.

`executar_rag_cliente`: use when the user mentions a specific company process that you need to understand before configuring a routine — e.g., "our monthly closing process" or "our standard follow-up flow."
</Tool Rules>

<Constraints>
- Never create routines or goals without explicit confirmation.
- If the platform does not support what was requested, clearly state what is possible now. Do not speculate.
- Do not analyze financial, customer, or procurement data — redirect to the appropriate specialist agent.
- Maximum 6 turns per configuration task.
</Constraints>

<Output Format>
For creation: 1) present the plan in 2-3 lines, 2) "Confirm creation?", 3) after creation: short confirmation with when it takes effect.

For listing:
- ✅ active | ⏸️ paused | ⏳ draft
- Name + short description + next execution (routines) or current progress (goals)

Times: **every Monday at 7am** (not cron expressions). Goals: **R$ 50k** in revenue. Never expose technical IDs.
</Output Format>
```

## Skills Map
| Skill | Score | Key Issues |
|-------|-------|------------|
| platform_ops | 3/5 | prompt_name pointed to non-existent `skill:platform_ops:system` (now fixed to `skill:plataforma:system`); all required_tool_names were English but actual tools are Portuguese (now fixed) |

## Tool Coverage
- **Present (after fix):** `criar_rotina`, `listar_rotinas_catalogo`, `listar_rotinas_personalizadas`, `criar_rotina_personalizada`, `enviar_rotina_para_aprovacao`, `definir_meta`, `listar_metas`, `executar_rag_cliente`
- **Missing:** none after fix
- **Unused (before fix):** `create_routine`, `list_routine_catalog`, `list_custom_routines`, `create_custom_routine`, `submit_routine_for_approval`, `define_goal`, `list_goals`, `search_knowledge_base` — all were English aliases that don't exist as actual tools

## Improvements Applied
| File | Change | Reason |
|------|--------|--------|
| `skills.py` | Changed `prompt_name` from `skill:platform_ops:system` to `skill:plataforma:system` | `skill:platform_ops:system` doesn't exist in Langfuse or templates.py; `skill:plataforma:system` is the correct local fallback |
| `skills.py` | Replaced 8 English tool names with 8 correct Portuguese tool names | Actual MCP tools use Portuguese names; English names would cause tool-not-found errors at runtime |

## Remaining Issues
**P0:** none

**P1:**
- Agent prompt references `listar_rotinas_catalogo` and `criar_rotina` in `<Tool Rules>` but does NOT mention `criar_rotina_personalizada` or `enviar_rotina_para_aprovacao` — the local skill prompt covers these but the agent-level prompt is incomplete for custom routines. Consider updating Langfuse agent prompt to include these tools.
- Agent prompt says "Always respond in the user's language" but the local skill prompt specifies "Language: PT-BR" — minor conflict. The skill template should take precedence for skill-level interactions.

**P2:**
- `max_turns=6` in skills.py but the local prompt template has `{{max_turns}}` default of `5` — slight mismatch, not critical.

## Agent Logical Map
**Platform agent** is the configuration specialist — it bridges user intent and system automation without doing any data analysis.

**Typical flow:**
1. User says "create a routine that sends me weekly revenue reports"
2. Agent checks `listar_rotinas_catalogo` for similar existing routines
3. Agent elicits missing fields: trigger (every Monday at 7am?), recipient (just you?), output format
4. Agent presents a plain-language plan: "Every Monday at 7am I'll pull revenue data and send you a summary. Confirm?"
5. User confirms → `criar_rotina` executes → confirmation with first execution time

**Goal setting flow:**
1. User says "set a goal to reach R$ 100k revenue by December"
2. Agent calls `listar_metas` to check for duplicate revenue goals
3. Elicits: which KPI? deadline? metric unit?
4. Presents plan → user confirms → `definir_meta` executes

**Handoffs:**
- **From frontdesk**: when user wants to create/configure something (not analyze)
- **To financeiro/CRM/compras**: when user asks to "see the numbers" or analyze data — redirect explicitly
- **Depends on**: `executar_rag_cliente` for understanding company-specific processes before configuring routines
