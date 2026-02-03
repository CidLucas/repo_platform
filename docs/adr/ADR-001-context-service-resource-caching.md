# ADR-001: Context Service as Single Source of Truth for Client Resources

**Status:** Accepted
**Date:** 2026-01-29
**Deciders:** Lucas Cruz
**Technical Story:** Modernize prompt management and unify resource caching

## Context and Problem Statement

The Vizu platform evolved with multiple libraries handling client-scoped data:
- `vizu_context_service` for client auth and context caching
- `vizu_prompt_management` for prompt templates and versioning
- Direct Supabase calls scattered in tool modules

This created code duplication (180+ hardcoded lines in nodes.py), performance issues (SQL configs fetched per-query), and inconsistent patterns across the codebase.

## Decision Drivers

* Need for single source of truth for client-scoped resources
* Performance: SQL configs should be cached, not fetched per query
* Code elimination: Remove 200+ lines of duplicate prompt code
* Consistency: All tools should follow same patterns
* MCP exposure: Prompts should be accessible via MCP protocol

## Considered Options

1. **Extend context_service** - Add resource caching methods, keep prompt_management for templates
2. **Create new resource_service** - Separate lib for tool resources
3. **Keep tools independent** - Each tool fetches its own resources

## Decision Outcome

Chosen option: **"Extend context_service"**, because:
- Already handles Redis caching infrastructure
- Already used by most tools for client context
- Minimal new dependencies
- Follows existing singleton patterns

## Architecture After Change

```
┌─────────────────────────────────────────────────────────────────────┐
│                    vizu_context_service (Extended)                  │
│                     "Single Source of Truth"                        │
├─────────────────────────────────────────────────────────────────────┤
│  Client Context         │  Tool Resources        │  Prompts         │
│  ───────────────        │  ───────────────       │  ────────        │
│  • nome_empresa         │  • sql_table_configs   │  • system prompt │
│  • tier                 │  • rag_collection      │  • task prompts  │
│  • enabled_tools        │  • integration_tokens  │                  │
│  • prompt_base          │  • knowledge_base_cfg  │                  │
│  • horario              │                        │                  │
├─────────────────────────────────────────────────────────────────────┤
│         Redis Pool (Singleton)    +    Supabase Client (Singleton)  │
└─────────────────────────────────────────────────────────────────────┘
```

## Singleton Patterns (Mandatory)

All shared resources MUST follow existing singleton patterns:

| Resource Type | Pattern | Example |
|---------------|---------|---------|
| Connection Pools | Global variable + cleanup | `_redis_pool`, `_supabase_client` |
| Clients | Singleton via `get_*()` | `get_supabase_client()`, `get_qdrant_client()` |
| Configuration | `@lru_cache` decorator | `get_settings()`, `get_llm_settings()` |
| Services | Per-request with singleton pools | `ContextService(cache_service=redis_service)` |

**Anti-patterns to avoid:**
- Creating clients inside functions (creates new connection per call)
- Reading config inside hot paths (should be cached at startup)
- Missing cleanup functions (memory leaks on shutdown)

## Consequences

### Positive

* Single import for all client-scoped data
* ~210 lines eliminated from atendente_core
* SQL configs cached in Redis (300s TTL)
* Consistent patterns across all tools
* Prompts exposed via MCP tools

### Negative

* context_service becomes larger (more methods)
* Tighter coupling between tools and context_service

### Neutral

* No database migration required
* Backward compatible (V3 template already has all content)

## Technical Details

### New Methods in ContextService

```python
async def get_sql_table_configs(self, cliente_id: UUID) -> list[dict]:
    """Get SQL table configs with Redis caching."""

async def get_cached_prompt(
    self, name: str, cliente_id: UUID | None,
    loader: PromptLoader, variables: dict
) -> str:
    """Get prompt with Redis caching for raw template."""
```

### Files Changed

| File | Action |
|------|--------|
| `libs/vizu_context_service/.../context_service.py` | +80 lines (new methods) |
| `libs/vizu_prompt_management/.../loader.py` | +50 lines (Supabase backend) |
| `libs/vizu_prompt_management/.../variables.py` | +15 lines (tools description builder) |
| `libs/vizu_prompt_management/.../dynamic_builder.py` | NEW (unified prompt building) |
| `services/tool_pool_api/.../prompt_module.py` | NEW (native MCP prompts) |
| `services/atendente_core/.../nodes.py` | -180 lines (major refactor) |
| `services/atendente_core/.../service.py` | -20 lines (removed legacy framework toggle) |
| `services/tool_pool_api/.../sql_module.py` | Uses cached configs via context_service |

### Files Deleted (Legacy Cleanup)

| File | Reason |
|------|--------|
| `services/tool_pool_api/.../prompts.py` | Replaced by native @mcp.prompt in prompt_module.py |
| `libs/vizu_prompt_management/.../mcp_builder.py` | Replaced by native @mcp.prompt decorator |

## Implementation Summary

| Phase | Action | Status |
|-------|--------|--------|
| 1 | Extend context_service with `get_sql_table_configs()`, `get_cached_prompt()` | ✅ |
| 2 | Add Supabase backend to PromptLoader, create dynamic_builder.py | ✅ |
| 3 | Create prompt_module with native MCP prompts | ✅ |
| 4 | Refactor atendente_core, delete hardcoded prompts, remove legacy framework | ✅ |
| 5 | Update SQL module to use cached configs | ✅ |
| 6 | Legacy cleanup: delete deprecated prompts.py and mcp_builder.py | ✅ |

## Links

* Related: `libs/vizu_prompt_management` - Prompt templates and versioning
* Related: `libs/vizu_context_service` - Client context and caching
* Related: `services/tool_pool_api` - MCP server with tools
