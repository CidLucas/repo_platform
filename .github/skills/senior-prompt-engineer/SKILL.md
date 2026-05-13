---
name: senior-prompt-engineer
description: World-class prompt engineering skill for LLM optimization, prompt patterns, structured outputs, and AI product development. Expertise in Claude, GPT-4, prompt design patterns, few-shot learning, chain-of-thought, and AI evaluation. Includes RAG optimization, agent design, and LLM system architecture. Use when building AI products, optimizing LLM performance, designing agentic systems, or implementing advanced prompting techniques.
---

# Senior Prompt Engineer

Repo-adapted prompt and agent design guidance for `blu-mono`.

This skill is tuned to the prompt and agent architecture that actually exists in this monorepo:

- Fragment-based and named-prompt composition through `libs/blu_prompt_management`
- Langfuse-first prompt management with `production` labels and builtin fallback `.md` files
- LangGraph agents built via `AgentBuilder` in `libs/blu_agent_framework`
- Layer 3 domain agents registered in `AgentTypeRegistry` (`registry.py`)
- Layer 2 ephemeral skills registered in `SKILL_REGISTRY` (`skills.py`), executed by `SkillFactory`
- `UnifiedAgentFactory` in `services/agent_api` — session-scoped agent assembly with context injection
- Supervisor + worker delegation pattern in `services/atendente_core`
- Context assembly through `ContextService` (`libs/blu_context_service`)
- Tool execution via MCP protocol against `services/tool_pool_api`

Use this skill when you are:

- designing or refactoring system prompts, prompt fragments, or tool prompts
- adding or changing agent fragment stacks, `AgentTypeConfig`, or `SkillDefinition`
- evaluating prompt quality for SQL, RAG, reporting, or procurement flows
- wiring new context variables from `ContextService` into prompt assembly
- deciding whether logic belongs in prompts, graph nodes, tool contracts, or context assembly

---

## Architecture Layers

| Layer                      | What it is                                   | Config                             | Prompt                                                 |
| -------------------------- | -------------------------------------------- | ---------------------------------- | ------------------------------------------------------ |
| **Supervisor**             | Routes to domain agents via delegation tools | `fragment/supervisor-*` stack      | Dynamic `workers_description` from `AgentTypeRegistry` |
| **Layer 3 — Domain Agent** | Stateful LangGraph agent, Redis checkpointer | `AgentTypeConfig` in `registry.py` | Fragment list or named `prompt_name`                   |
| **Layer 2 — Skill**        | Ephemeral sub-agent, no checkpointer         | `SkillDefinition` in `skills.py`   | `skill:<name>:system` in Langfuse                      |
| **Tool prompts**           | Internal LLM calls inside tools              | n/a                                | `tool/<name>` in Langfuse                              |

---

## Tech Stack

**Language:** Python
**Agent runtime:** LangGraph + `blu_agent_framework`
**Prompt management:** Langfuse + `blu_prompt_management` (compose_prompt, build_prompt)
**Context layer:** `blu_context_service` — Redis cache + Supabase (sql_table_config, agent_sessions)
**Observability:** Langfuse traces
**Tool execution:** MCP protocol → `tool_pool_api`
**Primary services:** `agent_api` (standalone), `atendente_core` (supervisor), `tool_pool_api` (tools)

---

## Key File Locations

### Prompt content (builtin fallbacks)

```
libs/blu_prompt_management/src/blu_prompt_management/prompts/
  fragment/          — shared and agent-specific fragments
  tool/              — internal tool LLM call prompts
  skill/             — skill system prompt fallbacks (must exist for each SkillDefinition)
  atendente/         — supervisor prompt variants
```

### Agent and skill registry

```
libs/blu_agent_framework/src/blu_agent_framework/
  registry.py        — AgentTypeConfig + AgentTypeRegistry (Layer 3)
  skills.py          — SkillDefinition + SKILL_REGISTRY (Layer 2)
  skill_factory.py   — SkillFactory runtime
  builder.py         — AgentBuilder fluent API
  nodes.py           — NodeRegistry decorator pattern
  state.py           — AgentState dataclass
  supervisor.py      — Supervisor graph
```

### Tool registry

```
libs/blu_tool_registry/src/blu_tool_registry/
  registry.py        — BUILTIN_TOOLS, GOOGLE_TOOLS, DOCKER_MCP_TOOLS + ToolMetadata
```

### Factory (session-scoped agent assembly)

```
services/agent_api/src/agent_api/core/factory.py   — UnifiedAgentFactory
```

### Context service

```
libs/blu_context_service/src/blu_context_service/
  context_service.py — ContextService: get_client_context_by_id, get_sql_table_configs
```

### Prompt management scripts

