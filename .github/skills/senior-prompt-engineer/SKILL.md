---
name: senior-prompt-engineer
description: World-class prompt engineering skill for LLM optimization, prompt patterns, structured outputs, and AI product development. Expertise in Claude, GPT-4, prompt design patterns, few-shot learning, chain-of-thought, and AI evaluation. Includes RAG optimization, agent design, and LLM system architecture. Use when building AI products, optimizing LLM performance, designing agentic systems, or implementing advanced prompting techniques.
---

# Senior Prompt Engineer

Repo-adapted prompt and agent design guidance for `blu-mono`.

This skill is tuned to the prompt and agent architecture that actually exists in this monorepo:

- **Single prompt entry point**: `build_prompt(name, variables)` from `blu_prompt_management` — `compose_prompt` is REMOVED, do not use it
- Langfuse-first prompt management with `production` labels and builtin fallback in `templates.py`
- LangGraph agents built via `AgentBuilder` in `libs/blu_agent_framework`
- Layer 4 Orchestrator (`use_orchestrator_graph`) — decomposes multi-step requests, routes to L3 specialists
- Layer 3 domain agents registered in `AgentTypeRegistry` (`registry.py`) — always use `prompt_name`, never `fragments`
- Layer 2 ephemeral skills registered in `SKILL_REGISTRY` (`skills.py`), executed by `SkillFactory`
- `UnifiedAgentFactory` in `services/agent_api` — session-scoped agent assembly
- Supervisor fan-out in `libs/blu_agent_framework/supervisor.py` — `_WorkerInvoker._get_prompt()` injects schema/KB context from `BluClientContext`
- Context assembly through `ContextService` (`libs/blu_context_service`)
- Tool execution via MCP protocol against `services/tool_pool_api`
- Dynamic context injection via `VariableExtractor` in `libs/blu_prompt_management/src/blu_prompt_management/variables.py`

Use this skill when you are:

- designing or refactoring system prompts, skill prompts, or tool prompts
- adding or changing `AgentTypeConfig` or `SkillDefinition`
- evaluating prompt quality for SQL, RAG, reporting, or procurement flows
- wiring new context variables from `ContextService` or `BluClientContext` into prompt assembly
- deciding whether logic belongs in prompts, graph nodes, tool contracts, or context assembly
- pushing new prompts to Langfuse or auditing the production label state

---

## Architecture Layers

| Layer                      | What it is                                                              | Config                                      | Prompt                                 |
| -------------------------- | ----------------------------------------------------------------------- | ------------------------------------------- | -------------------------------------- |
| **L4 — Orchestrator**      | Meta-agent: parse_intent → decompose → plan → execute_step → synthesize | `use_orchestrator_graph()` in `builder.py`  | `orchestrator/*` in Langfuse           |
| **L3 — Domain Specialist** | Stateful LangGraph agent, Redis checkpointer, fan-out worker            | `AgentTypeConfig` in `registry.py`          | `agents/<slug>` in Langfuse            |
| **L2 — Skill**             | Ephemeral sub-agent, no checkpointer, tool subset                       | `SkillDefinition` in `skills.py`            | `skill:<name>:system` in Langfuse      |
| **Supervisor**             | Routes to domain agents via delegation tools                            | `route_after_supervisor` in `supervisor.py` | `fragment/supervisor-role` in Langfuse |
| **Tool prompts**           | Internal LLM calls inside tools (tool_pool_api)                         | n/a                                         | `tool/<name>` — builtins only          |

---

## Tech Stack

**Language:** Python
**Agent runtime:** LangGraph + `blu_agent_framework`
**Prompt management:** Langfuse + `blu_prompt_management` — `build_prompt` only
**Context layer:** `blu_context_service` — Redis cache + Supabase (`sql_table_config`, `agent_sessions`)
**Variable extraction:** `VariableExtractor` in `blu_prompt_management/variables.py` — renders `sql_schema_context` and `kb_context` from `BluClientContext`
**Observability:** Langfuse traces
**Tool execution:** MCP protocol → `tool_pool_api`
**Primary services:** `agent_api` (frontdesk + standalone + supervisor), `tool_pool_api` (tools)

