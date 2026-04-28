# Api Design Patterns

## Overview

This document captures backend design patterns that are actually visible in `blu-mono` today. It is meant to prevent generic architecture advice from being mistaken for repo convention.

## Patterns and Practices

### Pattern 1: Follow the owning service's FastAPI construction style

**Description:**
Services are not perfectly uniform, but each service has a stable local pattern. Copy the owning service's structure before introducing a new abstraction.

**When to Use:**

- Adding a new endpoint to an existing FastAPI service
- Refactoring startup/shutdown behavior
- Introducing routers, health checks, or observability bootstrap

**Implementation:**

```python
# file_upload_api: explicit factory
def create_app() -> FastAPI:
    app = FastAPI(..., lifespan=lifespan)
    app.include_router(api_router, prefix="/v1/upload")
    return app

# atendente_core / tool_pool_api: module-level app with lifespan
app = FastAPI(..., lifespan=lifespan)
app.include_router(api_router, prefix="/api/v1")
```

**Benefits:**

- Lower local surprise for maintainers
- Easier review because diffs fit nearby code
- Safer startup/shutdown handling in services with runtime-specific concerns

**Trade-offs:**

- There is no single universal service template yet
- Cross-service abstractions should be introduced only when duplication is real and stable

### Pattern 2: Shared libraries hold reusable infrastructure

**Description:**
Reusable concerns live in `libs/` rather than being reimplemented in each service.

**Common shared boundaries:**

- `blu_auth`
- `blu_supabase_client`
- `blu_context_service`
- `blu_db_connector`
- `blu_sql_factory`
- `blu_observability_bootstrap`

**Implementation:**

```python
from blu_auth.core.jwt_decoder import decode_jwt
from blu_context_service.context_service import ContextService
from blu_supabase_client import get_supabase_client
from blu_observability_bootstrap import setup_observability
```

**Benefits:**

- Avoids service-local rewrites of security and DB concerns
- Keeps service code thinner
- Makes platform-wide fixes easier to roll out

**Trade-offs:**

- Shared libraries become architectural choke points
- A weak abstraction in `libs/` can spread quickly

### Pattern 3: Singleton heavy resources, per-request lightweight context

**Description:**
`atendente_core` demonstrates the repo pattern clearly: expensive graph/runtime objects are singleton-like, while tenant/request context is injected per call.

**Implementation:**

```python
class AtendenteService:
    def __init__(self):
        self.graph = get_agent_graph()
        self.db = BluDBConnector()

    async def process_message(..., context_service: ContextService, ...):
        ...
```

**When to Use:**

- Expensive graph/model/tool initialization
- Durable network clients
- Request flows that need fresh tenant or auth context

**Benefits:**

- Lower per-request overhead
- Better reuse of warm resources

**Trade-offs:**

- Requires discipline around mutable shared state
- Test isolation matters more

### Pattern 4: Router layer stays thin, service/core layer owns orchestration

**Description:**
FastAPI routers typically assemble dependencies, normalize HTTP concerns, and delegate orchestration.

**Examples in repo:**

- `atendente_core.api.router` delegates to `AtendenteService`
- auth is injected through dependencies, not reimplemented in business logic
- transport-specific details such as headers, Twilio forms, and SSE remain at the router edge

## Guidelines

### Code Organization

- Prefer `api/`, `core/`, and `services/` separation where the service already uses it
- Put reusable cross-service logic in `libs/`, not in a random service helper file
- Keep route schemas near routes unless the service already centralizes them elsewhere
- Reuse root Makefile and service-local config conventions instead of inventing new command entrypoints

### Performance Considerations

- Treat graph/tool/bootstrap work as startup or singleton cost when the service already does
- Prefer DB-side aggregation for analytics/reporting endpoints
- Protect DB sessions with timeouts where that pattern is already established

### Security Best Practices

- Reuse `blu_auth` JWT parsing and model types
- Make tenant scoping explicit at the route or RPC layer
- Separate public, private, admin, webhook, and internal routers clearly

## Common Patterns

### Observability-first startup

- `setup_observability(...)` is called during app construction when available
- health endpoints exist even when optional runtime dependencies fail
- shutdown paths flush telemetry rather than silently discarding it

### MCP as a mounted sub-application

- `tool_pool_api` mounts MCP under `/mcp` inside lifespan
- initialization is guarded so the service can still boot in degraded mode

### Background fire-and-forget tasks with explicit references

- `atendente_core` keeps a `_background_tasks` set so async tasks are not garbage collected prematurely
- use this only when non-blocking persistence/evaluation is acceptable

## Anti-Patterns to Avoid

### Reimplementing shared auth or Supabase access in each service

If `blu_auth`, `blu_supabase_client`, or `blu_context_service` already solve the concern, reusing them is usually lower risk.

### Mixing tenant resolution rules casually

The repo has an important nuance: in some flows the JWT `sub` represents the Supabase user and must be resolved into an internal tenant/client record. Do not assume every `client_id` variable means the same thing in every layer.

### Over-abstracting service bootstrapping

Do not force all services into one bootstrap pattern when their runtime concerns differ.

## Tools and Resources

### Recommended Tools

- Root `Makefile`
- `blu_observability_bootstrap`
- `blu_supabase_client`
- `blu_sql_factory`

### Further Reading

- `services/tool_pool_api/src/tool_pool_api/main.py`
- `services/atendente_core/src/atendente_core/main.py`
- `services/atendente_core/src/atendente_core/core/service.py`
- `services/file_upload_api/src/file_upload_api/main.py`
- `/memories/repo/blu-mono-architecture.md`

## Unknowns To Verify Before Large Changes

- Whether all newer services still follow the same observability conventions
- Which shared libraries are considered stable public APIs versus local implementation details
- Whether there is an intended future unification between app-factory and module-level app patterns

## Conclusion

The right backend pattern in this repo is usually the nearest proven one, not the most abstract one. Start locally, reuse shared libs, and call out subsystem-specific nuance when it is still unclear.
