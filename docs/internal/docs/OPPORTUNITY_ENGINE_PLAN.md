# Opportunity Engine — Implementation Plan (Adapted to vizu-mono)

> Industry-Agnostic Opportunity Identification & Report Generation Platform
> First Use Case: Recyclable Materials Trading — Price Asymmetry & Inventory Opportunities
> Created: 2026-03-11 | Revised: 2026-03-11

---

## Table of Contents

1. [Project Summary](#1-project-summary)
2. [Design Principles — Agnostic Architecture](#2-design-principles--agnostic-architecture)
3. [What We Already Have (Repo Leverage Map)](#3-what-we-already-have-repo-leverage-map)
4. [What We Need to Build](#4-what-we-need-to-build)
5. [Architecture Overview](#5-architecture-overview)
6. [Phase 0 — Discovery & Requirements](#6-phase-0--discovery--requirements)
7. [Phase 1 — FDW Dev Tooling & Data Extraction](#7-phase-1--fdw-dev-tooling--data-extraction)
8. [Phase 2 — ETL Pipeline (BigQuery Scheduled Queries)](#8-phase-2--etl-pipeline-bigquery-scheduled-queries)
9. [Phase 3 — EDA & Price Modeling PoC (Notebook)](#9-phase-3--eda--price-modeling-poc-notebook)
10. [Phase 4 — System Design](#10-phase-4--system-design)
11. [Phase 5 — Generic Agent & Tool Implementation](#11-phase-5--generic-agent--tool-implementation)
12. [Phase 6 — Opportunity Engine Service (Use-Case Assembly)](#12-phase-6--opportunity-engine-service-use-case-assembly)
13. [Phase 7 — Testing, Go-Live & Maintenance](#13-phase-7--testing-go-live--maintenance)
14. [Dependency Graph](#14-dependency-graph)
15. [Decisions & Open Items](#15-decisions--open-items)

---

## 1. Project Summary

Build an **industry-agnostic platform** of reusable agents, tools, and pipelines for identifying business opportunities and generating analytical reports from structured data. The first deployment targets recyclable materials trading (price asymmetry & inventory optimization), but every component is designed for reuse across different industries and business contexts.

**Platform delivers (reusable across clients/industries):**
1. **Structured Data → Natural Language Context Generator** — Reads tabular data, produces rich NL descriptions per entity, stores as RAG documents in our vector database
2. **Generic Report Generator Agent** (LangGraph) — Produces reports from RAG context + statistical data, with tool use for data queries
3. **Generic Opportunity Identifier Agent** (LangGraph) — Scores and ranks business opportunities from structured data, writes results back to client's infrastructure
4. **Statistical Data Tools** — Python functions/tools that help LLMs reason about statistical distributions, trends, and anomalies
5. **NL from Structured Data API Endpoint** — Standalone endpoint for converting tabular rows into natural language summaries

**First use case delivers (recyclables trading):**
1. **Opportunity scoring** — Results written back to client's BigQuery, consumed by client's own dashboard
2. **Weekly vendor guidelines** — AI-generated using RAG (inventory context, company policies, market data)
3. **Monthly performance reviews** — AI-generated using RAG + statistical structured data
4. **Cron-triggered on Cloud Run** — Simple Cloud Run Jobs or Cloud Scheduler → Cloud Run endpoints

**Boundary: Our infra vs. Client infra:**
- **Our infra (vizu Cloud Run)**: Agents, tools, RAG vector DB, LLM orchestration, Langfuse prompts
- **Client infra**: BigQuery (raw data + ETL + calculation results), their own frontend/dashboard
- **Bridge**: FDW reads client's BQ into Supabase → we generate NL context → store in Qdrant → agents use RAG for reports → reports served via API

**Domain (first client)**: Recyclable solid residue trading
**Client infra**: BigQuery + custom dashboard, < 10 locations across Brazilian states, < 10K transactions/month
**Approach**: Statistical-first price modeling, logistics-aware delta scoring, incremental delivery with validation gates

---

## 2. Design Principles — Agnostic Architecture

### Core Principle: Build Generic, Deploy Specific

Every component we build must be domain-agnostic at its core. The recyclables use case is how we validate the platform, but the code should work for any industry that has structured data requiring opportunity identification or report generation.

### Separation of Concerns

| Layer | Scope | Example |
|-------|-------|---------|
| **Generic agents** (`libs/`) | Domain-agnostic LangGraph agents with configurable prompts and tools | `ReportGeneratorAgent`, `OpportunityIdentifierAgent` |
| **Generic tools** (`tool_pool_api/`) | Reusable tools for data → NL conversion, statistical summaries, RAG ingestion | `generate_nl_context`, `statistical_summary`, `ingest_to_vector_db` |
| **Use-case service** (`services/`) | Thin orchestration layer that assembles generic components with domain config | `opportunity_engine` wires recyclables prompts + scoring config + client BQ tables |
| **Domain prompts** (Langfuse) | Domain-specific instructions, output formats, and business rules | `opportunity/weekly-guidelines`, `opportunity/monthly-review` |
| **Client infra** (external) | Client's data, dashboards, and business logic | BigQuery tables, client's frontend |

### Reusability Patterns

1. **Agents as configurable graphs** — Use `vizu_agent_framework` + LangGraph. Each agent type (report generator, opportunity identifier, RAG context builder) is a reusable graph that accepts:
   - A prompt name (loaded from Langfuse)
   - A set of tools (from `vizu_tool_registry`)
   - A data source configuration (which tables/columns to read)
   - An output destination (where to write results)

2. **Tools as atomic operations** — Each tool does ONE thing:
   - `query_structured_data(query, client_id)` — Read from FDW/Supabase
   - `generate_nl_summary(data_rows, entity_type, template)` — Convert rows to NL
   - `compute_statistics(data, group_by, metrics)` — Statistical aggregation
   - `ingest_rag_documents(documents, client_id, scope)` — Store in vector DB
   - `query_rag_context(query, client_id, scope)` — Retrieve from vector DB

3. **Prompts parameterized, not hardcoded** — All domain knowledge lives in Langfuse prompts. The agent code never mentions "recyclables" or "cardboard" — it works with `{{product_categories}}`, `{{opportunity_data}}`, `{{company_policies}}`.

4. **Data schemas as configuration** — Column mappings, entity types, and metric definitions are configuration, not code. A new industry deployment means new config + new prompts, not new agent code.

### Example: How Another Industry Would Use This

**E-commerce inventory optimization** (hypothetical second client):
- Same `ReportGeneratorAgent` → different Langfuse prompts about SKU restocking
- Same `OpportunityIdentifierAgent` → different scoring formula (margin × velocity × stockout_risk)
- Same `generate_nl_context` tool → different entity templates ("Product X has 45 units, last sold 3 days ago...")
- Same statistical tools → applied to sales velocity instead of price movements
- Same FDW bridge → different BQ tables mapping to their ERP

---

## 3. What We Already Have (Repo Leverage Map)

### ✅ Fully Reusable — Zero New Code Needed

| Component | Location | How It Helps |
|-----------|----------|--------------|
| **BigQuery FDW infrastructure** | `supabase/migrations/20251219_setup_bigquery_wrapper.sql` + fixes | `create_bigquery_server()` and `create_bigquery_foreign_table()` RPCs already exist. We can query the client's BigQuery inventory and transaction tables as regular Postgres tables via FDW. Credential storage in Vault is handled. |
| **FDW onboarding flow** | `apps/vizu_dashboard/src/services/connectorService.ts` | The dashboard already has the UI flow for connecting BigQuery — enter service account JSON, project ID, dataset ID → creates FDW server + foreign tables automatically. |
| **Agent framework** | `libs/vizu_agent_framework/` | `AgentBuilder`, `AgentConfig`, `AgentState`, `NodeRegistry`, `MCPConnectionManager`, `RedisCheckpointer` — build a new agent with `AgentBuilder(config).with_llm().build()`. |
| **Prompt management** | `libs/vizu_prompt_management/` | `build_prompt()` with Langfuse-first loading + Jinja2 fallback. Create new prompts in Langfuse (`opportunity/weekly-guidelines`, `opportunity/monthly-review`) and they'll be loaded automatically. |
| **LLM service** | `libs/vizu_llm_service/` | `get_model(tier="DEFAULT")` — provider-agnostic, already configured for 4 providers × 3 tiers. |
| **Context service** | `libs/vizu_context_service/` | `ContextService` with Redis caching — fetch `VizuClientContext` by client ID. Client context sections (company_profile, data_schema) feed directly into prompts. |
| **Models** | `libs/vizu_models/` | `ClienteVizu`, `VizuClientContext`, `SafeClientContext`, `CredencialServicoExterno` — all existing. |
| **Auth** | `libs/vizu_auth/` | JWT + API-Key auth with `verify_api_key`, `Depends(get_current_user)`. |
| **Observability** | `libs/vizu_observability_bootstrap/` | `setup_observability(app, "opportunity-engine")` — one line for OTel + Langfuse + Grafana. |
| **Supabase client** | `libs/vizu_supabase_client/` | `get_supabase_client().table("x").select("*")` — for reading/writing opportunity results. |
| **Docker patterns** | `services/atendente_core/Dockerfile`, `docker-compose.yml` | Copy the Dockerfile structure (builder stage + slim runtime), add service to compose. |
| **Cloud Run deployment** | `docker-compose.cloud-run.yml`, `Makefile` | Existing patterns for building, pushing to Artifact Registry, deploying to Cloud Run. |

### ⚠️ Partially Reusable — Extend or Adapt

| Component | Location | What to Adapt |
|-----------|----------|---------------|
| **Tool registry** | `libs/vizu_tool_registry/` | Register new tools for the opportunity agent if it needs MCP tools (e.g., `query_opportunities`, `query_price_stats`). Or skip MCP entirely if the agent reads directly from BigQuery/Supabase. |
| **HITL service** | `libs/vizu_hitl_service/` | Reuse for the HITL review flow on agent-generated reports. The criteria (`LOW_CONFIDENCE`, `MANUAL_FLAG`) and Redis priority queue already exist. Needs adaptation: current HITL is per-message, we need it per-report. |
| **Elicitation service** | `libs/vizu_elicitation_service/` | Could be used if the agent needs to ask clarifying questions during report generation (unlikely for cron-triggered batch reports). |
| **Data connectors** | `libs/vizu_data_connectors/` | BigQuery SDK connector was removed in favor of FDW. We use FDW (Postgres-native) for all BigQuery access. But the `AbstractDataConnector` pattern could be extended if we need direct BigQuery API access for ETL monitoring. |
| **SQL factory** | `libs/vizu_sql_factory/` | The text-to-SQL pattern with RLS, allowlists, and PII masking could be adapted for the opportunity query API. However, this agent generates reports from structured data, not from user natural language queries — so likely overkill. |

### 🆕 New Code Required

| Component | Why | Generic or Domain-Specific? |
|-----------|-----|-----------------------------|
| **`scripts/fdw_to_csv.py`** | Reusable dev tool: query any FDW foreign table → export CSV for notebooks. Works with any non-standard DB connected via FDW. | **Generic** — dev tooling |
| **Generic tools in `tool_pool_api/`** | `generate_nl_context`, `compute_statistics`, `ingest_rag_documents` — atomic tools for data→NL, stats, and RAG ingestion | **Generic** — reusable across all clients |
| **NL from Structured Data endpoint** | Standalone API: POST structured rows → GET natural language summaries. Used by agents and cron jobs. | **Generic** — any industry |
| **LangGraph report generator agent** | Configurable graph: reads RAG + stats → generates report with tool use → writes output. Reusable for any report type. | **Generic** — agent pattern |
| **LangGraph opportunity identifier agent** | Configurable graph: reads structured data → scores entities → writes results to destination. | **Generic** — agent pattern |
| **`services/opportunity_engine/`** | Thin use-case service: wires generic agents with recyclables-specific config, prompts, and BQ table mappings. Cron endpoints for Cloud Run. | **Domain-specific** — recyclables |
| **BigQuery write-back function** | After calculations, write `opportunity_results` back to client's BigQuery (not Supabase — client's dashboard reads from their BQ). | **Domain-specific** — client infra |
| **Langfuse prompts** | `opportunity/weekly-guidelines`, `opportunity/monthly-review`, `generic/nl-from-structured-data`, `generic/statistical-summary` | Mixed |
| **BigQuery scheduled queries** (ETL) | Run inside client's BigQuery: categorization, price statistics, inventory aggregation. Client's infra. | **Domain-specific** |
| **Notebook (EDA)** | One-time exploration: FDW → CSV → Jupyter. | Dev tooling |

---

## 4. What We Need to Build

### Generic Components (Reusable Platform)

#### 1. Dev Tool: `scripts/fdw_to_csv.py`

A reusable development script for any project that needs to query data from non-standard databases through FDW. Not just for this client — anytime we connect a new data source via FDW, this script lets us quickly export data for analysis.

```python
# Usage:
# python scripts/fdw_to_csv.py --table "bigquery.{schema}_inventory" --output ./data/inventory.csv
# python scripts/fdw_to_csv.py --query "SELECT * FROM bigquery.client_x_sales WHERE date > '2026-01-01'" --output ./data/sales.csv
# python scripts/fdw_to_csv.py --table "fdw_postgres.erp_orders" --limit 50000 --output ./data/orders.csv
```

Leverages `vizu_supabase_client` for connection. Supports `--table`, `--query`, `--limit`, `--output` args. Handles pagination for large tables.

#### 2. Generic Tools (registered in `tool_pool_api/`)

New tool module: `tool_pool_api/server/tool_modules/data_intelligence_module.py`

```python
# Tool 1: generate_nl_context
# Converts structured data rows into natural language descriptions per entity.
# Uses an LLM with a configurable template prompt.
# Input: list[dict] (rows), entity_type: str, context_template: str (Langfuse prompt name)
# Output: list[NLDocument] with entity_id, text, metadata

# Tool 2: compute_statistics
# Aggregates structured data into statistical summaries that LLMs can reason about.
# Input: data: list[dict], group_by: list[str], metrics: list[str], operations: list[str]
# Output: StatisticalSummary with formatted text + raw numbers
# Operations: mean, median, p25, p75, std, cv, trend_direction, yoy_change, rolling_avg

# Tool 3: ingest_rag_documents
# Takes NL documents and stores them in the vector DB (vector_db.document_chunks).
# Input: documents: list[NLDocument], client_id: str, scope: str, category: str
# Output: IngestResult with count, chunk_ids

# Tool 4: query_structured_data
# Reads from FDW/Supabase tables with type-safe filtering.
# Input: table: str, filters: dict, order_by: str, limit: int, client_id: str
# Output: list[dict] rows
```

#### 3. NL from Structured Data — API Endpoint

Standalone FastAPI endpoint (can live in `tool_pool_api` or a dedicated micro-service):

```
POST /api/v1/nl-from-data
Body: {
    "rows": [...],              # Structured data rows
    "entity_type": "product",   # What each row represents
    "prompt_name": "generic/nl-from-structured-data",  # Langfuse prompt
    "variables": {...},         # Extra context for the prompt
    "output_format": "paragraph" | "bullet_points" | "summary"
}
Response: {
    "documents": [
        {"entity_id": "...", "text": "Product X at Location Y has 500kg in stock...", "metadata": {...}}
    ]
}
```

This endpoint is the foundation for the RAG context pipeline: structured data → NL descriptions → vector DB → agents query via RAG.

#### 4. Statistical Data Tools for LLMs

A Python library of functions that format statistical information in LLM-friendly ways:

```python
# libs/vizu_shared_utils or new tool module
class StatisticalFormatter:
    """Formats statistical data so LLMs can reason about it effectively."""

    @staticmethod
    def format_distribution(values, label) -> str:
        """'Price of Cardboard in SP: median R$2.50/kg (IQR: R$2.10–R$2.80),
        trending up +5.2% over 30d, moderate volatility (CV=18%)'"""

    @staticmethod
    def format_comparison(group_a, group_b, metric) -> str:
        """'Cardboard prices in SP (R$2.50/kg) are 15% higher than RJ (R$2.17/kg),
        gap widening over last 30d'"""

    @staticmethod
    def format_time_series_summary(series, label) -> str:
        """'30-day trend: upward (+8.3%), with weekly seasonality (peaks Mon-Tue).
        Last 7d: stable. 3 anomalies detected (>2σ).'"""

    @staticmethod
    def detect_anomalies(values, method="zscore", threshold=2.0) -> list[dict]:
        """Returns anomaly points with context for LLM consumption."""

    @staticmethod
    def rank_with_context(items, score_field, context_fields) -> str:
        """'Top 3 opportunities: 1) Cardboard SP→RJ (score: 85, delta: +R$0.40/kg,
        vol: 2000kg) 2) ...'"""
```

These functions are used by agents as tools (via tool_pool_api) and also by the context builder directly.

#### 5. LangGraph Agent Patterns

Two reusable agent graphs built on `vizu_agent_framework`:

**ReportGeneratorAgent** — A LangGraph graph that:
1. Receives a report configuration (prompt name, data sources, output format)
2. Uses tools to: query RAG context, compute statistics, fetch structured data
3. Builds a rich context from tool outputs
4. Calls LLM with domain prompt + context to generate the report
5. Validates output structure
6. Writes to output destination (Supabase, API response, etc.)

**OpportunityIdentifierAgent** — A LangGraph graph that:
1. Receives a scoring configuration (metrics, thresholds, entity definitions)
2. Uses tools to: read structured data, compute statistical baselines
3. Applies scoring formula (configurable per domain)
4. Ranks and filters results
5. Generates NL context for top opportunities (via `generate_nl_context` tool)
6. Writes scored results to destination (client's BQ, Supabase, etc.)

Both agents use `AgentBuilder` from `vizu_agent_framework` with LangGraph for tool orchestration. This is needed because report generation involves multi-step tool calls (query data → compute stats → query RAG → compose report), not just a single LLM call.

### Domain-Specific Components (Recyclables Use Case)

#### 6. Use-Case Service: `services/opportunity_engine/`

```
services/opportunity_engine/
├── Dockerfile
├── pyproject.toml
└── src/
    └── opportunity_engine/
        ├── main.py                     # FastAPI app + cron endpoints
        ├── api/
        │   ├── router.py              # POST /generate-weekly, /generate-monthly, GET /reports
        │   └── cron_router.py         # Cloud Scheduler trigger endpoints
        ├── config/
        │   ├── settings.py            # Pydantic Settings
        │   ├── scoring_config.py      # Recyclables-specific scoring formula + weights
        │   └── table_mappings.py      # BQ table names, column mappings, entity definitions
        ├── pipelines/
        │   ├── rag_context_pipeline.py    # Cron: read BQ via FDW → NL context → vector DB
        │   ├── weekly_report_pipeline.py  # Cron: assemble weekly report via generic agents
        │   └── monthly_report_pipeline.py # Cron: assemble monthly report via generic agents
        ├── bigquery_etl/              # Versioned SQL for client's BQ scheduled queries
        │   ├── 01_categorize_products.sql
        │   ├── 02_price_statistics.sql
        │   ├── 03_inventory_aggregation.sql
        │   └── 04_opportunity_scoring.sql
        └── prompts/
            └── templates.py           # Fallback templates for this use case
```

This service is a **thin orchestration layer**. It:
- Configures which BQ tables to read, which scoring formula to use, which prompts to load
- Wires the generic `ReportGeneratorAgent` with recyclables-specific prompts and data sources
- Wires the generic `OpportunityIdentifierAgent` with recyclables scoring config
- Exposes cron endpoints for Cloud Scheduler
- Does NOT contain generic agent logic — that lives in `libs/` and `tool_pool_api/`

#### 7. BigQuery Write-Back

After opportunity scoring calculations, results are written **back to client's BigQuery** (not stored in Supabase). The client's own dashboard reads from their BQ tables directly.

```python
# opportunity_engine/pipelines/scoring_pipeline.py
# Uses vizu_data_connectors BigQueryConnector or google-cloud-bigquery SDK
# to write opportunity_results back to client's BQ dataset.
# Table: {client_dataset}.opportunity_results
```

We only store in **our** infrastructure:
- RAG documents (NL context in vector DB) — used by our agents
- Report drafts (`opportunity_reports` in Supabase) — agent outputs with HITL status
- Observability data (Langfuse traces, OTel metrics)

### Tables

```sql
-- opportunity_reports: agent-generated reports with HITL status (in OUR Supabase)
CREATE TABLE opportunity_reports (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    client_id UUID NOT NULL REFERENCES clientes_vizu(id),
    report_type TEXT NOT NULL,  -- 'weekly_guidelines' or 'monthly_review'
    content TEXT NOT NULL,       -- The generated report (markdown)
    status TEXT NOT NULL DEFAULT 'draft',  -- draft, approved, published, rejected
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    reviewed_by UUID,
    reviewed_at TIMESTAMPTZ,
    reviewer_notes TEXT,
    prompt_version TEXT,         -- Langfuse prompt version used
    context_snapshot JSONB,      -- Snapshot of data the agent saw
    metadata JSONB DEFAULT '{}'
);

-- NOTE: opportunity_results lives in CLIENT'S BigQuery, not here.
-- We read it via FDW for agent context, but the client's dashboard reads it directly from BQ.
```

### New Langfuse Prompts

**Generic prompts (reusable across industries):**

**`generic/nl-from-structured-data`** — Converts tabular data rows into natural language descriptions per entity. Variables: `{{entity_type}}`, `{{column_descriptions}}`, `{{data_rows}}`, `{{output_format}}`, `{{domain_context}}`

**`generic/statistical-summary`** — Formats statistical data into LLM-readable narrative. Variables: `{{metric_name}}`, `{{data_points}}`, `{{comparison_context}}`, `{{time_period}}`

**`generic/report-generator-system`** — System prompt for the ReportGeneratorAgent. Variables: `{{report_type}}`, `{{company_context}}`, `{{output_structure}}`, `{{tool_descriptions}}`

**`generic/opportunity-identifier-system`** — System prompt for OpportunityIdentifierAgent. Variables: `{{scoring_criteria}}`, `{{entity_type}}`, `{{business_context}}`, `{{threshold_rules}}`

**Domain-specific prompts (recyclables):**

**`opportunity/weekly-guidelines`** — Variables: `{{company_name}}`, `{{report_date}}`, `{{top_opportunities}}`, `{{price_trends}}`, `{{risk_alerts}}`, `{{market_summary}}`, `{{company_policies}}`

**`opportunity/monthly-review`** — Variables: `{{company_name}}`, `{{period}}`, `{{performance_vs_guidelines}}`, `{{price_trend_analysis}}`, `{{market_dynamics}}`, `{{data_quality_summary}}`

**`opportunity/product-nl-context`** — Template for generating NL descriptions of recyclable products. Variables: `{{product_category}}`, `{{location}}`, `{{stock_data}}`, `{{price_history}}`, `{{market_position}}`

---

## 5. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Client's Infrastructure                               │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    Client's BigQuery                              │   │
│  │  ┌──────────────┐  ┌──────────────────┐  ┌───────────────────┐  │   │
│  │  │ inventory_raw │  │ transactions_raw │  │ ETL cron queries  │  │   │
│  │  └──────┬───────┘  └────────┬─────────┘  │ (scheduled daily) │  │   │
│  │         │                   │            └─────────┬─────────┘  │   │
│  │         ▼                   ▼                      │            │   │
│  │  ┌──────────────────────────────────────┐          │            │   │
│  │  │ categorized_inventory                │◄─────────┤            │   │
│  │  │ market_transactions                  │◄─────────┤            │   │
│  │  │ price_statistics                     │◄─────────┤            │   │
│  │  │ opportunity_results  ◄───────────────┼──────────┘            │   │
│  │  │ (scores written back by our service) │                       │   │
│  │  └──────────────┬───────────────────────┘                       │   │
│  └─────────────────┼───────────────────────────────────────────────┘   │
│                    │                                                     │
│  ┌─────────────────┼───────────────────┐                                │
│  │  Client's Dashboard (their code)    │                                │
│  │  Reads opportunity_results from BQ  │                                │
│  │  Reads reports via our API          │                                │
│  └─────────────────────────────────────┘                                │
└────────────────────┼────────────────────────────────────────────────────┘
                     │ FDW (Supabase Wrappers)
                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      Vizu Infrastructure                                 │
│                                                                          │
│  ┌──────────────────────┐  ┌────────────────────────────────────────┐   │
│  │   Supabase (Postgres) │  │  Vector DB (Qdrant via Supabase)      │   │
│  │  ┌──────────────────┐ │  │  ┌──────────────────────────────────┐ │   │
│  │  │ FDW foreign tables│ │  │  │ vector_db.document_chunks        │ │   │
│  │  │ (reads client BQ) │ │  │  │ (NL context per product/entity) │ │   │
│  │  ├──────────────────┤ │  │  │ scope: "opportunity_context"     │ │   │
│  │  │ opportunity_      │ │  │  └────────────────┬─────────────────┘ │   │
│  │  │   reports (HITL)  │ │  │                   │                   │   │
│  │  └──────────────────┘ │  └───────────────────┼───────────────────┘   │
│  └──────────┬───────────┘                       │                        │
│             │                                    │                        │
│             ▼                                    ▼                        │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │              tool_pool_api (Cloud Run)                            │   │
│  │  ┌───────────────────┐  ┌──────────────────┐  ┌──────────────┐  │   │
│  │  │ generate_nl_context│  │ compute_statistics│  │ query_rag    │  │   │
│  │  │ (data → NL text)  │  │ (stats for LLMs) │  │ (RAG search) │  │   │
│  │  └───────────────────┘  └──────────────────┘  └──────────────┘  │   │
│  │  ┌───────────────────┐  ┌──────────────────┐                    │   │
│  │  │ ingest_rag_docs   │  │ query_struct_data│                    │   │
│  │  │ (NL → vector DB)  │  │ (FDW reader)     │                    │   │
│  │  └───────────────────┘  └──────────────────┘                    │   │
│  └──────────────────────────────┬───────────────────────────────────┘   │
│                                 │ tools                                   │
│                                 ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │            opportunity_engine (Cloud Run)                         │   │
│  │                                                                   │   │
│  │  Cron Pipelines (Cloud Scheduler → Cloud Run endpoints):          │   │
│  │                                                                   │   │
│  │  1. RAG Context Pipeline (daily):                                 │   │
│  │     Read BQ via FDW → generate_nl_context → ingest_rag_docs       │   │
│  │                                                                   │   │
│  │  2. Weekly Guidelines Pipeline (Monday):                          │   │
│  │     ReportGeneratorAgent(LangGraph)                               │   │
│  │       → tool: query_rag (inventory + policies + market)           │   │
│  │       → tool: compute_statistics (price trends)                   │   │
│  │       → LLM generates report                                     │   │
│  │       → save to opportunity_reports (draft)                       │   │
│  │                                                                   │   │
│  │  3. Monthly Review Pipeline (1st of month):                       │   │
│  │     ReportGeneratorAgent(LangGraph)                               │   │
│  │       → tool: query_rag (context)                                 │   │
│  │       → tool: compute_statistics (30d performance)                │   │
│  │       → tool: query_structured_data (actuals vs guidelines)       │   │
│  │       → LLM generates report                                     │   │
│  │       → save to opportunity_reports (draft)                       │   │
│  │                                                                   │   │
│  │  4. Opportunity Scoring Pipeline (daily, after ETL):              │   │
│  │     OpportunityIdentifierAgent(LangGraph)                         │   │
│  │       → read FDW data → score → write back to client's BQ         │   │
│  │                                                                   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌──────────────────────────────────────────────────────┐               │
│  │  Langfuse (Prompt Management + Observability)         │               │
│  │  Generic prompts + Domain-specific prompts            │               │
│  └──────────────────────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Architecture Decisions

#### 1. Data Stays in Client's Infrastructure
`opportunity_results` lives in client's BigQuery. Their dashboard reads from their own BQ. We write results back to BQ after scoring. We never duplicate their data in our Supabase — we only read via FDW and generate NL context for our vector DB.

#### 2. RAG as the Bridge Between Structured Data and LLM Reports
Rather than passing raw structured data to the LLM, we:
1. **Daily cron**: Read structured data via FDW → generate natural language context per entity → store in vector DB
2. **Report time**: Agent queries RAG for relevant context (inventory, policies, market) → LLM generates report from NL context

This pattern is critical because:
- LLMs reason better about natural language than raw tables
- RAG context can blend structured data summaries with unstructured company policies
- The same RAG pipeline works for any industry — just change the NL templates

#### 3. LangGraph for Report Generation (Not Simple LLM Calls)
Reports require multi-step tool use:
- Query RAG for inventory context
- Compute statistics for price trends
- Query structured data for specific comparisons
- Compose report from all gathered context

This is a LangGraph agent with tool nodes, not a single `build_prompt() → get_model().invoke()` call. The agent decides which tools to call based on the report type and available data.

#### 4. FDW as the Data Bridge (Unchanged)
Same rationale as before. FDW infrastructure already exists in our repo.

#### 5. Frontend is Client's Responsibility
We do NOT build dashboard tabs in `vizu_dashboard`. The client builds their own dashboard UI. We expose:
- **API endpoints**: `GET /reports`, `POST /reports/{id}/approve` (HITL)
- **Data in their BQ**: `opportunity_results` table they query directly
- **RAG context**: Available to their agents if they want NL summaries

#### 6. Simple Cron with Cloud Run
Cloud Scheduler triggers Cloud Run endpoints. No complex job orchestration. Each pipeline is an HTTP endpoint that Cloud Scheduler POSTs to on schedule.

---

## 6. Phase 0 — Discovery & Requirements

**Goal**: Align on core metrics, personas, data access, and constraints.

### Steps

1. **BigQuery onboarding via existing dashboard flow**
   - Client uses `vizu_dashboard` > Connector page to provide BigQuery credentials
   - `connectorService.ts` → `create_bigquery_server()` RPC → Vault-stored credentials
   - We get the inventory and transaction tables as FDW foreign tables automatically
   - **Leverage**: `connectorService.ts`, `create_bigquery_server()`, `create_bigquery_foreign_table()`

2. **Core metric definition** — Finalize with client:
   - `delta = estimated_market_price - (acquisition_cost + logistics_cost)`
   - "Estimated market price" formula: e.g., P50 of recent transactions + regional correction
   - Logistics cost model: flat multiplier per state pair, or `freight_rate × quantity × distance_factor`

3. **Persona mapping** — Who uses what:
   - **Buyer/vendor**: Weekly guidelines — what to buy/sell, where, at what price
   - **Manager**: Monthly review — performance vs guidelines, trend analysis, market dynamics

4. **Raw data profiling** — Run exploratory queries through FDW foreign tables in Supabase
   - Distinct products, locations, date ranges, null rates, price distributions

5. **Product categorization design** — Cluster raw product descriptions (Material → Sub-type → Grade)

6. **Client validation workshop** — Present taxonomy + delta formula + persona actions

### Deliverables
- Requirements spec with approved delta formula and logistics model
- Data dictionary, data quality report
- Approved product taxonomy
- Persona action mapping

### Exit gate
- Client signs off on taxonomy, delta formula, personas
- FDW foreign tables accessible in Supabase

---

## 7. Phase 1 — FDW Dev Tooling & Data Extraction

**Goal**: Build reusable dev tools for FDW data access and export. Get client data accessible for EDA.

### Steps

1. **Create FDW foreign tables** for the specific inventory and transaction tables we need
   - Use existing `create_bigquery_foreign_table()` RPC
   - **Leverage**: `supabase/migrations/20251219_setup_bigquery_wrapper.sql`, timeout fix (`20260123`)
   - Tables: `bigquery.{client_id}_inventory`, `bigquery.{client_id}_transactions`

2. **Build `scripts/fdw_to_csv.py`** — Reusable dev tool (NOT specific to this client)
   ```python
   # A generic development utility for exporting data from any FDW-connected source.
   # Usage examples:
   #   python scripts/fdw_to_csv.py --table "bigquery.polen_inventory" --output ./data/inventory.csv
   #   python scripts/fdw_to_csv.py --query "SELECT * FROM bigquery.x_sales LIMIT 1000" --output ./data/sales.csv
   #   python scripts/fdw_to_csv.py --table "fdw_postgres.erp_orders" --limit 50000 --output ./data/orders.csv --chunk-size 5000
   #
   # Features:
   #   - Works with ANY FDW foreign table (BigQuery, Postgres, etc.)
   #   - Pagination for large tables (--chunk-size)
   #   - Column filtering (--columns "col1,col2,col3")
   #   - Automatic type inference and CSV formatting
   #   - Progress bar for large exports
   #   - Leverages vizu_supabase_client for connection
   ```
   This script joins the existing `scripts/` collection and will be used every time we connect a new data source. It's the FDW equivalent of a database client's "Export to CSV" button.

3. **Verify data quality** — Row counts, null rates, date ranges from the FDW tables

### Deliverables
- FDW foreign tables for inventory + transactions accessible in Supabase
- `scripts/fdw_to_csv.py` — generic FDW-to-CSV dev tool (reusable across all projects)
- CSV files ready for EDA

### Exit gate
- Can `SELECT * FROM bigquery.{client_id}_inventory` successfully in Supabase
- `fdw_to_csv.py` works with at least 2 different FDW table types
- CSV files verified against expected row counts

---

## 8. Phase 2 — ETL Pipeline (BigQuery Scheduled Queries)

**Goal**: Build scheduled queries in the client's BigQuery that produce analysis-ready tables.

### Steps

1. **Design target tables** (in client's BigQuery dataset):
   - `categorized_inventory` — current stock × location × category × avg acquisition cost
   - `market_transactions` — historical trades with standardized categories
   - `price_statistics` — aggregated metrics per product × region × period

2. **Product categorization query** — SQL mapping from raw descriptions to approved taxonomy

3. **Price statistics query** — Per product-category × region:
   - Mean, median, P25/P75, weighted average
   - Rolling windows (7d, 30d, 90d)
   - Volatility (std dev, coefficient of variation)

4. **Inventory aggregation query** — Per location × category

5. **Set up BigQuery scheduled queries** — Daily cron

6. **Add FDW foreign tables** for the new ETL output tables
   - Use `create_bigquery_foreign_table()` for `price_statistics`, `categorized_inventory`

7. **Data validation** — Post-ETL sanity checks (row counts, null bounds)

### Deliverables
- ETL queries running on schedule in client's BigQuery
- FDW foreign tables for ETL outputs accessible in Supabase
- ETL monitoring/alerting

### Exit gate
- ETL stable for 1+ week
- Client validates sample outputs

### Note on repo artifacts
The BigQuery scheduled queries live in the client's infra. We version the SQL in our repo under a new directory:

```
services/opportunity_engine/
└── bigquery_etl/
    ├── 01_categorize_products.sql
    ├── 02_price_statistics.sql
    ├── 03_inventory_aggregation.sql
    └── 04_opportunity_scoring.sql
```

---

## 9. Phase 3 — EDA & Price Modeling PoC (Notebook)

**Goal**: Understand price dynamics, validate delta formula, build the pricing model. *Can overlap with late Phase 2.*

### Steps

1. **Create Jupyter notebook** using CSV exports from Phase 1
   - **Location**: `notebooks/opportunity_eda.ipynb` (new directory at repo root)

2. **Seasonal price analysis** — Decompose price time series per product × region (trend, seasonal, residual)

3. **Price stability classification** — Coefficient of variation per product × region:
   - Stable (< 10% CV), Moderate (10-25%), Volatile (> 25%)
   - Determines lookback window `n` for each product-region pair

4. **Data sufficiency assessment** — Flag thin-data segments, define minimum thresholds

5. **Lookback window optimization** — Test n = 7/14/30/60/90 days, minimize MAPE via backtesting

6. **Price estimation PoC** — Two-signal blend:
   - Signal A: Weighted moving average with optimized window
   - Signal B: Recent actual transaction prices
   - Combined: Weighted by data quality + stability

7. **Delta formula validation** — Simulate opportunity rankings, correlate with actual profitable sales

8. **PoC review** — Present to client

### Deliverables
- `notebooks/opportunity_eda.ipynb` with full analysis
- EDA report: seasonality, stability classes, data coverage
- Calibrated lookback windows per product × region
- Finalized delta formula with confidence metrics

### Exit gate
- Acceptable prediction accuracy
- Client validates opportunity logic

---

## 10. Phase 4 — System Design

**Goal**: Design all interfaces before building. Separate generic from domain-specific.

### Steps

1. **Generic agent architecture** — Design reusable LangGraph agent patterns:

   **ReportGeneratorAgent** (LangGraph graph):
   - **Nodes**: `init` → `plan_report` → `gather_data` → `compose_report` → `validate_output` → `save`
   - **Tools available**: `query_rag_context`, `compute_statistics`, `query_structured_data`
   - **Configurable via**: prompt name (from Langfuse), report type, data scope, output format
   - **State**: `AgentState` extended with `report_config`, `gathered_context`, `draft_content`
   - **Why LangGraph**: The agent needs to decide WHICH tools to call in WHICH order based on the report type and available data. A weekly report may need RAG + stats, while a monthly report may need structured data + RAG + stats + comparisons. The agent reasons about what to gather.

   **OpportunityIdentifierAgent** (LangGraph graph):
   - **Nodes**: `init` → `load_data` → `compute_scores` → `generate_context` → `write_results`
   - **Tools available**: `query_structured_data`, `compute_statistics`, `generate_nl_context`, `write_to_destination`
   - **Configurable via**: scoring formula (Python callable), entity type, data source, destination (BQ table, Supabase, etc.)
   - **State**: `AgentState` extended with `scoring_config`, `raw_data`, `scored_results`

   **RAGContextGenerator** (Pipeline, not necessarily LangGraph — can be a simple function chain):
   - **Steps**: Read structured data → chunk by entity → generate NL per entity → embed → store in vector DB
   - **Configurable via**: prompt name for NL generation, entity type, source table, vector DB scope
   - This could be a LangChain `Runnable` chain rather than a full LangGraph agent, since there's no conditional branching — it's a deterministic pipeline.

2. **Tool design** — Detailed specs for each generic tool:

   | Tool | Input | Output | Registered In |
   |------|-------|--------|---------------|
   | `generate_nl_context` | `rows: list[dict]`, `entity_type: str`, `prompt_name: str` | `list[NLDocument]` | `tool_pool_api` |
   | `compute_statistics` | `data: list[dict]`, `group_by: list[str]`, `metrics: list[str]`, `operations: list[str]` | `StatisticalSummary` (formatted text + raw dict) | `tool_pool_api` |
   | `ingest_rag_documents` | `documents: list[NLDocument]`, `client_id: str`, `scope: str` | `IngestResult` | `tool_pool_api` |
   | `query_structured_data` | `table: str`, `filters: dict`, `order_by: str`, `limit: int` | `list[dict]` rows | `tool_pool_api` |
   | `query_rag_context` | `query: str`, `client_id: str`, `scope: str`, `top_k: int` | `list[Document]` | `tool_pool_api` (extends existing `executar_rag_cliente`) |

3. **NL from Structured Data endpoint design**:
   ```
   POST /api/v1/nl-from-data        — Generate NL descriptions from structured rows
   POST /api/v1/statistical-summary  — Format statistical data for LLM consumption
   ```
   These can live in `tool_pool_api` as HTTP endpoints AND as MCP tools. Dual exposure.

4. **Context builder design** — How each report mode builds its agent context:

   | Mode | Agent Tools Used | RAG Scopes Queried | Statistical Operations |
   |------|-----------------|-------------------|----------------------|
   | Weekly Guidelines | `query_rag_context`, `compute_statistics` | `opportunity_context` (product NL), `company_policies`, `market_data` | 7d price trends, volatility flags, top-N ranking |
   | Monthly Review | `query_rag_context`, `compute_statistics`, `query_structured_data` | `opportunity_context`, `company_policies` | 30d performance, actuals vs. guidelines delta, trend analysis |

5. **API design** — Endpoints for the opportunity_engine service:
   ```
   # Cron triggers (Cloud Scheduler → Cloud Run)
   POST /cron/generate-rag-context   — Daily: refresh NL context in vector DB
   POST /cron/generate-weekly        — Monday: generate weekly guidelines report
   POST /cron/generate-monthly       — 1st of month: generate monthly review report
   POST /cron/score-opportunities    — Daily (after ETL): run scoring, write to client BQ

   # Report management (called by client's dashboard or internal tools)
   GET  /reports                     — List reports (filtered by type, status, date)
   GET  /reports/{id}                — Get specific report content
   POST /reports/{id}/approve        — HITL approve
   POST /reports/{id}/reject         — HITL reject
   GET  /health                      — Health check
   ```

6. **Langfuse prompt design** — Draft all prompts (generic + domain), version as `v1`, label `staging`

7. **Infrastructure design**:
   - Cloud Run service: `opportunity-engine` (same pattern as `atendente-core`)
   - Cloud Scheduler: 4 cron jobs (daily context refresh, daily scoring, weekly report, monthly report)
   - Redis: Only if LangGraph agents need checkpointing (likely yes for multi-step tool use)
   - Supabase: `opportunity_reports` table only (results go to client's BQ)
   - Vector DB: New scope `opportunity_context` in existing `vector_db.document_chunks`

### Deliverables
- API specification (OpenAPI)
- LangGraph agent graph designs (state diagrams)
- Tool interface specifications
- Langfuse prompt drafts (generic + domain)
- Architecture diagram (updated from Section 5)

### Exit gate
- Team reviews and approves agent graph designs
- Client approves report output format

---

## 11. Phase 5 — Generic Agent & Tool Implementation

**Goal**: Build the reusable platform components. These are industry-agnostic and live in `libs/` and `tool_pool_api/`. *Depends on Phase 4.*

### 5.1 Statistical Data Tools (`libs/vizu_shared_utils/` or new lib)

Add statistical formatting utilities that help LLMs reason about data:

```python
# libs/vizu_shared_utils/src/vizu_shared_utils/statistical_formatter.py

class StatisticalFormatter:
    """Formats statistical data for LLM consumption.

    Design principle: LLMs reason badly about raw numbers in tables.
    These functions convert statistical data into contextual natural language
    that preserves the important signals (trends, anomalies, comparisons).
    """

    @staticmethod
    def format_distribution(values: list[float], label: str, unit: str = "") -> str:
        """'Price of Cardboard in SP: median R$2.50/kg (IQR: R$2.10–R$2.80),
        trending up +5.2% over 30d, moderate volatility (CV=18%)'"""

    @staticmethod
    def format_comparison(groups: dict[str, list[float]], metric_label: str) -> str:
        """'Cardboard in SP (R$2.50/kg) is 15% higher than RJ (R$2.17/kg), gap widening'"""

    @staticmethod
    def format_time_series(series: list[tuple[str, float]], label: str) -> str:
        """'30-day trend: upward (+8.3%), weekly seasonality (peaks Mon-Tue).
         Last 7d: stable. 3 anomalies detected (>2σ).'"""

    @staticmethod
    def detect_anomalies(values: list[float], method: str = "zscore", threshold: float = 2.0) -> list[dict]:
        """Returns anomaly indices with context dicts for LLM consumption."""

    @staticmethod
    def rank_with_context(items: list[dict], score_field: str, context_fields: list[str], top_n: int = 10) -> str:
        """'Top 3: 1) Cardboard SP→RJ (score: 85, delta: +R$0.40/kg, vol: 2000kg) 2) ...'"""

    @staticmethod
    def compute_summary(values: list[float]) -> dict:
        """Returns dict with mean, median, p25, p75, std, cv, min, max, count, trend."""
```

**Best practice**: Pure functions, no side effects, no LLM calls. These are formatting utilities, not agents. They transform numbers into text that agents can include in prompts.

### 5.2 New Tool Module in `tool_pool_api/`

Register new generic tools in `tool_pool_api/server/tool_modules/data_intelligence_module.py`:

```python
@register_module
def register_data_intelligence_tools(mcp: FastMCP) -> list[str]:
    """Generic tools for data intelligence tasks — usable by any agent."""

    @mcp.tool()
    async def generate_nl_context(
        rows: list[dict],
        entity_type: str,
        prompt_name: str = "generic/nl-from-structured-data",
        domain_context: str = "",
    ) -> list[dict]:
        """Convert structured data rows into natural language descriptions per entity.

        Each row represents one entity (product, SKU, customer, etc.).
        Returns a list of {entity_id, text, metadata} dicts ready for RAG ingestion.

        Uses Langfuse prompt `prompt_name` for NL generation with LLM.
        """

    @mcp.tool()
    async def compute_statistics(
        data: list[dict],
        group_by: list[str],
        metrics: list[str],
        operations: list[str] = ["mean", "median", "std", "trend_direction"],
    ) -> dict:
        """Compute statistical aggregations and return both raw numbers and LLM-formatted text.

        Uses StatisticalFormatter to produce natural language summaries alongside raw data.
        Operations: mean, median, p25, p75, std, cv, min, max, trend_direction,
                    rolling_avg, yoy_change, anomaly_count.
        """

    @mcp.tool()
    async def ingest_rag_documents(
        documents: list[dict],  # [{entity_id, text, metadata}]
        client_id: str,
        scope: str,
        category: str = "structured_data_context",
    ) -> dict:
        """Ingest NL documents into vector DB (vector_db.document_chunks).

        Replaces existing documents for the same client_id + scope + entity_id
        to avoid stale context accumulation.
        """

    @mcp.tool()
    async def query_structured_data(
        table: str,
        filters: dict | None = None,
        order_by: str | None = None,
        limit: int = 100,
        client_id: str | None = None,
    ) -> list[dict]:
        """Read from Supabase tables or FDW foreign tables with type-safe filtering.

        If client_id is provided, automatically applies RLS-safe WHERE clause.
        Supports FDW tables (bigquery.*, fdw_postgres.*) and native Supabase tables.
        """

    return ["generate_nl_context", "compute_statistics", "ingest_rag_documents", "query_structured_data"]
```

**Best practice**: Each tool does ONE thing. No tool calls another tool. The LangGraph agent orchestrates multi-tool workflows.

### 5.3 NL from Structured Data — HTTP Endpoint

Add to `tool_pool_api` (or standalone service) as an HTTP endpoint accessible without MCP:

```python
# tool_pool_api/api/nl_endpoints.py

@router.post("/api/v1/nl-from-data")
async def generate_nl_from_data(request: NLFromDataRequest) -> NLFromDataResponse:
    """Standalone HTTP endpoint for converting structured data to natural language.

    Same logic as the generate_nl_context MCP tool, but accessible via REST API.
    Useful for cron jobs, scripts, and external integrations that don't use MCP.
    """

@router.post("/api/v1/statistical-summary")
async def generate_statistical_summary(request: StatisticalSummaryRequest) -> StatisticalSummaryResponse:
    """Standalone HTTP endpoint for statistical data formatting.

    Same logic as compute_statistics MCP tool, exposed as REST.
    """
```

**Best practice**: DRY — the HTTP endpoints and MCP tools share the same core logic. The endpoint is a thin HTTP wrapper around the same function the tool calls.

### 5.4 LangGraph Agent Patterns

Build reusable agent graph templates using `vizu_agent_framework`:

#### ReportGeneratorAgent

```python
# Could live in libs/vizu_agent_framework/ as a reusable pattern,
# or in a new lib like libs/vizu_report_agents/

class ReportGeneratorConfig(BaseModel):
    """Configuration for a report generation task."""
    report_type: str                    # e.g., "weekly_guidelines", "monthly_review"
    prompt_name: str                    # Langfuse prompt name
    data_scopes: list[str]             # RAG scopes to query
    statistical_queries: list[dict]     # Stats to compute
    output_format: str = "markdown"     # Output format
    company_context_fields: list[str]   # Which VizuClientContext fields to include

class ReportGeneratorAgent:
    """LangGraph agent that generates reports using RAG + statistics + structured data.

    Graph: init → plan → gather_context → compose → validate → save

    The 'plan' node uses the LLM to decide which tools to call based on
    the report config. The 'gather_context' node executes tool calls
    (potentially multiple rounds). The 'compose' node generates the
    final report from all gathered context.
    """

    def __init__(self, config: ReportGeneratorConfig):
        self.config = config
        self.graph = self._build_graph()

    def _build_graph(self) -> CompiledGraph:
        builder = AgentBuilder(AgentConfig(
            name=f"report_generator_{self.config.report_type}",
            role="report_generator",
            enabled_tools=[
                "query_rag_context", "compute_statistics", "query_structured_data"
            ],
        ))
        # Build LangGraph with tool nodes
        # The agent has access to tools and decides which to call
        ...
```

#### OpportunityIdentifierAgent

```python
class OpportunityScoringConfig(BaseModel):
    """Configuration for opportunity scoring."""
    entity_type: str                    # "product", "sku", "customer", etc.
    scoring_formula: str                # Python expression or callable name
    source_table: str                   # FDW table to read from
    destination: DestinationConfig      # Where to write results (BQ, Supabase, etc.)
    score_threshold: float = 0.0        # Minimum score to keep
    nl_context_prompt: str              # Prompt for NL generation of top results

class OpportunityIdentifierAgent:
    """LangGraph agent that scores entities and identifies opportunities.

    Graph: init → load_data → score → rank → generate_nl_context → write_results

    The scoring step applies a configurable formula.
    The NL context step generates natural language descriptions for top-N results.
    The write step pushes results to the configured destination.
    """
```

**Best practice**: These agents are GRAPH TEMPLATES, not final implementations. The use-case service (`opportunity_engine`) instantiates them with specific configs and prompts.

### 5.5 Supabase Migration — Reports Table

```sql
-- Only opportunity_reports in our Supabase (results go to client's BQ)
CREATE TABLE opportunity_reports (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    client_id UUID NOT NULL REFERENCES clientes_vizu(id),
    report_type TEXT NOT NULL,
    content TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    reviewed_by UUID,
    reviewed_at TIMESTAMPTZ,
    reviewer_notes TEXT,
    prompt_version TEXT,
    context_snapshot JSONB,
    metadata JSONB DEFAULT '{}'
);

ALTER TABLE opportunity_reports ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on opportunity_reports"
    ON opportunity_reports FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Users can view their own reports"
    ON opportunity_reports FOR SELECT
    USING (client_id IN (
        SELECT id FROM clientes_vizu WHERE auth.uid() = ANY(user_ids)
    ));
```

### 5.6 Langfuse Prompts — Generic

Create in Langfuse (label: `production`):
- `generic/nl-from-structured-data` (v1)
- `generic/statistical-summary` (v1)
- `generic/report-generator-system` (v1)
- `generic/opportunity-identifier-system` (v1)

Add to `scripts/create_langfuse_prompts.py` for automated creation.

### Deliverables
- `StatisticalFormatter` in `vizu_shared_utils`
- `data_intelligence_module` tools in `tool_pool_api`
- NL-from-data HTTP endpoints
- `ReportGeneratorAgent` and `OpportunityIdentifierAgent` graph templates
- `opportunity_reports` Supabase migration
- Generic Langfuse prompts

### Exit gate
- Tools can be called independently via MCP and HTTP
- Agent graphs can be instantiated with test configs and produce output
- Unit tests pass for `StatisticalFormatter`

---

## 12. Phase 6 — Opportunity Engine Service (Use-Case Assembly)

**Goal**: Wire generic components into the recyclables use case. This is the thin domain-specific layer. *Depends on Phase 5.*

### 6.1 Scoring Configuration

```python
# services/opportunity_engine/src/opportunity_engine/config/scoring_config.py

RECYCLABLES_SCORING = OpportunityScoringConfig(
    entity_type="recyclable_product",
    scoring_formula="delta * inventory_volume * price_confidence",
    source_table="bigquery.{client_id}_opportunity_scores",  # From BQ ETL
    destination=DestinationConfig(
        type="bigquery",
        table="{client_dataset}.opportunity_results",
        write_mode="replace",  # Full refresh daily
    ),
    score_threshold=0.0,
    nl_context_prompt="opportunity/product-nl-context",
)
```

### 6.2 Pipeline Wiring

```python
# services/opportunity_engine/src/opportunity_engine/pipelines/rag_context_pipeline.py

async def refresh_rag_context(client_id: str, settings: Settings):
    """Daily cron: Read structured data from BQ via FDW → generate NL context → store in vector DB.

    This is the RAG context pipeline that feeds the report agents.
    Uses generic tools (generate_nl_context, ingest_rag_documents) with
    recyclables-specific prompt (opportunity/product-nl-context).
    """
    # 1. Read structured data via FDW
    data = await query_structured_data(
        table=f"bigquery.{client_id}_categorized_inventory",
        limit=5000,
        client_id=client_id,
    )

    # 2. Generate NL context per product-location pair
    nl_docs = await generate_nl_context(
        rows=data,
        entity_type="recyclable_product",
        prompt_name="opportunity/product-nl-context",
        domain_context="Brazilian recyclable materials market",
    )

    # 3. Store in vector DB (replace stale context)
    await ingest_rag_documents(
        documents=nl_docs,
        client_id=client_id,
        scope="opportunity_context",
        category="inventory_context",
    )
```

```python
# services/opportunity_engine/src/opportunity_engine/pipelines/weekly_report_pipeline.py

async def generate_weekly_report(client_id: str, settings: Settings):
    """Monday cron: Generate weekly vendor guidelines using ReportGeneratorAgent.

    The agent uses RAG to gather:
    - Inventory context (from daily NL context refresh)
    - Company purchasing policies (from platform knowledge base)
    - Market trends (from price statistics)

    Then computes statistics on 7-day price movements and composes the report.
    """
    agent = ReportGeneratorAgent(ReportGeneratorConfig(
        report_type="weekly_guidelines",
        prompt_name="opportunity/weekly-guidelines",
        data_scopes=["opportunity_context", "company_policies", "market_data"],
        statistical_queries=[
            {"table": f"bigquery.{client_id}_price_statistics", "period": "7d",
             "metrics": ["price_mean", "price_cv"], "group_by": ["product_category", "region"]},
        ],
        output_format="markdown",
        company_context_fields=["company_profile", "purchasing_policies"],
    ))

    result = await agent.run(client_id=client_id)

    # Save to opportunity_reports with HITL status
    await save_report(client_id, "weekly_guidelines", result.content, result.context_snapshot)
```

```python
# services/opportunity_engine/src/opportunity_engine/pipelines/monthly_report_pipeline.py

async def generate_monthly_report(client_id: str, settings: Settings):
    """1st of month cron: Generate monthly performance review.

    Uses RAG for context + statistical tools for 30-day performance analysis.
    Compares actual transactions against previous guidelines.
    """
    agent = ReportGeneratorAgent(ReportGeneratorConfig(
        report_type="monthly_review",
        prompt_name="opportunity/monthly-review",
        data_scopes=["opportunity_context", "company_policies"],
        statistical_queries=[
            {"table": f"bigquery.{client_id}_market_transactions", "period": "30d",
             "metrics": ["actual_price", "recommended_price", "volume"],
             "group_by": ["product_category", "region"]},
            {"table": f"bigquery.{client_id}_price_statistics", "period": "30d",
             "metrics": ["price_mean", "price_cv", "trend_direction"],
             "group_by": ["product_category", "region"]},
        ],
        output_format="markdown",
        company_context_fields=["company_profile"],
    ))

    result = await agent.run(client_id=client_id)
    await save_report(client_id, "monthly_review", result.content, result.context_snapshot)
```

### 6.3 FastAPI Cron Endpoints

```python
# services/opportunity_engine/src/opportunity_engine/main.py

app = FastAPI(title="Opportunity Engine")
setup_observability(app, "opportunity-engine")

# Cron endpoints — triggered by Cloud Scheduler
@app.post("/cron/generate-rag-context")
async def cron_rag_context():
    """Daily: Refresh NL context in vector DB from structured data."""
    await refresh_rag_context(settings.client_id, settings)
    return {"status": "completed"}

@app.post("/cron/generate-weekly")
async def cron_weekly():
    """Monday 8am BRT: Generate weekly vendor guidelines."""
    report_id = await generate_weekly_report(settings.client_id, settings)
    return {"status": "draft", "report_id": report_id}

@app.post("/cron/generate-monthly")
async def cron_monthly():
    """1st of month 8am BRT: Generate monthly performance review."""
    report_id = await generate_monthly_report(settings.client_id, settings)
    return {"status": "draft", "report_id": report_id}

@app.post("/cron/score-opportunities")
async def cron_scoring():
    """Daily after ETL: Score opportunities and write back to client's BQ."""
    await run_opportunity_scoring(settings.client_id, settings)
    return {"status": "completed"}

# Report management — called by client's dashboard
@app.get("/reports")
async def list_reports(report_type: str | None = None, status: str | None = None):
    ...

@app.get("/reports/{report_id}")
async def get_report(report_id: str):
    ...

@app.post("/reports/{report_id}/approve")
async def approve_report(report_id: str, reviewer_notes: str | None = None):
    ...

@app.post("/reports/{report_id}/reject")
async def reject_report(report_id: str, reviewer_notes: str):
    ...
```

### 6.4 BigQuery Write-Back

```python
# services/opportunity_engine/src/opportunity_engine/pipelines/scoring_pipeline.py

async def run_opportunity_scoring(client_id: str, settings: Settings):
    """Read FDW data, apply scoring, write results BACK to client's BigQuery.

    Uses OpportunityIdentifierAgent with recyclables-specific scoring config.
    Results are written to {client_dataset}.opportunity_results in client's BQ.
    The client's dashboard reads from their own BQ.
    """
    agent = OpportunityIdentifierAgent(RECYCLABLES_SCORING)
    await agent.run(client_id=client_id)
```

For writing back to BigQuery, we use `google-cloud-bigquery` SDK (not FDW, which is read-only from Supabase's perspective). The `BigQueryConnector` in `vizu_data_connectors` or direct SDK usage.

### 6.5 Langfuse Prompts — Domain-Specific

Create in Langfuse (label: `production`):
- `opportunity/weekly-guidelines` (v1)
- `opportunity/monthly-review` (v1)
- `opportunity/product-nl-context` (v1)

Add fallback templates in `services/opportunity_engine/src/opportunity_engine/prompts/templates.py`

### 6.6 Docker & Compose

```yaml
# docker-compose.yml addition
opportunity_engine:
  container_name: vizu_opportunity_engine
  platform: linux/amd64
  build:
    context: .
    dockerfile: ./services/opportunity_engine/Dockerfile
  env_file:
    - .env
  environment:
    <<: *common-env
    PYTHONPATH: /app/services/opportunity_engine/src
    TARGET_CLIENT_ID: ${OPPORTUNITY_CLIENT_ID}
  ports:
    - "8010:8000"
  volumes:
    - ./services/opportunity_engine/src:/app/src
    - ./libs:/app/libs
```

### Deliverables
- `opportunity_engine` service deployed in staging
- All 4 cron pipelines functional (RAG context, scoring, weekly, monthly)
- Domain-specific Langfuse prompts live
- BQ write-back working (results appear in client's BigQuery)
- E2E: BQ ETL → FDW read → score → write back to BQ → NL context → vector DB → agent generates report → saves draft

### Exit gate
- Agent produces meaningful reports on real data
- Client can see scored opportunities in their BigQuery
- Reports accessible via API

---

## 13. Phase 7 — Testing, Go-Live & Maintenance

> **Note**: Frontend/dashboard is built by the client on their infrastructure, reading from their BigQuery (`opportunity_results`) and our API (`/reports`). We provide API documentation and sample queries but do NOT build the frontend.

### Testing

**Generic component tests:**
- Unit tests for `StatisticalFormatter` (pure functions, easy to test)
- Unit tests for `generate_nl_context`, `compute_statistics` tools (mock LLM + DB)
- Integration tests for `ReportGeneratorAgent` graph (mock tools, verify node transitions)
- Integration tests for `OpportunityIdentifierAgent` graph (mock data, verify scoring)

**Domain-specific tests:**
- Integration test: full pipeline (ETL → FDW → NL context → vector DB → agent → report → save)
- E2E test: BQ write-back (score → write to client BQ → verify results)
- Report quality: Human review of generated reports against expected format + content
- Prompt iteration: Tune prompts in Langfuse based on output quality

**API tests:**
- All cron endpoints return expected status codes
- Report CRUD operations with RLS enforcement
- Auth: Cloud Scheduler auth (API key or OIDC) verified

### Go-Live
- Deploy to Cloud Run (same pattern as atendente-core)
- Cloud Scheduler: 4 cron jobs
  - Daily ~7am BRT: RAG context refresh (`/cron/generate-rag-context`)
  - Daily ~7:30am BRT: Opportunity scoring (`/cron/score-opportunities`)
  - Monday 8am BRT: Weekly guidelines (`/cron/generate-weekly`)
  - 1st of month 8am BRT: Monthly review (`/cron/generate-monthly`)
- Monitoring: `setup_observability()` → Grafana dashboards
- 2-week close monitoring

### Agent Graduation
- After N successful HITL cycles with < X% edit rate → offer autonomous mode
- Configurable: `HITL_REQUIRED=true|false` env var

### Maintenance (Ongoing)
- Monthly review meetings
- Delta formula refinement based on real P&L outcomes
- Prompt tuning based on HITL edit patterns
- ML upgrade evaluation if data warrants it

---

## 14. Dependency Graph

```
Phase 0 (Discovery & Requirements)
    │
    ▼
Phase 1 (FDW Dev Tooling & CSV Export)
    │
    ├──────────────────────────┐
    ▼                          ▼
Phase 2 (BigQuery ETL)    Phase 3 (EDA Notebook — uses CSVs from Phase 1)
    │                          │
    └────────┬─────────────────┘
             ▼
       Phase 4 (System Design — generic + domain-specific)
             │
             ├─────────────────────────────────┐
             ▼                                  ▼
       Phase 5 (Generic Platform)          Phase 6 prep (Domain config)
       ├── 5.1 StatisticalFormatter        (can design scoring config,
       ├── 5.2 tool_pool_api tools          prompts, table mappings
       ├── 5.3 NL-from-data endpoint        in parallel with Phase 5)
       ├── 5.4 LangGraph agent patterns
       ├── 5.5 Supabase migration
       └── 5.6 Generic Langfuse prompts
             │
             ▼
       Phase 6 (Use-Case Assembly — Opportunity Engine)
       ├── 6.1 Scoring config
       ├── 6.2 Pipeline wiring (RAG context, weekly, monthly)
       ├── 6.3 FastAPI cron endpoints
       ├── 6.4 BQ write-back
       ├── 6.5 Domain Langfuse prompts
       └── 6.6 Docker & Compose
             │
             ▼
       Phase 7 (Test → Go-Live → Maintenance)
```

**Key insight**: Phase 5 (generic) can start before Phase 6 domain config is finalized. The generic tools and agent patterns don't depend on recyclables-specific details. This enables parallel work.

---

## 15. Decisions & Open Items

### Decisions Made

| Decision | Rationale |
|----------|-----------|
| **Agnostic architecture** | Every component (agents, tools, formatters) is domain-agnostic. Recyclables is the first deployment, not the only one. New industries = new config + prompts, not new code. |
| **`opportunity_results` in client's BigQuery** | Their dashboard reads from their BQ. We write results back to BQ after scoring. We never duplicate their structured data in our Supabase. |
| **Frontend is client's responsibility** | We provide API endpoints + data in their BQ. They build their own dashboard UI. We do NOT build tabs in `vizu_dashboard`. |
| **RAG as bridge between structured data and reports** | Daily cron generates NL context from structured data → stores in vector DB. Report agents query RAG instead of raw tables. LLMs reason better about NL than raw numbers. |
| **LangGraph for report generation** | Reports require multi-step tool use (RAG query + stats computation + structured data queries). Not a single LLM call — the agent decides which tools to call based on report config. |
| **`fdw_to_csv.py` as generic dev tool** | Not specific to this client — reusable every time we connect a new FDW data source. Lives in `scripts/` for the team. |
| **FDW as data bridge** (not BigQuery SDK for reads) | Infrastructure already exists. Query BQ as Postgres. No SDK dependency for reads. SDK only for write-back. |
| **ETL in client's BigQuery** | Data stays in their environment. We version the SQL in our repo. |
| **Statistical-first pricing** | No ML models initially. Weighted moving averages + stability classification. Upgrade path if EDA warrants. |
| **HITL → autonomous** graduation | Start with mandatory review. Graduate after proven reliability. |
| **Simple Cloud Run cron** | Cloud Scheduler POSTs to Cloud Run endpoints. No complex job orchestration. Each pipeline is one HTTP endpoint. |
| **Tools as atomic operations** | Each tool does ONE thing. No tool calls another tool. LangGraph agents orchestrate multi-tool workflows. |
| **DRY: MCP tools + HTTP endpoints share core logic** | Same function exposed as MCP tool (for agents) and HTTP endpoint (for cron jobs/scripts). Thin wrapper pattern. |

### Revised: What's NOT Needed from Original Plan

| Original Item | Status | Why |
|---------------|--------|-----|
| `opportunity_results` Supabase table | **Removed** | Results live in client's BQ, not our Supabase |
| FDW materialization (Supabase cron copying FDW → local table) | **Removed** | No local copy needed. Agent reads FDW directly for context; scores written back to BQ. |
| `vizu_dashboard` frontend tab | **Removed** | Client builds their own dashboard. We provide API + BQ data. |
| `GET /opportunities` endpoint | **Removed** | Client queries their own BQ directly for opportunity data. |
| Simple `build_prompt() → get_model().invoke()` for reports | **Replaced** | LangGraph agents with tool use for multi-step context gathering. |

### Open Items

| Item | Resolve By |
|------|-----------|
| Unit standardization (kg vs ton vs unit) | Phase 0 — data profiling |
| Prediction accuracy threshold | Phase 3 — PoC review with client |
| Logistics cost data source (client has freight rates or estimate?) | Phase 0 — requirements |
| Cloud Scheduler auth method (API key vs OIDC token) | Phase 4 — system design |
| `ReportGeneratorAgent` location: `libs/vizu_agent_framework/` or new lib? | Phase 4 — determine if agent patterns are generic enough for the framework lib or need their own |
| `StatisticalFormatter` location: `vizu_shared_utils` or new lib `vizu_analytics_utils`? | Phase 4 — based on scope |
| BQ write-back method: `vizu_data_connectors` BigQueryConnector or direct SDK? | Phase 4 — evaluate connector fitness |
| RAG context refresh strategy: full replace vs. incremental update | Phase 4 — depends on data volume |
| Email/notification delivery for reports | Phase 7 — maintenance backlog |
| Agent autonomy metrics (what edit rate triggers graduation?) | Phase 7 — after initial HITL data |

### Risk Register

| Risk | Mitigation |
|------|-----------|
| Data sparsity in some product × region combos | Wider regional averages as fallback, flag low-confidence in NL context |
| LLM output quality for reports | HITL review + iterative prompt tuning. LangGraph enables structured validation before output. |
| NL context quality (garbage in → garbage out for RAG) | Careful prompt design for `generic/nl-from-structured-data`. Human review of NL samples before going live. |
| Generic agents too abstract / hard to debug | Start with direct pipeline code, refactor to generic patterns once the domain logic stabilizes. Don't over-abstract too early. |
| FDW query performance on large BQ tables | Read once daily (cron), not on-demand. NL context cached in vector DB. |
| BigQuery write-back permissions | Requires service account with BQ write access to client's dataset. Validate in Phase 0. |
| BigQuery ETL scheduled query failures | Monitoring in client's GCP, alerting, manual re-run procedure |
| Logistics formula changes | Parameterize in BQ scoring SQL, reviewable without code deploy |
