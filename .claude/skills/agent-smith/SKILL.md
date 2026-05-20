---
name: agent-smith
description: Register and scaffold new agent capabilities inside the Blu platform. Use when adding a new domain specialist (Layer 3) or sub-skill (Layer 2). Covers AgentTypeConfig in registry.py, SkillDefinition in skills.py, ToolMetadata in tool_registry.py, agent_catalog Supabase migration, and prompt authoring. For prompt/fragment content use the senior-prompt-engineer skill.
---

# Agent Smith — Skill Registration Playbook

You are wiring a new agent capability into the Blu platform. Identify the layer first, then follow the touchpoint map.

---

## Classify the capability

| Layer                      | What it is                                                                                                                                                      | Examples                                        |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| **L3 — Domain Specialist** | Stateful multi-turn agent. Invoked by Orchestrator or Frontdesk. Registered in `AgentTypeRegistry`. Uses `use_default_graph()` unless a custom graph is needed. | `data-analyst`, `rfq-agent`, `context-gatherer` |
| **L2 — Skill**             | Ephemeral. Runs inside a specialist via `SkillFactory`. No checkpointer. Declares its tool subset.                                                              | `analyze_csv`, `rag_search`, `generate_rfq`     |

---

## Architecture Rules

1. **Orchestrator/Frontdesk → L3 Specialist → L2 Skill → L1 Tool. Never skip layers.**
2. **`AgentTypeConfig.tier_required` must be ≥ tier of every tool in `enabled_tools`.**
3. **`on_max_turns="raise"` only for transactional flows where partial execution causes harm** (e.g., RFQ dispatch, email mid-send).
4. **All `required_tool_names` in `SkillDefinition` must exist in `ToolRegistry` at registration time.**
5. **New specialists use `prompt_name`, not `fragments`.** The `fragments` list is legacy — only existing agents keep it until migrated.
6. **Only `build_prompt(name, variables)` for all prompt loading.** `compose_prompt` is removed.

---

## Touchpoints

### L3 — Domain Specialist

| #   | File                                                                        | What to do                                                           |
| --- | --------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| 1   | `libs/blu_agent_framework/src/blu_agent_framework/registry.py`              | Add `AgentTypeConfig` to `_AGENT_TYPES` dict                         |
| 2   | `libs/blu_tool_registry/src/blu_tool_registry/registry.py`                  | Add any new `ToolMetadata` entries to `BUILTIN_TOOLS`                |
| 3   | `libs/blu_prompt_management/src/blu_prompt_management/templates.py`         | Add `PromptTemplateConfig` to `BUILTIN_TEMPLATES` (builtin fallback) |
| 4   | `libs/blu_prompt_management/src/blu_prompt_management/prompts/specialists/` | Create `<slug>.md` (Langfuse source of truth, synced at deploy)      |
| 5   | `supabase/migrations/<ts>_add_<slug>_agent.sql`                             | Insert row into `public.agent_catalog`                               |

### L2 — Skill

| #   | File                                                                                         | What to do                                                           |
| --- | -------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| 1   | `libs/blu_agent_framework/src/blu_agent_framework/skills.py`                                 | Add `SkillDefinition` to `SKILL_REGISTRY`                            |
| 2   | `libs/blu_tool_registry/src/blu_tool_registry/registry.py`                                   | Validate all `required_tool_names` exist in `BUILTIN_TOOLS`          |
| 3   | `libs/blu_prompt_management/src/blu_prompt_management/templates.py`                          | Add `PromptTemplateConfig` to `BUILTIN_TEMPLATES` (builtin fallback) |
| 4   | `libs/blu_prompt_management/src/blu_prompt_management/prompts/skills/<skill_name>/system.md` | Create skill system prompt (Langfuse source of truth)                |

---

## AgentTypeConfig

**File:** `libs/blu_agent_framework/src/blu_agent_framework/registry.py`

```python
from blu_tool_registry.tool_metadata import TierLevel  # already imported at top of file

"<slug>": AgentTypeConfig(
    name="<Human Name>",
    slug="<slug>",                        # kebab-case, unique key
    description=(
        "<One or two sentences. This is what the Orchestrator LLM reads to decide "
        "whether to delegate. Format: 'Does X. Use for Y. Not for Z.'>"
    ),
    prompt_name="agents/<slug>",          # Langfuse key; maps to _LANGFUSE_MANAGED_PREFIXES "agents/"
    enabled_tools=[
        "<tool_name>",                    # must exist in BUILTIN_TOOLS
    ],
    tier_required=TierLevel.BASIC,        # FREE | BASIC | SME | PREMIUM | ENTERPRISE | ADMIN
    routing_hint="<keywords for delegation>",  # shown to supervisor LLM after description
    max_turns=4,
    on_max_turns="return_partial",        # "raise" only for transactional ops
    max_retries=2,
    tags=["<domain>"],                    # used for skill-tag intersection filtering
    graph_topology="default",            # "default" | "fanout" — custom graphs are rare
),
```

