# vizu_tool_registry

Centralized tool discovery and dynamic allocation for Vizu multi-agent architecture.

## Overview

This library provides:

1. **ToolRegistry** - Central registry of all available tools with metadata
2. **TierValidator** - Tier-based access control for tools
3. **DockerMCPBridge** - Integration with Docker MCP toolkit for composable tools

## Key Concepts

### Dynamic Tool Allocation

Instead of hardcoded boolean flags (`ferramenta_rag_habilitada`, etc.), tools are managed through a dynamic list:

```python
# Old way (deprecated)
if client.ferramenta_rag_habilitada:
    tools.append(rag_tool)

# New way
enabled_tools = client.enabled_tools  # ['executar_rag_cliente', 'executar_sql_agent']
available = ToolRegistry.get_available_tools(enabled_tools, tier=client.tier)
```

### Tier-Based Access

Tools are gated by client tier:

| Tier       | Tools Available                                    |
|------------|---------------------------------------------------|
| BASIC      | RAG only                                          |
| SME        | RAG + SQL + Scheduling                            |
| ENTERPRISE | All tools + Docker MCP integrations               |

### Usage

```python
from vizu_tool_registry import ToolRegistry, TierValidator

# Get tools available for a client
available_tools = ToolRegistry.get_available_tools(
    enabled_tools=["executar_rag_cliente", "executar_sql_agent"],
    tier="SME",
    include_docker_mcp=False
)

# Validate client configuration
is_valid, errors = ToolRegistry.validate_client_tools(
    enabled_tools=["executar_sql_agent"],
    tier="BASIC"
)
# is_valid=False, errors=["executar_sql_agent (requires SME, client has BASIC)"]

# Get default tools for a tier upgrade
new_tools = TierValidator.upgrade_tier_tools(
    current_tools=["executar_rag_cliente"],
    new_tier="SME"
)
# ["executar_rag_cliente", "executar_sql_agent", "agendar_consulta"]
```

## Docker MCP Integration

For ENTERPRISE tier clients, additional tools from Docker MCP toolkit:

```python
from vizu_tool_registry import DockerMCPBridge

bridge = DockerMCPBridge()
docker_tools = await bridge.discover_docker_mcp_servers()
# {"github_read": ToolMetadata(...), "slack_send": ToolMetadata(...)}
```

## Installation

```bash
poetry add vizu-tool-registry
```

Or in pyproject.toml:

```toml
vizu-tool-registry = { path = "../../libs/vizu_tool_registry", develop = true }
```
