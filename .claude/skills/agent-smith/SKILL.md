---
name: agent-smith
description: Register and scaffold new agent skills inside the Blu Python platform. Use when adding a new domain agent (Layer 3) or sub-skill (Layer 2). Covers AgentTypeConfig in registry.py, SkillDefinition in skills.py, ToolRegistry entries, and the agent_catalog Supabase row. For prompt/fragment authoring use the senior-prompt-engineer skill.
---

# Agent Smith — Skill Registration Playbook

You are wiring a new agent capability into the Blu platform. Identify the layer first, then follow the touchpoint map.

---

## Classify the skill

| Layer                      | What it is                                                                                                              | Examples                                    |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| **Layer 3 — Domain Agent** | Stateful, multi-turn LangGraph agent. Invoked by orchestrator or supervisor. Has its own graph, checkpointer, tool set. | `data-analyst`, `customer-communication`    |
| **Layer 2 — Sub-skill**    | Ephemeral. Runs inside a Layer 3 agent via `SkillFactory`. No checkpointer, no Redis.                                   | `analyze_csv`, `rag_search`, `generate_rfq` |

---

## Touchpoints

### Layer 3 — Domain Agent

| #   | File                                                           | What to do                                              |
| --- | -------------------------------------------------------------- | ------------------------------------------------------- |
| 1   | `libs/blu_agent_framework/src/blu_agent_framework/registry.py` | Add `AgentTypeConfig` to `_AGENT_TYPES`                 |
| 2   | `libs/blu_tool_registry/src/blu_tool_registry/registry.py`     | Add any new tools to `BUILTIN_TOOLS`                    |
| 3   | `supabase/migrations/<ts>_add_<slug>_agent.sql`                | Insert row into `agent_catalog`                         |
| 4   | Langfuse                                                       | Create prompt fragments — use `/senior-prompt-engineer` |

### Layer 2 — Sub-skill

| #   | File                                                         | What to do                                                          |
| --- | ------------------------------------------------------------ | ------------------------------------------------------------------- |
| 1   | `libs/blu_agent_framework/src/blu_agent_framework/skills.py` | Add `SkillDefinition` to `SKILL_REGISTRY`                           |
| 2   | Langfuse                                                     | Create `skill:<name>:system` prompt — use `/senior-prompt-engineer` |

---

## AgentTypeConfig

**File:** `libs/blu_agent_framework/src/blu_agent_framework/registry.py`

```python
"<slug>": AgentTypeConfig(
    name="<Human Name>",
    slug="<slug>",                       # kebab-case
    description="<Does X. Requires Y. Outputs Z. ≤2 sentences.>",
    fragments=[
        "fragment/standalone-base",      # Always first
        "fragment/<slug>-workflow",      # Agent-specific reasoning
        "fragment/standalone-response",  # Always last
    ],
    enabled_tools=["<tool_name>"],
    tier_required=TierLevel.BASIC,       # FREE | BASIC | SME | PREMIUM
    max_turns=4,
    on_max_turns="return_partial",       # "raise" only for transactional ops
),
```

> `description` is what the orchestrator reads to decide delegation. Format: _"Does X. Requires Y. Outputs Z."_

---

## SkillDefinition

**File:** `libs/blu_agent_framework/src/blu_agent_framework/skills.py`

```python
"<skill_name>": SkillDefinition(
    name="<skill_name>",                 # snake_case
    description="<One sentence for intent matching by classify_intent_node.>",
    required_tool_names=["<tool>"],      # Intersected with agent.enabled_tools at runtime
    prompt_name="skill:<skill_name>:system",
    max_turns=3,
    on_max_turns="return_partial",       # "raise" when partial output causes harm
    tags=["<domain>"],
),
```

---

## ToolMetadata (if adding a new tool)

**File:** `libs/blu_tool_registry/src/blu_tool_registry/registry.py`

```python
"<tool_name>": ToolMetadata(
    name="<tool_name>",
    category=ToolCategory.SQL,           # RAG | SQL | SCHEDULING | GOOGLE | CUSTOM
    description="<What it does and when to call it.>",
    tier_required=TierLevel.BASIC,
    requires_confirmation=False,         # True for mutations visible to clients
    tags=["<domain>"],
),
```

---

## agent_catalog migration

```sql
INSERT INTO public.agent_catalog (slug, name, description, prompt_name, agent_config, tier_required)
VALUES (
  '<slug>',
  '<Human Name>',
  '<same as AgentTypeConfig.description>',
  'fragment/<slug>-workflow',            -- or monolithic prompt name
  '{"enabled_tools": ["<tool_name>"]}'::jsonb,
  'BASIC'
);
```

---

## Rules

- `on_max_turns="raise"` only when partial execution causes harm (e.g., email sent mid-flow).
- Tier on `AgentTypeConfig` must be ≥ tier of every tool in `enabled_tools`.
- The orchestrator calls Layer 3 only. Layer 3 calls Layer 2 via `SkillFactory`. Never skip layers.
- Prompt and fragment content → use `/senior-prompt-engineer`.