> **`prompt_name` vs `fragments`**: New agents always use `prompt_name`. Legacy agents still use `fragments`; migrate them to `prompt_name` when touching them.
> **`routing_hint`**: Short keyword list the supervisor uses to decide delegation. E.g., `"CSV data, analytics, SQL queries, rankings, revenue trends."`.
> **`tags`**: Used for skill discovery intersection. A specialist can only dispatch skills whose `tags` intersect with the specialist's `tags`.

---

## SkillDefinition

**File:** `libs/blu_agent_framework/src/blu_agent_framework/skills.py`

```python
"<skill_name>": SkillDefinition(
    name="<skill_name>",                  # snake_case, matches SKILL_REGISTRY key
    description=(
        "<One sentence. Shown to the classify_skill_intent node to select this skill.>"
    ),
    required_tool_names=[
        "<tool_name>",                    # subset of the parent specialist's enabled_tools
    ],
    prompt_name="skill:<skill_name>:system",   # Langfuse key; auto-managed via "skill:" prefix
    max_turns=3,
    on_max_turns="return_partial",        # "raise" only when partial output causes harm
    tags=["<domain>"],                    # must intersect with parent specialist's tags
),
```

> **Tool filtering**: At runtime `SkillFactory` intersects `required_tool_names` with the specialist's `enabled_tools`. If the intersection is empty, the skill cannot run and the agent surfaces a tier message.
> **`prompt_name` convention**: Always `skill:<skill_name>:system`. This prefix is in `_LANGFUSE_MANAGED_PREFIXES` so Langfuse is tried first with builtin fallback.

---

## ToolMetadata (if adding a new tool)

**File:** `libs/blu_tool_registry/src/blu_tool_registry/registry.py`

```python
from blu_tool_registry.tool_metadata import ToolCategory, TierLevel  # already imported

"<tool_name>": ToolMetadata(
    name="<tool_name>",                   # snake_case, matches MCP tool name exactly
    category=ToolCategory.CUSTOM,         # RAG | SQL | SCHEDULING | DOCKER_MCP | PUBLIC | GOOGLE | CUSTOM
    description="<What it does and when to call it.>",
    tier_required=TierLevel.BASIC,        # must be ≤ tier_required of any specialist that enables it
    requires_confirmation=False,          # True for mutations visible to end users
    tags=["<domain>"],
),
```

---

## Prompt Authoring

## Always use the senior-prompt-engineer skill for prompt and fragment content. The key touchpoints for agent registration are the config and registry files. For prompt content, follow the exact patterns in the `.md` files in `prompts/specialists/` or `prompts/skills/<name>/`.

### How the loader resolves prompts

```
build_prompt("agents/<slug>", variables)
    ├── name in _LANGFUSE_MANAGED_PREFIXES ("agents/")
    ├── → try Langfuse (label="production", cache_ttl=300s, circuit breaker)
    │       hit  → render Langfuse template, return
    │       miss → fall back to BUILTIN_TEMPLATES["agents/<slug>"]
    └── name NOT in managed prefixes ("fragment/standalone-base", etc.)
            → load BUILTIN_TEMPLATES[name] directly, skip Langfuse
```

**Managed prefixes** (try Langfuse first): `orchestrator/`, `agents/`, `skill:`
**Non-managed** (builtins only): `fragment/*`, `classify/*`, `tool/*`, `atendente/*`

### Step 1 — Builtin fallback in `templates.py`

Every prompt needs a `PromptTemplateConfig` in `BUILTIN_TEMPLATES`. This is the runtime safety net.

```python
# libs/blu_prompt_management/src/blu_prompt_management/templates.py

PromptTemplateConfig(
    name="agents/<slug>",                 # must match prompt_name in AgentTypeConfig
    category=PromptCategory.SYSTEM,
    description="<Human description for logs>",
    required_variables=["nome_empresa", "tools_description"],
    optional_variables={
        "schema_description": "",
        "company_profile": "",
    },
    content="""Você é o <nome do agente> da **{{ nome_empresa }}**.

{% if company_profile %}
## Contexto da Empresa
{{ company_profile }}
{% endif %}

## Ferramentas Disponíveis
{{ tools_description }}

## Instruções
<instruções específicas do agente>

Responda sempre no idioma do usuário.
""",
),
```

**Template syntax rules**:

- Variables: `{{ variable_name }}` (Jinja2, spaces inside braces)
- Conditionals: `{% if variable %}...{% endif %}`
- Variables are **flat** — no dot notation. Use `{{ nome_empresa }}` not `{{ client.nome_empresa }}`
- Declare all required variables in `required_variables` list

