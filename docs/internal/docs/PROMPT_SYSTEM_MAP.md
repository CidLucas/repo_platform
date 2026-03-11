# Prompt System Map — Vizu Mono

> Generated 2026-03-11. Documents every prompt, where it's used, what variables feed it, and what it's trying to achieve.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [The Prompt Loading Chain](#2-the-prompt-loading-chain)
3. [Process Flow & Prompt Map](#3-process-flow--prompt-map)
   - [3.1 Supervisor (LangGraph Entry)](#31-supervisor-langgraph-entry)
   - [3.2 SQL Generation — Direct Path](#32-sql-generation--direct-path)
   - [3.3 SQL Generation — Tool Path](#33-sql-generation--tool-path)
   - [3.4 RAG Pipeline](#34-rag-pipeline)
   - [3.5 Supporting Prompts](#35-supporting-prompts)
4. [Variable Reference](#4-variable-reference)
5. [Prompt Techniques Used](#5-prompt-techniques-used)
6. [Langfuse Cleanup — Prompts to Delete](#6-langfuse-cleanup--prompts-to-delete)
7. [Known Issues & Tech Debt](#7-known-issues--tech-debt)

---

## 1. Architecture Overview

```
User (vizu_dashboard) ─→ atendente_core (LangGraph agent)
                              │
                              ├── Supervisor Node ─→ LLM call (system prompt from Langfuse)
                              │       │
                              │       ├── decides: call tool? respond? elicit?
                              │       │
                              ├── Execute Tools Node ─→ MCP tools via tool_pool_api
                              │       │
                              │       ├── execute_sql ─→ SQL generation LLM call (prompt from Langfuse)
                              │       ├── executar_rag_cliente ─→ RAG chain (prompt from templates.py ⚠️)
                              │       ├── Google Suite tools
                              │       └── Web Monitor tools
                              │
                              └── Await Elicitation Node ─→ HITL pause
```

The LangGraph agent has 3 nodes:
- **supervisor** — calls LLM with system prompt + conversation history, decides next action
- **execute_tools** — runs MCP tool calls in parallel, returns results to supervisor
- **await_elicitation** — pauses for human input when HITL is triggered

**Prompt sources** (by priority):
1. **Langfuse** (label=`"production"`) — primary source of truth, version-controlled
2. **Builtin fallback** (`templates.py` with Jinja2) — only if `PROMPT_ALLOW_FALLBACK=true`

---

## 2. The Prompt Loading Chain

```
build_prompt(name, variables, context_service)
    │
    ├── 1. PromptLoader._get_langfuse_client()
    │       └── LangfusePromptClient.get_prompt(name, label="production")
    │           └── Langfuse SDK internal cache (TTL 300s)
    │               └── HTTP to Langfuse server
    │
    ├── 2. On failure: Circuit breaker (60s cooldown)
    │       └── If PROMPT_ALLOW_FALLBACK=true:
    │           └── BUILTIN_TEMPLATES[name] → Jinja2 render
    │       └── If false: raise error
    │
    └── 3. Variable injection:
            ├── Langfuse: {{variable}} syntax (SDK .compile())
            └── Builtin: {{ variable }} + {% if %}/{% for %} (Jinja2 renderer)
```

**Key difference**: Langfuse's `{{var}}` syntax is plain substitution only — no conditionals or loops. The Jinja2 builtin fallback supports `{% if %}`, `{% for %}`, etc. Prompts must be designed to work with Langfuse's simpler syntax.

**File locations:**
- `libs/vizu_prompt_management/src/vizu_prompt_management/dynamic_builder.py` — `build_prompt()` entry point
- `libs/vizu_prompt_management/src/vizu_prompt_management/loader.py` — `PromptLoader` with Langfuse + fallback
- `libs/vizu_prompt_management/src/vizu_prompt_management/templates.py` — builtin template registry

---

## 3. Process Flow & Prompt Map

### 3.1 Supervisor (LangGraph Entry)

The supervisor is the brain of the agent. Every conversational turn starts here.

**Prompt selection** (in `nodes.py` → `build_dynamic_system_prompt()`):

| Condition | Prompt Name | Why |
|-----------|-------------|-----|
| `execute_sql` in client's tools | `atendente/sql-direct` | Supervisor generates SQL directly — saves a second LLM call |
| Otherwise | `atendente/default` | Relies on `executar_sql_agent` tool to handle SQL generation |

#### `atendente/sql-direct` (v5 — current in Langfuse)

| Aspect | Detail |
|--------|--------|
| **Langfuse name** | `atendente/sql-direct` |
| **Loaded via** | `build_prompt()` → Langfuse (primary) |
| **Goal** | System prompt for the data analyst agent when it has direct SQL execution capability. Contains the full database schema so the LLM can write SQL inline without a second LLM call. |
| **Variables** | `{{nome_empresa}}` — company name (from `SafeClientContext.nome_empresa`)<br>`{{tools_description}}` — dynamically built from `ToolRegistry` + available tools list<br>`{{context_sections}}` — compiled from Context 2.0 sections (company profile + data schema) |
| **Prompt techniques** | **Schema embedding** — full star schema with types, PKs, FKs, and row counts so the LLM knows what's available.<br>**Negative constraints** — "NEVER include client_id", "NOT valor_total", "No data_transacao column".<br>**Few-shot SQL examples** — 8+ real query patterns covering top-N, CTEs, JOINs, ILIKE, date filtering.<br>**Join reference table** — explicit FK mapping with warnings about asymmetric join (`data_competencia_id → data_id`).<br>**Response format spec** — constrains output to 2-3 sentence summaries since data shows in interactive table.<br>**RAG query rewriting rules** — embedded instructions for when the agent calls the RAG tool. |

#### `atendente/default` (v3 — current in Langfuse)

| Aspect | Detail |
|--------|--------|
| **Langfuse name** | `atendente/default` |
| **Loaded via** | `build_prompt()` → Langfuse (primary) |
| **Goal** | System prompt for the data analyst agent when SQL is handled by a separate tool (`executar_sql_agent`). No embedded schema — the tool handles SQL generation. |
| **Variables** | Same 3: `{{nome_empresa}}`, `{{tools_description}}`, `{{context_sections}}` |
| **Prompt techniques** | **Tool routing rules** — "data questions → executar_sql_agent", "knowledge questions → executar_rag_cliente".<br>**Fallback strategy table** — maps unavailable dimensions to alternatives (e.g., "no bairro data → offer by cidade").<br>**Common situations** — default behaviors for unspecified periods, rankings, empty data.<br>**RAG query rewriting rules** — same as sql-direct.<br>**Response format spec** — same 2-3 sentence summary constraint.<br>**Written in Portuguese** — matches the target user language. |

---

### 3.2 SQL Generation — Direct Path

When the supervisor has `execute_sql` available, it writes SQL inline and calls the tool. The tool validates + executes. **No second LLM call** — all SQL intelligence lives in the supervisor prompt (`atendente/sql-direct`).

```
User question
    → Supervisor LLM (atendente/sql-direct prompt, with embedded schema)
        → LLM generates: execute_sql(sql="SELECT ...")
            → execute_tools_node sends to tool_pool_api
                → sql_module.py validates SQL (SELECT only, no client_id, analytics_v2 schema)
                → Injects client_id WHERE clause automatically
                → Executes against PostgreSQL
                → Returns 3-tier result (full → frontend 20 rows → LLM 3 samples)
            → Supervisor receives tool result, generates natural language summary
```

**Prompts in this path:** Only `atendente/sql-direct` — the sql-direct prompt IS the SQL generation prompt.

---

### 3.3 SQL Generation — Tool Path

When the supervisor does NOT have `execute_sql`, it calls `executar_sql_agent(query="natural language question")`. Inside `tool_pool_api`, a **second LLM call** translates the question to SQL.

```
User question
    → Supervisor LLM (atendente/default prompt, no schema)
        → LLM generates: executar_sql_agent(query="top 10 clients by revenue")
            → execute_tools_node sends to tool_pool_api
                → sql_module.py:
                    1. Loads enriched schema via _get_enriched_schema_context()
                       (Redis-cached SqlTableConfig → raw SQLDatabase fallback → hardcoded fallback)
                    2. Builds context guidance via _build_context_guidance()
                       (industry, key metrics, report types from VizuClientContext)
                    3. Calls build_prompt("tool/sql-generation", variables)
                    4. Second LLM call: SystemMessage(sql_generation_prompt) + HumanMessage(query)
                    5. Validates + injects client_id + executes SQL
```

#### `tool/sql-generation` (v4 — current in Langfuse)

| Aspect | Detail |
|--------|--------|
| **Langfuse name** | `tool/sql-generation` |
| **Loaded via** | `build_prompt()` → Langfuse (primary) |
| **Goal** | Convert a natural language question into a single SQL query. Used by the tool when the supervisor can't write SQL directly. |
| **Variables** | `{{query}}` — the user's question (as passed by the supervisor)<br>`{{context_guidance}}` — client-specific business context (industry, key metrics, data notes from Context 2.0 sections)<br>`{{table_info}}` — **dynamically loaded at runtime** from actual DB metadata (via SQLDatabase or Redis-cached SqlTableConfig). Contains real column names, types, and values from the live schema. |
| **Prompt techniques** | **Dynamic schema injection** — `{{table_info}}` is the actual DB schema at runtime, not hardcoded.<br>**Explicit join reference** — maps FK relationships with USING vs ON warnings.<br>**Output-only constraint** — "Output ONLY SQL — no explanations, no markdown".<br>**Negative security rules** — "NEVER include client_id or tenant filters".<br>**Many-shot examples** — 11 SQL patterns covering all common query types.<br>**Trailing anchor** — ends with `USER QUESTION: {{query}}\n\nSQL:` to prime completion. |

**Note on `{{table_info}}`**: The schema in the prompt's fallback section uses the correct Portuguese table names, but at runtime the `{{table_info}}` variable is populated from live DB introspection — so it always has the real schema. The fallback in the prompt body only matters if no `table_info` is provided.

---

### 3.4 RAG Pipeline

When the supervisor calls `executar_rag_cliente(query="search terms")`, the tool pool routes to the RAG factory which runs a 4-stage pipeline.

```
Supervisor → executar_rag_cliente(query="rewritten search query")
    → vizu_rag_factory pipeline:
        1. RETRIEVE: Supabase vector search (pgvector + optional keyword hybrid)
        2. PREPROCESS: Query rewriting (optional, via separate LLM call)
        3. RERANK: Cohere / CrossEncoder / LLM reranker (scores relevance 0-10)
        4. MMR: Maximal Marginal Relevance for diversity
    → Final LLM call: RAG_TOOL_PROMPT with retrieved context + question
    → Returns answer to supervisor
```

#### `tool/rag-query` (v2 in Langfuse, but **⚠️ not loaded from Langfuse at runtime**)

| Aspect | Detail |
|--------|--------|
| **Langfuse name** | `tool/rag-query` |
| **Loaded via** | **Direct Python import** from `templates.py` — `from vizu_prompt_management.templates import RAG_TOOL_PROMPT` — then converted from Jinja2 to LangChain `{variable}` syntax. **Langfuse is bypassed entirely.** |
| **Goal** | Final answer generation from retrieved RAG context. Tells the LLM to synthesize information from multiple document chunks and cite sources. |
| **Variables** | `{context}` — formatted retrieved documents with metadata (source filename, relevance %, scope type)<br>`{question}` — the user's original question |
| **Prompt techniques** | **Context sovereignty** — "O contexto é soberano" (context is sovereign) — forces the LLM to only answer from provided context.<br>**Source citation** — instructs to cite `[Fonte: nome | Relevância: % | Escopo: tipo]` metadata.<br>**Multi-document synthesis** — explicitly tells LLM the chunks come from multiple documents and to combine them.<br>**Hallucination guard** — "Se você não sabe a resposta, apenas diga que não sabe." |

#### `rag/rerank` (v1 in Langfuse, loaded from templates.py)

| Aspect | Detail |
|--------|--------|
| **Langfuse name** | `rag/rerank` |
| **Loaded via** | Direct import from `templates.py` (used by LLM reranker option in vizu_rag_factory) |
| **Goal** | Score a single passage's relevance to a question (0-10 scale) for LLM-based reranking. |
| **Variables** | `{question}`, `{passage}` |
| **Prompt techniques** | **Structured scoring rubric** — defines 0/5/10 anchor points.<br>**Output constraint** — "Respond with ONLY a single integer number, nothing else." |

#### `tool/rag-query-rewrite` (v1 in Langfuse, loaded from templates.py)

| Aspect | Detail |
|--------|--------|
| **Langfuse name** | `tool/rag-query-rewrite` |
| **Loaded via** | Direct import from `templates.py` |
| **Goal** | Rewrite a user's conversational question into an optimized search query for embedding similarity + keyword search. |
| **Variables** | `{query}` |
| **Prompt techniques** | **Decomposition + expansion** — breaks multi-topic questions into core concepts, adds synonyms.<br>**Language preservation** — keeps query in same language as input.<br>**Word count target** — "15-40 words".<br>**Three worked examples** — Portuguese and English. |

#### `rag/metadata-enrichment` (v1 in Langfuse, loaded from templates.py)

| Aspect | Detail |
|--------|--------|
| **Langfuse name** | `rag/metadata-enrichment` |
| **Loaded via** | Used by the `enrich-metadata` Supabase Edge Function |
| **Goal** | Extract structured metadata (word cloud, theme classification, usage context) from document chunks during ingestion. |
| **Variables** | `{content}` — the raw text chunk |
| **Prompt techniques** | **Controlled vocabulary** — theme must be one of 13 predefined values.<br>**JSON-only output** — "Respond in JSON only — no markdown fences, no explanation".<br>**Quantity constraint** — "10-15 most salient terms". |

---

### 3.5 Supporting Prompts

These prompts exist in the codebase but play minor or legacy roles:

#### `tool/sql-agent-prefix` + `tool/sql-agent-suffix` (v1 in Langfuse)

| Aspect | Detail |
|--------|--------|
| **Status** | **LEGACY / DEPRECATED** |
| **Loaded via** | Imported in `vizu_sql_factory/factory.py` but **never actually used** — the factory function defines hardcoded inline strings instead. |
| **Original goal** | System prompt prefix/suffix for the LangChain `create_sql_agent()` ReAct agent. Instructs the agent to use `sql_db_list_tables`, `sql_db_schema`, `sql_db_query` tools. |
| **Note** | The entire `create_sql_agent_runnable()` function is deprecated. SQL generation now uses the direct single-LLM-call approach in `sql_module.py`. |

#### `tool/rag-context` (v1 in Langfuse)

| Aspect | Detail |
|--------|--------|
| **Loaded via** | Template exists, available for MCP prompt module |
| **Goal** | Simple RAG context injection — "Answer based ONLY on the context above." |
| **Variables** | `{retrieved_context}` |

#### `tool/elicitation-clarify` (v1 in templates.py only)

| Aspect | Detail |
|--------|--------|
| **Goal** | Prompt the user for missing information when a request is ambiguous. |
| **Variables** | `{original_request}`, `{missing_info}`, `{options}` (optional) |

#### `tool/sql-safety-system` (v1 in templates.py only)

| Aspect | Detail |
|--------|--------|
| **Goal** | SQL safety constraints for the `TextToSqlLLMCall` MCP prompt module. Enforces SELECT-only, client isolation, row limits. |
| **Variables** | None (static system prompt) |

#### `text_to_sql/system/v1` (v1 in templates.py only)

| Aspect | Detail |
|--------|--------|
| **Goal** | MCP prompt module system prompt for text-to-SQL with role-based access control. |
| **Variables** | `{question}`, `{schema_snapshot}`, `{role}`, `{max_rows}`, `{allowed_views}`, `{allowed_aggregates}` |

---

## 4. Variable Reference

All variables injected into prompts, where they come from, and which prompts use them:

| Variable | Source | Used In |
|----------|--------|---------|
| `{{nome_empresa}}` | `SafeClientContext.nome_empresa` (from Supabase `clientes_vizu` table) | `atendente/sql-direct`, `atendente/default` |
| `{{tools_description}}` | `build_tools_description(available_tools, ToolRegistry)` — dynamically lists tool names + descriptions based on client tier | `atendente/sql-direct`, `atendente/default` |
| `{{context_sections}}` | `VizuClientContext.to_safe_context().get_compiled_context()` — compiled from Context 2.0 sections (COMPANY_PROFILE, DATA_SCHEMA) stored in Supabase | `atendente/sql-direct`, `atendente/default` |
| `{{query}}` | User's question (or rewritten search query) | `tool/sql-generation`, `tool/rag-query-rewrite` |
| `{{context_guidance}}` | `_build_context_guidance(vizu_context)` — extracts industry, key metrics, report types, data rules from `VizuClientContext` sections | `tool/sql-generation` |
| `{{table_info}}` | `_get_enriched_schema_context()` — live DB metadata from SQLDatabase introspection or Redis-cached `SqlTableConfig` | `tool/sql-generation` |
| `{context}` | Formatted RAG results with source metadata | `tool/rag-query` |
| `{question}` | User's question | `tool/rag-query`, `rag/rerank` |
| `{passage}` | Single document chunk being scored | `rag/rerank` |
| `{content}` | Raw text chunk for metadata extraction | `rag/metadata-enrichment` |

---

## 5. Prompt Techniques Used

Summary of deliberate prompt engineering patterns across the system:

| Technique | Where | Purpose |
|-----------|-------|---------|
| **Schema embedding** | `atendente/sql-direct` | Full star schema with types, PKs, FKs so the LLM can write correct SQL without DB introspection |
| **Dynamic schema injection** | `tool/sql-generation` via `{{table_info}}` | Live schema from actual DB, plus client-specific `SqlTableConfig` enrichments (descriptions, enum values, examples) |
| **Negative constraints** | All SQL prompts | "NEVER include client_id", "NOT valor_total", "No data_transacao" — prevents the most common LLM mistakes |
| **Few-shot / many-shot examples** | `atendente/sql-direct`, `tool/sql-generation` | 8-11 real SQL query patterns covering joins, CTEs, window functions, ILIKE search |
| **Output format constraint** | `atendente/sql-direct`, `atendente/default` | "2-3 sentence summary" — prevents the LLM from dumping raw data that's already in the interactive table |
| **Completion priming** | `tool/sql-generation` | Ends with `SQL:` to prime the LLM to generate SQL immediately |
| **Context sovereignty** | `tool/rag-query` | "O contexto é soberano" — forces grounded answers, prevents hallucination |
| **Source citation** | `tool/rag-query` | Metadata format `[Fonte: X \| Relevância: Y%]` gives credibility and traceability |
| **Query decomposition** | RAG rewrite rules (embedded in supervisor prompts) + `tool/rag-query-rewrite` | Breaks multi-topic queries into keyword-rich search terms for better retrieval |
| **Fallback strategy table** | `atendente/default` | Maps unavailable dimensions to alternatives — graceful degradation |
| **Security by omission** | All SQL prompts | `client_id` is stripped from schema context before it reaches the LLM; filter is hard-injected after SQL generation |
| **Controlled vocabulary** | `rag/metadata-enrichment` | Theme must be from predefined list — ensures consistent categorical metadata |
| **Scoring rubric** | `rag/rerank` | Anchor points at 0/5/10 calibrate the LLM's relevance judgments |
| **Language-adaptive** | `atendente/sql-direct` | "YOU ALWAYS ANSWER in the user's language" — auto-detects Portuguese/English |

---

## 6. Langfuse Cleanup — Prompts to Delete

These prompts exist in Langfuse but are **never fetched by any code path**. They are safe to delete:

| Prompt | Version | Reason |
|--------|---------|--------|
| `atendente/confirmacao-agendamento` | v1 | No code references this name. Appointment confirmation feature was never built. |
| `atendente/esclarecimento` | v1 | No code references this name. Clarification flow uses elicitation service instead. |
| `rag/query` | v2 | Superseded by `tool/rag-query`. Different name, no code fetches `rag/query`. |
| `rag/hybrid` | v1 | Hybrid RAG prompt — never loaded from Langfuse, exists only in templates.py fallback. |
| `elicitation/options` | v1 | Elicitation service uses code-level logic, not Langfuse prompts. |
| `elicitation/confirmation` | v1 | Same — not loaded from Langfuse. |
| `elicitation/freeform` | v1 | Same — not loaded from Langfuse. |
| `error/tool-failed` | v1 | Error messages are generated inline in code, not via prompts. |
| `error/not-found` | v1 | Same — not loaded from Langfuse. |
| `sql-generation` | v1 | Duplicate of `tool/sql-generation` (missing `tool/` prefix). Code uses `tool/sql-generation`. |
| `sql/analytics-v2-schema` | v6 | Schema is now embedded directly in the SQL prompts. Standalone schema prompt is unused. |
| `sql/analytics-v2-guide` | v3 | Guide is now embedded directly in the SQL prompts. Standalone guide prompt is unused. |

**Total: 12 prompts to delete.**

---

## 7. Known Issues & Tech Debt

### ⚠️ RAG prompts bypass Langfuse entirely

`vizu_rag_factory/factory.py` imports `RAG_TOOL_PROMPT` directly from `templates.py` at module level and converts it to LangChain template syntax. Any edits to `tool/rag-query` in Langfuse have **zero effect** at runtime.

**Fix**: Refactor the RAG factory to use `build_prompt()` like `sql_module.py` does, or accept that RAG prompts are code-managed via `templates.py`.

### ⚠️ SQL factory imports are dead code

`vizu_sql_factory/factory.py` imports `SQL_AGENT_PREFIX` and `SQL_AGENT_SUFFIX` but uses hardcoded inline strings instead. The templates exist in `templates.py` and Langfuse but are never actually used.

**Fix**: Either wire up the templates or remove the dead imports and Langfuse entries.

### ⚠️ Langfuse variable syntax is limited

Langfuse's `{{var}}` syntax only supports plain substitution — no `{% if %}`, `{% for %}`, or default values. The builtin Jinja2 fallback supports these. This means:
- Prompts with optional sections (like `{% if context_sections %}`) work in fallback but are always rendered in Langfuse (empty string if no value provided)
- This is acceptable because `build_prompt()` always passes all variables, but the Langfuse version may have visible empty sections

### ⚠️ Hardcoded schema fallback may drift

`sql_module.py` has a `_get_hardcoded_analytics_v2_schema()` function (lines ~200-270) that returns a manually written schema string. This is the last-resort fallback if both Redis and SQLDatabase fail. If the schema changes, this function must be manually updated.

**Current status**: The hardcoded schema uses the **correct** Portuguese table/column names and matches the live database.
