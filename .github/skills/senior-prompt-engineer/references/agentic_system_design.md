# Agentic System Design

## Architecture Layers

The platform has four layers. Prompts serve different purposes at each layer.

| Layer                      | Runtime                                                  | Prompt surface                                                         | Key file                                                             |
| -------------------------- | -------------------------------------------------------- | ---------------------------------------------------------------------- | -------------------------------------------------------------------- |
| **Supervisor**             | LangGraph, Redis checkpointer, stateful                  | `fragment/supervisor-role` + `supervisor-workers` + `supervisor-rules` | `libs/blu_agent_framework/src/blu_agent_framework/supervisor.py`     |
| **Layer 3 — Domain Agent** | LangGraph, Redis checkpointer, stateful multi-turn       | Fragment list or named `prompt_name` via `AgentTypeConfig`             | `libs/blu_agent_framework/src/blu_agent_framework/registry.py`       |
| **Layer 2 — Skill**        | Ephemeral LangGraph sub-graph, no checkpointer, no Redis | `skill:<name>:system` from Langfuse                                    | `libs/blu_agent_framework/src/blu_agent_framework/skills.py`         |
| **Tool prompts**           | Single LLM call inside tool_pool_api                     | `tool/<name>` from Langfuse                                            | `libs/blu_prompt_management/src/blu_prompt_management/prompts/tool/` |

---

## Core Patterns

### Pattern 1: Supervisor with parallel worker delegation

The supervisor sees only delegation tools (`delegate_to_data_analyst`, etc.), not the underlying tool chains. `AgentTypeRegistry.build_supervisor_description(tier)` generates the `{{ workers_description }}` block dynamically — one entry per accessible agent at the user's tier, using each `AgentTypeConfig.description` and `.routing_hint`.

**Critical:** Never add a static routing table alongside `workers_description`. It will drift as new agents are added to the registry.

The supervisor emits multiple tool calls in a single response when the user's request spans multiple domains. LangGraph dispatches them in parallel via `Send` and merges results through reducers.

```
supervisor-role    — identity, company name, context sections
supervisor-workers — {{ workers_description }} (dynamic, from AgentTypeRegistry)
supervisor-rules   — parallel tool call rule, handle-directly cases, after-reply format
```

### Pattern 2: Layer 3 domain agent — fragment-based assembly

`UnifiedAgentFactory.get_standalone_agent()` in `services/agent_api/src/agent_api/core/factory.py`:

1. Fetches `agent_catalog` row from Supabase — gets slug, prompt_name, agent_config
2. Fetches `agent_sessions` row — gets `collected_context` (CSV datasets, document names, Google OAuth status)
3. Fetches `BluClientContext` via `ContextService.get_client_context_by_id()` — gets `nome_empresa`, `tier`, `data_schema`
4. If the agent has `fragment/sql-schema` in its fragment list, renders `schema_description` from `data_schema` via `_render_schema_description()`
5. Assembles `variables` dict from all of the above
6. Calls `compose_prompt(fragments=registry_cfg.fragments, variables=variables)` or `build_prompt(name=prompt_name, variables=variables)` for named prompts
7. Builds `AgentBuilder` → compiles LangGraph graph → caches as `BuiltAgent`

`BuiltAgent` contains: `graph`, `system_prompt`, `agent_name`, `enabled_tools`, `client_context`, `metadata`.

### Pattern 3: Layer 2 skill — ephemeral sub-graph

`SkillFactory` executes a skill by:

1. Loading the skill's `prompt_name` from Langfuse (`skill:<name>:system`)
2. Intersecting `skill.required_tool_names` with the parent agent's `enabled_tools` — tools not in the parent are silently dropped
3. Building a fresh `AgentBuilder` with the filtered tool set and the skill's system prompt
4. Running the sub-graph with the last N messages from the parent's state as seed
5. Returning the result or raising `SkillTurnLimitError` if `on_max_turns="raise"` and the budget is exceeded

Use `on_max_turns="raise"` only for transactional skills where partial execution causes harm (e.g., `generate_rfq` — partial dispatch to suppliers is invalid). All read/analytics skills use `"return_partial"`.

### Pattern 4: Context assembled before graph execution

All context (company profile, session data, uploaded files, OAuth status, schema mapping) is assembled by the factory before the graph starts. Tools and prompts receive a coherent view of the world at graph init time. The graph never goes back to Supabase or Redis to fetch session metadata mid-run.

Context sources and their prompt variables:

| Variable                                | Source                                                                    |
| --------------------------------------- | ------------------------------------------------------------------------- |
| `nome_empresa`                          | `BluClientContext.nome_empresa` via `ContextService`                      |
| `agent_name` / `agent_description`      | `agent_catalog` row                                                       |
| `collected_context`                     | `agent_sessions.collected_context` (JSON blob)                            |
| `csv_datasets` / `csv_datasets_details` | `collected_context.csv_datasets`                                          |
| `document_names` / `document_count`     | `collected_context.document_names`                                        |
| `google_connected`                      | `bool(collected_context.google_email)`                                    |
| `schema_description`                    | `ContextService.get_sql_table_configs()` → `_render_schema_description()` |
| `workers_description`                   | `AgentTypeRegistry.build_supervisor_description(tier)`                    |
| `context_sections`                      | `BluClientContext` summary for supervisor                                 |