```
scripts/audit_langfuse_prompts.py        — audit production labels across all prompts
scripts/verify_standalone_prompts.py     — verify fragment composition compiles
scripts/create_standalone_prompts.py     — seed standalone agent prompts in Langfuse
scripts/create_analytics_prompts.py      — seed SQL/analytics fragments in Langfuse
scripts/create_rfq_prompts.py            — seed RFQ fragments in Langfuse
scripts/create_supervisor_prompts.py     — seed supervisor fragments in Langfuse
scripts/update_atendente_fragments.py    — update atendente fragment content in Langfuse
```

---

## How This Repo Wires Prompts

### Fragment-based agent (most agents)

```python
# registry.py — AgentTypeConfig
AgentTypeConfig(
    slug="data-analyst",
    fragments=[
        "fragment/standalone-base",     # identity, company context, session metadata
        "fragment/sql-schema",          # schema (dynamic via schema_description variable)
        "fragment/sql-rules",           # SQL generation constraints
        "fragment/sql-examples",        # few-shot SQL patterns
        "fragment/fallback-strategy",   # what to do when queries fail
        "fragment/data-analyst-workflow", # step-by-step workflow
        "fragment/standalone-response", # response quality, language rule
    ],
    enabled_tools=["execute_sql", "execute_csv_query", "list_csv_datasets", "peek_csv_columns"],
)

# factory.py — assembled in UnifiedAgentFactory.get_standalone_agent()
variables = {
    "nome_empresa": ...,           # from BluClientContext
    "agent_name": ...,             # from agent_catalog
    "agent_description": ...,      # from agent_catalog
    "collected_context": ...,      # from agent_sessions.collected_context
    "schema_description": ...,     # rendered from sql_table_config via _render_schema_description()
    "csv_datasets": ...,           # from collected_context
    "document_names": ...,         # from collected_context
    "google_connected": ...,       # from collected_context.google_email
    ...
}
system_prompt = await compose_prompt(fragments=registry_cfg.fragments, variables=variables)
```

### Named-prompt agent (customer-support)

```python
AgentTypeConfig(
    slug="customer-support",
    prompt_name="agents/customer-support",  # loaded directly from Langfuse, no fragments
    enabled_tools=[...],
)
# factory: system_prompt = await build_prompt(name=prompt_name, variables=variables)
```

### Skill (Layer 2)

```python
# skills.py — SkillDefinition
SkillDefinition(
    name="analyze_csv",
    prompt_name="skill:analyze_csv:system",   # Langfuse key
    required_tool_names=["list_csv_datasets", "peek_csv_columns", "execute_csv_query"],
    max_turns=5,
    on_max_turns="return_partial",
)
# SkillFactory intersects required_tool_names with parent agent's enabled_tools at runtime
```

### Tool prompt (internal LLM call inside a tool)

```python
# Inside executar_sql_agent tool (tool_pool_api):
PromptLoader.load("tool/sql-generation", variables={"query": nl_query, "table_info": schema})
# Inside executar_rag_cliente tool:
PromptLoader.load("tool/rag-query-rewrite", variables={"query": original_query})
```

---

## Critical Patterns

### Fragment ordering

Order is meaningful — fragments are concatenated top to bottom:

1. **Identity first** (`standalone-base`) — company context, session metadata, language rule
2. **Domain knowledge** (`sql-schema`, `rag-search`, `document-intelligence-tools`) — what the agent knows
3. **Workflow** (`*-workflow`) — how the agent should act, which tools to call and in what order
4. **Response last** (`standalone-response`) — output format, quality standards

Never put tool USAGE instructions in rules/schema fragments — they belong in the workflow fragment.

### Tool ownership per agent

- `data-analyst` generates SQL itself (has schema fragments) → `execute_sql` only, no `executar_sql_agent`
- `report-generator` has no schema context → `executar_sql_agent` only (NL→SQL internally), no `execute_sql`
- Tool intersection: `SkillFactory` intersects `skill.required_tool_names` with `agent.enabled_tools` at runtime — a tool missing from the agent is silently dropped

### Dynamic schema injection

`schema_description` variable is populated in the factory from `ContextService.get_sql_table_configs()` → `_render_schema_description()`. The `fragment/sql-schema` uses it when non-empty, falls back to static analytics_v2 schema when empty.

### Supervisor workers list

`fragment/supervisor-workers` renders `{{ workers_description }}` generated by `AgentTypeRegistry.build_supervisor_description(tier)` — dynamic per tier. Do not add a static routing table alongside it; it will drift.

### RAG synthesis boundary

`executar_rag_cliente` returns raw passages. The agent synthesises them. There is no synthesis inside the tool. The `tool/rag-query-rewrite` prompt runs pre-retrieval to rewrite the query for better embedding search.

---

## Reference Documentation

- `references/prompt_engineering_patterns.md` — fragment rules, variable assembly, anti-patterns
- `references/agentic_system_design.md` — graph patterns, Layer 2/3, factory, context flow
- `references/llm_evaluation_frameworks.md` — how to validate prompt changes in this repo
