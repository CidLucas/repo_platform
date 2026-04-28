---
name: supabase-postgres-best-practices
description: Postgres performance optimization and best practices from Supabase. Use this skill when writing, reviewing, or optimizing Postgres queries, schema designs, or database configurations.
license: MIT
metadata:
  author: supabase
  version: "1.1.1"
  organization: Supabase
  date: January 2026
  abstract: Comprehensive Postgres performance optimization guide for developers using Supabase and Postgres. Contains performance rules across 8 categories, prioritized by impact from critical (query performance, connection management) to incremental (advanced features). Each rule includes detailed explanations, incorrect vs. correct SQL examples, query plan analysis, and specific performance metrics to guide automated optimization and code generation.
---

# Supabase Postgres Best Practices

Repo-adapted Postgres optimization guide for `blu-mono`.

This repo uses Postgres through Supabase as an application boundary, not just a backing store. The highest-value optimization work here usually touches one of these surfaces:

- analytics RPCs and views in `analytics_v2`
- RLS-aware client-scoped reads
- dashboard/reporting queries validated by integration tests
- ingestion and sync tables with large client-specific workloads
- Edge Functions or backend services that call SQL through Supabase clients

## When to Apply

Reference these guidelines when:

- Writing SQL queries or designing schemas
- Implementing indexes or query optimization
- Reviewing database performance issues
- Configuring connection pooling or scaling
- Optimizing for Postgres-specific features
- Working with Row-Level Security (RLS)

In this repo, also apply them when:

- adding or changing SQL RPCs under `supabase/migrations/`
- optimizing dashboard metrics that currently round-trip through Python or frontend code
- changing any query that relies on `public.get_my_client_id()`
- reviewing large analytics migrations such as the `analytics_v2` cleanup phases

## Rule Categories by Priority

| Priority | Category                 | Impact      | Prefix      |
| -------- | ------------------------ | ----------- | ----------- |
| 1        | Query Performance        | CRITICAL    | `query-`    |
| 2        | Connection Management    | CRITICAL    | `conn-`     |
| 3        | Security & RLS           | CRITICAL    | `security-` |
| 4        | Schema Design            | HIGH        | `schema-`   |
| 5        | Concurrency & Locking    | MEDIUM-HIGH | `lock-`     |
| 6        | Data Access Patterns     | MEDIUM      | `data-`     |
| 7        | Monitoring & Diagnostics | LOW-MEDIUM  | `monitor-`  |
| 8        | Advanced Features        | LOW         | `advanced-` |

## How to Use

Start with repo reality before applying generic optimization rules:

1. Identify whether the workload is user-scoped/RLS-scoped or service-role.
2. Check whether the logic belongs in SQL/RPC instead of app-side aggregation.
3. Verify whether an existing analytics RPC, test, or migration already encodes the expected contract.
4. Optimize the narrow slice and validate with the closest available test or query.

High-signal repo anchors:

```
supabase/migrations/
tests/test_dashboard_rpcs.py
tests/test_rls_regression.py
/memories/repo/security-audit-rls-fix.md
/memories/repo/rag-pipeline-optimization.md
```

Repo-specific heuristics:

- Prefer `SECURITY INVOKER` RPCs with explicit `search_path` for user-facing analytics reads.
- Prefer `client_id::text = public.get_my_client_id()` for tenant scoping on client-owned tables.
- Do not optimize by replacing RLS-aware SQL with service-role fan-out in Python.
- Favor SQL-side aggregation for dashboard/reporting workloads over repeated row hydration.
- Keep long-running request protection in mind; sampled services already set statement and idle timeouts.

## Highest-Value Rules In This Repo

### 1. Optimize the contract, not just the query plan

If a dashboard surface makes repeated client-side or Python-side aggregation calls, the first optimization question is whether the shape should become a single SQL RPC.

### 2. Tenant isolation is part of performance work

An optimization that bypasses `get_my_client_id()` or replaces user-scoped access with hidden service-role reads is a regression, not an improvement.

### 3. Use indexes to support the real predicate shape

In this repo, the important predicates are often combinations of:

- `client_id`
- date/time windows
- sync or ingestion status
- foreign keys into analytics dimensions

Index decisions should reflect those patterns, not generic advice divorced from the workload.

### 4. Treat migrations as performance artifacts

Large analytics migrations in this repo often encode both behavior and performance strategy. Review neighboring migrations before introducing a new pattern.

### 5. Validate with focused tests where they already exist

`tests/test_dashboard_rpcs.py` is a better validation anchor for dashboard SQL changes than a vague claim that the query is "more efficient".

## Unknowns To Verify

- Not every large operational table and index strategy has been mapped in this skill.
- Some historical migrations contain transitional or superseded patterns.
- Background jobs and Edge Functions may create query shapes not covered by the sampled dashboard tests.

## References

- https://www.postgresql.org/docs/current/
- https://supabase.com/docs
- https://wiki.postgresql.org/wiki/Performance_Optimization
- https://supabase.com/docs/guides/database/overview
- https://supabase.com/docs/guides/auth/row-level-security
