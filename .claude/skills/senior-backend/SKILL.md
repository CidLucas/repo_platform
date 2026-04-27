---
name: senior-backend
description: Comprehensive backend development skill for building scalable backend systems using NodeJS, Express, Go, Python, Postgres, GraphQL, REST APIs. Includes API scaffolding, database optimization, security implementation, and performance tuning. Use when designing APIs, optimizing database queries, implementing business logic, handling authentication/authorization, or reviewing backend code.
---

# Senior Backend

Repo-adapted backend guidance for `vizu-mono`.

This skill is tuned to the backend patterns that actually appear in this monorepo today:

- Python-first backend services with FastAPI
- Supabase/Postgres as the main data boundary
- JWT auth through `vizu_auth`
- RLS-aware reads plus service-role bypass where appropriate
- analytics-heavy SQL exposed through RPCs and views
- shared libraries under `libs/`
- mandatory observability/bootstrap concerns in production-facing services
- root-level operational workflow through the monorepo `Makefile`

Use this skill when you are:

- adding or reviewing FastAPI services in `services/`
- designing or reviewing Supabase RPCs, views, or migrations in `supabase/`
- wiring shared backend libraries in `libs/`
- checking tenant isolation, auth, internal cron/webhook endpoints, or observability
- documenting backend flows for agents, ingestion, reports, onboarding, or dashboard APIs

## Current Repo Patterns

### Service layout

- `services/atendente_core`: main conversational backend, LangGraph-driven, JWT protected
- `services/tool_pool_api`: MCP/tool backend, admin/internal routers, webhook and dispatch surfaces
- `services/file_upload_api`: upload + document processing entrypoint
- `services/standalone_agent_api`: standalone agent execution surface
- `libs/*`: reusable internal packages, especially auth, Supabase, context, SQL, observability, Google clients, and models

### Infrastructure assumptions

- Root dev workflow is centralized in the repo `Makefile`
- Root `pyproject.toml` defines monorepo tooling, not one deployable backend package
- Docker Compose is the default local orchestration path
- Many development flows use remote Supabase instead of a fully local DB stack

### Service construction patterns

- `file_upload_api` uses an explicit application factory (`create_app()`)
- `atendente_core` and `tool_pool_api` expose module-level FastAPI apps with lifespan handlers
- Lifespan is used for startup/shutdown concerns such as MCP warmup, mounting, and observability flushes
- Health endpoints are expected on backend services

### Cross-cutting concerns

- `vizu_observability_bootstrap` is the standard observability entrypoint when available
- Database timeout middleware is used in at least `atendente_core` and `tool_pool_api`
- JWT validation is centralized through `vizu_auth`
- Shared DB/context helpers live in `vizu_supabase_client`, `vizu_context_service`, and `vizu_db_connector`

## How To Use This Skill In This Repo

### For new FastAPI endpoints

1. Start from the existing service's router and dependency style.
2. Reuse shared auth/context/db helpers before inventing new ones.
3. Preserve the existing response/error style for that service.
4. Add observability and health behavior consistent with neighboring services.
5. Prefer narrow tests or smoke checks around the changed slice.

### For database work

1. Prefer Supabase migrations under `supabase/migrations/`.
2. Keep tenant isolation in SQL, not only in application code.
3. For reusable read APIs, prefer `SECURITY INVOKER` RPCs with explicit `search_path`.
4. Be explicit about whether the caller is service-role or user JWT scoped.
5. If the change feeds dashboard or agent behavior, document the source-of-truth flow.

## Reference Documentation

### Api Design Patterns

See `references/api_design_patterns.md` for concrete service and library patterns in `vizu-mono`.

### Database Optimization Guide

See `references/database_optimization_guide.md` for migration, RPC, and query-shaping guidance rooted in this repo.

### Backend Security Practices

See `references/backend_security_practices.md` for repo-specific auth, RLS, internal endpoint, and secret-handling guidance.

## Actual Stack Snapshot

**Primary backend language:** Python 3.11+
**HTTP framework:** FastAPI
**Database platform:** Supabase/Postgres
**ORM / DB access:** SQLAlchemy/SQLModel in some services, Supabase client wrappers in others
**Auth:** JWT via `vizu_auth`
**Observability:** `vizu_observability_bootstrap`, OTLP, Langfuse in selected flows
**Agent orchestration:** LangGraph/LangChain in `atendente_core`
**Tool protocol:** MCP in `tool_pool_api`
**Async integrations:** Google suite clients, Twilio, background async tasks

## Development Workflow

### Common commands

```bash
make dev
make dev-down
make test
make test-all
make lint
make fmt
make migrate
make migrate-prod
```

### Quality gates

```bash
ruff check .
pytest
make smoke-test
```

### Build context

- Root `pyproject.toml` is for monorepo tooling, not for shipping a single package.
- Individual libs/services may carry their own `pyproject.toml`.
- The repo mixes containerized development with direct local execution depending on the target.

## Best Practices Summary

### Code Quality

- Start from neighboring services and shared libs instead of inventing a new pattern.
- Keep service responsibilities thin; push reusable logic into `libs/` when it is truly shared.
- Prefer explicit dependencies and typed payloads at service boundaries.

### Performance

- Use request/session DB timeouts where the service already does.
- Prefer SQL/RPC aggregation for dashboard-like workloads instead of Python-side fan-out.
- Reuse singleton-heavy resources where the codebase already does so, such as graph instances.

