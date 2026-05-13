# Prompt Rebuild Plan

Full inventory of every prompt surface in the platform, what context enters each one and from where, and the execution plan for a clean rebuild.

---

## 1. Complete Inventory

### 1.1 Agents (Layer 3 — stateful, LangGraph, checkpointer)

| Agent                     | Slug                    | Tier  | Primary Tools                                                                 | Fragment Stack (current)                                                                                                              |
| ------------------------- | ----------------------- | ----- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| **Supervisor**            | —                       | any   | `delegate_to_*`                                                               | supervisor-role + supervisor-workers + supervisor-rules                                                                               |
| **Data Analyst**          | `data-analyst`          | SME   | `execute_sql`, `executar_sql_agent`, `execute_csv_query`, `list_csv_datasets` | standalone-base + sql-schema + sql-rules + sql-examples + fallback-strategy + data-analyst-workflow + standalone-response             |
| **Knowledge Assistant**   | `knowledge-assistant`   | BASIC | `executar_rag_cliente`                                                        | standalone-base + rag-search + knowledge-assistant-workflow + standalone-response                                                     |
| **Report Generator**      | `report-generator`      | SME   | SQL + RAG + Google Sheets tools                                               | standalone-base + csv-tools + rag-search + google-export + report-generator-workflow + standalone-response                            |
| **Document Intelligence** | `document-intelligence` | SME   | OCR tools + `executar_rag_cliente`                                            | standalone-base + rag-search + document-intelligence-tools + document-intelligence-workflow + standalone-response                     |
| **Customer Support**      | `customer-support`      | BASIC | Routine tools                                                                 | named prompt: `agents/customer-support`                                                                                               |
| **RFQ Agent**             | `rfq-agent`             | BASIC | All procurement tools                                                         | standalone-base + rfq-orchestrator + rfq-supplier-liaison + rfq-optimizer + rfq-report-composer + google-export + standalone-response |
| **Config Helper**         | `config-helper`         | BASIC | Config tools                                                                  | standalone-base + config-helper-workflow                                                                                              |

### 1.2 Skills (Layer 2 — ephemeral, SkillFactory, no checkpointer)

| Skill              | Tools                                                                                 | Prompt Key                      | on_max_turns   |
| ------------------ | ------------------------------------------------------------------------------------- | ------------------------------- | -------------- |
| `analyze_csv`      | `list_csv_datasets`, `peek_csv_columns`, `execute_csv_query`                          | `skill:analyze_csv:system`      | return_partial |
| `rag_search`       | `executar_rag_cliente`                                                                | `skill:rag_search:system`       | return_partial |
| `extract_document` | `extract_document_with_ocr`, `summarize_document_sections`, `extract_structured_data` | `skill:extract_document:system` | return_partial |
| `generate_rfq`     | parse + validate + list + dispatch + check                                            | `skill:generate_rfq:system`     | **raise**      |
| `write_to_kb`      | `write_summary_to_kb`                                                                 | `skill:write_to_kb:system`      | return_partial |
| `generate_report`  | CSV + RAG + Sheets                                                                    | `skill:generate_report:system`  | return_partial |

### 1.3 Tool Prompts (internal LLM calls inside tools, NOT agent system prompts)

| Prompt Key                 | Used By                                                    | Variables In                                   | What It Does                                                     |
| -------------------------- | ---------------------------------------------------------- | ---------------------------------------------- | ---------------------------------------------------------------- |
| `tool/sql-generation`      | `executar_sql_agent`                                       | `query`, `table_info?`, `context_guidance?`    | NL → SQL (single LLM call)                                       |
| `tool/sql-safety-system`   | `TextToSqlLLMCall` (system message)                        | none                                           | SQL safety constraints                                           |
| `tool/rag-query-rewrite`   | `executar_rag_cliente` (pre-retrieval)                     | `query`                                        | Rewrites user query for embedding search                         |
| `tool/rag-query`           | **ORPHANED** — conflicts with knowledge-assistant-workflow | `context`, `question`                          | Was synthesis inside tool; architecture moved synthesis to agent |
| `tool/elicitation-clarify` | Elicitation node                                           | `original_request`, `missing_info`, `options?` | Asks clarifying question                                         |

