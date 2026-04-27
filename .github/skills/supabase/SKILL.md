---
name: supabase
description: "Use when doing ANY task involving Supabase. Triggers: Supabase products (Database, Auth, Edge Functions, Realtime, Storage, Vectors, Cron, Queues); client libraries and SSR integrations (supabase-js, @supabase/ssr) in Next.js, React, SvelteKit, Astro, Remix; auth issues (login, logout, sessions, JWT, cookies, getSession, getUser, getClaims, RLS); Supabase CLI or MCP server; schema changes, migrations, security audits, Postgres extensions (pg_graphql, pg_cron, pg_vector)."
metadata:
  author: supabase
  version: "0.1.0"
---

# Supabase

Repo-adapted guidance for Supabase work in `vizu-mono`.

## Core Principles

**1. Verify current Supabase docs first, then fit the answer to this repo's established patterns.**
Supabase changes quickly, and this repo also has strong local conventions around RLS, `get_my_client_id()`, service-role usage, and Edge Functions. Check both.

**2. In this repo, tenant isolation is the primary constraint.**
Most Supabase changes are not just schema changes. They affect JWT identity mapping, RLS, analytics RPCs, dashboard queries, agent flows, storage access, or Edge Functions. A change that works but weakens tenant isolation is wrong.

**3. Verify with the narrowest real check available.**
After any fix, run the closest validation you can: a targeted SQL query, a focused test, an RPC smoke test, or an Edge Function check. A migration or policy change without validation is incomplete.

**4. Recover from Supabase errors by checking the data model, not only the code path.**
When a change fails, inspect RLS, `verify_jwt`, tenant mapping, service-role vs user client usage, and RPC/view security posture before retrying blindly.

**5. Prefer existing repo primitives over new ad hoc patterns.**
Common boundaries already exist:

- `vizu_supabase_client` for Python service access
- `public.get_my_client_id()` for client scoping in SQL/RLS
- root `supabase/migrations/` for schema history
- `supabase/config.toml` for Edge Function `verify_jwt` posture

## Repo-Specific Ground Truth

### Main usage surfaces

- `supabase/migrations/`: canonical schema and RLS history
- `supabase/functions/`: Edge Functions, some JWT-protected and some intentionally public
- `libs/vizu_supabase_client`: shared client access for Python services
- `tests/test_dashboard_rpcs.py` and `tests/test_rls_regression.py`: focused validation anchors
- service code in `services/` that mixes user-scoped and service-role clients depending on the operation

### Canonical tenant-scoping pattern

The repo-standard pattern is not generic `auth.uid() = user_id` everywhere.

- Use `external_user_id = auth.uid()` to map the logged-in Supabase user to the internal client record
- Use `public.get_my_client_id()` in RLS and SQL for client-scoped data
- Do not authorize by email or `user_metadata`

### Service-role usage in this repo

Service-role access exists and is legitimate in a few places, including upload/processing flows and Edge Functions. It must be explicit and justified.

Use service-role when:

- backend code must bypass RLS for trusted server-side work
- storage or ingestion services perform privileged writes
- Edge Functions validate the caller and then perform privileged operations

Do not use service-role when:

- a user-scoped client or `SECURITY INVOKER` RPC can express the same access safely
- the shortcut would bypass client isolation in dashboard or user-facing flows

## Repo Security Checklist

When touching auth, RLS, views, functions, storage, or Edge Functions, check these repo-specific traps first:

- **Auth and session security**
  - Never use email for authorization. This repo already had a real incident caused by non-unique email mapping.
  - Never use `user_metadata` for authorization.
  - Prefer `external_user_id = auth.uid()` as the user-to-client join.

- **API key and client exposure**
  - Never expose `SUPABASE_SERVICE_ROLE_KEY` outside trusted backend and Edge Function contexts.
  - Frontend code should never cache tenant identity in a way that can go stale across users.

- **RLS, views, and privileged database code**
  - Prefer `client_id::text = public.get_my_client_id()` for client-scoped policies.
  - Prefer `SECURITY INVOKER` plus explicit `search_path` on user-facing RPCs.
  - Do not move tenant filtering from SQL into trusted application code just because it is easier.
  - Remember that `UPDATE` needs a compatible `SELECT` policy.

