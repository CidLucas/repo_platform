# patterns.md — Code Patterns Baseline (#57)

> Baseline de convenções esperadas, derivado de docs/system_reference/ e inspeção da codebase.
> Usado como referência para o code review T57.2 (patterns consistency).

## 1. Python Conventions (libs/ + services/)

### Naming
- **Files:** snake_case (ex: `routine_functions.py`, `blu_supabase_client/`)
- **Functions:** snake_case (ex: `get_cash_position()`, `enqueue_polp_sync()`)
- **Classes:** PascalCase (ex: `ChatService`, `AgentState`, `ResourceResolver`)
- **Variables:** snake_case (ex: `client_id`, `tenant_config`)
- **Constants:** UPPER_SNAKE (ex: `DOMAIN_SECTIONS`, `VALID_ENTITY_TYPES`)

### Imports
- stdlib first, third-party second, project imports third (separated by blank line)
- `from libs.blu_models.src.models import ...` — full path from repo root
- No circular imports between libs/

### Structure
- Each lib: `src/<lib_name>/` with `__init__.py`
- Services: `src/<service_name>/` with `main.py` entry
- `__init__.py` exports public API
- `setup.py` or `pyproject.toml` at lib root

### Types
- Pydantic models for data (blu_models)
- Type hints on all public functions
- `mypy` / `pyright` strict mode expected

### Error Handling
- Custom exception hierarchy in each service
- `try/except` with specific exception types
- Correlation IDs passed via context
- Logging at appropriate level (info/warning/error)

### Logging
- Structured logging (JSON)
- Logger per module: `logger = logging.getLogger(__name__)`
- Include `client_id`, `correlation_id` in context

### Config
- Environment variables via `.env`
- `config.py` per service with typed config
- Supabase credentials from env, never hardcoded

## 2. TypeScript/TSX Conventions (apps/blu_v3/, packages/)

### Naming
- **Files:** PascalCase for components (`ChatRoom.tsx`), camelCase for utils (`api.ts`)
- **Components:** PascalCase (React convention)
- **Functions:** camelCase (ex: `fetchUnifiedTasks`)
- **Interfaces/Types:** PascalCase (ex: `UnifiedTask`, `AgendaExternalEvent`)
- **Hooks:** `use` prefix (ex: `useIntegrations`, `useOnboardingDraft`)

### Imports
- React first, third-party second, project third
- `import { Something } from '@/components/...'` (path aliases)
- Named exports preferred over default exports

### Structure
- `src/components/` — React components
- `src/hooks/` — custom hooks
- `src/api/` — API client functions
- `src/types/` — TypeScript interfaces
- `src/utils/` — pure utility functions
- `src/store/` — state management (Zustand)
- Tailwind classes in className

### Types
- `eslint` + `tsc --noEmit` expected
- Zod schemas for runtime validation
- No `any` without explicit justification

### Error Handling
- Error boundaries at room level
- `try/catch` with typed error responses
- User-facing errors in PT-BR

### Config
- Vite env vars: `VITE_` prefix
- `vite.config.ts` with path aliases

## 3. SQL Conventions (supabase/migrations/)

### Naming
- **Tables:** snake_case (ex: `fato_transacoes`, `dim_clientes`)
- **Columns:** snake_case (ex: `client_id`, `created_at`)
- **Functions:** snake_case with schema prefix (ex: `analytics_v2.get_kpi_mtd_comparison`)
- **Triggers:** `trg_` prefix (ex: `trg_drop_bigquery_fdw_server`)

### Structure
- Migrations: `YYYYMMDDHHMMSS_description.sql`
- Schemas: `public`, `analytics_v2`
- Functions grouped by domain

### Patterns
- `ON CONFLICT` for upserts
- `RETURNS TABLE(...)` for set-returning functions
- RLS policies per table
- CASCADE deletes where appropriate

## 4. Cross-Cutting Patterns

### Security
- Input validation at API boundary (Pydantic/Zod)
- RLS on Supabase tables
- JWT auth with expiry
- SQL via parameterized queries or RPC — no raw string interpolation
- Secrets in `.env` only (`.secrets.baseline` for audit)

### Testing
- Python: `pytest` with fixtures in `conftest.py`
- TypeScript: `jest` or `vitest`
- Integration tests for DB operations
- Mock external services (Supabase, Google, Langfuse)

### Documentation
- Python docstrings (Google style)
- README.md per lib/service
- Architecture decisions in HERMES.md
- System reference in docs/system_reference/
- Backlog in docs/backlog/

## 5. Anti-Patterns (flag during review)

| Anti-pattern | Severity | Example |
|---|---|---|
| Raw SQL string formatting | P0 | `f"SELECT * FROM {table}"` |
| Duplicated validation logic | P1 | Same Pydantic model in 3 libs |
| Hardcoded secrets | P0 | API key in source |
| Missing type hints | P1 | `def process(data):` |
| Unhandled promise | P1 | `fetch(...)` without await/catch |
| N+1 queries | P1 | Loop over `supabase.from(...).select()` |
| Missing error boundary | P1 | Component without try/catch |
| `any` type in TS | P2 | `const x: any = ...` |
| Wildcard imports | P2 | `from module import *` |
| Inconsistent naming | P2 | `camelCase` in Python file |