### Security

- Distinguish service-role operations from user-scoped/RLS operations.
- Keep JWT decoding and auth result construction in shared auth code.
- Internal cron/webhook endpoints need explicit auth or signature validation.

### Maintainability

- Preserve the service's existing startup/lifespan pattern.
- Document unknowns instead of fabricating repo knowledge.
- Favor additive, low-risk changes in migrations and routers.

## Known Unknowns

- This skill is grounded in sampled services, not every backend package in the repo.
- Some libs may have evolved APIs not covered in these docs.
- Deployment topology beyond local Docker and Cloud Run-oriented compose files is not fully mapped here.
- When changing a subsystem not covered by the sampled services, verify the local conventions before copying these patterns blindly.

## Resources

- `references/api_design_patterns.md`
- `references/database_optimization_guide.md`
- `references/backend_security_practices.md`

---

name: senior-backend
description: Comprehensive backend development skill for building scalable backend systems using NodeJS, Express, Go, Python, Postgres, GraphQL, REST APIs. Includes API scaffolding, database optimization, security implementation, and performance tuning. Use when designing APIs, optimizing database queries, implementing business logic, handling authentication/authorization, or reviewing backend code.

---

# Senior Backend

Complete toolkit for senior backend with modern tools and best practices.

## Quick Start

### Main Capabilities

This skill provides three core capabilities through automated scripts:

```bash
# Script 1: Api Scaffolder
python scripts/api_scaffolder.py [options]

# Script 2: Database Migration Tool
python scripts/database_migration_tool.py [options]

# Script 3: Api Load Tester
python scripts/api_load_tester.py [options]
```

## Core Capabilities

### 1. Api Scaffolder

Automated tool for api scaffolder tasks.

**Features:**

- Automated scaffolding
- Best practices built-in
- Configurable templates
- Quality checks

**Usage:**

```bash
python scripts/api_scaffolder.py <project-path> [options]
```

### 2. Database Migration Tool

Comprehensive analysis and optimization tool.

**Features:**

- Deep analysis
- Performance metrics
- Recommendations
- Automated fixes

**Usage:**

```bash
python scripts/database_migration_tool.py <target-path> [--verbose]
```

### 3. Api Load Tester

Advanced tooling for specialized tasks.

**Features:**

- Expert-level automation
- Custom configurations
- Integration ready
- Production-grade output

**Usage:**

```bash
python scripts/api_load_tester.py [arguments] [options]
```

## Reference Documentation

### Api Design Patterns

Comprehensive guide available in `references/api_design_patterns.md`:

- Detailed patterns and practices
- Code examples
- Best practices
- Anti-patterns to avoid
- Real-world scenarios

### Database Optimization Guide

Complete workflow documentation in `references/database_optimization_guide.md`:

- Step-by-step processes
- Optimization strategies
- Tool integrations
- Performance tuning
- Troubleshooting guide

### Backend Security Practices

Technical reference guide in `references/backend_security_practices.md`:

- Technology stack details
- Configuration examples
- Integration patterns
- Security considerations
- Scalability guidelines

## Tech Stack

**Languages:** TypeScript, JavaScript, Python, Go, Swift, Kotlin
**Frontend:** React, Next.js, React Native, Flutter
**Backend:** Node.js, Express, GraphQL, REST APIs
**Database:** PostgreSQL, Prisma, NeonDB, Supabase
**DevOps:** Docker, Kubernetes, Terraform, GitHub Actions, CircleCI
**Cloud:** AWS, GCP, Azure

## Development Workflow

### 1. Setup and Configuration

```bash
# Install dependencies
npm install
# or
pip install -r requirements.txt

# Configure environment
cp .env.example .env
```

### 2. Run Quality Checks

```bash
# Use the analyzer script
python scripts/database_migration_tool.py .

# Review recommendations
# Apply fixes
```

### 3. Implement Best Practices

Follow the patterns and practices documented in:

- `references/api_design_patterns.md`
- `references/database_optimization_guide.md`
- `references/backend_security_practices.md`

## Best Practices Summary

### Code Quality

- Follow established patterns
- Write comprehensive tests
- Document decisions
- Review regularly

### Performance

- Measure before optimizing
- Use appropriate caching
- Optimize critical paths
- Monitor in production

### Security

- Validate all inputs
- Use parameterized queries
- Implement proper authentication
- Keep dependencies updated

### Maintainability

- Write clear code
- Use consistent naming
- Add helpful comments
- Keep it simple

## Common Commands

```bash
# Development
npm run dev
npm run build
npm run test
npm run lint

# Analysis
python scripts/database_migration_tool.py .
python scripts/api_load_tester.py --analyze

# Deployment
docker build -t app:latest .
docker-compose up -d
kubectl apply -f k8s/
```

## Troubleshooting

### Common Issues

Check the comprehensive troubleshooting section in `references/backend_security_practices.md`.

### Getting Help

- Review reference documentation
- Check script output messages
- Consult tech stack documentation
- Review error logs

## Resources

- Pattern Reference: `references/api_design_patterns.md`
- Workflow Guide: `references/database_optimization_guide.md`
- Technical Guide: `references/backend_security_practices.md`
- Tool Scripts: `scripts/` directory