### Pattern 5: Tool-level LLM calls (not agent turns)

Some tools make their own internal LLM call via the prompt loader before or instead of returning data:

- `executar_sql_agent` — calls `tool/sql-generation` with `{query, table_info, context_guidance}` → returns SQL → executes it → returns rows. Client_id filter is injected AFTER the LLM output, not before.
- `executar_rag_cliente` — calls `tool/rag-query-rewrite` with `{query}` → rewrites query for embedding search → vector search → returns raw passages. Synthesis happens in the agent, not the tool.

Tool prompts live in `libs/blu_prompt_management/src/blu_prompt_management/prompts/tool/`.

---

## Tool Ownership Per Agent

Which tools belong to which agent family determines which skills are available:

| Agent                   | SQL tools                                                                   | RAG tools              | Special                                             |
| ----------------------- | --------------------------------------------------------------------------- | ---------------------- | --------------------------------------------------- |
| `data-analyst`          | `execute_sql`, `execute_csv_query`, `list_csv_datasets`, `peek_csv_columns` | —                      | Generates SQL from schema context in system prompt  |
| `report-generator`      | `executar_sql_agent` (NL→SQL black box)                                     | `executar_rag_cliente` | No SQL schema in fragments; uses executar_sql_agent |
| `knowledge-assistant`   | —                                                                           | `executar_rag_cliente` | —                                                   |
| `document-intelligence` | —                                                                           | `executar_rag_cliente` | OCR tools, `write_summary_to_kb`                    |
| `rfq-agent`             | —                                                                           | —                      | Full procurement tool chain                         |

**Rule:** If an agent has `fragment/sql-schema` in its fragment list, it generates SQL itself and should have `execute_sql`, not `executar_sql_agent`. If it has no SQL schema fragments, it must use `executar_sql_agent` as a black box.

---

## Best Practices

### Keep graph nodes narrow

Each node owns one responsibility: supervisor decision, tool execution, elicitation, response synthesis. Prompt changes should not encode workflow control that belongs in graph routing.

### Fragment ordering is meaningful

1. Identity (`standalone-base`) — always first; establishes persona and session context
2. Domain knowledge — schema, RAG tool description, OCR tool description
3. Workflow — step-by-step agent behaviour, which tools to call and when
4. Response (`standalone-response`) — always last; output format and quality standards

### Tool USAGE instructions belong in the workflow fragment

Rules fragments (`sql-rules`) state constraints on SQL generation. The instruction to call `execute_sql` with the generated query belongs in `data-analyst-workflow`, not in `sql-rules`.

### One tool does one job — don't give an agent both the smart and dumb SQL tools

`data-analyst` has schema context → `execute_sql` only.
`report-generator` has no schema context → `executar_sql_agent` only.
Giving both creates ambiguity the LLM will resolve randomly.

### Supervisor workers list is dynamic — never duplicate it statically

`workers_description` is generated from `AgentTypeRegistry.build_supervisor_description(tier)`. A hardcoded routing table in `supervisor-rules` will drift as agents are added.

---

## Anti-Patterns

| Anti-pattern                                                              | Why it fails                                                                                   |
| ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Static routing table alongside dynamic `workers_description`              | Drifts silently as new agents are added to the registry                                        |
| `executar_sql_agent` in an agent with SQL schema fragments                | Agent generates SQL twice (once itself, once in the tool); tool wins unpredictably             |
| `execute_sql` in an agent without SQL schema fragments                    | Agent attempts to write SQL with no schema knowledge; produces invalid queries                 |
| Tool in `skill.required_tool_names` not in parent agent's `enabled_tools` | Silently dropped at runtime; skill behaves differently than its definition                     |
| Tool USAGE instructions in schema or rules fragments                      | Duplicates workflow guidance; creates conflicts when workflow changes                          |
| Language rule only in `standalone-response`                               | Dropped if the fragment is ever removed; should be in `standalone-base`                        |
| Synthesis prompt inside a retrieval tool                                  | Couples retrieval and synthesis; prevents agent from reasoning over multiple retrieval results |

---

## Further Reading

- `libs/blu_agent_framework/src/blu_agent_framework/registry.py`
- `libs/blu_agent_framework/src/blu_agent_framework/skills.py`
- `libs/blu_agent_framework/src/blu_agent_framework/skill_factory.py`
- `libs/blu_agent_framework/src/blu_agent_framework/builder.py`
- `services/agent_api/src/agent_api/core/factory.py`
- `libs/blu_context_service/src/blu_context_service/context_service.py`
