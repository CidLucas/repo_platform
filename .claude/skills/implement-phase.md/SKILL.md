# Skill: Implement Dynamic Tool Binding Phase

## Context

You are implementing features from a design document into the Blu monorepo.
The repo uses a custom agent framework built on LangGraph with decorator-based node registration.

## Architecture (from existing code)

- `libs/blu_agent_framework/` — AgentBuilder, NodeRegistry, AgentState, MCPToolExecutor
- `libs/blu_tool_registry/` — ToolRegistry with BUILTIN_TOOLS dict
- `libs/blu_prompt_management/` — Fragment-based prompt composition
- `libs/blu_context_service/` — Redis + Supabase context
- `libs/blu_llm_service/` — Model tier routing via get_model()
- `services/standalone_agent_api/` — Factory pattern, session-scoped agents

## Task

Implement the phase described below, following the exact patterns from existing code.

## Phase to Implement: {{PHASE_NAME}}

Phase description: {{PHASE_DESCRIPTION}}

## Steps

### 1. Read Reference Implementations

Read these files to understand exact patterns:

- `libs/blu_agent_framework/src/blu_agent_framework/builder.py` — AgentBuilder pattern
- `libs/blu_agent_framework/src/blu_agent_framework/nodes.py` — NodeRegistry decorator pattern
- `libs/blu_agent_framework/src/blu_agent_framework/state.py` — AgentState fields
- `libs/blu_tool_registry/src/blu_tool_registry/registry.py` — ToolRegistry class
- `libs/blu_tool_registry/src/blu_tool_registry/tools.py` or `BUILTIN_TOOLS` location

### 2. Identify Integration Points

Based on the phase description, identify:

- Which existing files need modification
- Which new files need creation
- How the new code integrates with AgentBuilder, NodeRegistry, ToolRegistry
- What the state flow looks like (which fields are read/written)

### 3. Implement Following Exact Patterns

**For new Pydantic models:**

- Place in appropriate `libs/*/src/*/` directory
- Use `from pydantic import BaseModel, Field`
- Follow existing naming conventions

**For new nodes:**

- Use `@NodeRegistry.register("node_name")` decorator
- Signature: `async def node_name(state: AgentState, config: RunnableConfig) -&gt; dict`
- Return dict with state updates only (not full state)
- Access LLM via `config["configurable"].get("llm")` or closure injection

**For ToolRegistry methods:**

- Add methods alongside existing `_tools: dict[str, Callable]`
- Keep backward compatibility — existing callers must not break

**For AgentBuilder integration:**

- If adding graph nodes, modify `use_default_graph()` or add new method
- Builder methods chain: `.with_llm()`, `.with_checkpointer()`, `.with_mcp()`, etc.

**For state field additions:**

- Add to `AgentState` dataclass
- Update `create_initial_state()` if field needs initialization
- Document field purpose in docstring

### 4. Write Tests

- Place in `libs/*/tests/` matching the lib structure
- Use pytest, follow existing test patterns
- Mock Redis/Supabase where needed

### 5. Verify Integration

Check that:

- `standalone_agent_api/factory.py` can still build agents
- Existing agent_catalog entries still work
- New functionality is opt-in (feature flags or new catalog fields)

## Output

- List of files modified/created
- Explanation of state flow changes
- Test commands to run
- Any breaking changes or migration notes