### Step 2 — Langfuse source file (for managed prompts)

Create the `.md` file that will be synced to Langfuse. This is the canonical version used in production.

```
libs/blu_prompt_management/src/blu_prompt_management/prompts/
├── specialists/          ← agents/<slug> prompts
│   └── <slug>.md
├── skills/               ← skill:<name>:system prompts
│   └── <skill_name>/
│       └── system.md
├── orchestrator/         ← orchestrator/* prompts (already exists)
├── fragment/             ← context-gatherer fragments (Langfuse-managed)
└── tool/                 ← tool-specific prompts
```

The `.md` file uses Langfuse's `{{variable}}` syntax (no spaces, double braces):

```markdown
Você é o <nome do agente> da **{{nome_empresa}}**.

## Ferramentas Disponíveis

{{tools_description}}

## Instruções

<instruções>
```

> **Sync**: Prompts are pushed to Langfuse at deploy time. Until then, the builtin in `templates.py` is used.

---

## Database Migration — `agent_catalog` only

Skills live in Python `SKILL_REGISTRY` only. No `skill_catalog` table. No `prompt_catalog` table.

```sql
-- supabase/migrations/<timestamp>_add_<slug>_agent.sql

INSERT INTO public.agent_catalog (
    slug,
    name,
    description,
    prompt_name,
    agent_config,
    tier_required
) VALUES (
    '<slug>',
    '<Human Name>',
    '<same text as AgentTypeConfig.description>',
    'agents/<slug>',
    '{
        "enabled_tools": ["<tool_1>", "<tool_2>"],
        "max_turns": 4,
        "tags": ["<domain>"]
    }'::jsonb,
    'BASIC'
)
ON CONFLICT (slug) DO UPDATE
    SET name         = EXCLUDED.name,
        description  = EXCLUDED.description,
        agent_config = EXCLUDED.agent_config;
```

---

## Validation Checklist

Before submitting a new specialist or skill:

- [ ] **Tier consistency**: `AgentTypeConfig.tier_required` ≥ all tool `tier_required` in `enabled_tools`
- [ ] **Tool existence**: All `required_tool_names` exist in `BUILTIN_TOOLS` (`tool_registry/registry.py`)
- [ ] **Tag intersection**: `SkillDefinition.tags` ∩ `AgentTypeConfig.tags` ≠ ∅ (skill is discoverable by specialist)
- [ ] **Builtin template**: `PromptTemplateConfig` added to `BUILTIN_TEMPLATES` in `templates.py`
- [ ] **Prompt file**: `.md` created in `prompts/specialists/` or `prompts/skills/<name>/system.md`
- [ ] **`build_prompt` only**: No `compose_prompt` in new code
- [ ] **`prompt_name` set**: New specialists use `prompt_name`, not `fragments`
- [ ] **DB migration**: `agent_catalog` insert added (no `skill_catalog`, no `prompt_catalog`)
- [ ] **`on_max_turns`**: Only `"raise"` when partial execution causes real harm (RFQ dispatch, emails)

---

## Context Available at Each Layer

| Layer           | `AgentState` fields available                                                          | How it arrives                                                                                |
| --------------- | -------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| L4 Orchestrator | `client_context`, `nome_empresa`, `tier`, `plan`, `step_results`, `involved_domains`   | Loaded by `ContextService.get_client_context_by_id(client_id)` at session init                |
| L3 Specialist   | `client_context`, `nome_empresa`, `tier`, `messages`, `skill_results`, `current_skill` | Passed from Orchestrator via `AgentState` (same thread or `Send`)                             |
| L2 Skill        | `messages[-3:]` (parent context), variables injected from `client_context` into prompt | `SkillFactory.run()` injects `nome_empresa`, `schema_description`, etc. into prompt variables |
| L1 Tool         | `client_id`, MCP headers `X-Client-Id` + `X-Session-Id`                                | Set by `MCPToolExecutor` on each call                                                         |

> **Key**: L2 Skills do not receive the full `AgentState`. They receive a rendered prompt (variables injected) and the last 3 parent messages. Declare all needed data as prompt variables.

---

## Flow Summary

```
User Request
    │
    ▼
Frontdesk Specialist (L3)
    │  classify_intent → rag_search / simple_sql / delegate_to_specialist / health_check
    │
    ├─ simple → Skill (L2) → Tool (L1) → respond
    │
    └─ complex → Orchestrator (L4)
                    │  parse_intent → decompose → plan
                    ▼
               Specialist (L3) — own thread, classify → skill dispatch
                    │
                    ▼
               Skill (L2) — ephemeral, tool loop, max_turns
                    │
                    ▼
               Tool (L1) — stateless MCP execution
```

---

_For prompt content and fragment authoring, use `/senior-prompt-engineer`._

_End of Agent Smith Skill Registration Playbook_