### 1.4 Fragment Library (current, to be rebuilt)

**Identity / Shared**
| Fragment | Used By | Variables |
|----------|---------|-----------|
| `fragment/standalone-base` | all standalone agents | `agent_name`, `agent_description`, `nome_empresa`, `collected_context?`, `csv_datasets?`, `csv_datasets_details?`, `document_names?`, `document_count?`, `google_connected?`, `uploaded_file_count?` |
| `fragment/standalone-response` | all standalone agents | none |
| `fragment/supervisor-role` | Supervisor | `nome_empresa`, `context_sections?` |
| `fragment/supervisor-workers` | Supervisor | `workers_description` |
| `fragment/supervisor-rules` | Supervisor | none |

**SQL Domain**
| Fragment | Used By | Variables |
|----------|---------|-----------|
| `fragment/sql-schema` | data-analyst | none (static schema) |
| `fragment/sql-rules` | data-analyst | none |
| `fragment/sql-examples` | data-analyst | none |
| `fragment/fallback-strategy` | data-analyst | none |

**RAG Domain**
| Fragment | Used By | Variables |
|----------|---------|-----------|
| `fragment/rag-search` | knowledge-assistant, report-generator, document-intelligence | none |
| `fragment/rag-rules` | **UNUSED** — not in any agent's fragment list | none |

**Domain Specific**
| Fragment | Used By | Variables |
|----------|---------|-----------|
| `fragment/csv-tools` | report-generator | none |
| `fragment/google-export` | report-generator, rfq-agent | none |
| `fragment/document-intelligence-tools` | document-intelligence | none |
| `fragment/document-intelligence-workflow` | document-intelligence | none |
| `fragment/data-analyst-workflow` | data-analyst | `google_connected?` |
| `fragment/knowledge-assistant-workflow` | knowledge-assistant | none |
| `fragment/report-generator-workflow` | report-generator | none |
| `fragment/config-helper-workflow` | config-helper | `agent_name`, `agent_description`, `required_context`, `required_files`, `filled_fields`, `total_fields`, `uploaded_file_count`, `google_connected?` |
| `fragment/tool-usage-general` | **UNUSED** — not in any agent's fragment list | `tools_description?` |
| `fragment/anomaly-detection` | Routine: `daily_insights` (not an agent) | `kpi_snapshots`, `window_days`, `max_insights`, `language` |

**RFQ Domain** (fragments exist in registry but files not yet confirmed)
| Fragment | Used By |
|----------|---------|
| `fragment/rfq-orchestrator` | rfq-agent |
| `fragment/rfq-supplier-liaison` | rfq-agent |
| `fragment/rfq-optimizer` | rfq-agent |
| `fragment/rfq-report-composer` | rfq-agent |

### 1.5 Tool Inventory by Category

**SQL Tools**
| Tool | Tier | What It Does |
|------|------|-------------|
| `execute_sql` | SME | Executes pre-generated SQL. Agent generates SQL itself, passes it here. |
| `executar_sql_agent` | SME | NL → SQL (internal LLM call via `tool/sql-generation`) → execute. |
| `execute_csv_query` | SME | DuckDB SQL on uploaded CSVs. |
| `list_csv_datasets` | SME | Lists available CSV files + column names + row counts. |
| `peek_csv_columns` | BASIC | Preview columns + sample data from one CSV. |

**RAG / Knowledge Tools**
| Tool | Tier | What It Does |
|------|------|-------------|
| `executar_rag_cliente` | BASIC | Vector search → returns raw passages. Rewrites query first via `tool/rag-query-rewrite`. |
| `extract_document_with_ocr` | SME | OCR → markdown + structured tables. |
| `summarize_document_sections` | SME | LLM summarization of extracted sections. |
| `extract_structured_data` | SME | LLM field extraction from document text. |
| `compile_time_series` | SME | Sorts + stats on structured records with a time dimension. |
| `write_summary_to_kb` | SME | Saves analysis to knowledge base for future RAG retrieval. |

