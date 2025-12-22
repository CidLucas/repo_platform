# Vizu Mono — Claude Code Quick Reference Guide

**Last Updated:** December 2025

This guide helps Claude Code understand the vizu-mono repository structure, shared libraries, architectural patterns, and development workflows. Use this as your primary reference when working on any task in this monorepo.

---

## 0. Work Principles & Standards ⭐

These are the **core principles** that guide all development in the Vizu monorepo. Every code change, feature addition, or refactoring **MUST** adhere to these standards.

### 0.1 Modularity 🧩

**Principle:** Code should be organized into independent, self-contained modules with clear responsibilities.

**In Practice:**
- ✅ **DO:** Create separate modules for distinct functionalities
  ```python
  # Good: Separate modules
  libs/vizu_auth/          # Authentication only
  libs/vizu_llm_service/   # LLM interactions only
  libs/vizu_rag_factory/   # RAG chain creation only
  ```

- ❌ **DON'T:** Create monolithic modules that do everything
  ```python
  # Bad: God module
  libs/vizu_utils/
    ├── auth.py
    ├── llm.py
    ├── rag.py
    ├── db.py
    └── everything_else.py
  ```

**Service Level:**
- Each service should have a **single, clear responsibility**
- Use `services/<service>/src/<service>/` structure with submodules:
  ```
  services/atendente_core/src/atendente_core/
  ├── api/          # HTTP layer (routes, dependencies)
  ├── core/         # Business logic (graph, nodes, state)
  ├── data_access/  # Database layer
  └── services/     # External service integrations
  ```

