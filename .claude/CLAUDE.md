# Blu Platform — Claude Code Context

## Repo Structure

- `apps/blu_v3/` — React frontend
- `libs/` — Shared Python libraries (blu\_\*)
- `services/` — Backend services (standalone_agent_api, atendente_core, tool_pool_api)
- `supabase/` — Edge functions + DB

## Key Architectural Patterns

### Agent Building

- `AgentBuilder` chains: `.with_llm()`, `.with_checkpointer()`, `.with_mcp()`, `.use_default_graph()`
- Nodes registered via `@NodeRegistry.register("name")`
- Graph compiled with Redis checkpointer

### State Management

- `AgentState` dataclass, `create_initial_state()` factory
- `session_id` = LangGraph thread_id
- Context from `ContextService` (Redis + Supabase)

### Tool Execution

- `MCPToolExecutor` calls `tool_pool_api` via MCP protocol
- `ToolRegistry` catalogs tools in `BUILTIN_TOOLS`
- Dynamic binding planned via `ToolMetadata` + `get_for_task()`

### Prompts

- Fragment composition: `compose_prompt(fragments=[...], variables={})`
- Fragments in `libs/blu_prompt_management/src/blu_prompt_management/fragments/`

### Factory Pattern

- `StandaloneAgentFactory` builds per-session, caches by `session_id`
- `BuiltAgent` contains graph + system_prompt + context
- Agent catalog in Supabase `agent_catalog` table

## When Implementing

- Follow decorator-based node registration
- Use `AgentBuilder` chaining, don't break API
- Add to `AgentState` for new fields
- Use `ToolMetadata` for tool enrichment
- Keep backward compatibility — existing agents must not break
- Write tests in `libs/*/tests/`