**Procurement / RFQ Tools**
| Tool | Tier | Confirmation? |
|------|------|--------------|
| `parse_buying_list` | BASIC | No |
| `validate_buying_list` | BASIC | No |
| `list_suppliers` | BASIC | No |
| `add_supplier` / `update_supplier` / `remove_supplier` | BASIC | No |
| `dispatch_rfq` | BASIC | No |
| `dispatch_rfq_whatsapp` | SME | No |
| `check_rfq_responses` | BASIC | No |
| `submit_mock_response` | BASIC | No |
| `parse_supplier_reply` | SME | No |
| `suggest_counter_offer` | BASIC | No |
| `optimize_allocation` | BASIC | No |
| `generate_po_report` | BASIC | No |
| `create_purchase_order` | BASIC | **Yes** |
| `approve_purchase_order` | BASIC | **Yes** |
| `import_buying_list_from_sheets` | BASIC | No |
| `export_po_to_sheets` | BASIC | No |

**Config Tools**
| Tool | Tier |
|------|------|
| `check_config_completeness` | BASIC |
| `save_config_field` | BASIC |
| `get_agent_requirements` | BASIC |
| `finalize_config` | BASIC |

**Google Tools** (all PREMIUM)
`write_to_sheet`, `read_emails`, `query_calendar`, `list_google_accounts`, `list_spreadsheets`, `export_to_sheet`, `create_spreadsheet_with_data`, `google_docs_create`, `google_docs_read`, `google_docs_write`, `google_docs_list`

**Web Monitoring Tools** (BASIC)
`monitor_feature`, `monitor_keywords`, `monitor_company`

**Docker MCP Tools** (ENTERPRISE)
`github_read/write`, `slack_read/send`, `stripe_read/charge`, `postgres_query`, `jira_read/write`

---

## 2. Context Sources

Where each variable in prompts actually comes from:

| Variable                              | Source                                                 | Set Where                                                         |
| ------------------------------------- | ------------------------------------------------------ | ----------------------------------------------------------------- |
| `nome_empresa`                        | `AgentState.nome_empresa`                              | Injected at session start from client record                      |
| `agent_name`                          | `AgentTypeConfig.name`                                 | Factory, from registry                                            |
| `agent_description`                   | `AgentTypeConfig.description`                          | Factory, from registry                                            |
| `collected_context`                   | `ContextService` → `AgentState.client_context`         | Loaded pre-graph via context enrichment node                      |
| `context_sections`                    | Same as above, supervisor format                       | Supervisor graph init                                             |
| `workers_description`                 | `AgentTypeRegistry.build_supervisor_description(tier)` | Built at compose time                                             |
| `csv_datasets`                        | Session metadata (uploaded files)                      | Standalone factory, from session record                           |
| `csv_datasets_details`                | Same, column-level detail                              | Standalone factory                                                |
| `document_names` / `document_count`   | Session metadata (uploaded docs)                       | Standalone factory                                                |
| `google_connected`                    | Session OAuth status                                   | Standalone factory                                                |
| `uploaded_file_count`                 | Session metadata                                       | Standalone factory                                                |
| `schema_description`                  | `ContextService` → schema mapping                      | Context enrichment (injected into sql-schema fragment at compose) |
| `query` (tool prompts)                | User message / agent call                              | Tool execution, passed as tool argument                           |
| `table_info` (sql-generation)         | Schema mapping from context                            | `executar_sql_agent` tool logic                                   |
| `context_guidance` (sql-generation)   | Optional enrichment                                    | `executar_sql_agent` tool logic                                   |
| `kpi_snapshots` (anomaly-detection)   | Nightly routine job                                    | `daily_insights` routine runner                                   |
| `required_context` / `required_files` | `agent_catalog.required_context`                       | Config helper factory                                             |
| `filled_fields` / `total_fields`      | Session config state                                   | Config helper runtime                                             |

---

## 3. Problems with the Current System

1. **Schema is duplicated** — `fragment/sql-schema` and `tool/sql-generation` have the same schema with diverged content (`dim_categoria` missing from tool, `nf_numero`/`status`/`movement_type` missing from fragment).