---

## Key File Locations

### Prompt loading

```
libs/blu_prompt_management/src/blu_prompt_management/
  __init__.py          — exports build_prompt() — THE ONLY prompt entry point
  loader.py            — PromptLoader: Langfuse-first with builtin fallback + circuit breaker
  templates.py         — BUILTIN_TEMPLATES dict: all builtin PromptTemplateConfig entries
  variables.py         — VariableExtractor: render_sql_schema(), render_kb_context()
                         PromptVariables: sql_schema_context, kb_context fields
  prompts/             — source .md files pushed to Langfuse at deploy
    orchestrator/      — L4 orchestrator prompts (parse-intent, decompose, plan, synthesize)
    specialists/       — agents/<slug> prompts (L3 specialists)
    skills/            — skill:<name>:system prompt fallbacks
    fragment/          — shared fragments (supervisor-role, sql-schema, context-gatherer-*)
    tool/              — internal tool LLM call prompts
```

### Agent and skill registry

```
libs/blu_agent_framework/src/blu_agent_framework/
  registry.py          — AgentTypeConfig + AgentTypeRegistry (Layer 3)
  skills.py            — SkillDefinition + SKILL_REGISTRY (Layer 2)
  skill_factory.py     — SkillFactory runtime
  builder.py           — AgentBuilder fluent API; execute_worker_node_impl passes client_context
  nodes.py             — NodeRegistry decorator pattern
  state.py             — AgentState TypedDict; key fields: client_context, nome_empresa, tier
  supervisor.py        — _WorkerInvoker: invoke() + _get_prompt() with VariableExtractor
  orchestrator.py      — make_execute_step_node(): passes client_context to _WorkerInvoker
```

### Tool registry

```
libs/blu_tool_registry/src/blu_tool_registry/
  registry.py          — BUILTIN_TOOLS + ToolMetadata (name, category, tier_required, tags)
```

### Factory (session-scoped agent assembly)

```
services/agent_api/src/agent_api/core/factory.py   — UnifiedAgentFactory
  get_frontdesk_graph(tier, ctx_service)  — Frontdesk graph cached per tier; uses use_default_graph()
  get_supervisor_graph(tier, ctx_service) — Supervisor fan-out graph cached per tier; uses use_supervisor_graph()
  build_frontdesk_prompt(nome_empresa, ctx_service, client_context)
                                          — Builds agents/frontdesk prompt; variables: nome_empresa,
                                            tools_description, company_profile, schema_description
  get_standalone_agent(session_id, client_id, agent_catalog_id)
                                          — Per-session compiled graph from agent_catalog table
```

`BuiltAgent` contains `graph + system_prompt + client_context + metadata`.

### Context service

```
libs/blu_context_service/src/blu_context_service/
  context_service.py   — ContextService: get_client_context_by_id(), get_sql_table_configs()
                         Returns BluClientContext with data_schema.table_schemas
```

### Prompt management scripts

```
scripts/audit_langfuse_prompts.py        — audit production labels across all prompts
scripts/verify_standalone_prompts.py     — verify prompt compilation
scripts/create_supervisor_prompts.py     — seed supervisor fragments in Langfuse
scripts/create_analytics_prompts.py      — seed SQL/analytics fragments in Langfuse
scripts/create_rfq_prompts.py            — seed RFQ fragments in Langfuse
```

---

## Prompt Loading Resolution

### Managed prefixes (Langfuse-first)

These prefixes try Langfuse (`label=production`, `cache_ttl=300s`, circuit breaker on connection errors) and fall back to `BUILTIN_TEMPLATES`:

```
orchestrator/    → orchestrator/*.md source files
agents/          → specialists/*.md source files
skill:           → skills/<name>/system.md source files
```

