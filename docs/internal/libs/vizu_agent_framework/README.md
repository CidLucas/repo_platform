# vizu_agent_framework

Reusable LangGraph agent framework for Vizu multi-agent architecture.

## Overview

This library provides a shared foundation for building LangGraph-based agents with:
- Composable state management
- Reusable graph nodes (init, elicit, execute_tool, respond, end)
- MCP tool integration
- Redis-backed checkpointing
- Langfuse observability

## Installation

```bash
poetry add vizu-agent-framework
```

## Quick Start

### 1. Define Agent Configuration

```python
from vizu_agent_framework import AgentConfig, AgentBuilder

# Configure agent
config = AgentConfig(
    name="vendas_agent",
    role="Sales Representative",
    elicitation_strategy="sales_pipeline",
    enabled_tools=["executar_rag_cliente", "agendar_consulta"],
    max_turns=15,
    use_langfuse=True,
    model="openai:gpt-4o-mini",
)
```

### 2. Build and Run Agent

```python
from vizu_agent_framework import AgentBuilder

# Build agent graph
builder = AgentBuilder(config)
agent = builder.build()

# Invoke
result = await agent.ainvoke({
    "messages": [HumanMessage(content="Quero agendar um corte")],
    "session_id": "session-123",
    "cliente_id": "client-uuid",
})
```

### 3. Custom Nodes (Optional)

```python
from vizu_agent_framework import AgentBuilder, NodeRegistry

# Register custom node
@NodeRegistry.register("custom_validation")
async def validate_order(state: AgentState) -> dict:
    # Custom validation logic
    if not state.get("order_valid"):
        return {"error": "Invalid order"}
    return {"validated": True}

# Use in builder
builder = AgentBuilder(config)
builder.add_node("validate", "custom_validation")
builder.add_edge("execute_tool", "validate")
builder.add_edge("validate", "respond")
```

## Components

### AgentState

Base state class with common fields:

```python
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    session_id: str
    cliente_id: str
    thread_id: str
    enabled_tools: List[str]
    pending_elicitation: Optional[dict]
    tool_results: List[dict]
    turn_count: int
    ended: bool
```

### AgentConfig

Configuration dataclass:

```python
@dataclass
class AgentConfig:
    name: str                          # Agent identifier
    role: str                          # Agent role description
    elicitation_strategy: str          # Strategy name
    enabled_tools: List[str]           # Enabled tool names
    max_turns: int = 20                # Max conversation turns
    use_langfuse: bool = True          # Enable observability
    model: str = "openai:gpt-4o-mini"  # LLM model
    system_prompt: Optional[str] = None
    redis_url: str = "redis://localhost:6379"
```

### AgentBuilder

Factory for creating agents:

```python
class AgentBuilder:
    def __init__(self, config: AgentConfig):
        ...

    def add_node(self, name: str, handler: str | Callable) -> Self:
        ...

    def add_edge(self, from_node: str, to_node: str) -> Self:
        ...

    def add_conditional_edge(
        self,
        from_node: str,
        router: Callable,
        routes: Dict[str, str]
    ) -> Self:
        ...

    def build(self) -> CompiledGraph:
        ...
```

### Built-in Nodes

- `init`: Initialize agent state
- `elicit`: Gather information via elicitation strategies
- `execute_tool`: Execute MCP tools with context injection
- `respond`: Generate LLM response
- `end`: End conversation

### Routing Functions

- `route_from_elicit`: Route based on elicitation result
- `route_from_tool`: Route based on tool execution result
- `should_continue`: Check if conversation should continue

## MCP Integration

The framework integrates with MCP servers via `vizu_mcp_commons`:

```python
from vizu_agent_framework import MCPToolExecutor

executor = MCPToolExecutor(
    mcp_url="http://tool_pool_api:8000/mcp/v1",
    timeout=30.0,
)

result = await executor.execute(
    tool_name="executar_rag_cliente",
    tool_args={"query": "horário de funcionamento"},
    context={"cliente_id": "..."},
)
```

## Observability

Langfuse integration is built-in:

```python
from vizu_agent_framework import AgentBuilder

builder = AgentBuilder(config)
builder.with_langfuse(
    session_id="session-123",
    user_id="user-456",
    metadata={"channel": "whatsapp"},
)
agent = builder.build()
```

## Creating a New Agent

1. **Create agent service directory:**
```
services/my_agent/
├── src/my_agent/
│   ├── __init__.py
│   ├── main.py
│   ├── core/
│   │   ├── agent.py      # Agent definition
│   │   └── config.py     # Agent-specific config
│   └── api/
│       └── routes.py     # FastAPI routes
├── pyproject.toml
└── Dockerfile
```

2. **Define agent:**
```python
# services/my_agent/src/my_agent/core/agent.py

from vizu_agent_framework import AgentConfig, AgentBuilder
from vizu_tool_registry import ToolRegistry

class MyAgent:
    def __init__(self, cliente_context):
        # Get tools from registry
        available_tools = ToolRegistry.get_available_tools(
            enabled_tools=cliente_context.enabled_tools,
            tier=cliente_context.tier,
        )

        config = AgentConfig(
            name="my_agent",
            role="My Custom Role",
            elicitation_strategy="my_strategy",
            enabled_tools=[t.name for t in available_tools],
        )

        self.agent = AgentBuilder(config).build()

    async def process(self, message: str, session_id: str):
        return await self.agent.ainvoke({
            "messages": [HumanMessage(content=message)],
            "session_id": session_id,
        })
```

3. **Expose via FastAPI:**
```python
# services/my_agent/src/my_agent/api/routes.py

@router.post("/chat")
async def chat(request: ChatRequest):
    agent = MyAgent(request.cliente_context)
    return await agent.process(request.message, request.session_id)
```

## License

MIT