2. **`tool/rag-query` is orphaned** — synthesis was moved into the agent (knowledge-assistant-workflow explicitly says "tool returns raw passages, you synthesise"). The tool prompt is dead code.

3. **`fragment/rag-rules` is unused** — no agent in the registry includes it. Either dead or Langfuse-only with no builtin fallback.

4. **`fragment/tool-usage-general` is unused** — not in any agent's fragment list.

5. **data-analyst-workflow is CSV-centric** — workflow steps 1–4 are all `list_csv_datasets` / `execute_csv_query`. No SQL workflow exists. The agent's primary path (SQL) has no step-by-step guidance — only constraints scattered in `sql-rules`.

6. **data-analyst-workflow references Google Sheets** — `data-analyst` has no Google tools in `enabled_tools`.

7. **Language instruction lives in `standalone-response`** — if this fragment is ever dropped, agents have no language guidance.

8. **`tool/rag-query` is Portuguese, `tool/sql-generation` is English** — inconsistent internal prompt language.

9. **Fragment `fragment/sql-schema` is static** — schema is hardcoded. The dynamic schema from `ContextService` (`schema_description` variable) is never injected into the fragment; the fragment always shows the same hardcoded V2 schema regardless of client.

10. **Skill prompts don't exist in-repo** — all 6 skill prompts (`skill:*:system`) are Langfuse-only with no builtin fallback files.

---

## 4. New Architecture: What to Build

### Principles

- **One schema, one place** — schema fragment is the single source; tool/sql-generation references it or receives it as a variable, not as inline text.
- **No synthesis inside tools** — `executar_rag_cliente` returns raw passages. The agent synthesises.
- **Language in standalone-base** — not in standalone-response.
- **SQL and CSV are separate workflow paths** — data-analyst-workflow has two explicit branches.
- **Every fragment has exactly one owner** — no cross-cutting rules that appear in multiple fragments.
- **All skill prompts have builtin fallbacks** — parity with agent fragments.

### New Fragment Set

**Tier 0 — Identity (one per agent family)**

| New Fragment                   | Replaces | Change                                                         |
| ------------------------------ | -------- | -------------------------------------------------------------- |
| `fragment/standalone-base`     | same     | Add language instruction; move session context variables here  |
| `fragment/standalone-response` | same     | Remove language rule (moved to base); add conciseness guidance |
| `fragment/supervisor-role`     | same     | No change needed                                               |
| `fragment/supervisor-workers`  | same     | No change needed                                               |
| `fragment/supervisor-rules`    | same     | Minor cleanup                                                  |

**Tier 1 — SQL Domain**

| New Fragment                 | Replaces | Change                                                                                              |
| ---------------------------- | -------- | --------------------------------------------------------------------------------------------------- |
| `fragment/sql-schema`        | same     | Accept `{{ schema_description }}` variable for dynamic schema injection; keep static V2 as fallback |
| `fragment/sql-rules`         | same     | Remove "TOOL USAGE" section (belongs in workflow)                                                   |
| `fragment/sql-examples`      | same     | Add missing patterns (ROW_NUMBER, multi-dim) — bring to parity with tool/sql-generation examples    |
| `fragment/fallback-strategy` | same     | No change                                                                                           |

**Tier 1 — RAG Domain**

| New Fragment          | Replaces                      | Change                                                               |
| --------------------- | ----------------------------- | -------------------------------------------------------------------- |
| `fragment/rag-search` | rag-search + rag-rules merged | One fragment: tool description + query rewriting rules + usage rules |

Delete: `fragment/rag-rules` (unused, merge into rag-search)

**Tier 2 — Workflow (one per agent)**

