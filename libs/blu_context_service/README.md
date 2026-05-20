# blu_context_service

Client context loader for the Blu agent system — Redis-cached, Supabase-backed.

## Overview

`ContextService` is the single source of truth for per-client context inside agents.
It reads from Supabase and caches in Redis so subsequent turns within a session are
served from cache without a DB round-trip.

The resolved context is injected into `AgentState` at `context_enrichment_node` and
used to populate prompt variables (`{{ nome_empresa }}`, `{{ tier }}`, etc.) and to
filter available tools by tier.

## Key Technologies

- **Database:** PostgreSQL via `blu_db_connector` (Supabase)
- **Cache:** Redis
- **Package Manager:** Poetry

## Installation

```bash
poetry add blu-context-service
```

## Usage

```python
from blu_context_service import ContextService

ctx = ContextService(redis_url="redis://localhost:6379")

# Load context for a client (cached after first call)
client_context = await ctx.get_context(client_id="uuid-here")

print(client_context.nome_empresa)   # "Acme Ltda"
print(client_context.tier)           # "SME"
print(client_context.enabled_tools)  # ["executar_rag_cliente", "execute_sql", …]
```

## BluClientContext Fields

| Field                    | Type        | Description                                   |
| ------------------------ | ----------- | --------------------------------------------- |
| `client_id`              | `str`       | Client UUID                                   |
| `nome_empresa`           | `str`       | Company display name                          |
| `tier`                   | `str`       | Tier level string (`FREE`, `BASIC`, `SME`, …) |
| `enabled_tools`          | `list[str]` | Tools enabled for this client                 |
| `schema_description`     | `str`       | DB schema for SQL agents                      |
| `available_integrations` | `list[str]` | Connected data sources                        |

## Caching Strategy

- Cache key: `client_context:{client_id}`
- TTL: configurable (default ~5 min)
- Invalidation: call `ctx.invalidate(client_id)` after any client config change

## Integration with AgentState

The `context_enrichment_node` in `blu_agent_framework` calls this service and writes
the resolved values directly into `AgentState`:

```python
state["client_context"] = client_context.dict()
state["nome_empresa"]   = client_context.nome_empresa
state["tier"]           = client_context.tier
```

These fields are then available to all downstream nodes and prompt templates.
