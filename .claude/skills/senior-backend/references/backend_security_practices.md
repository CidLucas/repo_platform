# Backend Security Practices

## Overview

This repo's security posture depends on a few shared conventions: JWT decoding in shared auth code, tenant isolation in Supabase/RLS, careful separation between service-role and user-scoped access, and explicit protection for internal automation surfaces.

## Patterns and Practices

### Pattern 1: Centralize JWT decoding and auth result construction

**Description:**
Sampled services do not manually parse JWTs inside business logic. They depend on `blu_auth` and convert tokens into typed auth results at the API boundary.

**When to Use:**

- New protected FastAPI endpoints
- Refactors to auth middleware or dependencies
- Any endpoint that needs tenant or user identity from Supabase tokens

**Implementation:**

```python
claims = decode_jwt(credentials.credentials)
return AuthResult(
    client_id=UUID(claims.sub),
    auth_method=AuthMethod.JWT,
    external_user_id=claims.sub,
    email=claims.email,
)
```

**Benefits:**

- Consistent error handling and token validation
- Lower risk of auth drift across services
- Easier to test and review

**Trade-offs:**

- Requires preserving the shared auth contract
- Service-specific assumptions about `client_id` vs `external_user_id` must be understood

### Pattern 2: Tenant isolation lives in the data layer, not only the API layer

**Description:**
Supabase tables, storage paths, and SQL RPCs are part of the authorization model. Many operations rely on RLS or tenant-scoped helpers.

**Implementation:**

```sql
... security invoker
... set search_path = analytics_v2, public
... where client_id = public.get_my_client_id()
```

**Benefits:**

- Defense in depth
- Lower blast radius for route-level mistakes

**Trade-offs:**

- Security bugs can hide in SQL as well as Python

### Pattern 3: Internal endpoints need explicit non-user auth

Sampled internal automation endpoints in `tool_pool_api` use shared bearer secrets and webhook validation patterns. These are separate from end-user JWT auth.

**Examples:**

- Shared bearer token checks for internal dispatch routes
- Twilio webhook validation dependency hooks
- Health/info endpoints exposed separately from protected business endpoints

## Guidelines

### Code Organization

- Keep auth dependencies close to API entrypoints, not buried inside business logic
- Distinguish public, private, admin, webhook, and internal cron surfaces in router layout
- Keep secret-dependent integrations behind dedicated service or helper layers

### Performance Considerations

- Security controls here also protect availability: DB timeouts and degraded startup modes reduce outage blast radius
- Fail open only where the repo already treats the dependency as optional, such as some observability bootstraps or MCP degraded startup in tool services

### Security Best Practices

- Reuse `blu_auth` instead of homegrown JWT handling
- Be explicit about service-role usage
- Validate webhook signatures or internal bearer secrets on non-user entrypoints
- Avoid leaking raw exceptions in auth-sensitive paths
- Treat storage and SQL access as part of authorization, not just persistence

## Common Patterns

### Degraded startup without silent security bypass

- `tool_pool_api` can start without MCP if initialization fails, but it does not silently disable unrelated auth concerns

### Health endpoints remain fast and narrow

- `/health` is typically lightweight
- richer health checks can be mounted via observability bootstrap helpers

### Background tasks do not bypass the security model by accident

- fire-and-forget tasks are used for persistence or evaluation in sampled agent flows
- they should inherit already-resolved tenant context rather than rediscovering it implicitly

## Anti-Patterns to Avoid

### Treating Supabase user UUID and internal tenant ID as interchangeable everywhere

Sampled code shows they are not always the same conceptual identifier.

### Using service-role clients for convenience in user-facing code paths

That bypasses the repo's intended RLS protections.

### Letting internal endpoints rely on obscurity alone

Cron, webhook, and admin surfaces need explicit protection.

## Tools and Resources

### Recommended Tools

- `blu_auth`
- `blu_supabase_client`
- `blu_context_service`
- Service health and observability helpers

### Further Reading

- `services/atendente_core/src/atendente_core/api/auth.py`
- `services/atendente_core/src/atendente_core/api/router.py`
- `services/tool_pool_api/src/tool_pool_api/main.py`
- `/memories/repo/blu-mono-architecture.md`

## Unknowns To Verify Before Security-Sensitive Refactors

- The full production secret-management story beyond sampled env vars and Supabase usage was not exhaustively mapped here
- Not every webhook or internal route was reviewed in this pass
- Some auth semantics may differ across legacy services that were not sampled

## Conclusion

Security work in this repo should preserve the existing shared boundaries: auth in shared libs, tenant enforcement in Supabase/RLS, and explicit protection for internal automation entrypoints.
