# blu_agent_framework

Reusable LangGraph agent framework for the Blu 4-layer multi-agent architecture.

## Architecture

```
L4  Orchestrator    decomposes multi-step requests → plans → routes to L3
L3  Specialists     domain experts (frontdesk, context-gatherer, …)
L2  Skills          ephemeral tool bundles dispatched by L3 via SkillFactory
L1  Tools           stateless MCP tools executed by MCPToolExecutor
```

Entry point is always the **Frontdesk** L3 agent. It handles simple requests inline and
hands off complex ones to the L4 Orchestrator.

## Installation

```bash
poetry add blu-agent-framework
```

## Key Modules

| Module             | Responsibility                                                     |
| ------------------ | ------------------------------------------------------------------ |
| `registry.py`      | `AgentTypeRegistry` — L3 agent type catalog (`AgentTypeConfig`)    |
| `skills.py`        | `SKILL_REGISTRY` — L2 skill catalog (`SkillDefinition`)            |
| `orchestrator.py`  | L4 planner graph (parse → decompose → plan → execute → synthesize) |
| `builder.py`       | `AgentBuilder` — fluent graph compiler                             |
| `nodes.py`         | Built-in graph nodes (registered via `@NodeRegistry.register`)     |
| `routing.py`       | Conditional routing functions                                      |
| `state.py`         | `AgentState` TypedDict + `create_initial_state()`                  |
| `skill_factory.py` | `SkillFactory` — compiles and runs L2 skill subgraphs              |
| `mcp_executor.py`  | `MCPToolExecutor` — MCP protocol tool calls                        |

## AgentBuilder

```python
from blu_agent_framework import AgentBuilder

graph = (
    AgentBuilder()
    .with_llm(model="openai:gpt-4o-mini")
    .with_checkpointer(redis_url="redis://localhost:6379")
    .with_mcp(mcp_executor)
    .use_default_graph()
    .build()
)
```

### Default Graph Topology

```
init_node → classify_intent_node → context_enrichment_node
  → respond_node ←───────────────────────────────────┐
       ├── [tool call] execute_single_tool_node ──────┤
       ├── [skill]     run_skill_node                 │
       └── [done]      end_node                       │
                             (loops until ended) ──────┘
```

### Custom Nodes

```python
from blu_agent_framework import NodeRegistry, AgentState

@NodeRegistry.register("my_validation")
async def validate(state: AgentState) -> dict:
    if not state.get("data_ready"):
        return {"error": "Not ready"}
    return {}
```

## Agent Type Registry (L3)

Agent types declare which tools and prompts they use. The factory resolves them by slug.

```python
from blu_agent_framework.registry import AgentTypeRegistry, AgentTypeConfig
from blu_tool_registry import TierLevel

AgentTypeRegistry.register(AgentTypeConfig(
    slug="my-specialist",
    name="My Specialist",
    prompt_name="agents/my-specialist",   # Langfuse key
    enabled_tools=["execute_sql", "executar_rag_cliente"],
    max_turns=8,
    min_tier=TierLevel.BASIC,
    routing_hint="Handles domain X queries.",
    tags=["domain-x"],
))
```

**Registered agents:**

| Slug               | Prompt             | Min Tier | Purpose                           |
| ------------------ | ------------------ | -------- | --------------------------------- |
| `frontdesk`        | `agents/frontdesk` | BASIC    | Entry point, inline RAG/SQL       |
| `context-gatherer` | fragments          | BASIC    | Data mapping, routines, knowledge |

## Skill Registry (L2)

Skills are ephemeral subgraphs with a focused tool set. They run inside L3 agents
when `run_skill_node` detects a match from `specialists/classify-skill-intent`.

```python
from blu_agent_framework.skills import SKILL_REGISTRY, SkillDefinition

SKILL_REGISTRY["my_skill"] = SkillDefinition(
    name="My Skill",
    slug="my_skill",
    required_tools=["my_tool_a", "my_tool_b"],
    prompt_name="skill:my_skill:system",
    max_turns=4,
    on_max_turns="return_partial",
    tags=["my-domain"],
)
```

**Registered skills:**

| Slug               | Tools                                                                                 | Max Turns |
| ------------------ | ------------------------------------------------------------------------------------- | --------- |
| `analyze_csv`      | `list_csv_datasets`, `peek_csv_columns`, `execute_csv_query`                          | 5         |
| `rag_search`       | `executar_rag_cliente`                                                                | 3         |
| `extract_document` | `extract_document_with_ocr`, `summarize_document_sections`, `extract_structured_data` | 4         |
| `write_to_kb`      | `write_summary_to_kb`                                                                 | 2         |

## Orchestrator (L4)

The orchestrator handles requests that span multiple L3 domains.

```
parse_intent → [complex] → decompose → plan → execute_step (loop) → synthesize
            → [simple]  → execute_step
            → [uncertain] → confirm → execute_step
```

It reads available L3 agents from `AgentTypeRegistry` and builds a `plan` list with
`{id, skill_slug, task, depends_on, is_mutation, requires_confirmation, status, result}`.
Mutation steps gate on `confirmed=True` before execution.

## AgentState

```python
class AgentState(TypedDict):
    # Identifiers
    session_id: str
    client_id: str          # use client_id everywhere, not cliente_id
    thread_id: str
    channel: str            # "whatsapp" | "web" | "api"

    # Messages
    messages: Annotated[list[BaseMessage], add_messages]

    # Execution
    turn_count: int
    max_turns: int
    ended: bool
    end_reason: str | None

    # Tool execution
    tool_to_execute: str | None
    tool_args: dict | None
    tool_results: Annotated[list[dict], add]
    last_tool_result: dict | None

    # Skill routing
    complexity: str | None        # "simple" | "complex" | "uncertain"
    current_skill: str | None
    skill_results: Annotated[list[dict], add]

    # Client context
    client_context: dict
    nome_empresa: str
    tier: str

    # Orchestrator planning
    plan: list[dict] | None
    step_results: dict[str, str]
    pending_confirmation: dict | None
    confirmed: bool | None

    # Elicitation
    pending_elicitation: dict | None
    elicitation_response: Any | None
    elicitation_history: list[dict]

    # Error handling
    error: str | None
    errors: Annotated[list[str], ...]   # capped at 20
```

State is persisted across turns via Redis (`langgraph.checkpoint.redis`).
`session_id` maps 1:1 to LangGraph `thread_id`.

## MCP Integration

```python
from blu_agent_framework import get_mcp_manager, initialize_mcp

await initialize_mcp("http://tool_pool_api:8000/mcp")
manager = get_mcp_manager()
tools = await manager.list_tools()
```

`MCPToolExecutor` wraps the manager and injects `client_id` into every tool call.

## Observability

Langfuse v3 tracing is wired via `CallbackHandler`. Pass the handler through
`AgentBuilder.with_langfuse(session_id, user_id, metadata)`. Prompt versions are
linked automatically via `LoadedPrompt.langfuse_prompt`.

## Adding a New Agent

Use the `/agent-smith` skill in Claude Code for guided scaffolding, or manually:

1. Register an `AgentTypeConfig` in `registry.py`.
2. Add a prompt file to `libs/blu_prompt_management/src/blu_prompt_management/prompts/`
   and register it in `templates.py` as fallback.
3. Register any new tools with `ToolMetadata` in `libs/blu_tool_registry`.
4. Write tests in `libs/blu_agent_framework/tests/`.

See `docs/agent_system_map.md` for the full system reference.
