# Blu Platform — Claude Code Context

## Architecture: 4-Layer Progressive Context Disclosure

```
L4 Orchestrator  →  decomposes multi-step requests, routes to specialists
L3 Specialist    →  domain expert, classify → skill dispatch → respond
L2 Skill         →  ephemeral tool bundle via SkillFactory (no checkpointer)
L1 Tool          →  stateless MCP execution via MCPToolExecutor
```

The Orchestrator calls L3 only. L3 calls L2 via `SkillFactory`. Never skip layers.
Entry point: Frontdesk specialist (routes simple queries inline, hands off complex to Orchestrator).

## Repo Structure

- `apps/blu_v3/` — React frontend
- `libs/` — Shared Python libraries (blu\_\*)
- `services/agent_api/` — Agent API (primary backend service)
- `supabase/` — Edge functions + DB

## Key Architectural Patterns

### Agent Building

- `AgentBuilder` chains: `.with_llm()`, `.with_checkpointer()`, `.with_mcp()`, `.use_default_graph()`
- Nodes registered via `@NodeRegistry.register("name")`
- Graph compiled with Redis checkpointer (`create_checkpointer(redis_url)`)
- Agent types in `AgentTypeRegistry` (`libs/blu_agent_framework/src/blu_agent_framework/registry.py`)
- Skills in `SKILL_REGISTRY` (`libs/blu_agent_framework/src/blu_agent_framework/skills.py`)

### State Management

- `AgentState` TypedDict + `create_initial_state()` in `libs/blu_agent_framework/src/blu_agent_framework/state.py`
- `session_id` = LangGraph `thread_id`; `client_id` is the client UUID (used in all queries)
- Context from `ContextService` → `BluClientContext` (Redis-cached, Supabase-backed)
- Key state fields: `client_context`, `nome_empresa`, `tier`, `step_results`, `skill_results`, `plan`

### Tool Execution

- `MCPToolExecutor` calls `tool_pool_api` via MCP protocol
- `ToolRegistry` catalogs tools with `ToolMetadata` in `libs/blu_tool_registry/`
- Tier control: `TierLevel` enum (`FREE | BASIC | SME | PREMIUM | ENTERPRISE | ADMIN`)
- Tool categories: `ToolCategory` enum (`RAG | SQL | SCHEDULING | DOCKER_MCP | PUBLIC | GOOGLE | CUSTOM`)

### Prompts

- **Single entry point**: `build_prompt(name, variables)` from `blu_prompt_management`
- `compose_prompt` is removed — do not use it
- Non-managed prompts (fragment/*): load from `BUILTIN_TEMPLATES` in `templates.py` (Jinja2, flat vars)
- Langfuse-managed prefixes: `orchestrator/`, `agents/`, `skill:` — try Langfuse, fall back to builtin
- Builtin template variables use flat Jinja2 syntax: `{{ nome_empresa }}`, `{{ schema_description }}`
- New agents: declare `prompt_name="agents/<slug>"` on `AgentTypeConfig` (not `fragments` list)
- Prompt files (Langfuse source): `libs/blu_prompt_management/src/blu_prompt_management/prompts/`
- Builtin fallback registry: `libs/blu_prompt_management/src/blu_prompt_management/templates.py`

### Factory Pattern

- `UnifiedAgentFactory` in `services/agent_api/src/agent_api/core/factory.py`
- `get_supervisor_graph(tier)` → Frontdesk graph cached per tier (being renamed to `get_frontdesk_graph`)
- `get_standalone_agent(session_id, client_id, agent_catalog_id)` → per-session compiled graph
- `BuiltAgent` contains `graph + system_prompt + client_context`
- Agent catalog in Supabase `agent_catalog` table

## When Implementing

- Follow decorator-based node registration
- Use `AgentBuilder` chaining, don't break API
- Prefer `prompt_name` over `fragments` for new agents
- Only `build_prompt(name, variables)` for prompts — never `compose_prompt`
- `client_id` everywhere (not `cliente_id`) — DB and Python code are consistent
- Write tests in `libs/*/tests/`