### Non-managed (builtins only — skip Langfuse)

```
fragment/*       → BUILTIN_TEMPLATES only (no Langfuse lookup)
classify/*       → BUILTIN_TEMPLATES only
tool/*           → BUILTIN_TEMPLATES only
atendente/*      → BUILTIN_TEMPLATES only
```

> **Critical**: `fragment/*` prompts pushed to Langfuse (supervisor-role, sql-schema, context-gatherer-\*) are NOT loaded via `build_prompt`. They are stored in Langfuse for reference and content management but loaded as builtins at runtime. Only `orchestrator/`, `agents/`, and `skill:` prefixes trigger Langfuse lookups.

---

## AgentBuilder Graph Topologies

`AgentBuilder` is a fluent API in `libs/blu_agent_framework/src/blu_agent_framework/builder.py`. Choose the topology that matches the layer:

| Method                         | Layer                | When to use                                                                                                                   |
| ------------------------------ | -------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `use_default_graph()`          | L3 / standalone      | Default ReAct loop: init → classify_intent → context_enrichment → elicit/respond/select_skill/run_skill                       |
| `use_specialist_graph(cfg)`    | L3                   | Specialist invoked by orchestrator; adds `classify_skill_intent` node that selects from SKILL_REGISTRY filtered by `cfg.tags` |
| `use_fanout_graph()`           | L3                   | Parallel tool fan-out via `Send`; use when a single request spawns independent tool calls                                     |
| `use_supervisor_graph(tier)`   | Frontdesk/supervisor | Supervisor LLM routes via `delegate_to_*` tools; workers run as fan-out parallel loops                                        |
| `use_orchestrator_graph(tier)` | L4                   | Meta-skill: parse_intent → gather_context → decompose → plan → execute_step (loops) → synthesize                              |
| `use_skill_graph()`            | L2                   | Minimal: START → respond ↔ execute_tool → END; no init/classify; used by `SkillFactory._build_skill_graph()`                  |
| `use_custom_graph(graph_def)`  | standalone           | Compiled from `agent_catalog.workflow_graph` JSON; used for catalog-driven agent definitions                                  |

**Standard builder chain:**

```python
AgentBuilder(agent_cfg, mcp_executor=mcp_exec)
    .with_llm(llm)
    .with_checkpointer(checkpointer)      # Redis; omit for ephemeral skill sub-graphs
    .with_context_service(ctx_service)   # supervisor / orchestrator only
    .with_skill_factory(skill_factory)   # use_default_graph with skills enabled
    .use_specialist_graph(cfg)           # or whichever topology
    .build()
```

**Orchestrator `execute_step` compiles specialist subgraphs** (not `_WorkerInvoker`) — one per `AgentTypeConfig` slug, cached in memory. Each specialist runs as a full `use_specialist_graph` compiled graph with its own `SkillFactory`.

---

## How This Repo Wires Prompts

### Specialist agent (L3) — `prompt_name` pattern

All new specialists use `prompt_name`. The `fragments` list is **legacy** — do not use for new agents.

```python
# registry.py — AgentTypeConfig
AgentTypeConfig(
    slug="data-analyst",
    prompt_name="agents/data-analyst",   # Langfuse key; "agents/" prefix → managed
    enabled_tools=["execute_sql", "executar_rag_cliente"],
    tier_required=TierLevel.BASIC,
    tags=["sql", "analytics"],
)

# _WorkerInvoker._get_prompt() — supervisor.py / orchestrator.py
variables = {
    "nome_empresa": nome_empresa,
    "agent_name": cfg.name,
    "agent_description": cfg.description,
    "sql_schema_context": sql_schema_context,   # from VariableExtractor.render_sql_schema()
    "kb_context": kb_context,                   # from VariableExtractor.render_kb_context()
    # + context_sections, tools_description, collected_context, etc.
}
prompt = await build_prompt(name=cfg.prompt_name, variables=variables, context_service=...)
```