| New Fragment                              | Replaces | Change                                                                           |
| ----------------------------------------- | -------- | -------------------------------------------------------------------------------- |
| `fragment/data-analyst-workflow`          | same     | Two paths: SQL primary path + CSV secondary path; remove Google export reference |
| `fragment/knowledge-assistant-workflow`   | same     | No change                                                                        |
| `fragment/report-generator-workflow`      | same     | Align tool names with enabled_tools                                              |
| `fragment/document-intelligence-workflow` | same     | No change                                                                        |
| `fragment/config-helper-workflow`         | same     | No change                                                                        |
| `fragment/rfq-orchestrator`               | same     | Verify/write                                                                     |
| `fragment/rfq-supplier-liaison`           | same     | Verify/write                                                                     |
| `fragment/rfq-optimizer`                  | same     | Verify/write                                                                     |
| `fragment/rfq-report-composer`            | same     | Verify/write                                                                     |

**New: Tool-level fragments**

| Fragment                               | Replaces | Variables |
| -------------------------------------- | -------- | --------- |
| `fragment/csv-tools`                   | same     | none      |
| `fragment/google-export`               | same     | none      |
| `fragment/document-intelligence-tools` | same     | none      |

**Delete entirely**

| Prompt                        | Reason                          |
| ----------------------------- | ------------------------------- |
| `tool/rag-query`              | Orphaned; synthesis is in agent |
| `fragment/rag-rules`          | Unused; merged into rag-search  |
| `fragment/tool-usage-general` | Unused                          |

**Rebuild as-is (tool prompts)**

| Prompt                     | Change                                                                                                             |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `tool/sql-generation`      | Deduplicate schema vs fragment; make `table_info` always injected dynamically; align language (pick one: EN or PT) |
| `tool/sql-safety-system`   | Remove "always include client_id filter" — security is post-query, not in LLM output                               |
| `tool/rag-query-rewrite`   | No change needed — well-written                                                                                    |
| `tool/elicitation-clarify` | No change needed                                                                                                   |

**New: Skill fallback files** (all 6 skills need `libs/blu_prompt_management/prompts/skill/*.md`)

| File                        | Skill                           |
| --------------------------- | ------------------------------- |
| `skill/analyze_csv.md`      | `skill:analyze_csv:system`      |
| `skill/rag_search.md`       | `skill:rag_search:system`       |
| `skill/extract_document.md` | `skill:extract_document:system` |
| `skill/generate_rfq.md`     | `skill:generate_rfq:system`     |
| `skill/write_to_kb.md`      | `skill:write_to_kb:system`      |
| `skill/generate_report.md`  | `skill:generate_report:system`  |

---

## 5. Context Flow per Prompt Surface

### Agent system prompts (composed from fragments at graph init)

```
ContextService + session metadata
        ↓
StandaloneAgentFactory.compose_prompt()
        ↓
variables = {
  nome_empresa, agent_name, agent_description,    ← always present
  collected_context,                               ← from ContextService
  schema_description,                              ← from ContextService (SQL agents only)
  csv_datasets, csv_datasets_details,             ← from session (if files uploaded)
  document_names, document_count,                 ← from session (if docs uploaded)
  google_connected,                               ← from session OAuth
  uploaded_file_count,                            ← from session
}
        ↓
compose_prompt(fragments=[...], variables=variables)
        ↓
AgentState.system_prompt  ← set once, used for all turns
```

### Supervisor system prompt

```
AgentTypeRegistry.build_supervisor_description(tier)  → workers_description
ContextService                                         → context_sections
        ↓
compose_prompt([supervisor-role, supervisor-workers, supervisor-rules], variables)
```

### Tool: executar_sql_agent (internal call)

```
User message → agent → tool call with { query: "..." }
        ↓
tool_pool_api:
  schema_mapping from ContextService
        ↓
PromptLoader.load("tool/sql-generation", variables={
  query: user_nl_query,
  table_info: schema_mapping or static fallback,
  context_guidance: optional extra context
})
        ↓
LLM call → SQL string
        ↓
Execute SQL with hard-injected client_id filter
        ↓
Return result rows
```

### Tool: executar_rag_cliente (internal call)

```
User message → agent → tool call with { query: "..." }
        ↓
tool_pool_api:
PromptLoader.load("tool/rag-query-rewrite", variables={ query: original_query })
        ↓
LLM call → rewritten_query
        ↓
Vector search with rewritten_query + client_id scope
        ↓
Return raw passages with source metadata  ← NO synthesis here
        ↓
Agent (knowledge-assistant) synthesises the passages into a response
```