- **Storage access control**
  - Check both bucket/object policies and the backend path using them.
  - Upload and document-processing services may use privileged access intentionally; keep that boundary explicit.

- **Edge Function auth**
  - `verify_jwt = true` is the default secure posture in this repo.
  - Any function with `verify_jwt = false` should be treated as an exception requiring justification.
  - If a function accepts a `client_id` input, verify ownership server-side instead of trusting the payload.

For general Supabase security concerns not covered here, fetch the product security docs before implementing.

## Supabase CLI

Always discover commands via `--help` rather than guessing. CLI behavior changes, and this repo mixes local files with remote project workflows.

```bash
supabase --help                    # All top-level commands
supabase <group> --help            # Subcommands (e.g., supabase db --help)
supabase <group> <command> --help  # Flags for a specific command
```

**Repo guidance:**

- Prefer MCP SQL/advisor tools when available because they fit the current authenticated workflow better.
- If you need a new migration file, create it through the Supabase workflow rather than inventing a timestamp by hand.
- Keep migration names descriptive because this repo has a long-lived migration history with feature-phase naming.

**Version check and upgrade:** Run `supabase --version` to check. For CLI changelogs and version-specific features, consult the [CLI documentation](https://supabase.com/docs/reference/cli/introduction) or [GitHub releases](https://github.com/supabase/cli/releases).

## Supabase MCP Server

For setup instructions, server URL, and configuration, see the [MCP setup guide](https://supabase.com/docs/guides/getting-started/mcp).

**Troubleshooting connection issues** — follow these steps in order:

1. **Check if the server is reachable:**
   `curl -so /dev/null -w "%{http_code}" https://mcp.supabase.com/mcp`
   A `401` is expected (no token) and means the server is up. Timeout or "connection refused" means it may be down.

2. **Check `.mcp.json` configuration:**
   Verify the project root has a valid `.mcp.json` with the correct server URL. If missing, create one pointing to `https://mcp.supabase.com/mcp`.

3. **Authenticate the MCP server:**
   If the server is reachable and `.mcp.json` is correct but tools aren't visible, the user needs to authenticate. The Supabase MCP server uses OAuth 2.1 — tell the user to trigger the auth flow in their agent, complete it in the browser, and reload the session.

## Supabase Documentation

Before implementing any Supabase feature, find the relevant documentation. Use these methods in priority order:

1. **MCP `search_docs` tool** (preferred — returns relevant snippets directly)
2. **Fetch docs pages as markdown** — any docs page can be fetched by appending `.md` to the URL path.
3. **Web search** for Supabase-specific topics when you don't know which page to look at.

Then map the answer back to this repo's current patterns around:

- `get_my_client_id()`
- Edge Function `verify_jwt`
- service-role boundaries
- analytics RPCs and tests

## Making and Committing Schema Changes

For this repo, the safest path is:

1. Iterate with direct SQL where appropriate.
2. Validate against the real access model.
3. Generate or update the migration only when the shape is correct.

Do not make speculative RLS changes in a migration file without first proving the behavior against the target queries or tests.

**When ready to commit** your changes to a migration file:

1. **Run advisors** → `supabase db advisors` (CLI v2.81.3+) or MCP `get_advisors`. Fix any issues.
2. **Review the repo security checklist above** if your changes involve views, functions, triggers, storage, or Edge Functions.
3. **Ensure tenant mapping still uses the canonical pattern**.
4. **Verify with focused tests or queries**.

## Reference Guides

- **Skill Feedback** → [references/skill-feedback.md](references/skill-feedback.md)
  **MUST read when** the user reports that this skill gave incorrect guidance or is missing information.

## High-Signal Repo Checks

Use these anchors before making broad Supabase claims in this repo:

- `supabase/config.toml`
- `supabase/functions/`
- `supabase/migrations/`
- `tests/test_dashboard_rpcs.py`
- `tests/test_rls_regression.py`
- `/memories/repo/security-audit-rls-fix.md`

## Unknowns To Verify

- Some older migrations still contain comments or transitional patterns that do not reflect the current preferred approach.
- Not every Edge Function has been reviewed recently; treat `verify_jwt = false` entries as suspect until confirmed.
- Some backend services may still rely on legacy Supabase access wrappers not covered by this skill.