### Skill (L2)

```python
# skills.py — SkillDefinition
SkillDefinition(
    name="analyze_csv",
    prompt_name="skill:analyze_csv:system",     # "skill:" prefix → managed
    required_tool_names=["list_csv_datasets", "peek_csv_columns", "execute_csv_query"],
    max_turns=5,
    tags=["analytics", "csv"],
)
# SkillFactory intersects required_tool_names with parent agent's enabled_tools at runtime
```

### Tool prompt (internal LLM call inside tool_pool_api)

```python
# Inside executar_sql_agent tool:
PromptLoader.load("tool/sql-generation", variables={"query": nl_query, "table_info": schema})
# "tool/" prefix → NOT managed, builtin only
```

### L4 Orchestrator prompts

```python
# orchestrator.py nodes call build_prompt directly:
await build_prompt("orchestrator/parse-intent", variables={"workers_description": ...})
await build_prompt("orchestrator/decompose", variables={...})
await build_prompt("orchestrator/plan", variables={"workers_description": ...})
await build_prompt("orchestrator/synthesize", variables={...})
# "orchestrator/" prefix → Langfuse-managed
```

---

## Variable Injection — How Context Reaches Prompts

### `sql_schema_context` and `kb_context`

These two variables carry per-client context into every specialist prompt. They are rendered in `supervisor.py` and `orchestrator.py` via `VariableExtractor`:

```python
# supervisor.py — _WorkerInvoker._get_prompt()
from blu_prompt_management.variables import VariableExtractor

sql_schema_context = VariableExtractor.render_sql_schema(
    getattr(client_context, "data_schema", None)
)
kb_context = VariableExtractor.render_kb_context(client_context)
```

`render_sql_schema()` reads `data_schema.table_schemas` (from `sql_table_config` DB rows) and renders a markdown schema block. Returns `""` when no custom rows exist — currently all clients use the static `fragment/sql-schema` fallback (analytics_v2 star schema).

`render_kb_context()` reads `data_freshness`, `data_sources`, `policies`, `company_profile.sector` from `BluClientContext`. Returns `""` when nothing relevant is available.

### Variable inventory (current)

| Variable               | Type | Source                                                            | Injected at                                                                                  |
| ---------------------- | ---- | ----------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `nome_empresa`         | str  | `BluClientContext.nome_empresa`                                   | all agents                                                                                   |
| `agent_name`           | str  | `AgentTypeConfig.name`                                            | specialist prompts                                                                           |
| `agent_description`    | str  | `AgentTypeConfig.description`                                     | specialist prompts                                                                           |
| `sql_schema_context`   | str  | `VariableExtractor.render_sql_schema(client_context.data_schema)` | SQL agents; falls back to `fragment/sql-schema` static content when no table configs exist  |
| `kb_context`           | str  | `VariableExtractor.render_kb_context(client_context)`             | RAG agents                                                                                   |
| `context_sections`     | str  | `BluClientContext` summary                                        | orchestrator workers                                                                         |
| `workers_description`  | str  | `AgentTypeRegistry.build_supervisor_description(tier)`            | orchestrator prompts                                                                         |
| `company_profile`      | str  | `_render_company_profile(client_context.company_profile)`         | frontdesk, specialist prompts                                                                |
| `query`                | str  | tool call argument                                                | `tool/sql-generation`, `tool/rag-query-rewrite`                                              |
| `max_turns`            | int  | `SkillDefinition.max_turns` or `config.max_turns`                 | skill prompts                                                                                |

### `client_id` vs `cliente_id`

Always use `client_id` — this is the standard across DB, Python code, and MCP headers. `cliente_id` is legacy and must not appear in new code.

---

## Prompt Syntax

### Langfuse prompts (Mustache — `{{variable}}`)

Used in `.md` source files under `prompts/` and pushed to Langfuse. Mustache syntax:

