# Platform (Personal Portfolio)

> **A multi-tenant AI data platform built from the ground up**

This repository is my full-stack demonstration project: a production‑grade system that combines
LLMs, hybrid RAG retrieval, text‑to-SQL analytics, multi‑tenant security, and human‑in‑the‑loop workflows.

It showcases my skills across backend development, AI orchestration, frontend engineering, infra,
and observability. 

---

## 🚀 Key Highlights

- **Full-stack architecture**: React 18 dashboard + FastAPI microservices + LangGraph agents.
- **AI-centric design**: Hybrid RAG search, provider-agnostic LLM service (OpenAI, Anthropic, Google,
  Ollama) with tiered budgets.
- **Multi-tenancy at the DB layer**: PostgreSQL Row-Level Security, Supabase Edge Functions, and
  per-tenant context injection.
- **Text-to-SQL analytics**: Natural language queries converted to safe SQL with allowlists,
  PII masking, and RLS enforcement.
- **Human-in-the-Loop quality control**: Custom review queue and elicitation service with Streamlit
  UI.
- **Tier-based access control**: Six granular tiers (FREE→ADMIN) governing tool availability and
  rate limits.
- **Observability-first**: OpenTelemetry, Langfuse traces, Grafana Loki/Tempo/Mimir/Faro.
- **Extensible libraries**: 20+ shared Python packages used by all services (zero duplication).
- **Deployment-ready**: Docker Compose for dev, Google Cloud Run for production with CI-ready
  commands.

This project synthesizes dozens of technologies and demonstrates solid engineering practices,
including clean architecture, automated testing, linting, and detailed documentation.

---

## 🧩 Technical Skills Demonstrated

- Python 3.11+, FastAPI, Pydantic, SQLModel
- Building and orchestrating LLM-based agents (LangGraph, LangChain)
- Designing multi-tenant systems with PostgreSQL RLS
- Developing hybrid retrieval pipelines (pgvector + Cohere + MMR)
- Implementing secure text‑to‑SQL with allowlists, masking, and query sanitization
- Creating interactive, hot‑reload React applications (Vite, Chakra UI)
- Working with Supabase (Edge Functions, Auth, pgvector)
- Managing Redis for caching, checkpoints, and prioritized queues
- Integrating observability (OpenTelemetry, Langfuse, Grafana Cloud)
- Containerization and deployment (Docker, Cloud Run, Artifact Registry)
- GitHub workflow, monorepo management, and documentation best practices

---

## 📁 Repository Structure

```
apps/           # Frontend applications (React dashboard & HITL review UI)
services/       # FastAPI/agent microservices with independent Dockerfiles
libs/           # Reusable Python libraries (agent framework, RAG, auth, etc.)
supabase/       # Database schema, Edge Functions, migrations
scripts/        # Utility scripts for experiments and analytics
docs/           # Deep-dive design documents and architecture notes
```

---

## 🛠️ Quick Start (Local Dev)

1. Start Docker Desktop: `open -a Docker`
2. Launch core services: `make dev`
3. Open the dashboard: `open http://localhost:8080`

Services run with **hot reload** and connect to a remote Supabase instance —
no local database required. 



---

## 🛠️ Development & Deployment Commands

```bash
# Core development
make dev               # start dashboard + backend + tools
make dev-logs          # tail service logs
make dev-down          # stop dev stack
make dev-rebuild       # rebuild after dependency changes

# Full stack
make up                # start ALL services + workers
make down              # stop all containers
make logs s=<name>     # inspect service logs
make ps                # list running containers

# Testing
make test              # run unit tests
make test-all          # test every service
make smoke-test        # end-to-end integration
make experiment-run    # run experiment manifests

# Database
make migrate           # local Alembic migrations
make migrate-prod      # apply to Supabase
make db-shell          # open psql shell

# Code quality
make fmt               # format with ruff
make lint              # lint with ruff
make lint-fix          # auto-fix lint issues

# Deployment
make compose-cloud     # local Cloud Run testing
make cloudrun-build    # build Docker images
make cloudrun-push-all # push to Artifact Registry
```

---

## ✅ Why This Project Matters

This repo is more than a toy application; it's a comprehensive platform that I designed,
built, tested, and documented myself. It features:

1. Architect complex systems with secure multi-tenant data handling.
2. Integrate cutting-edge AI technologies and manage provider agnosticism.
3. Build maintainable, reusable libraries supporting multiple services.
4. Deliver production-ready code with observability and testing baked in.
5. Collaborate using modern development workflows in a mono-repo structure.

Feel free to explore the code, run the stack locally, and reach out if you'd like a
walkthrough or a chat about any part of the system.

---

*Developed and maintained by Cid Lucas*