**Library Level:**
- Each library should solve **one problem domain**
- Avoid cross-domain dependencies (e.g., `vizu_auth` shouldn't depend on `vizu_llm_service`)

---

### 0.2 Features & Code Reusability ♻️

**Principle:** Write code once, reuse everywhere. Achieve 95% code reuse across similar services.

**The Reusability Hierarchy:**
1. **Libraries** (`libs/`) — Shared utilities, models, clients
2. **Frameworks** (`vizu_agent_framework`) — Reusable patterns
3. **Service-specific code** — Only unique business logic

**Examples in the Repo:**

✅ **GOOD — 95% Reuse via vizu_agent_framework:**
```python
# services/vendas_agent/src/vendas_agent/core/agent.py (~150 lines)

from vizu_agent_framework import AgentConfig, AgentBuilder

config = AgentConfig(
    name="vendas_agent",
    role="Sales Representative",
    elicitation_strategy="sales_pipeline",
    enabled_tools=["executar_rag_cliente", "agendar_consulta"],
)

agent = AgentBuilder(config).build()
```

✅ **GOOD — Shared Models:**
```python
# All services use vizu_models
from vizu_models import Cliente, Agendamento, Produto
```

❌ **BAD — Duplication:**
```python
# services/service_a/src/service_a/models.py
class Cliente(Base):
    id = Column(UUID)
    # ...

# services/service_b/src/service_b/models.py
class Cliente(Base):  # DUPLICATE!
    id = Column(UUID)
    # ...
```

**Checklist Before Writing New Code:**
1. Does a library already exist for this? Check `libs/`
2. Can I extend an existing library instead of creating new code?
3. Will this code be used in multiple services? If yes, create a library
4. Is this pattern reusable? If yes, add to framework

---

### 0.3 Clean Code 🧹

**Principle:** Code should be self-documenting, readable, and maintainable.

**Standards:**

#### Naming Conventions
```python
# Classes: PascalCase
class ClienteContext:
    pass

# Functions/variables: snake_case
def get_client_context(cliente_id: str) -> ClienteContext:
    pass

# Constants: UPPER_SNAKE_CASE
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30.0

# Private methods: _leading_underscore
def _internal_helper():
    pass
```

#### Type Hints (MANDATORY)
```python
# ✅ Good: Modern type hints (Python 3.11+)
def process_message(
    message: str,
    session_id: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pass

# ❌ Bad: No type hints
def process_message(message, session_id, metadata=None):
    pass

# ❌ Bad: Old-style Optional
from typing import Optional
def process_message(message: str, metadata: Optional[dict]) -> dict:
    pass
```

#### Function Length & Complexity
```python
# ✅ Good: Small, focused functions
async def create_client(data: ClienteCreate, db: Session) -> Cliente:
    """Create a new client."""
    client = Cliente(**data.model_dump())
    db.add(client)
    await db.commit()
    return client

# ❌ Bad: Long, complex functions (>50 lines, multiple responsibilities)
async def create_client_and_send_email_and_log_and_notify(...):
    # 200 lines of mixed responsibilities
    pass
```

#### Imports (ruff I001 enforced)
```python
# ✅ Good: Sorted, grouped
import asyncio
import logging
from typing import Any

from fastapi import FastAPI, Depends
from pydantic import BaseModel

from vizu_models import Cliente
from vizu_db_connector import get_db_session

# ❌ Bad: Unsorted, mixed
from vizu_models import Cliente
import asyncio
from fastapi import FastAPI
from vizu_db_connector import get_db_session
import logging
```

#### Error Handling
```python
# ✅ Good: Specific exceptions, clear messages
from fastapi import HTTPException

try:
    client = await get_client(cliente_id)
except ClientNotFoundError as e:
    raise HTTPException(status_code=404, detail=f"Client {cliente_id} not found") from e

# ❌ Bad: Bare except, generic errors
try:
    client = await get_client(cliente_id)
except:
    raise Exception("Error")
```

---

### 0.4 Scalability (No Hardcoding, Always Parameters) 📈

**Principle:** Never hardcode values. Use configuration, environment variables, or parameters.

**Examples:**

❌ **BAD — Hardcoded Values:**
```python
# Bad: Hardcoded model
model = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

# Bad: Hardcoded URLs
response = requests.get("http://localhost:8000/api/tools")

# Bad: Hardcoded limits
if len(results) > 10:
    results = results[:10]
```

✅ **GOOD — Parameterized:**
```python
# Good: Configurable model
from vizu_llm_service.client import get_model

model = get_model(
    tier=settings.LLM_TIER,  # From env var
    temperature=settings.LLM_TEMPERATURE,  # From env var
)

# Good: Configurable URLs
response = requests.get(
    f"{settings.TOOL_POOL_URL}/api/tools",
    timeout=settings.REQUEST_TIMEOUT,
)

# Good: Configurable limits
max_results = config.max_results or 100
if len(results) > max_results:
    results = results[:max_results]
```

**Configuration Pattern (use Pydantic Settings):**
```python
# services/<service>/src/<service>/core/config.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Service config
    SERVICE_NAME: str = "my_service"
    PORT: int = 8000

    # Database
    DATABASE_URL: str

    # LLM
    LLM_PROVIDER: str = "ollama_cloud"
    LLM_TIER: str = "DEFAULT"
    LLM_TEMPERATURE: float = 0.7

    # External services
    TOOL_POOL_URL: str = "http://tool_pool_api:9000"
    REQUEST_TIMEOUT: int = 30

    # Limits
    MAX_RETRIES: int = 3
    MAX_RESULTS: int = 100

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

**Dockerfile Environment Variables:**
```dockerfile
# ✅ Good: Parameterized CMD
CMD uvicorn src.service.main:app --host 0.0.0.0 --port ${PORT:-8000}

# ❌ Bad: Hardcoded port
CMD uvicorn src.service.main:app --host 0.0.0.0 --port 8000
```

---

### 0.5 Tests 🧪

**Principle:** All critical paths must have tests. Aim for >80% coverage on libraries, >60% on services.

**Test Structure:**
```
services/<service>/tests/
├── conftest.py           # Shared fixtures
├── unit/                 # Unit tests (fast, isolated)
│   └── test_service.py
└── integration/          # Integration tests (DB, external APIs)
    └── test_full_flow.py

libs/<lib>/tests/
├── conftest.py
├── test_<module>.py
└── unit/
    └── test_<specific>.py
```

**Test Examples:**

✅ **Unit Test (Fast, Isolated):**
```python
# services/analytics_api/tests/unit/test_indicator_service.py

import pytest
from analytics_api.services.indicator_service import calculate_growth_rate

def test_calculate_growth_rate_positive():
    current = 100
    previous = 80
    assert calculate_growth_rate(current, previous) == 25.0

def test_calculate_growth_rate_zero_previous():
    current = 100
    previous = 0
    assert calculate_growth_rate(current, previous) == 0.0
```

✅ **Integration Test (Database):**
```python
# services/atendente_core/tests/integration/test_full_flow.py

import pytest
from httpx import AsyncClient
from atendente_core.main import app

@pytest.mark.asyncio
async def test_chat_endpoint_with_valid_api_key(test_client: AsyncClient, db_session):
    # Setup
    api_key = "test-api-key-123"

    # Execute
    response = await test_client.post(
        "/chat",
        json={"message": "Hello", "session_id": "test-123"},
        headers={"X-API-KEY": api_key},
    )

    # Assert
    assert response.status_code == 200
    assert "response" in response.json()
```

**Fixtures (conftest.py):**
```python
# services/<service>/tests/conftest.py

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

@pytest.fixture
async def db_session():
    """Provides a clean database session for each test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with AsyncSession(engine) as session:
        yield session
        await session.rollback()

@pytest.fixture
async def test_client():
    """Provides an HTTP client for API testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
```

**Running Tests:**
```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src --cov-report=term-missing

# Run specific tests
poetry run pytest tests/unit/
poetry run pytest tests/integration/test_full_flow.py -v
```

**Test Coverage Goals:**
- **Libraries:** >80% coverage (critical shared code)
- **Services:** >60% coverage (focus on business logic)
- **Critical paths:** 100% coverage (auth, payment, data integrity)

---

### 0.6 Maintainability 🔧

**Principle:** Code should be easy to understand, modify, and debug by any team member.

**Practices:**

#### Clear Documentation
```python
# ✅ Good: Docstrings for public APIs
def execute_rag_search(
    query: str,
    cliente_id: str,
    collection_name: str = "knowledge_base",
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    Execute a RAG search for the given query.

    Args:
        query: Natural language search query
        cliente_id: Client UUID for filtering results
        collection_name: Qdrant collection to search in
        top_k: Number of results to return

    Returns:
        List of search results with metadata

    Raises:
        QdrantConnectionError: If vector DB is unreachable
        ValueError: If cliente_id is invalid
    """
    pass
```

#### Dependency Documentation (pyproject.toml comments)
```toml
# services/<service>/pyproject.toml

[tool.poetry.dependencies]
# === CORE DEPENDENCIES ===
python = ">=3.11,<3.14"
fastapi = "^0.111.0"
uvicorn = {extras = ["standard"], version = "^0.29.0"}

# === LANGCHAIN DEPENDENCIES ===
langgraph = "^0.2"
langgraph-checkpoint-redis = "^0.1.3"  # Redis checkpointing for state persistence

# === VIZU INTERNAL LIBS (only directly used) ===
vizu-models = {path = "../../libs/vizu_models", develop = true}
vizu-db-connector = {path = "../../libs/vizu_db_connector", develop = true}
vizu-agent-framework = {path = "../../libs/vizu_agent_framework", develop = true}
```

#### Service README.md (Mandatory)
```markdown
# Service Name

## Purpose
One-sentence description of what this service does.

## Key Technologies
- FastAPI
- LangGraph
- Redis

## Environment Variables
| Variable | Description | Default |
|----------|-------------|---------|
| DATABASE_URL | PostgreSQL connection string | Required |
| REDIS_URL | Redis connection string | redis://redis:6379 |

## Running Locally
\`\`\`bash
cd services/<service>
poetry install
cp .env.example .env
poetry run uvicorn <service>.main:app --reload
\`\`\`

## Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | /chat | Send message |

## Testing
\`\`\`bash
poetry run pytest
\`\`\`
```

#### CHANGELOG.md for Breaking Changes
```markdown
# Changelog

## [Unreleased]

### Added
- New `execute_batch_search` endpoint for bulk RAG queries

### Changed
- **BREAKING:** `execute_rag_search` now requires `cliente_id` parameter

### Fixed
- Fixed timeout issue in MCP client connection
```

---

### 0.7 Poetry for Environment Management 📦

**Principle:** Use Poetry exclusively for dependency management. No pip, no requirements.txt.

**Standards:**

#### Always Use Poetry Commands
```bash
# ✅ Good
poetry add fastapi
poetry add --group dev pytest
poetry install
poetry lock

# ❌ Bad
pip install fastapi
pip freeze > requirements.txt
```

#### Lock File Discipline
```bash
# CRITICAL: Always lock after modifying pyproject.toml
poetry add new-package
poetry lock  # MUST RUN THIS

# Commit both files
git add pyproject.toml poetry.lock
git commit -m "chore: Add new-package dependency"
```

#### Development Dependencies
```toml
[tool.poetry.group.dev.dependencies]
pytest = "^8.2.0"
pytest-asyncio = "^0.23.0"
pytest-cov = "^5.0.0"
ruff = "^0.4.4"
fakeredis = "^2.32.0"  # For testing without real Redis
httpx = "^0.27.0"       # For testing FastAPI
```

#### Path Dependencies (Monorepo)
```toml
[tool.poetry.dependencies]
# develop=true: Install in editable mode (see changes immediately)
vizu-models = {path = "../../libs/vizu_models", develop = true}
vizu-db-connector = {path = "../../libs/vizu_db_connector", develop = true}
vizu-agent-framework = {path = "../../libs/vizu_agent_framework", develop = true}
```

#### Virtual Environments
```bash
# Set Poetry to create .venv in project root (already default)
poetry config virtualenvs.in-project true

# Activate environment
poetry shell

# Or run commands directly
poetry run pytest
poetry run uvicorn app.main:app --reload
```

---

### 0.8 Docker Ignores 🚫

**Principle:** Minimize Docker build context to speed up builds and reduce image size.

**Root .dockerignore:**
```dockerignore
# .dockerignore (root of monorepo)

**/__pycache__
**/.venv
**/.git
**/.pytest_cache
**/.ipynb_checkpoints
**/node_modules
**/.env
**/.env.*
!**/.env.example
**/*.pyc
**/.DS_Store
**/coverage.xml
**/htmlcov
**/.ruff_cache
```

**Why This Matters:**
- ✅ Faster builds (smaller context)
- ✅ Smaller images (no cache, no .git)
- ✅ No secrets in images (.env excluded)

**Verification:**
```bash
# Check what's being copied in build context
docker build --no-cache -t test . 2>&1 | grep "Sending build context"

# Should be < 50MB for most services
```

---

### 0.9 Sleek, Light Images (Minimal Dependencies & Image Sizes) 🪶

**Principle:** Docker images should be as small as possible. Target: <100MB for services, <500MB hard limit.

**Current Image Sizes:**
- `analytics_api`: 92.3 MB ✅
- `atendente_core`: ~180 MB ✅
- `tool_pool_api`: ~200 MB ✅

**Strategies:**

#### 1. Multi-Stage Builds (Mandatory)
```dockerfile
# Stage 1: Builder (heavy)
FROM python:3.11-slim AS builder

ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=true

WORKDIR /app
RUN pip install poetry==1.8.0

# Copy ONLY required libs (not all 20!)
COPY libs/vizu_db_connector libs/vizu_db_connector
COPY libs/vizu_models libs/vizu_models
COPY libs/vizu_auth libs/vizu_auth

COPY services/analytics_api services/analytics_api

WORKDIR /app/services/analytics_api
RUN poetry install --no-root --no-dev

# Stage 2: Runtime (light)
FROM python:3.11-slim AS final

WORKDIR /app/services/analytics_api

# Copy ONLY .venv and source code
COPY --from=builder /app/services/analytics_api/.venv ./.venv
COPY --from=builder /app/libs/vizu_db_connector/src /app/libs/vizu_db_connector/src
COPY --from=builder /app/libs/vizu_models/src /app/libs/vizu_models/src
COPY --from=builder /app/services/analytics_api/src ./src

ENV PATH="/app/services/analytics_api/.venv/bin:$PATH"

CMD ["uvicorn", "analytics_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 2. Copy ONLY Required Libraries
```dockerfile
# ❌ Bad: Copy all libs (unnecessary bloat)
COPY libs/ libs/

# ✅ Good: Copy only what you need
COPY libs/vizu_db_connector libs/vizu_db_connector
COPY libs/vizu_models libs/vizu_models
COPY libs/vizu_auth libs/vizu_auth
```

**How to know which libs are required?**
Check `pyproject.toml`:
```toml
[tool.poetry.dependencies]
vizu-db-connector = {path = "../../libs/vizu_db_connector"}
vizu-models = {path = "../../libs/vizu_models"}
vizu-auth = {path = "../../libs/vizu_auth"}
# Copy ONLY these three ^^^
```

#### 3. No Dev Dependencies in Production
```dockerfile
# ✅ Good: No dev dependencies
RUN poetry install --no-root --no-dev

# ❌ Bad: Includes pytest, ruff, etc.
RUN poetry install --no-root
```

#### 4. Minimal Base Image
```dockerfile
# ✅ Good: python:3.11-slim (150MB)
FROM python:3.11-slim

# ❌ Bad: python:3.11 (900MB)
FROM python:3.11
```

#### 5. CI Image Size Check (Enforced)
```yaml
# .github/workflows/ci.yml

- name: Check image size
  run: |
    SIZE=$(docker image inspect $IMAGE_NAME --format='{{.Size}}')
    SIZE_MB=$((SIZE / 1024 / 1024))
    echo "Image size: ${SIZE_MB}MB"
    if [ $SIZE_MB -gt 500 ]; then
      echo "ERROR: Image exceeds 500MB limit"
      exit 1
    fi
```

---

### 0.10 Lazy Loading ⚡

**Principle:** Import and initialize resources only when needed, not at module load time.

**Why Lazy Loading?**
- ✅ Faster startup time
- ✅ Lower memory usage
- ✅ Avoid circular imports
- ✅ Better testability

**Examples:**

❌ **BAD — Eager Loading:**
```python
# services/tool_pool_api/src/tool_pool_api/main.py

# Loaded immediately on import (slow startup!)
from vizu_llm_service.client import get_model
from vizu_qdrant_client import get_qdrant_client
from vizu_db_connector.database import get_db_session

# All initialized at import time
llm_model = get_model(tier="DEFAULT")  # ❌ Slow!
qdrant = get_qdrant_client()          # ❌ Connection opened immediately!
```

✅ **GOOD — Lazy Loading (Singleton Pattern with @lru_cache):**
```python
# libs/vizu_supabase_client/src/vizu_supabase_client/client.py

from functools import lru_cache
from supabase import create_client, Client

@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """
    Get or create Supabase client (lazy singleton).
    Client is created only on first call.
    """
    return create_client(
        supabase_url=settings.SUPABASE_URL,
        supabase_key=settings.SUPABASE_SERVICE_ROLE_KEY,
    )

# Usage: Client created only when this function is called
client = get_supabase_client()
```

✅ **GOOD — Lazy Loading (FastAPI Dependencies):**
```python
# services/analytics_api/src/analytics_api/api/routes.py

from fastapi import Depends
from vizu_db_connector.database import get_db_session

@router.get("/metrics")
async def get_metrics(
    db: Session = Depends(get_db_session),  # ✅ DB session created only for this request
):
    # DB connection opened here, closed after request
    return db.query(Metric).all()
```

✅ **GOOD — Lazy Imports for Optional Features:**
```python
# libs/vizu_llm_service/src/vizu_llm_service/client.py

def get_model(provider: str, tier: str):
    """Lazy import of provider-specific modules."""

    if provider == "openai":
        # Import only if OpenAI is used
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(...)

    elif provider == "anthropic":
        # Import only if Anthropic is used
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(...)

    elif provider == "ollama":
        # Import only if Ollama is used
        from langchain_ollama import ChatOllama
        return ChatOllama(...)
```

✅ **GOOD — Cached Configuration:**
```python
# services/tool_pool_api/src/tool_pool_api/core/config.py

from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    QDRANT_URL: str
    # ...

    class Config:
        env_file = ".env"

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Lazy load settings (parsed only once)."""
    return Settings()

# Usage
settings = get_settings()  # Parsed once, cached
```

**Performance Impact:**
```python
# Without lazy loading
import time
start = time.time()
from my_module import heavy_resource  # 2 seconds to import
print(f"Import time: {time.time() - start}s")  # 2.0s

# With lazy loading
import time
start = time.time()
from my_module import get_heavy_resource  # 0.01s to import
print(f"Import time: {time.time() - start}s")  # 0.01s

resource = get_heavy_resource()  # 2 seconds only when called
```

---

## Summary: Work Principles Checklist ✅

Before submitting any PR, verify:

- [ ] **Modularity:** Code is organized into focused modules with single responsibilities
- [ ] **Reusability:** Used existing libraries, no code duplication
- [ ] **Clean Code:** Type hints, clear naming, sorted imports, `ruff check` passes
- [ ] **Scalability:** No hardcoded values, all config in env vars or parameters
- [ ] **Tests:** Critical paths covered, tests pass (`pytest`)
- [ ] **Maintainability:** Docstrings, README updated, CHANGELOG for breaking changes
- [ ] **Poetry:** Dependencies added via `poetry add`, `poetry.lock` committed
- [ ] **Ignores:** `.dockerignore` excludes cache, secrets, dev files
- [ ] **Light Images:** Only required libs copied, image <500MB, multi-stage build
- [ ] **Lazy Loading:** Resources initialized on-demand, `@lru_cache` for singletons

---

## 1. Project Overview

**What is Vizu?** A production-ready conversational AI platform built with LangChain, LangGraph, and FastAPI.

**Monorepo Structure:**
```
vizu-mono/
├── libs/          # 20 shared Python libraries (avoid code duplication)
├── services/      # 14 microservices (FastAPI + LangGraph)
├── apps/          # 2 frontend applications (React)
└── ferramentas/   # Development tools
```

**Tech Stack:**
- **Language:** Python 3.11+
- **Framework:** FastAPI, LangChain, LangGraph
- **Package Manager:** Poetry (required for all services)
- **Databases:** PostgreSQL (Supabase), Redis, Qdrant (vector DB)
- **LLM Providers:** Ollama (local/cloud), OpenAI, Anthropic, Google Gemini
- **Observability:** Langfuse (LLM traces), OpenTelemetry
- **Cloud:** Google Cloud Platform (Cloud Run, Pub/Sub, Cloud Storage)
- **Containerization:** Docker + Docker Compose

---

## 2. Shared Libraries (libs/) — CRITICAL for Code Reuse

### Core Infrastructure

#### vizu_models
**Purpose:** Single source of truth for all data models
**Tech:** SQLModel (SQLAlchemy + Pydantic)
**Location:** [libs/vizu_models/src/vizu_models/](libs/vizu_models/src/vizu_models/)
**When to use:** Creating/modifying any database models or API schemas
**Key files:**
- `models.py` — All database models
- `schemas.py` — Pydantic request/response models

#### vizu_db_connector
**Purpose:** Database connectivity + Alembic migrations
**Tech:** SQLAlchemy, Alembic, psycopg2-binary
**Location:** [libs/vizu_db_connector/](libs/vizu_db_connector/)
**When to use:** Database access, running migrations
**Key patterns:**
```python
from vizu_db_connector.database import get_db_session

async def endpoint(db: Session = Depends(get_db_session)):
    # Use db session
```
**CLI:** `poetry run vizu-db migrate`

#### vizu_supabase_client
**Purpose:** Supabase REST API wrapper (alternative to direct PostgreSQL)
**Tech:** Singleton client pattern
**Location:** [libs/vizu_supabase_client/](libs/vizu_supabase_client/)
**When to use:** Production database access, DNS-friendly operations
**Key pattern:**
```python
from vizu_supabase_client.client import get_supabase_client

client = get_supabase_client()
response = client.table("clientes").select("*").execute()
```

#### vizu_observability_bootstrap
**Purpose:** OpenTelemetry configuration for all services
**Tech:** OTel SDK, FastAPI integration
**Location:** [libs/vizu_observability_bootstrap/](libs/vizu_observability_bootstrap/)
**When to use:** Setting up new services, adding tracing
**Key pattern:**
```python
from vizu_observability_bootstrap import setup_observability

setup_observability(app, service_name="my_service")
```

#### vizu_shared_utils
**Purpose:** Common utility functions to reduce duplication
**Tech:** Pure Python utilities
**Location:** [libs/vizu_shared_utils/](libs/vizu_shared_utils/)
**When to use:** Data transformation, text processing, validation

---

### LLM & AI Core

#### vizu_llm_service ⭐
**Purpose:** Multi-provider LLM abstraction layer
**Providers:** Ollama (local/cloud), OpenAI, Anthropic, Google Gemini
**Location:** [libs/vizu_llm_service/](libs/vizu_llm_service/)
**When to use:** Any LLM calls — NEVER call providers directly
**Key pattern:**
```python
from vizu_llm_service.client import get_model

# Automatic routing based on LLM_PROVIDER env var
model = get_model(tier="FAST")  # or "DEFAULT", "POWERFUL"
response = await model.ainvoke("Hello")
```
**Model Tiers:**
- `FAST` — Quick responses (gpt-4o-mini, claude-3-5-haiku)
- `DEFAULT` — Balanced (gpt-4o, claude-3-5-sonnet)
- `POWERFUL` — Complex tasks (o1-preview, claude-opus)

**Langfuse Integration:** Built-in, automatic tracing

#### vizu_agent_framework ⭐⭐⭐
**Purpose:** Reusable LangGraph agent builder (95% code reuse goal)
**Tech:** LangGraph, Redis checkpointing, MCP integration
**Location:** [libs/vizu_agent_framework/](libs/vizu_agent_framework/)
**When to use:** Building ANY new agent service
**Key files:**
- `agent_builder.py` — AgentBuilder class
- `agent_config.py` — AgentConfig dataclass
- `agent_state.py` — AgentState TypedDict
- `nodes.py` — Reusable graph nodes

**Example (from vendas_agent):**
```python
from vizu_agent_framework import AgentConfig, AgentBuilder

config = AgentConfig(
    name="vendas_agent",
    role="Sales Representative",
    elicitation_strategy="sales_pipeline",
    enabled_tools=["executar_rag_cliente", "agendar_consulta"],
    max_turns=15,
    model="openai:gpt-4o-mini",
)

agent = AgentBuilder(config).build()
result = await agent.ainvoke({"messages": [...], "session_id": "..."})
```

**Built-in Nodes:**
- `init` — Initialize state
- `elicit` — Gather info via elicitation strategies
- `execute_tool` — Execute MCP tools with context injection
- `respond` — Generate LLM response
- `end` — End conversation

#### vizu_tool_registry ⭐
**Purpose:** Dynamic tool discovery + tier-based access control
**Tech:** Tier validation (BASIC, SME, ENTERPRISE)
**Location:** [libs/vizu_tool_registry/](libs/vizu_tool_registry/)
**When to use:** Loading tools for agents, validating client access
**Key pattern:**
```python
from vizu_tool_registry import ToolRegistry

available_tools = ToolRegistry.get_available_tools(
    enabled_tools=["executar_rag_cliente"],
    tier="SME",  # BASIC, SME, or ENTERPRISE
)
```

#### vizu_rag_factory
**Purpose:** RAG (Retrieval-Augmented Generation) factory
**Tech:** LangChain, Qdrant, HuggingFace embeddings
**Location:** [libs/vizu_rag_factory/](libs/vizu_rag_factory/)
**When to use:** Creating RAG chains, knowledge base search

#### vizu_sql_factory
**Purpose:** Text-to-SQL agent factory
**Tech:** LangChain SQL agents, database introspection
**Location:** [libs/vizu_sql_factory/](libs/vizu_sql_factory/)
**When to use:** Natural language database queries

#### vizu_prompt_management
**Purpose:** Centralized prompt versioning and A/B testing
**Tech:** Jinja2 templates, database-backed
**Location:** [libs/vizu_prompt_management/](libs/vizu_prompt_management/)
**When to use:** Managing agent prompts, client-specific overrides

---

### Specialized Services

#### vizu_elicitation_service
**Purpose:** Human-in-the-loop interactive elicitation
**Tech:** Redis-backed state, exception-based control flow
**Location:** [libs/vizu_elicitation_service/](libs/vizu_elicitation_service/)
**Types:** CONFIRMATION, SELECTION, TEXT_INPUT, DATE_TIME
**Key pattern:**
```python
from vizu_elicitation_service import ElicitationRequired

raise ElicitationRequired(
    elicitation_type="CONFIRMATION",
    question="Confirmar agendamento?",
    options=["Sim", "Não"],
)
```

#### vizu_hitl_service
**Purpose:** Quality control queue for human review
**Tech:** Redis queue, Langfuse dataset creation
**Location:** [libs/vizu_hitl_service/](libs/vizu_hitl_service/)
**Criteria:** low_confidence, elicitation_pending, tool_call_failed, keyword_trigger, etc.

#### vizu_auth
**Purpose:** Centralized authentication (JWT + API-Key)
**Tech:** FastAPI dependencies, FastMCP middleware
**Location:** [libs/vizu_auth/](libs/vizu_auth/)
**Key pattern:**
```python
from vizu_auth import verify_api_key

@router.post("/chat")
async def chat(api_key: str = Depends(verify_api_key)):
    ...
```

#### vizu_context_service
**Purpose:** Client context retrieval with Redis caching
**Location:** [libs/vizu_context_service/](libs/vizu_context_service/)
**When to use:** Getting client configuration, enabled tools, tier info

---

## 3. Microservices (services/)

### Core Agent Services

#### atendente_core
**Port:** 8003
**Purpose:** Main conversational AI orchestrator
**Tech:** FastAPI, LangGraph, FastMCP client
**Location:** [services/atendente_core/](services/atendente_core/)
**README:** [services/atendente_core/README.md](services/atendente_core/README.md)
**Key files:**
- `main.py` — FastAPI app + `/chat` endpoint
- `core/graph.py` — LangGraph workflow
- `core/state.py` — AgentState definition
- `mcp/client.py` — MCP client for tool_pool_api

**Endpoints:**
- `POST /chat` — Send message (requires X-API-KEY)
- `GET /health` — Health check

**Integration:** Connects to `tool_pool_api:9000/mcp/` for tool access

#### tool_pool_api
**Port:** 8006 (host), 9000 (container)
**Purpose:** MCP server exposing RAG, SQL, and other tools
**Tech:** FastAPI, FastMCP
**Location:** [services/tool_pool_api/](services/tool_pool_api/)
**README:** [services/tool_pool_api/README.md](services/tool_pool_api/README.md)
**Key files:**
- `main.py` — FastMCP server
- `tools/rag_tool.py` — RAG implementation
- `tools/sql_tool.py` — SQL agent implementation

**Exposed Tools:**
- `executar_rag_cliente` — Semantic search
- `executar_sql_agent` — Natural language SQL queries
- `ferramenta_publica_de_teste` — Test tool

#### vendas_agent
**Purpose:** Sales agent (built with vizu_agent_framework)
**Location:** [services/vendas_agent/](services/vendas_agent/)
**Code:** ~150 lines agent-specific (95% reuse from framework)
**Features:** Sales pipeline, product recommendations, discount management

#### support_agent
**Purpose:** Technical support agent (built with vizu_agent_framework)
**Location:** [services/support_agent/](services/support_agent/)
**Features:** Issue classification, knowledge base search, ticket escalation

---

### Data Processing Services

#### embedding_service
**Port:** 11435
**Purpose:** HuggingFace sentence embeddings
**Tech:** FastAPI, Sentence Transformers
**Location:** [services/embedding_service/](services/embedding_service/)

#### file_upload_api
**Purpose:** File ingestion endpoint → GCS → Pub/Sub
**Location:** [services/file_upload_api/](services/file_upload_api/)

#### file_processing_worker
**Purpose:** Async file processor (Pub/Sub triggered)
**Flow:** GCS → embedding_service → Qdrant
**Location:** [services/file_processing_worker/](services/file_processing_worker/)

#### data_ingestion_api
**Purpose:** BigQuery/Pub/Sub connector for enterprise data
**Location:** [services/data_ingestion_api/](services/data_ingestion_api/)

#### data_ingestion_worker
**Purpose:** Async data processor (Cloud Function)
**Location:** [services/data_ingestion_worker/](services/data_ingestion_worker/)

---

### Supporting Services

#### analytics_api
**Purpose:** Data analytics API (Silver → Gold layer)
**Location:** [services/analytics_api/](services/analytics_api/)

#### migration_runner
**Purpose:** One-shot Alembic migrations service
**Location:** [services/migration_runner/](services/migration_runner/)

#### ollama_service
**Port:** 11434
**Purpose:** Local LLM inference
**Location:** [services/ollama_service/](services/ollama_service/)

---

## 4. Common Patterns & Anti-Patterns

### ✅ DO: Use Shared Libraries

**Bad (code duplication):**
```python
# services/my_service/src/my_service/models.py
class Cliente(Base):
    __tablename__ = "clientes"
    id = Column(UUID, primary_key=True)
    # ...
```

**Good (use vizu_models):**
```python
from vizu_models import Cliente
```

---

### ✅ DO: Use vizu_agent_framework for New Agents

**Bad (reinvent the wheel):**
```python
# 1200+ lines of custom LangGraph code
```

**Good (95% code reuse):**
```python
from vizu_agent_framework import AgentConfig, AgentBuilder

config = AgentConfig(name="my_agent", role="...", ...)
agent = AgentBuilder(config).build()
```

---

### ✅ DO: Use vizu_llm_service for LLM Calls

**Bad (direct provider calls):**
```python
import openai
response = openai.ChatCompletion.create(...)
```

**Good (provider-agnostic):**
```python
from vizu_llm_service.client import get_model

model = get_model(tier="DEFAULT")
response = await model.ainvoke("Hello")
```

---

### ✅ DO: Use vizu_tool_registry for Tool Access

**Bad (hardcoded tools):**
```python
tools = [executar_rag_cliente, executar_sql_agent]
```

**Good (tier-aware, dynamic):**
```python
from vizu_tool_registry import ToolRegistry

tools = ToolRegistry.get_available_tools(
    enabled_tools=client_context.enabled_tools,
    tier=client_context.tier,
)
```

---

### ❌ DON'T: Modify Dockerfile Patterns Without Updating All Services

**Canonical Multi-Stage Dockerfile Pattern:**
```dockerfile
# Stage 1: Builder
FROM python:3.11-slim as builder
RUN pip install poetry==1.8.0
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
COPY ./libs ./libs
COPY ./services/<service> ./services/<service>
WORKDIR /app/services/<service>
RUN poetry install --no-root

# Stage 2: Runtime
FROM python:3.11-slim
WORKDIR /app/services/<service>
COPY --from=builder /app/services/<service>/.venv ./.venv
COPY --from=builder /app/libs /app/libs
COPY --from=builder /app/services/<service>/src ./src
ENV PATH="/app/services/<service>/.venv/bin:$PATH"
ENV PYTHONPATH="src:../../libs/vizu_db_connector/src:..."
CMD ["uvicorn", "service_package.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Reference:** [services/atendente_core/Dockerfile](services/atendente_core/Dockerfile)

---

## 5. Development Workflows

### Local Development (Docker Compose)

```bash
# Start all services
make up

# View logs
make logs s=atendente_core

# Stop all
docker compose down -v

# Rebuild specific service
docker compose up --build -d atendente_core
```

### Running a Service Locally (Quick Iteration)

```bash
cd services/atendente_core
poetry install
cp .env.example .env
# Edit .env with required values
poetry run uvicorn atendente_core.main:app --reload
```

### Testing

```bash
cd services/<service>
poetry run pytest                 # All tests
poetry run pytest src/tests/ -v   # Verbose
```

### Linting & Formatting

```bash
# From root
poetry run ruff check .          # Lint
poetry run ruff check . --fix    # Auto-fix
poetry run ruff format .         # Format

# From service
cd services/analytics_api
poetry run ruff check src/
poetry run ruff check src/ --fix
```

### Database Migrations

```bash
# Create migration
cd libs/vizu_db_connector
poetry run alembic revision -m "Add new table"

# Apply migrations (local)
make migrate

# Apply migrations (production)
make migrate-prod
```

### Adding a New Dependency

```bash
cd services/my_service
poetry add new-package
poetry lock  # CRITICAL: Always lock after modifying pyproject.toml
```

---

## 6. Important Files & Locations

### Configuration Files

| File | Purpose |
|------|---------|
| [docker-compose.yml](docker-compose.yml) | Canonical local dev config (service names, ports, env vars) |
| [.github/workflows/ci.yml](.github/workflows/ci.yml) | Linting, building, testing pipeline |
| [.github/workflows/deploy-cloud-run.yml](.github/workflows/deploy-cloud-run.yml) | GCP deployment |
| `services/*/pyproject.toml` | Poetry dependencies per service |
| `services/*/.env.example` | Required environment variables |

### Key Reference Files

| File | When to Reference |
|------|------------------|
| [services/atendente_core/Dockerfile](services/atendente_core/Dockerfile) | Canonical Dockerfile pattern |
| [services/atendente_core/README.md](services/atendente_core/README.md) | Service-specific env vars, commands |
| [libs/vizu_agent_framework/README.md](libs/vizu_agent_framework/README.md) | Agent creation guide |
| [libs/vizu_db_connector/src/vizu_db_connector/database.py](libs/vizu_db_connector/src/vizu_db_connector/database.py) | DB session patterns |

---

## 7. Architecture Patterns

### Factory Pattern
- `AgentBuilder(config).build()` — vizu_agent_framework
- `ToolRegistry.get_available_tools()` — vizu_tool_registry
- `get_model(tier="DEFAULT")` — vizu_llm_service

### Singleton Pattern
- `get_supabase_client()` — vizu_supabase_client
- `get_context_service()` — vizu_context_service

### Dependency Injection
- FastAPI dependencies for DB sessions, auth
- `@inject_cliente_context` decorator

### Exception-Based Control Flow
- `ElicitationRequired` exception to pause LangGraph execution
- Caught by nodes for interactive UI prompts

### Tier-Based Authorization
- `BASIC`, `SME`, `ENTERPRISE` tiers
- Tool access controlled via ToolRegistry
- Prevents unauthorized feature usage

---

## 8. Environment Variables

### Common Across Services

```bash
# Database
DATABASE_URL=postgresql://user:password@postgres:5432/vizu_db

# Redis
REDIS_URL=redis://redis:6379/0

# LLM Provider (pick one)
LLM_PROVIDER=ollama_cloud  # or: ollama, openai, anthropic

# Ollama Cloud
OLLAMA_CLOUD_API_KEY=your-key
OLLAMA_CLOUD_BASE_URL=https://api.ollama.com/v1
OLLAMA_CLOUD_DEFAULT_MODEL=gpt-oss:20b

# OpenAI
OPENAI_API_KEY=sk-...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Langfuse (Observability)
LANGFUSE_HOST=http://host.docker.internal:3000
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...

# MCP (Tool Pool)
MCP_SERVER_URL=http://tool_pool_api:9000/mcp/

# Qdrant (Vector DB)
QDRANT_URL=http://qdrant_db:6333

# Embedding Service
EMBEDDING_SERVICE_URL=http://embedding_service:11435
```

### Service-Specific

See `services/<service>/.env.example` for service-specific variables.

---

## 9. CI/CD Pipelines

### CI Pipeline (.github/workflows/ci.yml)

1. **Lint Check:** `ruff check` on entire codebase
2. **Dependency Check:** Validate `pyproject.toml` syntax
3. **Docker Build:** Build all service images
4. **Image Size Check:** Fail if any image > 500MB

**Linting Rules:**
- `UP045` — Use `X | None` instead of `Optional[X]`
- `I001` — Import sorting
- Max line length: 88 characters

### Deployment Pipeline (.github/workflows/deploy-cloud-run.yml)

- **Trigger:** Push to `main` (if `services/` or `libs/` changed), or manual
- **Registry:** `us-east1-docker.pkg.dev` (GCP Artifact Registry)
- **Secrets:** `GCP_PROJECT_ID`, `GCP_SA_KEY`, `GCP_SA_EMAIL`
- **Services:** Agents pool + Workers pool

---

## 10. Troubleshooting

### Docker Build Failures

**Symptom:** `poetry install` fails in builder
**Fix:**
```bash
# Regenerate lock file
cd services/<service>
poetry lock --no-update
```

### Import Errors in Services

**Symptom:** `ModuleNotFoundError: No module named 'vizu_models'`
**Fix:**
1. Verify `PYTHONPATH` in Dockerfile: `src:../../libs/vizu_models/src:...`
2. Check `pyproject.toml` for path dependencies:
   ```toml
   [tool.poetry.dependencies]
   vizu_models = {path = "../../libs/vizu_models", develop = true}
   ```
3. Run `poetry install` locally to validate

### Port Conflicts

**Symptom:** `Address already in use`
**Fix:**
```bash
docker compose down -v
lsof -i :<port>  # Find conflicting process
kill -9 <PID>
```

### MCP Connection Issues

**Symptom:** Tools not accessible in atendente_core
**Debug:**
```bash
docker compose logs atendente_core | grep -i mcp
docker compose logs tool_pool_api | grep -i mcp
```

---

## 11. Quick Start Checklist (New Agent)

1. **Create service directory:**
   ```
   services/my_agent/
   ├── src/my_agent/
   │   ├── main.py
   │   ├── core/agent.py
   │   └── api/routes.py
   ├── pyproject.toml
   ├── Dockerfile
   └── README.md
   ```

2. **Add to pyproject.toml:**
   ```toml
   [tool.poetry.dependencies]
   python = "^3.11"
   vizu-agent-framework = {path = "../../libs/vizu_agent_framework", develop = true}
   vizu-tool-registry = {path = "../../libs/vizu_tool_registry", develop = true}
   vizu-models = {path = "../../libs/vizu_models", develop = true}
   ```

3. **Define agent in core/agent.py:**
   ```python
   from vizu_agent_framework import AgentConfig, AgentBuilder

   config = AgentConfig(name="my_agent", role="...", ...)
   agent = AgentBuilder(config).build()
   ```

4. **Expose via FastAPI in main.py:**
   ```python
   from fastapi import FastAPI

   app = FastAPI()

   @app.post("/chat")
   async def chat(request: ChatRequest):
       return await agent.ainvoke({...})
   ```

5. **Copy Dockerfile from atendente_core and update paths**

6. **Add to docker-compose.yml:**
   ```yaml
   my_agent:
     build:
       context: .
       dockerfile: services/my_agent/Dockerfile
     ports:
       - "8010:8000"
   ```

7. **Test:**
   ```bash
   make up
   make logs s=my_agent
   curl -X POST http://localhost:8010/chat -H "Content-Type: application/json" -d '{"message": "Hello"}'
   ```

---

## 12. Key Principles for Claude Code

### Code Reuse Over Duplication
- **Always check** if a library exists before creating new utilities
- **Prefer** editing existing libraries to creating new ones
- **Reference** `libs/` for common patterns before implementing

### Follow Established Patterns
- **Use** vizu_agent_framework for any agent (not custom LangGraph)
- **Use** vizu_llm_service for LLM calls (not direct provider APIs)
- **Use** vizu_models for data schemas (not inline Pydantic models)
- **Use** canonical Dockerfile pattern from atendente_core

### Minimal Changes
- **Scope** PRs to single service or library where possible
- **Avoid** changing Docker patterns without updating all services
- **Run** `poetry lock` after modifying `pyproject.toml`
- **Run** `ruff check . --fix` before committing

### Quality Standards
- **All** Python code must pass `ruff check`
- **Use** modern type hints (`X | None`, not `Optional[X]`)
- **Sort** imports (I001 rule enforced)
- **Verify** lint passes locally before pushing

### Observability First
- **Instrument** new tools with Langfuse
- **Include** session_id, user_id in traces
- **Use** vizu_observability_bootstrap for new services

### Documentation
- **Update** service README when adding env vars or endpoints
- **Document** new shared library functions
- **Reference** file paths in comments (e.g., `See libs/vizu_models/src/vizu_models/models.py:42`)

---

## 13. Recent Changes (December 2025)

### Analytics API
- New service: `services/analytics_api`
- Redis caching for query optimization
- Multi-period metrics (today, week, month, etc.)

### Lint Improvements
- Migrated `Optional[X]` → `X | None` (UP045)
- Fixed import sorting across all services (I001)

### Docker Improvements
- Canonical multi-stage pattern enforced
- Image size checks: max 500MB per image

### CI/CD
- `ci.yml`: ruff linting + Docker builds
- `deploy-cloud-run.yml`: GCP Artifact Registry deployment

---

## 14. Service Communication Patterns

### Internal Service URLs

Services use Docker Compose service names for internal communication:

```python
# atendente_core → tool_pool_api
MCP_SERVER_URL = "http://tool_pool_api:9000/mcp/"

# Any service → embedding_service
EMBEDDING_SERVICE_URL = "http://embedding_service:11435"

# Any service → postgres
DATABASE_URL = "postgresql://user:password@postgres:5432/vizu_db"
```

**Port Mapping:**
- Container internal port (e.g., `9000`) — used in service communication
- Host mapped port (e.g., `8006`) — used for local testing from host machine

---

## 15. Testing Patterns

### Unit Tests
```bash
cd services/<service>
poetry run pytest src/tests/test_*.py -v
```

### Integration Tests
```bash
# Start dependencies first
docker compose up -d postgres redis qdrant_db

# Run integration tests
cd services/tool_pool_api
poetry run pytest src/tests/integration/ -v
```

### End-to-End Tests
```bash
# Full stack up
make up

# Run E2E
make chat
make batch-run
```

---

## 16. Git Workflow

### Branch Naming
```
feature/add-new-agent
fix/tool-pool-api-timeout
refactor/agent-framework-cleanup
```

### Commit Messages
```
feat: Add support_agent with vizu_agent_framework
fix: Resolve MCP connection timeout in tool_pool_api
refactor: Migrate vendas_agent to new framework
chore: Update ruff rules and fix linting errors
```

### Before Committing
```bash
# Format
poetry run ruff format .

# Fix linting
poetry run ruff check . --fix

# Run tests
cd services/<service>
poetry run pytest
```

---

## 17. When to Modify Each Library

| Library | Modify When... |
|---------|---------------|
| vizu_models | Adding/changing database schema or API models |
| vizu_db_connector | Changing DB connection logic or adding migration utils |
| vizu_agent_framework | Improving core agent behavior across all agents |
| vizu_llm_service | Adding new LLM provider or model tier |
| vizu_tool_registry | Adding new tool or changing tier logic |
| vizu_auth | Changing authentication strategy |
| vizu_observability_bootstrap | Updating tracing/logging configuration |
| vizu_elicitation_service | Adding new elicitation types or strategies |
| vizu_hitl_service | Adding HITL criteria or queue management logic |
| vizu_rag_factory | Improving RAG chain construction |
| vizu_sql_factory | Enhancing text-to-SQL agent capabilities |

---

## 18. Dependency Management Rules

### Adding a Dependency

```bash
cd services/<service>
poetry add new-package
poetry lock  # CRITICAL: Always lock
git add pyproject.toml poetry.lock
git commit -m "chore: Add new-package to <service>"
```

### Adding a Library Dependency

```toml
# services/<service>/pyproject.toml
[tool.poetry.dependencies]
vizu_new_lib = {path = "../../libs/vizu_new_lib", develop = true}
```

### Upgrading a Dependency

```bash
poetry update package-name
poetry lock
```

### Shared Dependencies (libs/)

When modifying a library dependency:
1. Update `libs/<lib>/pyproject.toml`
2. Run `poetry lock` in the library
3. Run `poetry lock` in **all services** that depend on it
4. Test affected services before committing

---

## 19. Make Commands Reference

```bash
make up                 # Start all services (docker compose up --build -d)
make down               # Stop all services (docker compose down -v)
make logs s=<service>   # View logs for specific service
make test               # Run unit tests
make chat               # Quick chat test (atendente_core)
make batch-run          # Generate Langfuse traces
make migrate            # Apply database migrations
make migrate-prod       # Apply migrations to production (Supabase)
make seed               # Seed dev database
make fmt                # Format code (ruff format)
make lint               # Check code quality (ruff check)
make build s=<service>  # Rebuild specific service
```

---

## 20. Common Tasks Cheat Sheet

### Task: Add a New Tool

1. **Create tool in tool_pool_api:**
   ```python
   # services/tool_pool_api/src/tool_pool_api/server/tool_modules/my_tool.py

   from fastmcp.tool import tool

   @tool
   async def my_new_tool(query: str, _internal_context: dict) -> str:
       cliente_id = _internal_context["cliente_id"]
       # Implementation
       return result
   ```

2. **Register in vizu_tool_registry:**
   ```python
   # libs/vizu_tool_registry/src/vizu_tool_registry/registry.py

   ToolMetadata(
       name="my_new_tool",
       tier=ToolTier.SME,
       description="...",
   )
   ```

3. **Test:**
   ```bash
   make up
   make logs s=tool_pool_api
   # Check tool is listed in MCP server
   ```

### Task: Modify Database Schema

1. **Edit model in vizu_models:**
   ```python
   # libs/vizu_models/src/vizu_models/models.py

   class Cliente(SQLModel, table=True):
       new_field: str | None = None
   ```

2. **Create migration:**
   ```bash
   cd libs/vizu_db_connector
   poetry run alembic revision --autogenerate -m "Add new_field to Cliente"
   ```

3. **Review migration:**
   ```python
   # libs/vizu_db_connector/alembic/versions/<hash>_add_new_field.py
   ```

4. **Apply migration:**
   ```bash
   make migrate
   ```

### Task: Add Environment Variable

1. **Update .env.example:**
   ```bash
   # services/<service>/.env.example
   NEW_VAR=default_value
   ```

2. **Update docker-compose.yml:**
   ```yaml
   <service>:
     environment:
       - NEW_VAR=${NEW_VAR}
   ```

3. **Update README:**
   ```markdown
   # services/<service>/README.md

   ## Environment Variables

   - `NEW_VAR` — Description of what it does
   ```

---

## 21. What NOT to Do

❌ **DON'T** create inline Pydantic models — use vizu_models
❌ **DON'T** call LLM providers directly — use vizu_llm_service
❌ **DON'T** write custom LangGraph agents — use vizu_agent_framework
❌ **DON'T** hardcode tool lists — use vizu_tool_registry
❌ **DON'T** create custom DB session management — use vizu_db_connector
❌ **DON'T** modify Dockerfiles without following canonical pattern
❌ **DON'T** skip `poetry lock` after changing dependencies
❌ **DON'T** commit code that fails `ruff check`
❌ **DON'T** add backwards-compatibility hacks (unused vars, re-exports)
❌ **DON'T** create new utilities without checking if they exist in libs/

---

## 22. Where to Look for Examples

### New Agent Service
**Reference:** [services/vendas_agent/](services/vendas_agent/) or [services/support_agent/](services/support_agent/)

### Dockerfile Pattern
**Reference:** [services/atendente_core/Dockerfile](services/atendente_core/Dockerfile)

### FastAPI Service
**Reference:** [services/analytics_api/](services/analytics_api/)

### MCP Tool
**Reference:** [services/tool_pool_api/src/tool_pool_api/server/tool_modules/](services/tool_pool_api/src/tool_pool_api/server/tool_modules/)

### Database Migration
**Reference:** [libs/vizu_db_connector/alembic/versions/](libs/vizu_db_connector/alembic/versions/)

### Async Worker (Pub/Sub)
**Reference:** [services/file_processing_worker/](services/file_processing_worker/)

### LangGraph Agent
**Reference:** [services/atendente_core/src/atendente_core/core/graph.py](services/atendente_core/src/atendente_core/core/graph.py)

---

**End of Guide**

This guide should be your first stop when working on any task in vizu-mono. For questions not covered here, check service READMEs or library documentation in their respective directories.