```
{{variable}}                           — substitute variable
{{#variable}}...{{/variable}}          — render if variable is truthy
{{^variable}}...{{/variable}}          — render if variable is falsy (inverse)
```

Example with conditional schema:

```
{{#sql_schema_context}}
{{sql_schema_context}}
{{/sql_schema_context}}
{{^sql_schema_context}}
# DATABASE SCHEMA (Analytics V2 — Star Schema)
...static fallback...
{{/sql_schema_context}}
```

### Builtin templates (Jinja2 — `{{ variable }}`)

Used in `templates.py` `BUILTIN_TEMPLATES`. Jinja2 syntax (spaces inside braces):

```
{{ variable }}                         — substitute variable
{% if variable %}...{% endif %}        — conditional block
```

---

## Current Prompt Inventory

### Langfuse-managed (pushed, `production` label)

**Orchestrator (L4)**

- `orchestrator/parse-intent` — intent classifier; outputs JSON with complexity/plan
- `orchestrator/decompose` — task decomposer; outputs JSON sub_tasks by domain
- `orchestrator/plan` — execution planner; maps sub-tasks to L3 skill slugs
- `orchestrator/synthesize` — response synthesizer; coherent multi-skill output

**Supervisor fragments** (content in Langfuse, runtime loads as builtins)

- `fragment/supervisor-role` — identity, `{{nome_empresa}}`, optional context sections

**Context-gatherer fragments** (Langfuse-stored)

- `fragment/context-gatherer-base` — 4 jobs (schema, transaction, routine, KB)
- `fragment/transaction-extraction-rules` — field extraction + confirmation gate
- `fragment/schema-mapping-workflow` — 4-step schema mapping
- `fragment/routine-definition-workflow` — routine creation via L3 skill slugs
- `fragment/knowledge-curation-workflow` — KB curation with RAG conflict detection
- `fragment/confirmation-patterns` — two-turn confirmation gate for write tools

**Schema** (static — no dynamic injection since all clients use analytics_v2)

- `fragment/sql-schema` — full analytics_v2 star schema (tables, joins, rules, examples)

**Skills**

- `skill:simple_sql_query:system` — single-turn SQL lookup for Frontdesk; no schema context block
- `skill:analyze_csv:system` — DuckDB CSV analysis; optional `{{sql_schema_context}}` block
- `skill:rag_search:system` — RAG retrieval; optional `{{kb_context}}` block
- `skill:extract_document:system` — OCR document extraction
- `skill:generate_rfq:system` — RFQ procurement dispatch (transactional)
- `skill:write_to_kb:system` — knowledge-base persistence
- `skill:generate_report:system` — multi-source executive report

### Builtins only (in `templates.py`)

**Skill classification**

- `classify/skill-intent` — LLM prompt to select a SKILL_REGISTRY entry given a task + skills list; used by `_create_classify_skill_intent_node()` in `builder.py`

**Identity (standalone agents)**

- `fragment/standalone-base` — persona, session metadata, language rule
- `fragment/standalone-response` — output format and quality standards

**SQL domain**

- `fragment/sql-rules` — SQL generation constraints, column/join rules, defaults
- `fragment/sql-examples` — few-shot SQL patterns

**Tool prompts** (`tool/*`)

- `tool/sql-generation` — NL→SQL inside `executar_sql_agent`
- `tool/rag-query-rewrite` — pre-retrieval query rewriting
- `tool/rag-query` — RAG synthesis inside `executar_rag_cliente`

---

## Critical Patterns

### Only `build_prompt` — never `compose_prompt`

`compose_prompt` is removed from the codebase. The single entry point is:

```python
from blu_prompt_management import build_prompt

prompt = await build_prompt(name="agents/<slug>", variables=variables, context_service=cs)
```

### New specialists use `prompt_name`, not `fragments`

```python
# CORRECT — new agent
AgentTypeConfig(slug="my-agent", prompt_name="agents/my-agent", ...)

# WRONG — do not do this for new agents
AgentTypeConfig(slug="my-agent", fragments=["fragment/standalone-base", ...], ...)
```