### Skill prompts (ephemeral sub-agent)

```
SkillFactory.run(skill_name, parent_state)
        ↓
PromptLoader.load("skill:{name}:system", variables={})  ← no variables today
        ↓
Isolated AgentBuilder with filtered tools
        ↓
Last 3 messages from parent_state as conversation seed
        ↓
Run until skill output or max_turns
```

### Routine: anomaly-detection

```
Nightly job → compute KPI snapshots
        ↓
PromptLoader.load("fragment/anomaly-detection", variables={
  kpi_snapshots: json_list,
  window_days: 30,
  max_insights: 5,
  language: "pt-BR"
})
        ↓
Single LLM call → JSON insights list
```

---

## 6. Execution Plan

### Wave 1 — Delete dead weight (no prompt writing)

1. Delete `tool/rag-query` (orphaned synthesis)
2. Delete `fragment/rag-rules` (unused, merge content into `fragment/rag-search`)
3. Delete `fragment/tool-usage-general` (unused)
4. Remove Google export step from `fragment/data-analyst-workflow`

### Wave 2 — Fix SQL (highest correctness impact)

1. Rebuild `fragment/sql-schema` — add `{{ schema_description }}` variable, keep static V2 as fallback when variable is empty
2. Rebuild `fragment/sql-rules` — remove "TOOL USAGE" section
3. Rebuild `fragment/sql-examples` — bring to parity with `tool/sql-generation` examples (9 patterns, not 3)
4. Rebuild `tool/sql-generation` — remove inline schema (reference fragment instead); fix safety rule (remove "always include client_id" — that's post-execution)
5. Rebuild `fragment/data-analyst-workflow` — two explicit paths: SQL (primary) + CSV (secondary)

### Wave 3 — Fix RAG

1. Rebuild `fragment/rag-search` — merge rag-rules query-rewriting content in; single coherent fragment
2. Rebuild `fragment/knowledge-assistant-workflow` — no change needed (already correct)
3. Confirm `tool/rag-query-rewrite` is the active pre-retrieval prompt (no change)

### Wave 4 — Fix shared identity fragments

1. Move language instruction from `fragment/standalone-response` to `fragment/standalone-base`
2. Add conciseness guidance to `fragment/standalone-response`
3. Minor supervisor-rules cleanup

### Wave 5 — Write missing skill fallbacks

Write all 6 `skill/*.md` builtin fallback files with the same pattern as agent fragments.

### Wave 6 — RFQ domain audit

Verify the 4 RFQ fragments exist and are correct (rfq-orchestrator, rfq-supplier-liaison, rfq-optimizer, rfq-report-composer). These are referenced in the registry but not confirmed in-repo.

### Wave 7 — Customer Support agent

Named prompt `agents/customer-support` — not fragment-based. Audit its content separately.

---

## 7. Summary Counts

| Category             | Current           | To Delete                | To Rebuild                                  | To Create             |
| -------------------- | ----------------- | ------------------------ | ------------------------------------------- | --------------------- |
| Agent system prompts | 8                 | 0                        | 8                                           | 0                     |
| Skill prompts        | 6 (Langfuse-only) | 0                        | 6                                           | 6 (builtin fallbacks) |
| Tool prompts         | 5                 | 1 (`rag-query`)          | 2 (`sql-generation`, `sql-safety-system`)   | 0                     |
| Shared fragments     | 5                 | 0                        | 4                                           | 0                     |
| SQL fragments        | 4                 | 0                        | 3                                           | 0                     |
| RAG fragments        | 2                 | 1 (`rag-rules`)          | 1                                           | 0                     |
| Workflow fragments   | 9                 | 0                        | 2 (`data-analyst`, `document-intelligence`) | 0                     |
| Tool-use fragments   | 3                 | 1 (`tool-usage-general`) | 0                                           | 0                     |
| Routine prompts      | 1                 | 0                        | 0                                           | 0                     |
| **Total**            | **43**            | **3**                    | **26**                                      | **6**                 |
