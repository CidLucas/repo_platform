# Database Optimization Guide

## Overview

This repo uses Supabase/Postgres as more than a persistence layer. It is also an application boundary for analytics, dashboard RPCs, tenant isolation, storage metadata, and internal operational state. Optimization work should respect that architecture instead of bypassing it in service code.

## Patterns and Practices

### Pattern 1: Prefer SQL/RPC aggregation for analytics surfaces

**Description:**
For dashboard/reporting-style reads, the repo often uses SQL views and RPCs in Supabase instead of Python-side fan-out or repeated row hydration.

**When to Use:**

- Dashboard endpoints
- Aggregated operational summaries
- Reusable analytics reads needed by multiple clients or services

**Implementation:**

```sql
create or replace function analytics_v2.get_order_indicators(...)
returns table (...)
language sql
stable
security invoker
set search_path = analytics_v2, public
as $$
  ...
$$;
```

**Benefits:**

- Keeps expensive filtering and grouping in Postgres
- Encourages one source of truth for analytics logic
- Works naturally with RLS-aware access patterns

**Trade-offs:**

- SQL complexity can accumulate quickly
- Ownership is harder if the contract is not documented

### Pattern 2: Treat RLS scope as part of query design

**Description:**
Optimization cannot weaken tenant isolation. Query design must account for whether the caller is using service-role access or user-scoped access.

**Implementation:**

```python
# service-role
client = get_supabase_client(use_service_role=True)

# user-scoped or RPC path
... SECURITY INVOKER ...
```

**Key rule:**

- If data should respect the current tenant automatically, prefer SQL that composes with repo-standard tenant resolution helpers rather than assuming Python-side filtering is enough.

### Pattern 3: Guard DB sessions with timeouts at the service boundary

`atendente_core` and `tool_pool_api` both set session-level timeouts through middleware. Optimization here is not only about speed; it is also about protecting the pool and preventing lock or idle leaks.

**Observed settings in sampled services:**

- `statement_timeout = '30s'`
- `idle_in_transaction_session_timeout = '5min'`

## Guidelines

### Code Organization

- Keep migration logic in `supabase/migrations/`
- Keep service code thin when SQL is the better home for the logic
- When adding RPCs, keep signatures typed and documented in tests or service wrappers

### Performance Considerations

- Favor views/RPCs for repeated analytics logic
- Minimize cross-service round trips for report/dashboard pages
- Reuse integration test patterns such as `tests/test_dashboard_rpcs.py` when validating shape and isolation
- Benchmark the narrow slice you touched instead of hand-waving at performance

### Security Best Practices

- `SECURITY INVOKER` plus explicit `search_path` is the preferred posture for user-facing SQL RPCs in the sampled analytics work
- Use service-role only when the backend truly needs to bypass RLS
- Do not optimize by moving tenant filtering from SQL into trust-based Python code

## Common Patterns

### Analytics RPC contract tests

- RPC shape tests live in Python integration tests
- Isolation expectations are asserted explicitly

### Monorepo command centralization

- Use `make migrate`, `make migrate-prod`, and related targets rather than inventing ad hoc migration commands per change

### Shared query safety for generated SQL

- `blu_sql_factory` exists to parse, validate, and rewrite generated SQL
- if your optimization touches LLM-generated SQL flows, update the validation/rewrite path rather than bypassing it

## Anti-Patterns to Avoid

### Python-side aggregation over large tenant datasets

If the same grouping/filtering can be expressed once in SQL, repeated Python aggregation is usually the wrong optimization target here.

### Hidden service-role reads for user-facing endpoints

That may look faster or simpler in the short term, but it erodes the repo's tenant-isolation model.

### Long-running requests with no DB timeout protections

The sampled services already defend against this. Do not remove those protections casually.

## Tools and Resources

### Recommended Tools

- Supabase migrations under `supabase/migrations/`
- Integration tests under `tests/`
- `blu_sql_factory`
- Root `Makefile`

### Further Reading

- `tests/test_dashboard_rpcs.py`
- `services/tool_pool_api/src/tool_pool_api/main.py`
- `services/atendente_core/src/atendente_core/main.py`
- `/memories/repo/blu-mono-architecture.md`

## Unknowns To Verify Before Aggressive Optimization

- Full indexing strategy across the operational tables was not mapped here
- Not every analytics view or materialized-view lifecycle is documented in this guide
- Some services may still use older DB access paths not covered by the sampled tests

## Conclusion

In `blu-mono`, the best database optimization is usually better SQL structure, clearer tenant scoping, and fewer app-layer round trips, not clever Python refactors detached from the Supabase boundary.