The `fragments` list is kept only for existing agents that haven't been migrated. Migrate to `prompt_name` when touching a legacy agent.

### Fragment ordering (when maintaining legacy fragment-stack agents)

1. **Identity** (`standalone-base`) — persona, company name, language rule
2. **Domain knowledge** (`sql-schema`, `rag-search`) — what the agent knows
3. **Domain rules** (`sql-rules`, `fallback-strategy`) — constraints on tool use
4. **Workflow** (`*-workflow`) — which tools to call, in what order
5. **Response** (`standalone-response`) — output format (ALWAYS LAST)

Tool USAGE instructions belong in workflow fragments. Rules fragments contain constraints only.

### Workers description

`workers_description` is generated from `AgentTypeRegistry.build_supervisor_description(tier)` and injected into orchestrator prompts (`orchestrator/parse-intent`, `orchestrator/plan`). It is dynamic per tier — do not add a static routing table; it will drift.

### RAG synthesis boundary

`executar_rag_cliente` returns raw passages. The agent synthesises. No synthesis inside the tool. `tool/rag-query-rewrite` runs pre-retrieval only.

---

## Anti-Patterns

| Anti-pattern                                                             | Fix                                                                                                                                                                                                                    |
| ------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Using `compose_prompt()`                                                 | Use `build_prompt(name, variables)` — `compose_prompt` is removed                                                                                                                                                      |
| New agent uses `fragments` list                                          | Use `prompt_name="agents/<slug>"`                                                                                                                                                                                      |
| Tool USAGE instructions in a rules/schema fragment                       | Move to the agent's workflow fragment                                                                                                                                                                                  |
| `schema_description` variable in new Langfuse prompts                    | Use `sql_schema_context` (rendered by `VariableExtractor.render_sql_schema()`); `schema_description` is still used internally by `build_frontdesk_prompt()` for legacy compat but must not appear in new agent prompts |
| Variables fabricated in the prompt without a source                      | Wire the variable in `_WorkerInvoker._get_prompt()` or `factory.py`                                                                                                                                                    |
| Schema hardcoded in both agent prompt and tool prompt                    | Agent prompt uses `{{sql_schema_context}}`; tool prompt gets `table_info` as argument                                                                                                                                  |
| Skill `required_tool_names` includes tool not in agent's `enabled_tools` | Add to agent's `enabled_tools` or remove from skill                                                                                                                                                                    |
| Using `cliente_id` anywhere                                              | Use `client_id` consistently                                                                                                                                                                                           |
| Two SQL tools in same agent (`execute_sql` + `executar_sql_agent`)       | Use only one: `execute_sql` for agents with schema context, `executar_sql_agent` otherwise                                                                                                                             |
| Builtin fallback missing for a Langfuse-managed prompt                   | Add `PromptTemplateConfig` to `BUILTIN_TEMPLATES` in `templates.py`                                                                                                                                                    |
| `"connection" in str(e)` for Langfuse circuit breaker                    | Use `_is_connection_error()` — excludes 404s which trigger false circuit break                                                                                                                                         |
| Calling `_WorkerInvoker` directly from orchestrator                      | Use `make_execute_step_node` which compiles specialist subgraphs via `use_specialist_graph`; never bypass the graph layer                                                                                              |
| Building a new Frontdesk using `use_supervisor_graph`                    | Frontdesk uses `use_default_graph()` via `get_frontdesk_graph()`; supervisor fan-out is kept for legacy `get_supervisor_graph()` path                                                                                  |

---

## Reference Documentation

- `references/prompt_engineering_patterns.md` — variable assembly, Langfuse syntax, anti-patterns
- `references/agentic_system_design.md` — graph patterns, layer architecture, context flow
- `references/llm_evaluation_frameworks.md` — how to validate prompt changes in this repo
